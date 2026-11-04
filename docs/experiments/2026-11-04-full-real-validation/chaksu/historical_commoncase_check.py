"""Descriptive legacy comparison; no inference and no legacy result reuse."""
import collections,json
from pathlib import Path
import harness as h
from hyunoptic.seg.bundle import file_sha256

def main():
  rows=[json.loads(l) for l in (h.OUT/'private_reference_rows.jsonl').read_text().splitlines()]
  newrows={r['case_id']:r for r in rows}
  dice=json.loads((h.OUT/'private_all_returned_mask_dice.json').read_text())
  diceidx={(r['case_id'],r['model'],r['expert']):r for r in dice}
  metrics=json.loads((h.OUT/'private_metrics.json').read_text())
  metricidx={(r['case_id'],r['model'],r['expert']):r for r in metrics}
  report={'created_utc':h.now(),'posthoc_descriptive':True,
    'purpose':'Compare historical versus freshly inferred metrics only on legacy311 images where all five references passed. No new inference or substitution of old outputs.',
    'limits':'Legacy25 reference-blocked images had no model inference; old16/19 prediction failures among311 cannot be compared directly with new18/20 among336 as worsening. Old masks were not preserved, so label-level identity cannot be tested. Thread count changed from historical4 to current2; equality was not assumed.',
    'models':{}}
  mismatches=[]
  for model in h.MODEL_NAMES:
    paths=list((Path('models')/model/'evaluation').glob('chaksu*/model_eval_private_cases.json'));assert len(paths)==1
    path=paths[0];legacy=json.loads(path.read_text())['cases'];assert len(legacy)==336
    common=[r for r in legacy if r.get('failure_category')!='load_or_geometry_error'];assert len(common)==311
    blocked=[r for r in legacy if r.get('failure_category')=='load_or_geometry_error'];assert len(blocked)==25
    deltas=collections.defaultdict(list);statuses=collections.Counter()
    for old in common:
      row=newrows[old['case_id']];pred=next(p for p in row['predictions'] if p['model']==model)
      statuses[(old['status'],pred['status'])]+=1
      assert all(r['status']=='ok' for r in row['references'].values())
      if old['status']!=pred['status']:mismatches.append({'model':model,'case_id':old['case_id'],'kind':'status','old':old['status'],'new':pred['status']})
      for legacyexpert,expert in [('expert1','expert 1'),('expert2','expert 2')]:
        reference=row['references'][expert];new={**diceidx.get((row['case_id'],model,expert),{}),**metricidx.get((row['case_id'],model,expert),{}),'reference_vcdr':reference['vcdr']}
        for key in ['disc_dice','cup_dice','reference_vcdr','abs_vcdr_error']:
          if key not in old.get(legacyexpert,{}) or key not in new:continue
          delta=abs(old[legacyexpert][key]-new[key]);deltas[f'{expert}/{key}'].append(delta)
          if delta:mismatches.append({'model':model,'case_id':old['case_id'],'expert':expert,'metric':key,'absolute_difference':delta})
    report['models'][model]={'legacy_private_file_sha256':file_sha256(path),'n_legacy_images':336,'n_legacy_reference_blocked_without_inference':25,'n_comparable_images':311,
      'legacy_status_counts_on_common311':dict(collections.Counter(r['status'] for r in common)),
      'new_status_counts_on_common311':dict(collections.Counter(next(p for p in newrows[r['case_id']]['predictions'] if p['model']==model)['status'] for r in common)),
      'new_status_counts_on_previously_blocked25':dict(collections.Counter(next(p for p in newrows[r['case_id']]['predictions'] if p['model']==model)['status'] for r in blocked)),
      'status_transitions':[{'old':a,'new':b,'n':n} for (a,b),n in statuses.items()],
      'metrics':{key:{'n_compared':len(v),'n_exact_equal':sum(d==0 for d in v),'n_nonzero_difference':sum(d!=0 for d in v),'max_absolute_difference':max(v) if v else None} for key,v in deltas.items()}}
  h.write('historical_commoncase_public_safe.json',report);h.write('private_historical_metric_differences.json',mismatches)
  h.log(f'HISTORICAL CHECK complete; nonzero/status mismatch entries {len(mismatches)}')
if __name__=='__main__':main()
