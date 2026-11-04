import requests,json,pathlib,datetime,hashlib
out=pathlib.Path('reports/full_validation_20261104/new_external'); data=pathlib.Path('data/new_external_20261104')
s=requests.Session(); s.headers['User-Agent']='HyunOptic academic research provenance check'
records=[]
repo=s.get('https://api.github.com/repos/miag-ull/rim-one-dl/commits/master',timeout=30); repo.raise_for_status(); commit=repo.json()['sha']; (out/'official_commit.json').write_text(json.dumps(repo.json(),indent=2))
for name in ['README.md','LICENSE.txt','dcseg_to_binary_mask.py','generate_dir_binary_masks.py']:
 r=s.get(f'https://raw.githubusercontent.com/miag-ull/rim-one-dl/{commit}/{name}',timeout=30); r.raise_for_status(); (out/('official_'+name)).write_bytes(r.content); records.append(dict(name=name,url=r.url,sha256=hashlib.sha256(r.content).hexdigest(),bytes=len(r.content),status=r.status_code))
for name,fid in [('images','1teYi_smpLiNZNJcTWdxXgKKLW2fkUQr4'),('segmentations','1eb1V9V65TuwFNYmYsIzgdAgdWyD6o7bG')]:
 url=f'https://drive.google.com/uc?export=download&id={fid}'
 try:
  r=s.get(url,timeout=(30,60),stream=True); p=data/(name+('.zip' if 'zip' in r.headers.get('Content-Type','') or 'attachment' in r.headers.get('Content-Disposition','') else '_access_response.html')); h=hashlib.sha256(); n=0
  with p.open('wb') as f:
   for chunk in r.iter_content(1024*1024): f.write(chunk);h.update(chunk);n+=len(chunk)
  records.append(dict(name=name,source_url=url,resolved_url=r.url,status=r.status_code,content_type=r.headers.get('Content-Type'),bytes=n,sha256=h.hexdigest(),local_path=str(p)))
  print(name,r.status_code,n,r.url,flush=True)
 except Exception as e: records.append(dict(name=name,source_url=url,error=repr(e)));print(name,repr(e),flush=True)
(out/'provenance.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),official_commit=commit,assets=records),indent=2))
