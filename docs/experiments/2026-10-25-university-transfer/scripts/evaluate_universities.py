"""Frozen-model university-data evaluation. No training or source-mask modification."""
import collections, csv, hashlib, json, os, platform, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from hyunoptic.measure import dice, measure_masks
from hyunoptic.seg import preprocess
from hyunoptic.seg.bundle import verify_bundle, file_sha256
from hyunoptic.seg.inference import Predictor

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DATA=ROOT/'data/university_20261025'
MODELS={'baseline42':'papila_real_v1_20261025','baseline43':'papila_real_seed43_20261025',
        'baseline44':'papila_real_seed44_20261025','photometric43':'papila_camera_robust_seed43_20261025'}

def reference_masks(raw):
    if raw.ndim!=2 or not np.isfinite(raw).all() or not set(np.unique(raw)).issubset({0,-1,-2}):
        raise ValueError('Unexpected FairSeg label encoding/shape')
    disc=raw!=0;cup=raw==-2
    if not disc.any() or not cup.any():raise ValueError('Empty reference disc/cup')
    return disc,cup

def score(labels,reference):
    d=labels>=1;c=labels==2
    row={'model_status':'ok'}
    if not d.any() or not c.any():row['model_status']='invalid_geometry'
    else:
        m=measure_masks(d,c)
        if m.warnings:row['model_status']='invalid_geometry'
        else:row['predicted_vcdr']=m.vertical_cdr
    if reference is not None:
        try:
            rd,rc=reference_masks(reference)
            if labels.shape!=rd.shape:raise ValueError('Reference/image shape mismatch')
            row.update(disc_dice=dice(d,rd),cup_dice=dice(c,rc),reference_vcdr=measure_masks(rd,rc).vertical_cdr)
            if 'predicted_vcdr' in row:row['abs_vcdr_error']=abs(row['predicted_vcdr']-row['reference_vcdr'])
        except ValueError as e:row['reference_failure']=str(e)
    return row

def dist(values):
    a=np.array(values,float)
    return {'n':len(a),'mean':float(a.mean()) if len(a) else None,'median':float(np.median(a)) if len(a) else None}

def summarize(rows):
    return {'n_images':len(rows),'n_measurable':sum('predicted_vcdr' in r for r in rows),
            'n_model_failed':sum(r['model_status']!='ok' for r in rows),
            'n_reference_failed':sum('reference_failure' in r for r in rows),
            'model_status_counts':dict(collections.Counter(r['model_status'] for r in rows)),
            **{k:dist([r[k] for r in rows if k in r]) for k in ['disc_dice','cup_dice','abs_vcdr_error']}}

