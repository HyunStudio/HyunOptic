"""Compare saved original-only predictions to earlier saved reader-review run.

No inference or annotation access. SQLite and PNG artifacts are read directly;
output contains aggregate difference counts and hashes, never subject IDs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import numpy as np
from PIL import Image

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main(new,old,out):
    new_protocol=read(new/'protocol.json');old_protocol=read(old/'protocol.json')
    model_ids=[p['identity'] for p in new_protocol['models']]
    assert set(model_ids)=={p['identity'] for p in old_protocol['models']},'Model identities differ'
    assert new_protocol['source_content_sha256']==old_protocol['source_content_sha256'],'Source contents differ'
    selection=read(new/'private_selection.json');old_selection=read(old/'private_selection.json')
    assert set(selection)==set(old_selection) and len(selection)==len(old_selection)==98,'Cohort differs'
    new_rows=read(new/'private_scored_rows.json');old_rows=read(old/'private_rows.json')
    originals=[r for r in new_rows if r['condition']=='original']
    assert len(originals)==196 and len({(r['case_index'],r['model_index']) for r in originals})==196
    db=sqlite3.connect(f'file:{(old/"private_review/review.sqlite3").as_posix()}?mode=ro',uri=True)
    cases={r['ordinal']:r for r in (json.loads(x[0]) for x in db.execute('select data from cases'))}
    predictions={(cid,mid):json.loads(data) for cid,mid,data in db.execute('select case_id,model_identity,data from predictions')}
    db.close()
    assert len(cases)==98 and len(predictions)==196,'Earlier saved store incomplete'
    old_by_image={r['image_id']:r for r in old_rows};old_ord={image:i for i,image in enumerate(old_selection)}
    old_mi={p['identity']:i for i,p in enumerate(old_protocol['models'])}
    counts=Counter();max_error={f:0. for f in ('disc_dice','cup_dice','abs_vcdr_error')}
    for row in originals:
        image_id=selection[row['case_index']];mi=row['model_index'];identity=model_ids[mi]
        prior_row=old_by_image[image_id];prior=predictions[cases[old_ord[image_id]]['id'],identity]
        assert prior_row['ordinal']==old_ord[image_id]
        counts['predictions_compared']+=1
        counts['status_differences']+=row['status']!=prior['status']
        counts['measurement_differences']+=row['measurement']!=prior['measurement']
        counts['error_list_differences']+=row['errors']!=prior['errors']
        new_path=new/'private_predictions'/row['labels_file'] if row['labels_file'] else None
        old_path=old/'private_review'/prior['labels_path'] if prior.get('labels_path') else None
        counts['mask_presence_differences']+=(new_path is None)!=(old_path is None)
        if new_path is not None and old_path is not None:
            assert sha(new_path)==row['labels_sha256'] and sha(old_path)==prior['labels_sha256'],'Saved mask integrity failure'
            with Image.open(new_path) as im:a=np.array(im)
            with Image.open(old_path) as im:b=np.array(im)
            counts['mask_pairs_compared']+=1
            counts['mask_shape_or_dtype_differences']+=a.shape!=b.shape or a.dtype!=b.dtype
            equal=np.array_equal(a,b);counts['pixel_mask_differences']+=not equal
            if a.shape==b.shape:counts['different_pixels']+=int(np.count_nonzero(a!=b))
            counts['png_byte_hash_differences']+=row['labels_sha256']!=prior['labels_sha256']
        previous=prior_row['predictions'][old_mi[identity]]['metrics'];current=row['metrics']
        counts['metric_reader_availability_differences']+=set(previous)!=set(current)
        for reader in set(previous)&set(current):
            for field in max_error:
                a,b=current[reader].get(field),previous[reader].get(field)
                counts['metric_values_compared']+=1
                if a is None or b is None:counts['metric_value_differences']+=a!=b
                else:
                    delta=abs(a-b);max_error[field]=max(max_error[field],delta)
                    counts['metric_value_differences']+=delta!=0
    difference_keys=[k for k in counts if k.endswith('_differences') and k!='png_byte_hash_differences']
    report=dict(schema='hyunoptic-original-crossrun-verification/v1',passed=not any(counts[k] for k in difference_keys),
        counts=dict(counts),max_absolute_metric_difference=max_error,metric_tolerance=0,
        current_protocol_sha256=sha(new/'protocol.json'),prior_protocol_sha256=sha(old/'protocol.json'),
        verifier_sha256=sha(Path(__file__)),cohort_images=98,models=2,
        scope='All saved original-only predictions compared directly with earlier saved reader-review predictions; no new inference or reference annotation access.',
        png_hash_note='Encoded-byte differences are reported separately; pixel equality determines mask reproducibility.')
    out.mkdir(parents=True,exist_ok=True);(out/'original_crossrun_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--current',type=Path,default=Path('reports/full_validation_20261104/papila'))
    p.add_argument('--prior',type=Path,default=Path('reports/reader_review_20261104_run1'))
    p.add_argument('--output',type=Path,default=Path('reports/full_validation_20261104/independent'))
    a=p.parse_args();main(a.current,a.prior,a.output)
