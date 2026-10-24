"""Standalone bidirectional reader-role sensitivity command (PAPILA only)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inventory import inspect_papila
from .reader_symmetry import run_reader_symmetry, save_reader_symmetry
from .uncertainty import PerturbationConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HyunOptic exploratory exp1↔exp2 role sensitivity (not diagnostic validation)"
    )
    parser.add_argument("--papila-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/reader_v06"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--review-fraction", type=float, default=0.20)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Research fixtures/subsets only; full archive required by default")
    args = parser.parse_args(argv)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Choose a NEW, empty output directory; no old results may be overwritten")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest = inspect_papila(args.papila_root)
        (args.output_dir / "inventory.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not manifest["matches_full_published_shape"] and not args.allow_partial:
            parser.error("Full PAPILA inventory shape not matched; use --allow-partial for testing")
        result, rows = run_reader_symmetry(
            args.papila_root,
            config=PerturbationConfig(draws=args.draws, seed=args.seed),
            seed=args.seed,
            disagreement_threshold=args.threshold,
            review_fraction=args.review_fraction,
        )
        result["full_published_inventory_shape_match"] = manifest["matches_full_published_shape"]
        result["partial_or_unverified_input"] = not manifest["matches_full_published_shape"]
        save_reader_symmetry(result, rows, args.output_dir / "reader_symmetry.json",
                             args.output_dir / "reader_case_metrics.csv")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({
        "research_only": True, "version": "0.6.0",
        "patients": result["n_patients_analyzed"],
        "images": result["n_images_analyzed"],
        "partial_or_unverified_input": result["partial_or_unverified_input"],
        "protocol_sha256": result["protocol_sha256"],
        "reader_role_agreement": result["evaluation"]["holdout"]["reader_role_agreement"],
        "files": ["inventory.json", "reader_symmetry.json", "reader_case_metrics.csv"],
        "warning": "Inter-reader disagreement is not a clinical ground truth.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
