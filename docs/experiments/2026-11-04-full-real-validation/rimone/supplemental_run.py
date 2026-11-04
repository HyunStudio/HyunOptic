"""Supplemental complete frozen replication: persist masks, freeze queue, then score GT.
Exploratory follow-up after first-pass GT inspection; never replaces first-pass outputs.
"""
import argparse,collections,datetime,hashlib,io,json,pathlib,sys,zipfile
import numpy as np
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from hyunoptic.seg.bundle import verify_bundle,file_sha256
BASE=ROOT/'reports/full_validation_20261104/new_external';OUT=BASE/'supplemental_verification';DATA=ROOT/'data/new_external_20261104'
MODELS=['papila_real_seed43_20261025','papila_camera_robust_seed43_20261025']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def prepare():
 assert (BASE/'aggregate.json').exists(),'Wait for complete first pass; no overlapping heavy compute.'
 OUT.mkdir(exist_ok=True);assert not (OUT/'protocol.json').exists()
 first=json.loads((BASE/'protocol.json').read_text())
 p=dict(created_utc=now(),purpose='Exploratory supplemental artifact verification following inspection of first-pass results; NOT untouched confirmation and no tuning/training. No author RIM classification benchmark comparison.',n_images=174,unique_image_model_pairs=348,n_additional_actual_inferences=348,total_actual_inferences_across_both_passes=696,not_new_subjects=True,models=first['models'],first_protocol_sha256=file_sha256(BASE/'protocol.json'),first_aggregate_sha256=file_sha256(BASE/'aggregate.json'),manifest_sha256=file_sha256(BASE/'input_manifest.json'),archives=first['archives'],prediction='Complete174 images for each same frozen model, sequential CPUthreads2. Save original-resolution labels PNG (0background,1disc-rim,2cup) and SHA256/status/measurement before scoring. Missing labels saved as zero solely as explicit failure sentinel.',phase_order='Finish and hash all348 predictions, compute existing image-only priority from both saved labels for all174, freeze priorities and timestamps, THEN read GT masks and perform independent pixel arithmetic. No scores change prediction/priority artifacts.',independent_metrics='Direct boolean intersection/sums Dice at supplied original resolution; vCDR span=maxrow-minrow+1, cup/disc, measurable only if both nonempty. No shared measure.dice or measure.measure_masks called.',comparison='Compare every first/second-pass status, errors, disc/cup Dice and measurable vCDR absolute error; retain all discrepancies without replacement or winner selection.',research_events=dict(baseline='baseline error/invalid geometry => True; else min(discDice,cupDice)<threshold when reference valid; otherwise None, never negative.',thresholds=[.4,.5,.6],review_fractions=[.1,.2,.5],ordering='existing review.validation.order_cases over existing review.priority applied to saved two-model predictions. Also separately report both-models-ok subgroup with its own denominator.',interpretation='Technical segmentation research events, not clinical outcomes; no threshold selection or model promotion.'),source_sha256={str(p.relative_to(ROOT)):file_sha256(p) for p in [pathlib.Path(__file__),ROOT/'src/hyunoptic/seg/inference.py',ROOT/'src/hyunoptic/seg/preprocess.py',ROOT/'src/hyunoptic/seg/model.py',ROOT/'src/hyunoptic/seg/bundle.py',ROOT/'src/hyunoptic/review/priority.py',ROOT/'src/hyunoptic/review/inputs.py',ROOT/'src/hyunoptic/review/validation.py']})
 save(OUT/'protocol.json',p);print('Supplemental protocol frozen',p['created_utc'],flush=True)
def span(mask):
 ys=np.flatnonzero(mask.any(axis=1));return None if len(ys)==0 else int(ys[-1]-ys[0]+1)
def metric(pd,pc,d,c,status):
 dd=int(pd.sum())+int(d.sum());cd=int(pc.sum())+int(c.sum())
 r=dict(disc_dice=2*int((pd&d).sum())/dd if dd else 1.,cup_dice=2*int((pc&c).sum())/cd if cd else 1.)
 dv,cv,pdv,pcv=span(d),span(c),span(pd),span(pc)
 if status=='ok' and all(x is not None for x in [dv,cv,pdv,pcv]):r['vcdr_abs_error']=abs(pcv/pdv-cv/dv)
 return r

