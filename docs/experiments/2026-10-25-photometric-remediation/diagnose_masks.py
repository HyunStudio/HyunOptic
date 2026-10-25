import io,json,pathlib,zipfile,numpy as np,torch
from PIL import Image
from hyunoptic.chaksu import scan_test_archive
from hyunoptic.seg.bundle import verify_bundle,load_state_dict
from hyunoptic.seg.model import build
from hyunoptic.seg import preprocess
from hyunoptic.measure import measure_masks

torch.set_num_threads(4)
base=pathlib.Path('models/papila_real_seed43_20261025')
private=next((base/'evaluation').glob('chaksu*/model_eval_private_cases.json'))
rows=json.loads(private.read_text(encoding='utf-8'))['cases']
valid=[r for r in rows if r.get('expert1') and 'abs_vcdr_error' in r['expert1']]
groups={'invalid':[r for r in rows if r.get('failure_category')=='invalid_geometry'],
        'highest_error':sorted(valid,key=lambda r:r['expert1']['abs_vcdr_error'],reverse=True)[:16],
        'lowest_error':sorted(valid,key=lambda r:r['expert1']['abs_vcdr_error'])[:16]}
cases,_=scan_test_archive('data/Chaksu_Test.zip'); cases={c.case_id:c for c in cases}
bundle=verify_bundle(base); model=build(bundle.manifest['architecture']);model.load_state_dict(load_state_dict(bundle));model.eval()
output=[]
with zipfile.ZipFile('data/Chaksu_Test.zip') as archive,torch.no_grad():
    for name,selected in groups.items():
        values=[]
        for r in selected:
            image=Image.open(io.BytesIO(archive.read(cases[r['case_id']].image_member))).convert('RGB')
            arr,lb=preprocess.image_array(image,bundle.image_size)
            prob=model(torch.from_numpy(preprocess.normalise(arr)[None])).softmax(1)[0].numpy()
            raw=prob.argmax(0).astype(np.uint8); labels=preprocess.postprocess(raw)
            disc=labels>=1; cup=labels==2; largest=preprocess.largest_component(cup)
            v={'raw_cup_pixels':int((raw==2).sum()),'retained_cup_pixels':int(cup.sum()),'cup_component_removed_fraction':float(1-largest.sum()/cup.sum()) if cup.any() else None,'max_cup_probability':float(prob[2].max())}
            if cup.any():
                old=measure_masks(disc,cup).vertical_cdr; new=measure_masks(disc,largest).vertical_cdr
                ref=r['expert1']['reference_vcdr']
                v.update(predicted_vcdr=old,reference_vcdr=ref,largest_cup_vcdr=new,old_abs_error=abs(old-ref),largest_cup_abs_error=abs(new-ref))
            values.append(v)
        keys=sorted(set().union(*(v.keys() for v in values)))
        summary={'group':name,'n':len(values),'no_raw_cup':sum(v['raw_cup_pixels']==0 for v in values),'raw_cup_removed_by_disc_selection':sum(v['raw_cup_pixels']>0 and v['retained_cup_pixels']==0 for v in values),'mean':{k:float(np.mean([v[k] for v in values if v.get(k) is not None])) for k in keys if any(v.get(k) is not None for v in values)}}
        output.append(summary);print(json.dumps(summary),flush=True)
pathlib.Path('reports/remediation_20261025/mask_diagnostic_summary.json').write_text(json.dumps({'diagnostic_only_selected_cases_not_performance_estimate':True,'prediction_coordinate_system':'384px letterboxed model grid; reference vCDR comes from prior original-resolution report','groups':output},indent=2),encoding='utf-8')
