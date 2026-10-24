"""Locally fingerprint official dataset archives without sharing their contents."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .source_integrity import save_integrity_report, verify_archive


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Compare local ZIP SHA256 to reproducible independent public reference hashes."
    )
    p.add_argument("--papila-zip", type=Path)
    p.add_argument("--chaksu-test-zip", type=Path)
    p.add_argument("--output", type=Path, default=Path("reports/source_integrity.json"))
    p.add_argument("--require-reference-match", action="store_true",
                   help="Return 2 on any mismatch. Another legitimate archive version can differ.")
    a = p.parse_args(argv)
    if a.papila_zip is None and a.chaksu_test_zip is None:
        p.error("Pass at least one ZIP path")
    try:
        checks = []
        if a.papila_zip is not None:
            checks.append(verify_archive(a.papila_zip, "PAPILA"))
        if a.chaksu_test_zip is not None:
            checks.append(verify_archive(a.chaksu_test_zip, "CHAKSU_TEST"))
        save_integrity_report(checks, a.output)
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    for item in checks:
        print(f"{item['dataset']}: {item['computed_sha256']} "
              f"(public reference match: {item['matches_independent_public_reference']})")
    print(f"Report: {a.output}\nThese references are not official publisher signatures.")
    if a.require_reference_match and any(
            not r["matches_independent_public_reference"] for r in checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
