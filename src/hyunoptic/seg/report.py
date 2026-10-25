"""Model-experiment report discovery and schema validation (no PyTorch needed, used by the UI)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from . import REPORT_SCHEMA

if TYPE_CHECKING:
    from .bundle import Bundle


def find_reports(bundle_folder: str | Path) -> list[Path]:
    base = Path(bundle_folder) / "evaluation"
    return sorted(base.glob("*/model_eval_aggregate.json")) if base.is_dir() else []


def validate_report(data: dict, *, bundle: Bundle | None = None) -> dict:
    """Accept only evaluator output; anything else is rejected for display."""
    if not isinstance(data, dict) or data.get("schema") != REPORT_SCHEMA or data.get("project") != "HyunOptic":
        raise ValueError(f"Not a {REPORT_SCHEMA} report")
    for key in ("evaluation", "exploratory", "run_id", "n_images", "n_failed", "versus_expert1"):
        if key not in data:
            raise ValueError(f"Report is missing {key!r}")
    if data["evaluation"] not in ("internal_papila_holdout", "exploratory_external_chaksu"):
        raise ValueError("Unknown evaluation type")
    if not isinstance(data["exploratory"], bool):
        raise ValueError("Report exploratory flag must be a boolean")
    if data["evaluation"] == "exploratory_external_chaksu" and data["exploratory"] is not True:
        raise ValueError("External Chákṣu results must be labelled exploratory")
    if bundle is not None:
        for key, expected in (("run_id", bundle.run_id), ("weights_sha256", bundle.weights_sha256),
                              ("bundle_data_status", bundle.manifest["data_status"])):
            if data.get(key) != expected:
                raise ValueError(f"Report {key} does not match the selected bundle")
        if (bundle.synthetic or bundle.partial) and not data["exploratory"]:
            raise ValueError("Synthetic or partial bundle results must be labelled exploratory")
        if data["evaluation"] == "internal_papila_holdout":
            for key in ("split_manifest_sha256", "source_content_sha256"):
                if data.get(key) != bundle.manifest["training"][key]:
                    raise ValueError(f"Report {key} does not match the selected bundle")
    return data
