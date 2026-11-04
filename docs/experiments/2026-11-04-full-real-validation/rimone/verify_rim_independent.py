"""Independent RIM saved-artifact, reference coordinate and queue arithmetic audit.

No inference; no production metric, priority or budget implementation imported.
No raw images, coordinates, file members or subject identifiers in output.
"""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import zipfile
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, distance_transform_edt
import verify_full as independent

def stat(xs):
    a=np.array(xs,dtype=float)
    if not len(a):return dict(n=0,mean=None)
    draws=np.random.default_rng(20261104).choice(a,size=(2000,len(a)),replace=True).mean(axis=1)
    return dict(n=len(a),mean=float(a.mean()),sd=float(a.std(ddof=1)) if len(a)>1 else 0.,median=float(np.median(a)),
        min=float(a.min()),max=float(a.max()),image_bootstrap_95ci_mean=[float(x) for x in np.quantile(draws,[.025,.975])])
def main(base,data,out):
    read=independent.read;sha=independent.sha;same=independent.same;check=independent.check
    supp=base/'supplemental_verification';proto=read(supp/'protocol.json');firstproto=read(base/'protocol.json')
    manifest=read(base/'input_manifest.json');summary=read(supp/'aggregate.json');firstaggregate=read(base/'aggregate.json')
    names=list(proto['models']);assert len(names)==2 and len(manifest)==174
    same(proto['models'],firstproto['models'],'same frozen model identities')
    check(len({r['source_image_id'] for r in manifest})==174 and len({r['image_sha256'] for r in manifest})==174,'unique selected image files and payloads')
    check(all(r['reference_status']=='ok' for r in manifest),'all references available')
    same(sha(base/'protocol.json'),proto['first_protocol_sha256'],'first protocol hash')
    same(sha(base/'aggregate.json'),proto['first_aggregate_sha256'],'first aggregate hash')
    same(sha(base/'input_manifest.json'),proto['manifest_sha256'],'manifest hash')
    for p,h in proto['source_sha256'].items():same(sha(Path(p.replace('\\','/'))),h,'source freeze')
    for p,h in firstproto['source_sha256'].items():same(sha(Path(p.replace('\\','/'))),h,'first source freeze')
    for name,meta in proto['archives'].items():same(sha(data/(name+'.zip')),meta['sha256'],'archive hash')
    complete=read(supp/'predictions_complete.json');queues=read(supp/'priorities_before_gt.json');start=read(supp/'scoring_started.json')
    same(sha(supp/'priorities_before_gt.json'),start['priorities_sha256'],'priority frozen hash')
    check(proto['created_utc']<read(supp/'inference_started.json')['started_utc']<complete['completed_utc']<=queues['frozen_utc']<=start['started_utc'],'phase chronology')
    same(sha(supp/'protocol.json'),summary['protocol_sha256'],'supplement protocol hash')
    meta={n:read(supp/n/'predictions.json') for n in names};scores={n:read(supp/(n+'_independent_scores.json')) for n in names}
    first={n:[json.loads(x) for x in (base/(n+'_individual.jsonl')).read_text().splitlines()] for n in names}
    for n in names:
        check(len(meta[n])==len(scores[n])==len(first[n])==174,'model record count')
        same(sha(supp/n/'predictions.json'),complete['metadata_sha256'][n],'complete metadata hash')
        check(len(list((supp/n).glob('*_labels.png')))==174,'mask file count')
    computed={n:[] for n in names};priorities=[];coordinate=Counter();distances=[];first_diffs=Counter();exact_metric_diffs=0
    with zipfile.ZipFile(data/'segmentations.zip') as z,zipfile.ZipFile(data/'images.zip') as images:
        selected=sorted(n for n in images.namelist() if '/partitioned_by_hospital/test_set/' in n and n.endswith('.png'))
        same(selected,[r['image_member'] for r in manifest],'full official hospital test selection')
        for k,row in enumerate(manifest):
            with Image.open(io.BytesIO(images.read(row['image_member']))) as image:size=image.size
            same([row['width'],row['height']],list(size),'supplied image dimensions')
            check(size[0]==size[1],'supplied square ROI')
            same(independent.hashlib.sha256(images.read(row['image_member'])).hexdigest(),row['image_sha256'],'source image hash')
            refs={}
            for part in ('disc','cup'):
                raw=z.read(row[part+'_member']);same(independent.hashlib.sha256(raw).hexdigest(),row[part+'_sha256'],'reference PNG hash')
                with Image.open(io.BytesIO(raw)) as im:a=np.array(im)
                check(a.shape==(size[1],size[0]) and set(np.unique(a))=={0,255},'reference shape and polarity levels')
                refs[part]=a==255
                lines=z.read(row[part+'_member'].replace('.png','.txt')).decode().splitlines()
                xy=np.array([(int(lines[i])-1,int(lines[i+1])-1) for i in range(3,35,2)])
                center=(int(lines[1])-1,int(lines[2])-1)
                check((xy>=0).all() and (xy[:,0]<size[0]).all() and (xy[:,1]<size[1]).all(),'TXT coordinate bounds')
                coordinate['png_txt_pairs']+=1;coordinate['centers_on_255_foreground']+=bool(a[center[1],center[0]]==255)
                coordinate['four_corners_all_background']+=bool(np.all(a[[0,0,-1,-1],[0,-1,0,-1]]==0))
                boundary=refs[part]&~binary_erosion(refs[part]);dist=distance_transform_edt(~boundary)[xy[:,1],xy[:,0]]
                distances.extend(float(v) for v in dist);coordinate['contour_points_checked']+=len(xy)
            rm=independent.measurement(refs['disc'],refs['cup']);same(rm,row['reference_measurement'],'reference geometry')
            labels={}
            for n in names:
                rec=meta[n][k];saved=scores[n][k];old=first[n][k]
                same(rec['source_image_id'],row['source_image_id'],'prediction source association')
                same(saved['source_image_id'],row['source_image_id'],'supplement score source association')
                same(old['source_image_id'],row['source_image_id'],'first score source association')
                same(rec['ordinal'],k,'prediction ordinal');check(rec['saved_utc']<=complete['completed_utc'],'mask saved before completion')
                path=Path(rec['labels_path']);same(sha(path),rec['labels_sha256'],'prediction PNG hash')
                with Image.open(path) as im:a=np.array(im)
                check(a.shape==(size[1],size[0]) and a.dtype==np.uint8 and set(np.unique(a))<={0,1,2},'prediction geometry dtype classes')
                labels[n]=a;d,c=a>0,a==2;m=independent.measurement(d,c)
                same(m,rec['measurement'],'prediction measurement')
                same(rec['status'],'ok' if m is not None else 'invalid_geometry','prediction status from raster')
                calc=dict(disc_dice=independent.dice(d,refs['disc']),cup_dice=independent.dice(c,refs['cup']))
                if m is not None:calc['vcdr_abs_error']=abs(m['vertical_cdr']-rm['vertical_cdr'])
                for f,v in calc.items():same(v,saved[f],'saved metric arithmetic')
                check(('vcdr_abs_error' in calc)==('vcdr_abs_error' in saved),'vCDR metric availability')
                computed[n].append(calc)
                for f in ['prediction_status','prediction_errors','reference_status','disc_dice','cup_dice','vcdr_abs_error']:
                    a,b=old.get(f),saved.get(f)
                    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                        first_diffs[f]+=abs(a-b)>1e-12;exact_metric_diffs+=a!=b
                    else:first_diffs[f]+=a!=b
            sts=[meta[n][k]['status'] for n in names];pri=dict(group='pending',score=None,reasons=[],vcdr_delta=None)
            if 'error' in sts:pri.update(group='error',reasons=['prediction_error'])
            elif 'invalid_geometry' in sts:pri.update(group='invalid_geometry',reasons=['invalid_geometry'])
            else:
                a,b=(labels[n] for n in names)
                pri.update(group='disagreement',score=max(1-independent.dice(a>0,b>0),1-independent.dice(a==2,b==2)),
                    reasons=['model_mask_disagreement'],vcdr_delta=abs(meta[names[0]][k]['measurement']['vertical_cdr']-meta[names[1]][k]['measurement']['vertical_cdr']))
            same(pri,queues['rows'][k]['priority'],'image-only priority arithmetic');priorities.append(pri)
    for mi,n in enumerate(names):
        agg=firstaggregate['models'][mi];suppagg=next(x for x in summary['models'] if x['model']==n)
        counts=dict(Counter(r['status'] for r in meta[n]));same(counts,agg['prediction_status_counts'],'first status count');same(counts,suppagg['status_counts'],'supplement status count')
        for f in ('disc_dice','cup_dice','vcdr_abs_error'):
            vals=[r[f] for r in computed[n] if f in r];same(stat(vals),agg[f],'first aggregate full statistics and bootstrap')
            target=f+'_mean' if f!='vcdr_abs_error' else 'vcdr_mae';same(float(np.mean(vals)),suppagg[target],'supplement mean')
        same(sum('vcdr_abs_error' in r for r in computed[n]),suppagg['vcdr_measurable'],'vCDR coverage')
        for group,groupagg in agg['by_group'].items():
            vals=[computed[n][i] for i,r in enumerate(manifest) if r['group']==group]
            same(len(vals),groupagg['n_images'],'group denominator')
            for f in ('disc_dice','cup_dice','vcdr_abs_error'):same(stat([r[f] for r in vals if f in r]),groupagg[f],'group aggregate statistics and bootstrap')
            same(sum('vcdr_abs_error' in r for r in vals),groupagg['vcdr_measurable'],'group vCDR coverage')
    same(dict(Counter(p['group'] for p in priorities)),summary['image_only_priority_counts'],'priority aggregate count')
    groups={'error':0,'invalid_geometry':1,'disagreement':2,'pending':3};all_saturated=True
    for r in summary['research_queue_evaluation']:
        inds=list(range(174)) if r['subgroup']=='all174' else [i for i in range(174) if all(meta[n][i]['status']=='ok' for n in names)]
        inds.sort(key=lambda i:(groups[priorities[i]['group']],-priorities[i]['score'] if priorities[i]['group']=='disagreement' else 0,i))
        events=[True if meta[names[0]][i]['status']!='ok' else min(computed[names[0]][i]['disc_dice'],computed[names[0]][i]['cup_dice'])<r['threshold'] for i in inds]
        same(len(inds),r['n_images'],'queue subgroup count');same([independent.budget(events,f) for f in (.1,.2,.5)],r['budgets'],'queue independent order and arithmetic')
        all_saturated &= all(events)
    check(not any(first_diffs.values()),'first versus supplement matching')
    report=dict(schema='hyunoptic-independent-rim-artifact-audit/v1',passed=True,verifier_sha256=sha(Path(__file__)),
        unique_images=174,unique_image_model_pairs=348,total_actual_inferences=696,saved_masks_verified=348,
        first_vs_second_differences_at_1e12=dict(first_diffs),first_vs_second_exact_numeric_differences=exact_metric_diffs,
        reference_coordinate_checks=dict(coordinate),max_TXT_point_to_PNG_boundary_distance_px=max(distances),
        mean_TXT_point_to_PNG_boundary_distance_px=float(np.mean(distances)),
        models=summary['models'],image_only_priority_counts=summary['image_only_priority_counts'],all_queue_threshold_events_saturated=bool(all_saturated),
        no_detection_advantage_over_random=bool(all_saturated),protocol_sha256=sha(supp/'protocol.json'),
        limitations=['No first-pass label PNGs were retained: exact first/second pixel identity cannot be verified; statuses/errors/metrics can.',
          'Supplemental protocol followed first-pass outcome inspection and is exploratory artifact replication, not independent confirmation.',
          'Dataset supplies square optic-nerve-head crops; no reference-derived crop was created by this evaluation.',
          '174 images do not imply 174 independent patients. Repeating inference does not add images or subjects.',
          'PNG/TXT point and foreground checks do not establish full official interpolation/rasterization equivalence.',
          'Saturated research events cannot support event discrimination, specificity, AUROC or clinical triage benefit.'])
    out.mkdir(parents=True,exist_ok=True);(out/'rim_independent_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path('reports/full_validation_20261104/new_external'))
    p.add_argument('--data',type=Path,default=Path('data/new_external_20261104'))
    p.add_argument('--output',type=Path,default=Path('reports/full_validation_20261104/independent'))
    a=p.parse_args();main(a.input,a.data,a.output)
