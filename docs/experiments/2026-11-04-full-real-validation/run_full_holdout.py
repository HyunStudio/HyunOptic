"""Full reused PAPILA holdout robustness audit; no training or clinical claims.

Run from the repository root with authorized local data. All output is PRIVATE;
only reviewed aggregate JSON, protocols and this harness may be published.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image


CONDITIONS = [
    ("original", "original", None),
    ("brightness_low", "brightness", .5),
    ("brightness_high", "brightness", 1.5),
    ("contrast_low", "contrast", .5),
    ("contrast_high", "contrast", 1.5),
    ("grayscale", "saturation", 0),
    ("gamma_low", "gamma", .7),
    ("gamma_high", "gamma", 1.5),
    ("blur", "blur_px", 2),
    ("noise", "gaussian_noise_sigma", 8),
    ("jpeg", "jpeg_quality", 25),
    ("downsample", "downsample_restore_width", 128),
    ("rgb_shift", "rgb_gains", [.7, 1.2, 1.2]),
]


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mean(values):
    return float(np.mean(values)) if values else None


def interval(values, patients):
    """Equal-patient mean and percentile interval; not an image-weighted CI."""
    from hyunoptic.evaluation import patient_cluster_bootstrap_mean
    if len(set(patients)) < 2:
        return {"available": False, "n_patients": len(set(patients))}
    return patient_cluster_bootstrap_mean(values, patients, draws=2000, seed=20261104)


def summarize(folder, cases):
    from hyunoptic.measure import dice, measure_masks, polygon_mask
    from hyunoptic.papila import load_contours, load_image
    from hyunoptic.review.validation import order_cases, evaluate_budget
    protocol_bytes = (folder / "protocol.json").read_bytes()
    protocol = json.loads(protocol_bytes)
    rows = json.loads((folder / "private_predictions.json").read_text())
    assert len(rows) == len(cases) * len(CONDITIONS) * 2
    references = {}
    for i, case in enumerate(cases):
        image = load_image(case)
        for reader in ("exp1", "exp2"):
            try:
                d, c = load_contours(case, reader)
                disc, cup = polygon_mask(d, image.size), polygon_mask(c, image.size)
                measured = measure_masks(disc, cup)
                references[i, reader] = (disc, cup, measured.vertical_cdr, measured.warnings)
            except (ValueError, OSError) as exc:
                references[i, reader] = str(exc)
    for i, row in enumerate(rows):
        row["metrics"] = {}
        if row["labels_file"] is None:
            continue
        path = folder / "private_predictions" / row["labels_file"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["labels_sha256"]
        with Image.open(io.BytesIO(data)) as image:
            labels = np.array(image)
        for reader in ("exp1", "exp2"):
            ref = references[row["case_index"], reader]
            if isinstance(ref, str):
                continue
            disc, cup, vcdr, warnings = ref
            row["metrics"][reader] = {
                "disc_dice": dice(labels >= 1, disc),
                "cup_dice": dice(labels == 2, cup),
                "abs_vcdr_error": abs(row["measurement"]["vertical_cdr"] - vcdr)
                if row["measurement"] is not None else None,
            }
        if (i + 1) % 100 == 0:
            print(json.dumps({"scored_predictions": i + 1}), flush=True)
    write(folder / "private_scored_rows.json", rows)
    originals = {(r["case_index"], r["model_index"]): r for r in rows if r["condition"] == "original"}
    scores = []
    for name, family, value in CONDITIONS:
        for mi in range(2):
            group = [r for r in rows if r["condition"] == name and r["model_index"] == mi]
            for reader in ("exp1", "exp2"):
                item = {"condition": name, "family": family, "value": value,
                        "model_index": mi, "reader": reader, "n_images": len(group),
                        "n_patients": len({cases[r["case_index"]].patient_id for r in group}),
                        "prediction_status_counts": dict(Counter(r["status"] for r in group)),
                        "reference_failures": sum(isinstance(references[r["case_index"], reader], str) for r in group),
                        "reference_warning_cases": sum(bool(references[r["case_index"], reader][3]) for r in group
                                                       if not isinstance(references[r["case_index"], reader], str)),
                        "metrics": {}, "paired_with_original": {}}
                for field in ("disc_dice", "cup_dice", "abs_vcdr_error"):
                    avail = [(r["metrics"][reader][field], cases[r["case_index"]].patient_id)
                             for r in group if r["metrics"].get(reader, {}).get(field) is not None]
                    item["metrics"][field] = {"n_images": len(avail), "image_weighted_mean": mean([x for x, _ in avail]),
                                              "equal_patient_bootstrap": interval([x for x, _ in avail], [p for _, p in avail])}
                    pairs = []
                    for row in group:
                        a = originals[row["case_index"], mi]["metrics"].get(reader, {}).get(field)
                        b = row["metrics"].get(reader, {}).get(field)
                        if a is not None and b is not None:
                            pairs.append((a, b, cases[row["case_index"]].patient_id))
                    item["paired_with_original"][field] = {
                        "n_common_images": len(pairs),
                        "original_image_mean": mean([a for a, b, p in pairs]),
                        "condition_image_mean": mean([b for a, b, p in pairs]),
                        "image_mean_change": mean([b-a for a, b, p in pairs]),
                        "equal_patient_change_bootstrap": interval([b-a for a, b, p in pairs], [p for a, b, p in pairs]),
                    }
                scores.append(item)
    queues = json.loads((folder / "private_priorities.json").read_text())
    lookup = {(r["condition"], r["case_index"], r["model_index"]): r for r in rows}
    budgets = []
    for name, family, value in CONDITIONS:
        ordered = order_cases([q for q in queues if q["condition"] == name])
        for reader in ("exp1", "exp2"):
            for threshold in (.4, .5, .6):
                events = []
                for q in ordered:
                    r = lookup[name, q["ordinal"], 0]
                    metric = r["metrics"].get(reader)
                    events.append(True if r["status"] != "ok" else
                                  (min(metric["disc_dice"], metric["cup_dice"]) < threshold if metric else None))
                budgets.append({"condition": name, "reader": reader, "error_definition_threshold": threshold,
                                "budgets": [evaluate_budget(events, review_fraction=f) for f in (.1, .2, .5)],
                                "n_unknown_reference_outcomes": sum(x is None for x in events)})
    reference_counts = {reader: {"available": sum(not isinstance(references[i, reader], str) for i in range(len(cases))),
                                  "failed": sum(isinstance(references[i, reader], str) for i in range(len(cases)))}
                        for reader in ("exp1", "exp2")}
    summary = {"schema": "hyunoptic-full-holdout-robustness/v1", "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
               "n_patients": len({c.patient_id for c in cases}), "n_original_images": len(cases),
               "n_conditions": len(CONDITIONS), "n_predictions": len(rows),
               "prediction_status_counts": dict(Counter(r["status"] for r in rows)),
               "references": reference_counts, "aggregates": scores, "review_budget_results": budgets,
               "interpretation": protocol["limitations"]}
    write(folder / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("aggregates", "review_budget_results")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--papila-root", type=Path, default=Path("data/PAPILA"))
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--summarize-existing", action="store_true")
    args = parser.parse_args()
    import torch
    from hyunoptic.papila import discover_cases, load_image
    from hyunoptic.seg.bundle import verify_bundle
    from hyunoptic.seg.data import verify_split_manifest
    from hyunoptic.seg.inference import Predictor
    from hyunoptic.source_fingerprint import papila_content_sha256
    from hyunoptic.review.priority import priority
    import hyunoptic.seg.inference as inference_module
    torch.set_num_threads(args.threads)
    bundles = [verify_bundle(Path("models") / name) for name in
               ("papila_real_seed43_20261025", "papila_camera_robust_seed43_20261025")]
    splits = [verify_split_manifest(json.loads((b.folder / "split_manifest.json").read_text())) for b in bundles]
    assert splits[0] == splits[1]
    cases = sorted([c for c in discover_cases(args.papila_root) if c.image_id in splits[0]["splits"]["holdout"]], key=lambda c: c.image_id)
    assert len(cases) == 98 and len({c.patient_id for c in cases}) == 49
    if args.summarize_existing:
        if (args.output / "summary.json").exists():
            raise FileExistsError("Refusing to overwrite summary")
        expected = json.loads((args.output / "private_selection.json").read_text())
        assert expected == [c.image_id for c in cases]
        summarize(args.output, cases)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    transformer = Path("docs/experiments/2026-11-04-literature-100/run_stress100.py")
    spec = importlib.util.spec_from_file_location("frozen_stress_transform", transformer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    content_hash = papila_content_sha256(args.papila_root)
    assert all(content_hash == b.manifest["training"]["source_content_sha256"] for b in bundles)
    protocol = {"schema": "hyunoptic-full-holdout-robustness-protocol/v1", "date_kst": "2026-11-04",
                "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "seed": 20261104, "device": "cpu", "threads": args.threads,
                "conditions": [{"name": n, "family": f, "value": v} for n, f, v in CONDITIONS],
                "n_patients": 49, "n_original_images": 98, "n_expected_predictions": 2548,
                "selection": "Every image in the preserved patient-disjoint PAPILA holdout; reused evaluation cohort.",
                "reference_read_after_all_predictions_and_priorities": True,
                "source_content_sha256": content_hash,
                "models": [{"identity": b.identity, "run_id": b.run_id, "weights_sha256": b.weights_sha256} for b in bundles],
                "source_sha256": {str(p): sha(p) for p in (Path(__file__).resolve().relative_to(Path.cwd()), transformer,
                                                           Path(inference_module.__file__).resolve().relative_to(Path.cwd()))},
                "evaluation": {"readers": ["exp1", "exp2"], "bootstrap_draws": 2000,
                               "bootstrap_estimand": "equal-patient mean, patient resampling; paired common-case changes",
                               "queue_event": "baseline invalid/error or min(disc Dice,cup Dice) below threshold",
                               "queue_thresholds": [.4, .5, .6], "review_fractions": [.1, .2, .5]},
                "limitations": ["Reused holdout, exploratory, correlated eyes and perturbations; not an independent clinical validation.",
                                "No training, target-label tuning, checkpoint selection or default-policy promotion.",
                                "Own fixed perturbation strengths informed by literature, not original author benchmark reproduction.",
                                "Conditional vCDR error must be read with availability and common-case comparisons.",
                                "Patient bootstrap is descriptive on this reused cohort, with no multiplicity-adjusted efficacy claims."]}
    write(args.output / "protocol.json", protocol)
    write(args.output / "private_selection.json", [c.image_id for c in cases])
    mask_dir = args.output / "private_predictions"
    mask_dir.mkdir()
    models = [Predictor(b) for b in bundles]
    rows, queues = [], []
    start = time.perf_counter()
    for pi, case in enumerate(cases):
        image = load_image(case)
        for ci, (name, family, value) in enumerate(CONDITIONS):
            transformed = module.transform(image, {"name": name, "family": family, "value": value}, 20261104 + ci * 1000 + pi)
            assert transformed.size == image.size
            pair = []
            for mi, model in enumerate(models):
                pred = model.predict(transformed)
                row = {"case_index": pi, "condition": name, "model_index": mi, "status": pred.status,
                       "measurement": pred.measurement, "errors": pred.errors, "labels_file": None, "labels_sha256": None}
                if pred.labels is not None:
                    assert pred.labels.shape == (image.height, image.width)
                    assert pred.labels.dtype == np.uint8 and set(np.unique(pred.labels)).issubset({0, 1, 2})
                    path = mask_dir / f"{pi:03}-{ci:02}-{mi}.png"
                    Image.fromarray(pred.labels).save(path)
                    row.update(labels_file=path.name, labels_sha256=sha(path))
                pair.append({**row, "labels_path": str(mask_dir / row["labels_file"]) if row["labels_file"] else None})
                rows.append(row)
            queues.append({"ordinal": pi, "condition": name, "priority": priority(pair)})
        write(args.output / "private_predictions.json", rows)
        write(args.output / "private_priorities.json", queues)
        print(json.dumps({"images_done": pi + 1, "n_images": len(cases), "predictions": len(rows),
                          "seconds": round(time.perf_counter() - start, 2)}), flush=True)
    assert len(rows) == 2548
    write(args.output / "inference_timing.json", {"wall_seconds": round(time.perf_counter() - start, 2),
                                                "scope": "image loading, transforms, inference, original-resolution metrics, mask saving and image-only priority; no reference scoring"})
    assert papila_content_sha256(args.papila_root) == content_hash
    assert all(verify_bundle(b.folder).identity == b.identity for b in bundles)
    summarize(args.output, cases)


if __name__ == "__main__":
    main()
