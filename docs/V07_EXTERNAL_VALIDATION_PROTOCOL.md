# HyunOptic v0.7 — PAPILA-to-Chákṣu External-Domain Protocol

**Date:** 2026-10-24 | **Status:** implementation and synthetic ZIP tests; **no original Chákṣu performance claim yet**.

**Study title:** *Cross-Dataset Robustness of Candidate-Only Optic Nerve Measurement Quality Scores under Independent Human Annotation Disagreement.*

> **Research use only. Not a glaucoma diagnostic model or clinical decision support system.**

## 1. Methodological changes from v0.6

PAPILA distributes each ophthalmologist's optic disc and cup as XY contour text. Chákṣu distributes each expert's optic-disc and optic-cup binary masks. Comparing the v0.6 polygon-contour roughness against Chákṣu binary masks would change the feature's meaning without warning. For v0.7, HyunOptic defines a **new, shared MASK-based feature family** from scratch and applies it to both datasets.

**Fixed input information:** ONE fundus photo plus ONE expert's disc/cup masks. The second expert, other 3 experts, glaucoma decisions, and fused/majority/STAPLE masks are **never input** to candidate scoring.

Source features:
- `candidate_vcdr`: vertical cup-mask bounding span divided by disc-mask bounding span, with a common inclusive-pixel convention.
- `mask_q95`: 95th percentile of simulated absolute vCDR change from assumed independent cup/disc scale perturbations. This is mathematically just rescaled vCDR with fixed noise strength: a **negative-control comparator**, not calibrated error.
- `mask_roughness`: 4-connected pixel-edge perimeter squared divided by `4π × cup mask area`, minus 1. This is rasterization-dependent and different from v0.6 continuous-polygon roughness.
- `mask_boundary_weakness`: one minus mean normalized image grayscale gradient on candidate cup-mask boundary pixels. This may vary with camera characteristics and illumination.

**Experimental score:** equal-weight mean of three clipped z-scores (`mask_q95`, `mask_roughness`, `mask_boundary_weakness`), with z-score location/scale estimated **only** on PAPILA's first-expert development cohort. No second-expert labels are used for feature scaling.

## 2. PAPILA source lock (must precede Chákṣu test)

1. Obtain the original PAPILA dataset as described in [v0.5](V05_REPRODUCIBLE_REAL_DATA_RUN.md).
2. Verify the expected 244 patients, 488 photographs and 1,952 expert masks/contours before freezing.
3. Split patients deterministically into 60% development / 20% validation / 20% internal holdout. Both eyes stay within a patient.
4. Convert exp1 disc/cup polygons to pixel masks in original image coordinates.
5. Compute **shared v0.7** mask-based candidate-only features in development cases.
6. Fit the three unlabeled feature means and standard deviations on development cases only.
7. Freeze feature definitions, random simulation seed/draws, 20% review quota, 0.10 *research-only* vCDR discrepancy threshold and source inventory fingerprint in an immutable-by-convention JSON lock with SHA-256 content integrity check.

The lock fingerprint is an integrity check, **not third-party preregistration**. The user could still change code or create a new lock; the report must preserve the original source lock and commit to avoid misleading claims.

## 3. Chákṣu external Test.zip protocol

The original Chákṣu publication describes 1,345 images from three cameras and five experts. Its **Test** split contains 336 images:
- Bosch: **41**
- Forus: **31**
- Remidio: **264**

Relevant folders inside the published Test archive:
- `Test/1.0_Original_Fundus_Images/<camera>/<image>`
- `Test/3.0_Doctors_Annotations_Binary_OD_OC/Expert N/<camera>/<disc-or-cup>/<mask>` for all five experts

The reader accepts case-insensitive folder structure and TIFF/PNG binary masks. It reads directly from ZIP entries, without uncompressing multi-GB TIFF collections to disk. It requires all five expert's mask FILES for a case, but v0.7 deliberately analyzes **expert1 as candidate, expert2 as the reference**; experts 3–5 are reserved for future robustness analysis. It rejects missing masks, mismatched pixel dimensions and invalid/non-binary masks.

**The published data layout and code were checked against the 2023 Scientific Data description and an independent open-source Chákṣu loader**, but **full compatibility with the original 10+ GB archive is not yet experimentally verified**.

**Strict requirement:** all 336 published Test images must have a complete five-reader filename inventory AND 336 usable first/second reader mask pairs for a standard external-domain report. An explicit `--allow-partial` option is available **only for synthetic fixtures/incomplete exploratory subsets** and flags the report as partial/unverified.

