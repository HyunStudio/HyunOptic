import io
import sqlite3

import numpy as np
import pytest
from PIL import Image

from hyunoptic.review.store import ReviewStore
from hyunoptic.review.priority import priority


def image_bytes(mode='RGB'):
    stream = io.BytesIO()
    Image.new(mode, (8, 6)).save(stream, format='PNG')
    return stream.getvalue()


MODELS = [dict(folder='private/a', identity='a', run_id='a', weights_sha256='a'*64),
          dict(folder='private/b', identity='b', run_id='b', weights_sha256='b'*64)]


def setup_case(tmp_path):
    store = ReviewStore(tmp_path)
    sid = store.create_session([('../../secret.png', image_bytes())], MODELS)
    return store, sid, store.cases(sid)[0]['id']


def complete(store, cid):
    store.claim(cid)
    labels = np.zeros((6, 8), dtype=np.uint8)
    labels[1:5, 2:6] = 1
    labels[2:4, 3:5] = 2
    for model in MODELS:
        store.record_prediction(cid, model['identity'], dict(status='ok', measurement={'vcdr': .5}, errors=[], **{k:model[k] for k in ('run_id', 'weights_sha256')}), labels)
    store.finish(cid)


def test_copy_bad_inputs_persist_and_limits(tmp_path):
    store = ReviewStore(tmp_path)
    sid = store.create_session([('../../secret.png', image_bytes()), ('bad.png', b'broken'), ('rgba.png', image_bytes('RGBA'))], MODELS)
    cases = ReviewStore(tmp_path).cases(sid)
    assert len(cases) == 3
    assert [c['status'] for c in cases] == ['pending', 'error', 'error']
    assert cases[0]['input_path'].is_file()
    assert cases[0]['input_path'].is_relative_to(tmp_path)
    assert cases[0]['pixel_sha256']
    assert cases[1]['error'] and cases[2]['error']
    with pytest.raises(ValueError):
        store.create_session([('x', b'')]*501, MODELS)
    with pytest.raises(ValueError):
        store.create_session([('x', b'')], [MODELS[0], MODELS[0]])


