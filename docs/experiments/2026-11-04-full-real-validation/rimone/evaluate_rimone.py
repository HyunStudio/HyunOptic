"""RIM-ONE DL frozen external segmentation audit; only ignored local outputs.
Prepare freezes inputs and protocol without predicting. Run requires existing protocol.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,io,json,pathlib,sys,zipfile
import numpy as np
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hyunoptic.seg.bundle import verify_bundle,file_sha256
from hyunoptic.measure import dice,measure_masks
OUT=ROOT/'reports/full_validation_20261104/new_external'
DATA=ROOT/'data/new_external_20261104'
MODELS=['papila_real_seed43_20261025','papila_camera_robust_seed43_20261025']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def digest(b):return hashlib.sha256(b).hexdigest()
def read_image(z,n):
 with Image.open(io.BytesIO(z.read(n))) as im:return im.convert('RGB')
def refs(z,row,shape):
 ans=[]
 for part in ['disc','cup']:
  a=np.asarray(Image.open(io.BytesIO(z.read(row[part+'_member']))))
  if a.ndim!=2 or a.shape!=shape or set(np.unique(a))-{0,255}:raise ValueError('Reference shape/value contract violated: '+part)
  mask=a==255
  if not mask.any():raise ValueError('Empty reference '+part)
  ans.append(mask)
 return ans

def prepare():
 assert not (OUT/'protocol.json').exists(),'Refuse to overwrite frozen protocol'
 rows=[];failures=[];hashes=[]
 with zipfile.ZipFile(DATA/'images.zip') as iz,zipfile.ZipFile(DATA/'segmentations.zip') as sz:
  members=sorted(n for n in iz.namelist() if '/partitioned_by_hospital/test_set/' in n and n.endswith('.png'))
  assert len(members)==174,'Unexpected official test count'
  for n in members:
   pp=pathlib.PurePosixPath(n);stem=pp.stem;group=pp.parent.name
   row=dict(image_member=n,source_image_id=stem,group=group,image_sha256=digest(iz.read(n)))
   hashes.append(row['image_sha256'])
   try:
    im=read_image(iz,n);row['width'],row['height']=im.size
    for part in ['disc','cup']:
     mn=f'RIM-ONE_DL_reference_segmentations/{group}/{stem}-1-{part.title()}-T.png'
     row[part+'_member']=mn;row[part+'_sha256']=digest(sz.read(mn))
    d,c=refs(sz,row,(im.height,im.width));m=measure_masks(d,c).to_dict()
    row['reference_measurement']=m;row['reference_status']='ok'
   except Exception as e:row['reference_status']='error';row['reference_error']=repr(e);failures.append(row)
   rows.append(row)
 assert len(set(hashes))==174,'Duplicate image payload in selected hospital test'
 identities={}
 for name in MODELS:
  b=verify_bundle(ROOT/'models'/name);assert not b.synthetic and not b.partial
  identities[name]=dict(run_id=b.run_id,weights_sha256=b.weights_sha256,bundle_identity=b.identity)
 save(OUT/'input_manifest.json',rows);save(OUT/'reference_failures.json',failures)
 protocol=dict(created_utc=now(),dataset='RIM-ONE DL',purpose='Exploratory frozen PAPILA-trained external segmentation evaluation, NOT a reproduction of the original RIM-ONE DL benchmark or eligible RIM-only training leaderboard comparison.',terms='Research/education only; no redistribution or commercial use. All images/masks/IDs/weights and individual rows stay ignored/local.',official_repository='https://github.com/miag-ull/rim-one-dl',partition='Complete partitioned_by_hospital/test_set, HUMS+HCSC; do not add random partition or training images.',n_selected=len(rows),n_reference_valid=len(rows)-len(failures),n_reference_failure=len(failures),groups=dict(collections.Counter(r['group'] for r in rows)),patient_linkage='Unknown. No authoritative patient-to-image linkage verified; n_images must never be described as n_independent_patients. Image bootstrap intervals are descriptive and do not account for patient clustering.',reference='Official supplied binary PNG masks; foreground 255, background 0. Official conversion source archived for format provenance; no contour refitting, resizing or geometry repair.',prediction='Existing Predictor.predict(RGB image) only, bundle-fixed letterbox and postprocess; no reference crops, tuning, training or outcome-driven retries. CPU threads=2.',dice='Original supplied image resolution; disc includes cup. Per-image macro mean over reference-valid selected images, including invalid geometry and errors. Missing prediction masks replaced by all-empty masks for Dice; preserve statuses separately.',vcdr='Axis-aligned nonzero-mask vertical spans including endpoints; absolute error only where reference and prediction have valid nonempty disc/cup. Publish measurable numerator and reference-valid/selected denominators, plus failures and warnings.',statistics='Mean, SD, median, min,max; deterministic 2000 image bootstrap mean 95% percentile CI seed=20261104; exploratory, unclustered, no formal superiority claims.',models=identities,archives={n:dict(sha256=file_sha256(DATA/(n+'.zip')),bytes=(DATA/(n+'.zip')).stat().st_size) for n in ['images','segmentations']},manifest_sha256=file_sha256(OUT/'input_manifest.json'),source_sha256={str(p.relative_to(ROOT)):file_sha256(p) for p in [pathlib.Path(__file__),ROOT/'src/hyunoptic/seg/inference.py',ROOT/'src/hyunoptic/seg/preprocess.py',ROOT/'src/hyunoptic/seg/model.py',ROOT/'src/hyunoptic/seg/bundle.py',ROOT/'src/hyunoptic/measure.py']})
 save(OUT/'protocol.json',protocol)
 print(json.dumps({k:protocol[k] for k in ['n_selected','n_reference_valid','n_reference_failure','groups','created_utc']}),flush=True)

def stat(values):
 a=np.asarray(values,dtype=float)
 if not len(a):return dict(n=0,mean=None)
 rng=np.random.default_rng(20261104);bs=np.mean(a[rng.integers(0,len(a),size=(2000,len(a)))],axis=1)
 return dict(n=len(a),mean=float(a.mean()),sd=float(a.std(ddof=1)) if len(a)>1 else 0.,median=float(np.median(a)),min=float(a.min()),max=float(a.max()),image_bootstrap_95ci_mean=[float(x) for x in np.quantile(bs,[.025,.975])])

def run():
 import torch
 from hyunoptic.seg.inference import Predictor
 torch.set_num_threads(2)
 protocol=json.loads((OUT/'protocol.json').read_text());rows=json.loads((OUT/'input_manifest.json').read_text())
 assert file_sha256(OUT/'input_manifest.json')==protocol['manifest_sha256']
 for n,h in protocol['source_sha256'].items():assert file_sha256(ROOT/n)==h,'Source changed after protocol freeze: '+n
 for n,meta in protocol['archives'].items():assert file_sha256(DATA/(n+'.zip'))==meta['sha256']
 assert not (OUT/'inference_started.json').exists(),'No silent rerun permitted; preserve failure and obtain explicit new protocol if needed.'
 save(OUT/'inference_started.json',dict(started_utc=now(),protocol_sha256=file_sha256(OUT/'protocol.json')))
 aggregates=[]
 with zipfile.ZipFile(DATA/'images.zip') as iz,zipfile.ZipFile(DATA/'segmentations.zip') as sz:
  for name in MODELS:
   b=verify_bundle(ROOT/'models'/name);identity=protocol['models'][name]
   assert b.weights_sha256==identity['weights_sha256'] and b.identity==identity['bundle_identity']
   predictor=Predictor(b);results=[]
   with (OUT/(name+'_individual.jsonl')).open('x',encoding='utf-8') as f:
    for k,row in enumerate(rows,1):
     result=dict(source_image_id=row['source_image_id'],group=row['group'],reference_status=row['reference_status'])
     if row['reference_status']!='ok':result['reference_error']=row.get('reference_error')
     else:
      im=read_image(iz,row['image_member']);d,c=refs(sz,row,(im.height,im.width));pd=np.zeros_like(d);pc=np.zeros_like(c)
      try:
       pred=predictor.predict(im);result.update(prediction_status=pred.status,prediction_errors=pred.errors)
       if pred.disc is not None:pd=pred.disc
       if pred.cup is not None:pc=pred.cup
       if pred.measurement is not None:
        result['vcdr_abs_error']=abs(pred.measurement['vertical_cdr']-row['reference_measurement']['vertical_cdr']);result['prediction_measurement']=pred.measurement
      except Exception as e:result.update(prediction_status='exception',prediction_errors=[repr(e)])
      result.update(disc_dice=dice(d,pd),cup_dice=dice(c,pc),reference_measurement=row['reference_measurement'])
     f.write(json.dumps(result,allow_nan=False)+'\n');f.flush();results.append(result)
     if k%20==0 or k==len(rows):print(name,k,'/',len(rows),flush=True)
   valid=[r for r in results if r['reference_status']=='ok'];meas=[r for r in valid if 'vcdr_abs_error' in r]
   aggregate=dict(model=name,identity=identity,n_selected=len(rows),n_reference_valid=len(valid),n_reference_failure=len(rows)-len(valid),prediction_status_counts=dict(collections.Counter(r['prediction_status'] for r in valid)),disc_dice=stat([r['disc_dice'] for r in valid]),cup_dice=stat([r['cup_dice'] for r in valid]),vcdr_abs_error=stat([r['vcdr_abs_error'] for r in meas]),vcdr_measurable=len(meas),vcdr_reference_valid_denominator=len(valid),vcdr_selected_denominator=len(rows),reference_warning_count=sum(bool(r['reference_measurement']['warnings']) for r in valid),prediction_warning_count=sum(bool(r.get('prediction_measurement',{}).get('warnings')) for r in valid),by_group={g:dict(n_images=len(rs),disc_dice=stat([r['disc_dice'] for r in rs]),cup_dice=stat([r['cup_dice'] for r in rs]),vcdr_measurable=sum('vcdr_abs_error' in r for r in rs),vcdr_abs_error=stat([r['vcdr_abs_error'] for r in rs if 'vcdr_abs_error' in r])) for g in ['normal','glaucoma'] if (rs:=[r for r in valid if r['group']==g])},completed_utc=now())
   save(OUT/(name+'_aggregate.json'),aggregate);aggregates.append(aggregate)
 save(OUT/'aggregate.json',dict(dataset='RIM-ONE DL hospital-heldout test',protocol_sha256=file_sha256(OUT/'protocol.json'),completed_utc=now(),models=aggregates,patient_linkage=protocol['patient_linkage'],purpose=protocol['purpose']))
 print('COMPLETE',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args();globals()[args.action]()
