# HyunOptic v1.0.0 — one-command research runbook

> Research/education only. NOT for clinical use, glaucoma diagnosis or patient care.
> Completing this runbook produces a **consistent evidence package**, not proof of
> scientific validity or clinical accuracy.

v1.0.0 is the first non-candidate software release. It adds no new scoring method.
It packages the frozen protocol from v0.7–rc3 behind one command and adds an
aggregate-only HTML report and display accessibility options.

## 1. What `hyunoptic-pipeline` runs

All steps call the same functions as the individual commands and write into one
**new** output folder (an existing non-empty folder is refused).

| # | Step | Same as | Output |
|---|---|---|---|
| 1 | Archive identity (only when ZIPs are given) | `hyunoptic-verify-sources` | `sources.json` |
| 2 | PAPILA inventory (refuses incomplete data unless `--allow-partial`) | `hyunoptic-inventory` | `inventory.json` *(local only)* |
| 3 | Freeze exp1-only mask scaler on development patients | `hyunoptic-external freeze` | `model_lock.json` |
| 4 | Same frozen score on PAPILA validation + holdout patients | `hyunoptic-source-check` | `source_holdout/` |
| 5 | Chákṣu Test all-five-reader preflight | `hyunoptic-chaksu-audit` | `chaksu_audit/` |
| 6 | Chákṣu Test external analysis | `hyunoptic-external test` | `external/` |
| 7 | Evidence-package gate (needs all six artifacts) | `hyunoptic-evidence` | `evidence_review.json` |
| 8 | Aggregate-only HTML report | `hyunoptic-report` | `report.html` |

Each step is recorded in `pipeline_manifest.json` as:

- `passed` — ran and its output is complete/verified;
- `incomplete` — ran, but output is partial or unverified (e.g. synthetic fixture, archive checksum mismatch, failed gate checks);
- `failed` — raised an error (message recorded);
- `skipped` — input not supplied or an earlier step failed.

The manifest also stores SHA-256 for every shareable output and lists files that
must stay local (`inventory.json` and every `*private*` file contain per-image rows).

Exit codes: `0` all executed steps finished; `1` a step failed; `2` with
`--strict`, the evidence gate did not run or was not consistent.

## 2. Windows PowerShell — full run

```powershell
git pull
python -m pip install -e ".[ui,dev]"

# PAPILA: download from the official Figshare article (review terms first)
hyunoptic-download --archive "D:\datasets\PAPILA.zip" --extract-to "D:\datasets\PAPILA" --accept-dataset-terms

# Chákṣu: obtain the original Test.zip manually from its Figshare article.

hyunoptic-pipeline `
  --papila-root "D:\datasets\PAPILA" `
  --papila-zip "D:\datasets\PAPILA.zip" `
  --chaksu-test-zip "D:\datasets\Chaksu\Test.zip" `
  --output-dir "reports\v1" --verify-pixels --strict
```

If the extracted folder nests the data (e.g. `D:\datasets\PAPILA\PAPILA_DBv1`),
point `--papila-root` at the folder that directly contains `FundusImages\`.

PAPILA-only run (steps 5–7 are skipped):

```powershell
hyunoptic-pipeline --papila-root "D:\datasets\PAPILA" --output-dir "reports\v1_papila"
```

Open `reports\v1\report.html` in any browser. It works offline and loads no external resources.

## 3. GitHub Actions (PAPILA only)

The manual **PAPILA research run** workflow (Actions tab → *Run workflow* → `AGREE`)
downloads PAPILA on an ephemeral runner, runs the v0.5/v0.6 studies and the PAPILA
part of `hyunoptic-pipeline`, and uploads only aggregate files
(`report.html`, `pipeline_manifest.json`, `source_aggregate.json`, summaries) for 7 days.
Chákṣu is not downloaded automatically; run the external part locally.

## 4. Rebuilding a report from existing outputs

```powershell
hyunoptic-report --papila-inventory reports\rc3\inventory.json `
  --source-aggregate reports\rc3\source_holdout\source_aggregate.json `
  --external-aggregate reports\rc3\external\external_aggregate.json `
  --output reports\rc3\report.html
```

