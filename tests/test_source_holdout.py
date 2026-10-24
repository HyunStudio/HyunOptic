"""All fixtures are synthetic PAPILA-shaped data; no clinical performance data."""
import json
import numpy as np
import pytest
from PIL import Image

from hyunoptic.freeze import freeze_papila_model, save_lock
from hyunoptic.source_holdout import evaluate_source, save_source_evaluation
from hyunoptic.source_holdout_cli import main as source_main


def rectangle(x1, y1, x2, y2):
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=float)


def create_fixture(tmp_path, people=12):
    root = tmp_path / "PAPILA_DBv1"
    images = root / "FundusImages"
    outlines = root / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    outlines.mkdir(parents=True)
    for p in range(people):
        for eye in ("OD", "OS"):
            name = f"RET{p:03}{eye}"
            Image.new("RGB", (48, 48), (90+p*2, 95, 100)).save(images / (name+".jpg"))
            for expert in ("exp1", "exp2"):
                np.savetxt(outlines / f"{name}_disc_{expert}.txt",
                           rectangle(5,5,42,42))
                np.savetxt(outlines / f"{name}_cup_{expert}.txt",
                           rectangle(14,12+(p%3)+(expert=="exp2"),31,31+(p%5)+(expert=="exp2")*3))
    return root


def freeze(tmp_path, root):
    path = tmp_path / "papila.lock.json"
    save_lock(freeze_papila_model(root, seed=11, draws=70, allow_partial=True), path)
    return path


def test_locked_same_mask_family_and_patient_disjoint_outputs(tmp_path):
    root = create_fixture(tmp_path)
    lock = freeze(tmp_path, root)
    report, rows = evaluate_source(root, lock, allow_partial=True, bootstrap_draws=100)
    again, rows2 = evaluate_source(root, lock, allow_partial=True, bootstrap_draws=100)
    assert report == again and rows == rows2
    assert report["version"] == "1.0.0rc3"
    assert report["not_external_validation"] is True
    assert report["partial_or_unverified"] is True
    assert report["n_evaluated_images"] == len(rows)
    assert set(report["evaluation"]) == {"validation", "holdout"}
    assert "paired_patient_bootstrap_holdout" in report
    patient_splits = {}
    for row in rows:
        patient_splits.setdefault(row["patient_id"], set()).add(row["split"])
        assert "mask_q95" in row and "mask_roughness" in row
        assert "combined_candidate_score" in row
    assert all(len(v) == 1 for v in patient_splits.values())
    assert all(r["split"] != "development" for r in rows)
    assert "mask_q95" in report["evaluation"]["holdout"]["scores"]


def test_second_reader_has_no_influence_on_candidate_scoring(tmp_path):
    root = create_fixture(tmp_path)
    first_lock = freeze(tmp_path, root)
    before, before_rows = evaluate_source(root, first_lock, allow_partial=True, bootstrap_draws=100)
    target = next(r["image_id"] for r in before_rows if r["split"]=="holdout")
    annotation = root / "ExpertsSegmentations" / "Contours" / f"{target}_cup_exp2.txt"
    np.savetxt(annotation, rectangle(12,11,34,35))
    # Changing a reference contour invalidates the raw-data fingerprint;
    # refreeze to compare candidate-only score invariance fairly.
    with pytest.raises(ValueError, match="source CONTENT differs"):
        evaluate_source(root, first_lock, allow_partial=True, bootstrap_draws=100)
    new_lock = tmp_path / "new_model_lock.json"
    save_lock(freeze_papila_model(root, seed=11, draws=70, allow_partial=True), new_lock)
    after, after_rows = evaluate_source(root, new_lock, allow_partial=True, bootstrap_draws=100)
    assert {k: before["patient_split_counts"][k] for k in before["patient_split_counts"]} == after["patient_split_counts"]
    assert before["n_evaluated_images"] == after["n_evaluated_images"]
    a = {r["image_id"]:r for r in before_rows}
    b = {r["image_id"]:r for r in after_rows}
    for uid in a:
        for field in ("candidate_vcdr", "mask_q95", "mask_roughness",
                      "mask_boundary_weakness", "combined_candidate_score"):
            assert a[uid][field] == b[uid][field]
    assert a[target]["absolute_reader_vcdr_disagreement"] != b[target]["absolute_reader_vcdr_disagreement"]


def test_strict_mode_never_claims_full_source_from_fixture(tmp_path):
    root = create_fixture(tmp_path)
    lock = freeze(tmp_path, root)
    with pytest.raises(ValueError, match="Partial PAPILA"):
        evaluate_source(root, lock, allow_partial=False)
    output = tmp_path / "source_results"
    assert source_main(["--papila-root",str(root), "--model-lock",str(lock),
                        "--output-dir",str(output),"--bootstrap-draws","100",
                        "--allow-partial"]) == 0
    assert (output/"source_aggregate.json").exists()
    assert (output/"source_private_cases.json").exists()
    assert (output/"source_summary.md").exists()
    public = (output/"source_aggregate.json").read_text()
    assert "RET000OD" not in public
    assert '"patient_id"' not in public
    assert '"failures"' not in public
    summary = json.loads(public)
    assert summary["source_lock_sha256"] == json.loads(lock.read_text())["sha256"]
    with pytest.raises(FileExistsError):
        save_source_evaluation(summary, [], output)
