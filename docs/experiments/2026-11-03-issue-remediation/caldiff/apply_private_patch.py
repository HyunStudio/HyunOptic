"""Build private source variants without editing the pinned original checkout.

CalDiff has no verified license; generated source variants are private review
material. Only the minimal diff and this original harness are publication candidates.
"""
import argparse, difflib, hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parents[1]/'paper_execution_20261103/caldiff/source'
parser=argparse.ArgumentParser()
parser.add_argument('--stage',choices=['channels','clones','patched'],default='patched')
args=parser.parse_args()
DEST=ROOT/('private_'+args.stage)

def replace_once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

changes={
 'guided_diffusion/distribution.py':[
  ('self.blocks = []','self.blocks = nn.ModuleList()'),
  ('x = x.float()','x = x.to(dtype=next(self.blocks[0].parameters()).dtype)'),
  ("self.blocks[i].to('cuda')(x)",'self.blocks[i].to(device=x.device)(x)')],
 'guided_diffusion/script_util.py':[
  ('prior = AxisAlignedConvGaussian(input_channels_dist,','prior = AxisAlignedConvGaussian(input_channels_dist + 1,')],
 'guided_diffusion/gaussian_diffusion.py':[]}
if args.stage in ('clones','patched'):
    changes['guided_diffusion/gaussian_diffusion.py'] += [
      ('x_t=x_start.float()','x_t=x_start.float().clone()'),
      ('x_t_k=x_start.float()','x_t_k=x_start.float().clone()')]
if args.stage=='patched':
    changes['guided_diffusion/gaussian_diffusion.py'].append(("terms['sa']=terms['mse']","terms['sa']=terms['mse'].clone()"))
    changes['guided_diffusion/gaussian_diffusion.py'] += [
      ('from torchvision.utils import save_image',''),
      ('from .train_util import visualize',''),
      ('from torchvision import transforms','')]
diff=[]
manifest={}
for path in SRC.rglob('*.py'):
    rel=path.relative_to(SRC).as_posix()
    original=path.read_bytes().decode('utf-8')
    patched=original
    for old,new in changes.get(rel,[]):
        patched=replace_once(patched,old,new)
    target=DEST/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if patched == original:
        shutil.copy2(path,target)
    else:
        target.write_bytes(patched.encode('utf-8'))
    if patched!=original:
        diff.extend(difflib.unified_diff(original.splitlines(keepends=True),patched.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
        manifest[rel]=dict(original_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),patched_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(ROOT/(args.stage+'.patch')).write_bytes(''.join(diff).encode('utf-8'))
(ROOT/(args.stage+'_patch_manifest.json')).write_text(json.dumps(manifest,indent=2))
print(DEST)
