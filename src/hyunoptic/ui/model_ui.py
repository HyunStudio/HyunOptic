"""Streamlit helpers for the experimental model pages. PyTorch is imported lazily, only
after a bundle passes verification, so the rest of the workspace never needs it."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

from ..seg.bundle import SPLIT, Bundle
from ..viz import draw_contour, mask_outline
from .theme import EXPERT_COLORS, MODEL_CUP, MODEL_DISC


@st.cache_resource(show_spinner=False, max_entries=3)
def predictor(folder: str, weights_sha256: str):
    """One loaded model per verified weights hash (the hash is part of the cache key)."""
    from ..seg.bundle import verify_bundle
    from ..seg.inference import Predictor
    bundle = verify_bundle(folder)
    if bundle.weights_sha256 != weights_sha256:
        raise ValueError("Bundle changed while loading")
    return Predictor(bundle)


@st.cache_data(show_spinner=False, max_entries=32)
def predict(folder: str, weights_sha256: str, image_sha256: str, _image: Image.Image):
    """In-memory cache keyed by image-content hash + model hash; nothing is written to disk."""
    return predictor(folder, weights_sha256).predict(_image)


def image_sha256(image: Image.Image) -> str:
    rgb = image.convert("RGB")
    digest = hashlib.sha256(f"{rgb.width}x{rgb.height}".encode())
    digest.update(np.asarray(rgb).tobytes())
    return digest.hexdigest()


def split_role(bundle: Bundle, image_id: str) -> str | None:
    """Which split of THIS model an image belongs to (honest labelling of what is held out)."""
    try:
        splits = json.loads((bundle.folder / SPLIT).read_text(encoding="utf-8"))["manifest"]["splits"]
    except (OSError, ValueError, KeyError):
        return None
    return next((name for name, ids in splits.items() if image_id in ids), None)


def draw_prediction(image: Image.Image, disc: np.ndarray | None, cup: np.ndarray | None, *,
                    show_disc: bool, show_cup: bool, experts: list[tuple[int, object]] = (),
                    thickness: int = 2) -> tuple[Image.Image, list[tuple[str, str, str]]]:
    """Model: disc solid / cup dashed. Experts (optional, separate panel): dotted in their colours."""
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    legend = []
    span = 0.0
    if disc is not None and disc.any():
        ys = np.nonzero(disc)[0]
        span = float(ys.max() - ys.min())
    width = max(1, round(thickness * max(span, 60.0) / 110))
    for idx, reader in experts:
        color = EXPERT_COLORS[idx % len(EXPERT_COLORS)]
        if show_disc:
            draw_contour(draw, reader.disc_xy, color=color, width=width, style="dotted")
            legend.append((f"{reader.label} disc", color, "dotted"))
        if show_cup:
            draw_contour(draw, reader.cup_xy, color=color, width=width, style="dotted")
            legend.append((f"{reader.label} cup", color, "dotted"))
    for name, mask, color, style, on in (("Model disc", disc, MODEL_DISC, "solid", show_disc),
                                         ("Model cup", cup, MODEL_CUP, "dashed", show_cup)):
        if on and mask is not None and mask.any():
            draw_contour(draw, mask_outline(mask), color=color, width=width, style=style)
            legend.append((name, color, style))
    return out, legend


def crop_box(mask: np.ndarray | None, image: Image.Image, padding: float = 0.9):
    if mask is None or not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    span = max(np.ptp(xs), np.ptp(ys))
    m = max(24.0, span * padding)
    return (max(0, int(xs.min() - m)), max(0, int(ys.min() - m)),
            min(image.width, int(xs.max() + m)), min(image.height, int(ys.max() + m)))
