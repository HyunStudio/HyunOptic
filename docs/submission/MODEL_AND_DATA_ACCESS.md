# Model, data and execution access

All project source code is in the repository. Public access to code does not establish permission to redistribute third-party datasets or derived weights. The repository's existing license status remains unchanged.

## Actual local research bundles

Four previous real-data model bundles exist on the developer's computer. They are not included in this repository. The new workflow does not download them and does not claim they are publicly available. No new model accuracy estimate follows from the review feature.

Researchers may prepare their own bundle with `hyunoptic-seg train --help` and the [existing runbook](../V10_RUNBOOK.md). Acquire data using the original provider's conditions, preserve patient-disjoint splits, and follow any use restrictions. CPU inference is supported; full training requires materially more time and resources than reviewing a prepared bundle.

Use two distinct bundles with a verified `bundle_manifest.json`, `config.json`, `split_manifest.json`, `history.json` and `weights.pt`. Unsupported model contracts are rejected. Changing the manifest/config invalidates inference cache identity. A failed or unavailable model does not erase prior review records.

Bundle verification checks artifact integrity and supported contracts; it does not establish anatomical accuracy or validity in a new domain. Whole-fundus training does not validate cropped optic-nerve-head images, new cameras/sites, SLO or OCT. In the [full real-data audit](../experiments/2026-11-04-full-real-validation/README.md), all 174 RIM-ONE DL hospital-Test images were evaluated: baseline/photometric Cup Dice was 0.0018/0.0065, with 160/174 and 132/174 invalid geometries. Only two images were commonly measurable, insufficient for a superiority claim; the saturated queue endpoint showed no triage benefit. These are material model limits.

## Reproducible synthetic demonstration

Synthetic fixtures are created by project code and contain no patient images. The preparation script trains two actual models and creates an isolated workspace. The CPU integration test also trains and verifies real bundles; separate test adapters remain explicitly synthetic. Neither type is reported as clinical performance.

From an activated environment at the repository root, using new output folders:

```powershell
python scripts/prepare_submission_demo.py --output demo_data/submission --launch
```

Defaults: ten synthetic patients, 512×384 original images, model input 64×64, 80 epochs, base channels 8, depth 2, learning rate 0.003, seeds 42/43, CPU with up to four threads, partial-data declaration. The output contains `models/synthetic_42`, `models/synthetic_43`, fixed first-four images plus an unreadable input under `inputs`, and `workspace/workspace.json`. Existing output folders are refused. The launcher sets the isolated workspace only for the child app and does not change an existing workspace setting.

To relaunch after preparation, without retraining:

```powershell
$env:HYUNOPTIC_WORKSPACE = (Resolve-Path demo_data/submission/workspace).Path
python -m streamlit run app.py --server.address 127.0.0.1
```

Select the two synthetic bundles in Review Queue and files under `demo_data/submission/inputs`. The older two-epoch recipe actually produced four invalid-geometry outputs for seed 43 on the fixed four examples; the improved recipe produced measurable outputs for both models on those same examples. This does not establish anatomical accuracy. Preserve any failures rather than selecting examples to imply good performance. [Preparation and execution audit](../experiments/2026-11-04-submission-readiness/README.md).

## Public demonstration limits

Do not place PAPILA/Chákṣu/RIM-ONE DL/FairSeg/OLIVES/Iowa/Duke originals, masks, patient identifiers, or registration details in the submission. Screen recording rights and derived-weight redistribution must be checked separately. When rights are unresolved, use a clearly labeled synthetic demo and link the already published aggregate real-data evidence. This makes a runnable mechanics demonstration available without misrepresenting rights or transfer accuracy.

Windows/Python 3.12 is the local verification environment. Dependencies can be installed through the optional `ui,dev,ml` extras. CUDA is not required by the review runner. A CPU with sufficient RAM and local storage is needed; no unmeasured runtime guarantee is made.
