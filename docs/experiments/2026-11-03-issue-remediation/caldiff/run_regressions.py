"""Private controlled CalDiff regression harness; no datasets/checkpoints/installations.

Imports author modules through an explicitly labelled unused-import AST adapter.
The original checkout is never edited. --source chooses a private patched copy.
"""
import argparse, ast, hashlib, importlib, io, json, platform, subprocess, sys, traceback, types
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT.parents[1] / 'paper_execution_20261103/caldiff/source'
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=ORIGINAL)
parser.add_argument('--label', default='original')
args = parser.parse_args()
SRC = args.source.resolve()
sys.path.insert(0, str(SRC))
torch.set_num_threads(2)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.manual_seed(20261103)
np.random.seed(20261103)
R = dict(label=args.label, seed=20261103, python=sys.version, torch=torch.__version__,
         numpy=np.__version__, platform=platform.platform(), cuda=torch.version.cuda,
         gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
         source=str(SRC), original_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ORIGINAL,text=True).strip(),
         hashes={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.rglob('*.py')}, checks=[])

def check(name, fn):
    try:
        detail = fn()
        item = dict(name=name, status='PASS', detail=detail)
    except Exception as exc:
        item = dict(name=name, status='FAIL', error=repr(exc), traceback=traceback.format_exc())
    R['checks'].append(item)
    print(json.dumps(item), flush=True)

def import_native():
    return importlib.import_module('guided_diffusion.gaussian_diffusion').__name__
check('native_import_without_adapter', import_native)
path = SRC/'guided_diffusion/gaussian_diffusion.py'
tree = ast.parse(path.read_text())
removed=[]
body=[]
for node in tree.body:
    if isinstance(node, ast.ImportFrom) and node.module in ('torchvision.utils','torchvision','train_util'):
        removed.append(ast.get_source_segment(path.read_text(), node))
    else:
        body.append(node)
tree.body=body
if removed:
    gd=types.ModuleType('guided_diffusion.gaussian_diffusion')
    gd.__package__='guided_diffusion'
    sys.modules[gd.__name__]=gd
    exec(compile(tree,str(path),'exec'),gd.__dict__)
else:
    gd=importlib.import_module('guided_diffusion.gaussian_diffusion')
R['adapter_removed_unused_imports']=removed
R['import_mode']='AST adapter' if removed else 'direct native module import'
from guided_diffusion.distribution import AxisAlignedConvGaussian
from guided_diffusion.script_util import model_and_diffusion_defaults, create_model_and_diffusion

def dist(device):
    return AxisAlignedConvGaussian(2,[32,64,128,192],3,6,{'w':'he_normal','b':'normal'}).to(device,dtype=torch.double)

def encoder_optimizer(device):
    # Removing ModuleList registration makes SGD omit this weight even with a real nonzero gradient.
    p=dist(device)
    x=torch.randn(2,2,32,32,device=device)
    opt=torch.optim.SGD(p.parameters(),lr=1e-3)
    w=p.encoder.blocks[0][0].weight
    out=p(x)
    before=w.detach().clone()
    objective=sum(d.mean.square().mean()+d.variance.mean() for d in out)
    objective.backward()
    assert w.grad is not None and torch.isfinite(w.grad).all() and w.grad.abs().sum()>0
    opt.step()
    delta=(w-before).abs().max().item()
    assert delta>0, 'encoder weight has gradient but optimizer did not update it'
    return dict(max_encoder_weight_update=delta, encoder_gradient_norm=w.grad.norm().item())

def roundtrip(device):
    # Missing encoder state causes different output after a fresh module loads the saved state.
    p=dist(device).eval()
    x=torch.randn(2,2,32,32,device=device)
    expected=p(x)
    buf=io.BytesIO()
    torch.save(p.state_dict(),buf)
    buf.seek(0)
    state=torch.load(buf,weights_only=True,map_location=device)
    q=dist(device).eval()
    q.load_state_dict(state,strict=True)
    actual=q(x)
    assert any(k.startswith('encoder.blocks.') for k in state), 'encoder weights omitted from state_dict'
    assert all(torch.equal(a.mean,b.mean) and torch.equal(a.stddev,b.stddev) for a,b in zip(expected,actual)), 'output differs after state_dict roundtrip'
    assert torch.equal(p.encoder.blocks[0][0].weight,q.encoder.blocks[0][0].weight)
    return dict(state_entries=len(state), encoder_entries=sum(k.startswith('encoder.blocks.') for k in state), exact_output_equality=True)

