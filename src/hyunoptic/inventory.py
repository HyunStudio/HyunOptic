"""PAPILA dataset inventory and reproducibility checks (does not copy the images).

Published dataset expectation: 244 bilateral patients, 488 images, 1,952 contours.
The inventory hash is a FILE-METADATA fingerprint, not a SHA-256 of image bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .papila import _resolve_dirs, discover_cases, load_contours

_EXPECTED_IMAGE_SIZE = (2576, 1934)
_SUFFIX = re.compile(r"^RET\d{3}(?:OD|OS)_(?:disc|cup)_exp[12](?:\s+\d+)?\.txt$", re.I)


def inspect_papila(root: str | Path, *, verify_pixels: bool = False) -> dict:
    """Build a deterministic manifest; continue past malformed cases.

    No medical diagnoses or private clinical spreadsheet contents are read.
    """
    image_dir, contour_dir = _resolve_dirs(root)
    cases = discover_cases(root, require_complete=False)
    if not cases:
        raise ValueError("No PAPILA fundus images recognized in input")
    all_contours = sorted(contour_dir.glob("*.txt"), key=lambda p: p.name)
    skipped = []
    entries = []
    for case in cases:
        errors, warnings = [], []
        expected = [case.contour_path(s, e) for e in ("exp1", "exp2") for s in ("disc", "cup")]
        missing = [p.name for p in expected if not p.is_file()]
        if missing:
            errors.append("missing contour files: " + ", ".join(missing))
        image_size = None
        try:
            with Image.open(case.image_path) as img:
                image_size = list(img.size)
                if img.size != _EXPECTED_IMAGE_SIZE:
                    warnings.append("unexpected published PAPILA image dimensions")
                if verify_pixels:
                    img.verify()
        except (OSError, ValueError) as exc:
            errors.append("image cannot be opened/verified: " + str(exc))
        if not missing and image_size:
            try:
                for expert in ("exp1", "exp2"):
                    disc, cup = load_contours(case, expert)
                    for struct, points in (("disc", disc), ("cup", cup)):
                        if np.any(points[:, 0] < 0) or np.any(points[:, 1] < 0) or np.any(points[:, 0] >= image_size[0]) or np.any(points[:, 1] >= image_size[1]):
                            errors.append(f"out-of-bounds {expert}/{struct} coordinates")
            except (OSError, ValueError) as exc:
                errors.append("unreadable contour coordinates: " + str(exc))
        entry = {
            "image_id": case.image_id,
            "patient_id": case.patient_id,
            "eye": case.eye,
            "image_size": image_size,
            "annotation_files_present": 4 - len(missing),
            "errors": errors,
            "warnings": warnings,
        }
        entries.append(entry)
        if errors:
            skipped.append(case.image_id)
    patient_eyes: dict[str, set[str]] = {}
    for c in cases:
        patient_eyes.setdefault(c.patient_id, set()).add(c.eye)
    n_bilateral = sum(eyes == {"OD", "OS"} for eyes in patient_eyes.values())
    duplicate_like = [p.name for p in all_contours if re.search(r"\s+\d+\.txt$", p.name, re.I) and _SUFFIX.fullmatch(p.name)]
    unexpected_txt = [p.name for p in all_contours if not _SUFFIX.fullmatch(p.name)]
    canonical = sum(1 for p in all_contours if _SUFFIX.fullmatch(p.name) and p.name not in duplicate_like)
    fingerprint_material = [
        (str(path.relative_to(image_dir)), int(path.stat().st_size)) for path in sorted(image_dir.iterdir()) if path.is_file()
    ] + [
        (str(path.relative_to(contour_dir)), int(path.stat().st_size)) for path in all_contours if path.is_file()
    ]
    inventory_hash = hashlib.sha256(json.dumps(fingerprint_material, sort_keys=True).encode()).hexdigest()
    n_dim_mismatches = sum("unexpected published PAPILA image dimensions" in row["warnings"] for row in entries)
    full_shape_matches = (
        len(cases) == 488 and len(patient_eyes) == 244 and n_bilateral == 244
        and canonical == 1952 and len(skipped) == 0 and n_dim_mismatches == 0
    )
    return {
        "project": "HyunOptic", "version": "0.4.0",
        "source": "PAPILA local inventory; research only",
        "published_expectation": {
            "patients": 244, "eyes": 488, "contour_files": 1952, "image_size": list(_EXPECTED_IMAGE_SIZE)
        },
        "observed": {
            "patients": len(patient_eyes), "images": len(cases),
            "bilateral_patients": n_bilateral,
            "canonical_contours": canonical,
            "duplicate_like_contours": len(duplicate_like),
            "unexpected_txt_files": len(unexpected_txt),
            "unusable_images": len(skipped),
            "image_dimension_mismatches": n_dim_mismatches,
        },
        "matches_full_published_shape": full_shape_matches,
        "inventory_sha256_of_paths_and_sizes_only": inventory_hash,
        "hash_is_NOT_content_checksum": True,
        "duplicate_like_contour_names": duplicate_like,
        "unexpected_text_filenames": unexpected_txt,
        "unusable_image_ids": skipped,
        "cases": entries,
        "limitations": [
            "Matching expected file counts does not prove original image authenticity.",
            "No diagnosis labels or clinical validity evaluated.",
            "Inventory fingerprint is based only on names and byte sizes, not content hashes.",
            "Coordinate format compatibility must be verified on original archive."
        ],
    }


def save_inventory(manifest: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
