"""Opt-in PAPILA acquisition from Figshare's official article API.

No package dataset files. This code executes only on the user's machine when
explicitly invoked and requires acknowledgement of the publisher's terms.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ARTICLE_ID = 14798004
ARTICLE_API = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"
MAX_ARCHIVE_BYTES = 1_500_000_000
MAX_UNPACKED_BYTES = 9_000_000_000
MAX_ENTRIES = 30_000

def _official_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "figshare.com" or host.endswith(".figshare.com")):
        raise ValueError("Refusing non-HTTPS or non-Figshare source URL")
    return url

def figshare_metadata(open_url=urllib.request.urlopen) -> dict:
    """Look up latest Figshare article metadata; no hard-coded mirror URLs."""
    request = urllib.request.Request(ARTICLE_API, headers={"User-Agent": "HyunOptic-research/0.5"})
    with open_url(request, timeout=40) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Unexpectedly large article metadata")
    data = json.loads(payload)
    if int(data.get("id", -1)) != ARTICLE_ID:
        raise ValueError("Unexpected Figshare article ID")
    candidates = [file for file in data.get("files", [])
                  if file.get("name", "").lower() == "papila.zip"]
    if len(candidates) != 1:
        raise ValueError("Expected exactly one PAPILA.zip file on official Figshare article")
    entry = candidates[0]
    url = _official_url(entry["download_url"])
    size = int(entry["size"])
    if size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise ValueError("Unexpected PAPILA archive size")
    md5 = entry.get("supplied_md5") or entry.get("computed_md5") or entry.get("md5")
    if md5 is not None and not re.fullmatch("[a-fA-F0-9]{32}", str(md5)):
        raise ValueError("Malformed MD5 checksum in Figshare metadata")
    return {
        "article_id": ARTICLE_ID,
        "dataset": "PAPILA",
        "version": data.get("version"),
        "article_doi": data.get("doi"),
        "license_url": data.get("license", {}).get("url") if isinstance(data.get("license"), dict) else None,
        "file_id": entry["id"], "name": entry["name"], "download_url": url,
        "bytes_expected": size, "figshare_md5": str(md5).lower() if md5 else None,
        "metadata_source": ARTICLE_API,
    }

def acquire_archive(
    destination: str | Path, *,
    accept_terms: bool,
    metadata: dict | None = None,
    open_url=urllib.request.urlopen,
) -> dict:
    """Stream an official archive with atomic replacement and checksum validation.

    Existing ZIPs are NEVER overwritten. Failed downloads leave no final ZIP.
    """
    if not accept_terms:
        raise ValueError("Explicit --accept-dataset-terms required")
    target = Path(destination).expanduser().resolve()
    if target.suffix.lower() != ".zip":
        raise ValueError("Destination must be a .zip filename")
    if target.exists():
        raise FileExistsError(f"Will not overwrite an existing ZIP: {target}")
    source = metadata if metadata is not None else figshare_metadata(open_url=open_url)
    if int(source.get("article_id", -1)) != ARTICLE_ID:
        raise ValueError("Incorrect article provenance")
    _official_url(source["download_url"])
    size = int(source["bytes_expected"])
    if size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive size out of bounds")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, partial = tempfile.mkstemp(prefix=".papila-", suffix=".partial", dir=target.parent)
    total = 0
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    try:
        with os.fdopen(fd, "wb") as output:
            request = urllib.request.Request(source["download_url"], headers={"User-Agent": "HyunOptic-research/0.5"})
            with open_url(request, timeout=120) as response:
                # Detect an unexpected off-domain redirect where possible.
                resolved = getattr(response, "url", None)
                if resolved:
                    _official_url(resolved)
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > size or total > MAX_ARCHIVE_BYTES:
                        raise ValueError("Download exceeds Figshare advertised size")
                    output.write(block)
                    sha256.update(block)
                    md5.update(block)
        if total != size:
            raise ValueError(f"Incomplete download: expected {size}, got {total}")
        expected_md5 = source.get("figshare_md5")
        if expected_md5 and md5.hexdigest().lower() != expected_md5.lower():
            raise ValueError("Figshare MD5 mismatch; incomplete or altered download")
        if not zipfile.is_zipfile(partial):
            raise ValueError("Downloaded object is not a ZIP archive")
        os.replace(partial, target)
    finally:
        if os.path.exists(partial):
            os.remove(partial)
    return {
        "dataset": "PAPILA", "article_id": ARTICLE_ID,
        "source_article": ARTICLE_API, "source_file_id": source.get("file_id"),
        "size_bytes": total, "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(), "md5_verified_against_figshare": bool(source.get("figshare_md5")),
        "archive_path": str(target),
        "license_acknowledged": True,
        "warning": "Dataset includes clinical metadata; keep locally and do not publish raw files.",
    }

def safely_extract_archive(archive: str | Path, destination: str | Path) -> dict:
    """Extract without overwriting files, path traversal, symlinks or ZIP bombs.

    Use a fresh target directory. Fail without processing file content when
    the central directory violates safety checks.
    """
    archive = Path(archive).resolve()
    dest = Path(destination).resolve()
    if dest.exists():
        raise FileExistsError("Refusing to overwrite an existing extraction folder")
    if not zipfile.is_zipfile(archive):
        raise ValueError("Not a ZIP archive")
    with zipfile.ZipFile(archive) as zf:
        files = zf.infolist()
        if len(files) > MAX_ENTRIES:
            raise ValueError("Excessive number of archive entries")
        total = 0
        for item in files:
            normalized = item.filename.replace("\\", "/")
            pure = PurePosixPath(normalized)
            if (not normalized or normalized.startswith("/") or
                any(part in (".", "..") for part in pure.parts) or
                re.match(r"^[a-zA-Z]:", normalized) or
                item.flag_bits & 0x1 or
                ((item.external_attr >> 16) & 0o170000) == 0o120000):
                raise ValueError(f"Unsafe ZIP entry: {item.filename!r}")
            total += item.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("Unpacked size exceeds safety limit")
        dest.mkdir(parents=True, exist_ok=False)
        try:
            for item in files:
                pure = PurePosixPath(item.filename.replace("\\", "/"))
                target = dest.joinpath(*pure.parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(item) as src, target.open("xb") as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    return {"extraction_dir": str(dest), "entries": len(files),
            "uncompressed_bytes": total,
            "warning": "Extracted data are local research assets, not cleared for GitHub redistribution."}
