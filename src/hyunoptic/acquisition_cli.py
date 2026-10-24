"""PAPILA downloader CLI. Network operation occurs only when explicitly run."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .acquisition import acquire_archive, figshare_metadata, safely_extract_archive

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download official PAPILA ZIP from Figshare to YOUR computer (research use)"
    )
    parser.add_argument("--archive", type=Path, required=True, help="New .zip target path")
    parser.add_argument("--extract-to", type=Path, default=None,
                        help="Optional NEW directory for safe extraction")
    parser.add_argument("--accept-dataset-terms", action="store_true",
                        help="Confirm you reviewed official Figshare license and dataset conditions")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="Where to save source/checksum manifest (default: beside archive)")
    args = parser.parse_args(argv)
    if not args.accept_dataset_terms:
        parser.error("Visit https://figshare.com/articles/dataset/PAPILA/14798004 and pass --accept-dataset-terms")
    try:
        meta = figshare_metadata()
        print("Source:", meta["metadata_source"], "file ID:", meta["file_id"],
              "advertised bytes:", meta["bytes_expected"])
        print("License metadata:", meta.get("license_url") or "Review official Figshare page")
        manifest = acquire_archive(args.archive, accept_terms=True, metadata=meta)
        if args.extract_to is not None:
            manifest["extraction"] = safely_extract_archive(args.archive, args.extract_to)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    path = args.manifest or args.archive.with_suffix(".provenance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Provenance manifest:", path)
    print("Dataset is local; do not commit data or derived patient-level files to GitHub.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
