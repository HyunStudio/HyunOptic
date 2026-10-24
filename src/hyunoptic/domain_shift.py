"""Label-free descriptive camera shift diagnostics against frozen PAPILA features.

No external expert 2-5 data enter the scored features, source scaler or
shift computation. Use only as a warning, not as a trigger to tune the lock.
"""
from __future__ import annotations
import numpy as np
from .mask_features import MASK_FEATURES


def camera_feature_shift(rows: list[dict], frozen_scaler: dict,
                         *, z_threshold: float = 3.0) -> dict:
    if not rows or not np.isfinite(z_threshold) or z_threshold <= 0:
        raise ValueError("Expected nonempty rows and positive finite z threshold")
    result = {}
    for camera in ("all", "bosch", "forus", "remidio"):
        cohort = [row for row in rows if camera == "all" or row["camera"] == camera]
        if not cohort:
            result[camera] = {"n_images": 0, "status": "no data"}
            continue
        per_feature = {}
        for name in MASK_FEATURES:
            params = frozen_scaler[name]
            mu, sd = float(params["mean"]), float(params["sd"])
            values = np.asarray([r[name] for r in cohort], dtype=np.float64)
            if not (np.isfinite(values).all() and np.isfinite(mu) and
                    np.isfinite(sd) and sd > 0):
                raise ValueError("Nonfinite or invalid source normalization parameters")
            z = (values - mu) / sd
            per_feature[name] = {
                "mean_source_standardized": float(z.mean()),
                "median_source_standardized": float(np.median(z)),
                "n_abs_z_over_threshold": int(np.sum(np.abs(z) > z_threshold)),
                "fraction_abs_z_over_threshold": float(np.mean(np.abs(z) > z_threshold)),
            }
        result[camera] = {"n_images": len(cohort), "features": per_feature}
    return {
        "method": "unlabelled_source_standardized_feature_drift_v1",
        "z_threshold": z_threshold,
        "comparison": "Chaksu candidate-only feature distribution versus frozen PAPILA-development mean/SD",
        "camera_groups": result,
        "caveats": [
            "A difference in feature distributions is not proof of technical or clinical error.",
            "Source SD near zero may make external z-scores unstable; investigate without post-hoc tuning.",
            "Device effects can confound biological/reader variation; descriptive diagnostics only.",
            "No expert labels enter shift calculation; no p-value, transfer calibration or retuning is applied.",
        ],
    }
