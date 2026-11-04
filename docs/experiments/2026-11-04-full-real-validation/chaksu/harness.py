"""Private frozen-model Chaksu re-evaluation. Run from repository root."""
import collections, hashlib, json, math, platform, subprocess, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from hyunoptic.chaksu import scan_test_archive, load_test_case, _read_member, EXPERTS
from hyunoptic.seg.bundle import verify_bundle, file_sha256
from hyunoptic.seg.inference import Predictor
from hyunoptic.review.priority import priority
from hyunoptic.review.validation import order_cases, evaluate_budget

OUT = Path(__file__).resolve().parent
ARCHIVE = Path('data/Chaksu_Test.zip')
MODEL_NAMES = ['papila_real_seed43_20261025', 'papila_camera_robust_seed43_20261025']
SEED = 20261104
def now(): return datetime.now(timezone.utc).isoformat()
def write(name, obj):
    p=OUT/name; p.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n', encoding='utf-8')
def log(message):
    message=f'{now()} {message}'
    with (OUT/'progress.log').open('a',encoding='utf-8') as f: f.write(message+'\n')
    print(message,flush=True)
def append(name,obj):
    with (OUT/name).open('a',encoding='utf-8') as f: f.write(json.dumps(obj,allow_nan=False)+'\n')
def digest(b): return hashlib.sha256(b).hexdigest()
def span(mask):
    rows=np.flatnonzero(np.any(mask,axis=1))
    if not len(rows): raise ValueError('empty mask')
    return int(rows[-1]-rows[0]+1)
def vcdr(d,c): return span(c)/span(d)
def dice(a,b):
    den=int(np.count_nonzero(a))+int(np.count_nonzero(b))
    return 2*int(np.count_nonzero(a & b))/den if den else 1.0
def summary(values):
    a=np.array(values,dtype=float); n=len(a)
    if not n:return {'n':0,'mean':None,'image_iid_bootstrap_mean_95_interval':None}
    rng=np.random.default_rng(SEED)
    means=a[rng.integers(0,n,size=(2000,n))].mean(axis=1)
    return {'n':n,'mean':float(a.mean()),'median':float(np.median(a)),
      'min':float(a.min()),'max':float(a.max()),
      'image_iid_bootstrap_mean_95_interval':np.quantile(means,[.025,.975]).tolist()}
def rate(values):
    n=len(values); k=sum(values)
    if not n:return {'n':0,'positive':0,'fraction':None,'image_iid_wilson_95_interval':None}
    p=k/n; z=1.959963984540054; den=1+z*z/n
    mid=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'n':n,'positive':k,'fraction':p,'image_iid_wilson_95_interval':[mid-half,mid+half]}
def summarise(rows):
    out={'n_evaluable':len(rows)}
    for k in ['disc_dice','cup_dice','abs_vcdr_error']:out[k]=summary([r[k] for r in rows])
    out['abs_vcdr_error_gt_0_10']=rate([r['abs_vcdr_error']>.10 for r in rows])
    return out

