# Model, data and execution access

All project source code is in the repository. Public access to code does not establish permission to redistribute third-party datasets or derived weights. The repository's existing license status remains unchanged.

## Actual local research bundles

Four previous real-data model bundles exist on the developer's computer. They are not included in this repository. The new workflow does not download them and does not claim they are publicly available. No new model accuracy estimate follows from the review feature.

Researchers may prepare their own bundle with `hyunoptic-seg train --help` and the [existing runbook](../V10_RUNBOOK.md). Acquire data using the original provider's conditions, preserve patient-disjoint splits, and follow any use restrictions. CPU inference is supported; full training requires materially more time and resources than reviewing a prepared bundle.

Use two distinct bundles with a verified `bundle_manifest.json`, `config.json`, `split_manifest.json`, `history.json` and `weights.pt`. Unsupported model contracts are rejected. Changing the manifest/config invalidates inference cache identity. A failed or unavailable model does not erase prior review records.

## Reproducible synthetic demonstration

Synthetic fixtures are created by project code and contain no patient images. `hyunoptic-demo-data --help` and `hyunoptic-seg train --help` describe local preparation; `--allow-partial` is necessary for tiny synthetic cohorts. Train two small runs with different seeds. They are labeled synthetic and demonstrate the mechanism only. Tests perform this on tiny fixtures and fake predictions; fake predictions are never reported as real model performance.

From an activated environment at the repository root, using new output folders:

```powershell
hyunoptic-demo-data --output-dir demo_data/review --patients 10 --per-camera 2
hyunoptic-seg train --papila-root demo_data/review/PAPILA_SYNTHETIC --output models/review_demo_42 --image-size 64 --epochs 2 --batch-size 4 --base-channels 4 --depth 2 --seed 42 --device cpu --allow-partial
hyunoptic-seg train --papila-root demo_data/review/PAPILA_SYNTHETIC --output models/review_demo_43 --image-size 64 --epochs 2 --batch-size 4 --base-channels 4 --depth 2 --seed 43 --device cpu --allow-partial
streamlit run app.py
```

Select these two bundles in Review Queue and images from `demo_data/review/PAPILA_SYNTHETIC/FundusImages`. Tiny two-epoch models may return invalid geometry; show that failure as a recorded limitation rather than selecting examples to imply good accuracy. Training refuses an existing output folder to preserve frozen bundles.

## Public demonstration limits

Do not place PAPILA/Chákṣu/FairSeg/OLIVES/Iowa/Duke originals, masks, patient identifiers, or registration details in the submission. Screen recording rights and derived-weight redistribution must be checked separately. When rights are unresolved, use a clearly labeled synthetic demo and link the already published aggregate real-data evidence. This makes a runnable mechanics demonstration available without misrepresenting rights or transfer accuracy.

Windows/Python 3.12 is the local verification environment. Dependencies can be installed through the optional `ui,dev,ml` extras. CUDA is not required by the review runner. A CPU with sufficient RAM and local storage is needed; no unmeasured runtime guarantee is made.
