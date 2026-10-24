"""Freeze candidate-only mask scoring on PAPILA development images.

No held-out expert data are read when fitting these normalization parameters.
Exported lock is an integrity-checked CONFIG SNAPSHOT, not registration with
a third-party registry or proof of new scientific evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from .inventory import inspect_papila
from .mask_features import MASK_FEATURES, MASK_FEATURE_VERSION, fit_mask_scaler, mask_features
from .measure import polygon_mask
from .papila import discover_cases, load_contours, load_image
from .study import patient_splits
from .uncertainty import PerturbationConfig

def canonical_digest(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()

def freeze_papila_model(root: str | Path, *, seed: int = 42,
                        draws: int = 500, allow_partial: bool = False) -> dict:
    cfg = PerturbationConfig(draws=draws, seed=seed)
    cfg.validate()
    inventory = inspect_papila(root)
    if not inventory["matches_full_published_shape"] and not allow_partial:
        raise ValueError("Full PAPILA inventory required for a standard frozen model")
    cases = discover_cases(root)
    splits = patient_splits([c.patient_id for c in cases], seed)
    development = []
    failed = []
    for case in cases:
        if splits[case.patient_id] != "development":
            continue
        try:
            image = load_image(case)
            disc, cup = load_contours(case, "exp1")
            md = polygon_mask(disc, image.size)
            mc = polygon_mask(cup, image.size)
            development.append(mask_features(image, md, mc, cfg))
        except (OSError, ValueError, RuntimeError) as exc:
            failed.append({"case_id": case.image_id, "error": str(exc)})
    if failed:
        raise ValueError(f"Development dataset contains {len(failed)} unreadable cases; "
                         "inspect your local data and rerun before freezing")
    scaler = fit_mask_scaler(development)
    contents = {
        "project": "HyunOptic", "lock_version": "0.7.0",
        "method": MASK_FEATURE_VERSION,
        "candidate_reader": "exp1",
        "feature_names": list(MASK_FEATURES),
        "scaler": scaler,
        "perturbation": cfg.__dict__,
        "split_method": "sha256(seed|patient_id) ordered 60/20/20",
        "split_seed": seed,
        "source": "PAPILA development observations only",
        "source_complete_inventory": inventory["matches_full_published_shape"],
        "source_is_partial": not inventory["matches_full_published_shape"],
        "source_metadata_fingerprint": inventory["inventory_sha256_of_paths_and_sizes_only"],
        "n_development_images": len(development),
        "review_fraction": 0.20,
        "research_disagreement_threshold": 0.10,
        "target_definition": "abs(vCDR(candidate exp1) - vCDR(independent expert2)) > 0.10",
        "no_outcome_labels_used_in_scaling": True,
        "no_external_data_used_in_scaling": True,
        "warning": "Internal research setting, NOT a clinical threshold or medical device.",
    }
    return {"model": contents, "sha256": canonical_digest(contents)}

def validate_model_lock(payload: dict, *, permit_partial: bool = False) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"model", "sha256"}:
        raise ValueError("Invalid frozen model-lock structure")
    model = payload["model"]
    if canonical_digest(model) != payload["sha256"]:
        raise ValueError("Model-lock content does not match recorded SHA-256")
    if model["project"] != "HyunOptic" or model["lock_version"] != "0.7.0" or model["method"] != MASK_FEATURE_VERSION:
        raise ValueError("Unsupported scoring lock")
    if model["feature_names"] != list(MASK_FEATURES) or model["candidate_reader"] != "exp1":
        raise ValueError("Unexpected model features or candidate reader")
    if model["source_is_partial"] and not permit_partial:
        raise ValueError("Partial PAPILA lock is not permitted for real external evaluation")
    if model["review_fraction"] != 0.20 or model["research_disagreement_threshold"] != 0.10:
        raise ValueError("Non-frozen evaluation setting")
    if model["no_outcome_labels_used_in_scaling"] is not True or model["no_external_data_used_in_scaling"] is not True:
        raise ValueError("Training-label separation declaration absent")
    cfg = PerturbationConfig(**model["perturbation"])
    cfg.validate()
    for name in MASK_FEATURES:
        params = model["scaler"][name]
        if not (np.isfinite(params["mean"]) and np.isfinite(params["sd"]) and params["sd"] > 0):
            raise ValueError("Non-finite normalization parameters")
    return model

def save_lock(payload: dict, output: str | Path) -> None:
    output = Path(output)
    if output.exists():
        raise FileExistsError("Will not overwrite a previously frozen experiment")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def load_lock(path: str | Path, *, permit_partial: bool = False) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_model_lock(payload, permit_partial=permit_partial)
    return payload
