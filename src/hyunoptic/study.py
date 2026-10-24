"""Patient-disjoint PAPILA research benchmark; not external or clinical validation.

Rules: candidate features are produced from image + exp1 contour only; exp2
is loaded exclusively for retrospective outcomes AFTER feature production.
No labels inform candidate features, normalization or ranking weights.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .evaluation import evaluate_at_budget
from .features import FEATURE_NAMES, candidate_features
from .measure import compare_readers
from .papila import discover_cases, load_contours, load_image
from .uncertainty import PerturbationConfig

def patient_splits(patient_ids: list[str], seed: int = 42) -> dict[str, str]:
    """Stable 60/20/20 split by PATIENT (both eyes stay in the same split)."""
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be nonnegative integer")
    if not patient_ids or any(not str(p).strip() for p in patient_ids):
        raise ValueError("patient IDs cannot be empty")
    ids = sorted(set(patient_ids), key=lambda p: hashlib.sha256(
        f"{seed}|{p}".encode("utf-8")).hexdigest())
    n = len(ids)
    if n < 5:
        raise ValueError("at least five distinct patients required")
    a = max(1, int(0.6 * n))
    b = max(a + 1, int(0.8 * n))
    if b >= n:
        raise ValueError("not enough patients for three-way split")
    return {p: ("development" if i < a else "validation" if i < b else "holdout")
            for i, p in enumerate(ids)}

def _training_scaler(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Fixed unlabelled train-only feature standardizer, never uses outcomes."""
    development = [row for row in rows if row["split"] == "development"]
    if not development:
        raise ValueError("no development observations")
    params: dict[str, dict[str, float]] = {}
    for name in FEATURE_NAMES:
        values = np.asarray([r[name] for r in development], dtype=float)
        mu = float(values.mean())
        sd = float(values.std(ddof=0))
        params[name] = {"mean": mu, "sd": sd if sd > 1e-12 else 1.0}
    return params

def _apply_candidate_only_combination(rows: list[dict]) -> dict[str, dict[str, float]]:
    norm = _training_scaler(rows)
    for row in rows:
        # Fixed equal-weight UNSUPERVISED score; no target values or expert2 inputs.
        standardized = [float(np.clip((row[name] - norm[name]["mean"]) / norm[name]["sd"], -3.0, 3.0))
                        for name in FEATURE_NAMES]
        row["combined_candidate_score"] = 3.0 + sum(standardized) / len(standardized)
    return norm

def _patient_bootstrap_difference(
    rows: list[dict], *, baseline: str, candidate: str,
    threshold: float, fraction: float, seed: int = 42, draws: int = 1000,
) -> dict:
    """Paired patient-cluster percentile CI on delta precision@review-budget."""
    if draws < 100 or draws > 100_000:
        raise ValueError("draws must be between 100 and 100000")
    group: dict[str, list[dict]] = {}
    for row in rows:
        group.setdefault(row["patient_id"], []).append(row)
    ids = sorted(group)
    if len(ids) < 2:
        return {"available": False, "reason": "fewer than 2 patients"}
    rng = np.random.default_rng(seed)
    diffs = np.empty(draws, dtype=float)
    for i in range(draws):
        chosen = rng.integers(0, len(ids), size=len(ids))
        sample = [row for ix in chosen for row in group[ids[int(ix)]]]
        ref = np.asarray([r["heldout_absolute_vcdr_difference"] for r in sample])
        b = evaluate_at_budget([r[baseline] for r in sample], ref,
                               discrepancy_threshold=threshold, review_fraction=fraction)
        c = evaluate_at_budget([r[candidate] for r in sample], ref,
                               discrepancy_threshold=threshold, review_fraction=fraction)
        diffs[i] = c.precision_at_budget - b.precision_at_budget
    lo, hi = np.percentile(diffs, (2.5, 97.5))
    return {
        "available": True, "n_patients": len(ids), "draws": draws, "seed": seed,
        "metric": f"{candidate} minus {baseline} precision_at_budget",
        "delta_mean_bootstrap": float(np.mean(diffs)),
        "delta_95_percentile_interval": [float(lo), float(hi)],
        "interpretation": "Exploratory patient-cluster interval, not an externally validated effect.",
    }

