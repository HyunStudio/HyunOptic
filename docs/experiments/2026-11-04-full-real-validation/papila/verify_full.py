"""Independent saved-artifact audit; no inference, production metrics or queue helpers.

Only existing PAPILA contour loading and PIL polygon rasterization are shared.
Public output contains counts/hashes only; do not publish input data or masks.
"""
from pathlib import Path
import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal, ROUND_CEILING
import numpy as np
from PIL import Image
from hyunoptic.papila import discover_cases, load_contours
from hyunoptic.measure import polygon_mask

ROOT = Path.cwd()
F = ROOT / 'reports/full_validation_20261104/papila'
OUT = ROOT / 'reports/full_validation_20261104/independent'
PAPILA_ROOT = ROOT / 'data/PAPILA'
checks = Counter()
def check(ok, name):
    assert ok, name
    checks[name] += 1
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def same(a,b,name):
    if isinstance(a,dict):
        check(set(a)==set(b),name+' keys')
        for k in a: same(a[k],b[k],name+'.'+k)
    elif isinstance(a,list):
        check(len(a)==len(b),name+' len')
        for x,y in zip(a,b): same(x,y,name)
    elif isinstance(a,(float,int)) and not isinstance(a,bool):
        check(b is not None and abs(a-b) <= 1e-12,name)
    else: check(a==b,name)
def spans(m):
    ys = np.flatnonzero(m.any(axis=1)); xs = np.flatnonzero(m.any(axis=0))
    if len(ys)==0: return None
    return int(ys[-1]-ys[0]+1), int(xs[-1]-xs[0]+1), int(np.count_nonzero(m))
def measurement(d,c):
    ds,cs=spans(d),spans(c)
    if ds is None or cs is None: return None
    dv,dh,da=ds;cv,ch,ca=cs
    warnings=[]
    if np.any(c & ~d): warnings.append('Cup mask extends outside disc; review contour alignment.')
    if cv>dv or ch>dh or ca>da: warnings.append('Cup span/area exceeds disc; derived ratios are not clinically interpretable.')
    return dict(vertical_cdr=cv/dv,horizontal_cdr=ch/dh,area_cdr=ca/da,disc_vertical_px=dv,cup_vertical_px=cv,
                disc_horizontal_px=dh,cup_horizontal_px=ch,disc_area_px=da,cup_area_px=ca,warnings=warnings)
def dice(a,b):
    n=int(np.count_nonzero(a))+int(np.count_nonzero(b))
    return 2*int(np.count_nonzero(a & b))/n if n else 1.0
def average(xs): return float(np.mean(xs)) if len(xs) else None
def bootstrap(vals,ids):
    groups=sorted(set(ids))
    if len(groups)<2:return dict(available=False,n_patients=len(groups))
    grouped=np.array([sum(v for v,p in zip(vals,ids) if p==g)/ids.count(g) for g in groups])
    rng=np.random.default_rng(20261104)
    draws=grouped[rng.integers(0,len(groups),size=(2000,len(groups)))].mean(axis=1)
    return dict(method='equal_patient_weight_cluster_percentile_bootstrap_v1',n_eyes=len(vals),n_patients=len(groups),
                patient_weighted_mean=float(grouped.mean()),lower_95_percentile=float(np.quantile(draws,.025)),
                upper_95_percentile=float(np.quantile(draws,.975)),bootstrap_draws=2000,seed=20261104,
                interpretation='Dataset-level patient-weighted mean interval; not individual-patient diagnostic uncertainty.')
def budget(events,f):
    n=len(events);k=int((Decimal(str(f))*n).to_integral_value(rounding=ROUND_CEILING))
    r=[x for x in events[:k] if x is not None];u=[x for x in events[k:] if x is not None]
    total=sum(x is True for x in events);det=sum(r)
    return dict(n_cases=n,n_outcome_available=len(r)+len(u),n_outcome_missing=n-len(r)-len(u),review_fraction=f,
                cases_reviewed=k,reviewed_outcome_available=len(r),remaining_outcome_available=len(u),n_positive=total,
                detected=det,missed=total-det,precision=det/len(r) if r else None,recall=det/total if total else None,
                remaining_error_fraction=sum(u)/len(u) if u else None,random_expected_detected=k*total/n,
                random_expected_recall=k/n if total else None)

