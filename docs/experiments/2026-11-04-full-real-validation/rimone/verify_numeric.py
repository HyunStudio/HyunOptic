"""Independent numeric/accounting audit of frozen RIM-ONE external artifacts."""
import json,pathlib,statistics,hashlib,datetime
import numpy as np
OUT=pathlib.Path(__file__).resolve().parent
p=json.loads((OUT/'protocol.json').read_text());manifest=json.loads((OUT/'input_manifest.json').read_text());a=json.loads((OUT/'aggregate.json').read_text());checks=[];summaries=[]
assert p['created_utc']<json.loads((OUT/'inference_started.json').read_text())['started_utc']
assert len(manifest)==174 and len({r['source_image_id'] for r in manifest})==174
for model in a['models']:
 rows=[json.loads(line) for line in (OUT/(model['model']+'_individual.jsonl')).read_text().splitlines()]
 assert len(rows)==174 and [r['source_image_id'] for r in rows]==[r['source_image_id'] for r in manifest]
 valid=[r for r in rows if r['reference_status']=='ok'];meas=[r for r in valid if 'vcdr_abs_error' in r]
 assert model['n_selected']==len(rows) and model['n_reference_valid']==len(valid) and model['vcdr_measurable']==len(meas)
 for key in ['disc_dice','cup_dice']:
  vals=[r[key] for r in valid];assert all(0<=v<=1 for v in vals)
  assert abs(statistics.mean(vals)-model[key]['mean'])<1e-12
 vals=[r['vcdr_abs_error'] for r in meas]
 assert (abs(statistics.mean(vals)-model['vcdr_abs_error']['mean'])<1e-12 if vals else model['vcdr_abs_error']['mean'] is None)
 strict=[r['vcdr_abs_error'] for r in meas if not r['reference_measurement']['warnings'] and not r.get('prediction_measurement',{}).get('warnings')]
 summaries.append(dict(model=model['model'],all_rows_accounted=True,macro_means_independently_verified=True,n_selected=len(rows),n_reference_valid=len(valid),n_vcdr_measurable=len(meas),n_reference_warning=sum(bool(r['reference_measurement']['warnings']) for r in valid),strict_no_warning_vcdr=dict(n=len(strict),mae=statistics.mean(strict) if strict else None)))
 report_ids=set(p['models']);assert model['model'] in report_ids
checks.append('Frozen protocol precedes inference; all 174 selected rows accounted once for both models; independently recomputed macro means match aggregates to 1e-12.')
report=dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,models=summaries,scope='Independent arithmetic/accounting verification from saved individual results, not independent re-inference or raw predicted-mask Dice recomputation; prediction masks were not saved by protocol.')
(OUT/'independent_numeric_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