def main():
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    torch.manual_seed(SEED); np.random.seed(SEED)
    if (OUT/'protocol.json').exists():raise RuntimeError('Refusing overwrite of existing evaluation')
    cases,layout=scan_test_archive(ARCHIVE)
    assert len(cases)==336 and layout['readable_case_counts_by_camera']=={'bosch':41,'forus':31,'remidio':264}
    bundles=[verify_bundle(Path('models')/n) for n in MODEL_NAMES]
    source_files=['src/hyunoptic/chaksu.py','src/hyunoptic/seg/inference.py','src/hyunoptic/seg/preprocess.py',
                  'src/hyunoptic/seg/model.py','src/hyunoptic/measure.py','src/hyunoptic/review/priority.py','src/hyunoptic/review/validation.py']
    protocol={'created_utc_before_inference':now(),'dataset':'Chaksu published Test','n_images':336,
      'n_models':2,'expected_new_prediction_attempts':672,'reference_readers':list(EXPERTS),
      'seed':SEED,'torch_threads':2,'torch_interop_threads':1,'device':'CPU; unchanged production Predictor',
      'inference':'load_test_case(readers=()); no reference bytes read until all 672 attempts and queue saved',
      'reference_policy':'Each expert scored independently; strict original resolution, nonempty binary zero background, cup containment; no repair; failed readers remain unknown.',
      'metrics':'Explicit original-resolution pixel Dice and inclusive vertical spans; event abs vCDR error > 0.10; queue event either model exceeds threshold, unknown if neither known positive and any unknown.',
      'queue':'Actual app priority(), order_cases() on all 336; stable camera/stem input order ties; evaluate_budget() 10%,20%,50%, missing outcomes None.',
      'uncertainty':'2000 image-IID bootstrap means, paired image-IID bootstrap model deltas, Wilson event intervals; descriptive sensitivity only, incomplete patient linkage violates independence; no patient bootstrap or population/clinical guarantee.',
      'data_reuse':'Exploratory rerun: October 2026 model evaluation and candidate QC inspected Chaksu Test; earlier evaluation had only expert1/2 metrics and whole-case reference failures. Same frozen models and same images are reused. No untouched external confirmation, author benchmark replication, or clinical validation claim.',
      'models':[{'name':n,'identity':b.identity,'manifest':b.manifest} for n,b in zip(MODEL_NAMES,bundles)],
      'archive_sha256':file_sha256(ARCHIVE),'layout':layout,
      'source_sha256':{p:file_sha256(Path(p)) for p in source_files},'harness_sha256':file_sha256(Path(__file__)),
      'git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
      'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'platform':platform.platform()}
    write('protocol.json',protocol); log('PROTOCOL FROZEN; starting image-only inference')
    predictors=[Predictor(b) for b in bundles]; rows=[]; t=time.monotonic()
    with zipfile.ZipFile(ARCHIVE) as zf:
      for ordinal,case in enumerate(cases):
        row={'case_id':case.case_id,'camera':case.camera,'ordinal':ordinal,'predictions':[]}
        try:
          image,_=load_test_case(zf,case,readers=())
          row.update(image_size=list(image.size),image_member_sha256=digest(zf.read(case.image_member)),image_rgb_sha256=digest(image.tobytes()))
        except Exception as exc:
          row['image_load_error']=f'{type(exc).__name__}: {exc}'; image=None
        for name,predictor in zip(MODEL_NAMES,predictors):
          pr={'model':name,'status':'error','errors':[]}
          if image is None:pr['errors']=[row['image_load_error']]
          else:
            try:
              pred=predictor.predict(image.copy())
              pr.update(status=pred.status,errors=pred.errors,measurement=pred.measurement,preprocessing=pred.preprocessing)
              if pred.labels is not None:
                folder=OUT/'private_predictions'/name; folder.mkdir(parents=True,exist_ok=True)
                target=folder/f'{ordinal:03d}.png'; Image.fromarray(pred.labels).save(target)
                pr.update(labels_path=str(target),labels_sha256=file_sha256(target),labels_pixel_sha256=digest(pred.labels.tobytes()),labels_shape=list(pred.labels.shape))
                assert pred.labels.shape==(image.height,image.width)
                if pred.measurement is not None:
                  independent=vcdr(pred.labels>=1,pred.labels==2)
                  assert abs(independent-pred.measurement['vertical_cdr'])<1e-12
                  pr['independent_vcdr']=independent
            except Exception as exc:pr.update(status='error',errors=[f'{type(exc).__name__}: {exc}'])
          row['predictions'].append(pr)
        row['priority']=priority(row['predictions']); rows.append(row); append('private_predictions.jsonl',row)
        if (ordinal+1)%10==0:log(f'Inference {ordinal+1}/336 images, {2*(ordinal+1)}/672 attempts, elapsed {time.monotonic()-t:.1f}s')
    ordered=order_cases(rows)
    write('private_queue_frozen_before_references.json',{'created_utc':now(),'rows':ordered,
      'budgets_before_references_all_unknown':[evaluate_budget([None]*336,review_fraction=f) for f in [.1,.2,.5]]})
    write('inference_phase_complete.json',{'created_utc':now(),'attempts':sum(len(r['predictions']) for r in rows),
       'returned_masks':sum('labels_path' in p for r in rows for p in r['predictions']),
       'private_predictions_sha256':file_sha256(OUT/'private_predictions.jsonl'),
       'queue_sha256':file_sha256(OUT/'private_queue_frozen_before_references.json')})
    log('ALL INFERENCE AND QUEUE FROZEN; opening original expert references now')
    metrics=[]; failures=[]; reader_pairs=[]
    with zipfile.ZipFile(ARCHIVE) as zf:
      for i,(case,row) in enumerate(zip(cases,rows)):
        labels=[]
        for p in row['predictions']:
          if 'labels_path' in p:
            assert file_sha256(Path(p['labels_path']))==p['labels_sha256']
            labels.append(np.array(Image.open(p['labels_path'])))
          else:labels.append(None)
        refs={}; row['references']={}
        for expert in EXPERTS:
          ref={'status':'error','members':{},'errors':[]}; masks={}
          for structure in ['disc','cup']:
            member=case.mask_member(expert,structure)
            try:
              payload=zf.read(member); ref['members'][structure]={'sha256':digest(payload),'member':member}
              raw=np.asarray(_read_member(zf,member).convert('L'),dtype=np.uint8)
              levels=np.unique(raw); ref['members'][structure].update(shape=list(raw.shape),levels=levels.tolist())
              if raw.shape!=tuple(reversed(row.get('image_size',[]))):raise ValueError('resolution mismatch')
              if len(levels)>2 or 0 not in levels or raw.max()==0:raise ValueError('not a nonempty binary zero-background mask')
              masks[structure]=raw>0
            except Exception as exc:ref['errors'].append(f'{structure}: {type(exc).__name__}: {exc}')
          if len(masks)==2:
            outside=int(np.count_nonzero(masks['cup'] & ~masks['disc']));ref['cup_outside_disc_pixels']=outside
            if outside:ref['errors'].append(f'cup extends beyond disc ({outside} pixels); no repair')
          if not ref['errors']:
            ref.update(status='ok',vcdr=vcdr(masks['disc'],masks['cup'])); refs[expert]=masks
            for j,(p,lab) in enumerate(zip(row['predictions'],labels)):
              if lab is None or p['status']!='ok':continue
              met={'case_id':case.case_id,'camera':case.camera,'model':MODEL_NAMES[j],'expert':expert,
                'disc_dice':dice(lab>=1,masks['disc']),'cup_dice':dice(lab==2,masks['cup']),
                'reference_vcdr':ref['vcdr'],'predicted_vcdr':vcdr(lab>=1,lab==2)}
              met['abs_vcdr_error']=abs(met['predicted_vcdr']-met['reference_vcdr']); metrics.append(met)
          else:failures.append({'case_id':case.case_id,'camera':case.camera,'expert':expert,**ref})
          row['references'][expert]=ref
        for a in range(5):
          for b in range(a+1,5):
            ea,eb=EXPERTS[a],EXPERTS[b]
            if ea in refs and eb in refs:
              ra,rb=refs[ea],refs[eb];reader_pairs.append({'camera':case.camera,'readers':[ea,eb],
                'disc_dice':dice(ra['disc'],rb['disc']),'cup_dice':dice(ra['cup'],rb['cup']),
                'abs_vcdr_error':abs(row['references'][ea]['vcdr']-row['references'][eb]['vcdr'])})
        append('private_reference_rows.jsonl',row)
        if (i+1)%10==0:log(f'References {i+1}/336; valid model-reader rows {len(metrics)}; reader failures {len(failures)}')
    write('private_metrics.json',metrics);write('private_reference_failures.json',failures)
    write('private_reader_pairs.json',reader_pairs)
    metric_index={(m['case_id'],m['model'],m['expert']):m for m in metrics}
    agg={'created_utc':now(),'protocol_sha256':file_sha256(OUT/'protocol.json'),
      'dataset':'Chaksu Test; reused exploratory analysis','n_images':336,'n_predictions_attempted':672,
      'returned_masks':sum('labels_path' in p for r in rows for p in r['predictions']),
      'prediction_statuses':{n:dict(collections.Counter(r['predictions'][j]['status'] for r in rows)) for j,n in enumerate(MODEL_NAMES)},
      'image_load_failures':sum('image_load_error' in r for r in rows),
      'reference_valid_counts':{e:sum(r['references'][e]['status']=='ok' for r in rows) for e in EXPERTS},
      'reference_failure_counts':dict(collections.Counter(f['expert'] for f in failures)),
      'reference_failure_categories':dict(collections.Counter(err.split(':')[0] if ':' in err else 'cup_containment' for f in failures for err in f['errors'])),
      'queue_priority_groups':dict(collections.Counter(r['priority']['group'] for r in rows)),
      'models':{},'paired_model_comparison_robust_minus_real':{},'queue_evaluation':{},'reader_agreement':{},
      'limitations':[protocol['data_reuse'],protocol['uncertainty'],'Strict reference failures excluded separately per expert; missing outcomes remain unknown.','Five experts are correlated annotations, not five independent datasets.']}
    cameras=['all','bosch','forus','remidio']
    for name in MODEL_NAMES:
      agg['models'][name]={e:{cam:summarise([m for m in metrics if m['model']==name and m['expert']==e and (cam=='all' or m['camera']==cam)]) for cam in cameras} for e in EXPERTS}
    for e in EXPERTS:
      agg['paired_model_comparison_robust_minus_real'][e]={}
      for cam in cameras:
        common=[r for r in rows if (cam=='all' or r['camera']==cam) and all((r['case_id'],n,e) in metric_index for n in MODEL_NAMES)]
        agg['paired_model_comparison_robust_minus_real'][e][cam]={k:summary([metric_index[r['case_id'],MODEL_NAMES[1],e][k]-metric_index[r['case_id'],MODEL_NAMES[0],e][k] for r in common]) for k in ['disc_dice','cup_dice','abs_vcdr_error']}
      agg['queue_evaluation'][e]={}
      for scope in MODEL_NAMES+['either_model']:
        outcomes=[]
        for r in ordered:
          selected=MODEL_NAMES if scope=='either_model' else [scope]
          vals=[metric_index.get((r['case_id'],n,e)) for n in selected]
          flags=[m['abs_vcdr_error']>.1 if m is not None else None for m in vals]
          outcome=True if True in flags else (None if None in flags else False)
          outcomes.append(outcome)
        budgets=[]
        for f in [.1,.2,.5]:
          budget=evaluate_budget(outcomes,review_fraction=f);k=budget['cases_reviewed']
          budget['reviewed_unknown']=sum(v is None for v in outcomes[:k]);budget['remaining_unknown']=sum(v is None for v in outcomes[k:])
          budget['reviewed_event_rate_interval']=rate([v for v in outcomes[:k] if v is not None]);budget['remaining_event_rate_interval']=rate([v for v in outcomes[k:] if v is not None])
          budgets.append(budget)
        agg['queue_evaluation'][e][scope]=budgets
    for a in range(5):
      for b in range(a+1,5):
        pair=[EXPERTS[a],EXPERTS[b]]
        agg['reader_agreement'][f'{a+1}_vs_{b+1}']={cam:summarise([r for r in reader_pairs if r['readers']==pair and (cam=='all' or r['camera']==cam)]) for cam in cameras}
    write('aggregate_public_safe.json',agg)
    write('completion.json',{'completed_utc':now(),'elapsed_seconds':time.monotonic()-t,'aggregate_sha256':file_sha256(OUT/'aggregate_public_safe.json'),
       'scope':'reports/full_validation_20261104/chaksu only; no src/tests/public docs/model modifications'})
    log(f'COMPLETE elapsed {time.monotonic()-t:.1f}s; aggregate written')
if __name__=='__main__': main()
