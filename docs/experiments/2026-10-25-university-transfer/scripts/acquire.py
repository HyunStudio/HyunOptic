"""Acquire official archives; preserve checksums and source metadata locally."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'university_20261025'
OUT.mkdir(parents=True, exist_ok=True)

def acquire(name, url, md5=None):
    target = OUT / name
    partial = OUT / (name + '.part')
    if not target.exists():
        start = time.time()
        with urllib.request.urlopen(url, timeout=90) as r, partial.open('wb') as w:
            last = start
            while block := r.read(4*1024*1024):
                w.write(block)
                if time.time()-last > 25:
                    print(name, round(w.tell()/1e6), 'MB', flush=True)
                    last = time.time()
        partial.rename(target)
    h = hashlib.md5()
    sha = hashlib.sha256()
    with target.open('rb') as f:
        while block := f.read(4*1024*1024):
            h.update(block); sha.update(block)
    if md5 and h.hexdigest() != md5:
        raise ValueError('Source checksum mismatch: '+name)
    result = dict(name=name, url=url, bytes=target.stat().st_size, md5=h.hexdigest(), sha256=sha.hexdigest(), source_md5_verified=bool(md5))
    (OUT / (name+'.provenance.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps(result), flush=True)
    return result

if __name__ == '__main__':
    jobs = [
      ('Harvard-FairSeg.zip','https://zenodo.org/api/records/13178701/files/Harvard-FairSeg.zip/content','b5d4de9869064df7786b7ba29ed84faa'),
      ('OLIVES_Dataset_Labels.zip','https://zenodo.org/api/records/7105232/files/OLIVES_Dataset_Labels.zip/content','e0b14b14f457e4abcafafdd60b8d3952'),
      ('2015_BOE_Chiu2.zip','https://people.duke.edu/~sf59/Datasets/2015_BOE_Chiu2.zip',None)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(acquire,*j) for j in jobs]
        for f in concurrent.futures.as_completed(fs):
            try:f.result()
            except Exception as e:print(type(e).__name__, str(e), flush=True)
