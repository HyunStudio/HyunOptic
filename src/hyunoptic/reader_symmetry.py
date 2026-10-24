"""Bidirectional reader-role sensitivity audit for internal PAPILA research.

Each reader becomes the CANDIDATE exactly once, with the OTHER reader
unavailable during candidate feature computation. All targets are
retrospective inter-reader differences, not medical outcomes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .evaluation import evaluate_at_budget
from .agreement import reader_agreement
from .features import FEATURE_NAMES, candidate_features
from .measure import compare_readers
from .papila import discover_cases, load_contours, load_image
from .ranking import ranking_metrics
from .study import _apply_candidate_only_combination, patient_splits
from .uncertainty import PerturbationConfig

READER_NAMES = ("exp1", "exp2")
SCORE_NAMES = ("candidate_vcdr", "v02_q95", "cup_roughness",
               "cup_boundary_weakness", "combined_candidate_score")


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks across exact ties; used for descriptive Spearman."""
    n = len(values)
    indices = np.argsort(values, kind="stable")
    result = np.empty(n, dtype=float)
    start = 0
    while start < n:
        stop = start + 1
        while stop < n and values[indices[stop]] == values[indices[start]]:
            stop += 1
        result[indices[start:stop]] = (start + stop - 1) / 2.0
        start = stop
    return result


def _score_agreement(rows_a: list[dict], rows_b: list[dict],
                     *, metric: str, review_fraction: float) -> dict:
    a = {r["image_id"]: r for r in rows_a}
    b = {r["image_id"]: r for r in rows_b}
    if set(a) != set(b):
        raise ValueError("Candidate directions must have identical image IDs")
    ids = sorted(a)
    x = np.asarray([a[i][metric] for i in ids], dtype=float)
    y = np.asarray([b[i][metric] for i in ids], dtype=float)
    n = len(ids)
    k = max(1, math.ceil(n * review_fraction))
    top_a = set(np.argsort(-x, kind="stable")[:k])
    top_b = set(np.argsort(-y, kind="stable")[:k])
    ranks_a, ranks_b = _average_ranks(x), _average_ranks(y)
    if np.std(ranks_a) < 1e-12 or np.std(ranks_b) < 1e-12:
        rho = None
    else:
        rho = float(np.corrcoef(ranks_a, ranks_b)[0, 1])
    return {
        "n_images": n,
        "reviewed_per_direction": k,
        "top_k_overlap_count": len(top_a & top_b),
        "top_k_overlap_fraction": len(top_a & top_b) / k,
        "spearman_rank_correlation": rho,
        "interpretation": (
            "How strongly candidate-only rankings depend on which ophthalmologist "
            "was chosen as the candidate reader; NOT diagnostic agreement."
        ),
    }