Any subset of inputs is accepted; missing sections are named in the report rather than hidden.

## 5. Report design (plan item F08) and accessibility (F09)

- Reads aggregate JSON only and strips keys that may hold identifiers (`failures`, `cases`, `rows`, file-name lists) before rendering. All text is HTML-escaped.
- Shows a prominent warning whenever any input is partial or unverified.
- PASS/FAIL are written as words, not only colours; tables use captions and header scopes; base text is 16 px and follows the system light/dark preference; narrow screens scroll tables horizontally.
- Streamlit viewer: *Display & accessibility* sidebar with text size (Standard/Large/Extra large), high-contrast yellow/blue contours, dashed cup vs solid disc outline, and line thickness. The image caption always states colour **and** line style.

## 6. Using the v1.1 research workspace app

```powershell
streamlit run app.py
```

1. **Datasets** → *Edit* on each card: set the extracted PAPILA folder (optionally `PAPILA.zip`) and the original Chákṣu `Test.zip`. Run the **Integrity Check** for each.
2. **Batch Analysis** → *Start analysis*. This calls `hyunoptic-pipeline` and writes a new folder under `reports/`; the run becomes the active run in the sidebar. Leave *Allow partial data* off for the real datasets.
3. Review **Reliability Analysis**, **Source Holdout** and **External Validation**, run **Evidence Check**, then export from **Reports**.

Result pages read only the selected run folder. Per-image files are used locally for curves and box plots but are never exported. To try the app without real data, run `hyunoptic-demo-data` and point the Datasets page at its two outputs; every result will be marked partial.

## 7. What remains for the researcher

1. Run the full chain on the original PAPILA and Chákṣu archives and keep the output folder unchanged.
2. Review `report.html`, the limitations, and the evidence gate. Report null or negative results as they are (plan §8 Stop/Pivot rule).
3. Choose a software license (still unselected) before public reuse.
4. Do not publish `inventory.json` or any `*private*` file without dataset-license and privacy review.

---

## 8. Experimental PyTorch segmentation

Design: [PyTorch optic segmentation design](superpowers/specs/2026-10-25-pytorch-optic-segmentation-design.md).
Training, splitting and evaluation are **CLI-only and offline**; the app only reads verified bundles and reports.

```powershell
python -m pip install -e ".[ui,dev,ml]"     # or install a CPU/GPU torch build first, then this
# 1. Train on PAPILA development patients (expert 1), select the checkpoint on validation patients
hyunoptic-seg train --papila-root "D:\datasets\PAPILA" --output models\unet_run1 --image-size 384 --epochs 40
# 2. Evaluate the untouched internal holdout ONCE (a repeat is refused unless marked exploratory)
hyunoptic-seg evaluate --bundle models\unet_run1 --papila-root "D:\datasets\PAPILA"
# 3. Optional exploratory external analysis (Chákṣu was already inspected by the QC protocol)
hyunoptic-seg evaluate --bundle models\unet_run1 --chaksu-test-zip "D:\datasets\Chaksu\Test.zip"
# Check a bundle without loading PyTorch
hyunoptic-seg verify --bundle models\unet_run1
```

