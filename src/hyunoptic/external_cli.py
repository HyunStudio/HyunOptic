"""Freeze on PAPILA development then score external Chaksu TEST independently."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .external import run_external_test, save_external
from .freeze import freeze_papila_model, save_lock

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="HyunOptic frozen source-model and external-domain Test validation (research only)"
    )
    cmd = p.add_subparsers(dest="command", required=True)
    src = cmd.add_parser("freeze", help="Fit an unlabeled PAPILA development-only mask feature scaler")
    src.add_argument("--papila-root", type=Path, required=True)
    src.add_argument("--output", type=Path, default=Path("reports/v07/papila_frozen_mask_model.json"))
    src.add_argument("--seed", type=int, default=42)
    src.add_argument("--draws", type=int, default=500)
    src.add_argument("--allow-partial", action="store_true", help="ONLY for synthetic/source fixture")
    ext = cmd.add_parser("test", help="Evaluate a FROZEN model on a local Chaksu Test.zip")
    ext.add_argument("--model-lock", type=Path, required=True)
    ext.add_argument("--chaksu-test-zip", type=Path, required=True)
    ext.add_argument("--output-dir", type=Path, default=Path("reports/v07/external"))
    ext.add_argument("--allow-partial", action="store_true",
                     help="ONLY for synthetic/incomplete research fixtures, not validation claims")
    args = p.parse_args(argv)
    try:
        if args.command == "freeze":
            lock = freeze_papila_model(
                args.papila_root, seed=args.seed, draws=args.draws,
                allow_partial=args.allow_partial)
            save_lock(lock, args.output)
            print(json.dumps({
                "model_lock_path": str(args.output),
                "sha256": lock["sha256"],
                "source_partial": lock["model"]["source_is_partial"],
                "development_images": lock["model"]["n_development_images"],
                "note": "Feature settings were fit without expert2 or external annotations",
            }, indent=2))
        else:
            result, rows = run_external_test(
                args.chaksu_test_zip, args.model_lock,
                allow_partial=args.allow_partial)
            save_external(result, rows, args.output_dir)
            print(json.dumps({
                "output_dir": str(args.output_dir),
                "source_lock_sha256": result["source_lock_sha256"],
                "n_images": result["n_test_images_scored"],
                "complete_external_file_layout": result["full_layout_and_readability_verified"],
                "warning": "Inter-reader measurement agreement is NOT clinical glaucoma diagnosis",
            }, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        p.error(str(exc))

if __name__ == "__main__":
    raise SystemExit(main())