def factory(device):
    cfg=model_and_diffusion_defaults()
    cfg.update(image_size=32,num_channels=32,num_res_blocks=1,channel_mult='1,2',num_heads=1,
               attention_resolutions='1',learn_sigma=True)
    model,diff,p,q=create_model_and_diffusion(**cfg)
    return model.to(device),diff,p.to(device),q.to(device)

def loss_case(device, action):
    model,diff,p,q=factory(device)
    image=torch.randn(2,1,32,32,device=device)
    mask=(torch.rand_like(image)>.6).float()
    x=torch.cat([image,mask],1)
    original=x.clone()
    t=torch.tensor([0,10],device=device)
    noise=torch.full_like(mask,.25)
    calls=[]
    hook=model.register_forward_hook(lambda mod, inputs, output: calls.append(output))
    # Capture the actual random SA noise, leaving the author's sampling method unchanged.
    noises=[]
    native_q_sample=diff.q_sample
    def record_sample(*a,**kw):
        noises.append(kw['noise'].clone())
        return native_q_sample(*a,**kw)
    diff.q_sample=record_sample
    terms,y=diff.training_losses_segmentation(model,None,p,q,x,t,noise=noise)
    hook.remove()
    assert set(terms)=={'vb','mse','kl','sa','loss'}
    assert all(v.shape==(2,) and torch.isfinite(v).all() for v in terms.values())
    if action=='input':
        assert torch.equal(x,original), 'author loss mutated caller input'
        return dict(input_unchanged=True)
    if action=='arithmetic':
        assert terms['mse'].data_ptr()!=terms['sa'].data_ptr(), 'MSE and SA alias the same storage'
        # Author EPSILON target: independent reconstruction from captured noise/predictions.
        base=(noise-calls[0][:,:1]).square().mean((1,2,3))
        consecutive=(noises[1]-calls[1][:,:1]).square().mean((1,2,3))
        expected_sa=(base+consecutive*torch.tensor([0.,1.],device=device))/4
        torch.testing.assert_close(terms['mse'],base)
        torch.testing.assert_close(terms['sa'],expected_sa)
        expected_loss=base+terms['vb']+.01*terms['kl']+.99*expected_sa
        torch.testing.assert_close(terms['loss'],expected_loss)
        return dict(mse=base.detach().cpu().tolist(),sa=expected_sa.detach().cpu().tolist(),loss=terms['loss'].detach().cpu().tolist(),independent_storage=True,normalization='SA=(MSE_t + masked MSE_t_minus_1)/4; KL unchanged /1000')
    terms['loss'].mean().backward()
    groups={}
    for name,module in [('unet',model),('prior',p),('posterior',q)]:
        params=list(module.named_parameters())
        assert all(v.grad is not None and torch.isfinite(v.grad).all() for _,v in params),name
        groups[name]=dict(parameter_tensors=len(params),nonzero_gradient_tensors=sum(v.grad.abs().sum().item()>0 for _,v in params))
    assert p.encoder.blocks[0][0].weight.grad.abs().sum()>0
    return dict(loss=terms['loss'].detach().cpu().tolist(),gradients=groups,output_shape=list(y.shape),prior_input_channels=p.encoder.input_channels)

devices=['cpu']+(['cuda'] if torch.cuda.is_available() else [])
for device in devices:
    check(device+'_encoder_optimizer_update',lambda d=device:encoder_optimizer(d))
    check(device+'_encoder_state_roundtrip',lambda d=device:roundtrip(d))
    for action in ('input','arithmetic','backward'):
        check(device+'_factory_loss_'+action,lambda d=device,a=action:loss_case(d,a))
(ROOT/(args.label+'_results.json')).write_text(json.dumps(R,indent=2))
print('SUMMARY',json.dumps({s:sum(c['status']==s for c in R['checks']) for s in ('PASS','FAIL')}),flush=True)
