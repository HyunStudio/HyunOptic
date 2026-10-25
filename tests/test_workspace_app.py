"""Research workspace UI on synthetic data only. Empty workspaces must never show numbers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from hyunoptic.demo_data import make_chaksu, make_papila
from hyunoptic.pipeline import run_pipeline
from hyunoptic.ui.charts import pr_points
from hyunoptic.ui.images import SYNTHETIC, list_cases, load_case, render_overlay
from hyunoptic.ui.workspace import (Workspace, append_history, chaksu_status, find_runs, load_run,
                                    papila_status, read_history)
from hyunoptic.viz import mask_outline

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGES = ["overview", "image_review", "datasets", "reliability", "source_holdout", "external_validation",
         "reports", "model_settings", "evidence_check", "batch_analysis", "legacy_study_results",
         "legacy_dataset_quality", "legacy_reader_roles", "model_inference", "model_experiment"]


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    base = tmp_path_factory.mktemp("demo")
    papila = make_papila(base / "PAPILA", patients=12)
    chaksu = make_chaksu(base / "Test.zip", per_camera=3)
    run_pipeline(papila, base / "reports" / "run_a", chaksu_test_zip=chaksu, allow_partial=True,
                 draws=100, bootstrap_draws=100)
    return base, papila, chaksu


def use_workspace(monkeypatch, folder: Path, **paths) -> Workspace:
    monkeypatch.setenv("HYUNOPTIC_WORKSPACE", str(folder / ".hyunoptic"))
    ws = Workspace(reports_dir=str(folder / "reports"), **paths)
    ws.save()
    return ws


def open_page(name: str) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=90).run()
    if name != "overview":
        app.switch_page(f"views/{name}.py").run()
    assert not app.exception, [str(e.message) for e in app.exception]
    return app


def page_text(app: AppTest) -> str:
    return " ".join(m.value for m in app.markdown)


@pytest.mark.parametrize("name", PAGES)
def test_every_page_renders_empty_workspace_without_invented_results(tmp_path, monkeypatch, name):
    use_workspace(monkeypatch, tmp_path)
    text = page_text(open_page(name))
    if name in ("reliability", "reports", "model_settings", "evidence_check"):
        assert "No analysis run yet" in text
    if name in ("source_holdout", "external_validation"):
        assert "No source-holdout results" in text or "No external results" in text
    if name == "overview":
        assert "Not run" in text and "0 of 2" in text


@pytest.mark.parametrize("name", PAGES[:10])
def test_every_page_renders_demo_run_and_flags_it_partial(demo, tmp_path, monkeypatch, name):
    base, papila, chaksu = demo
    use_workspace(monkeypatch, base, papila_root=str(papila), chaksu_zip=str(chaksu))
    monkeypatch.chdir(tmp_path)
    text = page_text(open_page(name))
    if name in ("reliability", "source_holdout", "external_validation", "reports"):
        assert "Partial or unverified inputs" in text
    if name == "overview":
        assert "Partial" in text and "Synthetic" not in text.split("Research Overview")[0]


def test_image_review_chaksu_five_expert_comparison(demo, monkeypatch):
    base, papila, chaksu = demo
    use_workspace(monkeypatch, base, papila_root=str(papila), chaksu_zip=str(chaksu))
    app = open_page("image_review")
    app.selectbox(key="ir_ds").set_value("Chákṣu").run()
    for k in range(5):
        app.checkbox(key=f"ir_e{k}").check()
    app.run()
    assert not app.exception, [str(e.message) for e in app.exception]
    text = page_text(app)
    assert "Cup (Expert 5)" in text and "dotted" in text
    app.button(key="ir_next").click().run()
    assert not app.exception
    assert app.session_state["selection"]["index"] == 1
    app.segmented_control(key="ir_tab").set_value("Quality").run()
    assert "Frozen lock" in page_text(app)  # combined score from the run's frozen lock


def test_batch_analysis_creates_run_and_integrity_check_logs_history(demo, tmp_path, monkeypatch):
    base, papila, chaksu = demo
    use_workspace(monkeypatch, tmp_path, papila_root=str(papila), chaksu_zip=str(chaksu))
    app = open_page("batch_analysis")
    app.text_input(key="ba_name").set_value("ui_run")
    app.button(key="ba_start").click().run()
    assert not app.exception, [str(e.message) for e in app.exception]
    manifest = json.loads((tmp_path / "reports" / "ui_run" / "pipeline_manifest.json").read_text())
    assert manifest["settings"]["allow_partial"] is True  # synthetic data defaults to partial
    app = open_page("datasets")
    app.selectbox(key="ic_dataset").set_value("Chákṣu").run()
    next(b for b in app.button if b.label == "Run Integrity Check").click().run()
    assert not app.exception, [str(e.message) for e in app.exception]
    entries = read_history("integrity")
    assert entries[0]["dataset"] == "Chákṣu" and entries[0]["check"] == "Full integrity check"


def test_workspace_status_runs_and_history(demo, tmp_path, monkeypatch):
    base, papila, chaksu = demo
    monkeypatch.setenv("HYUNOPTIC_WORKSPACE", str(tmp_path))
    p, c = papila_status(str(papila)), chaksu_status(str(chaksu))
    assert p.connected and p.synthetic and p.n_images == 24 and p.n_patients == 12
    assert c.connected and c.synthetic and c.n_images == 9
    assert not papila_status("").configured
    assert chaksu_status(str(tmp_path / "missing.zip")).state == "Error"
    runs = find_runs(base / "reports")
    assert [r.name for r in runs] == ["run_a"]
    run = load_run(runs[0])
    assert run.partial and run.lock_sha and run.source_rows and run.external_rows
    append_history("export", name="x")
    assert read_history("export")[0]["name"] == "x" and read_history("integrity") == []


def test_overlay_legend_styles_and_mask_outline(demo):
    _, papila, chaksu = demo
    ref = list_cases("Chákṣu", str(chaksu))[0]
    image, readers = load_case(ref, str(chaksu))
    assert len(readers) == 5
    _, legend = render_overlay(image, readers, experts=[0, 2], compare=True)
    assert [s for _, _, s in legend] == ["solid", "solid", "dashed", "dotted"]
    _, single = render_overlay(image, readers, experts=[0, 2], compare=False, dashed_cup=True)
    assert [s for _, _, s in single] == ["solid", "dashed"]
    image, readers = load_case(list_cases(SYNTHETIC, "")[0], "")
    assert image.size == (720, 540) and len(readers) == 2
    mask = np.zeros((60, 80), bool)
    mask[10:50, 20:60] = True
    outline = mask_outline(mask)
    assert outline[:, 0].min() >= 19 and outline[:, 0].max() <= 61


def test_pr_points_handles_ties_and_no_positives():
    recall, precision = pr_points([0.9, 0.9, 0.1, 0.5], [1, 0, 0, 1])
    assert recall.tolist() == [0.0, 0.5, 1.0, 1.0]
    assert precision.tolist() == [1.0, 0.5, 2 / 3, 0.5]
    assert pr_points([1, 2], [0, 0])[0].tolist() == [0.0]


def test_demo_data_cannot_pass_as_complete(demo):
    _, papila, _ = demo
    assert (papila / "SYNTHETIC_DEMO_DATA.txt").is_file()
    with Image.open(next((papila / "FundusImages").glob("*.jpg"))) as img:
        assert img.size == (640, 480)  # published PAPILA is 2576×1934


@pytest.mark.parametrize("change", ["location", "contents"])
def test_dataset_verification_is_invalidated_when_inputs_change(tmp_path, monkeypatch, change):
    root = make_papila(tmp_path / "PAPILA", patients=4)
    use_workspace(monkeypatch, tmp_path, papila_root=str(root))
    app = open_page("datasets")
    next(b for b in app.button if b.label == "Run Integrity Check").click().run()
    assert not app.exception
    assert page_text(app).split("Recent Verification History")[0].count("Never") == 1
    if change == "location":
        replacement = make_papila(tmp_path / "replacement", patients=4)
        app.text_input(key="pap_root").set_value(str(replacement))
        app.button(key="pap_save").click().run()
    else:
        contour = next((root / "ExpertsSegmentations" / "Contours").glob("*.txt"))
        contour.write_text("1 1\n2 2\n3 3\n", encoding="utf-8")
        app.run()
    assert not app.exception
    assert page_text(app).split("Recent Verification History")[0].count("Never") == 2
    assert any("Results and timings appear here" in caption.value for caption in app.caption)