def run_study(
    root: str | Path, *, config: PerturbationConfig | None = None,
    split_seed: int = 42, discrepancy_threshold: float = 0.10,
    review_fraction: float = 0.20, bootstrap_draws: int = 1000,
) -> tuple[dict, list[dict]]:
    """PAPILA-only patient-disjoint research benchmark with untrained baselines.

    These comparisons are hypothesis-generating; no held-out generalization
    is established until this protocol is locked and a real dataset is run.
    """
    config = config or PerturbationConfig()
    config.validate()
    cases = discover_cases(root)
    if not cases:
        raise ValueError("no complete PAPILA cases found")
    split_by_patient = patient_splits([c.patient_id for c in cases], seed=split_seed)
    rows, skipped = [], []
    for case in cases:
        try:
            image = load_image(case)
            d1, c1 = load_contours(case, "exp1")
            # Security boundary: candidate_features has no exp2 data argument.
            features = candidate_features(image, d1, c1, config)
            d2, c2 = load_contours(case, "exp2")
            outcome = compare_readers(d1, c1, d2, c2, image.size)
            row = {
                "patient_id": case.patient_id, "image_id": case.image_id, "eye": case.eye,
                "split": split_by_patient[case.patient_id],
                **features,
                "heldout_absolute_vcdr_difference": outcome["absolute_vcdr_difference"],
                "retrospective_disc_dice": outcome["disc_dice"],
                "retrospective_cup_dice": outcome["cup_dice"],
            }
            if any(not np.isfinite(v) for v in features.values()):
                raise ValueError("non-finite candidate feature")
            rows.append(row)
        except (OSError, ValueError, RuntimeError) as exc:
            skipped.append({"image_id": case.image_id, "reason": str(exc)})
    if not rows:
        raise ValueError("no usable PAPILA cases")
    if len({r["patient_id"] for r in rows}) < 5:
        raise ValueError("insufficient usable patient groups")
    if any(not any(r["split"] == split for r in rows)
           for split in ("development", "validation", "holdout")):
        raise ValueError("skipped annotations caused an empty evaluation split")
    norm = _apply_candidate_only_combination(rows)
    scores = list(FEATURE_NAMES) + ["combined_candidate_score", "candidate_vcdr"]
    results: dict[str, dict] = {}
    for split in ("validation", "holdout"):
        subset = [r for r in rows if r["split"] == split]
        y = [r["heldout_absolute_vcdr_difference"] for r in subset]
        results[split] = {
            "n_images": len(subset),
            "n_patients": len({r["patient_id"] for r in subset}),
            "scores": {
                metric: evaluate_at_budget(
                    [r[metric] for r in subset], y,
                    discrepancy_threshold=discrepancy_threshold,
                    review_fraction=review_fraction,
                ).to_dict() for metric in scores
            },
        }
    holdout = [r for r in rows if r["split"] == "holdout"]
    bs = _patient_bootstrap_difference(
        holdout, baseline="v02_q95", candidate="combined_candidate_score",
        threshold=discrepancy_threshold, fraction=review_fraction,
        draws=bootstrap_draws, seed=split_seed,
    )
    protocol_settings = {
        "split_method": "sha256(seed|patient_id) ordered 60/20/20",
        "split_seed": split_seed, "perturbation": asdict(config),
        "discrepancy_threshold_research_only": discrepancy_threshold,
        "review_fraction": review_fraction,
        "candidate_features": list(FEATURE_NAMES),
        "combo": "train-only z-score each feature, clip [-3,3], equal weight, add 3",
    }
    protocol_hash = hashlib.sha256(json.dumps(protocol_settings, sort_keys=True).encode()).hexdigest()
    summary = {
        "project": "HyunOptic", "version": "0.3.0", "status": "research-only",
        "study_type": "PAPILA-only exploratory patient-disjoint INTERNAL holdout",
        "not_external_validation": True, "not_clinical_diagnosis": True,
        "protocol_sha256": protocol_hash, "protocol_settings": protocol_settings,
        "n_analyzed": len(rows), "n_skipped": len(skipped), "skipped": skipped,
        "development_only_unsupervised_scaling": norm,
        "evaluation": results, "paired_holdout_bootstrap": bs,
        "caveats": [
            "No clinical labels or external dataset used for the primary target.",
            "The second expert is only a retrospective disagreement target, not disease truth.",
            "Patient splits avoid bilateral leakage, but do not guarantee site/device generalization.",
            "v0.2 Q95 is largely proportional to vCDR under fixed log-scale perturbation settings.",
            "Feature combination is a fixed exploratory heuristic; superiority is NOT presupposed.",
            "Do not treat internal holdout as external validation or iterate on it indefinitely.",
        ],
    }
    return summary, rows

def save_study(summary: dict, rows: list[dict], json_path: str | Path, csv_path: str | Path | None = None) -> None:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"summary": summary, "cases": rows},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if csv_path is not None:
        csv_file = Path(csv_path)
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        with csv_file.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