def main():
    torch.set_num_threads(4)
    assert torch.cuda.is_available()
    bundles={k:verify_bundle(ROOT/'models'/v) for k,v in MODELS.items()}
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),
      'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'runner_sha256':file_sha256(Path(__file__)),
      'models':{k:{'folder':v.folder.name,'weights_sha256':v.weights_sha256,'run_id':v.run_id} for k,v in bundles.items()},
      'research_only':True,'exploratory':True,'retraining':False,'reference_based_crops':False,
      'selection':'All 2000 official FairSeg Test NPZ; OLIVES all complete fundus TIFFs in predeclared bounded archive-prefix pilot',
      'fairseg_mapping':'0 background, -1 rim, -2 cup; disc union(-1,-2), cup=-2; official utils confirms class2 cup',
      'fairseg_input':'uint8 original SLO, replicated to RGB via PIL; no contrast stretch, crop, histogram adaptation or target-derived preprocessing',
      'inference':'Existing whole-image letterbox384, fixed normalization and largest_disc_component_v1; CUDA float32 batches8, no AMP',
      'metrics':'Original-resolution per-image Dice includes invalid predictions; vCDR pixel-span MAE only when measurable; paired error separately',
      'no_claims':['clinical validity','diagnostic accuracy','population fairness','independent institutional validation'],
      'runtime':{'python':platform.python_version(),'torch':torch.__version__,'device':torch.cuda.get_device_name(0)}}
    p=HERE/'protocol.json'
    if not p.exists():p.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    else:
        frozen=json.loads(p.read_text())
        assert frozen['runner_sha256']==protocol['runner_sha256'] and frozen['models']==protocol['models']
    print('Protocol frozen; waiting for verified acquisition',flush=True)
    while not (DATA/'fairseg_test/download_result.json').exists() or not (DATA/'olives_pilot/private_manifest.json').exists():
        time.sleep(10)
    acquisition=json.loads((DATA/'fairseg_test/download_result.json').read_text())
    assert acquisition['verified']==2000 and not acquisition['errors']
    manifest=json.loads((DATA/'fairseg_test/source_manifest.json').read_text())
    fairfiles=sorted(manifest['files'],key=lambda x:x['path'])
    assert len(fairfiles)==2000
    # Validate official metadata partition and source hashes before predictions.
    meta=list(csv.DictReader((DATA/'fairseg_test/data_summary.csv').open()))
    meta={r['filename']:r for r in meta}
    for f in fairfiles:
        path=DATA/'fairseg_test'/Path(f['path']).name
        assert file_sha256(path)==f['lfs']['oid']
        assert meta[path.name]['use'].lower()=='test',meta[path.name]['use']
    olives=json.loads((DATA/'olives_pilot/private_manifest.json').read_text())['images']
    assert len(olives)>0
    inventories={'fairseg':len(fairfiles),'olives_pilot':len(olives),'fairseg_revision':manifest['revision']}
    (HERE/'inventory.json').write_text(json.dumps(inventories,indent=2))
    allrows={}
    for dataset,items in [('fairseg',fairfiles),('olives_pilot',olives)]:
        for model,bundle in bundles.items():
            output=HERE/(dataset+'_'+model+'_private.jsonl')
            previous=[json.loads(l) for l in output.read_text().splitlines()] if output.exists() else []
            assert len(previous)<=len(items)
            predictor=Predictor(bundle)
            network=predictor.model.to('cuda')
            rows=list(previous);started=time.time()
            with output.open('a',encoding='utf-8') as stream:
                for start in range(len(rows),len(items),8):
                    images=[];lbs=[];refs=[];names=[]
                    for item in items[start:start+8]:
                        if dataset=='fairseg':
                            path=DATA/'fairseg_test'/Path(item['path']).name
                            with np.load(path,allow_pickle=False) as npz:
                                image=npz['slo_fundus'];ref=npz['disc_cup_mask']
                            assert image.dtype==np.uint8 and image.ndim==2 and image.shape==ref.shape
                            im=Image.fromarray(image).convert('RGB')
                        else:
                            path=DATA/'olives_pilot'/item['local'];ref=None
                            assert file_sha256(path)==item['sha256']
                            with Image.open(path) as original:im=original.convert('RGB')
                        arr,lb=preprocess.image_array(im,bundle.image_size)
                        images.append(preprocess.normalise(arr));lbs.append(lb);refs.append(ref);names.append(path.name)
                    x=torch.from_numpy(np.stack(images)).to('cuda')
                    with torch.inference_mode():raw=network(x).argmax(1).cpu().numpy().astype(np.uint8)
                    for lab,lb,ref,name in zip(raw,lbs,refs,names):
                        lab=preprocess.to_original(preprocess.postprocess(lab),lb)
                        row={'case':name,**score(lab,ref)}
                        stream.write(json.dumps(row,allow_nan=False)+'\n');rows.append(row)
                    stream.flush()
                    if (start//8)%25==0:print(dataset,model,len(rows),'/',len(items),flush=True)
            allrows[(dataset,model)]=rows
            (HERE/(dataset+'_'+model+'_aggregate.json')).write_text(json.dumps(summarize(rows),indent=2))
            print('DONE',dataset,model,json.dumps(summarize(rows)),'seconds',round(time.time()-started,1),flush=True)
            del predictor,network;torch.cuda.empty_cache()
    paired={}
    for ds in ['fairseg','olives_pilot']:
        old={r['case']:r for r in allrows[(ds,'baseline43')]}
        new={r['case']:r for r in allrows[(ds,'photometric43')]}
        common=[k for k in old if 'abs_vcdr_error' in old[k] and 'abs_vcdr_error' in new[k]]
        paired[ds]={'n':len(common),'baseline43':dist([old[k]['abs_vcdr_error'] for k in common]),'photometric43':dist([new[k]['abs_vcdr_error'] for k in common])}
    (HERE/'paired_metrics.json').write_text(json.dumps(paired,indent=2))
    for key,b in bundles.items():assert verify_bundle(b.folder).weights_sha256==protocol['models'][key]['weights_sha256']
    (HERE/'completed.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'all_model_hashes_unchanged':True,'datasets':inventories},indent=2))

if __name__=='__main__':main()
