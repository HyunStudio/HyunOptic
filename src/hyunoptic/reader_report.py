"""Aggregate-only Markdown report for bidirectional reader sensitivity results.

Neither raw eye images, identifiers nor per-case measurements are emitted.
"""
from __future__ import annotations

from pathlib import Path


def render_reader_summary(summary: dict) -> str:
    if summary.get("project") != "HyunOptic" or summary.get("version") != "0.6.0":
        raise ValueError("Expected HyunOptic reader sensitivity v0.6 summary")
    evaluation = summary["evaluation"]
    def fmt(value):
        return "N/A" if value is None else f"{float(value):.3f}"
    lines = [
        "# HyunOptic v0.6 — Reader-Role Sensitivity Audit",
        "",
        "> **Research-only, exploratory internal analysis. NOT glaucoma diagnosis or external validation.**",
        "> These results concern inter-reader vCDR disagreement; no expert is treated as disease ground truth.",
        "",
        f"- Images included: **{summary['n_images_analyzed']}**",
        f"- Patients included: **{summary['n_patients_analyzed']}**",
        f"- Images excluded: **{summary['n_images_skipped']}**",
        f"- Full published archive shape matched: **{summary.get('full_published_inventory_shape_match', False)}**",
        f"- Input partial/unverified: **{summary.get('partial_or_unverified_input', True)}**",
        f"- Protocol digest: `{summary['protocol_sha256']}`",
        "",
        "## Fixed review-budget performance by reader direction",
        "",
        "| Partition | Candidate reader | Score | n images | High disagreement | Precision@budget | Recall@budget | AP | ROC AUC |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("validation", "holdout"):
        for reader in ("exp1", "exp2"):
            body = evaluation[split][reader]
            for name in ("candidate_vcdr", "v02_q95", "combined_candidate_score"):
                stats = body["scores"][name]
                review, ranking = stats["review"], stats["ranking"]
                lines.append(
                    f"| {split} | {reader} | {name} | {body['n_images']} | "
                    f"{review['n_discrepant']} | {fmt(review['precision_at_budget'])} | "
                    f"{fmt(review['recall_at_budget'])} | "
                    f"{fmt(ranking['average_precision'])} | {fmt(ranking['roc_auc'])} |"
                )
    lines.extend(["", "## Sensitivity to which expert acts as the candidate", ""])
    for split in ("validation", "holdout"):
        overlap = evaluation[split]["reader_role_agreement"]
        combined = overlap["combined_candidate_score"]
        lines.append(
            f"- {split}: combined-score top-k overlap **"
            f"{combined['top_k_overlap_count']}/{combined['reviewed_per_direction']}**; "
            f"tie-aware rank correlation **{fmt(combined['spearman_rank_correlation'])}**."
        )
        agreement = evaluation[split].get("bland_altman_inter_reader", {})
        if agreement.get("available") is False:
            lines.append(f"- {split}: Bland-Altman summary unavailable ({agreement.get('reason', 'small cohort')}).")
        elif agreement:
            lines.append(
                f"- {split}: signed vCDR bias (exp1−exp2) **{fmt(agreement['signed_bias'])}**; "
                f"descriptive normal-theory LoA **[{fmt(agreement['limits_of_agreement_lower'])}, "
                f"{fmt(agreement['limits_of_agreement_upper'])}]**."
            )
    lines.extend([
        "",
        "## Interpretation / limitations",
        "",
        "- Reader-swap sensitivity is NOT independent validation on a new site, new camera or new clinical population.",
        "- Results with few high-disagreement cases may have undefined AP/ROC-AUC; N/A values must not be filled with zero.",
        "- Expert disagreements do not tell us which reader is correct; patient outcomes are not assessed.",
        "- Normal-theory Bland-Altman LoA are descriptive; patient-cluster resampling addresses some dependence, not all modeling assumptions.",
        "- Clinical acceptability thresholds were not prospectively established.",
        "- Development of methods after viewing an internal holdout prevents confirmatory claims.",
        "- No new algorithm novelty or reliability advantage is assumed.",
        "",
        "## Further work",
        "",
        "Assess a complete official PAPILA archive, review excluded cases and published annotation conventions,",
        "then register a frozen protocol before Chákṣu external-domain reader comparisons.",
        "",
    ])
    return "\n".join(lines)


def write_reader_summary(summary: dict, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_reader_summary(summary), encoding="utf-8")
