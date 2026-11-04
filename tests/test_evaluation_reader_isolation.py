"""A failed reference must not erase independent image-only predictions/readers."""
from __future__ import annotations

import json
import struct
from types import SimpleNamespace
import zipfile

import numpy as np
from PIL import Image
import pytest

pytest.importorskip("torch")
from hyunoptic.seg import evaluate
from hyunoptic.seg.inference import Prediction
from hyunoptic.measure import measure_masks
from hyunoptic.demo_data import make_chaksu


def bundle(tmp_path):
    return SimpleNamespace(folder=tmp_path / "bundle", run_id="isolated", weights_sha256="a" * 64,
                           synthetic=False, partial=False, manifest={"data_status": "real", "training": {
                               "source_content_sha256": "source", "split_manifest_sha256": "split"}})


def install_predictor(monkeypatch, status="ok"):
    calls = []

    class Fixed:
        def __init__(self, _bundle):
            pass

        def predict(self, image):
            calls.append(image.size)
            if status == "error":
                return Prediction("error", image.size, errors=["model failed"])
            labels = np.zeros((image.height, image.width), np.uint8)
            labels[10:60, 10:60] = 1
            labels[25:45, 25:45] = 2
            return Prediction("ok", image.size, labels=labels,
                              measurement=measure_masks(labels >= 1, labels == 2).to_dict())

    monkeypatch.setattr(evaluate, "Predictor", Fixed)
    return calls


def corrupt_member(path, fragment):
    with zipfile.ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    selected = next(n for n in members if fragment in n)
    members[selected] = b"deliberately invalid image"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


def corrupt_crc(path, fragment):
    with zipfile.ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    with zipfile.ZipFile(path) as archive:
        entry = next(v for v in archive.infolist() if fragment in v.filename)
    raw = bytearray(path.read_bytes())
    name_len, extra_len = struct.unpack_from("<HH", raw, entry.header_offset + 26)
    start = entry.header_offset + 30 + name_len + extra_len
    raw[start + entry.file_size // 2] ^= 1
    path.write_bytes(raw)


@pytest.mark.parametrize("image_member", [False, True])
def test_chaksu_crc_failure_is_isolated_to_reader_or_image(tmp_path, monkeypatch, image_member):
    path = make_chaksu(tmp_path / "Test.zip", per_camera=1)
    fragment = "Original_Fundus_Images/Bosch/" if image_member else "Expert 3/Bosch/Disc/"
    corrupt_crc(path, fragment)
    calls = install_predictor(monkeypatch)
    folder = evaluate.evaluate_chaksu(bundle(tmp_path), path)
    rows = json.loads((folder / "model_eval_private_cases.json").read_text())["cases"]
    row = next(r for r in rows if r["camera"] == "bosch")
    assert len(rows) == 3 and len(calls) == (2 if image_member else 3)
    if image_member:
        assert row["status"] == "error" and row["failure_category"] == "image_load_or_prediction_error"
    else:
        assert row["status"] == "ok" and "expert3" in row["reference_errors"]
        assert "expert1" in row and "expert2" in row and "expert4" in row and "expert5" in row


@pytest.mark.parametrize("bad_reader", [1, 3, 5])
def test_chaksu_bad_reader_keeps_prediction_and_other_readers(tmp_path, monkeypatch, bad_reader):
    path = make_chaksu(tmp_path / "Test.zip", per_camera=1)
    corrupt_member(path, f"Expert {bad_reader}/Bosch/Cup/")
    calls = install_predictor(monkeypatch)
    folder = evaluate.evaluate_chaksu(bundle(tmp_path), path)
    rows = json.loads((folder / "model_eval_private_cases.json").read_text())["cases"]
    report = json.loads((folder / "model_eval_aggregate.json").read_text())
    assert len(calls) == 3  # all image-only predictions, irrespective of reference integrity
    row = next(r for r in rows if r["camera"] == "bosch")
    assert row["status"] == "ok"
    assert row["reference_errors"].keys() == {f"expert{bad_reader}"}
    for reader in range(1, 6):
        assert (f"expert{reader}" in row) == (reader != bad_reader)
        assert report["versus_all_experts"][f"expert{reader}"]["cup_dice"]["n"] == (2 if reader == bad_reader else 3)
    assert report["n_failed"] == 0
    assert report["reference_failures_by_reader"][f"expert{bad_reader}"] == 1


def test_chaksu_prediction_error_is_not_overwritten_by_reference_error(tmp_path, monkeypatch):
    path = make_chaksu(tmp_path / "Test.zip", per_camera=1)
    corrupt_member(path, "Expert 1/Bosch/Cup/")
    calls = install_predictor(monkeypatch, "error")
    folder = evaluate.evaluate_chaksu(bundle(tmp_path), path)
    rows = json.loads((folder / "model_eval_private_cases.json").read_text())["cases"]
    assert len(calls) == 3
    assert all(r["status"] == "error" and r["failure_category"] == "error" and r["errors"] == ["model failed"] for r in rows)
    assert next(r for r in rows if r["camera"] == "bosch")["reference_errors"]


def test_chaksu_missing_reference_does_not_remove_original_image(tmp_path, monkeypatch):
    path = make_chaksu(tmp_path / "Test.zip", per_camera=1)
    with zipfile.ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist()
                   if "Expert 3/Bosch/Disc/" not in n}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    calls = install_predictor(monkeypatch)
    folder = evaluate.evaluate_chaksu(bundle(tmp_path), path)
    report = json.loads((folder / "model_eval_aggregate.json").read_text())
    assert len(calls) == report["n_images"] == 3
    assert report["versus_all_experts"]["expert1"]["cup_dice"]["n"] == 3
    assert report["versus_all_experts"]["expert3"]["cup_dice"]["n"] == 2
    assert report["reference_failures_by_reader"]["expert3"] == 1


