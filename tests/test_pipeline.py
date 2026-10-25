"""Synthetic fixtures only; a completed pipeline is NOT a scientific result."""
from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image

from hyunoptic.html_report import build_html_report, main as report_main
from hyunoptic.pipeline import main as pipeline_main, run_pipeline
from hyunoptic.viz import overlay_contours
from test_external import chaksu_fixture, source_fixture


def run(tmp_path, **kwargs):
    root = source_fixture(tmp_path / "PAPILA_DBv1", count=12)
    kwargs.setdefault("allow_partial", True)
    return run_pipeline(root, tmp_path / "out", draws=100, bootstrap_draws=100, **kwargs)


def test_full_chain_partial_fixture_runs_every_step(tmp_path):
    archive = chaksu_fixture(tmp_path / "Test.zip", cases=6)
    manifest = run(tmp_path, chaksu_test_zip=archive)
    out = tmp_path / "out"
    status = {s["name"]: s["status"] for s in manifest["steps"]}
    assert "failed" not in status.values()
    # Synthetic data must never look complete.
    for name in ("papila_inventory", "papila_source_holdout",
                 "chaksu_external_test", "evidence_gate"):
        assert status[name] == "incomplete"
    assert manifest["evidence_package_consistent"] is False
    assert manifest["scientific_validity_established"] is False
    assert manifest["clinical_accuracy_established"] is False
    for rel in ("model_lock.json", "source_holdout/source_aggregate.json",
                "external/external_aggregate.json", "evidence_review.json", "report.html"):
        assert (out / rel).is_file()
        assert rel in manifest["output_sha256"]
    assert "inventory.json" in manifest["private_local_files_not_for_sharing"]
    assert "external/external_private_cases.json" in manifest["private_local_files_not_for_sharing"]
    saved = json.loads((out / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert saved["steps"] == manifest["steps"]


def test_report_and_manifest_hold_no_case_identifiers(tmp_path):
    archive = chaksu_fixture(tmp_path / "Test.zip", cases=6)
    run(tmp_path, chaksu_test_zip=archive)
    out = tmp_path / "out"
    for rel in ("report.html", "pipeline_manifest.json"):
        text = (out / rel).read_text(encoding="utf-8")
        assert "RET00" not in text
        assert "IMG_00" not in text and "img_00" not in text
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "NOT for clinical use" in html
    assert "PARTIAL or UNVERIFIED" in html


def test_papila_only_run_skips_external_and_gate(tmp_path):
    manifest = run(tmp_path)
    status = {s["name"]: s["status"] for s in manifest["steps"]}
    assert status["chaksu_external_test"] == "skipped"
    assert status["evidence_gate"] == "skipped"
    assert status["papila_source_holdout"] == "incomplete"
    html = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "Chákṣu external analysis" in html  # listed as not included


def test_incomplete_source_is_refused_without_allow_partial(tmp_path):
    manifest = run(tmp_path, allow_partial=False)
    status = {s["name"]: s["status"] for s in manifest["steps"]}
    assert status["papila_inventory"] == "failed"
    assert status["freeze_papila_development"] == "skipped"
    assert not (tmp_path / "out" / "model_lock.json").exists()
    assert manifest["all_executed_steps_passed"] is False


def test_refuses_non_empty_output_and_cli_exit_codes(tmp_path):
    root = source_fixture(tmp_path / "PAPILA_DBv1", count=12)
    out = tmp_path / "out"
    args = ["--papila-root", str(root), "--output-dir", str(out),
            "--draws", "100", "--bootstrap-draws", "100"]
    assert pipeline_main(args) == 1  # incomplete source without --allow-partial
    with pytest.raises(SystemExit):
        pipeline_main(args)  # output folder already used
    strict = ["--papila-root", str(root), "--output-dir", str(tmp_path / "strict"),
              "--draws", "100", "--bootstrap-draws", "100", "--allow-partial", "--strict"]
    assert pipeline_main(strict) == 2


def test_html_escapes_text_and_drops_private_keys():
    html = build_html_report(
        source={"project": "HyunOptic", "partial_or_unverified": True,
                "limitations": ["<script>alert(1)</script>"],
                "failures": [{"case_id": "RET999OD"}]},
        generated_at="fixed")
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    assert "RET999OD" not in html
    assert "Evidence gate" in html  # missing inputs are named, not hidden


def test_html_report_cli(tmp_path):
    with pytest.raises(SystemExit):
        report_main(["--output", str(tmp_path / "r.html")])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"project": "Other"}))
    with pytest.raises(SystemExit):
        report_main(["--source-aggregate", str(bad), "--output", str(tmp_path / "r.html")])
    good = tmp_path / "audit.json"
    good.write_text(json.dumps({"project": "HyunOptic", "n_checked": 3,
                                "all_published_test_masks_structurally_verified": False,
                                "readable_by_camera": {"Bosch": 1}}))
    assert report_main(["--chaksu-audit", str(good), "--output", str(tmp_path / "r.html")]) == 0
    assert "all-five-reader" in (tmp_path / "r.html").read_text(encoding="utf-8")


def test_dashed_cup_and_high_contrast_overlay():
    img = Image.new("RGB", (80, 80))
    disc = np.array([[10, 10], [70, 10], [70, 70], [10, 70]], dtype=float)
    cup = np.array([[25, 25], [55, 25], [55, 55], [25, 55]], dtype=float)
    solid = np.asarray(overlay_contours(img, disc, cup, line_width=2, dashed_cup=False))
    dashed = np.asarray(overlay_contours(img, disc, cup, line_width=2, dashed_cup=True))
    cup_row_solid = solid[25, 25:56].any(axis=1)
    cup_row_dashed = dashed[25, 25:56].any(axis=1)
    assert cup_row_solid.all()
    assert 0 < cup_row_dashed.sum() < cup_row_solid.sum()  # visible gaps
    high = np.asarray(overlay_contours(img, disc, cup, line_width=2, palette="high_contrast"))
    assert tuple(high[10, 40]) == (0xFF, 0xD4, 0x00)
    with pytest.raises(ValueError):
        overlay_contours(img, disc, cup, palette="unknown")
