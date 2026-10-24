# HyunOptic

**Quantitative Optic Nerve Measurement & Reliability Validation**

**Status: v0.3 executable experimental research pipeline (2026-10-24).** The software has undergone synthetic-data unit tests and UI smoke tests through GitHub Actions; no full real-dataset scientific validation has been conducted. **No PAPILA-wide or clinical validation, diagnostic performance, or novel uncertainty-detection result is claimed.**

> Research/education only. **NOT for clinical use, glaucoma diagnosis, or patient-specific care.**

HyunOptic is an independent medical imaging research software project intended to explore the **reliability and reproducibility of optic disc/cup measurements**, rather than to produce medical diagnoses.

## Quick start

On Python 3.10+ (Python 3.12 recommended):

```bash
python -m venv .venv
# Activate the environment before running the commands below.
python -m pip install -e ".[ui,dev]"
pytest -q
streamlit run app.py
```

The viewer opens with a **synthetic geometry demo** that uses no patient images.

Windows PowerShell instructions, PAPILA file layout and CLI examples: **[Getting Started](docs/GETTING_STARTED.md)**.

## Implemented (v0.1)

- Local PAPILA image/annotation discovery, with **exact** expert contour filenames.
- Handles both eyes grouped by the same patient ID (`OD` = right eye; `OS` = left eye).
- Loads optic **disc** and **cup** contour coordinates from independent experts (`exp1`/`exp2`).
- Converts contours to full-resolution masks; measures **vertical**, **horizontal**, and **area** cup-to-disc ratios.
- Compares two readers' vCDR and disc/cup **Dice** overlap (retrospective comparison).
- Flags out-of-bounds annotations and inconsistent cup/disc geometry.
- Streamlit image overlay, optic disc crop, comparison table, JSON and PNG export.
- Offline CLI and synthetic data tests; GitHub Actions unit-test workflow for Python 3.10/3.12.

**The current app displays existing expert annotations; it does not yet segment new images autonomously.** Dice is computed with both experts present and is **not** a prospective reference-free QC score.

## Run PAPILA locally

1. Obtain [PAPILA](https://figshare.com/articles/dataset/PAPILA/14798004) under the distributor's stated terms.
2. Extract the dataset, keeping `PAPILA_DBv1/FundusImages/` and `PAPILA_DBv1/ExpertsSegmentations/Contours/`.
3. Use the sidebar in the Streamlit app or run:

```bash
hyunoptic --papila-root /path/to/PAPILA_DBv1 --image-id RET001OD --output reports/RET001OD.json
```

**No images or clinical dataset files are bundled or uploaded by the tool.** PAPILA format support was based on the dataset descriptor and file convention; running against the complete original archive is still required.

## Added in v0.2 (implemented as research prototypes)

- Reproducible candidate-only vertical-span perturbation simulation (independent/shared log-normal factors).
- Covariance-aware delta-method error propagation and empirical simulated vCDR variance.
- Simulated 2.5–97.5% range and Q95 absolute perturbation-induced vCDR change, **not medical confidence intervals or diagnostic probabilities**.
- Streamlit sensitivity control panel and candidate-only sensitivity export in JSON.
- Exploratory PAPILA batch CLI with JSON/CSV export, top-20%-review ranking, retrospective independent-reader comparison, and patient-cluster bootstrap for the **dataset-level** mean difference.
- No claimed calibration, diagnostic accuracy, external validation, novelty or superiority.

See [v0.2 uncertainty and evaluation protocol](docs/V02_UNCERTAINTY_PROTOCOL.md). The implemented perturbation model uses **assumed** correlated scale changes, not observed expert error. A proper patient-disjoint evaluation and Chákṣu external test remain future work.

Example batch command:

```bash
hyunoptic --papila-root /path/to/PAPILA_DBv1 --batch --output reports/audit.json --csv-output reports/audit.csv
```

## Added in v0.3 — patient-disjoint internal benchmark (CLI)

- Reference-free **candidate-only** image/contour features: cup-outline isoperimetric roughness and local grayscale boundary contrast, alongside v0.2 Q95 and vCDR comparators.
- Reproducible 60/20/20 **patient-level** development/validation/internal holdout partition (both eyes of one patient stay together).
- Fixed equal-weight combination of development-standardized candidate-only features; no fitting to or leakage of expert-2 labels.
- Precision and recall at a fixed 20% expert-review budget against retrospective **inter-reader vCDR disagreement**, not glaucoma outcomes.
- Patient-cluster bootstrap interval for paired precision difference versus v0.2 baseline, including possible null/negative results.
- JSON/CSV case reports, protocol hash, skipped-case trace, and regression tests that alter expert-2 labels without altering candidate-only scores.

**Why v0.3 matters:** with fixed log-scale perturbation settings, the previous Q95 sensitivity score is effectively proportional to candidate vCDR. v0.3 treats it as a *baseline*, not as newly demonstrated evidence of annotation unreliability.

Run with lawfully downloaded local PAPILA files:

```bash
hyunoptic-study --papila-root /path/to/PAPILA_DBv1 --output reports/v03.json --csv-output reports/v03.csv
```

Details: [v0.3 patient split / evaluation protocol](docs/V03_PATIENT_SPLIT_PROTOCOL.md).

**Scientific limit:** Candidate scoring logic and synthetic tests are implemented; no actual full PAPILA trial, superiority claim or independent external Chákṣu test is completed. The v0.3 benchmark is exploratory, not a glaucoma diagnostic tool. The interactive Streamlit viewer remains focused on the v0.2 measurement and sensitivity screens.

## Planned research, not yet implemented

1. Running and verifying full PAPILA-file compatibility and reporting predeclared internal outcomes without holdout tuning.
2. Testing anatomical/spatial perturbations and stronger literature-supported reference-free baseline methods.
3. Patient-disjoint internal validation and locked Chákṣu external evaluation.
4. Failure-mode, reproducibility and subgroup analyses using real data.
5. English research report, poster and PhD portfolio presentation.

**Research question:** Can a reference-free QC score better prioritize measurements that will disagree substantially with an independent expert at a fixed expert-review budget? This remains an untested hypothesis; prior literature already addresses segmentation, CDR and uncertainty.

## Project documentation

- [Korean research plan](docs/PROJECT_PLAN_KO.md)
- [English research protocol](docs/RESEARCH_PROTOCOL_EN.md)
- [Installation, data format and methodology](docs/GETTING_STARTED.md)
- [v0.2 sensitivity and exploratory research protocol](docs/V02_UNCERTAINTY_PROTOCOL.md)
- [v0.3 patient-disjoint internal research protocol](docs/V03_PATIENT_SPLIT_PROTOCOL.md)

## Research dataset information

| Dataset | Planned role | Source |
|---|---|---|
| PAPILA | Two-expert imaging and measure-comparison development | [2022 Scientific Data paper](https://doi.org/10.1038/s41597-022-01388-1) · [Figshare](https://figshare.com/articles/dataset/PAPILA/14798004) |
| Chákṣu | Future external reader/device reliability testing | [Scientific Data paper](https://doi.org/10.1038/s41597-023-01943-4) |
| Harvard-GDP | Optional later OCT/RNFL research | [Research repository](https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP) |

Respect the individual dataset license, consent and redistribution restrictions. Do not place raw eye images or private clinical information in this public repo. No clinical deployment is permitted.

## Technology

Python · NumPy · Pillow · Streamlit · pytest. Research dataset ingestion uses local files; no automatic downloads, API keys or cloud upload endpoints.

## License

A software license has **not yet been selected**. Dataset licenses and code licenses are separate; do not assume the dataset is re-licensed by this repository.
