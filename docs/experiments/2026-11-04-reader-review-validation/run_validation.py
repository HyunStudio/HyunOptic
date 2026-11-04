"""Exploratory full PAPILA holdout reader/review study. Run from repository root.

Outputs include private image copies and masks; publish reviewed aggregates only.
This is an Oxford-literature-informed evaluation, not reproduction of its algorithm.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import time

import numpy as np
from PIL import Image

from hyunoptic.evaluation import patient_cluster_bootstrap_mean
from hyunoptic.measure import dice, measure_masks, polygon_mask
from hyunoptic.papila import load_image, load_contours
from hyunoptic.review.store import ReviewStore
from hyunoptic.review.validation import order_cases, evaluate_budget
from hyunoptic.review.export import export_session, verify_export
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.data import verify_split_manifest, cases_for
from hyunoptic.seg.inference import Predictor
from hyunoptic.source_fingerprint import papila_content_sha256


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False),encoding='utf-8')


def mean(values):
    return float(np.mean(values)) if values else None


def interval(pairs):
    if len({p[1] for p in pairs}) < 2:
        return {'available':False,'n_patients':len({p[1] for p in pairs})}
    return patient_cluster_bootstrap_mean([p[0] for p in pairs],[p[1] for p in pairs],draws=2000,seed=20261104)


def summarize(rows, models):
    result={'n_images':len(rows),'n_patients':len({r['patient_id'] for r in rows}),
            'averaging':'Outer means are image-weighted; bootstrap intervals include their separate equal-patient weighted point estimate.',
            'models':[], 'reader_context':{}, 'review_budgets':{}, 'paired_models':{}}
    for reader in ['exp1','exp2']:
        refs=[r['references'][reader] for r in rows]
        result['reader_context'][reader]={'n_available':sum(v['available'] for v in refs),
                'n_failed':sum(not v['available'] for v in refs),
                'n_with_geometry_warnings':sum(bool(v.get('warnings')) for v in refs)}
    for field in ['disc_dice','cup_dice','abs_vcdr_difference']:
        values=[(r['reader_agreement'][field],r['patient_id']) for r in rows if r.get('reader_agreement')]
        result['reader_context'][field]={'n_images':len(values),'mean':mean([v[0] for v in values]),
                                      'patient_cluster_interval':interval(values)}
    for mi,model in enumerate(models):
        item={'run_id':model['run_id'],'identity':model['identity'],'readers':{}}
        predictions=[r['predictions'][mi] for r in rows]
        item['prediction_status_counts']={s:sum(p['status']==s for p in predictions)
                                         for s in ['ok','invalid_geometry','error']}
        for reader in ['exp1','exp2']:
            scores=[(p['metrics'][reader],r['patient_id']) for p,r in zip(predictions,rows) if reader in p['metrics']]
            metrics={}
            for field in ['disc_dice','cup_dice','abs_vcdr_error']:
                values=[(v[field],pid) for v,pid in scores if v.get(field) is not None]
                metrics[field]={'n_images':len(values),'mean':mean([v[0] for v in values]),
                                'patient_cluster_interval':interval(values)}
            item['readers'][reader]=metrics
        paired=[]
        for p,r in zip(predictions,rows):
            if all(e in p['metrics'] for e in ['exp1','exp2']):
                paired.append((p['metrics']['exp1'],p['metrics']['exp2'],r['patient_id']))
        item['paired_reader_change_exp2_minus_exp1']={}
        for field in ['disc_dice','cup_dice','abs_vcdr_error']:
            diffs=[(b[field]-a[field],pid) for a,b,pid in paired if a.get(field) is not None and b.get(field) is not None]
            item['paired_reader_change_exp2_minus_exp1'][field]={'n_images':len(diffs),'mean':mean([v[0] for v in diffs]),
                                                              'patient_cluster_interval':interval(diffs)}
        result['models'].append(item)
    # The priority rows contain no reference information. Only now attach outcomes.
    lookup={r['ordinal']:r for r in rows}
    order=order_cases([{'ordinal':r['ordinal'],'priority':r['priority']} for r in rows])
    ordered=[lookup[r['ordinal']] for r in order]
    for reader in ['exp1','exp2']:
        result['review_budgets'][reader]={}
        for threshold in [.4,.5,.6]:
            def outcome(row):
                p=row['predictions'][0]
                if p['status']!='ok': return True
                metrics=p['metrics'].get(reader)
                return None if metrics is None else min(metrics['disc_dice'],metrics['cup_dice'])<threshold
            events=[outcome(r) for r in ordered]
            both_ok=[r for r in ordered if all(p['status']=='ok' for p in r['predictions'])]
            # Secondary comparison removes known failure-first cases from both policies.
            groups={ 'full_queue':[outcome(r) for r in ordered],
                    'both_models_geometry_ok':[outcome(r) for r in both_ok]}
            entry={}
            for label,values in groups.items():
                if not values:
                    entry[label]={'n_cases':0};continue
                entry[label]=[evaluate_budget(values,review_fraction=f) for f in [0,.1,.2,.5,1]]
            entry['low_disagreement_large_error']={
                'n_cases':sum(bool(r['priority']['group']=='disagreement' and r['priority']['score']<=.1) for r in ordered),
                'n_positive':sum(bool(outcome(r) is True and r['priority']['group']=='disagreement' and r['priority']['score']<=.1) for r in ordered)}
            result['review_budgets'][reader][str(threshold)]=entry
    for reader in ['exp1','exp2']:
        comparisons={}
        for field in ['disc_dice','cup_dice','abs_vcdr_error']:
            common=[]
            for r in rows:
                a,b=[p['metrics'].get(reader,{}) for p in r['predictions']]
                if a.get(field) is not None and b.get(field) is not None:
                    common.append((b[field]-a[field],r['patient_id']))
            comparisons[field]={'n_common_images':len(common),'mean_photo_minus_baseline':mean([x[0] for x in common]),
                                'patient_cluster_interval':interval(common)}
        result['paired_models'][reader]=comparisons
    for field in ['disc_dice','cup_dice']:
        flips=0;available=0
        for r in rows:
            ps=r['predictions']
            if all(reader in p['metrics'] for p in ps for reader in ['exp1','exp2']):
                available+=1
                deltas=[ps[1]['metrics'][e][field]-ps[0]['metrics'][e][field] for e in ['exp1','exp2']]
                flips+=int(deltas[0]*deltas[1]<-1e-12)
        result[f'{field}_per_image_model_preference_flips_by_reader']={'n_available':available,'n_flips':flips}
    return result


def summarize_existing(output):
    """Recover aggregate writing from verified saved evidence, without new inference."""
    if (output/'summary.json').exists():raise FileExistsError('Summary already exists')
    protocol_bytes=(output/'protocol.json').read_bytes()
    protocol=json.loads(protocol_bytes)
    rows=json.loads((output/'private_rows.json').read_text(encoding='utf-8'))
    store=ReviewStore(output/'private_review')
    sessions=store.sessions()
    if len(sessions)!=1:raise ValueError('Need one unambiguous saved session')
    saved=store.cases(sessions[0]['id'])
    if len(saved)!=98 or len(rows)!=98 or any(r.get('integrity_error') or r['status']!='complete' for r in saved):
        raise ValueError('Incomplete or changed saved evidence')
    if [m['identity'] for m in sessions[0]['models']]!=[m['identity'] for m in protocol['models']]:
        raise ValueError('Saved model identities differ from frozen protocol')
    priorities={r['ordinal']:r['priority'] for r in saved}
    for row in rows:
        current=priorities[row['ordinal']]
        if current!=row['priority']:raise ValueError('Recomputed priority differs from saved scoring rows')
    result=summarize(rows,protocol['models'])
    timing_path=output/'execution.json'
    if timing_path.exists():timing=json.loads(timing_path.read_text(encoding='utf-8'))
    else:
        log=output.with_suffix('.log').read_text(encoding='utf-8')
        match=re.search(r'Predicted 98/98; ([0-9.]+)s',log)
        timing={'inference_seconds_logged_approx':float(match.group(1)) if match else None}
    result.update(protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),
                  n_model_predictions=sum(len(r['predictions']) for r in saved),
                  export_verified=verify_export(output/'private-evidence.zip')['valid'],
                  **timing,
                  recovery='Initial aggregate write failed on NumPy int64; recomputed from preserved rows and reverified artifacts. No new inference.',
                  limitations=['Previously evaluated holdout; exploratory reuse,not independent confirmation.',
                    'Image review units and patient-cluster intervals answer different questions.',
                    'Reader annotations are references,not disease truth.',
                    'Disagreement is not calibrated uncertainty or observed review-time benefit.'])
    write(output/'summary.json',result)
    print('Recovered summary from verified saved predictions; no new inference.',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--papila-root',type=Path,default=Path('data/PAPILA'))
    parser.add_argument('--baseline',type=Path,default=Path('models/papila_real_seed43_20261025'))
    parser.add_argument('--comparison',type=Path,default=Path('models/papila_camera_robust_seed43_20261025'))
    parser.add_argument('--summarize-existing',action='store_true',help='Recover aggregates from saved evidence only')
    args=parser.parse_args()
    if args.summarize_existing:return summarize_existing(args.output)
    args.output.mkdir(parents=True,exist_ok=False)
    import torch
    torch.set_num_threads(4)
    bundles=[verify_bundle(p) for p in [args.baseline,args.comparison]]
    splits=[verify_split_manifest(json.loads((b.folder/'split_manifest.json').read_text(encoding='utf-8'))) for b in bundles]
    if splits[0]!=splits[1]:raise ValueError('Models must share the identical frozen split')
    print('Verifying full PAPILA source bytes before protocol freeze...',flush=True)
    content=papila_content_sha256(args.papila_root)
    if any(b.manifest['training']['source_content_sha256']!=content for b in bundles):
        raise ValueError('PAPILA contents do not match trained bundle provenance')
    selected=sorted(cases_for(args.papila_root,splits[0],'holdout'),key=lambda c:c.image_id)
    if len(selected)!=98 or len({c.patient_id for c in selected})!=49:
        raise ValueError('Expected complete previously evaluated holdout: 98 images,49 patients')
    models=[dict(folder=str(b.folder.resolve()),identity=b.identity,run_id=b.run_id,
                 weights_sha256=b.weights_sha256,data_status={'synthetic':b.synthetic,'partial':b.partial}) for b in bundles]
    commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    protocol=dict(schema='hyunoptic.reader-review-validation/v1',date='2026-11-04',base_commit=commit,
        exploratory_reuse=True,no_training=True,independent_confirmation=False,
        dataset='PAPILA frozen holdout',n_images=98,n_patients=49,source_content_sha256=content,
        split_sha256=bundles[0].manifest['training']['split_manifest_sha256'],
        models=[{k:v for k,v in m.items() if k!='folder'} for m in models],
        references=['exp1 training reader','exp2 sensitivity reader'],
        prediction='CPU image-only, original resolution, no transforms; torch threads=4',
        reading_order='Save all 196 predictions before reading expert contours',
        research_event='baseline prediction failure OR min(disc Dice,cup Dice)<0.5 against specified reader',
        threshold_sensitivity=[.4,.6],review_fractions=[0,.1,.2,.5,1],budget='ceil(fraction*all cases)',
        queue='execution error,invalid geometry,descending max(1-discDice,1-cupDice) between models; input ordinal ties',
        random='exact uniform fixed-size random selection expected count = k*n_positive/n_all',
        secondary='Both-model-geometry-ok subset; same priority ordering, budget recalculated on subset',
        missing_reference='unavailable outcome, never negative; explicitly counted, budget includes it',
        intervals='2000 patient-cluster bootstrap draws, seed 20261104; equal patient weighting',
        intended_success='descriptive only; no tuned threshold, superiority or generalization gate',
        sources=[{'title':'The hidden value of uncertainty in medical segmentation',
                  'url':'https://doi.org/10.3389/fimag.2026.1965816','use':'inspiration for reader sensitivity,not algorithm reproduction'},
                 {'title':'TRIPOD+AI','url':'https://doi.org/10.1136/bmj-2023-078378','use':'applicable transparency principles,not full diagnostic-model checklist certification'},
                 {'title':'DECIDE-AI','url':'https://doi.org/10.1136/bmj-2022-070904','use':'separating offline checks from future human/clinical evaluation'},
                 {'title':'NASSS-CAT','url':'https://www.phc.ox.ac.uk/research/groups-and-centres/interdisciplinary-research-in-health-sciences/enasss-cat','use':'implementation limitations,not computational model testing'}])
    write(args.output/'protocol.json',protocol)
    protocol_hash=hashlib.sha256((args.output/'protocol.json').read_bytes()).hexdigest()
    write(args.output/'private_selection.json',[c.image_id for c in selected])
    print(f'Frozen protocol {protocol_hash}; 98 images / 49 patients',flush=True)
    store=ReviewStore(args.output/'private_review')
    sid=store.create_session([(f'input-{i:03}.jpg',c.image_path.read_bytes()) for i,c in enumerate(selected)],models,
                             software_commit=commit)
    initial=store.cases(sid)
    predictors=[Predictor(b) for b in bundles]
    start=time.perf_counter()
    for i,(row,case) in enumerate(zip(initial,selected),1):
        token=store.claim(row['id'])
        image=load_image(case)
        errors=[]
        for model,predictor in zip(models,predictors):
            prediction=predictor.predict(image.copy())
            record={k:getattr(prediction,k) for k in ['status','measurement','errors','preprocessing','run_id','weights_sha256']}
            store.record_prediction(row['id'],model['identity'],record,prediction.labels,claim_token=token)
            if prediction.status=='error':errors.append('prediction_error')
        store.finish(row['id'],error=';'.join(errors) or None,claim_token=token)
        if i%10==0 or i==len(selected): print(f'Predicted {i}/98; {time.perf_counter()-start:.1f}s',flush=True)
    elapsed=time.perf_counter()-start
    write(args.output/'execution.json',{'inference_seconds':round(elapsed,2)})
    # Reading source input/mask integrity and priorities precedes all reference scoring.
    predictions=store.cases(sid)
    if any(r.get('integrity_error',False) for r in predictions):raise ValueError('Stored evidence failed integrity verification')
    rows=[]
    for row,case in zip(predictions,selected):
        item={'ordinal':row['ordinal'],'patient_id':case.patient_id,'image_id':case.image_id,
              'priority':row['priority'],'references':{},'predictions':[]}
        references={}
        image=load_image(case)
        for reader in ['exp1','exp2']:
            try:
                d,c=load_contours(case,reader)
                masks=polygon_mask(d,image.size),polygon_mask(c,image.size)
                measured=measure_masks(*masks).to_dict()
                references[reader]=(masks,measured)
                item['references'][reader]={'available':True,'warnings':measured['warnings']}
            except (OSError,ValueError) as exc:
                item['references'][reader]={'available':False,'error':str(exc)}
        if len(references)==2:
            a,b=[references[e] for e in ['exp1','exp2']]
            item['reader_agreement']={'disc_dice':dice(a[0][0],b[0][0]),'cup_dice':dice(a[0][1],b[0][1]),
                                      'abs_vcdr_difference':abs(a[1]['vertical_cdr']-b[1]['vertical_cdr'])}
        by_id={p['model_identity']:p for p in row['predictions']}
        for model in models:
            pred=by_id[model['identity']]
            p={'status':pred['status'],'metrics':{}}
            if pred.get('labels_path'):
                data=Path(pred['labels_path']).read_bytes()
                if hashlib.sha256(data).hexdigest()!=pred['labels_sha256']:
                    raise ValueError('Saved labels changed during reference scoring')
                with Image.open(io.BytesIO(data)) as f:labels=np.asarray(f)
                for reader,(masks,measured) in references.items():
                    p['metrics'][reader]={'disc_dice':dice(labels>=1,masks[0]),'cup_dice':dice(labels==2,masks[1]),
                        'abs_vcdr_error':abs(pred['measurement']['vertical_cdr']-measured['vertical_cdr']) if pred['measurement'] else None}
            item['predictions'].append(p)
        rows.append(item)
    write(args.output/'private_rows.json',rows)
    result=summarize(rows,models)
    result.update(protocol_sha256=protocol_hash,inference_seconds=round(elapsed,2),n_model_predictions=196,
                  export_verified=verify_export(export_session(store,sid,args.output/'private-evidence.zip'))['valid'],
                  limitations=['Previously evaluated holdout; exploratory reuse,not independent validation.',
                  'Both eyes are clustered; review budget unit is an image,not a patient.',
                  'Reader differences do not identify which expert is correct.',
                  'Model disagreement is not calibrated uncertainty; errors may be shared.',
                  'Offline error detection is not observed time saving or clinical utility.'])
    write(args.output/'summary.json',result)
    print('Finished: summary.json; original images,masks,case rows remain private',flush=True)


if __name__=='__main__':main()
