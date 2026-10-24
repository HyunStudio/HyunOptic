# HyunOptic v0.6 — Reader-Role Robustness and Agreement Audit

**Version:** 0.6.0 · **Status:** implemented analysis pipeline; no real PAPILA study results claimed · **Date:** 2026-10-24

> Research/education only. NOT glaucoma diagnosis, a clinically validated device, or independently replicated evidence.

## Why this is scientifically necessary

PAPILA has two independent expert contour sets for each eye. v0.3–v0.5 predicted retrospective expert discrepancy while always treating **expert 1** as the candidate measurement. A reliability method that only works for one reader or annotation convention may not generalize to another specialist.

**Research question:** When the two independent readers exchange candidate and reference roles, do candidate-only measurement-quality scores preserve their relative ranking and fixed-budget error discovery rate?

This directly tests **reader-dependence**, not disease diagnosis, and it does not prove methodological novelty.

## Experimental protocol

For each eye in PAPILA:
1. Load original image and both expert polygons.
2. Compute candidate-only features from image + exp1 polygons, without using exp2 coordinates.
3. Independently compute the same features from image + exp2 polygons, without using exp1 coordinates.
4. Only after both feature sets exist, compute the retrospective **absolute vCDR difference**, common to both directions.
5. Keep the bilateral patient-disjoint 60/20/20 split fixed using deterministic seeded patient hashes.
6. For each candidate direction, fit unlabeled feature standardization using only that direction's **development** partition. Never fit on validation/holdout outcomes.
7. Apply the fixed, untrained equal-weight combination. Evaluate without searching thresholds or weights on holdout cases.

The two directions have the SAME retrospective disagreement target but independent candidate-only features. Their score rankings may differ. If a result is worse in one direction, report it.

## Reported outcomes

- **Precision and recall at fixed review quota (20% default)** for `|vCDR(exp1) − vCDR(exp2)| > 0.10` (research threshold only).
- **Average precision (AP)** across all distinct-score thresholds; report N/A when no high-disagreement cases exist.
- **ROC-AUC** with positive/negative tie score 0.5; report N/A if either class is absent. This is AUC for **reader disagreement**, never glaucoma diagnosis.
- **Top-k review overlap** between exp1-candidate and exp2-candidate at the fixed review quota. High overlap means less sensitivity to reader choice; it does not prove correctness.
- **Tie-aware Spearman correlation** between reader-specific QC scores; N/A when all scores are constant.
- **Signed Bland–Altman vCDR bias and descriptive normal-theory limits of agreement** exp1 minus exp2, along with patient-cluster resampled percentile intervals.

### Interpretation safeguards

1. **Both eyes from a patient are correlated.** We bootstrap the measurement-agreement intervals by patient. Simple normal-theory LoA are descriptive for the observed eye-level differences, not a model that removes all repeated-eye effects.
2. Normal-theory Bland–Altman LoA assume appropriate difference distributions and negligible proportional bias/heteroscedasticity. We have not verified those assumptions on PAPILA, so conclusions are exploratory.
3. Neither reader represents a medical reference standard. Study targets characterize **annotator disagreement**, not false glaucoma diagnoses.
4. Rank ties are handled explicitly for AP/AUC; fixed-budget top-k uses deterministic sorted image order.
5. The perturbation Q95 score is analytically close to a rescaled candidate vCDR with fixed simulation sigmas; it is a **baseline**.
6. PAPILA is one single-center corpus. Reader-role reversal is not external hospital/camera validation.
7. We must freeze an external-data protocol and avoid tuning repeatedly on the same internal holdout before examining Chákṣu.

### Code-level leakage guard

The candidate feature function accepts **one image, one optic-disc contour and one optic-cup contour**, not the comparison expert's labels. Regression tests mutate expert 2 contours, verifying all expert-1 candidate-only features and combined scores stay unchanged. Evaluation-target differences are allowed to change.

## Running on Windows

First use the official data download guide in [v0.5](V05_REPRODUCIBLE_REAL_DATA_RUN.md). Once the original PAPILA archive is available locally:

```powershell
git pull
python -m pip install -e ".[ui,dev]"
pytest -q

hyunoptic-reader-check --papila-root "D:\\datasets\\PAPILA" --output-dir "reports\\reader_v06"
streamlit run app.py
```

Open the **Reader Roles** page and upload `reports/reader_v06/reader_symmetry.json`.

Default strict mode requires the complete published dataset layout. For synthetic software fixtures or incomplete exploratory subsets only, add `--allow-partial`; the output will explicitly mark the data partial/unverified.

### Outputs

| Filename | Contents | Public sharing guidance |
|---|---|---|
| `inventory.json` | Local file completeness and dimensions | Contains original image IDs; review before publication |
| `reader_symmetry.json` | Full case-level and aggregate analysis | **Keep private** pending data/license review |
| `reader_case_metrics.csv` | Per-eye candidate score and disagreement | **Keep private** pending data/license review |
| `reader_role_summary.md` | Aggregate precision/AP/AUC and Bland–Altman description | Can be considered for sharing after verifying accuracy and licensing |

By default, the pipeline generates no fabricated patient outcomes. Automated CI tests operate on synthetic data only.

## Next phase

1. Execute and inspect the official PAPILA archive on a controlled machine.
2. Verify contour coordinate handling against the authors' bundled `HelpCode`, particularly vertical/horizontal diameter definitions.
3. Evaluate proportional bias and heteroscedasticity before making clinical-style agreement claims.
4. Publish reproducible internal results including negative findings and sensitivity to expert selection.
5. Design a locked Chákṣu adapter (5 independent experts and multiple devices) for an *external-domain*, not clinical-deployment, evaluation.
6. Decide on novelty after explicit literature comparison; a replication/generalizability study can be useful without inventing a new equation.

## Methods references

- Kovalyk et al. 2022, PAPILA (Scientific Data): https://doi.org/10.1038/s41597-022-01388-1
- PAPILA official Figshare v2: https://figshare.com/articles/dataset/PAPILA/14798004
- Giavarina 2015, Understanding Bland Altman analysis: https://pmc.ncbi.nlm.nih.gov/articles/PMC4470095/
- Koo & Li 2016, Reliability and agreement reporting: https://pmc.ncbi.nlm.nih.gov/articles/PMC4913118/
- 2020 measurement comparison guideline: https://pubmed.ncbi.nlm.nih.gov/32252039/
