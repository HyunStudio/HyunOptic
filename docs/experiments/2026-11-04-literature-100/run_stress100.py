"""Private, predeclared100-condition own-model audit; not100 paper reproductions."""
from __future__ import annotations
import argparse,hashlib,io,json,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageEnhance,ImageFilter


def conditions():
    out=[dict(name='original',family='original',value=None)]
    families={
        'brightness':[.2,.35,.5,.65,.8,1.2,1.4,1.6,1.8],
        'contrast':[.2,.35,.5,.65,.8,1.2,1.4,1.6,1.8],
        'saturation':[0,.2,.4,.6,.8,1.2,1.5,2,3],
        'gamma':[.3,.4,.5,.65,.8,1.2,1.5,2,3],
        'blur_px':[.25,.5,.75,1,1.5,2,3,4,6],
        'gaussian_noise_sigma':[1,2,4,6,8,12,16,24,32],
        'jpeg_quality':[5,10,15,25,35,50,65,80,95],
        'brightness_contrast':[[b,c] for b in [.4,.7,1.3] for c in [.4,.7,1.3]],
        'downsample_restore_width':[16,24,32,48,64,96,128,192,256],
        'central_occlusion_fraction':[.01,.02,.04,.06,.08,.1,.15,.2,.3],
        'rgb_gains':[[.5,1,1],[1,.5,1],[1,1,.5],[1.5,1,1],[1,1.5,1],[1,1,1.5],[.7,1.2,1.2],[1.2,.7,1.2],[1.2,1.2,.7]]}
    for family,values in families.items():
        for index,value in enumerate(values):out.append(dict(name=f'{family}_{index+1:02}',family=family,value=value))
    assert len(out)==100 and len({c['name'] for c in out})==100
    return out