def run():
 import torch
 from hyunoptic.seg.inference import Predictor
 from hyunoptic.review.priority import priority
 from hyunoptic.review.validation import order_cases,evaluate_budget
 p=json.loads((OUT/'protocol.json').read_text());rows=json.loads((BASE/'input_manifest.json').read_text())
 for n,h in p['source_sha256'].items():assert file_sha256(ROOT/n)==h
 assert file_sha256(BASE/'input_manifest.json')==p['manifest_sha256']
 for n,m in p['archives'].items():assert file_sha256(DATA/(n+'.zip'))==m['sha256']
 assert not (OUT/'inference_started.json').exists();save(OUT/'inference_started.json',dict(started_utc=now(),protocol_sha256=file_sha256(OUT/'protocol.json')))
 torch.set_num_threads(2);allmeta={}
 with zipfile.ZipFile(DATA/'images.zip') as iz:
  for name in MODELS:
   b=verify_bundle(ROOT/'models'/name);assert b.identity==p['models'][name]['bundle_identity'];predic=Predictor(b)
   folder=OUT/name;folder.mkdir();meta=[]
   for k,row in enumerate(rows):
    with Image.open(io.BytesIO(iz.read(row['image_member']))) as source:im=source.convert('RGB')
    status='error';errors=[];measurement=None;had_labels=False;labels=np.zeros((im.height,im.width),dtype=np.uint8)
    try:
     pred=predic.predict(im);status=pred.status;errors=pred.errors;measurement=pred.measurement
     if pred.labels is not None:
      a=np.asarray(pred.labels);assert a.shape==labels.shape and np.isin(a,[0,1,2]).all();labels=a.astype(np.uint8);had_labels=True
    except Exception as e:status='error';errors=[repr(e)]
    target=folder/(f'{k:04d}_labels.png');Image.fromarray(labels).save(target)
    rec=dict(ordinal=k,source_image_id=row['source_image_id'],status=status,errors=errors,measurement=measurement,had_labels=had_labels,labels_path=str(target.resolve()),labels_sha256=file_sha256(target),shape=list(labels.shape),saved_utc=now(),run_id=b.run_id,weights_sha256=b.weights_sha256)
    meta.append(rec);save(folder/'predictions.json',meta)
    if (k+1)%20==0 or k+1==len(rows):print('supplement',name,k+1,'/',len(rows),flush=True)
   allmeta[name]=meta
 save(OUT/'predictions_complete.json',dict(completed_utc=now(),n_saved=348,metadata_sha256={name:file_sha256(OUT/name/'predictions.json') for name in MODELS}))
 queues=[]
 for k,row in enumerate(rows):
  preds=[allmeta[name][k] for name in MODELS]
  queues.append(dict(ordinal=k,source_image_id=row['source_image_id'],priority=priority(preds),both_models_ok=all(r['status']=='ok' for r in preds)))
 save(OUT/'priorities_before_gt.json',dict(frozen_utc=now(),n_images=len(queues),rows=queues));save(OUT/'scoring_started.json',dict(started_utc=now(),priorities_sha256=file_sha256(OUT/'priorities_before_gt.json')))
 # First access to reference raster payloads in this supplemental pass occurs here.
 comparisons=[];scored={};model_summary=[]
 with zipfile.ZipFile(DATA/'segmentations.zip') as sz:
  for name in MODELS:
   first=[json.loads(l) for l in (BASE/(name+'_individual.jsonl')).read_text().splitlines()];results=[]
   for k,row in enumerate(rows):
    pred=allmeta[name][k];target=pathlib.Path(pred['labels_path']);assert file_sha256(target)==pred['labels_sha256'];labels=np.asarray(Image.open(target));assert list(labels.shape)==pred['shape']
    result=dict(ordinal=k,source_image_id=row['source_image_id'],prediction_status=pred['status'],reference_status=row['reference_status'],prediction_errors=pred['errors'])
    if row['reference_status']=='ok':
     d=np.asarray(Image.open(io.BytesIO(sz.read(row['disc_member']))))==255;c=np.asarray(Image.open(io.BytesIO(sz.read(row['cup_member']))))==255
     result.update(metric(labels>=1,labels==2,d,c,pred['status']))
    differences={}
    for key in ['prediction_status','prediction_errors','reference_status','disc_dice','cup_dice','vcdr_abs_error']:
     old=first[k].get(key);new=result.get(key)
     equal=abs(old-new)<=1e-12 if isinstance(old,(int,float)) and isinstance(new,(int,float)) else old==new
     if not equal:differences[key]=dict(first=old,supplement=new)
    if differences:comparisons.append(dict(model=name,ordinal=k,source_image_id=row['source_image_id'],differences=differences))
    results.append(result)
   scored[name]=results;save(OUT/(name+'_independent_scores.json'),results)
   vals=[r for r in results if r['reference_status']=='ok'];vm=[r['vcdr_abs_error'] for r in vals if 'vcdr_abs_error' in r]
   model_summary.append(dict(model=name,n_images=len(results),status_counts=dict(collections.Counter(r['prediction_status'] for r in vals)),disc_dice_mean=float(np.mean([r['disc_dice'] for r in vals])),cup_dice_mean=float(np.mean([r['cup_dice'] for r in vals])),vcdr_measurable=len(vm),vcdr_mae=float(np.mean(vm)) if vm else None))
 queue_evaluation=[]
 for subgroup in ['all174','both_models_ok']:
  cases=queues if subgroup=='all174' else [r for r in queues if r['both_models_ok']]
  ordered=order_cases(cases)
  for threshold in p['research_events']['thresholds']:
   outcomes=[]
   for q in ordered:
    result=scored[MODELS[0]][q['ordinal']]
    event=True if result['prediction_status']!='ok' else (min(result['disc_dice'],result['cup_dice'])<threshold if result['reference_status']=='ok' else None)
    outcomes.append(event)
   stats=[evaluate_budget(outcomes,review_fraction=b) for b in p['research_events']['review_fractions']] if outcomes else []
   queue_evaluation.append(dict(subgroup=subgroup,n_images=len(cases),threshold=threshold,priority_counts=dict(collections.Counter(c['priority']['group'] for c in cases)),budgets=stats))
 save(OUT/'first_vs_supplement_discrepancies.json',comparisons)
 summary=dict(completed_utc=now(),n_images=174,unique_image_model_pairs=348,first_pass_actual_inferences=348,supplement_actual_inferences=348,total_actual_inferences=696,n_saved_original_resolution_label_pngs=348,n_comparison_discrepancies=len(comparisons),models=model_summary,image_only_priority_counts=dict(collections.Counter(r['priority']['group'] for r in queues)),research_queue_evaluation=queue_evaluation,protocol_sha256=file_sha256(OUT/'protocol.json'),priorities_frozen_before_gt_scoring=True,patient_linkage='Unknown authoritative linkage;174images,not174verifiedindependentpatients',interpretation='Exploratory artifact verification and technical segmentation queue stress test; replication is not additional unique data or clinical evidence. First-pass outputs unchanged.')
 save(OUT/'aggregate.json',summary);print('SUPPLEMENT COMPLETE',json.dumps(summary),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);a=ap.parse_args();globals()[a.action]()
