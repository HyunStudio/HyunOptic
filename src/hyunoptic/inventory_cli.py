"""CLI for local PAPILA file integrity and compatibility inventory."""
from __future__ import annotations

import argparse
from pathlib import Path

from .inventory import inspect_papila, save_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Research-only PAPILA data inventory; does not upload images or read diagnoses"
    )
    parser.add_argument("--papila-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/papila_inventory.json"))
    parser.add_argument("--strict-full", action="store_true",
                        help="Exit nonzero unless expected full PAPILA image/patient/contour counts match")
    parser.add_argument("--verify-pixels", action="store_true",
                        help="Verify JPEG file integrity, slower than reading image headers only")
    args = parser.parse_args(argv)
    try:
        report = inspect_papila(args.papila_root, verify_pixels=args.verify_pixels)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    save_inventory(report, args.output)
    counts = report["observed"]
    print(
        "Inventory saved:", args.output, "|",
        counts["patients"], "patients,",
        counts["images"], "images,",
        counts["canonical_contours"], "contours,",
        counts["unusable_images"], "unusable images.",
    )
    print("Matches complete published inventory:", report["matches_full_published_shape"])
    if args.strict_full and not report["matches_full_published_shape"]:
        print("FAIL: dataset is incomplete or failed structural integrity checks.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
