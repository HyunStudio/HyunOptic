import io,json,pathlib,zipfile,numpy as np
from PIL import Image
from hyunoptic.chaksu import scan_test_archive
from hyunoptic.seg import preprocess
from hyunoptic.seg.data import cases_for,verify_split_manifest
from hyunoptic.papila import load_image

def stats(image):
    arr,_=preprocess.image_array(image,384); arr=arr.astype(float)/255
    pixels=arr[arr.max(2)>.05]; means=pixels.mean(0)
    return {'r':float(means[0]),'g':float(means[1]),'b':float(means[2]),'r_over_g':float(means[0]/max(means[1],1e-8)),'b_over_g':float(means[2]/max(means[1],1e-8)),'luma':float((pixels@np.array([.2126,.7152,.0722])).mean()),'luma_sd':float((pixels@np.array([.2126,.7152,.0722])).std())}
def sample(items,n): return [items[k] for k in np.linspace(0,len(items)-1,min(n,len(items)),dtype=int)]
split=verify_split_manifest(json.loads(pathlib.Path('models/papila_real_v1_20261025/split_manifest.json').read_text(encoding='utf-8')))
groups={'papila_development':[stats(load_image(c)) for c in sample(cases_for(pathlib.Path('data/PAPILA'),split,'development'),32)]}
cases,_=scan_test_archive('data/Chaksu_Test.zip')
with zipfile.ZipFile('data/Chaksu_Test.zip') as archive:
    for camera in ('bosch','forus','remidio'):
        groups[camera]=[stats(Image.open(io.BytesIO(archive.read(c.image_member))).convert('RGB')) for c in sample([c for c in cases if c.camera==camera],16)]
output={key:{'n':len(values),'mean':{name:float(np.mean([v[name] for v in values])) for name in values[0]},'min':{name:float(np.min([v[name] for v in values])) for name in values[0]},'max':{name:float(np.max([v[name] for v in values])) for name in values[0]}} for key,values in groups.items()}
pathlib.Path('reports/remediation_20261025/colour_diagnostic_summary.json').write_text(json.dumps({'sampled_diagnostic_not_performance_estimate':True,'groups':output},indent=2),encoding='utf-8')
print(json.dumps(output),flush=True)
