"""Model-experiment report discovery and schema validation (no PyTorch needed, used by the UI)."""
from __future__ import annotations

from pathlib import Path

from . import REPORT_SCHEMA


def find_reports(bundle_folder: str | Path) -> list[Path]:
    base = Path(bundle_folder) / "evaluation"
    return sorted(base.glob("*/model_eval_aggregate.json")) if base.is_dir() else []


def validate_report(data: dict) -> dict:
    """Accept only evaluator output; anything else is rejected for display."""
    if not isinstance(data, dict) or data.get("schema") != REPORT_SCHEMA or data.get("project") != "HyunOptic":
        raise ValueError(f"Not a {REPORT_SCHEMA} report")
    for key in ("evaluation", "exploratory", "run_id", "n_images", "n_failed", "versus_expert1"):
        if key not in data:
            raise ValueError(f"Report is missing {key!r}")
    if data["evaluation"] not in ("internal_papila_holdout", "exploratory_external_chaksu"):
        raise ValueError("Unknown evaluation type")
    if data["evaluation"] == "exploratory_external_chaksu" and data["exploratory"] is not True:
        raise ValueError("External Chákṣu results must be labelled exploratory")
    return data
