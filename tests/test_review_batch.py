"""Synthetic 100-case recovery/inventory check, not a model accuracy benchmark."""
import io
from types import SimpleNamespace

import numpy as np
from PIL import Image

from hyunoptic.review.export import export_session, verify_export
from hyunoptic.review.runner import run_next
from hyunoptic.review.store import ReviewStore


def test_hundred_case_batch_preserves_review_and_failure_on_resume(tmp_path):
    stream = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(stream, format='PNG')
    models = [dict(identity=str(i), folder=str(tmp_path / str(i)), run_id=str(i), weights_sha256=str(i)) for i in range(2)]
    store = ReviewStore(tmp_path / 'review')
    sid = store.create_session([(f'{i}.png', stream.getvalue()) for i in range(99)] + [('bad.png', b'bad')], models)
    labels = np.zeros((8, 8), dtype=np.uint8)
    labels[1:7, 1:7] = 1
    labels[3:5, 3:5] = 2

    def factory(model):
        result = SimpleNamespace(status='ok', measurement={'vertical_cdr': .333}, errors=[],
                                 preprocessing={}, run_id=model['run_id'], weights_sha256=model['weights_sha256'], labels=labels)
        return SimpleNamespace(predict=lambda image: result)

    for _ in range(5):
        assert run_next(store, sid, predictor_factory=factory)
    complete = next(c for c in store.cases(sid) if c['status'] == 'complete')
    store.decide(complete['id'], 'held', ['uncertain'], '', complete['revision'])
    interrupted = store.next_pending(sid)
    store.claim(interrupted['id'])
    store = ReviewStore(store.root)
    store.recover(sid)
    while run_next(store, sid, predictor_factory=factory):
        pass
    cases = store.cases(sid)
    assert len(cases) == 100
    assert sum(c['status'] == 'complete' for c in cases) == 99
    assert sum(c['status'] == 'error' for c in cases) == 1
    assert sum(len(c['predictions']) for c in cases) == 198
    assert next(c for c in cases if c['id'] == complete['id'])['review_state'] == 'held'
    assert verify_export(export_session(store, sid, tmp_path / 'batch.zip'))['valid']
