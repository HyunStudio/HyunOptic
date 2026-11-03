"""Verify original byte preservation and record private remediation artifact hashes."""
import ast, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parents[1]/'paper_execution_20261103/caldiff/source'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
baseline=json.loads((ROOT/'original_results.json').read_text())['hashes']
assert baseline=={str(p.relative_to(SRC)):sha(p) for p in SRC.rglob('*.py')}
subprocess.run(['git','diff','--exit-code'],cwd=SRC,check=True)
subprocess.run(['git','apply','--check',str(ROOT/'patched.patch')],cwd=SRC,check=True)
changed=[]
for rel in baseline:
    if sha(SRC/rel)!=sha(ROOT/'private_patched'/rel): changed.append(rel.replace('\\','/'))
assert sorted(changed)==['guided_diffusion/distribution.py','guided_diffusion/gaussian_diffusion.py','guided_diffusion/script_util.py']
result=json.loads((ROOT/'patched_results.json').read_text())
tree=ast.parse((SRC/'guided_diffusion/gaussian_diffusion.py').read_text())
unused_import_loads={name:sum(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id==name for n in ast.walk(tree)) for name in ('save_image','visualize','transforms')}
assert all(count==0 for count in unused_import_loads.values())
assert all(c['status']=='PASS' for c in result['checks'])
assert len([c for c in result['checks'] if c['status']=='PASS'])==11
assert result['import_mode']=='direct native module import'
R=dict(original_bytes_match_baseline=True,original_git_diff_exit_code=0,patch_apply_check_exit_code=0,
       byte_changed_files=changed,controlled_regressions_passed=10,native_import_passed=True,removed_import_executable_name_loads=unused_import_loads,
       artifacts={p.name:sha(p) for p in ROOT.iterdir() if p.is_file() and p.name not in ('artifact_verification.json','verification.log')})
(ROOT/'artifact_verification.json').write_text(json.dumps(R,indent=2))
print(json.dumps(R,indent=2))