def run_reader_symmetry(
    root: str | Path, *, config: PerturbationConfig | None = None,
    seed: int = 42, disagreement_threshold: float = 0.10,
    review_fraction: float = 0.20,
) -> tuple[dict, list[dict]]:
    """Fixed 60/20/20 patient split; examine reader direction on identical cases.

    Do not select a winning reader direction based on the internal holdout.
    The first direction is exp1 -> exp2, second is exp2 -> exp1.
    """
    config = config or PerturbationConfig()
    config.validate()
    if not 0 < review_fraction <= 1 or not np.isfinite(review_fraction):
        raise ValueError("review_fraction must be within (0, 1]")
    if disagreement_threshold < 0 or not np.isfinite(disagreement_threshold):
        raise ValueError("disagreement_threshold must be finite and nonnegative")
    cases = discover_cases(root)
    if not cases:
        raise ValueError("No complete PAPILA cases found")
    splits = patient_splits([case.patient_id for case in cases], seed)
    by_reader = {name: [] for name in READER_NAMES}
    skipped = []
    for case in cases:
        try:
            image = load_image(case)
            d1, c1 = load_contours(case, "exp1")
            d2, c2 = load_contours(case, "exp2")
            # Each candidate feature generator consumes only its own annotation.
            f1 = candidate_features(image, d1, c1, config)
            f2 = candidate_features(image, d2, c2, config)
            # Ground truth disagreement computed after BOTH candidate scores.
            comparison = compare_readers(d1, c1, d2, c2, image.size)
            outcome = comparison["absolute_vcdr_difference"]
            reader_vcdr_1 = comparison["exp1"]["vertical_cdr"]
            reader_vcdr_2 = comparison["exp2"]["vertical_cdr"]
            for reader, feat in (("exp1", f1), ("exp2", f2)):
                by_reader[reader].append({
                    "patient_id": case.patient_id,
                    "image_id": case.image_id,
                    "eye": case.eye,
                    "split": splits[case.patient_id],
                    "candidate_reader": reader,
                    **feat,
                    "heldout_absolute_vcdr_difference": outcome,
                    "exp1_retrospective_vcdr": reader_vcdr_1,
                    "exp2_retrospective_vcdr": reader_vcdr_2,
                })
        except (OSError, ValueError, RuntimeError) as exc:
            skipped.append({"image_id": case.image_id, "reason": str(exc)})
    if len({r["patient_id"] for r in by_reader["exp1"]}) < 5:
        raise ValueError("Too few analyzable patients")
    norm = {reader: _apply_candidate_only_combination(by_reader[reader])
            for reader in READER_NAMES}
    evaluation = {}
    for split in ("validation", "holdout"):
        evaluation[split] = {}
        for reader in READER_NAMES:
            selected = [r for r in by_reader[reader] if r["split"] == split]
            if not selected:
                raise ValueError(f"Empty {split} split for reader {reader}")
            outcome = [r["heldout_absolute_vcdr_difference"] for r in selected]
            evaluation[split][reader] = {
                "n_patients": len({r["patient_id"] for r in selected}),
                "n_images": len(selected),
                "scores": {
                    name: {
                        "review": evaluate_at_budget(
                            [r[name] for r in selected], outcome,
                            discrepancy_threshold=disagreement_threshold,
                            review_fraction=review_fraction).to_dict(),
                        "ranking": ranking_metrics(
                            [r[name] for r in selected], outcome,
                            threshold=disagreement_threshold),
                    } for name in SCORE_NAMES
                },
            }
        a = [r for r in by_reader["exp1"] if r["split"] == split]
        b = [r for r in by_reader["exp2"] if r["split"] == split]
        try:
            evaluation[split]["bland_altman_inter_reader"] = reader_agreement(
                [r["exp1_retrospective_vcdr"] for r in a],
                [r["exp2_retrospective_vcdr"] for r in a],
                [r["patient_id"] for r in a], draws=500, seed=seed,
            )
        except ValueError as exc:
            evaluation[split]["bland_altman_inter_reader"] = {"available": False, "reason": str(exc)}
        evaluation[split]["reader_role_agreement"] = {
            name: _score_agreement(a, b, metric=name, review_fraction=review_fraction)
            for name in ("candidate_vcdr", "v02_q95", "combined_candidate_score")
        }
    protocol = {
        "data": "PAPILA; two readers and bilateral patients",
        "candidate_directions": ["exp1->exp2", "exp2->exp1"],
        "split": "patient-disjoint deterministic SHA256 60/20/20",
        "split_seed": seed,
        "perturbation": dict(config.__dict__),
        "review_fraction": review_fraction,
        "absolute_vcdr_disagreement_threshold": disagreement_threshold,
        "scores": list(SCORE_NAMES),
        "normalization": "separate reader-specific DEVELOPMENT features only",
    }
    return {
        "project": "HyunOptic",
        "version": "0.6.0",
        "status": "research-only",
        "study_type": "EXPLORATORY bidirectional internal reader-role sensitivity",
        "not_external_validation": True,
        "not_clinical_diagnosis": True,
        "protocol_settings": protocol,
        "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
        "n_images_analyzed": len(by_reader["exp1"]),
        "n_patients_analyzed": len({r["patient_id"] for r in by_reader["exp1"]}),
        "n_images_skipped": len(skipped),
        "skipped": skipped,
        "development_scaling_by_reader": norm,
        "evaluation": evaluation,
        "caveats": [
            "Reversing readers is a sensitivity analysis, not external validation.",
            "Disagreement is not a clinical disease ground truth.",
            "Reader-specific development scaling is separately fitted without outcomes.",
            "Average precision is undefined if no high-disagreement cases occur.",
            "ROC AUC is undefined when only one class exists.",
            "Repeated internal holdout inspection precludes confirmatory claims.",
            "Tie-breaking at fixed review fraction uses deterministic image order.",
            "Bland-Altman limits are descriptive normal-theory limits, not clinical acceptance limits.",
        ],
    }, by_reader["exp1"] + by_reader["exp2"]


def save_reader_symmetry(summary: dict, rows: list[dict], output: str | Path,
                         csv_output: str | Path | None = None) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"summary": summary, "cases": rows},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if csv_output is not None:
        target = Path(csv_output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
