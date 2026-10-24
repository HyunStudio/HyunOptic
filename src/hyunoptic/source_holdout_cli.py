"""Run a frozen, patient-disjoint PAPILA mask study before external Test."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .source_holdout import evaluate_source, save_source_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PAPILA heldout mask-scoring benchmark; research only, not diagnosis"
    )
    parser.add_argument("--papila-root", type=Path, required=True)
    parser.add_argument("--model-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/papila_source_rc3"))
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Synthetic/incomplete exploratory data ONLY (cannot claim full validation)")
    args = parser.parse_args(argv)
    try:
        result, rows = evaluate_source(
            args.papila_root, args.model_lock, allow_partial=args.allow_partial,
            bootstrap_draws=args.bootstrap_draws,
        )
        save_source_evaluation(result, rows, args.output_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "research_only": True,
        "source_lock_sha256": result["source_lock_sha256"],
        "source_original_full": result["full_source_holdout_scored"],
        "validation_images": result["evaluation"]["validation"]["n_images"],
        "holdout_images": result["evaluation"]["holdout"]["n_images"],
        "patient_cluster_bootstrap": result["paired_patient_bootstrap_holdout"],
        "results_dir": str(args.output_dir),
        "not_external_or_clinical_validation": True,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
