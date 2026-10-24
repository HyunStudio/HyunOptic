"""Run the v0.3 PAPILA-only internal research benchmark locally."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .study import run_study, save_study
from .uncertainty import PerturbationConfig

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HyunOptic v0.3 experimental research study; not clinical")
    parser.add_argument("--papila-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/papila_v03.json"))
    parser.add_argument("--csv-output", type=Path, default=Path("reports/papila_v03.csv"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--review-fraction", type=float, default=0.20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        summary, rows = run_study(
            args.papila_root,
            config=PerturbationConfig(draws=args.draws, seed=args.seed),
            split_seed=args.split_seed, discrepancy_threshold=args.threshold,
            review_fraction=args.review_fraction, bootstrap_draws=args.bootstrap_draws,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    save_study(summary, rows, args.output, args.csv_output)
    print(json.dumps({
        "research_only": True,
        "images": summary["n_analyzed"],
        "patients_in_holdout": summary["evaluation"]["holdout"]["n_patients"],
        "protocol_sha256": summary["protocol_sha256"],
        "holdout_review_scores": summary["evaluation"]["holdout"]["scores"],
        "json": str(args.output), "csv": str(args.csv_output),
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
