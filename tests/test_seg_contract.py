"""Segmentation contracts that need NO PyTorch: preprocessing, split, bundle/report schema, UI empty states."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from hyunoptic.demo_data import make_papila
from hyunoptic.measure import polygon_mask
from hyunoptic.seg import preprocess
from hyunoptic.seg.data import build_split_manifest, verify_split_manifest
from hyunoptic.seg.report import validate_report

APP = str(Path(__file__).resolve().parents[1] / "app.py")


# --- no PyTorch needed ---------------------------------------------------------------

def test_letterbox_round_trip_preserves_original_coordinates():
    w, h = 300, 200
    disc = np.array([[100, 50], [220, 50], [220, 170], [100, 170]], float)
    cup = np.array([[140, 90], [180, 90], [180, 130], [140, 130]], float)
    full = preprocess.class_map(polygon_mask(disc, (w, h)), polygon_mask(cup, (w, h)))
    lb = preprocess.plan(w, h, 96)
    assert (lb.new_w, lb.new_h, lb.pad_x, lb.pad_y) == (96, 64, 0, 16)
    back = preprocess.to_original(preprocess.letterbox_labels(full, lb), lb)
    assert back.shape == full.shape
    assert (back == full).mean() > 0.97  # only boundary pixels move under nearest resampling
    ys, xs = np.nonzero(back == 2)
    assert abs(xs.mean() - 160) < 3 and abs(ys.mean() - 110) < 3


def test_postprocess_keeps_largest_disc_and_cup_inside_it():
    labels = np.zeros((20, 20), np.uint8)
    labels[2:10, 2:10] = 1
    labels[4:7, 4:7] = 2
    labels[15:17, 15:17] = 2  # stray blob outside the main disc
    out = preprocess.postprocess(labels)
    assert out[15:17, 15:17].sum() == 0 and (out == 2).sum() == 9 and (out >= 1).sum() == 64
    with pytest.raises(ValueError):
        preprocess.plan(10, 10, 50)  # not a multiple of 16


def test_split_manifest_is_patient_disjoint_and_tamper_evident(tmp_path):
    root = make_papila(tmp_path / "P", patients=10)
    payload = build_split_manifest(root, seed=42)
    body = verify_split_manifest(payload)
    eyes = {i for ids in body["splits"].values() for i in ids}
    assert len(eyes) == 20
    for split, ids in body["splits"].items():
        assert {i[:6] for i in ids} == set(body["patients"][split])  # both eyes together
    assert build_split_manifest(root, seed=42)["sha256"] == payload["sha256"]
    payload["manifest"]["splits"]["holdout"].append("RET999OD")
    with pytest.raises(ValueError, match="SHA-256"):
        verify_split_manifest(payload)


def test_report_schema_rejects_unlabelled_external_and_foreign_json():
    good = {"schema": "hyunoptic.seg_experiment_report/v1", "project": "HyunOptic",
            "evaluation": "exploratory_external_chaksu", "exploratory": True, "run_id": "r",
            "n_images": 1, "n_failed": 0, "versus_expert1": {}}
    assert validate_report(dict(good))
    with pytest.raises(ValueError, match="exploratory"):
        validate_report({**good, "exploratory": False})
    with pytest.raises(ValueError):
        validate_report({"project": "HyunOptic"})


def test_workspace_ui_never_imports_torch():
    code = ("import sys, hyunoptic.ui.state, hyunoptic.ui.review, hyunoptic.seg.bundle, hyunoptic.seg.preprocess, hyunoptic.seg.report, hyunoptic.ui.model_ui; "
            "print('torch' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


# --- UI pages ------------------------------------------------------------------------

def _page(monkeypatch, folder: Path, name: str, **ws) -> AppTest:
    from hyunoptic.ui.workspace import Workspace
    monkeypatch.setenv("HYUNOPTIC_WORKSPACE", str(folder / ".hyunoptic"))
    Workspace(reports_dir=str(folder / "reports"), **ws).save()
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.switch_page(f"views/{name}.py").run()
    assert not app.exception, [str(e.message) for e in app.exception]
    return app


def _text(app) -> str:
    return " ".join(m.value for m in app.markdown)


def test_model_pages_honest_empty_states(tmp_path, monkeypatch):
    from hyunoptic.seg import torch_available
    app = _page(monkeypatch, tmp_path, "model_inference", models_dir=str(tmp_path / "none"))
    # Without PyTorch the first failed gate is the missing extra; with it, the missing bundle.
    expected = "No verified local model loaded" if torch_available() else "PyTorch is not installed"
    assert expected in _text(app)
    app = _page(monkeypatch, tmp_path, "model_experiment", models_dir=str(tmp_path / "none"))
    assert "No model experiment yet" in _text(app)
    monkeypatch.setenv("HYUNOPTIC_DISABLE_TORCH", "1")
    app = _page(monkeypatch, tmp_path, "model_inference", models_dir=str(tmp_path / "none"))
    assert "PyTorch is not installed" in _text(app)
