# HyunOptic

**Quantitative Optic Nerve Measurement & Reliability Validation**

**Status: v0.1 executable research prototype (2026-10-24).** The software has undergone synthetic-data unit tests. **No PAPILA-wide or clinical validation, diagnostic performance, or novel uncertainty-detection result is claimed.**

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

## Planned research, not yet implemented

1. Paired boundary perturbation and covariance/bootstrapped measurement sensitivity.
2. **Reference-free quality-control** scores computed without a second reader.
3. Patient-disjoint internal validation and locked Chákṣu external evaluation.
4. Detailed failure-mode, reproducibility and subgroup analyses.
5. English research report, poster and PhD portfolio presentation.

**Research question:** Can a reference-free QC score better prioritize measurements that will disagree substantially with an independent expert at a fixed expert-review budget? This remains an untested hypothesis; prior literature already addresses segmentation, CDR and uncertainty.

## Project documentation

- [Korean research plan](docs/PROJECT_PLAN_KO.md)
- [English research protocol](docs/RESEARCH_PROTOCOL_EN.md)
- [Installation, data format and methodology](docs/GETTING_STARTED.md)

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
