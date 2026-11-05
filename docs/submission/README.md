# HyunOptic — local AI prediction review

**Current acceptance (2026-11-05):** [Actual browser and current-source audit](../experiments/2026-11-05-final-acceptance/README.md) — 442 tests passed in development and 442 against a non-editable CPU wheel. Actual browser import, inference, compare, hold/save-next, reload, keyboard save and independently verified ZIP download passed. A narrow-screen header defect was fixed. [New local 2:47 demonstration](media-20261105/README.md) is rendered and independently checked. [New public video](https://youtu.be/C5KE1KaHWGI) is published with verified English captions and public playback. Native 200% zoom, personal final review and actual Devpost entry remain pending.

Research software for inspecting optic disc/cup predictions, recording review decisions and exporting traceable evidence. A measurable result is not necessarily an anatomically correct result. This project is not a diagnostic or patient-care tool.

**Current public demonstration:** [YouTube](https://youtu.be/C5KE1KaHWGI), [verification](VIDEO_PUBLICATION_20261105.md), [MP4/captions/source](media-20261105/README.md). The materials below retain their historical version references.

**Historical submission materials:** [copy-ready fields](SUBMISSION.md), [public YouTube video](https://youtu.be/xbs47mX0d5g), [original MP4](media/hyunoptic-demo.mp4), [captions](media/hyunoptic-demo.en.srt), [transcript](media/transcript.md), [publication verification](VIDEO_PUBLICATION.md), and [specific personal review worksheet](HUMAN_REVIEW.md). The video is publicly uploaded; personal final review and the actual Devpost entry remain pending.

## Run the submitted code

Python 3.10+; Python 3.12 recommended. No hosted account or API key is needed. Downloading Python dependencies requires internet; inference and review data remain on the local computer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[ui,dev,ml]"
python -m pytest -q
streamlit run app.py
```

For an isolated, runnable demonstration without private datasets or weights, replace the last command with:

```powershell
python scripts/prepare_submission_demo.py --output demo_data/submission --launch
```

This generates synthetic data and actually trains two small CPU models (80 epochs each). It refuses an existing output folder. In Review Queue, select the two `synthetic_42` / `synthetic_43` bundles and import the generated `demo_data/submission/inputs` files. The unreadable example is intentional. See [model/data access](MODEL_AND_DATA_ACCESS.md) for relaunching the isolated workspace. Synthetic execution does not establish accuracy.

Open **Model Inference** to configure the models directory, then **Review Queue**. Two distinct verified local model bundles are required for a new review session. Their preparation and access restrictions are in [MODEL_AND_DATA_ACCESS.md](MODEL_AND_DATA_ACCESS.md). Without models, existing review records remain inspectable and the page shows an honest creation gate.

## Main task

1. Choose the primary and comparison model, identify modality, select local images and confirm local retention. Input supports RGB/grayscale PNG/JPEG/single-frame TIFF. The new queue limits each session to 500 images and 2GB total input, with 30MB/file and 25MP/image checks. Unsupported/failed cases remain visible.
2. Process a bounded step (default five images). Repeat the step to continue. Processing is synchronous on CPU; it is not a background service. Stop between steps. After a process interruption, use **Recover interrupted cases**, then continue.
3. Inspect the full image and model overlays. Bundle identity does not establish accuracy. Cropped optic-nerve-head inputs, other devices and other modalities remain unvalidated even when geometry is measurable. Priority shows execution failures, invalid measurements, and model disagreement. It is not calibrated confidence, disease risk, or a proven error detector.
4. Save **unreviewed**, **reviewed**, or **held**. A held result needs a reason. Other reasons need a private note. Review completion does not certify correctness. A stale tab cannot overwrite a newer decision.
5. Build the evidence ZIP, verify it and download it. Default export omits original images, masks, names, paths and private notes. Statuses, model provenance, measurements, reasons and hashes are retained. Hashes are not a guarantee of anonymity.
6. Explicit deletion removes the session's retained inputs, artifacts and review history. Export files already downloaded elsewhere cannot be recalled.

The local review database and copied inputs are under `.hyunoptic/review/` by default, or `HYUNOPTIC_WORKSPACE/review/`. Do not share this directory. It is not encrypted by the application. Use a trusted local account and device appropriate for your data permissions.

Verify a downloaded package independently:

```powershell
python -m hyunoptic.review.export path/to/evidence.zip
```

## Evidence and scope

- [Current readiness decision and remaining submission requirements](READINESS.md)
- [Devpost description draft](DEVPOST_DRAFT.md)
- [Rubric-to-evidence map](RUBRIC_EVIDENCE.md)
- [November 4 actual browser and cold-source audit](../experiments/2026-11-04-submission-readiness/README.md)
- [Final source/domain-guidance and browser verification: 390 tests](../experiments/2026-11-04-final-submission-polish/README.md)
- [Full November 4 real-data audit: 3,916 calls and severe cropped-ROI transfer failure](../experiments/2026-11-04-full-real-validation/README.md)
- [Baseline and contribution boundary](BASELINE.md)
- [Actual development dates](EVENT_CHANGES.md)
- [AI use and human verification](AI_DISCLOSURE.md)
- [Model and data access](MODEL_AND_DATA_ACCESS.md)
- [Validation record and limits](VALIDATION.md)
- [Three-minute demo script](DEMO.md)
- [Final publication checklist](CHECKLIST.md)
- [Prior real-data study results](../experiments/2026-10-25-university-transfer/README.md)

There is no new independent clinical study or review-efficiency result in this release. Existing transfer failures motivate the workflow but do not validate its ranking. Reference annotations do not enter prediction or priority. The current public video is linked above with its exact source/capture basis; the older video remains separately labeled as historical. No hosted app is provided or required for routine judging. The RIM-ONE DL queue endpoint equalled random expectation.

## Reproducible source boundary

A review session’s `software_commit` is its **creation-time** source identifier, not a per-prediction execution attestation. Resuming under different code does not record each execution commit. For a reproducible study, keep the application checkout and dependencies fixed for the session and preserve its source/environment alongside exported evidence. Installed wheels can report `unknown` for Git identity; package version and model identities remain separately recorded. This release does not claim cross-version execution attestation.