## 4. External endpoint and statistics

**Fixed reference discrepancy:** `abs(vCDR(expert1 mask) - vCDR(expert2 mask)) > 0.10`. This **is not a medical diagnostic threshold**. Using expert1 vs expert2 makes the target structurally comparable to the original PAPILA two-reader evaluation.

**Main ranking metrics:** precision and recall among the top 20% of images at fixed review budget. Tie-aware average precision (AP) and ROC-AUC are descriptive secondary scores; N/A if the required positive/negative cases do not exist.

**Strata:** report both aggregate Test and Bosch, Forus, Remidio separately. Device stratification is predeclared, but these groups can be small, so interpret wide uncertainty carefully.

**No patient-cluster confidence intervals on Chákṣu:** a complete, reliable patient identifier for every Chákṣu eye is not confirmed. It would be scientifically wrong to label images as distinct independent patients or to pretend patient-level bootstrap intervals are valid. v0.7 reports descriptive metrics and counts only.

**No retuning using Test results.** Any failure prompts either a documented excluded-case report, a versioned bug fix followed by revalidation, or a later independently held-out dataset. Do not call exploratory reanalysis confirmatory.

## 5. Windows setup and commands

```powershell
git pull
python -m pip install -e ".[ui,dev]"
pytest -q

# First freeze the SOURCE model from complete, locally acquired PAPILA.
hyunoptic-external freeze --papila-root "D:\\datasets\\PAPILA" --output "reports\\v07\\papila_frozen_mask_model.json"

# Separately download the official Chákṣu Test.zip under the publisher's terms:
# https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135
# Do NOT unpack the multi-GB archive just to read the provided TIFF masks.

hyunoptic-external test --model-lock "reports\\v07\\papila_frozen_mask_model.json" --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v07\\external"
```

**Keep reports separate from the public Git repository.** The evaluator writes:
- `external_aggregate.json` — per-camera and overall fixed-budget ranking metrics, source lock fingerprint, warnings and completeness status.
- `external_private_cases.json` — **case IDs and per-image metrics; do not share without ethics/license review**.
- `external_summary.md` — data-derived aggregate summary with no photographic images.

The Chákṣu downloader is **not** bundled and the experiment does **not** start automatically in GitHub Actions. Due to dataset volume and license/cloud processing considerations, the external Test ZIP is supplied locally by the researcher. **Neither user consent nor the actual 336-image external study result is presumed.**

## 6. Limitations and integrity statement

- This is **external-domain measurement DISAGREEMENT evaluation**, not validation of a clinical glaucoma diagnosis, treatment, or disease prognosis.
- Agreement/disagreement between expert annotators is not objective disease truth.
- PAPILA mask-v0.7 and Chákṣu mask-v0.7 features use shared definitions; v0.6 polygon features remain a separate historical experiment.
- Chákṣu camera shift can change the gradient and boundary-roughness distributions, potentially degrading transfer performance. Report negative results.
- Chákṣu contains five experts but this protocol intentionally uses the same first/second pair as the main endpoint; other-reader permutations require an additional preregistered sensitivity analysis.
- The 0.10 vCDR discrepancy threshold and 20% review budget are research settings, not medically established acceptability limits.
- No original full ZIP was analyzed in the agent runtime when this protocol was authored. All CI results described here use synthetic files.

## Sources

1. Chákṣu data descriptor, *Scientific Data* 2023: https://doi.org/10.1038/s41597-023-01943-4
2. Chákṣu distribution, Figshare: https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135
3. PAPILA data descriptor, *Scientific Data* 2022: https://doi.org/10.1038/s41597-022-01388-1
4. Public Chákṣu directory/mask reader implementation: https://github.com/staskh/fundus-atlas/blob/main/src/datasets/chaksu.py

## Roadmap

1. Run original PAPILA v0.7 freeze after successful inventory and inspect source masks/geometry.
2. Run Chákṣu Test.zip read-only on controlled, authorized local environment.
3. Compare frozen model with vCDR and q95 baselines and report device-wise cases/zeros/undefined metrics.
4. Inspect bad-mask and instrument-specific failures; distinguish method failure from format/parsing errors.
5. Report reproducibility, uncertainty, limitations and an honest negative result if appropriate.
6. Write a technical paper draft only after real observations and scientific review.
