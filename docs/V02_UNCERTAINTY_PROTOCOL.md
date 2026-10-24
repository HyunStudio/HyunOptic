# HyunOptic v0.2 — Geometric sensitivity and exploratory validation

**Date:** 2026-10-24. **Use:** research and education only. NOT for clinical use or glaucoma diagnosis.

## Measurement and statistical model

The candidate annotation (exp1) contains an optic cup and disc polygon. Let A and B be the **continuous coordinate** vertical extents of cup and disc respectively, and nominal R=A/B. The earlier v0.1 CDR is based on rasterized masks with inclusive pixel spans, so numerical quantization can differ slightly.

For reproducible Monte Carlo draws, generate G ~ N(0,σshared²), U ~ N(0,σcup²), V ~ N(0,σdisc²), mutually independent, then

- A_i = A × exp(G_i + U_i)
- B_i = B × exp(G_i + V_i)
- R_i = A_i/B_i

These hypothetical span perturbations are NOT calibrated to experts' real error. The shared G induces a synthetic covariance between A and B; if only G is present, it cancels exactly in R. The first-order delta-method variance uses

Var(R) ≈ Var(A)/E[B]² + E[A]² Var(B)/E[B]⁴ − 2 E[A] Cov(A,B)/E[B]³.

The v0.2 software reports the covariance-aware and covariance-omitting approximation, empirical perturbation variance, SD, 2.5/97.5 percentiles, and the **95th percentile of absolute perturbation-induced vCDR change** (candidate-only sensitivity/QC candidate score).

**Important distinctions:** The simulation percentile range is NOT a population-level or clinical confidence interval. The Q95 score is NOT the probability of error or a glaucoma probability. It can be driven by the assumed sigma values. No new method originality or patient outcome benefit has been established.

Defaults: 500 draws, seed 42, shared log-SD 0.02, cup 0.03, disc 0.03. These are illustrative settings, not fitted or medically recommended parameters.

## Local PAPILA retrospective audit

Using the PAPILA folder, the batch CLI computes Q95 from exp1 **before** reading expert 2. Only afterward are exp2 annotations used to calculate absolute inter-reader vCDR difference and Dice. For a pre-specified review fraction (default 20%) and *research* discrepancy threshold (default absolute difference >0.10), it calculates precision/recall at that review budget.

A patient-cluster bootstrap averages eyes per patient first, then resamples patients (2,000 draws), producing an interval for the **patient-weighted mean inter-reader absolute difference**. The interval is not a confidence interval on any individual image.

Example:
```powershell
hyunoptic --papila-root "D:\\datasets\\PAPILA_DBv1" --batch --output reports\\audit.json --csv-output reports\\audit.csv
```

Each report retains settings, case IDs, scores, retrospective disagreements, annotations flagged by the geometry validator and skipped-case reasons. Synthetic fixture tests verify modifying exp2 leaves the exp1-only score unchanged.

**Limitations:** This is **exploratory on one dataset, with no patient-disjoint train/test evaluation, no Chákṣu external validation, no calibrated boundary noise, and no comparison demonstrating superiority**. The two experts are not a disease ground truth. Do not interpret the discrepancy threshold as a clinical cutoff. Do not use the held-out reader's measurements or retrospective Dice as a prospective candidate-only input.

## Validity roadmap

1. Confirm PAPILA file coverage/coordinates from a lawfully obtained complete archive.
2. Examine sensitivity to assumed sigma and compare with more anatomical local deformation models.
3. Choose strong reference-free baselines and patient-disjoint development/test splits.
4. Lock model/threshold decisions before running Chákṣu external evaluation.
5. Report failures, effect sizes, uncertainty, device strata, sample sizes and negative results.
6. Prepare peer-review-quality methods and an Oxford/JHU research portfolio.

## CI and access boundaries

The automated synthetic-data tests cover seed determinism, zero perturbation, common scaling cancellation, covariance math, input validation, fixed-budget ranking, bilateral patient clustering and no use of exp2 by the candidate-only score. No third-party dataset is embedded, redistributed or automatically uploaded.

Reference context: [PAPILA Scientific Data](https://doi.org/10.1038/s41597-022-01388-1), [Chákṣu Scientific Data](https://doi.org/10.1038/s41597-023-01943-4). Dataset terms and code licensing remain separate matters.
