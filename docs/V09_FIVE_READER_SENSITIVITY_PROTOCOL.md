# HyunOptic v0.9 — Five-Expert Disagreement Sensitivity (Secondary Analysis)

**2026-10-24 | Research-only protocol implemented in software. NO original Chákṣu or PAPILA results were generated in this release.**

## Motivation

The Chákṣu public archive offers five independent expert optic disc (OD) and optic cup (OC) annotations per image, rather than the two annotations available for each PAPILA eye. The v0.7/v0.8 Chákṣu study only measured disagreement between experts 1 and 2. A result that depends on one arbitrarily selected second reader may be misleading.

v0.9 retains the **EXISTING PRIMARY endpoint unchanged**:
- Candidate: optic-disc/cup masks from expert 1 and the fundus image.
- Held-out reference: expert 2 vertical CDR.
- Positive research target: `abs(vCDR_expert1 − vCDR_expert2) > 0.10`.
- Frozen review budget: top 20% of images by a fixed score.
- Overall and three-camera reporting.

The new **SECONDARY, exploratory endpoint** uses all five independent experts but does **not** change candidate feature calculation, scoring parameters, or source-model lock.

## Exactly how the five-reader secondary target works

For each Test image, denote the five experts' vertical cup-to-disc ratios by `r1…r5`.

**Candidate scoring:** use *only* image and expert 1's OD/OC masks. No expert 2–5 annotations, labels, fusion masks, or consensus values are inputs.

**Reference stage, after scoring:**
- Compute four differences `|r1-r2|, |r1-r3|, |r1-r4|, |r1-r5|`.
- Record their arithmetic mean and maximum.
- Predeclare **secondary high-disagreement** when **at least two of the four** differences exceed `0.10`.
- Independently calculate ten unordered pairwise differences among all five experts, their mean and maximum, and the sample SD of the five vCDR values. These are agreement descriptors, **not** clinical ground truth.

The 2-of-4 rule is an **arbitrary research operationalization**. The four reviewers are not assumed independent and their agreement is not a clinically established reference diagnosis. Do NOT call this a “majority diagnosis” or use it for patient triage.

## Outcome measures and safeguards

On the exact same original Test images and by camera:
- Primary expert1–expert2 discrepancy: existing precision@budget, recall@budget, tie-aware AP and ROC AUC.
- Secondary expert1–experts2–5 2-of-4 discrepancy: precision@budget, recall@budget, AP and ROC AUC (undefined metrics shown as N/A).
- Mean pairwise absolute vCDR across all 10 reader pairs, descriptively.
- Combined score versus simple candidate vCDR, reported side-by-side.
- Incomplete/malformed annotations cause case-level exclusions; a **complete external claim is blocked** when strict preflight does not pass.

**No new training on Test data.** A single source lock is created from PAPILA development data, and all five-reader outcomes are calculated AFTER the candidate-only score. Using this secondary outcome to tune model weights would invalidate its interpretation as held-out corroboration.

**No patient-level bootstrap or naive per-image p-values:** reliable patient grouping is not established for all Chákṣu images and some images may represent the same participant. With the available assumptions, results remain descriptive and hypothesis-generating. No clinical diagnosis or treatment performance can be inferred.

## How to run

Download and inspect official dataset usage terms first:
- [PAPILA](https://figshare.com/articles/dataset/PAPILA/14798004)
- [Chákṣu](https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135)

Locally on Windows, after `pip install -e ".[ui,dev]"`:

```powershell
hyunoptic-external freeze --papila-root "D:\\datasets\\PAPILA" --output "reports\\v09\\papila_mask_lock.json"

hyunoptic-chaksu-audit --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v09\\preflight" --strict

hyunoptic-external test --model-lock "reports\\v09\\papila_mask_lock.json" --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\v09\\external"

streamlit run app.py
```

Read the **External Validation** app page and select `external_aggregate.json`. On v0.9 reports it displays the added secondary five-expert table. Source images and private individual cases stay local. The textual `external_summary.md` also includes the secondary analysis.

Results must be explicitly labelled *unverified/incomplete* if the source or external dataset archive cannot pass the full structural preflight. If the primary Test results are observed before this hypothesis is registered externally, treat the analysis as exploratory; a Git SHA is not a recognized preregistration service.

## Existing limitations

1. The 0.10 discrepancy threshold is **not a clinical cutoff**.
2. Experts are not interchangeable with an objective independent disease gold standard.
3. Four peer annotations are correlated; consensus is not error-free.
4. The previously known v0.2/v0.7 `Q95` is a scaled vCDR baseline under fixed perturbation settings, not calibrated medical uncertainty.
5. Camera-specific differences may reflect acquisition or annotation practices rather than true image reliability.
6. Results from a single holdout must not be repeatedly used to redesign and retest the same score as a new confirmatory experiment.
7. Software unit tests use synthetic images/annotations; **no real case statistics have yet been measured**.

## Research progression

First run and validate the full official PAPILA source dataset, then freeze the mask scoring and external test protocol. Run the original Chákṣu Test archive with five-reader preflight, record failure counts and report both primary and secondary outcomes — including negative or undefined results. Subsequent academic reporting needs careful comparison to existing work, proper independent replication, and a clear scientific contribution.

## References

- Chákṣu source article, *Scientific Data* 2023: https://doi.org/10.1038/s41597-023-01943-4
- Chákṣu Figshare official distribution: https://doi.org/10.6084/m9.figshare.20123135
- PAPILA source, *Scientific Data* 2022: https://doi.org/10.1038/s41597-022-01388-1
