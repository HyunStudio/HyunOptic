# HyunOptic v0.8 — External Archive Integrity and Interpretation Gate

**Date:** 24 October 2026 | **Status:** Software QA on synthetic archives; no full PAPILA or Chákṣu research run was conducted.

## What v0.8 fixes

Earlier versions checked that the Chákṣu Test.zip contained 336 images and paths to five experts' disc/cup masks, but the primary evaluation decoded only the first two experts' masks. The remaining experts' *file existence* is insufficient evidence that the archive is structurally usable. v0.8 creates a dedicated **all-five-reader payload preflight**, and makes full payload verification a hard gate for unqualified external-domain evaluation.

The loader also accommodates dataset naming differences: the published material calls the Remidio/Remedio camera by both spellings, and some archive layouts call the top-level partition `Test`, `Test set`, or `Test_set`. These aliases are handled without interpreting training data as a test set.

### Data-distribution facts

The Chákṣu Scientific Data article (2023) reports 1,345 fundus images, including **336 Test** images: Bosch 41, Forus 31, Remidio 264, with five expert OD/OC annotations per image. The article describes masks under `3.0_Doctors_Annotations_Binary_OD_OC`; fused masks are not independent annotator ground truth.

- https://doi.org/10.1038/s41597-023-01943-4
- https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135

## New audit command

Run on the official local Chákṣu Test.zip. ZIP is read in place; the app does not extract TIFFs or transmit eye photos.

```powershell
git pull
python -m pip install -e ".[ui,dev]"

# Preflight every published Test image and all five experts.
hyunoptic-chaksu-audit --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v08\\chaksu_audit" --strict
```

Use `--max-cases 10` only for a quick diagnostic. Such a subset **always** reports partial/unverified; it cannot pass full strict validation.

Output files:
- `audit_aggregate.json` — counts, camera-specific readable cases, decoded mask failures, mismatched published camera resolution, structural completeness; contains no case IDs.
- `audit_private_errors.json` — case identifiers and raw error strings for local diagnostics; do not publish.

**Data integrity gates:** published split structure, total count, five expert mask paths, binary nonempty masks, matching image/mask dimensions, cup-within-disc containment, declared camera resolution, and no problematic duplicate/encrypted/oversize members. Any failure prevents full QA confirmation. The program never silently repairs human annotations.

**Important limitations:** even if all checks pass, the source may not be authentic or annotations medically correct. Verify publisher checksums and data terms separately. Legitimate expert masks may occasionally fail strict geometric containment; document such observations as exclusion/sensitivity questions rather than editing the raw dataset to force a pass.

## External-domain ranking comparison

For a full external research run, v0.8 now requires the five-reader structural preflight. It preserves the already frozen PAPILA development-only mask scoring method and reports:
- Precision/recall at the frozen 20% review budget, AP, and ROC AUC.
- Overall Test results and Bosch/Forus/Remidio subgroups.
- **Descriptive paired-cohort differences** between the combined candidate score and vCDR-only ranking (precision, recall, AP, ROC AUC where defined).

These are disagreement metrics against a second expert **not** glaucoma diagnostic scores. No patient-cluster CI, p-value, or significance claim is generated for Chákṣu because complete independent-patient grouping is not established. Repeated imaging of a person would invalidate a naive per-image independent-bootstrap CI.

The summary explicitly labels differences *descriptive*, whether favorable, negative, or zero. It must not be used to repeatedly optimize scoring after the Test outcome has been viewed.

## Suggested reproducible execution

```powershell
# 1) PAPILA model-lock (locally obtained official 488-image corpus)
hyunoptic-external freeze --papila-root "D:\\datasets\\PAPILA" --output "reports\\v08\\papila_frozen_mask_model.json"

# 2) Full five-expert Chákṣu payload preflight
hyunoptic-chaksu-audit --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v08\\audit" --strict

# 3) Only after the preflight, run external Test with the SAME frozen scoring
hyunoptic-external test --model-lock "reports\\v08\\papila_frozen_mask_model.json" --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v08\\external"

# 4) Display local read-only aggregate metrics
streamlit run app.py
```

The external command repeats its own strict preflight for a defensible default. This adds I/O overhead but prevents a user from bypassing integrity checks simply by skipping the standalone audit. Only the aggregate report is potentially shareable, after verifying its content and the dataset license.

## Engineering completion vs scientific evidence

- **Implemented/tested with synthetic data:** filename variants, malformed/missing reader masks, camera resolution issues, manifest restrictions, source-lock and held-out-label separation, ranking output.
- **Not established:** full real Chákṣu compatibility, scientific benefit over simple vCDR, robustness across hospitals, clinical glaucoma diagnosis accuracy, independent patient-group confidence intervals or original algorithmic novelty.

**Next research priority:** Run a fully authorized official PAPILA dataset and Chákṣu Test archive; preserve failures, original frozen lock and execution hashes; only then interpret numeric effects. If structural checks prove too strict for authentic published masks, investigate and version a documented change without converting the same Test split into a fresh confirmatory holdout.
