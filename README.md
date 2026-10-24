# HyunOptic

**Quantitative Optic Nerve Measurement & Reliability Validation**

**Status: v0.2 executable research prototype (2026-10-24).** The software has undergone synthetic-data unit tests and UI smoke tests through GitHub Actions. **No PAPILA-wide or clinical validation, diagnostic performance, or novel uncertainty-detection result is claimed.**

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

## Planned research, not yet implemented

1. Validating actual PAPILA-file coverage and realistic **spatial** contour perturbations.
2. Calibrated and comparative reference-free QC scores (v0.2 Q95 is a hypothetical candidate score, not a validated reliability prediction).
3. Patient-disjoint internal validation and locked Chákṣu external evaluation.
4. Failure-mode, reproducibility and subgroup analyses using real data.
5. English research report, poster and PhD portfolio presentation.

**Research question:** Can a reference-free QC score better prioritize measurements that will disagree substantially with an independent expert at a fixed expert-review budget? This remains an untested hypothesis; prior literature already addresses segmentation, CDR and uncertainty.

## Project documentation

- [Korean research plan](docs/PROJECT_PLAN_KO.md)
- [English research protocol](docs/RESEARCH_PROTOCOL_EN.md)
- [Installation, data format and methodology](docs/GETTING_STARTED.md)
- [v0.2 sensitivity and exploratory research protocol](docs/V02_UNCERTAINTY_PROTOCOL.md)

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
