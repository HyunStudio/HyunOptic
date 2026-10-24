"""Exploratory LOCAL PAPILA measurement audit; not external or clinical validation."""
from __future__ import annotations
import csv
import json
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .evaluation import evaluate_at_budget, patient_cluster_bootstrap_mean
from .measure import compare_readers
from .papila import discover_cases, load_contours, load_image
from .uncertainty import PerturbationConfig, analyze_vertical_sensitivity

def audit_papila(root: str | Path, *, config: PerturbationConfig | None = None,
                 disagreement_threshold: float = 0.10,
                 review_fraction: float = 0.20) -> tuple[dict, list[dict]]:
    """Candidate-only exp1 sensitivity; compare with exp2 ONLY after scoring."""
    config = config or PerturbationConfig()
    config.validate()
    cases = discover_cases(root)
    if not cases:
        raise ValueError("No complete PAPILA image/annotation cases discovered")
    rows: list[dict] = []
    skipped: list[dict] = []
    for case in cases:
        try:
            image = load_image(case)
            disc1, cup1 = load_contours(case, "exp1")
            sensitivity = analyze_vertical_sensitivity(disc1, cup1, config)
            candidate_score = sensitivity.q95_absolute_vcdr_change
            disc2, cup2 = load_contours(case, "exp2")
            agreement = compare_readers(disc1, cup1, disc2, cup2, image.size)
            rows.append({
                "patient_id": case.patient_id,
                "image_id": case.image_id,
                "eye": case.eye,
                "candidate_q95_absolute_vcdr_change": candidate_score,
                "candidate_simulated_vcdr_sd": sensitivity.simulated_sd_vcdr,
                "candidate_delta_covariance_term": sensitivity.covariance_cup_disc_vertical,
                "exp1_vcdr": agreement["exp1"]["vertical_cdr"],
                "exp2_vcdr": agreement["exp2"]["vertical_cdr"],
                "heldout_absolute_vcdr_difference": agreement["absolute_vcdr_difference"],
                "disc_dice_retrospective": agreement["disc_dice"],
                "cup_dice_retrospective": agreement["cup_dice"],
                "annotation_warning": bool(agreement["exp1"]["warnings"] or agreement["exp2"]["warnings"]),
            })
        except (OSError, ValueError, RuntimeError) as error:
            skipped.append({"image_id": case.image_id, "reason": str(error)})
    if not rows:
        raise ValueError("No analyzable cases; review annotations and data layout")
    scores = np.array([r["candidate_q95_absolute_vcdr_change"] for r in rows])
    differences = np.array([r["heldout_absolute_vcdr_difference"] for r in rows])
    review = evaluate_at_budget(scores, differences, discrepancy_threshold=disagreement_threshold,
                                review_fraction=review_fraction)
    summary = {
        "project": "HyunOptic", "version": "0.2.0", "status": "research-only",
        "study_type": "exploratory same-dataset reader comparison; no external validation",
        "candidate_score_input": "exp1 optic disc/cup polygons only",
        "heldout_result": "absolute(exp1 vCDR - exp2 vCDR)",
        "no_clinical_validity": True, "config": asdict(config),
        "n_analyzed": len(rows), "n_skipped": len(skipped), "skipped": skipped,
        "review_budget_result": review.to_dict(),
        "limitations": [
            "Perturbation strengths are hypothetical, not calibrated to reader disagreement.",
            "Retrospective exp1/exp2 pair is not a clinical disease gold standard.",
            "No patient-disjoint testing, external performance or superiority established.",
            "Mask-span vCDR differs in quantization from continuous-coordinate sensitivity vCDR.",
        ],
    }
    try:
        summary["patient_bootstrap_absolute_vcdr_difference"] = patient_cluster_bootstrap_mean(
            differences, [r["patient_id"] for r in rows], draws=2000, seed=config.seed
        )
    except ValueError as exc:
        summary["patient_bootstrap_unavailable"] = str(exc)
    return summary, rows

def write_audit(summary: dict, rows: list[dict], out_json: str | Path, out_csv: str | Path | None = None) -> None:
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if out_csv is not None:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