| Design requirement | Implementation |
|---|---|
| Image-only inference | `seg.inference.Predictor.predict(image)` takes a PIL image only; whole-image letterbox, no optic-disc crop |
| Patient-disjoint split, frozen with a hash | `seg.data.build_split_manifest` reuses `study.patient_splits` (same 60/20/20 as the QC study); `split_manifest.json` + SHA-256 in the bundle |
| Expert 2 never in training/selection | Targets read `exp1` only (tested by recording every contour read); expert 2 is loaded by the evaluator after prediction |
| Explicit training loop | `seg.train`: U-Net (`unet_small_v1`), CE + mean soft Dice (disc, rim, cup), AdamW, cosine schedule, predeclared augmentations, seeded |
| Checkpoint by validation only | Best mean per-image (disc + cup Dice)/2 on validation; holdout untouched until `evaluate` |
| Holdout once | `evaluation/papila_holdout/` is write-once; `--exploratory-rerun` writes a separately labelled folder |
| Shared vCDR definition | Predicted masks go through `measure.measure_masks`, like expert masks |
| Safe weights | `weights.pt` is a tensor `state_dict` loaded with `torch.load(weights_only=True)` after SHA-256 checks of every bundle file |
| Patient-grouped intervals, failures counted | `evaluation.patient_cluster_bootstrap_mean` for PAPILA; failure categories reported; no intervals for Chákṣu |
| Aggregate vs private outputs | `model_eval_aggregate.json` (no identifiers) and `model_eval_private_cases.json` (local) |

**In the app:** *Model Inference* shows the empty state until PyTorch and a verified bundle exist, rejects tampered bundles visibly, predicts from the image only, labels whether the image was in this model's development/validation/holdout split, keeps the expert comparison in a separate panel that is off by default, and disables case-level export until the risk is acknowledged. *Model Experiment* shows only evaluator reports and the bundle's training history; the internal holdout is listed first and Chákṣu is always badged exploratory. Bundles trained on synthetic or partial data carry a red or amber banner everywhere.

**Status:** pipeline implemented, with synthetic-fixture CI and an [executed real-data segmentation baseline](experiments/2026-10-25-real-data-baseline/README.md) on PAPILA plus exploratory Chákṣu evaluation. The separate candidate-QC study and clinical validation remain uncompleted; see the experiment report for denominators, failures and limitations.

Training optionally accepts `--photometric-policy camera_robust_v2`: stronger brightness/contrast, per-channel gains and gamma with separate extra RNG and black-pixel preservation. Default `baseline_v1` and inference/postprocessing remain unchanged. The [single-run photometric follow-up](experiments/2026-10-25-photometric-remediation/README.md) has mixed outcomes and did not meet its full prespecified rule; this is an experimental option, not a promoted replacement.

### Review safeguards

Model Experiment rejects reports whose run ID, weights hash, data status or internal source/split hashes differ from the selected bundle. Synthetic and partial model reports must remain exploratory. Tiny nonempty prediction masks remain drawable; their outlines do not change measurement masks.

Dataset verification cards show a historic check only while its input paths and file metadata match the checked snapshot. Changing a location or ordinary file contents invalidates the displayed status; older history without a snapshot must be checked again. This UI snapshot is not a content checksum: rerun integrity verification before relying on data identity, including after any change that preserves file size and timestamps.

The test workflow covers Linux Python 3.10/3.12 and Windows Python 3.12, with a separate CPU PyTorch synthetic-data job. Passing these tests demonstrates software behavior, not real-data model performance.

## 한국어 요약

- **v1.0.0**은 새 점수 방법을 추가하지 않고, v0.7–rc3에서 고정한 프로토콜 전체를 `hyunoptic-pipeline` 한 번으로 실행하도록 묶은 첫 정식 소프트웨어 릴리스입니다.
- 실행 순서: 아카이브 해시 → PAPILA 인벤토리 → 개발 환자만으로 모델 동결 → PAPILA 검증/홀드아웃 → Chákṣu 5인 판독 사전검사 → 외부 테스트 → 증거 게이트 → **집계 전용 HTML 보고서**.
- 각 단계는 `passed / incomplete / failed / skipped`로 `pipeline_manifest.json`에 기록됩니다. 합성·부분 데이터는 절대 `passed`로 표시되지 않습니다.
- Streamlit 뷰어에 글자 크기, 고대비 색상, 점선 cup 윤곽, 선 굵기 설정이 추가되었습니다(기획서 F09).
- **아직 남은 일:** 실제 PAPILA·Chákṣu 원본으로 전체 실행, 결과(음성 결과 포함) 검토, 소프트웨어 라이선스 선택. 이 저장소는 실제 데이터 결과를 주장하지 않습니다.
