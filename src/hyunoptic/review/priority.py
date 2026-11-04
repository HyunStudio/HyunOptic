"""Deterministic image-only model disagreement; no reference annotations."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image

from .inputs import sha256


def priority(predictions: list[dict]) -> dict:
    result = {'group': 'pending', 'score': None, 'reasons': [], 'vcdr_delta': None}
    if any(p.get('status') == 'error' for p in predictions):
        return {**result, 'group': 'error', 'reasons': ['prediction_error']}
    if any(p.get('status') == 'invalid_geometry' for p in predictions):
        return {**result, 'group': 'invalid_geometry', 'reasons': ['invalid_geometry']}
    if len(predictions) != 2 or any(p.get('status') != 'ok' for p in predictions):
        return result
    masks = []
    try:
        for prediction in predictions:
            data = Path(prediction['labels_path']).read_bytes()
            if sha256(data) != prediction['labels_sha256']:
                raise ValueError('Mask hash mismatch')
            with Image.open(io.BytesIO(data)) as image:
                labels = np.array(image)
            if labels.ndim != 2 or not np.isin(labels, [0, 1, 2]).all():
                raise ValueError('Invalid label map')
            masks.append(labels)
        if masks[0].shape != masks[1].shape:
            raise ValueError('Mask resolution mismatch')
    except (OSError, ValueError, KeyError):
        return {**result, 'group': 'error', 'reasons': ['artifact_integrity_error']}
    disagreements = []
    for select in (lambda x: x >= 1, lambda x: x == 2):
        a, b = (select(m) for m in masks)
        if not a.any() or not b.any():
            return {**result, 'group': 'invalid_geometry', 'reasons': ['empty_mask']}
        disagreements.append(1 - 2 * np.count_nonzero(a & b) / (np.count_nonzero(a) + np.count_nonzero(b)))
    values = [(p.get('measurement') or {}).get('vertical_cdr') for p in predictions]
    delta = abs(values[0] - values[1]) if all(isinstance(v, (int, float)) for v in values) else None
    return {**result, 'group': 'disagreement', 'score': float(max(disagreements)),
            'reasons': ['model_mask_disagreement'], 'vcdr_delta': delta}
