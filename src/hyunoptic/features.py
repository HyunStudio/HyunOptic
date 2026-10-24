"""Candidate-only image and contour features for experimental QC research.

Features do not consume any second-reader annotation or glaucoma diagnosis.
"""
from __future__ import annotations
import math
import numpy as np
from PIL import Image
from .measure import measure_contours, polygon_mask
from .uncertainty import PerturbationConfig, analyze_vertical_sensitivity

FEATURE_NAMES = ("v02_q95", "cup_roughness", "cup_boundary_weakness")

def contour_roughness(points_xy: np.ndarray) -> float:
    """Isoperimetric excess (P^2/(4 pi A) - 1), 0 for an ideal circle."""
    p = np.asarray(points_xy, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError("invalid contour for roughness")
    nxt = np.roll(p, -1, axis=0)
    area = 0.5 * abs(np.sum(p[:, 0] * nxt[:, 1] - nxt[:, 0] * p[:, 1]))
    perimeter = np.linalg.norm(nxt - p, axis=1).sum()
    if area <= 0 or perimeter <= 0:
        raise ValueError("degenerate contour")
    return float(max(0.0, perimeter**2 / (4 * math.pi * area) - 1))

def boundary_gradient_strength(image: Image.Image, points_xy: np.ndarray) -> float:
    """Mean greyscale central-difference gradient sampled at candidate vertices.

    Exploratory camera-dependent contrast proxy, not a validated image quality score.
    Coordinates use the original full-resolution image; no held-out labels are used.
    """
    pixels = np.asarray(image.convert("L"), dtype=np.float32)
    height, width = pixels.shape
    if min(width, height) < 3:
        raise ValueError("image too small for boundary gradient")
    points = np.asarray(points_xy, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3 or not np.isfinite(points).all():
        raise ValueError("invalid boundary coordinates")
    x, y = np.rint(points[:, 0]).astype(int), np.rint(points[:, 1]).astype(int)
    if np.any(x < 0) or np.any(x >= width) or np.any(y < 0) or np.any(y >= height):
        raise ValueError("boundary coordinates outside the image")
    x, y = np.clip(x, 1, width - 2), np.clip(y, 1, height - 2)
    dx = np.abs(pixels[y, x + 1] - pixels[y, x - 1]) / (2 * 255.0)
    dy = np.abs(pixels[y + 1, x] - pixels[y - 1, x]) / (2 * 255.0)
    return float(np.mean(np.sqrt(dx * dx + dy * dy) / np.sqrt(2)))

def candidate_features(
    image: Image.Image, disc_xy: np.ndarray, cup_xy: np.ndarray,
    config: PerturbationConfig | None = None,
) -> dict[str, float]:
    """Candidate-only, fixed-definition research baseline features."""
    config = config or PerturbationConfig()
    measurement = measure_contours(disc_xy, cup_xy, image.size)
    sensitivity = analyze_vertical_sensitivity(disc_xy, cup_xy, config)
    disc = polygon_mask(disc_xy, image.size)
    cup = polygon_mask(cup_xy, image.size)
    outside_fraction = float(np.count_nonzero(cup & ~disc) / max(np.count_nonzero(cup), 1))
    return {
        "v02_q95": sensitivity.q95_absolute_vcdr_change,
        "cup_roughness": contour_roughness(cup_xy),
        "cup_boundary_weakness": 1.0 - boundary_gradient_strength(image, cup_xy),
        "candidate_vcdr": measurement.vertical_cdr,
        "cup_outside_fraction": outside_fraction,
    }
