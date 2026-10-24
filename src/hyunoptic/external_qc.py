"""Read-only structural audit of all five Chaksu expert masks.

A completed inventory alone is NOT a data validation. This optional audit
decodes masks and original photographs without writing any images to disk.
The aggregate report never includes patient or image identifiers.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import json
import zipfile
from pathlib import Path
from .chaksu import CAMERAS, EXPECTED_RESOLUTION, EXPERTS, load_test_case, scan_test_archive


def check_chaksu_archive(archive: str | Path, *, max_cases: int | None = None) -> tuple[dict, list[dict]]:
    cases, manifest = scan_test_archive(archive)
    if max_cases is not None and (not isinstance(max_cases, int) or max_cases < 1):
        raise ValueError("max_cases must be positive or omitted")
    selection = cases[:max_cases] if max_cases is not None else cases
    failures: list[dict] = []
    errors = Counter()
    successes = Counter()
    camera_size_mismatch = Counter()
    with zipfile.ZipFile(archive) as zf:
        for case in selection:
            try:
                image, masks = load_test_case(zf, case, readers=EXPERTS)
                if image.size not in EXPECTED_RESOLUTION[case.camera]:
                    camera_size_mismatch[case.camera] += 1
                    failures.append({"case_id": case.case_id, "reason": "unexpected camera resolution"})
                if len(masks) != 10:
                    raise ValueError("Expected 10 independent masks for 5 readers")
                successes[case.camera] += 1
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                errors[case.camera] += 1
                failures.append({"case_id": case.case_id, "reason": type(exc).__name__ + ": " + str(exc)})
    complete = (
        max_cases is None
        and manifest["matches_published_test_file_layout"]
        and len(cases) == 336
        and sum(successes.values()) == 336
        and not failures
        and not manifest.get("suspicious_members")
    )
    summary = {
        "project": "HyunOptic",
        "version": "0.8.0",
        "dataset": "Chaksu Test.zip",
        "research_only": True,
        "filename_structure_matches_published_dataset": manifest["matches_published_test_file_layout"],
        "n_test_images_in_archive": manifest["image_entries"],
        "n_cases_with_all_expert_mask_paths": len(cases),
        "n_checked": len(selection),
        "n_readable_with_all_five_experts": sum(successes.values()),
        "n_errors": sum(errors.values()) + sum(camera_size_mismatch.values()),
        "readable_by_camera": {cam: int(successes[cam]) for cam in CAMERAS},
        "decode_errors_by_camera": {cam: int(errors[cam]) for cam in CAMERAS},
        "resolution_flags_by_camera": {cam: int(camera_size_mismatch[cam]) for cam in CAMERAS},
        "number_of_missing_annotation_cases": len(manifest["missing_annotation_cases"]),
        "number_of_ambiguous_duplicate_members": len(manifest["ambiguous_duplicate_members"]),
        "number_of_suspicious_members": len(manifest.get("suspicious_members", [])),
        "all_published_test_masks_structurally_verified": bool(complete),
        "partial_audit_or_unverified": not complete,
        "warnings": [
            "All-five-reader structural verification is not evidence that any segmentation is clinically correct.",
            "The check never uses fused masks as independent expert labels.",
            "Partial/sampled audit results cannot be claimed as complete Test-set validation.",
            "Cases can fail containment although published human masks are authentic; investigate failures without silently editing source masks.",
        ],
    }
    return summary, failures


def save_chaksu_audit(summary: dict, failures: list[dict], target_folder: str | Path) -> None:
    folder = Path(target_folder)
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError("Refusing to overwrite an existing external audit folder")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "audit_aggregate.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "audit_private_errors.json").write_text(
        json.dumps(failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
