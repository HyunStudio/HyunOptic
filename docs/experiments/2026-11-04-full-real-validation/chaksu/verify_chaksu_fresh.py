"""Fresh arithmetic + stratified pixel QA; no inference or product metric imports."""
import collections, hashlib, io, json, pathlib, zipfile
import numpy as np
from PIL import Image
ROOT=pathlib.Path.cwd(); BASE=ROOT/'reports/full_validation_20261104/chaksu'
read=lambda p:json.loads(p.read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=[json.loads(l) for l in (BASE/'private_reference_rows.jsonl').read_text().splitlines()]
dices=read(BASE/'private_all_returned_mask_dice.json'); supp=read(BASE/'supplement_public_safe.json')
models=list(supp['all_returned_mask_dice']); experts=['expert '+str(i) for i in range(1,6)]
idx={(r['case_id'],r['model'],r['expert']):r for r in dices}
assert len(idx)==len(dices)==3284
checks=0
def same(a,b):
 global checks
 checks+=1
 if isinstance(a,dict):
  assert a.keys()==b.keys()
  for k in a:same(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):same(x,y)
 elif isinstance(a,(int,float)) and not isinstance(a,bool):assert abs(a-b)<1e-12,(a,b)
 else:assert a==b,(a,b)
def stats(xs):
 a=np.array(xs,float);n=len(a)
 if not n:return dict(n=0,mean=None,image_iid_bootstrap_mean_95_interval=None)
 means=np.random.default_rng(20261104).choice(a,size=(2000,n)).mean(1)
 return dict(n=n,mean=float(a.mean()),median=float(np.median(a)),min=float(a.min()),max=float(a.max()),image_iid_bootstrap_mean_95_interval=np.quantile(means,[.025,.975]).tolist())
for m in models:
 for e in experts:
  for cam in ['all','bosch','forus','remidio']:
   rr=[r for r in dices if r['model']==m and r['expert']==e and (cam=='all' or r['camera']==cam)]
   for field in ['disc_dice','cup_dice']:same(stats([r[field] for r in rr]),supp['all_returned_mask_dice'][m][e][cam][field])
for e in experts:
 for cam in ['all','bosch','forus','remidio']:
  rr=[r for r in rows if (cam=='all' or r['camera']==cam) and all((r['case_id'],m,e) in idx for m in models)]
  for field in ['disc_dice','cup_dice']:
   same(stats([idx[r['case_id'],models[1],e][field]-idx[r['case_id'],models[0],e][field] for r in rr]),supp['paired_model_dice_robust_minus_real'][e][cam][field])
same({e:sum(r['references'][e]['status']=='ok' for r in rows) for e in experts},{e:sum((r['case_id'],models[0],e) in idx for r in rows) for e in experts})
selected=[r for cam in ['bosch','forus','remidio'] for r in sorted([r for r in rows if r['camera']==cam],key=lambda r:r['case_id'])[:10]]
qa=collections.Counter()
def ratio(d,c):
 dy=np.flatnonzero(d.any(1));cy=np.flatnonzero(c.any(1))
 return float((cy[-1]-cy[0]+1)/(dy[-1]-dy[0]+1)) if len(dy) and len(cy) else None
def dice(a,b):
 den=int(a.sum())+int(b.sum());return float(2*np.logical_and(a,b).sum()/den) if den else 1.
with zipfile.ZipFile(ROOT/'data/Chaksu_Test.zip') as z:
 for r in selected:
  labs={}
  for p in r['predictions']:
   raw=pathlib.Path(p['labels_path']).read_bytes();same(sha(raw),p['labels_sha256'])
   lab=np.asarray(Image.open(io.BytesIO(raw)));same(sha(lab.tobytes()),p['labels_pixel_sha256'])
   same(list(lab.shape),list(reversed(r['image_size'])));assert set(np.unique(lab))<={0,1,2}
   value=ratio(lab>=1,lab==2);same(value is not None,p['measurement'] is not None)
   if value is not None:same(value,p['measurement']['vertical_cdr'])
   same(p['status'],'ok' if value is not None else 'invalid_geometry')
   qa['prediction_masks']+=1;labs[p['model']]=lab
  for e in experts:
   ref=r['references'][e];masks=[];valid=True
   for part in ['disc','cup']:
    raw=z.read(ref['members'][part]['member']);same(sha(raw),ref['members'][part]['sha256'])
    arr=np.asarray(Image.open(io.BytesIO(raw)).convert('L'));levels=set(np.unique(arr))
    valid &= arr.shape==tuple(reversed(r['image_size'])) and len(levels)<=2 and 0 in levels and arr.max()>0
    masks.append(arr>0);qa['reference_rasters']+=1
   d,c=masks;valid &= not np.any(c&~d)
   same(bool(valid),ref['status']=='ok');qa['valid_reader_references' if valid else 'failed_reader_references']+=1
   for m,lab in labs.items():
    same((r['case_id'],m,e) in idx,bool(valid))
    if valid:
     met=idx[r['case_id'],m,e]
     same(dice(lab>=1,d),met['disc_dice']);same(dice(lab==2,c),met['cup_dice']);qa['pixel_dice_model_reader_rows']+=1
     same(ratio(d,c),ref['vcdr'])
  qa['cases']+=1
report=dict(passed=True,scope='Full 3284 saved Dice-row aggregate arithmetic, plus first 10 lexicographic cases EACH of 3 cameras: 30-case stratified original-pixel QA. QA selection is not a performance estimator; all inference remains the separate complete 336-image run.',aggregate_rows=3284,aggregate_summary_cells=120,n_numeric_and_identity_checks=checks,pixel_qa=dict(qa),independent_product_imports=False,inference_performed=False,reference_failures='Retained as unavailable, never zero Dice or zero error.',limitations=['Full 3284 raw-pixel model-reader Dice recomputation was not performed by this reviewer.','Image-IID intervals are descriptive; patient linkage is incomplete.'])
out=ROOT/'reports/full_validation_20261104/final_review/chaksu_fresh_verification.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
