"""Independently recompute the new study's metrics from private saved mask bytes.

No inference, no overwriting frozen summaries. Original data and private report needed.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hyunoptic.measure import polygon_mask
from hyunoptic.papila import discover_cases, load_contours, load_image
from hyunoptic.review.store import ReviewStore


def overlap(a,b):
    denominator=int(a.sum())+int(b.sum())
    return 2*int((a&b).sum())/denominator if denominator else 1.


def vertical_ratio(disc,cup):
    d=np.flatnonzero(np.any(disc,axis=1))
    c=np.flatnonzero(np.any(cup,axis=1))
    if not len(d) or not len(c):return None
    return float((c[-1]-c[0]+1)/(d[-1]-d[0]+1))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--papila-root',type=Path,default=Path('data/PAPILA'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Do not overwrite previous verification')
    protocol=json.loads((args.report/'protocol.json').read_text(encoding='utf-8'))
    summary=json.loads((args.report/'summary.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((args.report/'protocol.json').read_bytes()).hexdigest()==summary['protocol_sha256']
    rows=json.loads((args.report/'private_rows.json').read_text(encoding='utf-8'))
    cases={c.image_id:c for c in discover_cases(args.papila_root)}
    store=ReviewStore(args.report/'private_review')
    sessions=store.sessions()
    assert len(sessions)==1
    session=sessions[0]
    saved={r['ordinal']:r for r in store.cases(session['id'])}
    checks=0;hashes=0;max_difference=0.
    for row in rows:
        case=cases[row['image_id']]
        actual=saved[row['ordinal']]
        assert actual['status']=='complete' and not actual.get('integrity_error')
        image=load_image(case)
        references={}
        for reader in ['exp1','exp2']:
            if row['references'][reader]['available']:
                d,c=load_contours(case,reader)
                references[reader]=polygon_mask(d,image.size),polygon_mask(c,image.size)
        masks=[]
        by_identity={p['model_identity']:p for p in actual['predictions']}
        for mi,model in enumerate(protocol['models']):
            pred=by_identity[model['identity']]
            data=Path(pred['labels_path']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==pred['labels_sha256']
            hashes+=1
            with Image.open(io.BytesIO(data)) as f:labels=np.array(f)
            assert labels.shape==(image.height,image.width)
            assert np.isin(labels,[0,1,2]).all()
            masks.append((labels>=1,labels==2))
            measured=vertical_ratio(*masks[-1])
            if pred['status']=='ok':
                assert abs(measured-pred['measurement']['vertical_cdr'])<1e-12
                checks+=1
            else:assert pred['measurement'] is None
            for reader,reference in references.items():
                expected=row['predictions'][mi]['metrics'][reader]
                independent={'disc_dice':overlap(masks[-1][0],reference[0]),
                             'cup_dice':overlap(masks[-1][1],reference[1]),
                             'abs_vcdr_error':abs(measured-vertical_ratio(*reference)) if pred['status']=='ok' else None}
                for field,value in independent.items():
                    if value is None:assert expected[field] is None
                    else:
                        difference=abs(value-expected[field])
                        max_difference=max(max_difference,difference)
                        assert difference<1e-12
                    checks+=1
        if row['priority']['group']=='disagreement':
            value=max(1-overlap(masks[0][0],masks[1][0]),1-overlap(masks[0][1],masks[1][1]))
            difference=abs(value-row['priority']['score'])
            max_difference=max(max_difference,difference)
            assert difference<1e-12
            checks+=1
    assert len(rows)==98 and hashes==196
    result={'valid':True,'n_images':len(rows),'n_mask_hashes_verified':hashes,
            'n_metric_comparisons':checks,'max_absolute_difference':max_difference,
            'method':'Independent boolean pixel sums and occupied-row spans; references rasterized with shared polygon convention; no model inference',
            'protocol_sha256':summary['protocol_sha256']}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
