# HyunOptic — Getting Started (v0.1)

**Research only. Not intended for clinical use.**

## Install (Windows PowerShell, Python 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[ui,dev]"
pytest -q
streamlit run app.py
```

For the CLI only: `python -m pip install -e .` (Streamlit not needed).

## Run offline without a dataset

Launch `streamlit run app.py`, select **Synthetic demo**. This uses computer-generated shapes, **not real fundus images**. It verifies geometry and viewer functions but does NOT validate a clinical measurement.

## Run with PAPILA data

1. Read the [dataset paper](https://doi.org/10.1038/s41597-022-01388-1) and [license and dataset instructions](https://figshare.com/articles/dataset/PAPILA/14798004). Download yourself; this repo does not distribute dataset assets.
2. Extract the downloaded directory somewhere **outside the repo** (preferably) or under gitignored `data/`.
3. The loader recognizes either of these paths:

```
<root>/PAPILA_DBv1/FundusImages/RET001OD.jpg
<root>/PAPILA_DBv1/ExpertsSegmentations/Contours/RET001OD_disc_exp1.txt
<root>/PAPILA_DBv1/ExpertsSegmentations/Contours/RET001OD_cup_exp1.txt
# exp2 and the OS eye share analogous names.
```

4. In the Streamlit sidebar choose **Local PAPILA folder** and paste the directory path. Select case and expert.
5. Or produce one JSON report from the command line:

```powershell
hyunoptic --papila-root "D:\datasets\PAPILA_DBv1" --image-id RET001OD --output reports\RET001OD.json
```

PAPILA expert contour files must be whitespace-delimited (x,y) coordinates in **full-resolution pixel space**. The loader expects exact `_cup_exp1.txt`/`_disc_exp1.txt` and `_exp2.txt` names; extra duplicate files (e.g., `exp2 2.txt`) are ignored. The loader skips incomplete cases. `OD`/`OS` identify **right**/**left** eye, not optic disc. Data are not uploaded by the software.

## Measurement definitions

- **vCDR**: vertical extent of the cup mask divided by vertical extent of the disc mask.
- **hCDR**: horizontal extent ratio.
- **aCDR**: pixel-area ratio. This is **not** vCDR.
- Rasterization: PIL polygon fill, mask spans in pixel units measured on original image.
- Red/coral is cup, cyan is disc, with text labels in UI.
- Out-of-disc cups or invalid contour points are surfaced as warnings/errors, **not silently repaired**.
- Dice and reader vCDR differences describe **retrospective inter-reader agreement** only.

## Limitations / next phase

- No trained glaucoma classifier, reference-free QC score, clinical diagnostic output, uncertainty calibration or external validation is present in v0.1.
- Different contour rasterization conventions can change pixel-level results; use one convention for all baselines and document any comparisons.
- The full PAPILA archive was not bundled with this release. Run the application against your lawful local download to confirm dataset-wide compatibility.
- Next phase: boundary perturbation analysis and leak-proof reference-free QC assessment with patient-group splits and external evaluation.

## HyunOptic v0.2 — Candidate-only sensitivity

The Streamlit sidebar provides a Monte Carlo **geometry sensitivity** experiment with configurable shared and independent log-normal perturbations. The simulated 2.5–97.5% range is **not a clinical confidence interval**; the 95th-percentile absolute vCDR change is **not a probability that an annotation is wrong**.

The single-case CLI JSON now includes a `candidate_only_sensitivity` object. For an **exploratory retrospective** batch audit (not an independent external validation), run:

```powershell
hyunoptic --papila-root "D:\\datasets\\PAPILA_DBv1" --batch --output reports\\papila_audit.json --csv-output reports\\papila_audit.csv
```

For the batch, candidate scores are computed from `exp1` only and later compared with independent `exp2` results. A patient-group bootstrap estimates a **dataset-level** mean difference rather than treating two eyes as independent people. No novel reliability performance, patient-disjoint validation, external testing or clinical usefulness has been established. See the [v0.2 method limitations](V02_UNCERTAINTY_PROTOCOL.md).