def test_revision_and_prediction_identity(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    assert case['prediction_set_hash'] and case['priority']['score'] == 0
    store.decide(cid, 'reviewed', [], '', case['revision'])
    with pytest.raises(ValueError, match='revision'):
        store.decide(cid, 'held', ['image_quality'], '', case['revision'])
    current = store.cases(sid)[0]
    with pytest.raises(ValueError):
        store.decide(cid, 'held', [], '', current['revision'])
    with pytest.raises(ValueError):
        store.decide(cid, 'held', ['other'], '', current['revision'])
    store.record_prediction(cid, 'a', dict(status='error', errors=['failure']), None)
    changed = store.cases(sid)[0]
    assert changed['review_state'] == 'unreviewed' and not changed['prediction_set_hash']
    assert len(store.events(sid)) >= 3


def test_recovery_preserves_prediction_error_and_interruption(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    store.claim(cid)
    store.record_prediction(cid, 'a', dict(status='error', errors=['model failed']), None)
    resumed = ReviewStore(tmp_path)
    resumed.recover(sid)
    case = resumed.cases(sid)[0]
    assert case['status'] == 'pending' and 'interrupt' in case['error'].lower()
    assert case['predictions'][0]['errors'] == ['model failed']


def test_tampered_evidence_cannot_be_reviewed(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    case['predictions'][0]['labels_path'].write_bytes(b'tampered')
    with pytest.raises(ValueError):
        store.decide(cid, 'reviewed', [], '', case['revision'])
    assert store.cases(sid)[0]['priority']['group'] == 'error'


def test_replaced_input_rejects_claim_and_decision(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    case['input_path'].write_bytes(image_bytes('L'))
    with pytest.raises(ValueError):
        store.decide(cid, 'reviewed', [], '', case['revision'])


def test_priority_invalid_geometry_precedes_disagreement(tmp_path):
    assert priority([dict(status='invalid_geometry'), dict(status='ok')])['group'] == 'invalid_geometry'
    assert priority([dict(status='error'), dict(status='invalid_geometry')])['group'] == 'error'


def test_schema_refuses_future_database(tmp_path):
    ReviewStore(tmp_path)
    with sqlite3.connect(tmp_path / 'review.sqlite3') as db:
        db.execute('PRAGMA user_version = 999')
    with pytest.raises(ValueError, match='schema'):
        ReviewStore(tmp_path)


def test_failed_event_insert_rolls_back_review(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    with sqlite3.connect(store.db_path) as db:
        db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
    with pytest.raises(sqlite3.Error):
        store.decide(cid, 'reviewed', [], '', case['revision'])
    restored = ReviewStore(tmp_path).cases(sid)[0]
    assert restored['review_state'] == 'unreviewed'
    assert restored['revision'] == case['revision']


def test_recovery_quarantines_orphan_never_adopts_it(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    orphan = tmp_path / sid / 'predictions' / 'orphan.png'
    orphan.parent.mkdir()
    orphan.write_bytes(image_bytes())
    temporary = orphan.with_suffix('.tmp')
    temporary.write_bytes(b'partial')
    store.recover(sid)
    assert not orphan.exists() and not temporary.exists()
    assert len(list((tmp_path / sid / 'quarantine').iterdir())) == 2
    assert not store.cases(sid)[0]['predictions']


def test_reviewed_tampered_case_shows_unreviewed(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    store.decide(cid, 'reviewed', [], '', case['revision'])
    case['predictions'][0]['labels_path'].unlink()
    assert store.cases(sid)[0]['review_state'] == 'unreviewed'


def test_unversioned_existing_database_is_not_overwritten(tmp_path):
    with sqlite3.connect(tmp_path / 'review.sqlite3') as db:
        db.execute('CREATE TABLE unrelated (x TEXT)')
    with pytest.raises(ValueError, match='schema'):
        ReviewStore(tmp_path)


def test_empty_masks_are_geometry_invalid_and_disagreement_uses_full_size(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    store.claim(cid)
    first = np.ones((6, 8), dtype=np.uint8)
    first[2:4, 3:5] = 2
    second = first.copy()
    second[2:4, 3:5] = 1
    second[0:2, 0:2] = 2
    store.record_prediction(cid, 'a', dict(status='ok'), first)
    store.record_prediction(cid, 'b', dict(status='ok'), second)
    store.finish(cid)
    case = store.cases(sid)[0]
    assert case['priority']['score'] == 1
    store.record_prediction(cid, 'b', dict(status='ok'), np.zeros_like(first))
    store.finish(cid)
    assert store.cases(sid)[0]['priority']['group'] == 'invalid_geometry'


def test_limits_and_delete_are_explicit_and_safe(tmp_path, monkeypatch):
    from hyunoptic.review import inputs
    monkeypatch.setattr(inputs, 'MAX_FILE_BYTES', 4)
    store = ReviewStore(tmp_path)
    with pytest.raises(ValueError, match='30 MB'):
        store.create_session([('big', b'12345')], MODELS)
    monkeypatch.setattr(inputs, 'MAX_FILE_BYTES', 30*1024**2)
    monkeypatch.setattr(inputs, 'MAX_TOTAL_BYTES', 4)
    with pytest.raises(ValueError, match='2 GB'):
        store.create_session([('big', b'12345')], MODELS)
    monkeypatch.setattr(inputs, 'MAX_TOTAL_BYTES', 2*1024**3)
    sid = store.create_session([('gray', image_bytes('L'))], MODELS)
    assert store.cases(sid)[0]['status'] == 'pending'
    with pytest.raises(ValueError):
        store.delete_session('../outside')
    store.delete_session(sid)
    assert not store.sessions() and not (tmp_path / sid).exists()


def test_priority_reports_actual_measurement_vertical_cdr(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    predictions = case['predictions']
    predictions[0]['measurement'] = {'vertical_cdr': .25}
    predictions[1]['measurement'] = {'vertical_cdr': .75}
    assert priority(predictions)['vcdr_delta'] == .5


def test_held_rejects_empty_reason_string(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    with pytest.raises(ValueError):
        store.decide(cid, 'held', [''], '', case['revision'])


def test_next_pending_selects_only_unfinished_case(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    assert store.next_pending(sid)['id'] == cid
    complete(store, cid)
    assert store.next_pending(sid) is None


def test_review_reason_allowlist_and_managed_export_deletion(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    case = store.cases(sid)[0]
    with pytest.raises(ValueError, match='reason'):
        store.decide(cid, 'held', ['private patient identifier'], '', case['revision'])
    export = tmp_path / 'exports' / f'{sid}.zip'
    export.parent.mkdir()
    export.write_bytes(b'local export')
    store.delete_session(sid)
    assert not export.exists()
def test_retry_error_preserves_failure_event(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    store.claim(cid)
    store.finish(cid, error='Temporary unavailable model')
    before = len(store.events(sid))
    store.retry(cid)
    row = store.cases(sid)[0]
    assert row['status'] == 'pending'
    assert len(store.events(sid)) > before
    assert any(e.get('error') == 'Temporary unavailable model' for e in store.events(sid))


def test_recovered_claim_rejects_old_worker(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    old_token = store.claim(cid)
    store.recover(sid)
    current_token = store.claim(cid)
    assert old_token != current_token
    with pytest.raises(ValueError, match='claim'):
        store.record_prediction(cid, 'a', dict(status='error'), None, claim_token=old_token)
    with pytest.raises(ValueError, match='claim'):
        store.finish(cid, error='stale worker failure', claim_token=old_token)
    assert store.cases(sid)[0]['status'] == 'processing'


def test_changed_input_hides_derived_predictions(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    row = store.cases(sid)[0]
    row['input_path'].write_bytes(b'changed source')
    invalid = store.cases(sid)[0]
    assert invalid['status'] == 'error'
    assert invalid['predictions'] == []
    assert invalid['integrity_error'] is True