def transform(image,c,seed):
    family,value=c['family'],c['value']
    if family=='original':return image.copy()
    if family=='brightness':return ImageEnhance.Brightness(image).enhance(value)
    if family=='contrast':return ImageEnhance.Contrast(image).enhance(value)
    if family=='saturation':return ImageEnhance.Color(image).enhance(value)
    if family=='blur_px':return image.filter(ImageFilter.GaussianBlur(value))
    if family=='brightness_contrast':return ImageEnhance.Contrast(ImageEnhance.Brightness(image).enhance(value[0])).enhance(value[1])
    if family=='downsample_restore_width':
        return image.resize((value,max(1,round(image.height*value/image.width))),Image.Resampling.BILINEAR).resize(image.size,Image.Resampling.BILINEAR)
    if family=='jpeg_quality':
        buff=io.BytesIO();image.save(buff,format='JPEG',quality=value)
        with Image.open(io.BytesIO(buff.getvalue())) as decoded:return decoded.convert('RGB').copy()
    array=np.asarray(image,dtype=np.float64)
    if family=='gamma':array=255*(array/255)**value
    elif family=='gaussian_noise_sigma':array+=np.random.default_rng(seed).normal(0,value,array.shape)
    elif family=='rgb_gains':array*=np.asarray(value)[None,None,:]
    elif family=='central_occlusion_fraction':
        side=np.sqrt(value);w,h=image.size
        x0=round(w*(1-side)/2);x1=round(w*(1+side)/2)
        y0=round(h*(1-side)/2);y1=round(h*(1+side)/2)
        array[y0:y1,x0:x1]=0
    else:raise ValueError(f'Unknown condition {family}')
    return Image.fromarray(np.clip(np.rint(array),0,255).astype(np.uint8),'RGB')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--papila-root',type=Path,default=Path('data/PAPILA'))
    parser.add_argument('--baseline',type=Path,default=Path('models/papila_real_seed43_20261025'))
    parser.add_argument('--comparison',type=Path,default=Path('models/papila_camera_robust_seed43_20261025'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import torch
    from hyunoptic.papila import discover_cases,load_image,load_contours
    from hyunoptic.seg.bundle import verify_bundle
    from hyunoptic.seg.data import verify_split_manifest
    from hyunoptic.seg.inference import Predictor
    from hyunoptic.source_fingerprint import papila_content_sha256
    from hyunoptic.measure import dice,measure_masks,polygon_mask
    args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4)
    bundles=[verify_bundle(p) for p in [args.baseline,args.comparison]]
    splits=[verify_split_manifest(json.loads((b.folder/'split_manifest.json').read_text(encoding='utf-8'))) for b in bundles]
    assert splits[0]==splits[1]
    content_hash=papila_content_sha256(args.papila_root)
    assert all(content_hash==b.manifest['training']['source_content_sha256'] for b in bundles)
    selected=[];patients=set()
    for case in sorted(discover_cases(args.papila_root),key=lambda x:x.image_id):
        if case.image_id in splits[0]['splits']['holdout'] and case.patient_id not in patients:
            selected.append(case);patients.add(case.patient_id)
        if len(selected)==4:break
    assert len(selected)==4
    test_conditions=conditions()
    # Validate transformation geometry before freezing the protocol, without inference/annotations.
    control=Image.new('RGB',(37,23),(75,115,145))
    for i,c in enumerate(test_conditions):
        assert transform(control,c,20261104+i).size==control.size
    import hyunoptic.seg.inference as inference_module
    import hyunoptic.seg.preprocess as preprocess_module
    protocol=dict(schema='hyunoptic-own-model-corruption100-v1',date_kst='2026-11-04',
        base_commit='1d3c1b108e2da8a19bd444337562882115f16ecd',seed=20261104,device='cpu',threads=4,
        selection='First lexicographic holdout image per patient, first four distinct patients; same tiny cohort as earlier pilot.',
        n_patients=4,n_original_images=4,n_conditions=100,n_image_conditions=400,n_expected_predictions=800,
        no_training=True,independent_cohort=False,reference_read_after_prediction=True,
        conditions=test_conditions,source_content_sha256=content_hash,
        models=[dict(identity=b.identity,run_id=b.run_id,weights_sha256=b.weights_sha256) for b in bundles],
        source_files_sha256={str(p):digest(p) for p in [Path(inference_module.__file__).relative_to(Path.cwd()),Path(preprocess_module.__file__).relative_to(Path.cwd())]},
        metrics='Disc/cup Dice all returned masks; failures explicit; vCDR on available cases with paired original comparisons.',
        conceptual_sources=['https://arxiv.org/abs/1903.12261','https://arxiv.org/abs/1906.02530'],
        interpretation='Own predeclared exploratory strengths; not ImageNet-C, author benchmarks, calibrated confidence,100paper reproductions or clinical/time-saving evidence.')
    encoded=json.dumps(protocol,indent=2,sort_keys=True,allow_nan=False).encode('utf-8')
    (args.output/'protocol.json').write_bytes(encoded)
    (args.output/'private_selection.json').write_text(json.dumps([c.image_id for c in selected]),encoding='utf-8')
    models=[Predictor(b) for b in bundles]
    rows=[];start=time.perf_counter()
    pred_dir=args.output/'private_predictions';pred_dir.mkdir()
    for ci,c in enumerate(test_conditions):
        for pi,case in enumerate(selected):
            source=load_image(case).convert('RGB')
            image=transform(source,c,20261104+ci*100+pi)
            assert image.size==source.size
            for mi,model in enumerate(models):
                pred=model.predict(image)
                row=dict(case_index=pi,condition=c['name'],family=c['family'],model_index=mi,status=pred.status,
                         measurement=pred.measurement,errors=pred.errors,labels_file=None,labels_sha256=None)
                if pred.labels is not None:
                    assert pred.labels.shape==(source.height,source.width)
                    assert pred.labels.dtype==np.uint8 and set(np.unique(pred.labels)).issubset({0,1,2})
                    path=pred_dir/f'{ci:03}-{pi}-{mi}.png';Image.fromarray(pred.labels).save(path)
                    row.update(labels_file=path.name,labels_sha256=digest(path))
                rows.append(row)
        (args.output/'private_predictions.json').write_text(json.dumps(rows,allow_nan=False),encoding='utf-8')
        print(json.dumps(dict(condition=ci+1,total=100,predictions=len(rows),seconds=round(time.perf_counter()-start,2))),flush=True)
    elapsed=time.perf_counter()-start
    assert len(rows)==800
    # References are first interpreted only after every prediction is frozen.
    refs=[]
    for case in selected:
        image=load_image(case);d,c=load_contours(case,'exp1')
        disc,cup=polygon_mask(d,image.size),polygon_mask(c,image.size)
        refs.append((disc,cup,measure_masks(disc,cup).vertical_cdr))
    for row in rows:
        if row['labels_file'] is None:continue
        path=pred_dir/row['labels_file'];data=path.read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['labels_sha256']
        with Image.open(io.BytesIO(data)) as im:labels=np.asarray(im).copy()
        d,c,v=refs[row['case_index']]
        row['disc_dice']=dice(labels>=1,d);row['cup_dice']=dice(labels==2,c)
        row['abs_vcdr_error']=abs(row['measurement']['vertical_cdr']-v) if row['measurement'] is not None else None
    (args.output/'private_scored_rows.json').write_text(json.dumps(rows,allow_nan=False),encoding='utf-8')
    originals={(r['case_index'],r['model_index']):r for r in rows if r['condition']=='original'}
    aggregates=[]
    for cond in test_conditions:
        for mi in range(2):
            group=[r for r in rows if r['condition']==cond['name'] and r['model_index']==mi]
            scored=[r for r in group if 'disc_dice' in r]
            paired=[(originals[(r['case_index'],mi)]['abs_vcdr_error'],r['abs_vcdr_error']) for r in scored if r['abs_vcdr_error'] is not None and originals[(r['case_index'],mi)]['abs_vcdr_error'] is not None]
            mean=lambda v:float(np.mean(v)) if v else None
            aggregates.append(dict(condition=cond['name'],family=cond['family'],value=cond['value'],model_index=mi,n_cases=4,
                n_dice=len(scored),disc_dice=mean([r['disc_dice'] for r in scored]),cup_dice=mean([r['cup_dice'] for r in scored]),
                geometry_failures=sum(r['status']=='invalid_geometry' for r in group),execution_failures=sum(r['status']=='error' for r in group),
                n_vcdr=sum(r['abs_vcdr_error'] is not None for r in scored),vcdr_mae=mean([r['abs_vcdr_error'] for r in scored if r['abs_vcdr_error'] is not None]),
                n_common_original_vcdr=len(paired),paired_original_vcdr_mae=mean([v[0] for v in paired]),paired_condition_vcdr_mae=mean([v[1] for v in paired])))
    assert papila_content_sha256(args.papila_root)==content_hash
    assert all(verify_bundle(b.folder).identity==b.identity for b in bundles)
    summary=dict(protocol_sha256=hashlib.sha256(encoded).hexdigest(),n_patients=4,n_original_images=4,n_conditions=100,
        n_transformed_image_cases=400,n_model_predictions=800,n_masks=sum(r['labels_file'] is not None for r in rows),
        inference_wall_seconds=round(elapsed,2),conditions=aggregates,
        total_geometry_failures=sum(r['status']=='invalid_geometry' for r in rows),total_execution_failures=sum(r['status']=='error' for r in rows),
        original_source_and_bundles_unchanged=True,limitation=protocol['interpretation'])
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='conditions'},indent=2))


if __name__=='__main__':main()
