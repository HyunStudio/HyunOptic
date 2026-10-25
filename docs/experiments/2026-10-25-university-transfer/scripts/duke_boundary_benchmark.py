"""Compare supplied Duke automatic boundaries with supplied manual readers.

This is a re-analysis of distributed algorithm outputs, NOT HyunOptic OCT inference.
No model is trained and no missing annotation is filled.
"""
import io,json,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def compare(a,b,height):
    if a.shape!=b.shape or a.ndim!=3 or a.shape[0]!=8:raise ValueError('Boundary shape mismatch')
    ref=np.isfinite(b);pred=np.isfinite(a)
    valid=ref&pred&(a>=0)&(a<=height)&(b>=0)&(b<=height)
    errors=np.abs(a[valid]-b[valid])
    return {'reference_points':int(ref.sum()),'common_valid_points':int(valid.sum()),
      'reference_points_without_finite_prediction':int((ref&~pred).sum()),
      'out_of_bounds_finite_pairs':int((ref&pred&~valid).sum()),
      'mae_px':float(errors.mean()) if len(errors) else None,
      'annotated_reference_bscans':int(ref.any(axis=(0,1)).sum()),
      'per_layer_mae_px':[float(np.abs(a[i][valid[i]]-b[i][valid[i]]).mean()) if valid[i].any() else None for i in range(8)]}

if __name__=='__main__':
    small=np.ones((8,2,2));assert compare(small,small,10)['mae_px']==0
    missing=small.copy();missing[0,0,0]=np.nan
    assert compare(missing,small,10)['reference_points_without_finite_prediction']==1
    protocol={'task':'Re-analyse distributed automatic OCT layer boundaries against both manual readers',
      'primary_summary':'Unweighted mean of subject-level MAE over common finite in-bounds points; also report per-layer and coverage',
      'models':['automaticLayersDME','automaticLayersNormal'],'references':['manualLayers1','manualLayers2'],
      'no_retraining':True,'not_hyunoptic_model_performance':True,'no_imputation':True,
      'no_od_oc_metrics':True,'not_independent_validation_of_original_Duke_algorithm':True}
    (HERE/'duke_boundary_protocol.json').write_text(json.dumps(protocol,indent=2))
    rows=[]
    with zipfile.ZipFile(ROOT/'data/university_20261025/2015_BOE_Chiu2.zip') as z:
        for name in sorted(n for n in z.namelist() if n.endswith('.mat') and not n.startswith('__MACOSX/')):
            data=loadmat(io.BytesIO(z.read(name)))
            for model in protocol['models']:
                for ref in protocol['references']:
                    rows.append({'member':name,'algorithm':model,'reference':ref,**compare(data[model],data[ref],data['images'].shape[0])})
    result=[]
    for model in protocol['models']:
        for ref in protocol['references']:
            group=[r for r in rows if r['algorithm']==model and r['reference']==ref]
            result.append({'algorithm':model,'reference':ref,'n_subject_files':len(group),
              'mean_subject_mae_px':float(np.mean([r['mae_px'] for r in group])),
              'common_valid_points':sum(r['common_valid_points'] for r in group),
              'reference_points':sum(r['reference_points'] for r in group),
              'reference_points_without_finite_prediction':sum(r['reference_points_without_finite_prediction'] for r in group),
              'out_of_bounds_finite_pairs':sum(r['out_of_bounds_finite_pairs'] for r in group),
              'annotated_reference_bscans':sum(r['annotated_reference_bscans'] for r in group),
              'mean_subject_per_layer_mae_px':np.mean([r['per_layer_mae_px'] for r in group],axis=0).tolist()})
    (HERE/'duke_boundary_private_rows.json').write_text(json.dumps(rows,indent=2))
    (HERE/'duke_boundary_results.json').write_text(json.dumps({'protocol':protocol,'results':result},indent=2))
    print(json.dumps(result,indent=2))
