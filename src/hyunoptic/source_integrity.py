"""Optional local archive identity checks with reproducible reference digests.

These SHA-256 digests are transcribed from an independent public dataset
index, not digital signatures issued by the dataset publishers.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REFERENCE_ARCHIVES = {
    "PAPILA": {
        "filename": "PAPILA.zip",
        "sha256": "15b053dff496bc8e53eb8a8d0707ef73ba3d56c988eea92b65832c9c82852a7d",
        "source": "https://github.com/staskh/fundus-atlas/blob/main/src/datasets/papila.py",
    },
    "CHAKSU_TEST": {
        "filename": "Test.zip",
        "sha256": "90e89ad01bfb0c4c238ba22a4a46ab46b5849e2fc9253c7bda09509f6ca259fa",
        "source": "https://github.com/staskh/fundus-atlas/blob/main/src/datasets/chaksu.py",
    },
}


def sha256_file(path: str | Path, *, chunk_size: int = 4 * 1024 * 1024) -> tuple[str, int]:
    """Hash a local archive while streaming; keep no images or ZIP contents in RAM."""
    if not isinstance(chunk_size, int) or not 1024 <= chunk_size <= 64 * 1024 * 1024:
        raise ValueError("chunk_size must be 1024 bytes to 64 MB")
    file = Path(path).expanduser()
    if not file.is_file():
        raise FileNotFoundError(f"Archive not found: {file}")
    digest = hashlib.sha256()
    total = 0
    with file.open("rb") as src:
        while block := src.read(chunk_size):
            total += len(block)
            digest.update(block)
    return digest.hexdigest(), total


def verify_archive(path: str | Path, dataset: str) -> dict:
    """Identity verification only; no network upload, no patient data processing."""
    if dataset not in REFERENCE_ARCHIVES:
        raise ValueError("Unknown data source; expected PAPILA or CHAKSU_TEST")
    reference = REFERENCE_ARCHIVES[dataset]
    actual, size = sha256_file(path)
    matching = actual == reference["sha256"]
    return {
        "project": "HyunOptic",
        "dataset": dataset,
        "archive_bytes": size,
        "computed_sha256": actual,
        "public_reference_sha256": reference["sha256"],
        "matches_independent_public_reference": matching,
        "reference_type": "third-party public checksum, NOT a dataset publisher signature",
        "reference_code_url": reference["source"],
        "version_sensitivity_warning": (
            "Mismatched SHA256 could mean a different legitimate dataset version, "
            "or a damaged/altered archive. Verify with the publisher before research."
        ) if not matching else (
            "Identical archive bytes to a publicly indexed reference; "
            "this does not verify scientific annotation correctness or clinical validity."
        ),
        "image_data_uploaded": False,
    }


def save_integrity_report(reports: list[dict], output: str | Path) -> None:
    output = Path(output)
    if output.exists():
        raise FileExistsError("Will not overwrite prior source integrity reports")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"project": "HyunOptic", "version": "1.0.0rc1",
               "checks": reports, "images_uploaded": False}
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