def test_holdout_bad_second_reader_keeps_first_reader_and_prediction(tmp_path, monkeypatch):
    b = bundle(tmp_path)
    b.folder.mkdir()
    (b.folder / evaluate.SPLIT).write_text("{}")
    case = SimpleNamespace(image_id="RET001OD", patient_id="RET001", eye="OD")
    monkeypatch.setattr(evaluate, "papila_content_sha256", lambda _root: "source")
    monkeypatch.setattr(evaluate, "verify_split_manifest", lambda _value: {})
    monkeypatch.setattr(evaluate, "cases_for", lambda *_args: [case])
    monkeypatch.setattr(evaluate, "inspect_papila", lambda _root: {"matches_full_published_shape": False})
    monkeypatch.setattr(evaluate, "load_image", lambda _case: Image.new("RGB", (80, 80)))

    def contour(_case, reader):
        if reader == "exp2":
            raise ValueError("invalid second-reader contour")
        return np.array([[10, 10], [59, 10], [59, 59], [10, 59]]), np.array([[25, 25], [44, 25], [44, 44], [25, 44]])

    monkeypatch.setattr(evaluate, "load_contours", contour)
    install_predictor(monkeypatch)
    folder = evaluate.evaluate_holdout(b, tmp_path)
    row = json.loads((folder / "model_eval_private_cases.json").read_text())["cases"][0]
    report = json.loads((folder / "model_eval_aggregate.json").read_text())
    assert row["status"] == "ok" and row["expert1"]["cup_dice"] == 1
    assert "expert2" not in row and "expert2" in row["reference_errors"]
    assert report["n_failed"] == 0 and report["reference_failures_by_reader"]["expert2"] == 1
    assert report["versus_expert1"]["cup_dice"]["n"] == 1


@pytest.mark.parametrize("synthetic,partial", [(True, False), (False, True), (True, True), (False, False)])
@pytest.mark.parametrize("rerun", [False, True])
def test_holdout_report_labels_data_status_and_remains_readable(tmp_path, monkeypatch, synthetic, partial, rerun):
    from hyunoptic.demo_data import make_papila
    from hyunoptic.seg.data import build_split_manifest
    from hyunoptic.seg.report import validate_report

    root = make_papila(tmp_path / "P", patients=10, size=(80, 80))
    split = build_split_manifest(root)
    b = bundle(tmp_path)
    b.synthetic, b.partial = synthetic, partial
    b.manifest["data_status"] = {"synthetic": synthetic, "partial": partial}
    b.manifest["training"].update(source_content_sha256=evaluate.papila_content_sha256(root),
                                   split_manifest_sha256=split["sha256"])
    b.folder.mkdir()
    (b.folder / evaluate.SPLIT).write_text(json.dumps(split), encoding="utf-8")
    install_predictor(monkeypatch)
    evaluate.evaluate_holdout(b, root)
    if rerun:
        folder = evaluate.evaluate_holdout(b, root, exploratory_rerun=True)
    else:
        folder = b.folder / "evaluation" / "papila_holdout"
    report = json.loads((folder / "model_eval_aggregate.json").read_text(encoding="utf-8"))

    assert report["exploratory"] is (synthetic or partial or rerun)
    assert validate_report(report, bundle=b) is report
    if rerun:
        assert report["exploratory_reason"] == "Repeat evaluation of an already inspected holdout"
    elif synthetic or partial:
        assert "partial or synthetic" in report["exploratory_reason"]
    else:
        assert report["exploratory_reason"] == ""
