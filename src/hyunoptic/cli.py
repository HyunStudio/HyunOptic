"""Batch-friendly CLI. Avoids requiring Streamlit to run measurements."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .measure import compare_readers, measure_contours
from .papila import discover_cases, load_contours, load_image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HyunOptic research-only PAPILA reader comparison")
    parser.add_argument("--papila-root", type=Path, required=True, help="Directory containing PAPILA_DBv1 or dataset subfolders")
    parser.add_argument("--image-id", type=str, default=None, help="Example: RET001OD")
    parser.add_argument("--output", type=Path, default=None, help="Optional local JSON path")
    args = parser.parse_args(argv)
    cases = discover_cases(args.papila_root)
    if not cases:
        parser.error("No complete PAPILA cases found. Verify directory and annotation files.")
    if args.image_id:
        matches = [case for case in cases if case.image_id == args.image_id.upper()]
        if not matches:
            parser.error("Requested image ID is not a complete discovered PAPILA case")
        case = matches[0]
    else:
        case = cases[0]
    image = load_image(case)
    d1, c1 = load_contours(case, "exp1")
    d2, c2 = load_contours(case, "exp2")
    result = {
        "project": "HyunOptic", "status": "research-only", "image_id": case.image_id,
        "patient_id": case.patient_id, "eye": case.eye,
        "image_size": list(image.size),
        "reader_comparison": compare_readers(d1, c1, d2, c2, image.size),
    }
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
