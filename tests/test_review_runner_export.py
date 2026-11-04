"""Runner and shareable export contracts (synthetic mechanics only)."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import numpy as np
from PIL import Image
import pytest


class MemoryStore:
    def __init__(self, root):
        self.root = root
        image = Image.new('RGB', (4, 4), 'red')
        image.save(root / 'input.png')
        self.data = dict(id='case-1', input_path=root / 'input.png', original_name='PRIVATE-patient.png',
                         pixel_sha256=hashlib.sha256(json.dumps({'size':image.size,'mode':'RGB'},sort_keys=True).encode()+image.tobytes()).hexdigest(), status='pending',
                         predictions=[], review_state='unreviewed', revision=0, reasons=[],
                         note='PRIVATE note', prediction_set_hash=None, priority={'group':'pending','score':None})
        self.models = [dict(folder=str(root / str(i)), identity=str(i), run_id='run'+str(i), weights_sha256='w'+str(i)) for i in range(2)]
        self.history = [{'action':'create', 'actor_local_alias':'PRIVATE actor', 'note':'PRIVATE event'}]
    def session(self, sid):
        return {'id':sid, 'models':self.models, 'software_commit':'commit', 'input_modality':'color_fundus'}
    def cases(self, sid): return [self.data]
    def events(self, sid): return self.history
    def snapshot(self, sid): return copy.deepcopy({'session':self.session(sid), 'cases':self.cases(sid), 'events':self.events(sid)})
    def publish_export(self, sid, temporary, target): temporary.replace(target)
    def claim(self, cid): self.data['status']='processing'
    def record_prediction(self, cid, identity, prediction, labels):
        self.data['predictions'].append(dict(prediction, model_identity=identity))
    def finish(self, cid, error=None):
        self.data['status']='error' if error else 'complete'
        self.data['error']=error


def test_runner_retains_both_model_outcomes_and_only_passes_image(tmp_path):
    from hyunoptic.review.runner import run_next
    store = MemoryStore(tmp_path)
    def factory(model):
        def predict(image):
            assert isinstance(image, Image.Image)
            if model['identity']=='1': raise RuntimeError('model failed')
            return SimpleNamespace(status='invalid_geometry', labels=np.zeros((4,4), np.uint8),
                                   errors=['empty cup'], measurement=None, preprocessing={})
        return SimpleNamespace(predict=predict)
    assert run_next(store, 'session', factory)
    assert [p['status'] for p in store.data['predictions']]==['invalid_geometry','error']
    assert store.data['status']=='error'
    assert not run_next(store, 'session', factory)


def test_default_runner_rejects_changed_identity_before_loading_predictor(tmp_path, monkeypatch):
    from hyunoptic.review import runner
    store = MemoryStore(tmp_path)
    monkeypatch.setattr(runner, 'verify_bundle', lambda folder: SimpleNamespace(identity='changed'))
    assert runner.run_next(store, 'session')
    assert store.data['status']=='error'
    assert store.data['predictions']==[]
    assert 'identity' in store.data['error'].lower()


def test_export_is_private_deterministic_and_preserves_missing_values(tmp_path):
    from hyunoptic.review.export import export_session, verify_export
    store = MemoryStore(tmp_path)
    store.data['status']='error'
    store.data['predictions']=[dict(model_identity='0', status='error', measurement=None, errors=['PRIVATE filename'], run_id='=HYPERLINK("x")')]
    store.models[0]['run_id']='=HYPERLINK("x")'
    first = export_session(store, 'session', tmp_path/'one.zip')
    second = export_session(store, 'session', tmp_path/'two.zip')
    assert first.read_bytes()==second.read_bytes()
    assert verify_export(first)['valid']
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist())=={'manifest.json','session.json','cases.csv','predictions.csv','reviews.csv','events.jsonl','summary.html'}
        content = b''.join(archive.read(n) for n in archive.namelist())
        assert b'PRIVATE' not in content
        assert str(tmp_path).encode() not in content
        predictions=list(csv.DictReader(io.StringIO(archive.read('predictions.csv').decode())))
        assert predictions[0]['status']=='error'
        assert predictions[0]['vertical_cdr']==''
        assert b'no_reference' in content
        assert b"'=HYPERLINK" in content


@pytest.mark.parametrize('corruption', ['tamper','missing','traversal','duplicate','extra'])
def test_verify_rejects_invalid_packages(tmp_path, corruption):
    from hyunoptic.review.export import export_session, verify_export
    good=export_session(MemoryStore(tmp_path), 'session', tmp_path/'good.zip')
    with zipfile.ZipFile(good) as archive: members={n:archive.read(n) for n in archive.namelist()}
    if corruption=='tamper': members['cases.csv']+=b'changed'
    if corruption=='missing': members.pop('cases.csv')
    if corruption=='traversal': members['../outside']=b'x'
    if corruption=='extra': members['extra.txt']=b'x'
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as archive:
        for name,data in members.items(): archive.writestr(name,data)
        if corruption=='duplicate':
            with pytest.warns(UserWarning, match='Duplicate name'):
                archive.writestr('cases.csv',members['cases.csv'])
    with pytest.raises(ValueError): verify_export(bad)

def _input_bytes(color='red'):
    stream = io.BytesIO()
    Image.new('RGB', (4, 4), color).save(stream, format='PNG')
    return stream.getvalue()


def test_real_store_default_adapter_recovers_partial_case_and_preserves_review_history(tmp_path, monkeypatch):
    from hyunoptic.review.store import ReviewStore
    from hyunoptic.review import runner
    from hyunoptic.review.export import export_session, verify_export
    store=ReviewStore(tmp_path/'store')
    models=[dict(folder=str(tmp_path/str(i)), identity=str(i), run_id='run'+str(i), weights_sha256='w'+str(i)) for i in range(2)]
    sid=store.create_session([('PRIVATE-patient.png',_input_bytes())],models)
    case=store.cases(sid)[0]
    labels=np.ones((4,4),dtype=np.uint8)
    labels[1:3,1:3]=2
    store.claim(case['id'])
    store.record_prediction(case['id'], '0', dict(status='ok',measurement={'vertical_cdr':.5},errors=[]),labels)
    store.recover(sid)
    monkeypatch.setattr(runner, 'verify_bundle', lambda folder: SimpleNamespace(identity=Path(folder).name))
    monkeypatch.setattr(runner, '_default_predictor', lambda bundle: SimpleNamespace(predict=lambda image: SimpleNamespace(
        status='ok', labels=labels, measurement={'vertical_cdr':.5}, errors=[], preprocessing={})))
    assert runner.run_next(store,sid)
    final=store.cases(sid)[0]
    assert final['status']=='complete'
    assert len(final['predictions'])==2
    assert not runner.run_next(store,sid)
    store.decide(case['id'],'held',['boundary_mismatch'],'PRIVATE note',expected_revision=0)
    export=export_session(store,sid,tmp_path/'review.zip')
    assert verify_export(export)['valid']
    with zipfile.ZipFile(export) as archive:
        assert b'PRIVATE' not in b''.join(archive.read(n) for n in archive.namelist())
        events=[json.loads(line) for line in archive.read('events.jsonl').splitlines()]
        decision=next(e for e in events if e['action']=='review_changed')
        assert decision['new_state']=='held'
    assert any(e['action']=='interrupted' for e in store.events(sid))


def test_runner_changed_bundle_preserves_partial_prediction_and_history(tmp_path, monkeypatch):
    from hyunoptic.review.store import ReviewStore
    from hyunoptic.review import runner
    store=ReviewStore(tmp_path/'store')
    models=[dict(folder=str(i),identity=str(i),run_id=str(i),weights_sha256=str(i)) for i in range(2)]
    sid=store.create_session([('input.png',_input_bytes())],models)
    cid=store.cases(sid)[0]['id']
    store.claim(cid)
    store.record_prediction(cid,'0',dict(status='invalid_geometry'),np.zeros((4,4),np.uint8))
    store.recover(sid)
    original=store.cases(sid)[0]['predictions']
    history=store.events(sid)
    monkeypatch.setattr(runner,'verify_bundle',lambda folder:SimpleNamespace(identity='changed'))
    assert runner.run_next(store,sid)
    final=store.cases(sid)[0]
    assert final['status']=='error'
    assert final['predictions']==original
    assert store.events(sid)[:len(history)]==history


def test_export_escapes_html_and_csv_formula_prefixes(tmp_path):
    from hyunoptic.review.export import export_session
    store=MemoryStore(tmp_path)
    store.data['id']='<script>alert(1)</script>'
    store.data['review_state']='=SUM(1,2)'
    path=export_session(store,'session',tmp_path/'export.zip')
    with zipfile.ZipFile(path) as archive:
        summary=archive.read('summary.html').decode()
        assert '<script>' not in summary
        assert '&lt;script&gt;' in summary
        rows=list(csv.DictReader(io.StringIO(archive.read('reviews.csv').decode())))
        assert rows[0]['state']=="'=SUM(1,2)"


def test_verify_rejects_oversized_member_without_reading_it(tmp_path,monkeypatch):
    from hyunoptic.review import export
    package=export.export_session(MemoryStore(tmp_path),'session',tmp_path/'export.zip')
    monkeypatch.setattr(export,'MAX_MEMBER_BYTES',10)
    with pytest.raises(ValueError,match='oversized'):
        export.verify_export(package)

def test_runner_does_not_process_a_claim_that_already_completed(tmp_path):
    from hyunoptic.review.runner import run_next
    store=MemoryStore(tmp_path)
    store.claim=lambda cid:False
    def factory(model):
        pytest.fail('Completed claim must not run another prediction')
    assert not run_next(store,'session',factory)
    assert not store.data['predictions']


@pytest.mark.parametrize('corruption',['manifest_duplicate','manifest_path','symlink'])
def test_verify_rejects_manifest_ambiguity_and_symbolic_links(tmp_path,corruption):
    from hyunoptic.review.export import export_session,verify_export
    good=export_session(MemoryStore(tmp_path),'session',tmp_path/'good.zip')
    with zipfile.ZipFile(good) as archive: members={n:archive.read(n) for n in archive.namelist()}
    manifest=json.loads(members['manifest.json'])
    if corruption=='manifest_duplicate': manifest['files'][1]=manifest['files'][0]
    if corruption=='manifest_path': manifest['files'][0]['name']='../cases.csv'
    members['manifest.json']=json.dumps(manifest).encode()
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as archive:
        for name,data in members.items():
            info=zipfile.ZipInfo(name)
            if corruption=='symlink' and name=='cases.csv': info.external_attr=0o120777<<16
            archive.writestr(info,data)
    with pytest.raises(ValueError): verify_export(bad)


def test_export_verification_cli_and_import_do_not_require_torch(tmp_path):
    import subprocess
    import sys
    from hyunoptic.review.export import export_session
    good=export_session(MemoryStore(tmp_path),'session',tmp_path/'good.zip')
    result=subprocess.run([sys.executable,'-m','hyunoptic.review.export',str(good)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['valid']
    imported=subprocess.run([sys.executable,'-c',
        "import sys; import hyunoptic.review.runner, hyunoptic.review.export; assert 'torch' not in sys.modules"],capture_output=True,text=True)
    assert imported.returncode==0,imported.stderr

def test_runner_uses_bounded_pending_lookup_and_persists_input_integrity_failure(tmp_path):
    from hyunoptic.review.store import ReviewStore
    from hyunoptic.review.runner import run_next
    store=ReviewStore(tmp_path/'store')
    models=[dict(folder=str(i),identity=str(i),run_id=str(i),weights_sha256=str(i)) for i in range(2)]
    sid=store.create_session([('input.png',_input_bytes())],models)
    case=store.cases(sid)[0]
    Path(case['input_path']).write_bytes(_input_bytes('blue'))
    def no_full_scan(sid):
        pytest.fail('Runner must query just the next pending case')
    store.cases=no_full_scan
    assert run_next(store,sid,lambda model:pytest.fail('Corrupt inputs cannot run'))
    assert not run_next(store,sid,lambda model:pytest.fail('Failed input should remain visible without looping'))
    del store.cases
    assert store.cases(sid)[0]['status']=='error'
