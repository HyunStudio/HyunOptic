"""Post-run integrity audit and returned-mask Dice sensitivity; no repairs."""
import ast, collections, json, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image
import harness as h
from hyunoptic.chaksu import scan_test_archive, _read_member, EXPERTS
from hyunoptic.seg.bundle import file_sha256, verify_bundle

def main():
  assert (h.OUT/'completion.json').exists()
  protocol=json.loads((h.OUT/'protocol.json').read_text())
  assert file_sha256(h.OUT/'harness.py')==protocol['harness_sha256']
  source_changes=[{'path':p,'executed_source_sha256':v,'post_run_source_sha256':file_sha256(Path(p))} for p,v in protocol['source_sha256'].items() if file_sha256(Path(p))!=v]
  assert all(c['path']=='src/hyunoptic/chaksu.py' for c in source_changes), source_changes
  old_source=subprocess.check_output(['git','show','9cd674e:src/hyunoptic/chaksu.py']).decode('utf-8')
  new_source=Path('src/hyunoptic/chaksu.py').read_text(encoding='utf-8')
  function_proof={}
  for name in ['_read_member','load_test_case']:
    dumps=[]
    for source in [old_source,new_source]:
      node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
      dumps.append(ast.dump(node,include_attributes=False))
    assert dumps[0]==dumps[1],name
    function_proof[name]={'ast_identical_without_line_attributes':True,'ast_sha256':h.digest(dumps[0].encode())}
  assert all(verify_bundle(Path('models')/m['name']).identity==m['identity'] for m in protocol['models'])
  phase=json.loads((h.OUT/'inference_phase_complete.json').read_text())
  assert phase['private_predictions_sha256']==file_sha256(h.OUT/'private_predictions.jsonl')
  assert phase['queue_sha256']==file_sha256(h.OUT/'private_queue_frozen_before_references.json')
  rows=[json.loads(l) for l in (h.OUT/'private_reference_rows.jsonl').read_text().splitlines()]
  assert len(rows)==336
  metrics=json.loads((h.OUT/'private_metrics.json').read_text())
  dice_rows=[{k:r[k] for k in ['case_id','camera','model','expert','disc_dice','cup_dice']} for r in metrics]
  statuses=collections.Counter(); missing=[]; refcats=collections.Counter(); checks=0
  cases,layout=scan_test_archive(h.ARCHIVE)
  assert layout['metadata_path_fingerprint_only']==protocol['layout']['metadata_path_fingerprint_only']
  assert layout['readable_case_counts_by_camera']==protocol['layout']['readable_case_counts_by_camera']
  with zipfile.ZipFile(h.ARCHIVE) as zf:
    for case,row in zip(cases,rows):
      assert case.case_id==row['case_id']
      for expert,ref in row['references'].items():
        if ref['status']!='ok':
          for err in ref['errors']:
            cat='reference_geometry_cup_outside_disc' if err.startswith('cup extends') else ('reference_geometry_resolution' if 'resolution mismatch' in err else ('reference_binary_semantics' if 'binary zero-background' in err else 'reference_load_decode_error'))
            refcats[(expert,cat)]+=1
      for pred in row['predictions']:
        statuses[(pred['model'],pred['status'])]+=1
        if 'labels_path' not in pred:
          missing.append({'case_id':case.case_id,'model':pred['model'],'status':pred['status'],'errors':pred['errors']});continue
        target=Path(pred['labels_path']);assert file_sha256(target)==pred['labels_sha256']
        lab=np.array(Image.open(target));assert h.digest(lab.tobytes())==pred['labels_pixel_sha256']
        assert lab.shape==tuple(reversed(row['image_size'])) and np.isin(lab,[0,1,2]).all();checks+=1
        if pred['status']=='ok':continue
        for expert,ref in row['references'].items():
          if ref['status']!='ok':continue
          masks={}
          for structure in ['disc','cup']:
            member=case.mask_member(expert,structure)
            assert h.digest(zf.read(member))==ref['members'][structure]['sha256']
            masks[structure]=np.asarray(_read_member(zf,member).convert('L'))>0
          dice_rows.append({'case_id':case.case_id,'camera':case.camera,'model':pred['model'],'expert':expert,
            'disc_dice':h.dice(lab>=1,masks['disc']),'cup_dice':h.dice(lab==2,masks['cup'])})
  report={'created_utc':h.now(),'scope':'Separate descriptive supplement: Dice on all returned masks including invalid geometry; vCDR and queue unknowns unchanged.',
     'protocol_sha256':file_sha256(h.OUT/'protocol.json'),'supplement_harness_sha256':file_sha256(Path(__file__)),
     'original_harness_models_inference_source_and_artifact_hashes_verified':True,
     'source_changes_during_run':source_changes,
     'source_change_semantic_proof':{'baseline_git_revision':'9cd674e','reader_functions':function_proof,
       'default_strict_scan_metadata_path_fingerprint_matches':True,'camera_counts_match':True,
       'default_strict_scan_optional_incomplete_case_path_not_used':True},
     'source_change_explanation':'Parent reported production Chaksu opt-in incomplete-reader indexing fix while this run already held the original module in memory. Original protocol hashes retained; new default strict scan yields identical 336 case IDs. No data/model/inference/measurement changes.',
     'post_run_default_strict_scan_matches_all_336_original_case_ids':True,'n_original_resolution_masks_verified':checks,
     'n_predictions_without_labels':len(missing),'n_returned_mask_reader_dice_rows':len(dice_rows),
     'uncertainty':protocol['uncertainty'],'reference_failure_categories':[{'expert':e,'category':c,'count':n} for (e,c),n in sorted(refcats.items())],
     'prediction_statuses':[{'model':m,'status':s,'count':n} for (m,s),n in sorted(statuses.items())],
     'all_returned_mask_dice':{},'paired_model_dice_robust_minus_real':{}}
  idx={(r['case_id'],r['model'],r['expert']):r for r in dice_rows}
  for model in h.MODEL_NAMES:
    report['all_returned_mask_dice'][model]={e:{cam:{k:h.summary([r[k] for r in dice_rows if r['model']==model and r['expert']==e and (cam=='all' or r['camera']==cam)]) for k in ['disc_dice','cup_dice']} for cam in ['all','bosch','forus','remidio']} for e in EXPERTS}
  for e in EXPERTS:
    report['paired_model_dice_robust_minus_real'][e]={}
    for cam in ['all','bosch','forus','remidio']:
      common=[r for r in rows if (cam=='all' or r['camera']==cam) and all((r['case_id'],m,e) in idx for m in h.MODEL_NAMES)]
      report['paired_model_dice_robust_minus_real'][e][cam]={k:h.summary([idx[r['case_id'],h.MODEL_NAMES[1],e][k]-idx[r['case_id'],h.MODEL_NAMES[0],e][k] for r in common]) for k in ['disc_dice','cup_dice']}
  h.write('private_all_returned_mask_dice.json',dice_rows);h.write('private_missing_prediction_masks.json',missing)
  h.write('supplement_public_safe.json',report)
  frozen=json.loads((h.OUT/'private_queue_frozen_before_references.json').read_text())['rows']
  rowidx={r['case_id']:r for r in rows}
  technical={'created_utc':h.now(),'posthoc_exploratory':True,
    'addendum_sha256':file_sha256(h.OUT/'technical_event_posthoc_addendum.json'),
    'queue_sha256':file_sha256(h.OUT/'private_queue_frozen_before_references.json'),
    'interpretation':'Technical event complements original vCDR endpoint. All thresholds reported; no optimization or new inference. Unknown only if prediction status ok and reader invalid.',
    'results':{}}
  for subgroup in ['all_336','both_models_ok']:
    selected=[rowidx[r['case_id']] for r in frozen if subgroup=='all_336' or all(p['status']=='ok' for p in rowidx[r['case_id']]['predictions'])]
    technical['results'][subgroup]={'n_images':len(selected),'thresholds':{}}
    for threshold in [.4,.5,.6]:
      byexpert={}
      for e in EXPERTS:
        byexpert[e]={}
        for scope in h.MODEL_NAMES+['either_model']:
          outcomes=[]
          for row in selected:
            flags=[]
            for pred in row['predictions']:
              if scope!='either_model' and pred['model']!=scope:continue
              met=idx.get((row['case_id'],pred['model'],e))
              flags.append(True if pred['status'] in ['error','invalid_geometry'] else (min(met['disc_dice'],met['cup_dice'])<threshold if met is not None else None))
            outcomes.append(True if True in flags else (None if None in flags else False))
          budgets=[]
          for fraction in [.1,.2,.5]:
            budget=h.evaluate_budget(outcomes,review_fraction=fraction);k=budget['cases_reviewed']
            budget['reviewed_unknown']=sum(v is None for v in outcomes[:k]);budget['remaining_unknown']=sum(v is None for v in outcomes[k:])
            budget['reviewed_event_rate_interval']=h.rate([v for v in outcomes[:k] if v is not None]);budget['remaining_event_rate_interval']=h.rate([v for v in outcomes[k:] if v is not None]);budgets.append(budget)
          byexpert[e][scope]=budgets
      technical['results'][subgroup]['thresholds'][str(threshold)]=byexpert
  h.write('technical_event_posthoc_public_safe.json',technical)
  h.log(f'SUPPLEMENT VERIFIED {checks} original-resolution masks; {len(dice_rows)} Dice rows')
if __name__=='__main__':main()
