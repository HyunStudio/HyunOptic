"""Decode the bytes whose digest was checked, even during file replacement."""
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hyunoptic.review.inputs import sha256
from hyunoptic.review.priority import priority
from hyunoptic.review.store import ReviewStore


def png(labels):
    buffer=io.BytesIO()
    Image.fromarray(labels).save(buffer,format='PNG')
    return buffer.getvalue()


def maps():
    labels=np.zeros((20,20),np.uint8)
    labels[1:9,1:9]=1
    labels[3:6,3:6]=2
    shifted=np.roll(labels,10,axis=1)
    return labels,shifted


def test_priority_threshold_counts_can_be_saved_as_standard_json(tmp_path):
    labels,_=maps()
    data=png(labels)
    paths=[tmp_path/'a.png',tmp_path/'b.png']
    for path in paths:path.write_bytes(data)
    result=priority([dict(status='ok',labels_path=str(p),labels_sha256=sha256(data)) for p in paths])
    # This ordinary downstream aggregate failed with NumPy int64 during the real study.
    encoded=json.dumps({'n_low_disagreement':sum(r['score']<=.1 for r in [result])},allow_nan=False)
    assert json.loads(encoded)=={'n_low_disagreement':1}


def test_disagreement_decodes_verified_bytes_not_replaced_path(tmp_path,monkeypatch):
    original,shifted=maps()
    data=png(original)
    paths=[tmp_path/'a.png',tmp_path/'b.png']
    for path in paths:path.write_bytes(data)
    records=[dict(status='ok',labels_path=str(path),labels_sha256=sha256(data)) for path in paths]
    read=Path.read_bytes
    fired=[]
    def racing_read(path):
        value=read(path)
        if path==paths[0] and not fired:
            fired.append(True)
            path.write_bytes(png(shifted))
        return value
    monkeypatch.setattr(Path,'read_bytes',racing_read)
    result=priority(records)
    assert result['group']=='disagreement'
    assert result['score']==0.0  # both SHA-verified snapshots have identical pixels
    assert priority(records)['group']=='error'  # next read sees the changed artifact


def test_store_geometry_check_decodes_the_verified_snapshot(tmp_path,monkeypatch):
    labels,_=maps()
    path=tmp_path/'mask.png'
    data=png(labels)
    path.write_bytes(data)
    store=ReviewStore(tmp_path/'store')
    read=Path.read_bytes
    def racing_read(current):
        value=read(current)
        if current==path:current.write_bytes(png(np.zeros((4,4),np.uint8)))
        return value
    monkeypatch.setattr(Path,'read_bytes',racing_read)
    # The declared hash and geometry describe the 20x20 snapshot, not the replacement.
    store._verify_predictions({'height':20,'width':20},[
        dict(status='ok',labels_path=str(path),labels_sha256=sha256(data))])


def test_store_withholds_predictions_if_priority_detects_replacement(tmp_path,monkeypatch):
    labels,shifted=maps()
    image=io.BytesIO()
    Image.new('RGB',(20,20)).save(image,format='PNG')
    store=ReviewStore(tmp_path/'store')
    models=[dict(folder=str(i),identity=str(i),run_id=str(i),weights_sha256=str(i)) for i in range(2)]
    sid=store.create_session([('sample.png',image.getvalue())],models)
    cid=store.cases(sid)[0]['id']
    token=store.claim(cid)
    for model in models:
        store.record_prediction(cid,model['identity'],dict(status='ok'),labels,claim_token=token)
    store.finish(cid,claim_token=token)
    row=store.cases(sid)[0]
    target=Path(row['predictions'][0]['labels_path'])
    verify=store._verify_predictions
    def replace_after_verification(case,predictions):
        verify(case,predictions)
        target.write_bytes(png(shifted))
    monkeypatch.setattr(store,'_verify_predictions',replace_after_verification)
    row=store.cases(sid)[0]
    assert row.get('integrity_error') is True
    assert row['predictions']==[]
    assert row['prediction_set_hash'] is None
