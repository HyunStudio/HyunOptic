"""Controlled CalDiff execution; never loads external checkpoints/data or installs packages."""
import ast, hashlib, importlib, json, platform, subprocess, sys, traceback, types
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'source'
sys.path.insert(0, str(SRC))
import numpy as np
import torch
torch.manual_seed(20261103)
torch.cuda.manual_seed_all(20261103)
np.random.seed(20261103)
torch.set_num_threads(2)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
R = {'seed':20261103, 'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,
     'platform':platform.platform(),'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),
     'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=SRC,text=True).strip(),
     'source_sha256':{str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.rglob('*.py')},'checks':[]}
def check(name, fn):
    try:
        val=fn(); R['checks'].append({'name':name,'status':'PASS','detail':val})
    except Exception as e:
        R['checks'].append({'name':name,'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()})
    print(json.dumps(R['checks'][-1],default=str),flush=True)

check('unmodified_gaussian_diffusion_import',lambda:importlib.import_module('guided_diffusion.gaussian_diffusion').__name__)
from guided_diffusion.distribution import AxisAlignedConvGaussian
device='cuda'
def dist(ch, posterior=False):
    return AxisAlignedConvGaussian(ch,[32,64,128,192],3,6,{'w':'he_normal','b':'normal'},posterior=posterior).to(device,dtype=torch.double)
patch=torch.randn(2,1,32,32,device=device)
mask=(torch.rand_like(patch)>.6).float()
prior=dist(1)
posterior=dist(1,True)
def native_calibration():
    p=prior(patch); q=posterior(patch,mask)
    assert len(p)==len(q)==3
    for d in p+q:
        assert d.mean.shape==(2,6) and torch.isfinite(d.mean).all() and (d.stddev>0).all()
    kl=[torch.distributions.kl_divergence(a,b) for a,b in zip(q,p)]
    assert all(torch.isfinite(k).all() and (k>=0).all() for k in kl)
    sum(k.mean() for k in kl).backward()
    assert torch.isfinite(prior.conv_layer1.weight.grad).all()
    registered={id(p) for p in prior.parameters()}
    missing=[n for n,_ in prior.encoder.blocks[0].named_parameters() if id(dict(prior.encoder.blocks[0].named_parameters())[n]) not in registered]
    assert missing
    return {'distribution_shapes':[[*d.mean.shape] for d in p], 'kl_mean':[k.mean().item() for k in kl], 'encoder_block0_parameters_missing_from_model_parameters':missing, 'note':'Author Encoder.blocks is a plain list, so optimizer/state_dict omit encoder weights; gradients still computed.'}
check('unmodified_author_calibration_forward_kl_backward',native_calibration)
check('unmodified_factory_prior_called_as_author_loss',lambda:prior(patch,mask))

# Only bypass unavailable UNUSED imports. AST retains every function/class body verbatim.
path=SRC/'guided_diffusion/gaussian_diffusion.py'
tree=ast.parse(path.read_text())
removed=[]
new=[]
for node in tree.body:
    if isinstance(node,ast.ImportFrom) and node.module in ('torchvision.utils','torchvision','train_util'):
        removed.append(ast.get_source_segment(path.read_text(),node)); continue
    new.append(node)
tree.body=new
gd=types.ModuleType('guided_diffusion.gaussian_diffusion')
gd.__package__='guided_diffusion'
sys.modules[gd.__name__]=gd
exec(compile(tree,str(path),'exec'),gd.__dict__)
R['import_adapter_removed_unused_imports']=removed
from guided_diffusion.unet import UNetModel
model=UNetModel(image_size=32,in_channels=2,model_channels=32,out_channels=2,num_res_blocks=1,attention_resolutions=(),channel_mult=(1,2),num_heads=1).cuda()
diff=gd.GaussianDiffusion(betas=gd.get_named_beta_schedule('linear',1000),model_mean_type=gd.ModelMeanType.EPSILON,model_var_type=gd.ModelVarType.LEARNED_RANGE,loss_type=gd.LossType.MSE)
def native_unet():
    y=model(torch.cat([patch,mask],1),torch.tensor([0,10],device=device))
    assert y.shape==(2,2,32,32) and torch.isfinite(y).all()
    return {'shape':list(y.shape),'parameters':sum(p.numel() for p in model.parameters()),'note':'Unmodified author UNet body; reduced model config, random weights.'}
check('unmodified_author_unet_forward_reduced_config',native_unet)
t=torch.tensor([0,10],device=device)
def loss_run(p, backward=True):
    x=torch.cat([patch,mask],1)
    terms,y=diff.training_losses_segmentation(model,None,p,posterior,x,t,noise=torch.zeros_like(mask))
    assert y.shape==(2,1,32,32)
    assert set(terms)=={'vb','mse','kl','sa','loss'}
    for k,v in terms.items(): assert v.shape==(2,) and torch.isfinite(v).all(),k
    if backward:
        terms['loss'].mean().backward()
        assert model.out[-1].weight.grad is not None and torch.isfinite(model.out[-1].weight.grad).all()
        assert torch.isfinite(p.conv_layer1.weight.grad).all()
    return {'terms':{k:v.detach().cpu().tolist() for k,v in terms.items()},'mse_and_sa_same_tensor':terms['mse'].data_ptr()==terms['sa'].data_ptr(),'input_mutated':not torch.equal(x[:,-1:],mask), 'note':'No optimizer step; controlled tensors and random weights, no performance evidence.'}
check('author_loss_body_with_factory_prior_import_adapter_only',lambda:loss_run(prior))
adapted_prior=dist(2)
check('author_loss_body_prior_two_channels_adapter_forward_only',lambda:loss_run(adapted_prior,False))
check('author_loss_body_prior_two_channels_adapter_forward_backward',lambda:loss_run(adapted_prior))
# Evidence above isolates the second failure to x_start.float() aliases reused
# in consecutive steps. Add clones only at those two assignments in-memory.
class CloneInput(ast.NodeTransformer):
    def visit_Assign(self,node):
        if any(isinstance(t,ast.Name) and t.id in ('x_t','x_t_k') for t in node.targets):
            if ast.unparse(node.value)=='x_start.float()':
                node.value=ast.Call(func=ast.Attribute(value=node.value,attr='clone',ctx=ast.Load()),args=[],keywords=[])
        return node
adapted_tree=CloneInput().visit(tree)
ast.fix_missing_locations(adapted_tree)
exec(compile(adapted_tree,str(path),'exec'),gd.__dict__)
R['loss_adapter']='x_t=x_start.float().clone(); x_t_k=x_start.float().clone(); prior input_channels=2. No other function-body edits.'
diff=gd.GaussianDiffusion(betas=gd.get_named_beta_schedule('linear',1000),model_mean_type=gd.ModelMeanType.EPSILON,model_var_type=gd.ModelVarType.LEARNED_RANGE,loss_type=gd.LossType.MSE)
check('adapted_author_loss_two_channels_and_clone_forward_backward',lambda:loss_run(adapted_prior))
(ROOT/'results.json').write_text(json.dumps(R,indent=2,default=str))
print('RESULTS',ROOT/'results.json',flush=True)
