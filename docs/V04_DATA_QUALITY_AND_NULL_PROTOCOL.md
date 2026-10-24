# HyunOptic v0.4 — Dataset Integrity and Patient-Level Null Checks

**Date:** 2026-10-24  
**Research stage:** executable engineering/analysis infrastructure, **not** a peer-reviewed or clinically validated result.

## 1. Rationale

v0.3 implemented an exploratory internal benchmark for disagreement between the PAPILA experts. v0.4 improves **reproducibility and auditability** by (a) checking a local PAPILA archive before analysis and (b) comparing internal holdout rankings with a patient-group label-permutation null. It is not a claim that HyunOptic diagnoses glaucoma.

## 2. PAPILA inventory gate

The data-descriptor paper reports:
- 244 patients with 2 eyes each → **488 JPEG images**.
- For each eye, cup/disc contours by 2 experts → **1,952 canonical contour TXT files**.
- Published original JPEG dimensions: 2576 × 1934 pixels.
- Two eye codes: **OD = right eye**, **OS = left eye**.

Official dataset and paper:
- https://figshare.com/articles/dataset/PAPILA/14798004
- https://doi.org/10.1038/s41597-022-01388-1

`hyunoptic-inventory` checks dataset path, patient/eye mapping, image-header dimensions, canonical annotation completeness, numeric coordinate bounds, unreadable files, duplicate-like TXT names, and expected full-package counts. Optional `--verify-pixels` verifies JPEG payload integrity. It creates JSON without reading clinical diagnosis labels or exporting patient images. A metadata-only SHA-256 fingerprint is reported as a stable **names/byte sizes** fingerprint and does **not** attest to content integrity.

**Important:** A non-official subset may be useful for software testing but will never pass the full-size inventory check. The inventory does not prove the content is authentic or all coordinates align clinically. Actual archive compatibility remains unverified until a complete official archive is processed.

### Run

```powershell
hyunoptic-inventory --papila-root "D:\\datasets\\PAPILA_DBv1" --output reports\\inventory_v04.json --strict-full --verify-pixels
```

The command writes the audit file even if the strict full-data check fails, then exits with nonzero status. The source archive must be obtained directly under the distributor's terms; no dataset files are packaged or automatically uploaded.

## 3. Research-only patient-group permutation baseline

**Question:** At a fixed review quota, could a candidate-only QC score select high expert-disagreement observations more effectively than rankings unrelated to those disagreement labels?

- Rank candidate features without access to reader 2.
- Hold candidate ranking fixed.
- Permute reader-disagreement outcome **by patient group** (not eye by eye); when a patient has only one eye, permute only among others with the same OD/OS configuration.
- Recompute precision@budget over 499 seeded draws (default).
- Report observed precision, permutation-null mean, null 2.5–97.5 percentiles, and exploratory one-sided tail proportion with plus-one correction.

Assumptions: patients are exchangeable within laterality patterns under the null; this may fail for site, diagnosis mix, age, image quality or other factors. A null test is not clinical proof or confirmatory multiple-comparison-adjusted significance. Do not compare values across repeatedly optimized internal holdout protocols.

## 4. Reproducibility and anti-leakage

- Data splitting uses patient IDs, keeping OD and OS with the same participant.
- v0.4 references fixed candidate-only features, with all normalization parameters fitted on development features **without** reader-2 outcomes.
- The second reader is used only as an evaluation target, never as a prospective QC input.
- Internal holdout results cannot be advertised as hospital-to-hospital external validation.
- Every report retains a SHA256 digest of the chosen protocol settings, except this hash is not a digitally signed preregistration.
- Synthetic-data unit tests verify that changing expert 2 does not alter candidate score and that patient grouping is preserved.

## 5. Planned limitations and next required steps

1. **Run actual PAPILA archive** with inventory + study commands and review all skipped cases. A complete source archive was not available in the execution environment when this version was authored. No real-patient performance numbers are shown here.
2. Compare annotation geometry with published/reference scripts on manually inspected original cases.
3. Document size and uncertainty of high-disagreement outcomes in internal holdout.
4. Freeze method and thresholds before independent Chákṣu evaluation; ensure the five-expert annotations are correctly represented and assess potential site and camera shift.
5. Make an experimental methods table and clearly label results if null or inconclusive.
6. For graduate admission, discuss the methodological contribution and constraints rather than claiming innovation simply from using covariance or complex equations.

## 6. Portfolio claim boundaries

**Appropriate now:** “Implemented a reproducible ophthalmic measurement audit and exploratory patient-disjoint evaluation pipeline, including quality checks, covariance simulations, and patient-group null controls.”

**Not yet supported:** “Developed a clinically accurate glaucoma detector” or “demonstrated significant improvement in real-world optic nerve measurements.”

This protocol is a working **research plan and implemented evaluation framework**, not completed validation evidence.
