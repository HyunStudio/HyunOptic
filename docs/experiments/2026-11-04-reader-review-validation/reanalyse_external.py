"""Aggregate preserved Chaksu reader metrics; no new inference or mask ranking.

Run at repository root. Private rows are inputs only; identifiers never exported.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def analyse(models_root):
    paths=[]
    for name in ['papila_real_seed43_20261025','papila_camera_robust_seed43_20261025']:
        matches=list((models_root/name/'evaluation').glob('chaksu*/model_eval_private_cases.json'))
        if len(matches)!=1:raise ValueError('Need exactly one preserved external evaluation for each model')
        paths.append(matches[0])
    datasets=[json.loads(p.read_text(encoding='utf-8'))['cases'] for p in paths]
    ids=[[(r['camera'],r['case_id']) for r in rows] for rows in datasets]
    if any(len(set(keys))!=len(keys) for keys in ids) or set(ids[0])!=set(ids[1]):
        raise ValueError('Duplicate or unmatched camera/case identities')
    if len(ids[0])!=336:raise ValueError('Expected all 336 original Chaksu records')
    index=[{(r['camera'],r['case_id']):r for r in rows} for rows in datasets]
    keys=sorted(index[0])
    out={'schema':'hyunoptic.external-reader-reanalysis/v1','dataset':'Chaksu Test',
         'new_inference':False,'n_original_records':336,'patient_linkage_available':False,
         'source_private_file_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
         'models':[],'paired_models':{},'preference_flips':{},
         'limitations':['Preserved October 25 model evaluation rows, not November 4 predictions.',
                        'No preserved label masks for the same review-queue evaluation; not recomputed from vCDR.',
                        '25 reference-loading failures stay separate from model geometry failures.',
                        'No patient-level uncertainty intervals because external patient linkage is unavailable.']}
    for path,records in zip(paths,datasets):
        model={'bundle_folder':path.parent.parent.parent.name,'readers':{},
               'n_reference_load_failures':sum(r.get('failure_category')=='load_or_geometry_error' for r in records),
               'n_model_geometry_failures':sum(r['status']=='invalid_geometry' for r in records),
               'paired_reader_change_exp2_minus_exp1':{}}
        for reader in ['expert1','expert2']:
            model['readers'][reader]={}
            for field in ['disc_dice','cup_dice','abs_vcdr_error']:
                values=[r[reader][field] for r in records if field in r.get(reader,{})]
                model['readers'][reader][field]={'n_images':len(values),'mean':float(np.mean(values)) if values else None}
        for field in ['disc_dice','cup_dice','abs_vcdr_error']:
            diffs=[r['expert2'][field]-r['expert1'][field] for r in records
                   if all(field in r.get(reader,{}) for reader in ['expert1','expert2'])]
            model['paired_reader_change_exp2_minus_exp1'][field]={
                'n_common_images':len(diffs),'mean':float(np.mean(diffs)) if diffs else None}
        out['models'].append(model)
    for reader in ['expert1','expert2']:
        out['paired_models'][reader]={}
        for field in ['disc_dice','cup_dice','abs_vcdr_error']:
            pairs=[(index[0][key][reader][field],index[1][key][reader][field]) for key in keys
                   if all(field in records[key].get(reader,{}) for records in index)]
            out['paired_models'][reader][field]={'n_common_images':len(pairs),
                'baseline_mean':float(np.mean([a for a,b in pairs])) if pairs else None,
                'photo_mean':float(np.mean([b for a,b in pairs])) if pairs else None,
                'mean_photo_minus_baseline':float(np.mean([b-a for a,b in pairs])) if pairs else None}
    for field in ['disc_dice','cup_dice']:
        flips=0;available=0
        for key in keys:
            if all(field in records[key].get(reader,{}) for records in index for reader in ['expert1','expert2']):
                available+=1
                ds=[index[1][key][e][field]-index[0][key][e][field] for e in ['expert1','expert2']]
                flips+=int(ds[0]*ds[1]<-1e-12)
        out['preference_flips'][field]={'n_available':available,'n_flips':flips}
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-root',type=Path,default=Path('models'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Do not overwrite evidence')
    result=analyse(args.models_root)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print('Reanalysed 336 preserved external records per model; no new inference.')
