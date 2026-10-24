"""Pixel-space quantitative measurements of expert-drawn OD/OC polygons.

vCDR/hCDR use axis-aligned *mask spans* in pixels. This convention is
explicit and should be held fixed when comparing readers or datasets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class Measurement:
    vertical_cdr: float
    horizontal_cdr: float
    area_cdr: float
    disc_vertical_px: int
    cup_vertical_px: int
    disc_horizontal_px: int
    cup_horizontal_px: int
    disc_area_px: int
    cup_area_px: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def polygon_mask(points_xy: np.ndarray, image_size: tuple[int, int]) -> np.ndarray:
    """Rasterize (x,y) points into a bool mask of shape (height,width)."""
    width, height = image_size
    points = np.asarray(points_xy, dtype=np.float64)
    if width <= 0 or height <= 0:
        raise ValueError("image_size must be positive (width,height)")
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("polygon requires at least three (x,y) points")
    if not np.isfinite(points).all():
        raise ValueError("polygon coordinates must be finite")
    if np.any(points[:, 0] < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] < 0) or np.any(points[:, 1] >= height):
        raise ValueError("polygon coordinates lie outside original image bounds")
    canvas = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    draw.polygon([tuple(map(float, pt)) for pt in points], fill=1)
    return np.asarray(canvas, dtype=np.bool_)


def _spans(mask: np.ndarray) -> tuple[int, int, int]:
    yy, xx = np.nonzero(mask)
    if not len(yy):
        raise ValueError("polygon rasterized to an empty mask")
    return int(yy.max() - yy.min() + 1), int(xx.max() - xx.min() + 1), int(len(yy))


def measure_masks(disc: np.ndarray, cup: np.ndarray) -> Measurement:
    """Calculate indices on equally sized masks; never silently repair bad contours."""
    if disc.ndim != 2 or cup.ndim != 2 or disc.shape != cup.shape:
        raise ValueError("disc and cup masks must be equally-sized 2D arrays")
    disc, cup = disc.astype(bool), cup.astype(bool)
    dv, dh, da = _spans(disc)
    cv, ch, ca = _spans(cup)
    issues: list[str] = []
    if np.any(cup & ~disc):
        issues.append("Cup mask extends outside disc; review contour alignment.")
    if cv > dv or ch > dh or ca > da:
        issues.append("Cup span/area exceeds disc; derived ratios are not clinically interpretable.")
    return Measurement(
        vertical_cdr=cv / dv, horizontal_cdr=ch / dh, area_cdr=ca / da,
        disc_vertical_px=dv, cup_vertical_px=cv,
        disc_horizontal_px=dh, cup_horizontal_px=ch,
        disc_area_px=da, cup_area_px=ca, warnings=tuple(issues),
    )


def measure_contours(disc_xy: np.ndarray, cup_xy: np.ndarray, image_size: tuple[int, int]) -> Measurement:
    disc = polygon_mask(disc_xy, image_size)
    cup = polygon_mask(cup_xy, image_size)
    return measure_masks(disc, cup)


def dice(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    if mask_a.shape != mask_b.shape:
        raise ValueError("Mask shapes must match")
    a, b = mask_a.astype(bool), mask_b.astype(bool)
    union = int(a.sum()) + int(b.sum())
    return float(2 * np.count_nonzero(a & b) / union) if union else 1.0


def compare_readers(
    disc1: np.ndarray, cup1: np.ndarray, disc2: np.ndarray, cup2: np.ndarray,
    image_size: tuple[int, int],
) -> dict:
    """Retrospective expert agreement (not a prospective reference-free QC score)."""
    d1, c1 = polygon_mask(disc1, image_size), polygon_mask(cup1, image_size)
    d2, c2 = polygon_mask(disc2, image_size), polygon_mask(cup2, image_size)
    m1, m2 = measure_masks(d1, c1), measure_masks(d2, c2)
    return {
        "exp1": m1.to_dict(), "exp2": m2.to_dict(),
        "absolute_vcdr_difference": abs(m1.vertical_cdr - m2.vertical_cdr),
        "disc_dice": dice(d1, d2), "cup_dice": dice(c1, c2),
    }
