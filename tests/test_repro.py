"""Exercise v0.5 strict/partial execution with synthetic PAPILA-like contours only."""
import json

import numpy as np
import pytest
from PIL import Image
from hyunoptic.repro import reproduce


def make_fake_papila(tmp_path, patients=10):
    root = tmp_path / "PAPILA_DBv1"
    images = root / "FundusImages"
    contours = root / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    def rectangle(x1, y1, x2, y2):
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    for p in range(patients):
        for eye in ("OD", "OS"):
            stem = f"RET{p:03}{eye}"
            Image.new("RGB", (50, 50), "gray").save(images / f"{stem}.jpg")
            for expert in ("exp1", "exp2"):
                np.savetxt(contours / f"{stem}_disc_{expert}.txt",
                           rectangle(5, 5, 43, 43))
                np.savetxt(contours / f"{stem}_cup_{expert}.txt",
                           rectangle(18, 18 if expert == "exp1" else 17, 29, 30 + p % 4))
    return root


def test_strict_rejects_partial_with_inventory_saved(tmp_path):
    root = make_fake_papila(tmp_path)
    output = tmp_path / "results"
    with pytest.raises(ValueError, match="Full-data inventory failed"):
        reproduce(root, output, draws=50, bootstrap_draws=100)
    assert (output / "inventory.json").exists()
    assert not (output / "study.json").exists()


def test_explicit_partial_generates_fingerprinted_study(tmp_path):
    root = make_fake_papila(tmp_path)
    output = tmp_path / "results"
    report = reproduce(root, output, allow_partial=True, draws=50, bootstrap_draws=100)
    assert report["partial_or_unverified_input"] is True
    assert report["n_patients_with_results"] == 10
    assert report["n_images_with_results"] == 20
    assert (output / "run_manifest.json").exists()
    assert (output / "study.json").exists()
    assert (output / "case_metrics.csv").exists()
    body = json.loads((output / "study.json").read_text())
    assert body["summary"]["not_external_validation"] is True
    assert "clinical" in report["note"]
