"""Fixed, image-only preprocessing contract (no PyTorch needed).

``letterbox_v1``: scale the WHOLE image so its longer side equals ``size``, centre it on a
black square canvas, and record scale/padding so predictions map back to original pixel
coordinates. No optic-disc crop is used, so no reference mask can influence inference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image

from ..measure import polygon_mask

METHOD = "letterbox_v1"
MEAN = (0.5, 0.5, 0.5)
STD = (0.25, 0.25, 0.25)
MAX_PIXELS = 40_000_000  # refuse absurd inputs instead of freezing the UI


@dataclass(frozen=True)
class Letterbox:
    size: int
    orig_w: int
    orig_h: int
    scale: float
    new_w: int
    new_h: int
    pad_x: int
    pad_y: int

    def to_dict(self) -> dict:
        return asdict(self)


def plan(width: int, height: int, size: int) -> Letterbox:
    if size < 32 or size % 16:
        raise ValueError("size must be a multiple of 16 and at least 32")
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise ValueError(f"Image size {width}×{height} is outside the supported range")
    scale = size / max(width, height)
    new_w, new_h = max(1, round(width * scale)), max(1, round(height * scale))
    return Letterbox(size, width, height, scale, new_w, new_h, (size - new_w) // 2, (size - new_h) // 2)


def image_array(image: Image.Image, size: int) -> tuple[np.ndarray, Letterbox]:
    """uint8 H×W×3 letterboxed image (bilinear)."""
    rgb = image.convert("RGB")
    lb = plan(rgb.width, rgb.height, size)
    canvas = Image.new("RGB", (size, size))
    canvas.paste(rgb.resize((lb.new_w, lb.new_h), Image.BILINEAR), (lb.pad_x, lb.pad_y))
    return np.asarray(canvas, dtype=np.uint8), lb


def normalise(array: np.ndarray) -> np.ndarray:
    """uint8 H×W×3 → float32 3×H×W with fixed mean/std."""
    x = array.astype(np.float32) / 255.0
    x = (x - np.asarray(MEAN, np.float32)) / np.asarray(STD, np.float32)
    return np.ascontiguousarray(x.transpose(2, 0, 1))


def class_map(disc: np.ndarray, cup: np.ndarray) -> np.ndarray:
    """0 background, 1 disc rim, 2 cup (cup clipped to disc)."""
    disc = np.asarray(disc, bool)
    cup = np.asarray(cup, bool) & disc
    out = np.zeros(disc.shape, np.uint8)
    out[disc] = 1
    out[cup] = 2
    return out


def target_from_contours(disc_xy: np.ndarray, cup_xy: np.ndarray, width: int, height: int,
                         size: int) -> np.ndarray:
    """Rasterise at ORIGINAL resolution with the shared polygon convention, then letterbox (nearest)."""
    full = class_map(polygon_mask(disc_xy, (width, height)), polygon_mask(cup_xy, (width, height)))
    return letterbox_labels(full, plan(width, height, size))


def letterbox_labels(labels: np.ndarray, lb: Letterbox) -> np.ndarray:
    small = Image.fromarray(labels.astype(np.uint8)).resize((lb.new_w, lb.new_h), Image.NEAREST)
    canvas = np.zeros((lb.size, lb.size), np.uint8)
    canvas[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w] = np.asarray(small)
    return canvas


def to_original(labels: np.ndarray, lb: Letterbox) -> np.ndarray:
    """Model-resolution class map → original image coordinates (nearest)."""
    crop = labels[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w].astype(np.uint8)
    return np.asarray(Image.fromarray(crop).resize((lb.orig_w, lb.orig_h), Image.NEAREST))


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Largest 4-connected component (predeclared post-processing ``largest_disc_component_v1``)."""
    m = np.asarray(mask, bool)
    if not m.any():
        return m
    labels = np.zeros(m.shape, np.int32)
    best, best_size, current = 0, 0, 0
    h, w = m.shape
    for y0, x0 in zip(*np.nonzero(m)):
        if labels[y0, x0]:
            continue
        current += 1
        stack, size = [(y0, x0)], 0
        labels[y0, x0] = current
        while stack:
            y, x = stack.pop()
            size += 1
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = current
                    stack.append((ny, nx))
        if size > best_size:
            best, best_size = current, size
    return labels == best


def postprocess(labels: np.ndarray) -> np.ndarray:
    """Keep the largest disc component; cup only inside it. Deterministic, image-only."""
    disc = largest_component(labels >= 1)
    out = np.zeros(labels.shape, np.uint8)
    out[disc] = 1
    out[disc & (labels == 2)] = 2
    return out
