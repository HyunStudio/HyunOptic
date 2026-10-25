"""Duke DME original archive integrity and annotation compatibility audit."""
import io,json,time,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from hyunoptic.seg.bundle import file_sha256

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'data/university_20261025/2015_BOE_Chiu2.zip'
if __name__=='__main__':
    while not path.exists():time.sleep(5)
    rows=[];fields={};examples=[]
    with zipfile.ZipFile(path) as z:
        bad=z.testzip();assert bad is None,bad
        mats=[n for n in z.namelist() if n.endswith('.mat') and not n.startswith('__MACOSX/')]
        for name in mats:
            data=loadmat(io.BytesIO(z.read(name)))
            entry={}
            for k,a in data.items():
                if k.startswith('__'):continue
                if isinstance(a,np.ndarray):
                    record={'shape':list(a.shape),'dtype':str(a.dtype)}
                    if np.issubdtype(a.dtype,np.number):
                        record['n_finite']=int(np.isfinite(a).sum());record['n_nan']=int(np.isnan(a).sum())
                        if np.isfinite(a).any():record.update(min=float(np.nanmin(a)),max=float(np.nanmax(a)))
                    entry[k]=record
            rows.append({'member':name,'fields':entry})
        field_names=sorted({k for r in rows for k in r['fields']})
    report={'source':'https://people.duke.edu/~sf59/Chiu_BOE_2014_dataset.htm',
      'archive_sha256':file_sha256(path),'archive_bytes':path.stat().st_size,
      'all_zip_member_crc_verified':True,'mat_files_read':len(rows),'field_names':field_names,
      'status':'data_integrity_and_task_compatibility_audit_completed',
      'model_inference_performed':False,'model_accuracy_metrics_available':False,
      'reason':'OCT B-scan retinal-layer/fluid annotation task differs from fundus optic-disc/cup segmentation; no OD/OC reference masks. Existing fundus weights cannot establish OCT layer performance.',
      'source_terms':'Research/education only; no commercialization or redistribution; cite Chiu et al. BOE 2015',
      'per_file_schema':[r['fields'] for r in rows]}
    (Path(__file__).parent/'duke_private_inventory.json').write_text(json.dumps(rows,indent=2))
    (Path(__file__).parent/'duke_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
