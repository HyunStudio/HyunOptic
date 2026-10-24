"""Deterministic, content-based PAPILA image/annotation fingerprint.

Unlike the older metadata-only fingerprint, changing any file bytes causes
a different digest even if the filename and byte length remain unchanged.
The digest is a local integrity marker, NOT publisher-authenticated proof.
Clinical spreadsheet files are not opened or included.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from .papila import _resolve_dirs


def papila_content_sha256(root: str | Path) -> str:
    """Stream hashes of all top-level fundus image and contour files.

    Include unknown files, not just recognizable ones, so additions and
    replacements change the fingerprint. No raw file bytes are returned.
    """
    images, outlines = _resolve_dirs(root)
    digest = hashlib.sha256()
    for prefix, folder in (("FundusImages", images),
                           ("ExpertsSegmentations/Contours", outlines)):
        entries = sorted((p for p in folder.iterdir() if p.is_file()),
                         key=lambda p: p.name)
        for path in entries:
            file_digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    file_digest.update(chunk)
            # Unambiguous length-prefixed UTF-8 records, portable across OS.
            name = f"{prefix}/{path.name}".encode("utf-8")
            digest.update(len(name).to_bytes(4, "big"))
            digest.update(name)
            digest.update(size.to_bytes(8, "big"))
            digest.update(file_digest.digest())
    return digest.hexdigest()
