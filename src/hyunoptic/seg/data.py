"""PAPILA split manifest and expert-1 training targets (no PyTorch needed).

The split reuses ``study.patient_splits`` (sha256(seed|patient) ordered 60/20/20), so both
eyes of a patient stay together and the partition matches the earlier QC protocol.
Expert-2 contours are never read here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..papila import PapilaCase, discover_cases, load_contours, load_image
from ..study import patient_splits
from . import preprocess

SPLIT_SCHEMA = "hyunoptic.seg_split/v1"
TRAIN_READER = "exp1"


def canonical_sha256(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def build_split_manifest(root: str | Path, seed: int = 42) -> dict:
    cases = discover_cases(root)
    if not cases:
        raise ValueError("No complete PAPILA image/contour sets found")
    assignment = patient_splits([c.patient_id for c in cases], seed)
    splits = {name: sorted(c.image_id for c in cases if assignment[c.patient_id] == name)
              for name in ("development", "validation", "holdout")}
    body = {
        "schema": SPLIT_SCHEMA, "dataset": "PAPILA", "seed": seed,
        "method": "study.patient_splits: sha256(seed|patient_id) ordered 60/20/20",
        "splits": splits,
        "patients": {name: sorted({c.patient_id for c in cases if assignment[c.patient_id] == name})
                     for name in splits},
    }
    return {"manifest": body, "sha256": canonical_sha256(body)}


def verify_split_manifest(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"manifest", "sha256"}:
        raise ValueError("Invalid split manifest structure")
    body = payload["manifest"]
    if body.get("schema") != SPLIT_SCHEMA:
        raise ValueError("Unsupported split manifest schema")
    if canonical_sha256(body) != payload["sha256"]:
        raise ValueError("Split manifest content does not match its SHA-256")
    patients = [set(body["patients"][s]) for s in ("development", "validation", "holdout")]
    if patients[0] & patients[1] or patients[0] & patients[2] or patients[1] & patients[2]:
        raise ValueError("A patient appears in more than one split")
    return body


def cases_for(root: str | Path, split_body: dict, split: str) -> list[PapilaCase]:
    wanted = set(split_body["splits"][split])
    found = [c for c in discover_cases(root) if c.image_id in wanted]
    if len(found) != len(wanted):
        raise ValueError(f"{len(wanted) - len(found)} {split} images listed in the split are missing")
    return found


def training_example(case: PapilaCase, size: int) -> tuple[np.ndarray, np.ndarray]:
    """Letterboxed image and EXPERT-1 class-map target. Expert 2 is never loaded."""
    image = load_image(case)
    disc, cup = load_contours(case, TRAIN_READER)
    arr, _ = preprocess.image_array(image, size)
    target = preprocess.target_from_contours(disc, cup, image.width, image.height, size)
    return arr, target
