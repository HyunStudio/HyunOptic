# HyunOptic v0.5 — Official Dataset Acquisition, Reproducibility Gate, and Research Reporting

**Status:** executable research infrastructure; real PAPILA-wide performance has **not** been measured or claimed by this release (2026-10-24).

## What changed

The v0.4 code evaluates inter-reader measurement consistency on a local PAPILA dataset. v0.5 adds an explicit provenance and execution chain so that **study metrics cannot silently be presented as originating from a complete original dataset when only an incomplete fixture is present**.

### The five-stage provenance chain

1. **Official metadata lookup:** query Figshare article ID [14798004](https://figshare.com/articles/dataset/PAPILA/14798004) over HTTPS and locate its unique `PAPILA.zip` entry.
2. **Local opt-in download:** explicitly acknowledge the dataset license/terms. Download to a new ZIP file only. Verify downloaded file size and Figshare-supplied MD5 if published; always calculate local SHA-256. Never overwrite the original ZIP.
3. **Safe extraction:** refuse ZIP path traversal, symlinks, encrypted archive entries, unsafe expansion size and existing extract directories.
4. **Inventory gate:** create a local `inventory.json`, checking the expected **244 patients, 488 fundus images, 1,952 contour files and 2576×1934 source image resolution**. Reject incomplete material for the strict full dataset run. **Shape checks are NOT proof of authenticity or clinical validity.**
5. **Exploratory internal research run:** run the existing patient-disjoint v0.4 study, generate CSV/JSON, a provenance JSON manifest and a study-derived Markdown summary.

A complete download is approximately **563 MB**. Extraction and analysis require additional disk space and may require substantial CPU time. This release has **not** been tested end-to-end against the official archive.

## Windows PowerShell commands

Run on Windows with Python 3.12 and a local data folder outside the GitHub repository.

```powershell
git clone https://github.com/HyunStudio/HyunOptic.git
cd HyunOptic
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[ui,dev]"
pytest -q

# First read the terms here: https://figshare.com/articles/dataset/PAPILA/14798004
hyunoptic-download --archive "D:\\datasets\\PAPILA.zip" --extract-to "D:\\datasets\\PAPILA" --accept-dataset-terms

# Default strict mode blocks evaluation of incomplete archives:
hyunoptic-reproduce --papila-root "D:\\datasets\\PAPILA" --output-dir "reports\\v05" --verify-pixels
```

The command should create:
- `reports/v05/inventory.json`: local dataset completeness and annotation checks.
- `reports/v05/study.json`: exploratory internal cohort results (contains pseudonymized eye IDs; **do not publish raw per-case output without review**).
- `reports/v05/case_metrics.csv`: per-case figures, for private research quality checks.
- `reports/v05/run_manifest.json`: dataset inventory fingerprint, protocol hash, output SHA-256, explicit partial/full status.
- `reports/v05/research_summary.md`: **data-derived, aggregate** metrics, uncertainty intervals and limitations, with no raw fundus images.

**Important:** A subset or synthetic fixture needs `--allow-partial` to run, and the provenance manifest **explicitly marks it partial**. Never advertise its result as a full-dataset study.

## GitHub Actions alternative (manual only)

The repository includes **Actions → PAPILA research run (manual, consent required) → Run workflow**. The runner downloads the official dataset to its temporary filesystem and publishes only the **aggregate Markdown report and run manifest** as an ephemeral 7-day Actions artifact. It does not publish or commit source photographs, clinical spreadsheet files, or per-case result tables.

Before selecting **AGREE**, decide whether the dataset's access terms, security expectations and your institution's policies permit processing on a GitHub-hosted third-party cloud runner. If not, use the local Windows workflow instead. The workflow does not start automatically on Git pushes.

## Scientific interpretation

Primary research task remains **measurement consistency**, not glaucoma diagnosis:
- Candidate-only features: vCDR / hypothetical Q95 perturbation, cup contour roughness and fundus edge contrast.
- Internal patient-disjoint split (60/20/20). Development-only unlabeled scaling.
- Independent second reader for retrospective target; no second-reader data enter candidate features.
- Fixed review-budget precision and recall; pairwise patient-cluster bootstrap.
- Exploratory permutation-null comparison.
- Research-only discrepancy threshold (default |ΔvCDR| >0.10), not a diagnostic cutoff.

A claim such as “our model improves glaucoma diagnosis” or “a medically meaningful difference” is **not supported** by this pipeline. Actual study results, baselines, a critical literature review and independently frozen external validation are still required.

### Existing methodological caveats

- The v0.2 Q95 score under fixed log-scale model parameters is effectively proportional to candidate vCDR; it is a baseline, not a novel validated uncertainty score.
- A same-dataset internal holdout is not an external Chákṣu evaluation.
- Repeatedly checking or redesigning methods using the holdout invalidates confirmatory conclusions.
- Internal permutation p-values are exploratory and not multiplicity-adjusted.
- PAPILA labels and demographic distributions do not automatically transfer to other hospitals or retinal cameras.
- A matching inventory is not cryptographic verification of every data file. Figshare MD5, when provided, is archive integrity, not proof of clinical annotation quality.
- The data owner/distributor defines permitted uses; the software's as-yet-unselected code license does not grant rights to redistribute dataset assets.

## Next real study milestone

1. Actually run the complete original archive and record downloadable provenance/checksums and exclusion counts.
2. Manually inspect the optic cup/disc contours on a small lawful sample, comparing vCDR with published helper conventions.
3. Preserve the first internal study output and interpret negative outcomes honestly.
4. Identify literature-supported reference-free baselines that are not functions of the same vCDR alone.
5. Define and lock the Chákṣu external study before viewing its independent-expert outcomes.
6. Publish a reproducible scientific methods report or research preprint **only when real results and scientific validity have been reviewed**.

## Primary sources

- Kovalyk et al. (2022), PAPILA: https://doi.org/10.1038/s41597-022-01388-1
- PAPILA official archive (Figshare v2): https://figshare.com/articles/dataset/PAPILA/14798004
- Chákṣu descriptor: https://doi.org/10.1038/s41597-023-01943-4
