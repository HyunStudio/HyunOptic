"""Predeclared evaluation of a frozen bundle.

* Internal PAPILA holdout: evaluated ONCE. A second run is refused unless explicitly marked
  exploratory, which is then recorded in its report.
* Chákṣu Test: always EXPLORATORY, because Chákṣu was already inspected by the earlier
  candidate-QC protocol (design §Data gate 4).

Predictions are image-only. Expert 1 is the primary reference; expert 2 is a separate
reader-sensitivity reference; expert 1 vs 2 agreement is context, not a ceiling.
Aggregate reports hold no case identifiers; per-image rows go to a *private* file.
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .. import __version__
from ..chaksu import EXPERTS, load_test_case, scan_test_archive
from ..evaluation import patient_cluster_bootstrap_mean
from ..inventory import inspect_papila
from ..measure import measure_masks, polygon_mask
from ..papila import load_contours, load_image
from ..source_fingerprint import papila_content_sha256
from . import REPORT_SCHEMA, RESEARCH_THRESHOLD
from .bundle import SPLIT, Bundle
from .data import cases_for, verify_split_manifest
from .inference import Predictor
from .train import dice

HIST_BINS = [round(x, 2) for x in np.linspace(0, 1, 21)]


def _distribution(values: list[float]) -> dict:
    v = np.asarray(values, float)
    if not v.size:
        return {"n": 0}
    q = np.percentile(v, [0, 25, 50, 75, 100])
    counts, _ = np.histogram(np.clip(v, 0, 1), bins=HIST_BINS)
    return {"n": int(v.size), "mean": float(v.mean()), "min": float(q[0]), "q25": float(q[1]),
            "median": float(q[2]), "q75": float(q[3]), "max": float(q[4]),
            "histogram": {"bin_edges": HIST_BINS, "counts": counts.astype(int).tolist()}}


def _reference_metrics(pred, disc_ref: np.ndarray, cup_ref: np.ndarray) -> dict:
    ref = measure_masks(disc_ref, cup_ref)
    row = {"disc_dice": dice(pred.disc, disc_ref), "cup_dice": dice(pred.cup, cup_ref),
           "reference_vcdr": ref.vertical_cdr}
    if pred.measurement is not None:
        err = abs(pred.measurement["vertical_cdr"] - ref.vertical_cdr)
        row.update(abs_vcdr_error=err, vcdr_error_over_threshold=err > RESEARCH_THRESHOLD)
    return row


def _summarise(rows: list[dict], ref: str, patients: bool) -> dict:
    ok = [r for r in rows if r.get(ref)]
    out = {
        "disc_dice": _distribution([r[ref]["disc_dice"] for r in ok]),
        "cup_dice": _distribution([r[ref]["cup_dice"] for r in ok]),
        "abs_vcdr_error": _distribution([r[ref]["abs_vcdr_error"] for r in ok if "abs_vcdr_error" in r[ref]]),
    }
    errs = [r[ref]["vcdr_error_over_threshold"] for r in ok if "vcdr_error_over_threshold" in r[ref]]
    out["n_vcdr_error_over_threshold"] = int(sum(errs))
    out["fraction_vcdr_error_over_threshold"] = float(np.mean(errs)) if errs else None
    if patients:
        ids = [r["patient_id"] for r in ok]
        intervals = {}
        for name, key in (("cup_dice", "cup_dice"), ("disc_dice", "disc_dice"), ("abs_vcdr_error", "abs_vcdr_error")):
            pairs = [(r[ref][key], r["patient_id"]) for r in ok if key in r[ref]]
            try:
                intervals[name] = patient_cluster_bootstrap_mean([p[0] for p in pairs], [p[1] for p in pairs],
                                                                 draws=2000, seed=42)
            except ValueError as exc:
                intervals[name] = {"available": False, "reason": str(exc)}
        out["patient_cluster_bootstrap"] = intervals
        out["n_patients"] = len(set(ids))
    return out


def _failure_categories(rows: list[dict]) -> dict:
    cats: dict[str, int] = {}
    for r in rows:
        if r["status"] != "ok":
            cats[r["failure_category"]] = cats.get(r["failure_category"], 0) + 1
    return cats


def _write(folder: Path, report: dict, rows: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "model_eval_aggregate.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (folder / "model_eval_private_cases.json").write_text(
        json.dumps({"cases": rows}, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")


def _header(bundle: Bundle, kind: str, exploratory: bool, reason: str) -> dict:
    return {
        "schema": REPORT_SCHEMA, "project": "HyunOptic", "software_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation": kind, "exploratory": exploratory, "exploratory_reason": reason,
        "run_id": bundle.run_id, "weights_sha256": bundle.weights_sha256,
        "bundle_data_status": bundle.manifest["data_status"],
        "research_only": True, "not_clinical_validation": True,
        "prediction_inputs": "fundus image only (no expert masks, contours or expert-derived crops)",
        "research_threshold_abs_vcdr": RESEARCH_THRESHOLD,
    }


def evaluate_holdout(bundle: Bundle, papila_root: str | Path, *, exploratory_rerun: bool = False,
                     progress=None) -> Path:
    model = bundle.manifest
    root = Path(papila_root)
    if papila_content_sha256(root) != model["training"]["source_content_sha256"]:
        raise ValueError("PAPILA file contents differ from the data this bundle was trained on")
    split = verify_split_manifest(json.loads((bundle.folder / SPLIT).read_text(encoding="utf-8")))
    target = bundle.folder / "evaluation" / "papila_holdout"
    reason = ""
    if target.exists():
        if not exploratory_rerun:
            raise FileExistsError("The internal holdout was already evaluated for this bundle. A repeat is "
                                  "exploratory: pass --exploratory-rerun to record it as such.")
        target = bundle.folder / "evaluation" / f"papila_holdout_rerun_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
        reason = "Repeat evaluation of an already inspected holdout"
    predictor = Predictor(bundle)
    rows = []
    cases = cases_for(root, split, "holdout")
    for k, case in enumerate(cases, 1):
        row = {"image_id": case.image_id, "patient_id": case.patient_id, "eye": case.eye}
        try:
            image = load_image(case)
            pred = predictor.predict(image)       # image only
            row["status"] = pred.status
            if pred.status != "ok":
                row["failure_category"] = pred.status
                row["errors"] = pred.errors
            else:
                row["predicted_vcdr"] = pred.measurement["vertical_cdr"]
            refs = {}
            for reader in ("exp1", "exp2"):     # references are read only AFTER prediction
                d, c = load_contours(case, reader)
                refs[reader] = (polygon_mask(d, image.size), polygon_mask(c, image.size))
            if pred.labels is not None:
                row["expert1"] = _reference_metrics(pred, *refs["exp1"])
                row["expert2"] = _reference_metrics(pred, *refs["exp2"])
            m1, m2 = measure_masks(*refs["exp1"]), measure_masks(*refs["exp2"])
            row["expert1_vs_expert2"] = {"disc_dice": dice(refs["exp1"][0], refs["exp2"][0]),
                                         "cup_dice": dice(refs["exp1"][1], refs["exp2"][1]),
                                         "abs_vcdr_difference": abs(m1.vertical_cdr - m2.vertical_cdr)}
        except (OSError, ValueError) as exc:
            row.update(status="error", failure_category="load_or_geometry_error", errors=[str(exc)])
        rows.append(row)
        if progress is not None:
            progress(k, len(cases))
    inventory = inspect_papila(root)
    ok = [r for r in rows if r["status"] == "ok"]
    report = _header(bundle, "internal_papila_holdout", exploratory_rerun or bundle.partial, reason or (
        "Bundle trained on partial or synthetic data" if bundle.partial else ""))
    report.update({
        "dataset": "PAPILA", "split": "holdout", "split_manifest_sha256": model["training"]["split_manifest_sha256"],
        "source_content_sha256": model["training"]["source_content_sha256"],
        "source_inventory_complete": inventory["matches_full_published_shape"],
        "n_images": len(rows), "n_patients": len({r["patient_id"] for r in rows}),
        "n_evaluable": len(ok), "n_failed": len(rows) - len(ok), "failure_categories": _failure_categories(rows),
        "primary_reference": "expert 1 (training reader)",
        "versus_expert1": _summarise(rows, "expert1", patients=True),
        "versus_expert2_sensitivity": _summarise(rows, "expert2", patients=True),
        "reader_context_expert1_vs_expert2": {
            "disc_dice": _distribution([r["expert1_vs_expert2"]["disc_dice"] for r in rows if "expert1_vs_expert2" in r]),
            "cup_dice": _distribution([r["expert1_vs_expert2"]["cup_dice"] for r in rows if "expert1_vs_expert2" in r]),
            "abs_vcdr_difference": _distribution([r["expert1_vs_expert2"]["abs_vcdr_difference"]
                                                  for r in rows if "expert1_vs_expert2" in r]),
        },
        "limitations": [
            "Expert annotations are references, not disease truth; vCDR error is not diagnostic accuracy.",
            "Internal holdout from one dataset does not show cross-camera or cross-site generalisation.",
            "Intervals resample patients (both eyes together) and describe this cohort only.",
            "Softmax outputs are not calibrated uncertainty; no confidence score is reported.",
        ],
    })
    _write(target, report, rows)
    return target


def evaluate_chaksu(bundle: Bundle, test_zip: str | Path, *, progress=None) -> Path:
    """Exploratory external analysis on the (previously inspected) Chákṣu Test set."""
    target = bundle.folder / "evaluation" / f"chaksu_exploratory_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cases, layout = scan_test_archive(test_zip)
    predictor = Predictor(bundle)
    rows = []
    with zipfile.ZipFile(test_zip) as zf:
        for k, case in enumerate(cases, 1):
            row = {"case_id": case.case_id, "camera": case.camera}
            try:
                image, masks = load_test_case(zf, case, readers=EXPERTS)
                pred = predictor.predict(image)
                row["status"] = pred.status
                if pred.status != "ok":
                    row.update(failure_category=pred.status, errors=pred.errors)
                if pred.labels is not None:
                    row["expert1"] = _reference_metrics(pred, masks[("expert 1", "disc")], masks[("expert 1", "cup")])
                    row["expert2"] = _reference_metrics(pred, masks[("expert 2", "disc")], masks[("expert 2", "cup")])
            except (OSError, ValueError, KeyError) as exc:
                row.update(status="error", failure_category="load_or_geometry_error", errors=[str(exc)])
            rows.append(row)
            if progress is not None:
                progress(k, len(cases))
    report = _header(bundle, "exploratory_external_chaksu", True,
                     "Chákṣu was previously inspected by the HyunOptic candidate-QC protocol; "
                     "this is not untouched independent confirmation.")
    ok = [r for r in rows if r["status"] == "ok"]
    report.update({
        "dataset": "Chákṣu Test (binary masks of five experts; expert 1 primary)",
        "published_layout_matched": layout["matches_published_test_file_layout"],
        "n_images": len(rows), "n_evaluable": len(ok), "n_failed": len(rows) - len(ok),
        "failure_categories": _failure_categories(rows),
        "patient_linkage": "Not identifiable for most images; no patient-level intervals are computed.",
        "versus_expert1": _summarise(rows, "expert1", patients=False),
        "versus_expert2_sensitivity": _summarise(rows, "expert2", patients=False),
        "by_camera": {cam: _summarise([r for r in rows if r["camera"] == cam], "expert1", patients=False)
                      for cam in sorted({r["camera"] for r in rows})},
        "limitations": [
            "Exploratory only: dataset previously inspected; camera and annotation conventions differ from PAPILA.",
            "Chákṣu masks are binary images while PAPILA references are contours; boundaries may differ systematically.",
            "Images are not independent patients; no intervals are reported.",
        ],
    })
    _write(target, report, rows)
    return target
