import pytest

from test_seg_contract import _page, _text


def test_queue_empty_state_is_honest_and_local(tmp_path, monkeypatch):
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    text = _text(app) + ' '.join(x.value for x in app.info)
    assert 'Review Queue' in text
    assert 'No review sessions' in text
    assert 'two verified' in text.lower()
    assert 'Research' in text


@pytest.mark.parametrize('check',['upload_limit','model_names'])
def test_creation_form_exposes_model_names_and_actual_upload_limit(tmp_path,monkeypatch,check):
    from pathlib import Path
    from types import SimpleNamespace
    import hyunoptic.seg.bundle as bundles
    folders=[Path('synthetic_42'),Path('synthetic_43')]
    # Bundle verification is tested separately; this checks the real rendered form.
    monkeypatch.setattr(bundles,'find_bundles',lambda _:folders)
    monkeypatch.setattr(bundles,'verify_bundle',lambda p:SimpleNamespace(run_id='run-'+p.name[-2:]))
    app=_page(monkeypatch,tmp_path,'model_review_queue')
    assert not app.exception
    if check=='upload_limit':
        assert app.get('file_uploader')[0].proto.max_upload_size_mb==30
    else:
        primary=next(x for x in app.selectbox if x.label=='Primary model')
        assert 'synthetic_42' in primary.options[0] and 'run-42' in primary.options[0]


def test_priority_ties_follow_input_order_not_random_case_uuid(tmp_path, monkeypatch):
    """Identical predictions must have the same queue order across imported sessions."""
    import io
    from uuid import UUID
    import numpy as np
    from PIL import Image
    import hyunoptic.review.store as module
    image = io.BytesIO()
    Image.new('RGB',(16,16),'red').save(image,format='PNG')
    store = module.ReviewStore(tmp_path / '.hyunoptic' / 'review')
    models = [dict(folder=str(i),identity=str(i),run_id=str(i),weights_sha256=str(i)) for i in range(2)]
    identifiers = (UUID(int=i) for i in range(1000, 0, -1))
    with monkeypatch.context() as context:
        context.setattr(module,'uuid4',lambda:next(identifiers))
        sid = store.create_session([('first.png',image.getvalue()),('second.png',image.getvalue())],models)
    labels = np.zeros((16,16),np.uint8)
    labels[2:14,2:14]=1
    labels[5:10,5:10]=2
    rows=store.cases(sid)
    for row in rows:
        token=store.claim(row['id'])
        for m in models:
            store.record_prediction(row['id'],m['identity'],dict(status='ok'),labels,claim_token=token)
        store.finish(row['id'],claim_token=token)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception
    selected=next(x for x in app.selectbox if x.label=='Inspect case')
    assert selected.options == ['Case 001', 'Case 002']
    assert selected.value == rows[0]['id']
    selected.select(rows[1]['id']).run()
    assert selected.value == rows[1]['id']


def _seed_session(tmp_path):
    import io
    import numpy as np
    from PIL import Image
    from hyunoptic.review.store import ReviewStore
    root = tmp_path / '.hyunoptic' / 'review'
    store = ReviewStore(root)
    image = io.BytesIO()
    Image.new('RGB', (32, 32), 'red').save(image, format='PNG')
    models = [dict(folder=str(tmp_path / str(i)), identity=str(i), run_id=f'test-{i}', weights_sha256=str(i)) for i in range(2)]
    sid = store.create_session([('private.png', image.getvalue())], models)
    case = store.cases(sid)[0]
    store.claim(case['id'])
    labels = np.zeros((32, 32), dtype=np.uint8)
    labels[5:25, 5:25] = 1
    labels[10:20, 10:20] = 2
    for model in models:
        store.record_prediction(case['id'], model['identity'], dict(status='ok', errors=[],
            measurement={'vertical_cdr': 0.5}, preprocessing={}, run_id=model['run_id'], weights_sha256=model['weights_sha256']), labels)
    store.finish(case['id'])
    return store, sid, case['id']


def test_queue_persistent_case_and_held_review(tmp_path, monkeypatch):
    from hyunoptic.review.store import ReviewStore
    store, sid, cid = _seed_session(tmp_path)
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    assert not app.exception
    state = next(x for x in app.selectbox if x.label.startswith('Review record'))
    state.select('held')
    next(x for x in app.multiselect if x.label.startswith('Reasons')).select('wrong_location')
    next(x for x in app.button if x.label == 'Save review record').click()
    app.run()
    assert not app.exception
    restored = ReviewStore(store.root).cases(sid)[0]
    assert restored['review_state'] == 'held'
    assert restored['reasons'] == ['wrong_location']


def test_stale_form_shows_explicit_conflict(tmp_path, monkeypatch):
    store, sid, cid = _seed_session(tmp_path)
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    next(x for x in app.selectbox if x.label.startswith('Review record')).select('held')
    next(x for x in app.multiselect if x.label.startswith('Reasons')).select('wrong_location')
    store.decide(cid, 'reviewed', [], '', 0)
    next(x for x in app.button if x.label == 'Save review record').click()
    app.run()
    assert not app.exception
    assert any('conflict' in x.value.lower() for x in app.error)
    assert store.cases(sid)[0]['review_state'] == 'reviewed'
