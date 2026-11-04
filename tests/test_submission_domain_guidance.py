"""Known color-fundus ROI failure must remain visible beside usable geometry."""
from test_seg_contract import _page, _text
from test_review_queue_ui import _seed_session


def test_color_fundus_session_keeps_roi_limit_visible(tmp_path, monkeypatch):
    store, sid, _ = _seed_session(tmp_path)
    assert store.session(sid)['modality'] == 'color_fundus'
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    assert not app.exception
    assert any('ROI' in warning.value for warning in app.warning)
    assert '2026-11-04-full-real-validation' in _text(app)
    assert '160/174' in _text(app) and '132/174' in _text(app)


def test_measurable_geometry_is_not_presented_as_verified_accuracy(tmp_path, monkeypatch):
    store, sid, _ = _seed_session(tmp_path)
    app = _page(monkeypatch, tmp_path, 'model_review_queue', models_dir=str(tmp_path / 'missing'))
    assert not app.exception
    assert 'measurable geometry' in _text(app).lower()
    assert 'accuracy unverified' in _text(app).lower()
    assert all(p['status'] == 'ok' for p in store.cases(sid)[0]['predictions'])
