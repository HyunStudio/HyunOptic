"""Bounded, image-only processing; importing this module never imports PyTorch."""
from __future__ import annotations

from pathlib import Path

from ..seg.bundle import verify_bundle


def _default_predictor(bundle):
    from ..seg.inference import Predictor
    return Predictor(bundle)


def run_next(store, session_id: str, predictor_factory=None) -> bool:
    """Process one pending/interrupted case. Explicit factories accept model dictionaries.

    The default path reverifies every selected bundle before any inference. A supplied
    factory is a test adapter and can use synthetic model identities without bundles.
    Failed cases remain visible; retry is an explicit store recovery action.
    """
    if hasattr(store, 'next_pending'):
        pending = store.next_pending(session_id)
    else:
        pending = next((c for c in store.cases(session_id)
                        if c['status'] in {'pending', 'interrupted'}), None)
    if pending is None:
        return False
    case_id = pending['id']
    if pending['status'] == 'error':
        store.finish(case_id, error=pending.get('error') or 'Input evidence integrity failure')
        return True
    token = store.claim(case_id)
    if token is False:
        return False
    ownership = {'claim_token': token} if isinstance(token, str) else {}
    models = store.session(session_id)['models']
    try:
        bundles = []
        if predictor_factory is None:
            for model in models:
                bundle = verify_bundle(model['folder'])
                if bundle.identity != model['identity']:
                    raise ValueError('Model bundle identity changed; create a new session')
                bundles.append(bundle)
        # Decoding is separate from display settings and receives no reference data.
        from .inputs import decode_image, inspect_input
        data = Path(pending['input_path']).read_bytes()
        image = decode_image(data)
        if inspect_input(data)['pixel_sha256'] != pending['pixel_sha256']:
            raise ValueError('Input pixel identity changed; restore the input or create a new session')
    except Exception as exc:
        store.finish(case_id, error=str(exc), **ownership)
        return True
    errors = []
    for index, model in enumerate(models):
        labels = None
        try:
            predictor = (predictor_factory(model) if predictor_factory is not None
                         else _default_predictor(bundles[index]))
            result = predictor.predict(image.copy())
            labels = result.labels
            prediction = {key: getattr(result, key, default) for key, default in (
                ('status', 'error'), ('measurement', None), ('errors', []),
                ('preprocessing', {}), ('run_id', model['run_id']),
                ('weights_sha256', model['weights_sha256']))}
        except Exception as exc:
            prediction = dict(status='error', measurement=None, errors=[str(exc)],
                              preprocessing={}, run_id=model['run_id'],
                              weights_sha256=model['weights_sha256'])
        if prediction['status'] == 'error':
            errors.append(f"Model {index + 1} failed")
        # Store failures must propagate: do not pretend an unwritten result completed.
        store.record_prediction(case_id, model['identity'], prediction, labels, **ownership)
    store.finish(case_id, error='; '.join(errors) or None, **ownership)
    return True