def main():
    protocol=read(F/'protocol.json');summary=read(F/'summary.json');rows=read(F/'private_scored_rows.json')
    predictions=read(F/'private_predictions.json');queues=read(F/'private_priorities.json')
    check(summary['protocol_sha256']==sha(F/'protocol.json'),'protocol hash')
    for p,h in protocol['source_sha256'].items():check(sha(ROOT/p.replace('\\','/'))==h,'frozen source hash')
    selection=read(F/'private_selection.json')
    cases=sorted([c for c in discover_cases(PAPILA_ROOT) if c.image_id in selection],key=lambda c:c.image_id)
    check([c.image_id for c in cases]==selection,'selection order')
    check(len(cases)==98 and len(set(c.patient_id for c in cases))==49,'cohort counts')
    for model in ('papila_real_seed43_20261025','papila_camera_robust_seed43_20261025'):
        envelope=read(ROOT/'models'/model/'split_manifest.json');split=envelope['manifest']
        check(hashlib.sha256(json.dumps(split,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()==envelope['sha256'],'split body hash')
        check(set(selection)==set(split['splits']['holdout']),'full preserved holdout')
    conditions=[c['name'] for c in protocol['conditions']]
    expected={(i,c,m) for i in range(98) for c in conditions for m in range(2)}
    check(len(rows)==2548 and len(conditions)==13,'prediction count')
    check(len(predictions)==2548,'unscored prediction count')
    same(summary['n_predictions'],2548,'summary prediction count')
    same(summary['n_original_images'],98,'summary image count')
    same(summary['n_patients'],49,'summary patient count')
    same(summary['n_conditions'],13,'summary condition count')
    check({(r['case_index'],r['condition'],r['model_index']) for r in rows}==expected,'full Cartesian keys')
    check(len(queues)==1274 and len({(q['ordinal'],q['condition']) for q in queues})==1274,'priority Cartesian keys')
    for a,b in zip(rows,predictions):same({k:v for k,v in a.items() if k!='metrics'},b,'prediction/scored artifact')
    check(set(p.name for p in (F/'private_predictions').iterdir())=={r['labels_file'] for r in rows if r['labels_file']},'no extra masks')
    actual={};actual_queues={};ref_warn={};ref_available=Counter();status=Counter()
    for i,case in enumerate(cases):
        with Image.open(case.image_path) as im:size=im.size
        refs={}
        for reader in ('exp1','exp2'):
            try:
                d,c=load_contours(case,reader);d,c=polygon_mask(d,size),polygon_mask(c,size)
                m=measurement(d,c)
                if m is None:raise ValueError('Empty reference')
                refs[reader]=(d,c,m);ref_available[reader]+=1;ref_warn[i,reader]=bool(m['warnings'])
            except (ValueError,OSError):refs[reader]=None;ref_warn[i,reader]=False
        for condition in conditions:
            pair=[]
            for mi in range(2):
                r=next(r for r in rows if r['case_index']==i and r['condition']==condition and r['model_index']==mi)
                status[r['status']]+=1;metrics={};labels=None
                if r['labels_file']:
                    p=F/'private_predictions'/r['labels_file'];check(sha(p)==r['labels_sha256'],'mask SHA256')
                    with Image.open(p) as im:labels=np.array(im)
                    check(labels.dtype==np.uint8 and labels.shape==(size[1],size[0]),'original geometry/dtype')
                    check(set(np.unique(labels)).issubset({0,1,2}),'label classes')
                    d,c=labels>=1,labels==2;m=measurement(d,c)
                    same(m,r['measurement'],'prediction measurement')
                    check(r['status']==('ok' if m is not None else 'invalid_geometry'),'geometry status')
                    for reader,ref in refs.items():
                        if ref is not None:
                            rd,rc,rm=ref
                            metrics[reader]=dict(disc_dice=dice(d,rd),cup_dice=dice(c,rc),
                                abs_vcdr_error=abs(m['vertical_cdr']-rm['vertical_cdr']) if m is not None else None)
                else:check(r['status']=='error' and r['measurement'] is None,'error status')
                same(metrics,r['metrics'],'per-prediction metrics')
                actual[i,condition,mi]=metrics;pair.append((r,labels))
            sts=[p[0]['status'] for p in pair]
            pri=dict(group='pending',score=None,reasons=[],vcdr_delta=None)
            if 'error' in sts:pri.update(group='error',reasons=['prediction_error'])
            elif 'invalid_geometry' in sts:pri.update(group='invalid_geometry',reasons=['invalid_geometry'])
            else:
                a,b=pair[0][1],pair[1][1]
                pri.update(group='disagreement',score=max(1-dice(a>=1,b>=1),1-dice(a==2,b==2)),
                    reasons=['model_mask_disagreement'],vcdr_delta=abs(pair[0][0]['measurement']['vertical_cdr']-pair[1][0]['measurement']['vertical_cdr']))
            saved=next(q['priority'] for q in queues if q['ordinal']==i and q['condition']==condition)
            same(pri,saved,'priority artifact');actual_queues[i,condition]=pri
        if (i+1)%10==0:print(json.dumps(dict(verified_images=i+1)),flush=True)
    same(dict(status),summary['prediction_status_counts'],'status aggregate')
    for reader in ('exp1','exp2'):same(dict(available=ref_available[reader],failed=98-ref_available[reader]),summary['references'][reader],'reference count')
    check(len(summary['aggregates'])==52,'aggregate count')
    for ag in summary['aggregates']:
        cond,mi,reader=ag['condition'],ag['model_index'],ag['reader']
        same(ag['n_images'],98,'aggregate denominator');same(ag['n_patients'],49,'aggregate patient denominator')
        same(ag['prediction_status_counts'],dict(Counter(r['status'] for r in rows if r['condition']==cond and r['model_index']==mi)),'group statuses')
        same(ag['reference_failures'],98-ref_available[reader],'group reference failure')
        same(ag['reference_warning_cases'],sum(ref_warn[i,reader] for i in range(98)),'group reference warnings')
        for field in ('disc_dice','cup_dice','abs_vcdr_error'):
            vals=[];ids=[];pairs=[];pids=[]
            for i,c in enumerate(cases):
                v=actual[i,cond,mi].get(reader,{}).get(field);orig=actual[i,'original',mi].get(reader,{}).get(field)
                if v is not None:vals.append(v);ids.append(c.patient_id)
                if v is not None and orig is not None:pairs.append((orig,v));pids.append(c.patient_id)
            same(dict(n_images=len(vals),image_weighted_mean=average(vals),equal_patient_bootstrap=bootstrap(vals,ids)),ag['metrics'][field],'aggregate metrics')
            changes=[b-a for a,b in pairs]
            same(dict(n_common_images=len(pairs),original_image_mean=average([a for a,b in pairs]),condition_image_mean=average([b for a,b in pairs]),
                 image_mean_change=average(changes),equal_patient_change_bootstrap=bootstrap(changes,pids)),ag['paired_with_original'][field],'paired metrics')
    check(len(summary['review_budget_results'])==78,'queue result count')
    groups={'error':0,'invalid_geometry':1,'disagreement':2,'pending':3}
    lookup={(r['case_index'],r['condition'],r['model_index']):r for r in rows}
    for result in summary['review_budget_results']:
        cond,reader,t=result['condition'],result['reader'],result['error_definition_threshold']
        def key(i):
            p=actual_queues[i,cond];return groups[p['group']],-p['score'] if p['group']=='disagreement' else 0,i
        events=[]
        for i in sorted(range(98),key=key):
            r=lookup[i,cond,0];m=actual[i,cond,0].get(reader)
            events.append(True if r['status']!='ok' else min(m['disc_dice'],m['cup_dice'])<t if m else None)
        same(sum(x is None for x in events),result['n_unknown_reference_outcomes'],'unknown outcomes')
        same([budget(events,f) for f in (.1,.2,.5)],result['budgets'],'queue budget arithmetic')
    report=dict(schema='hyunoptic-independent-full-artifact-verification/v1',passed=True,protocol_sha256=sha(F/'protocol.json'),verifier_sha256=sha(Path(__file__)),
        n_original_images=98,n_patients=49,n_conditions=13,n_predictions=2548,n_readers=2,n_model_condition_reader_aggregates=52,
        n_queue_definitions=78,n_queue_budget_results=234,n_bootstrap_comparisons=312,tolerance=1e-12,
        shared_code='PAPILA contour loading and polygon rasterization only; no production measurement, Dice, bootstrap, priority or budget helper',
        checks=dict(checks),limitations=protocol['limitations'])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=F)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--papila-root',type=Path,default=PAPILA_ROOT)
    args=parser.parse_args();F=args.input;OUT=args.output;PAPILA_ROOT=args.papila_root
    OUT.mkdir(parents=True,exist_ok=True)
    main()
