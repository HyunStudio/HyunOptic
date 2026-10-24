"""Offline streaming provenance checks; synthetic bytes, no medical data."""
from __future__ import annotations
import hashlib
import json
import pytest
from hyunoptic.source_integrity import (
    REFERENCE_ARCHIVES, sha256_file, verify_archive, save_integrity_report
)
from hyunoptic.source_integrity_cli import main


def test_local_checksum_streamed_and_reference_matched(tmp_path, monkeypatch):
    filename = tmp_path / "PAPILA.zip"
    data = b"synthetic-zip-digest-only" * 200
    filename.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    monkeypatch.setitem(REFERENCE_ARCHIVES, "PAPILA",
                        {"filename": "PAPILA.zip", "sha256": expected,
                         "source": "https://github.com/repro/reference"})
    assert sha256_file(filename, chunk_size=1024) == (expected, len(data))
    check = verify_archive(filename, "PAPILA")
    assert check["matches_independent_public_reference"] is True
    assert check["image_data_uploaded"] is False
    assert "NOT a dataset publisher signature" in check["reference_type"]
    output = tmp_path / "sha.json"
    save_integrity_report([check], output)
    assert json.loads(output.read_text())["checks"][0]["computed_sha256"] == expected
    with pytest.raises(FileExistsError):
        save_integrity_report([], output)


def test_mismatch_is_reported_and_strict_cli_returns_2(tmp_path):
    archive = tmp_path / "PAPILA.zip"
    archive.write_bytes(b"different-revision")
    output = tmp_path / "verification.json"
    code = main(["--papila-zip", str(archive), "--output", str(output),
                 "--require-reference-match"])
    assert code == 2
    doc = json.loads(output.read_text())
    assert doc["checks"][0]["matches_independent_public_reference"] is False
    assert doc["images_uploaded"] is False


def test_invalid_source_and_missing_files_rejected(tmp_path):
    with pytest.raises(ValueError):
        verify_archive(tmp_path/"whatever.zip", "UNKNOWN")
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path/"missing.zip")
    with pytest.raises(ValueError):
        sha256_file(tmp_path/"missing.zip", chunk_size=7)
    with pytest.raises(SystemExit):
        main([])
