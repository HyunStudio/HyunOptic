"""Independent equation checks, NOT author code or a trained UMCT model.
Source: Xia2020 JHU PDF, pp.5-8, Eqs.1-6,9 and Algorithm1.
No weights/data/dependencies downloaded. CPU only; deterministic seed.
"""
import hashlib, json, platform, sys, time
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parent
SEED = 20261103
torch.manual_seed(SEED)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)
torch.set_default_dtype(torch.float64)
results = []

def check(name, fn):
    start = time.perf_counter()
    details = fn()
    results.append(dict(name=name, status="PASS", seconds=time.perf_counter()-start, details=details))

def variance(samples):
    # Eq.5; population MC variance, not unbiased sample variance.
    return (samples.square().mean(0) - samples.mean(0).square()).clamp_min(0)

def fusion(predictions, uncertainty, excluded, stabilize=True):
    ids = [j for j in range(len(predictions)) if j != excluded]
    u = uncertainty[ids]
    # Numerical guard is OUR addition: the paper's 1/U has a U=0 singularity.
    c = (u.clamp_min(1e-12) if stabilize else u).reciprocal()
    weights = c / c.sum()
    target = sum(weights[k] * predictions[j] for k,j in enumerate(ids))
    return target, weights

def dice(p, y):
    dims = (0,2,3,4)
    return (1 - 2*(p*y).sum(dims)/(p.square().sum(dims)+y.square().sum(dims)).clamp_min(1e-12)).mean()

def alignment():
    x = torch.arange(2*3*5).reshape(1,1,2,3,5)
    permutations = [(0,1,2,3,4),(0,1,3,4,2),(0,1,4,2,3)]
    for p in permutations:
        inv = tuple(p.index(i) for i in range(5))
        assert torch.equal(x.permute(p).permute(inv),x)
        assert torch.equal(x.permute(p).flip(-1).flip(-1).permute(inv),x)
    rotated = torch.rot90(x,1,(-2,-1))
    assert torch.equal(torch.rot90(rotated,-1,(-2,-1)),x)
    return {"shape":list(x.shape),"permutations":len(permutations),"flip_and_rotation_roundtrips":True}

def analytical_variance_fusion():
    # Ten controlled MC outputs, binary probabilities on noncubic 3D volumes.
    delta = torch.tensor([-1.,1.]*5).reshape(10,1,1,1,1)
    ps=[]; us=[]
    for mean,amp in [(0.2,0.01),(0.4,0.02),(0.8,0.04)]:
        foreground = (mean+amp*delta).expand(10,1,2,3,5)
        samples = torch.stack([1-foreground,foreground],dim=2)
        v = variance(samples)
        assert torch.allclose(v, torch.full_like(v,amp*amp),atol=1e-15)
        assert torch.allclose(v,samples.var(0,correction=0),atol=1e-15)
        ps.append(samples.mean(0)); us.append(v.sum())
    us=torch.stack(us)
    target,w=fusion(ps,us,0)
    assert torch.allclose(w,torch.tensor([0.8,0.2]),atol=1e-12)
    assert torch.allclose(target[:,1],torch.full_like(target[:,1],0.48))
    changed=list(ps); changed[0]=1-ps[0]
    assert torch.equal(fusion(changed,us,0)[0],target)
    assert torch.allclose(target.sum(1),torch.ones_like(target[:,0]))
    return {"K":10,"volume_uncertainty":us.tolist(),"exclude_view0_weights":w.tolist(),"fused_foreground":float(target[:,1].mean()),"self_view_excluded":True}

def zero_variance_edge():
    ps=[torch.tensor([0.2,0.8]),torch.tensor([0.8,0.2]),torch.tensor([0.4,0.6])]
    uncertainty=torch.tensor([0.,0.,0.])
    raw,_=fusion(ps,uncertainty,0,stabilize=False)
    assert not torch.isfinite(raw).all()
    safe,w=fusion(ps,uncertainty,0)
    assert torch.isfinite(safe).all()
    return {"literal_reciprocal_nonfinite":True,"guarded_weights":w.tolist(),"guard_is_independent_implementation_choice":True}

def loss_backward():
    logits=[torch.randn(1,2,3,4,5,requires_grad=True) for _ in range(3)]
    p=[x.softmax(1) for x in logits]
    label=torch.nn.functional.one_hot(torch.randint(0,2,(1,3,4,5)),2).permute(0,4,1,2,3).double()
    assert abs(float(dice(label,label))) < 1e-12
    # Stop-gradient targets chosen for this test; author detach semantics unavailable.
    u=torch.tensor([0.1,0.2,0.4])
    sup=sum(dice(v,label) for v in p)
    cot=sum(dice(p[i],fusion([v.detach() for v in p],u,i)[0]) for i in range(3))
    total=sup+0.2*cot
    total.backward()
    norms=[float(x.grad.norm()) for x in logits]
    assert torch.isfinite(total) and all(torch.isfinite(x.grad).all() for x in logits)
    assert all(v>0 for v in norms)
    # A small step along -gradient must lower this fixed-target objective.
    targets=[fusion([v.detach() for v in p],u,i)[0] for i in range(3)]
    with torch.no_grad():
        q=[(x-0.01*x.grad).softmax(1) for x in logits]
        after=sum(dice(v,label) for v in q)+0.2*sum(dice(q[i],targets[i]) for i in range(3))
    assert after < total
    return {"sup":float(sup.detach()),"cot":float(cot.detach()),"total_before":float(total.detach()),"total_after_gradient_step":float(after),"gradient_norms":norms,"lambda_cot":0.2}

def dropout_forward():
    # Tiny independently constructed Conv3d, deliberately NOT paper ResNet18.
    model=torch.nn.Sequential(torch.nn.Conv3d(1,4,(3,3,1),padding=(1,1,0)),torch.nn.ReLU(),torch.nn.Dropout3d(0.5),torch.nn.Conv3d(4,2,1))
    x=torch.randn(1,1,4,5,6)
    model.train()
    with torch.no_grad():
        samples=torch.stack([model(x).softmax(1) for _ in range(10)])
    u=variance(samples)
    assert samples.shape==(10,1,2,4,5,6)
    assert torch.isfinite(u).all() and u.sum()>0
    model.eval()
    with torch.no_grad():
        a=model(x);b=model(x)
    assert torch.equal(a,b)
    return {"shape":list(samples.shape),"train_mc_volume_uncertainty":float(u.sum()),"eval_repeat_equal":True,"random_toy_weights":True}

start=time.perf_counter()
for name,fn in [("inverse_view_alignment",alignment),("eq5_eq6_analytical",analytical_variance_fusion),("zero_variance_singularity",zero_variance_edge),("eq1_eq2_eq4_eq9_backward",loss_backward),("toy_3d_dropout_forward",dropout_forward)]:
    check(name,fn)
out={"classification":"independent_formula_unit_checks_only_not_author_execution_or_accuracy","seed":SEED,"python":sys.version,"torch":torch.__version__,"platform":platform.platform(),"device":"cpu","cuda_available":torch.cuda.is_available(),"checks":results,"total_seconds":time.perf_counter()-start,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"paper_sha256":hashlib.sha256((ROOT/'xia2020uncertainty.pdf').read_bytes()).hexdigest()}
(ROOT/'formula_results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
