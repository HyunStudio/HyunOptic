import hashlib,importlib.util,json,math,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).parent
SRC=ROOT/'DDU'
sys.path.insert(0,str(SRC))
sys.path.insert(0,str(ROOT/'deps'))
torch.manual_seed(20261103)
torch.set_num_threads(2)
from utils.gmm_utils import gmm_fit,gmm_get_logits
from metrics.uncertainty_confidence import entropy,mutual_information_prob

results=[]
def check(name,fn):
    start=time.perf_counter()
    try:
        detail=fn()
        results.append(dict(name=name,status='passed',seconds=round(time.perf_counter()-start,4),detail=detail))
    except Exception as exc:
        results.append(dict(name=name,status='failed',seconds=round(time.perf_counter()-start,4),error=type(exc).__name__+': '+str(exc)))

means=torch.tensor([[0.,0.],[5.,0.],[0.,5.]],dtype=torch.float64)
features=torch.cat([.2*torch.randn(128,2,dtype=torch.float64)+m for m in means])
labels=torch.arange(3).repeat_interleave(128)

def full_rank():
    g,j=gmm_fit(features,labels,3)
    logits=gmm_get_logits(g,means)
    assert torch.isfinite(logits).all()
    assert logits.argmax(1).tolist()==[0,1,2]
    # Independent NumPy Gaussian log-pdf calculation.
    sample=np.array([.1,.2]); actual=gmm_get_logits(g,torch.tensor(sample)[None])[0].numpy()
    expected=[]
    for c in range(3):
        x=features[labels==c].numpy(); mu=x.mean(0); cov=np.cov(x,rowvar=False,ddof=1)
        d=sample-mu; expected.append(-.5*(2*math.log(2*math.pi)+np.linalg.slogdet(cov)[1]+d@np.linalg.inv(cov)@d))
    error=float(np.max(np.abs(actual-np.array(expected))))
    assert error<1e-6
    inside=torch.logsumexp(logits,1)
    outside=torch.logsumexp(gmm_get_logits(g,torch.tensor([[50.,50.]],dtype=torch.float64)),1)
    assert outside.max()<inside.min()
    return dict(jitter=float(j),analytic_max_absolute_error=error,controlled_class_means_correct=3,
                synthetic_ood_density_lower=True,not_a_dataset_benchmark=True)

def spectral_model():
    from net.resnet import resnet18
    net=resnet18(spectral_normalization=True,mod=True).eval()
    image=torch.randn(2,3,32,32)
    with torch.no_grad(): a=net(image); b=net(image)
    assert a.shape==(2,10) and torch.isfinite(a).all()
    assert torch.allclose(a,b)
    assert net.feature.shape[0]==2
    return dict(logits_shape=list(a.shape),features_shape=list(net.feature.shape),random_weights=True)

def entropy_check():
    h=entropy(torch.zeros(3,10))
    assert torch.allclose(h,torch.full((3,),math.log(10)),atol=1e-6)
    p=torch.softmax(torch.randn(5,10),1)
    mi=mutual_information_prob(p[None].repeat(4,1,1))
    assert torch.allclose(mi,torch.zeros_like(mi),atol=1e-6)
    return dict(uniform_entropy=float(h[0]),identical_model_mi_max_abs=float(mi.abs().max()))

def singular_native():
    g,j=gmm_fit(torch.zeros(16,2,dtype=torch.float64),torch.arange(2).repeat_interleave(8),2)
    val=gmm_get_logits(g,torch.zeros(1,2,dtype=torch.float64))
    assert torch.isfinite(val).all()
    return dict(jitter=float(j),finite=True)

check('author_gda_full_rank_and_analytic_density',full_rank)
check('author_spectral_resnet18_forward_repeat',spectral_model)
check('author_entropy_and_mutual_information',entropy_check)
check('author_singular_covariance_jitter_current_runtime',singular_native)
summary=dict(paper='Deep Deterministic Uncertainty: A New Simple Baseline (CVPR2023), related to 2021 segmentation workshop',
    upstream='https://github.com/omegafragger/DDU',commit=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip(),
    python=sys.version.split()[0],torch=torch.__version__,seed=20261103,device='cpu',
    isolated_dependencies={'tqdm':'4.67.1'},initial_import_failure='ModuleNotFoundError: No module named tqdm; installed isolated --target dependency only',
    execution='Unmodified author functions on controlled tensors and random-weight network; no trained model or real dataset accuracy',
    source_hashes={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SRC/'utils/gmm_utils.py',SRC/'net/resnet.py',SRC/'metrics/uncertainty_confidence.py']},tests=results)
(ROOT/'oxford_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
