# HyunOptic — Research Concept & Evaluation Protocol (Draft)

**Title:** HyunOptic: An Uncertainty-Aware Framework for Quantitative Optic Nerve Measurement Validation  
**Version:** 0.1, 24 October 2026 | **Status:** Proposed research; no experiments have been performed.

## Abstract

Optic disc (OD) and optic cup (OC) segmentation allows fundus photographs to be summarized by measurement indices such as vertical cup-to-disc ratio (vCDR). Previous work already reports segmentation overlap metrics, vCDR errors, expert-reader variability and consensus annotations. HyunOptic proposes to evaluate whether **reference-free measurement-instability scores**, computed from a candidate image and candidate segmentation alone, can identify measurements likely to disagree substantially with a separate expert reading. This is a reliability-assessment research task, **not glaucoma diagnosis**.

## Research question

Can a pre-specified uncertainty/quality-control score detect high independent-reader vCDR disagreement at a fixed review budget, compared with feasible reference-free baselines, and retain usefulness on an external dataset?

## Proposed contributions — conditional, not established

1. A reproducible separation between measurement reliability and clinical diagnostic claims.
2. Paired geometric perturbation and empirical uncertainty analysis of vCDR, with explicit covariance handling.
3. A leakage-controlled retrospective evaluation in which the held-out reader is unavailable when computing the QC score.
4. A pre-locked external-data evaluation and transparent negative/failure-case reporting.

**Novelty is not guaranteed:** expert variability, CDR, Dice, IoU, and uncertainty are well studied. A literature gap will be assessed before claiming an original method.

## Data and study population

- **PAPILA:** 488 fundus images, both eyes from 244 patients, two experts' OD/OC contours and clinical data. Development and patient-disjoint internal evaluation. [Dataset](https://figshare.com/articles/dataset/PAPILA/14798004) | [Descriptor](https://doi.org/10.1038/s41597-022-01388-1). Figshare lists GPL 3.0+; confirm compliance before any redistribution.
- **Chákṣu:** 1,345 images from three fundus camera models with five-reader annotations. Locked external evaluation, including camera subgroups where sample sizes permit. [Dataset](https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135) | [Descriptor](https://doi.org/10.1038/s41597-023-01943-4). Listed as CC BY 4.0.
- **Harvard-GDP (optional extension only):** 1,000 OCT RNFL maps and partial progression labels; non-commercial research and CC BY-NC-ND terms. [Repository](https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP). Cross-sectional maps/labels do not justify longitudinal differential-equation modeling without time-indexed patient measurements.

## Primary experiment

**Input at inference:** single image + single candidate OD/OC segmentation; no second-reader annotation, consensus labels, or reference-based overlap scores.

**Prediction target:** whether the candidate vCDR differs from an independently held-out expert's vCDR by more than a research threshold τ. Pre-specify τ using the development process; e.g. 0.10 with sensitivity analysis at 0.05. These are **not clinical cutoffs**.

**Primary outcome:** detection of above-threshold disagreement at a fixed review quota (e.g. 20% flagged images), versus feasible baseline QC scores derived from the same input information. PR-AUC and coverage/error trade-offs are secondary or co-described; fix a single primary metric before testing.

**Internal design:** participant-disjoint splits (two eyes from the same person remain grouped). Prevent augmentation, derived contours, or feature selection leakage. Train/tune only on designated PAPILA development material. Lock hyperparameters and thresholds before external Chákṣu evaluation.

**External design:** use Chákṣu reader annotations to reproduce candidate/independent-reader separation. Report estimates with uncertainty, device-stratified performance and reader-choice sensitivity checks. Avoid calling expert agreement a disease gold standard.

**Uncertainty methods:** geometry validity checks, paired boundary perturbations, covariance-aware first-order delta approximation when its assumptions hold, empirical bootstrap sensitivity, and ablations with covariance/perturbation components removed.

**Comparators:** mask containment/validity rules, contour-shape/quality heuristics, perturbation-only scoring. Retrospective Dice against the reference reader is a descriptive metric **not** a deployable reference-free comparator.

**Statistics:** report effect sizes and patient-cluster bootstrap 95% intervals; note limitations when patient IDs are unavailable. Show failures and negative findings, not just means. Do not optimize thresholds on external test labels.

## Software deliverables

- Dataset adapter/validation and patient/eye metadata checking.
- OD/OC contours, masks, and vCDR/hCDR/aCDR measurement with unit tests.
- Reference-free quality scores, perturbation and uncertainty analysis.
- Evaluation scripts (internal, external, and ablations).
- Interactive local research viewer, accessible typography/keyboard interaction, CSV/JSON/HTML reports.
- Environment lock, deterministic seed, model/data provenance and reproducible commands.

## Schedule and acceptance gates

| Phase | Weeks | Gate |
|---|---|---|
| Scope, literature, and rights | 1 | Documented research gap and dataset provenance |
| Measurement MVP | 2 | Tested mask geometry and PAPILA loading |
| Uncertainty & QC | 3–4 | Deterministic output; no held-out-reader leakage |
| Locked external evaluation | 5–6 | Reproducible Chákṣu results and baselines |
| Research portfolio | 7–8 | English technical report, negative results, demo and code |

## Safety, ethics and limitations

This project is for research/education only; it is **not for clinical decisions or patient care**. CDR is only one structural measure and does not establish glaucoma diagnosis. No personal clinical datasets should be collected without applicable institutional approvals and privacy review. Raw dataset assets will not be stored in the public repository. Software licensing will be reviewed separately from research-data licenses. Reporting will follow suitable guidance such as TRIPOD+AI for prediction modeling or STARD-AI when a genuine diagnostic accuracy study is performed; these are not automatically applicable to the proposed measurement-reliability task.

## Research positioning

- **Biomedical Engineering:** imaging geometry, error propagation and evaluation rigor.
- **Health Sciences Informatics:** data reliability, auditability, and human-review prioritization.
- **Evidence-Based Health Care:** measurement uncertainty, external validity, scientific reporting and limitations.

## Sources

1. PAPILA: https://doi.org/10.1038/s41597-022-01388-1
2. Chákṣu: https://doi.org/10.1038/s41597-023-01943-4
3. Harvard-GDP: https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP
4. Retrospective DL vs manual OD/OC annotations: https://pmc.ncbi.nlm.nih.gov/articles/PMC7414704/
5. TRIPOD+AI: https://www.bmj.com/content/385/bmj-2023-078378
6. STARD-AI: https://www.nature.com/articles/s41591-025-03953-8
