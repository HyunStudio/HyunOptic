# Reproduction prerequisites and audit records

This directory publishes aggregates, protocols and actual orchestration scripts, not source data or model bundles. The original experiment used code commit `1f42b54385d8cf918c8417b475c0629d25ce874c` plus the exact standalone runners preserved here. Hashes in `protocol.json` and `iowa_protocol.json` bind the original evaluator bytes. See `environment.json` for recorded package versions. CUDA inference was used; this is not a CPU benchmark.

## Required model bundles

Recreate the four bundles using the [baseline](../2026-10-25-real-data-baseline/REPRODUCE.txt), [seed follow-up](../2026-10-25-seed-stability/README.md) and [photometric follow-up](../2026-10-25-photometric-remediation/README.md) instructions, or use your preserved original local bundles. Expected folder names and original checkpoint hashes are in `protocol.json`. Public aggregate manifests cannot be loaded as trained models. Recreated weights may differ because of recorded CUDA nondeterminism; do not claim exact numerical reproduction unless the original hashes match.

## Script placement

The scripts preserve the original local layout and resolve the repository from `Path(__file__).parents[2]`. In a fresh experiment checkout, copy `scripts/*.py` to **`reports/university_20261025/`** and run them from the repository root. Do not run them in place under `docs/experiments/.../scripts/`. Keep all resulting source data, patient-level intermediates and models inside ignored `data/`, `reports/` and `models/` directories.

The experiment-only audit environment additionally requires SciPy and Matplotlib; neither is added to production dependencies. Run the six adapter checks before inference:

```powershell
python -m pytest reports/university_20261025/test_adapter.py -q
```

## Dataset acquisition and evaluation

1. **FairSeg:** obtain the publisher's official Test split at HF revision `3c33b4e0ff8a864af9ce517879fca42e17688037`. `acquire_fairseg.py` records a resolved source revision and verifies each NPZ against LFS SHA256, follows pagination and requires exactly 2,000 files. **The preserved script resolves the publisher's current revision when run. Check it against the recorded revision before evaluation; a newer revision is a different source experiment.** `data_summary.csv` must identify all selected files as `test`. The original script writes source/download manifests under `data/university_20261025/fairseg_test/`.
2. **OLIVES:** `olives_pilot.py` obtains bounded prefixes from both original nested archives. It writes the exact selection protocol before prediction and validates extracted fundus TIFF CRC32. It is deliberately a 30-file pilot, not the whole dataset. Do not report complete archive MD5 verification or full-cohort performance. The official lighter HF release exposes OCT scans and is not a drop-in fundus replacement.
3. With the exact four original local bundles and successful source manifests, `evaluate_universities.py` freezes a new protocol and evaluates FairSeg and OLIVES. It requires CUDA. **Use an empty output directory for an independent run.** Its original local resume path lacks a per-row protocol binding; do not reuse stale JSONL. Preserve the original published experiment instead of overwriting or relabeling it.
4. **Duke:** obtain the ZIP through the official source and preserve it as `data/university_20261025/2015_BOE_Chiu2.zip`. `audit_duke.py` checks the archive and schemas; `duke_boundary_benchmark.py` compares provided algorithm boundary arrays against both readers. It does not run HyunOptic on OCT or train an OCT model.
5. **Iowa:** register through the official provider yourself, then obtain `pamidataset.rar` from its HTTPS link. Validate archive paths before extraction. The local prerequisites for `evaluate_iowa.py` are the extracted tree at `data/university_20261025/iowa/` and `reports/university_20261025/iowa_private_inventory.json`: one record per TIFF with `path` relative to that tree, `depth` determined by `TransDepth` in the filename, and `frames` read from Pillow. Require 30 original non-depth TIFFs with two frames each and 30 depth references. The evaluator freezes its protocol before processing both RGB frames from every original stereo TIFF. It refuses an existing Iowa protocol. No depth image is a model input or fabricated OD/OC label.
6. **Columbia:** no public download for the described patient reports/eye-tracking data was verified. Do not substitute article figures or unrelated code/model files and call that a patient-dataset test.

`acquire.py` is the initial acquisition audit record: its default main also attempts the full FairSeg Zenodo ZIP, which was stopped locally after the pinned HF Test-file route was adopted. That partial ZIP was never used for evaluation. Its `acquire()` helper was also used for the successful Iowa download. Do not confuse a preserved local SHA256 with a publisher-provided expected checksum.

## Independent verification

Verify the downloaded/checked-out evidence without ML dependencies:

```powershell
python docs/experiments/2026-10-25-university-transfer/scripts/verify_public_evidence.py
# During publication, also verify the exact bytes that Git will publish:
python docs/experiments/2026-10-25-university-transfer/scripts/verify_public_evidence.py --git-index
```

Private per-case rows are not distributed. Public arithmetic can be inspected in the full-precision aggregate JSON, but reproducing case-level verification requires legally acquired inputs and locally rerun predictions. Check checkpoint hashes, source revision/file hashes, expected case order, all denominators and paired measurable subsets. Do not infer clinical validity, fairness, equivalent imaging modalities or institutional endorsement from a completed execution check.
