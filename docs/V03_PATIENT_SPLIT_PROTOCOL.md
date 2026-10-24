# HyunOptic v0.3 — Patient-Disjoint Internal Benchmark

**Protocol draft, 24 October 2026. Research only — not for clinical decisions.**

## Why v0.3?

Under the v0.2 fixed log-scale model, the 95th percentile of absolute vCDR perturbation is proportional to nominal continuous-coordinate vCDR, because

\[
R_i=\frac{A\exp(G_i+U_i)}{B\exp(G_i+V_i)}
=\frac AB\exp(U_i-V_i).
\]

Therefore, with one fixed draw sequence across all cases, v0.2's Q95 is effectively a monotone scaling of vCDR, **not established independent evidence of unreliable annotation**. v0.3 explicitly includes both `v02_q95` and `candidate_vcdr` as negative-control comparators. Do not report v0.2 Q95 as a novel performance improvement.

## v0.3 research question

Can *candidate-only* contour roughness and local image boundary contrast help prioritize cases with high disagreement between two independent readers at a fixed review capacity, beyond simpler vCDR/Q95 ranking?

**This is exploratory and unproven.** A difference between two experts is not glaucoma ground truth, and a single dataset cannot establish external validity.

## Dataset and split

PAPILA: original right/left eye images and two expert cup/disc contour sets. A stable SHA-256(patient ID + split seed) ordering produces **60% development, 20% validation and 20% internal holdout by patient**. Both eyes of a patient always share the same split.

1. Create candidate features using each image plus first expert `exp1` contours only.
2. Load independent expert `exp2` contours **after** candidate feature calculation, and calculate absolute vCDR difference.
3. Develop feature scaling using **unlabelled development-split feature distributions only**.
4. Run fixed, equal-weight and capped z-score combination; no label-based fit is performed.
5. Evaluate all baseline and combined scores on validation and internal holdout partitions without parameter search.
6. Provide patient-cluster bootstrap interval of **difference in precision@budget** between the combined candidate score and v0.2 Q95. This is exploratory and may include zero or negative values.

**No validation/holdout results from this study should be repeatedly used to tune the score**. A truly independently locked prospective or external Chákṣu test is a later project.

## Candidate-only comparison features

| Column | Definition | Direction |
|---|---|---|
| `candidate_vcdr` | Rasterized vertical cup/disc span ratio | larger-first baseline |
| `v02_q95` | 95th percentile of absolute vCDR change under fixed hypothetical paired log perturbations | larger-first baseline; related to vCDR |
| `cup_roughness` | Isoperimetric excess P²/(4πA)−1 from candidate cup polygon | larger = more irregular |
| `cup_boundary_weakness` | 1 − mean normalized grayscale gradient sampled along cup contour vertices | larger = weaker sampled edge contrast |
| `combined_candidate_score` | Mean of capped [−3,3] development-standardized Q95, roughness, weakness, plus 3 | larger = selected sooner |

Every feature is calculated without second-reader annotations. The grayscale edge feature is sensitive to camera settings, focus, photometric conditions and point sampling; it is only a **hypothesis-generating signal**. The roughness indicator also depends on annotation style. These features are not calibrated glaucoma uncertainty estimates.

## Retrospective outcome and review-budget metrics

- Target: `abs(vCDR_exp1 − vCDR_exp2) > 0.10` by default, research threshold **not** a medical boundary.
- Fixed review budget: first `ceil(0.20 × N)` cases sorted by score, default.
- Precision@budget, recall@budget (null if no positive cases), number of positive examples.
- Equal-patient resampling for *paired* bootstrap on precision delta, maintaining bilateral grouping.
- Seeds, sample counts, excluded case reasons, scoring settings and protocol SHA256 are exported.
- The same internal holdout is **not an independent external hospital or camera test**.

## Execution

Download PAPILA from its official distribution page under the relevant dataset terms, and keep the extracted data on your own computer, outside the public Git repository.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest -q
hyunoptic-study --papila-root "D:\\datasets\\PAPILA_DBv1" --output reports\\v03.json --csv-output reports\\v03.csv
```

Run `hyunoptic-study --help` for research threshold, fraction and reproducibility seeds. This command does **not** download data or upload eye images. Source code and tests are available on GitHub; no real PAPILA study result should be claimed until the original data have actually been executed and its logs reviewed.

## Acceptance and publication discipline

1. Verify contour parsing against the **original** PAPILA complete archive.
2. Report each split's patient count, eye count, high-disagreement prevalence and skip reasons.
3. Report internal holdout metrics, paired bootstrap intervals and all negative results.
4. Assess reader-selection sensitivity, threshold sensitivity **as clearly secondary** analysis.
5. Before claiming any novel QC method, review recent work on inter-reader disagreement and image-based annotation quality; replicate meaningful baselines.
6. Build a Chákṣu loader and freeze all settings before any external analysis. Note that Chákṣu is roughly 10.56 GB compressed; access and protocol feasibility matter.
7. Do not infer clinical safety, diagnostic accuracy or glaucoma prognosis from agreement metrics.

## Foundational dataset descriptions

- PAPILA: https://doi.org/10.1038/s41597-022-01388-1
- Official PAPILA dataset: https://figshare.com/articles/dataset/PAPILA/14798004
- Chákṣu: https://doi.org/10.1038/s41597-023-01943-4
- Official Chákṣu dataset: https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135
