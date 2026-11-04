"""Synthetic regression checks for review navigation, terminal errors and consent."""
import io
from PIL import Image
import pytest
from test_seg_contract import _page
from test_review_queue_ui import _seed_session
from hyunoptic.review.store import ReviewStore


def session(tmp_path, count=1, broken=False):
    store = ReviewStore(tmp_path / '.hyunoptic' / 'review')
    stream=io.BytesIO(); Image.new('RGB',(32,32),'red').save(stream,format='PNG')
    models=[dict(folder=str(i),identity=str(i),run_id=f'run{i}',weights_sha256=str(i)) for i in range(2)]
    sid=store.create_session([(f'input-{i}.png',b'broken' if broken else stream.getvalue()) for i in range(count)],models)
    return store,sid


def checkbox(app):
    return next(c for c in app.checkbox if c.label.startswith('Delete this session'))


def button(app,label):
    return next(b for b in app.button if b.label==label)


@pytest.mark.parametrize('transition',['delete','switch_back'])
def test_delete_consent_resets_on_session_transition(tmp_path,monkeypatch,transition):
    store,a=session(tmp_path); _,b=session(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    checkbox(app).check().run()
    if transition=='delete':
        button(app,'Delete local session').click().run()
        assert len(store.sessions())==1
    else:
        app.selectbox(key='rq_session').select(b).run()
        app.selectbox(key='rq_session').select(a).run()
    assert not app.exception
    assert checkbox(app).value is False
    assert button(app,'Delete local session').disabled


def test_deletion_failure_is_visible_and_retains_session(tmp_path,monkeypatch):
    store,sid=session(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    def fail(*args):raise OSError('simulated removal failure')
    monkeypatch.setattr(ReviewStore,'delete_session',fail)
    checkbox(app).check().run(); button(app,'Delete local session').click().run()
    assert not app.exception
    assert len(store.sessions())==1 and app.selectbox(key='rq_session').value==sid
    assert any('removal failure' in e.value for e in app.error)


def test_unsupported_input_has_one_terminal_message_and_no_retry(tmp_path,monkeypatch):
    session(tmp_path,broken=True)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception
    assert not any(b.label=='Retry failed case' for b in app.button)
    assert len(app.error)==1
    assert 'Unsupported input' in app.error[0].value


def test_supported_operational_failure_still_offers_retry(tmp_path,monkeypatch):
    store,sid=session(tmp_path)
    cid=store.cases(sid)[0]['id']; token=store.claim(cid)
    store.finish(cid,error='model temporarily unavailable',claim_token=token)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    button(app,'Retry failed case').click().run()
    assert not app.exception
    assert store.cases(sid)[0]['status']=='pending'


def completed_pair(tmp_path):
    import numpy as np
    store,sid=session(tmp_path,2)
    rows=store.cases(sid)
    for row in rows:
        token=store.claim(row['id']); labels=np.zeros((32,32),dtype=np.uint8)
        labels[5:25,5:25]=1; labels[10:20,10:20]=2
        for model in store.session(sid)['models']:
            store.record_prediction(row['id'],model['identity'],dict(status='ok',errors=[]),labels,claim_token=token)
        store.finish(row['id'],claim_token=token)
    return store,sid,[r['id'] for r in rows]


def test_save_next_advances_only_after_success(tmp_path,monkeypatch):
    store,sid,ids=completed_pair(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    next(x for x in app.selectbox if x.label.startswith('Review record')).select('reviewed')
    button(app,'Save and next case').click().run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label=='Inspect case').value==ids[1]
    assert store.cases(sid)[0]['review_state']=='reviewed'
    next(x for x in app.selectbox if x.label.startswith('Review record')).select('reviewed')
    button(app,'Save and next case').click().run()
    assert not app.exception
    assert any('No later eligible' in x.value for x in app.success)


def test_stale_save_next_keeps_selection(tmp_path,monkeypatch):
    store,sid,ids=completed_pair(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    store.decide(ids[0],'reviewed',[],'',0)
    button(app,'Save and next case').click().run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label=='Inspect case').value==ids[0]
    assert any('conflict' in x.value.lower() for x in app.error)


def test_case_names_are_local_opt_in_and_default_stable_labels(tmp_path,monkeypatch):
    store,sid,cid=_seed_session(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    select=next(x for x in app.selectbox if x.label=='Inspect case')
    assert select.options==['Case 001']
    assert 'private.png' not in str(app.dataframe[0].value)
    next(x for x in app.toggle if x.label=='Show local filenames').set_value(True).run()
    select=next(x for x in app.selectbox if x.label=='Inspect case')
    assert 'private.png' in select.options[0]


def test_save_next_respects_unreviewed_filter_after_saved_case_disappears(tmp_path,monkeypatch):
    store,sid,ids=completed_pair(tmp_path)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    next(x for x in app.selectbox if x.label=='Show cases').select('Unreviewed').run()
    next(x for x in app.selectbox if x.label.startswith('Review record')).select('reviewed')
    button(app,'Save and next case').click().run()
    assert not app.exception
    selected=next(x for x in app.selectbox if x.label=='Inspect case')
    assert selected.value==ids[1] and selected.options==['Case 002']


def test_ui_uses_metadata_and_one_verified_detail(tmp_path,monkeypatch):
    store,sid,ids=completed_pair(tmp_path)
    def strict_all_forbidden(*args):raise AssertionError('UI scanned all artifacts')
    monkeypatch.setattr(ReviewStore,'cases',strict_all_forbidden)
    calls=[]; original=ReviewStore.verified_case
    def observed(self,session_id,case_id):
        calls.append(case_id)
        return original(self,session_id,case_id)
    monkeypatch.setattr(ReviewStore,'verified_case',observed)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception and calls==[ids[0]]


def test_missing_primary_prediction_keeps_comparison_model_slot(tmp_path,monkeypatch):
    import numpy as np
    store,sid=session(tmp_path)
    cid=store.cases(sid)[0]['id']; token=store.claim(cid)
    labels=np.zeros((32,32),dtype=np.uint8);labels[5:25,5:25]=1;labels[10:20,10:20]=2
    store.record_prediction(cid,'1',dict(status='ok',errors=[]),labels,claim_token=token)
    store.finish(cid,claim_token=token)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception
    text=' '.join(x.value for x in app.markdown)
    assert '**Primary model**' in text and '**Comparison model**' in text
    assert any('No prediction recorded' in x.value for x in app.info)
    assert any(x.value=='run1' for x in app.caption)
