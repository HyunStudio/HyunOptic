# Portable reproduction instructions

This is an exploratory external segmentation audit with frozen PAPILA-trained models. It is not the original RIM-ONE DL classification benchmark or a RIM-only-training leaderboard submission. RIM-ONE DL permits research/education and prohibits redistribution and unauthorized commercial use. Download from the authors' official links; do not copy dataset files, IDs, masks, original third-party source/PDF copies or weights into Git.

Use repository revision `9cd674e3ee54d903410a24071f6a4de99fb38cdf` with the Python/package versions recorded in `environment_provenance.json`. The original private model bundles must be lawfully available at `models/papila_real_seed43_20261025` and `models/papila_camera_robust_seed43_20261025`, with identities matching the public protocols. The scripts verify restricted tensor-only weights and will refuse identity/hash changes. Those weights are not distributed with this harness.

Copy exactly the 12 own-authored source files listed in `PUBLIC_HARNESS_MANIFEST.json` into this fixed ignored layout, relative to repository root:

```text
reports/full_validation_20261104/new_external/
```

Preserve their original bytes, encoding and newlines. For example, use `Path(destination).write_bytes(Path(source).read_bytes())`. Verify every SHA-256 against the manifest after copying. Do not copy the archived `official_*` files as publication assets; the download script obtains them locally from the authors. The source identity of `evaluate_rimone.py` and `supplemental_run.py` is already frozen in the original protocols. If any implementation or layout must change, declare a new experiment/protocol rather than claim the old source hash.

The commands below are for an empty destination in a fresh research checkout, with existing ignore rules for `reports/`, `data/` and `models/`. Do not execute them over the completed original run. The scripts deliberately refuse to overwrite a protocol or silently repeat inference.

```powershell
New-Item -ItemType Directory -Force -Path data/new_external_20261104, reports/full_validation_20261104/new_external | Out-Null
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/download_official.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/download_confirm.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py prepare
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py run
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/audit_references.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/check_png_txt_coordinates.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/verify_numeric.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/supplemental_run.py prepare
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/supplemental_run.py run
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/final_verify_saved_masks.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/make_private_montage.py
```

The authors' asset links are [official images](https://bit.ly/rim-one-dl-images) and [official reference segmentations](https://bit.ly/rim-one-dl-reference-segmentations), documented by the [official repository](https://github.com/miag-ull/rim-one-dl). `download_official.py` records the then-current author commit and initial HTTP responses. `download_confirm.py` follows the normal official Google Drive large-file download form; it does not use a mirror or bypass authentication. Verify the images archive SHA-256 `85aed5f95c794f52d11b6ed953032108a66576ffcff4b587365df467491b603d` and reference archive SHA-256 `edc363b1f0deabc8ed7a356250a9e1fb21825bf06f7337889fd1e764e1947901` to reproduce this asset version. A different hash is a different input version and must be retained/reported separately, not silently substituted.

All 174 images from the hospital test partition are selected once. The random partition is a duplicate variant, not extra data. Supplied source images are optic-nerve-head crops; there is no new reference-derived crop. Raw official binary PNG masks are used directly; the optional TXT coordinate check does not regenerate masks or claim full interpolation equivalence. `scikit-image` is not required by this harness. `scipy`, Pillow, NumPy, requests and PyTorch are required.

The first pass pre-audits references before prediction and is not label-blind; both models remain frozen. The supplemental pass is explicitly exploratory after the first results were known. Within that pass, all 348 original-resolution prediction PNGs are saved and hashed, all 174 image-only priorities are frozen, and only then are references scored. Independent artifact verification recomputes pixel Dice and row-span vCDR, checks source/metadata/queue hashes and timestamps, and compares every first/supplemental status/error/metric. It does not train or select a model.

There are 696 actual inferences across two passes, but only 348 unique image-model pairs and 174 images. Authoritative patient linkage was not verified; never relabel these as 696 samples or 174 independent patients. Keep all generated masks, individual rows, queue rows, coordinate details and the private QA montage in ignored directories. Publish only reviewed aggregate metrics, safe protocols/provenance summaries, this reproduction note and own-authored harness files.

## Separate independent verifier

The additional `verify_rim_independent.py` imports its sibling `verify_full.py`; both files are included. They may be run from this public source location with authorized saved private artifacts and a new private output directory:

```powershell
.venv/Scripts/python.exe docs/experiments/2026-11-04-full-real-validation/rimone/verify_rim_independent.py --input reports/full_validation_20261104/new_external --data data/new_external_20261104 --output reports/rim_independent_fresh
```

This performs no new model inference. The copied public script and sibling dependency were actually reexecuted successfully; [compatibility receipt](public_verifier_compatibility.json). The verifier's arithmetic dependency is also used by the full PAPILA check; its split-envelope parser correction is documented in the enclosing PAPILA verification-issue record.
