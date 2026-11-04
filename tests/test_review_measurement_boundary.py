"""The review store must not display caller-supplied measurements as mask evidence."""
import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from hyunoptic.measure import measure_masks
from hyunoptic.review.export import export_session
from hyunoptic.review.store import ReviewStore


def setup(tmp_path):
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8)).save(buffer, format='PNG')
    models = [dict(folder=str(i), identity=str(i), run_id=str(i), weights_sha256=str(i)) for i in range(2)]
    store = ReviewStore(tmp_path)
    sid = store.create_session([('sample.png', buffer.getvalue())], models)
    cid = store.cases(sid)[0]['id']
    token = store.claim(cid)
    labels = np.zeros((8, 8), np.uint8)
    labels[1:7, 1:7] = 1
    labels[3:5, 3:5] = 2
    return store, sid, cid, token, labels


@pytest.mark.parametrize('supplied', [{'vertical_cdr': .99}, {'vertical_cdr': float('nan')}, None])
def test_measurement_is_derived_from_labels_not_caller(tmp_path, supplied):
    store, sid, cid, token, labels = setup(tmp_path)
    for identity in ['0', '1']:
        store.record_prediction(cid, identity, dict(status='ok', measurement=supplied), labels, claim_token=token)
    store.finish(cid, claim_token=token)
    row = store.cases(sid)[0]
    expected = measure_masks(labels >= 1, labels == 2).to_dict()
    for pred in row['predictions']:
        assert pred['measurement']['vertical_cdr'] == expected['vertical_cdr']
        assert pred['measurement_source'] == 'recomputed_from_saved_labels_v1'
    with zipfile.ZipFile(export_session(store, sid, tmp_path / 'evidence.zip')) as archive:
        text = archive.read('predictions.csv').decode()
        assert '.99' not in text and 'NaN' not in text and str(expected['vertical_cdr']) in text


@pytest.mark.parametrize('mode', ['empty_disc', 'empty_cup'])
def test_empty_geometry_cannot_be_saved_as_success(tmp_path, mode):
    store, sid, cid, token, labels = setup(tmp_path)
    labels[:] = 0 if mode == 'empty_disc' else 1
    store.record_prediction(cid, '0', dict(status='ok', measurement={'vertical_cdr': .5}), labels, claim_token=token)
    pred = store.cases(sid)[0]['predictions'][0]
    assert pred['status'] == 'invalid_geometry'
    assert pred['measurement'] is None and pred['errors']


@pytest.mark.parametrize('status', ['error', 'invalid_geometry'])
def test_failed_prediction_never_retains_success_measurement(tmp_path, status):
    store, sid, cid, token, labels = setup(tmp_path)
    store.record_prediction(cid, '0', dict(status=status, measurement={'vertical_cdr': .99}),
                            labels, claim_token=token)
    pred = store.cases(sid)[0]['predictions'][0]
    assert pred['status'] == status and pred['measurement'] is None


@pytest.mark.parametrize('errors', ['not-a-list', [123], None])
def test_malformed_error_metadata_is_rejected_before_artifact_write(tmp_path, errors):
    store, sid, cid, token, labels = setup(tmp_path)
    with pytest.raises(ValueError, match='errors'):
        store.record_prediction(cid, '0', dict(status='ok', errors=errors), labels, claim_token=token)
    assert store.cases(sid)[0]['predictions'] == []
