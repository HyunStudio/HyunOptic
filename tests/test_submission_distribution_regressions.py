"""Submission boundary regressions using synthetic inputs only."""
import io
import json
import threading

import pytest
from PIL import Image

from hyunoptic.review.inputs import decode_image
from hyunoptic.review.store import ReviewStore
from hyunoptic.review import export

MODELS = [dict(folder=str(i), identity=str(i), run_id=str(i), weights_sha256=str(i) * 64)
          for i in range(2)]
BROKEN_PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000080000000808020000004b6d29dc0000000249444154789c639e181e00004fc80001ad40762200004f0049454e44ae426082")
BROKEN_TIFF = bytes.fromhex("49492a00080000000a0000010400010000000800000001010400010000000800000002010300030000008600000003010300010000000100000006010300010000000200000011010400010000008c0000001501030001000000030000001601040001000000080000001701040001000000c00000001c010300010000000100000000260000080008000800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")


def image_bytes():
    stream = io.BytesIO()
    Image.new("RGB", (8, 8)).save(stream, format="PNG")
    return stream.getvalue()


@pytest.mark.parametrize("data", [BROKEN_PNG, BROKEN_TIFF], ids=["png", "tiff"])
def test_malformed_decoder_errors_are_normalized(data):
    with pytest.raises(ValueError, match="cannot be decoded"):
        decode_image(data)


@pytest.mark.parametrize("data", [BROKEN_PNG, BROKEN_TIFF], ids=["png", "tiff"])
def test_malformed_image_does_not_abort_valid_neighbor(tmp_path, data):
    store = ReviewStore(tmp_path)
    sid = store.create_session([("valid.png", image_bytes()), ("malformed", data)], MODELS)
    cases = ReviewStore(tmp_path).cases(sid)
    assert [c["status"] for c in cases] == ["pending", "error"]
    assert cases[0]["input_path"].read_bytes() == image_bytes()
    assert "cannot be decoded" in cases[1]["error"]


def test_deleted_session_cannot_publish_inflight_managed_export(tmp_path, monkeypatch):
    store = ReviewStore(tmp_path)
    sid = store.create_session([("synthetic.png", image_bytes())], MODELS)
    target = store.root / "exports" / f"{sid}.zip"
    ready, resume = threading.Event(), threading.Event()
    original = export.verify_export

    def paused(path):
        result = original(path)
        ready.set()
        assert resume.wait(10), "export pause timed out"
        return result

    monkeypatch.setattr(export, "verify_export", paused)
    errors = []

    def worker():
        try:
            export.export_session(store, sid, target)
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        assert ready.wait(10), "export did not reach publication"
        # Separate connection/store represents another tab/process.
        ReviewStore(tmp_path).delete_session(sid)
    finally:
        resume.set()
        thread.join(10)
    assert not thread.is_alive()
    assert not store.sessions()
    assert not target.exists()
    assert len(errors) == 1 and isinstance(errors[0], ValueError)
    assert "Unknown session" in str(errors[0])
    assert not list(target.parent.glob(".review-export-*"))


def test_cli_report_uses_current_software_version(tmp_path, capsys):
    from hyunoptic import __version__
    from hyunoptic.cli import main
    from hyunoptic.demo_data import make_papila
    root = make_papila(tmp_path / "synthetic", patients=1, size=(160, 120))
    assert main(["--papila-root", str(root), "--draws", "30"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["version"] == __version__
