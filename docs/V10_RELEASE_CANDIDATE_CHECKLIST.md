# HyunOptic v1.0 Release Candidate — Reproducible Source Integrity & Domain Shift

**Version:** 1.0.0rc1 · **Date:** 2026-10-24 · **Status:** software release candidate, **NOT completed scientific or clinical validation**

## Objective

Before reporting actual PAPILA → Chákṣu research effects, verify that:

1. Local data archives have clear, reproducible identities.
2. Candidate-only model settings were frozen on PAPILA development data.
3. The original Chákṣu Test ZIP contains complete five-reader annotation files and decodable original images.
4. External candidate features may shift dramatically by camera; inspect this *without* using reader outcomes for fitting.
5. Reports describe agreement/disagreement between annotations, **not glaucoma diagnostic accuracy**.

The project already includes 60/20/20 patient grouping for PAPILA, a source-only model lock, a primary expert1↔expert2 reference-disagreement target, and a secondary five-reader disagreement sensitivity endpoint. This release candidate adds *archive identity* and *domain shift*.

## 1. Archive identity: independent SHA-256 references

Official dataset pages:

- PAPILA: https://figshare.com/articles/dataset/PAPILA/14798004 (distributor lists GPL 3.0+; check terms directly)
- Chákṣu: https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135 (CC BY 4.0 listed; verify terms)

A public independent dataset-indexing project records the following **reference SHA-256 digests**:

| Archive | Third-party reference SHA-256 |
|---|---|
| `PAPILA.zip` | `15b053dff496bc8e53eb8a8d0707ef73ba3d56c988eea92b65832c9c82852a7d` |
| Chákṣu `Test.zip` | `90e89ad01bfb0c4c238ba22a4a46ab46b5849e2fc9253c7bda09509f6ca259fa` |

Source code of these independently listed checksums:
- https://github.com/staskh/fundus-atlas/blob/main/src/datasets/papila.py
- https://github.com/staskh/fundus-atlas/blob/main/src/datasets/chaksu.py

**These are not vendor signatures or publisher-signed attestations.** Another legitimate version of the dataset may produce a different SHA-256. A matching digest means exactly the same byte sequence as the indexed reference—not that segmentation labels are scientifically correct, patient samples independent, or clinical data safe. A mismatch should trigger a documented source/version review; do not automatically call it malicious or corrupt.

```powershell
git pull
python -m pip install -e ".[ui,dev]"

# First ensure both ORIGINAL zip files are present locally. The command does not upload files.
hyunoptic-verify-sources `
  --papila-zip "D:\\datasets\\PAPILA.zip" `
  --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" `
  --output "reports\\v10\\archive_sha256.json" `
  --require-reference-match
```

The opt-in `--require-reference-match` flag returns exit code 2 on mismatch, while still creating a report. For source revisions not recorded by this independent index, omit the flag, investigate, and document the provenance separately. **A full multi-GB ZIP hash can take noticeable I/O time**; the algorithm reads chunks rather than expanding the file.

## 2. Reproducible experiment sequence

1. Confirm the raw ZIP provenance and exact Figshare version and read the dataset licenses.
2. Download/extract PAPILA locally using the opt-in `hyunoptic-download`, or use an already lawfully obtained archive.
3. Check PAPILA completeness: 244 patients, 488 eye images and 1,952 canonical contour files (PAPILA v1/v2 paper descriptor).
4. Freeze only **exp1 image+mask feature distributions from the PAPILA development partition**.
5. Verify Chákṣu original **Test.zip**, including **336 images, five expert masks for each of cup/disc**, the original camera resolution, and strict full-archive layout.
6. Run external analysis **without re-estimating source model parameters**.
7. Inspect fixed-score rankings for exp1 vs exp2 disagreement, plus secondary 2-of-4 peer disagreement.
8. Investigate failures separately, publish negative results as such, and do NOT adjust scoring after reading Test outcomes while calling the same Test evaluation confirmatory.

```powershell
hyunoptic-inventory --papila-root "D:\\datasets\\PAPILA" --output "reports\\v10\\papila_inventory.json" --strict-full --verify-pixels

hyunoptic-external freeze `
  --papila-root "D:\\datasets\\PAPILA" `
  --output "reports\\v10\\papila_frozen_mask_model.json"

hyunoptic-chaksu-audit `
  --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" `
  --output-dir "reports\\v10\\chaksu_audit" --strict

hyunoptic-external test `
  --model-lock "reports\\v10\\papila_frozen_mask_model.json" `
  --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" `
  --output-dir "reports\\v10\\external"

streamlit run app.py
```

All output folders must be new/empty. Under Streamlit → **External Validation**, load `reports/v10/external/external_aggregate.json`.

## 3. New unlabeled camera-shift diagnostic

Using the PAPILA **development-only** mean and SD values saved in the frozen model lock, convert each Chákṣu expert1 candidate-only feature to the source-standardized value

```
z = (candidate_feature_from_Chaksu - mean_PAPILA_development) / sd_PAPILA_development
```

For each camera (Bosch, Forus, Remidio) and combined Test set, report:

- Number of scored images
- Mean and median source-standardized feature value
- Number and fraction with `|z| > 3`

Features: simulated fixed-noise vCDR baseline, mask roughness, and boundary weakness. These numbers are **descriptive distribution shifts**—they are **not a glaucoma probability, calibrated segmentation error, performance confidence interval, or proof that a camera is defective**.

**Important:** A low PAPILA source standard deviation can amplify standardized values even without meaningful quality change. Do not use the Chákṣu labels or results to tune these feature normalizers after external testing.

## 4. Reporting/publication boundaries

Files permitted for inspection without original images include aggregate JSON and aggregate Markdown. The local external private-case JSON includes case IDs; verify source terms and confidentiality before any sharing. Original images, clinical spreadsheets, and full annotation files are not committed to this public repo.

A run can be structurally complete and produce descriptive metrics **without demonstrating clinical benefit, scientific novelty, or generalization to real patient outcomes**. For PhD preparation, a correctly executed negative replication can be a more defensible project than an unsubstantiated significant effect.

## 5. Release acceptance matrix

| Claim | What is required | Current project status |
|---|---|---|
| Software tests pass | CI Python 3.10 and 3.12, synthetic fixtures | Automated verification |
| Exact source identity compared | Real local ZIP and independent public SHA-256 | **Not executed on original archives in this environment** |
| PAPILA full source study | Official archive, detailed inventory, stable lock | **Not executed** |
| Chákṣu complete Test study | Official Test.zip with all 5 experts and full strict preflight | **Not executed** |
| Meaningful score improvement | Actual scores, comparisons, uncertainty and proper study design | **Unproven** |
| Clinical safety / diagnostic accuracy | A separate, appropriate prospective validation protocol | **Not studied / no such claim** |

**1.0.0rc1 is a software release candidate, NOT v1.0 clinically validated software.**

## Source references

- Kovalyk et al., PAPILA, *Scientific Data* (2022): https://doi.org/10.1038/s41597-022-01388-1
- Chákṣu dataset descriptor, *Scientific Data* (2023): https://doi.org/10.1038/s41597-023-01943-4
- Reproducibility reference code: https://github.com/staskh/fundus-atlas/
