"""Inspect official Chaksu Test.zip masks without extraction or study results."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .external_qc import check_chaksu_archive, save_chaksu_audit

def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description="HyunOptic all-five-expert Chaksu Test ZIP audit (research only)")
    p.add_argument("--chaksu-test-zip", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("reports/v08/chaksu_audit"))
    p.add_argument("--max-cases", type=int, default=None,
                   help="Optional quick sample (marks results partial; NEVER full validation)")
    p.add_argument("--strict", action="store_true",
                   help="Exit status 2 unless all 336 published Test cases pass full five-reader checks")
    args = p.parse_args(argv)
    try:
        report, failures = check_chaksu_archive(args.chaksu_test_zip, max_cases=args.max_cases)
        save_chaksu_audit(report, failures, args.output_dir)
    except (OSError, ValueError, KeyError) as error:
        p.error(str(error))
    print(json.dumps({
        "report_folder": str(args.output_dir),
        "n_checked": report["n_checked"],
        "n_errors": report["n_errors"],
        "all_test_masks_verified": report["all_published_test_masks_structurally_verified"],
        "note": "Structural checks only; no clinical validity established.",
    }, indent=2))
    if args.strict and not report["all_published_test_masks_structurally_verified"]:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
