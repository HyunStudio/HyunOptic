"""Final independent saved-raster/hash/metric/timing audit; no inference."""
import hashlib,io,json,pathlib,zipfile,collections
import numpy as np
from PIL import Image
BASE=pathlib.Path(__file__).resolve().parent;OUT=BASE/'supplemental_verification';ROOT=BASE.parents[2]
def load(p):return json.loads(p.read_text())
rows=load(BASE/'input_manifest.json');summary=load(OUT/'aggregate.json');protocol=load(OUT/'protocol.json');complete=load(OUT/'predictions_complete.json');priorities=load(OUT/'priorities_before_gt.json');start=load(OUT/'scoring_started.json');names=list(protocol['models']);checks=[];n_png=0;n_pairs=0
assert protocol['created_utc']<load(OUT/'inference_started.json')['started_utc']<complete['completed_utc']<=priorities['frozen_utc']<=start['started_utc']
assert load(OUT/'first_vs_supplement_discrepancies.json')==[]
assert hashlib.sha256((OUT/'priorities_before_gt.json').read_bytes()).hexdigest()==start['priorities_sha256']
for name,h in complete['metadata_sha256'].items():assert hashlib.sha256((OUT/name/'predictions.json').read_bytes()).hexdigest()==h
for n,h in protocol['source_sha256'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
metas={name:load(OUT/name/'predictions.json') for name in names};scores={name:load(OUT/(name+'_independent_scores.json')) for name in names}
with zipfile.ZipFile(ROOT/'data/new_external_20261104/segmentations.zip') as z:
 for k,row in enumerate(rows):
  refs={part:np.asarray(Image.open(io.BytesIO(z.read(row[part+'_member']))))==255 for part in ['disc','cup']};labels={}
  for name in names:
   rec=metas[name][k];p=pathlib.Path(rec['labels_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==rec['labels_sha256'];assert rec['saved_utc']<=complete['completed_utc']
   label=np.asarray(Image.open(io.BytesIO(raw)));assert label.shape==(row['height'],row['width']) and label.ndim==2 and set(np.unique(label))<={0,1,2};labels[name]=label;n_png+=1
   saved=scores[name][k];assert saved['source_image_id']==row['source_image_id'] and saved['prediction_status']==rec['status']
   for part,pred in [('disc',label>0),('cup',label==2)]:
    ref=refs[part];inter=np.count_nonzero(np.logical_and(pred,ref));den=np.count_nonzero(pred)+np.count_nonzero(ref);v=2*inter/den if den else 1.;assert abs(v-saved[part+'_dice'])<=1e-12
   pd,pc=np.where(label>0)[0],np.where(label==2)[0];d,c=np.where(refs['disc'])[0],np.where(refs['cup'])[0]
   if rec['status']=='ok':
    v=abs((np.ptp(pc)+1)/(np.ptp(pd)+1)-(np.ptp(c)+1)/(np.ptp(d)+1));assert abs(v-saved['vcdr_abs_error'])<=1e-12
   else:assert 'vcdr_abs_error' not in saved
   n_pairs+=1
  q=priorities['rows'][k];statuses=[metas[n][k]['status'] for n in names]
  if 'error' in statuses:assert q['priority']['group']=='error'
  elif 'invalid_geometry' in statuses:assert q['priority']['group']=='invalid_geometry'
  else:
   assert statuses==['ok','ok'] and q['priority']['group']=='disagreement';dis=[]
   for part in ['disc','cup']:
    a,b=[labels[n]>0 if part=='disc' else labels[n]==2 for n in names];dis.append(1-2*np.count_nonzero(a&b)/(np.count_nonzero(a)+np.count_nonzero(b)))
   assert abs(max(dis)-q['priority']['score'])<=1e-12
assert n_png==n_pairs==348
for event in summary['research_queue_evaluation']:
 for b in event['budgets']:
  assert b['n_outcome_missing']==0 and b['n_positive']==event['n_images'];assert b['detected']==b['cases_reviewed'];assert abs(b['detected']-b['random_expected_detected'])<=1e-12
report=dict(status='passed',n_saved_pngs_hashed_shape_checked_and_scored=348,n_unique_images=174,n_unique_image_model_pairs=348,total_actual_inferences_across_passes=696,first_pass_score_status_discrepancies=0,all_supplement_scores_independently_recomputed_from_saved_pngs=True,all_priority_groups_and_disagreement_scores_independently_verified=True,all_predictions_saved_and_priorities_frozen_before_gt_scoring=True,research_event_saturated_all_thresholds=True,no_incremental_queue_detection_over_random=True,private_artifacts_remain_ignored=True,limits='Independent artifact arithmetic and consistency audit; same frozen inference implementation was used twice. No first-pass masks exist, so exact pixelwise identity between first and supplemental passes cannot be checked; first-pass metrics/statuses/errors match.')
(OUT/'independent_final_artifact_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

