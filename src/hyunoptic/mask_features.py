"""Common mask-based candidate-only QC features for PAPILA and Chaksu.

Separate v0.7 feature family: DO NOT reuse older polygon-derived scaling.
"""
from __future__ import annotations
import math
from dataclasses import asdict
import numpy as np
from PIL import Image
from .measure import measure_masks
from .uncertainty import PerturbationConfig

MASK_FEATURES = ("mask_q95", "mask_roughness", "mask_boundary_weakness")
MASK_FEATURE_VERSION = "mask_shared_v1"

def _boundary(mask: np.ndarray) -> tuple[np.ndarray, int]:
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2 or not m.any():
        raise ValueError("Expected a nonempty two-dimensional mask")
    p = np.pad(m, 1, constant_values=False)
    center = p[1:-1, 1:-1]
    top, bottom = p[:-2, 1:-1], p[2:, 1:-1]
    left, right = p[1:-1, :-2], p[1:-1, 2:]
    boundary = center & ~(top & bottom & left & right)
    # Four-connected pixel-edge perimeter. Does not imply continuous shape.
    length = int((center & ~top).sum() + (center & ~bottom).sum()
                 + (center & ~left).sum() + (center & ~right).sum())
    return boundary, length

def mask_features(image: Image.Image, disc: np.ndarray, cup: np.ndarray,
                  config: PerturbationConfig | None = None) -> dict[str, float]:
    """No second reader, fused mask or clinical outcome can enter this API."""
    config = config or PerturbationConfig()
    config.validate()
    if image.size != (disc.shape[1], disc.shape[0]) or disc.shape != cup.shape:
        raise ValueError("Mask size does not match original fundus image")
    disc, cup = disc.astype(bool), cup.astype(bool)
    if not disc.any() or not cup.any() or np.any(cup & ~disc):
        raise ValueError("Invalid optic cup/disc containment or empty mask")
    measurement = measure_masks(disc, cup)
    nominal = measurement.vertical_cdr
    # This is a known rescaled-vCDR negative-control baseline, NOT calibrated uncertainty.
    rng = np.random.default_rng(config.seed)
    cup_noise = rng.normal(0, config.cup_log_sd, config.draws)
    disc_noise = rng.normal(0, config.disc_log_sd, config.draws)
    q95 = float(nominal * np.percentile(np.abs(np.exp(cup_noise - disc_noise) - 1), 95))
    boundary, perimeter = _boundary(cup)
    area = int(cup.sum())
    roughness = float(max(0.0, perimeter**2 / (4 * math.pi * area) - 1.0))
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)
    # Central differences with edge replication, sampled only along cup mask.
    padded = np.pad(grayscale, 1, mode="edge")
    dx = np.abs(padded[1:-1, 2:] - padded[1:-1, :-2]) / (2 * 255)
    dy = np.abs(padded[2:, 1:-1] - padded[:-2, 1:-1]) / (2 * 255)
    gradient = np.sqrt(dx * dx + dy * dy) / math.sqrt(2)
    weak = float(1.0 - gradient[boundary].mean())
    return {
        "mask_q95": q95,
        "mask_roughness": roughness,
        "mask_boundary_weakness": weak,
        "candidate_vcdr": nominal,
    }

def fit_mask_scaler(development_features: list[dict]) -> dict:
    """Unlabeled PAPILA DEVELOPMENT observations only."""
    if not development_features:
        raise ValueError("Need PAPILA development data to freeze a scaler")
    parameters = {}
    for name in MASK_FEATURES:
        values = np.asarray([row[name] for row in development_features], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite PAPILA development feature")
        std = float(values.std(ddof=0))
        parameters[name] = {"mean": float(values.mean()), "sd": std if std > 1e-12 else 1.0}
    return parameters

def apply_mask_score(features: dict, scaler: dict) -> float:
    """Fixed equal-weight scoring, not trained on expert2 labels."""
    standardized = []
    for name in MASK_FEATURES:
        value, params = float(features[name]), scaler[name]
        if not np.isfinite(value) or params["sd"] <= 0 or not np.isfinite(params["sd"]):
            raise ValueError("Invalid feature/scaler")
        standardized.append(float(np.clip((value - params["mean"]) / params["sd"], -3, 3)))
    return 3.0 + sum(standardized) / len(standardized)
