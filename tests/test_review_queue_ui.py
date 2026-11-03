from test_seg_contract import _page, _text


def test_queue_empty_state_is_honest_and_local(tmp_path, monkeypatch):
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    text = _text(app) + ' '.join(x.value for x in app.info)
    assert 'Review Queue' in text
    assert 'No review sessions' in text
    assert 'two verified' in text.lower()
    assert 'Research' in text


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
