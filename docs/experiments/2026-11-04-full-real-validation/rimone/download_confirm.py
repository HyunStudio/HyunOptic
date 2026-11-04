import requests,re,pathlib,json,hashlib,zipfile
p=pathlib.Path('data/new_external_20261104'); out=pathlib.Path('reports/full_validation_20261104/new_external'); html=(p/'images_access_response.html').read_text(); params=dict(re.findall(r'name="([^"]+)" value="([^"]+)"',html)); r=requests.get('https://drive.usercontent.google.com/download',params=params,stream=True,timeout=(30,90)); h=hashlib.sha256();n=0
with (p/'images.zip').open('wb') as f:
 for c in r.iter_content(1024*1024):f.write(c);h.update(c);n+=len(c)
record=dict(source='official Google Drive download confirmation form',url=r.url,status=r.status_code,bytes=n,sha256=h.hexdigest(),content_type=r.headers.get('Content-Type'))
(out/'images_confirm_download.json').write_text(json.dumps(record,indent=2));print(record,flush=True)
for name in ['images','segmentations']:
 z=zipfile.ZipFile(p/(name+'.zip')); (out/(name+'_archive_listing.json')).write_text(json.dumps([dict(name=i.filename,size=i.file_size,compressed=i.compress_size) for i in z.infolist()],indent=2));print(name,len(z.namelist()),z.namelist()[:12],flush=True)
