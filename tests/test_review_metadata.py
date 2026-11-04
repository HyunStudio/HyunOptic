"""Recorded metadata is cheap; selected evidence remains byte verified."""
import csv
import io
import json
from pathlib import Path
import zipfile

import pytest

from hyunoptic.review.export import export_session
from test_review_store import MODELS, complete, image_bytes, setup_case


def test_metadata_never_reads_or_resolves_evidence(tmp_path, monkeypatch):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    def forbidden(*args, **kwargs):
        raise AssertionError('metadata touched evidence')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(store, '_path', forbidden)
    rows = store.list_case_metadata(sid)
    assert len(rows) == 1 and rows[0]['id'] == cid
    assert rows[0]['priority']['score'] == 0
    assert rows[0]['priority_verification'] == 'recorded'
    assert rows[0]['evidence_verification'] == 'not_checked'
    assert 'input_path' not in rows[0] and 'predictions' not in rows[0]


def test_verified_detail_returns_exact_bytes_and_only_reads_selected_case(tmp_path, monkeypatch):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    other_sid = store.create_session([('other.png', image_bytes())], MODELS)
    other_cid = store.cases(other_sid)[0]['id']
    original = Path.read_bytes
    reads = []
    def counted(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', counted)
    row = store.verified_case(sid, cid)
    assert row['source_bytes'] == image_bytes()
    assert all(p['labels_bytes'].startswith(b'\x89PNG') for p in row['predictions'])
    assert len(reads) == 3 and len(set(reads)) == 3
    with pytest.raises(ValueError, match='session'):
        store.verified_case(sid, other_cid)
    assert len(reads) == 3


@pytest.mark.parametrize('artifact', ['input', 'mask'])
def test_metadata_does_not_claim_tamper_detection_but_detail_save_export_reject_it(tmp_path, artifact):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    row = store.cases(sid)[0]
    store.decide(cid, 'reviewed', [], '', row['revision'])
    path = row['input_path'] if artifact == 'input' else row['predictions'][0]['labels_path']
    path.write_bytes(b'tampered')
    metadata = store.list_case_metadata(sid)[0]
    assert metadata['status'] == 'complete' and metadata['review_state'] == 'reviewed'
    assert metadata['evidence_verification'] == 'not_checked'
    detail = store.verified_case(sid, cid)
    assert detail['integrity_error'] and detail['predictions'] == []
    assert not detail.get('source_bytes') and detail['review_state'] == 'unreviewed'
    with pytest.raises(ValueError, match='hash mismatch'):
        store.decide(cid, 'reviewed', [], '', row['revision'] + 1)
    target = export_session(store, sid, tmp_path / 'public.zip')
    with zipfile.ZipFile(target) as archive:
        cases = list(csv.DictReader(io.StringIO(archive.read('cases.csv').decode())))
        reviews = list(csv.DictReader(io.StringIO(archive.read('reviews.csv').decode())))
    assert cases[0]['status'] == 'error' and cases[0]['prediction_count'] == '0'
    assert reviews[0]['state'] == 'unreviewed'


def test_metadata_priority_binding_legacy_and_fresh_decisions(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    row = store.list_case_metadata(sid)[0]
    store.decide(cid, 'held', ['uncertain'], '', row['revision'])
    current = store.list_case_metadata(sid)[0]
    assert current['review_state'] == 'held' and current['revision'] == 1
    with store._db(write=True) as db:
        case = store._case(db, cid)
        case['prediction_set_hash'] = 'changed'
        store._save_case(db, case)
    unverified = store.list_case_metadata(sid)[0]
    assert unverified['priority']['group'] == 'pending'
    assert unverified['priority_verification'] == 'unverified'
    with store._db(write=True) as db:
        case = store._case(db, cid)
        case.pop('recorded_priority', None)
        store._save_case(db, case)
    assert store.list_case_metadata(sid)[0]['priority_verification'] == 'unverified'


def test_prediction_invalidation_and_recovery_clear_recorded_priority(tmp_path):
    store, sid, cid = setup_case(tmp_path)
    complete(store, cid)
    store.record_prediction(cid, 'a', dict(status='error', errors=['temporary']), None)
    assert store.list_case_metadata(sid)[0]['priority_verification'] == 'unverified'
    store.recover(sid)
    assert store.list_case_metadata(sid)[0]['priority_verification'] == 'unverified'
    store.claim(cid)
    store.finish(cid, error='temporary')
    assert store.list_case_metadata(sid)[0]['priority_verification'] == 'recorded'
    store.retry(cid)
    assert store.list_case_metadata(sid)[0]['priority_verification'] == 'unverified'


@pytest.mark.parametrize('legacy', [False, True])
def test_session_export_preserves_software_version_when_git_is_unknown(tmp_path, legacy):
    from hyunoptic import __version__
    store, sid, cid = setup_case(tmp_path)
    assert store.session(sid)['software_commit'] == 'unknown'
    assert store.session(sid).get('software_version') == __version__
    if legacy:
        with store._db(write=True) as db:
            session = store._session(db, sid)
            session.pop('software_version')
            db.execute('UPDATE sessions SET data=? WHERE id=?', (json.dumps(session), sid))
    path = export_session(store, sid, tmp_path / 'versioned.zip')
    with zipfile.ZipFile(path) as archive:
        public = json.loads(archive.read('session.json'))
    assert public['software_commit'] == 'unknown'
    assert public['software_version'] == ('unknown' if legacy else __version__)
