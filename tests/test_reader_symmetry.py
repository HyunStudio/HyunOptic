"""Direction reversal tests on wholly synthetic reader contours."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from hyunoptic.reader_symmetry import run_reader_symmetry, save_reader_symmetry
from hyunoptic.reader_cli import main as reader_cli
from hyunoptic.uncertainty import PerturbationConfig


def rect(x1, y1, x2, y2):
    return np.asarray([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=float)


def make_fake_papila(tmp_path, people=12):
    root = tmp_path / "PAPILA_DBv1"
    images = root / "FundusImages"
    contours = root / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    for patient in range(people):
        for eye in ("OD", "OS"):
            stem = f"RET{patient:03}{eye}"
            Image.new("RGB", (64, 64), (100 + patient, 100, 100)).save(images / f"{stem}.jpg")
            for expert in ("exp1", "exp2"):
                disc = rect(5, 5, 55, 55)
                cup = rect(20, 20, 38, 35 + (patient % 5) + (3 if expert == "exp2" else 0))
                np.savetxt(contours / f"{stem}_disc_{expert}.txt", disc)
                np.savetxt(contours / f"{stem}_cup_{expert}.txt", cup)
    return root


def test_symmetry_consistent_patient_split_and_direction_targets(tmp_path):
    root = make_fake_papila(tmp_path)
    kw = dict(config=PerturbationConfig(draws=80, seed=4), seed=8)
    summary, rows = run_reader_symmetry(root, **kw)
    assert summary == run_reader_symmetry(root, **kw)[0]
    assert summary["n_patients_analyzed"] == 12
    assert summary["n_images_analyzed"] == 24
    assert len(rows) == 48
    assert {r["candidate_reader"] for r in rows} == {"exp1", "exp2"}
    by_id = {}
    by_patient = {}
    for r in rows:
        by_id.setdefault(r["image_id"], []).append(r)
        by_patient.setdefault(r["patient_id"], set()).add(r["split"])
    assert all(len(v) == 2 for v in by_id.values())
    assert all(len(v) == 1 for v in by_patient.values())
    assert all(
        v[0]["heldout_absolute_vcdr_difference"] == v[1]["heldout_absolute_vcdr_difference"]
        for v in by_id.values()
    )
    assert summary["evaluation"]["holdout"]["exp1"]["scores"]["candidate_vcdr"]["ranking"]["not_glaucoma_diagnosis"]
    assert 0 <= summary["evaluation"]["holdout"]["reader_role_agreement"]["candidate_vcdr"]["top_k_overlap_fraction"] <= 1


def test_change_second_reader_does_not_change_first_direction_score(tmp_path):
    root = make_fake_papila(tmp_path)
    kw = dict(config=PerturbationConfig(draws=50, seed=1), seed=5)
    _, before = run_reader_symmetry(root, **kw)
    path = root / "ExpertsSegmentations" / "Contours" / "RET000OD_cup_exp2.txt"
    np.savetxt(path, rect(16, 15, 44, 47))
    _, after = run_reader_symmetry(root, **kw)
    left = {r["image_id"]: r for r in before if r["candidate_reader"] == "exp1"}
    right = {r["image_id"]: r for r in after if r["candidate_reader"] == "exp1"}
    for key in left:
        for score in ("v02_q95", "cup_roughness", "cup_boundary_weakness", "combined_candidate_score"):
            assert left[key][score] == right[key][score]
    assert left["RET000OD"]["heldout_absolute_vcdr_difference"] != right["RET000OD"]["heldout_absolute_vcdr_difference"]


def test_reader_cli_refuses_incomplete_archive_without_flag(tmp_path):
    root = make_fake_papila(tmp_path)
    out = tmp_path / "audit"
    with pytest.raises(SystemExit):
        reader_cli(["--papila-root", str(root), "--output-dir", str(out), "--draws", "50"])
    assert (out / "inventory.json").exists()
    assert not (out / "reader_symmetry.json").exists()


def test_reader_cli_explicit_partial_writes_reports(tmp_path):
    root = make_fake_papila(tmp_path)
    out = tmp_path / "audit"
    rc = reader_cli(["--papila-root", str(root), "--output-dir", str(out),
                     "--draws", "50", "--allow-partial"])
    assert rc == 0
    assert (out / "reader_symmetry.json").exists()
    assert (out / "reader_case_metrics.csv").exists()
    assert (out / "reader_role_summary.md").exists()
    text = (out / "reader_role_summary.md").read_text(encoding="utf-8")
    assert "Bland-Altman" in text and "NOT glaucoma diagnosis" in text
    assert "RET000OD" not in text

    s = json.loads((out / "reader_symmetry.json").read_text(encoding="utf-8"))["summary"]
    assert s["partial_or_unverified_input"]
    assert "reader_role_agreement" in s["evaluation"]["holdout"]
