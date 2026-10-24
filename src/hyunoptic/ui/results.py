"""Normalise source-holdout and external outputs into comparable partitions."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .workspace import RunData

SCORES = ("combined_candidate_score", "candidate_vcdr", "mask_q95")
METRICS = {
    "Precision@budget": ("review", "precision_at_budget"),
    "Recall@budget": ("review", "recall_at_budget"),
    "Average precision": ("ranking", "average_precision"),
    "ROC-AUC": ("ranking", "roc_auc"),
}
CAMERA_LABELS = {"all": "Chákṣu (all)", "bosch": "Bosch", "forus": "Forus", "remidio": "Remidio"}


@dataclass
class Partition:
    key: str
    label: str
    dataset: str
    n_images: int
    n_high: int
    scores: dict
    rows: list = field(default_factory=list)
    target_key: str = ""
    n_patients: int | None = None

    def metric(self, score: str, metric: str):
        part, name = METRICS[metric]
        value = self.scores.get(score, {}).get(part, {}).get(name)
        return None if value is None or (isinstance(value, float) and not np.isfinite(value)) else value

    def delta(self, metric: str, score: str = "combined_candidate_score", baseline: str = "candidate_vcdr"):
        a, b = self.metric(score, metric), self.metric(baseline, metric)
        return None if a is None or b is None else a - b

    @property
    def differences(self) -> np.ndarray:
        return np.asarray([r[self.target_key] for r in self.rows if self.target_key in r], dtype=float)

    def labels(self, threshold: float = 0.10) -> np.ndarray:
        return self.differences > threshold

    def score_values(self, score: str) -> np.ndarray:
        return np.asarray([r[score] for r in self.rows if self.target_key in r], dtype=float)


def partitions(run: RunData, *, secondary: bool = False) -> list[Partition]:
    out: list[Partition] = []
    if run.source and not secondary:
        rows = run.source_rows or []
        for split in ("validation", "holdout"):
            group = run.source.get("evaluation", {}).get(split)
            if not group:
                continue
            out.append(Partition(
                f"papila_{split}", f"PAPILA {split}", "PAPILA", group.get("n_images", 0),
                group.get("n_high_disagreement", 0), group.get("scores", {}),
                [r for r in rows if r.get("split") == split], "absolute_reader_vcdr_disagreement",
                group.get("n_patients")))
    if run.external:
        rows = run.external_rows or []
        source = run.external.get("secondary_five_reader_results" if secondary else "results", {})
        for camera, group in source.items():
            if group.get("missing"):
                continue
            subset = [r for r in rows if camera == "all" or r.get("camera") == camera]
            n = group.get("n_images", group.get("n", 0))
            high = group.get("high_disagreement_with_at_least_two_of_four_peers",
                             group.get("n_high_disagreement", 0))
            out.append(Partition(f"chaksu_{camera}", CAMERA_LABELS.get(camera, camera), "Chákṣu", n, high,
                                 group.get("scores", {}), subset,
                                 "absolute_expert1_expert2_vcdr_difference"))
    return out


STEP_TITLES = {
    "archive_identity": "Archive identity (SHA-256)",
    "papila_inventory": "PAPILA inventory",
    "freeze_papila_development": "Freeze model on development patients",
    "papila_source_holdout": "PAPILA validation + holdout",
    "chaksu_five_reader_preflight": "Chákṣu five-reader preflight",
    "chaksu_external_test": "Chákṣu external test",
    "evidence_gate": "Evidence-package gate",
    "html_report": "HTML report",
}
STEP_TONE = {"passed": "ok", "incomplete": "warn", "failed": "bad", "skipped": ""}
