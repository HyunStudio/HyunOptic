"""Strict local reproducibility gate: inventory first, study second.

The report is exploratory and never a statement of clinical effectiveness.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .inventory import inspect_papila, save_inventory
from .study import run_study, save_study
from .uncertainty import PerturbationConfig

def reproduce(
    root: str | Path, out_dir: str | Path, *,
    allow_partial: bool = False, draws: int = 500, seed: int = 42,
    bootstrap_draws: int = 1000, verify_pixels: bool = False,
) -> dict:
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    inventory = inspect_papila(root, verify_pixels=verify_pixels)
    save_inventory(inventory, folder / "inventory.json")
    complete = bool(inventory["matches_full_published_shape"])
    if not complete and not allow_partial:
        raise ValueError(
            "Full-data inventory failed. See inventory.json for causes; "
            "use --allow-partial for synthetic fixtures or exploratory subsets only."
        )
    summary, rows = run_study(
        root, config=PerturbationConfig(draws=draws, seed=seed),
        split_seed=seed, bootstrap_draws=bootstrap_draws,
    )
    save_study(summary, rows, folder / "study.json", folder / "case_metrics.csv")
    study_bytes = (folder / "study.json").read_bytes()
    result = {
        "project": "HyunOptic", "version": "0.5.0", "status": "research-only",
        "data_source": "PAPILA provided locally by user",
        "full_published_inventory_shape_match": complete,
        "partial_or_unverified_input": not complete,
        "inventory_metadata_fingerprint": inventory["inventory_sha256_of_paths_and_sizes_only"],
        "study_protocol_sha256": summary["protocol_sha256"],
        "study_json_sha256": hashlib.sha256(study_bytes).hexdigest(),
        "n_patients_with_results": len({r["patient_id"] for r in rows}),
        "n_images_with_results": len(rows),
        "n_skipped_by_study": summary["n_skipped"],
        "note": "Not external validation, clinical diagnosis, prospective evidence, or a guarantee of novelty.",
    }
    (folder / "run_manifest.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result

def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="HyunOptic gated exploratory PAPILA study")
    parser.add_argument("--papila-root", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("reports/v05"), type=Path)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Only for synthetic fixtures or incomplete exploratory samples")
    parser.add_argument("--verify-pixels", action="store_true")
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        manifest = reproduce(
            args.papila_root, args.output_dir,
            allow_partial=args.allow_partial, draws=args.draws,
            seed=args.seed, bootstrap_draws=args.bootstrap_draws,
            verify_pixels=args.verify_pixels,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
