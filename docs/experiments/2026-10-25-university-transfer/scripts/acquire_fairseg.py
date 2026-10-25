import concurrent.futures, hashlib, json, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/university_20261025/fairseg_test'
OUT.mkdir(parents=True,exist_ok=True)
BASE='https://huggingface.co/datasets/harvardairobotics/FairSeg'

def get(url):
    for attempt in range(4):
        try:
            return urllib.request.urlopen(url,timeout=90).read()
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)

if __name__=='__main__':
    info=json.loads(get('https://huggingface.co/api/datasets/harvardairobotics/FairSeg'))
    revision=info['sha']
    # Tree response is paginated: follow HTTP Link, not a guessed file range.
    url='https://huggingface.co/api/datasets/harvardairobotics/FairSeg/tree/'+revision+'/Dataset/Test?recursive=true&limit=1000'
    files=[]
    while url:
        with urllib.request.urlopen(url,timeout=60) as r:
            files.extend(json.load(r)); link=r.headers.get('Link','')
        import re
        match=re.search(r'<([^>]+)>; rel="next"',link)
        url=match.group(1) if match else None
    files=[x for x in files if x['type']=='file' and x['path'].endswith('.npz')]
    assert len(files)==2000,len(files)
    manifest={'revision':revision,'n_files':len(files),'files':files}
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'data_summary.csv').write_bytes(get(BASE+'/resolve/'+revision+'/ReadMe/data_summary.csv'))
    def download(item):
        p=OUT/Path(item['path']).name
        expected=item['lfs']['oid']
        if not p.exists():
            b=get(BASE+'/resolve/'+revision+'/'+item['path'])
            assert len(b)==item['size']
            assert hashlib.sha256(b).hexdigest()==expected
            p.write_bytes(b)
        else:
            assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
        return p.name
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(download,x):x for x in files}
        for n,f in enumerate(concurrent.futures.as_completed(futures),1):
            try:f.result()
            except Exception as e:errors.append({'path':futures[f]['path'],'error':str(e)})
            if n%50==0:print('FairSeg verified',n,'/',len(files),'errors',len(errors),flush=True)
    (OUT/'download_result.json').write_text(json.dumps({'verified':len(files)-len(errors),'errors':errors},indent=2))
    assert not errors,errors
