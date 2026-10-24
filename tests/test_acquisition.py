"""Offline tests: synthetic files only, no third-party dataset bundled."""
import hashlib
import io
import json
import zipfile
import pytest
from hyunoptic.acquisition import ARTICLE_API, ARTICLE_ID, acquire_archive, figshare_metadata, safely_extract_archive

class FakeResponse(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

def opener(data, url):
    return lambda request, timeout=40: FakeResponse(data, url)

def zip_bytes(name="PAPILA_DBv1/example.txt"):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, "synthetic")
    return b.getvalue()

def metadata(data):
    return {
        "article_id": ARTICLE_ID, "file_id": 123,
        "bytes_expected": len(data), "figshare_md5": hashlib.md5(data).hexdigest(),
        "download_url": "https://ndownloader.figshare.com/files/123"
    }

def test_metadata_official():
    raw = json.dumps({"id": ARTICLE_ID, "version": 2, "files": [
        {"name": "PAPILA.zip", "id": 123, "size": 12345,
         "download_url": "https://ndownloader.figshare.com/files/123",
         "supplied_md5": "a" * 32}]}).encode()
    result = figshare_metadata(open_url=opener(raw, ARTICLE_API))
    assert result["version"] == 2 and result["file_id"] == 123

def test_reject_non_official_source():
    data = zip_bytes()
    bad = dict(metadata(data), download_url="https://evil.example.com/file")
    with pytest.raises(ValueError):
        acquire_archive("x.zip", accept_terms=True, metadata=bad)

def test_download_and_safe_extract(tmp_path):
    data = zip_bytes()
    target = tmp_path / "papila.zip"
    report = acquire_archive(target, accept_terms=True, metadata=metadata(data),
                             open_url=opener(data, "https://s3.amazonaws.com/object"))
    assert report["md5_verified_against_figshare"]
    assert report["sha256"] == hashlib.sha256(data).hexdigest()
    extracted = safely_extract_archive(target, tmp_path / "unpacked")
    assert extracted["entries"] == 1
    assert (tmp_path / "unpacked/PAPILA_DBv1/example.txt").read_text() == "synthetic"

def test_terms_and_existing_file(tmp_path):
    data = zip_bytes()
    path = tmp_path / "papila.zip"
    with pytest.raises(ValueError, match="accept"):
        acquire_archive(path, accept_terms=False, metadata=metadata(data))
    path.write_bytes(data)
    with pytest.raises(FileExistsError):
        acquire_archive(path, accept_terms=True, metadata=metadata(data))

def test_bad_hash_and_partial_download_cleanup(tmp_path):
    data = zip_bytes()
    path = tmp_path / "papila.zip"
    with pytest.raises(ValueError, match="MD5"):
        acquire_archive(path, accept_terms=True,
                        metadata=dict(metadata(data), figshare_md5="0" * 32),
                        open_url=opener(data, "https://figshare.com/file"))
    assert not path.exists()
    with pytest.raises(ValueError, match="Incomplete"):
        acquire_archive(path, accept_terms=True,
                        metadata=dict(metadata(data), bytes_expected=len(data) + 1),
                        open_url=opener(data, "https://figshare.com/file"))
    assert not path.exists()

@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "C:/drive.txt"])
def test_traversal_rejected(tmp_path, name):
    path = tmp_path / "unsafe.zip"
    path.write_bytes(zip_bytes(name))
    with pytest.raises(ValueError, match="Unsafe"):
        safely_extract_archive(path, tmp_path / "extract")
    assert not (tmp_path / "extract").exists()

def test_non_https_final_redirect(tmp_path):
    data = zip_bytes()
    with pytest.raises(ValueError, match="non-HTTPS"):
        acquire_archive(tmp_path / "papila.zip", accept_terms=True, metadata=metadata(data),
                        open_url=opener(data, "http://evil.example/file"))
