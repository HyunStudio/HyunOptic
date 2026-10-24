"""Synthetic filesystem fixtures: no PAPILA participant data involved."""
import json
import numpy as np
from PIL import Image
from hyunoptic.inventory import inspect_papila, save_inventory
from hyunoptic.inventory_cli import main


def case_fixture(tmp_path):
    root = tmp_path / "PAPILA_DBv1"
    images = root / "FundusImages"
    contours = root / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    pts = np.array([[5, 5], [18, 5], [18, 18], [5, 18]], float)
    for patient in (1, 2):
        for eye in ("OD", "OS"):
            stem = f"RET{patient:03}{eye}"
            Image.new("RGB", (32, 32), "black").save(images / f"{stem}.jpg")
            for expert in ("exp1", "exp2"):
                for structure in ("disc", "cup"):
                    np.savetxt(contours / f"{stem}_{structure}_{expert}.txt", pts)
    return root


def test_inventory_reports_counts_bilateral_structure_and_fingerprint(tmp_path):
    root = case_fixture(tmp_path)
    a = inspect_papila(root)
    b = inspect_papila(root)
    assert a == b
    assert a["observed"]["patients"] == 2
    assert a["observed"]["images"] == 4
    assert a["observed"]["bilateral_patients"] == 2
    assert a["observed"]["canonical_contours"] == 16
    assert a["observed"]["unusable_images"] == 0
    assert a["matches_full_published_shape"] is False
    assert len(a["inventory_sha256_of_paths_and_sizes_only"]) == 64
    assert a["hash_is_NOT_content_checksum"] is True
    assert all(row["warnings"] for row in a["cases"])  # intentionally tiny fixture


def test_missing_and_out_of_bounds_are_flagged(tmp_path):
    root = case_fixture(tmp_path)
    contour_dir = root / "ExpertsSegmentations" / "Contours"
    (contour_dir / "RET001OD_cup_exp2.txt").unlink()
    out = contour_dir / "RET002OS_disc_exp1.txt"
    np.savetxt(out, [[-1, 1], [2, 1], [2, 2], [-1, 2]])
    result = inspect_papila(root, verify_pixels=True)
    assert result["observed"]["unusable_images"] == 2
    assert any("RET001OD" == row["image_id"] and row["errors"] for row in result["cases"])
    assert any("RET002OS" == row["image_id"] and row["errors"] for row in result["cases"])


def test_duplicate_like_annotation_reported(tmp_path):
    root = case_fixture(tmp_path)
    orig = root / "ExpertsSegmentations" / "Contours" / "RET001OD_cup_exp2.txt"
    (orig.parent / "RET001OD_cup_exp2 2.txt").write_bytes(orig.read_bytes())
    result = inspect_papila(root)
    assert result["observed"]["duplicate_like_contours"] == 1
    assert result["observed"]["canonical_contours"] == 16


def test_inventory_command_writes_json_and_strict_rejects_partial(tmp_path):
    root = case_fixture(tmp_path)
    dest = tmp_path / "inventory.json"
    assert main(["--papila-root", str(root), "--output", str(dest)]) == 0
    assert json.loads(dest.read_text())["observed"]["patients"] == 2
    assert main(["--papila-root", str(root), "--output", str(dest), "--strict-full"]) == 2
