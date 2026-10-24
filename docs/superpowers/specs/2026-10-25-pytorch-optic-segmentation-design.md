# HyunOptic PyTorch optic-disc/cup segmentation — design

**Date:** 2026-10-25  
**Status:** proposed design; no model training or real-data performance result is asserted here.  
**Decision:** extend HyunOptic with one reproducible retinal fundus-image model experiment. Do not start a separate glaucoma, retinal, or visual-cortex app.

## Intent and context

The immediate purpose is to demonstrate genuine, explainable PyTorch model-building work for a medical-imaging research application while extending HyunOptic's existing optic-disc/cup measurement and reader-disagreement work. This is a portfolio and research-software milestone, **not** a clinical product, glaucoma diagnostic study, or claim of qualification for a particular job.

Today the repository implements image/annotation ingestion, expert comparison, source and external **candidate-only measurement-QC** protocols, provenance checks, and synthetic software tests. It does **not** autonomously segment unseen images. Its README states that complete original PAPILA and Chákṣu scientific runs have not been verified. The new model must not silently replace, reuse the claimed endpoints of, or be presented as validation of those earlier QC scores.

The motivating a2z Radiology AI role emphasizes custom PyTorch training loops, experiments, reproducibility, and whole-study CT. A retinal 2-D segmentation project can show part of that capability and is strongly connected to the existing project; it **cannot** demonstrate 3-D CT or vision-language expertise. The application must state this gap plainly.

## Approaches considered

1. **Extend HyunOptic with a PyTorch retinal model — selected.** Reuses legitimate image/annotation workflows, patient grouping, provenance conventions, and the reader-disagreement question. The main tradeoff is that a fundus-image model is not a CT model.
2. **Build a separate 3-D CT model portfolio.** Closer to the hiring team's modality, but a substantially new data and compute pipeline with less connection to the user's current ophthalmology work. A small MedMNIST3D exercise alone would not substantiate whole-scan clinical research competence.
3. **Combine retina, optic nerve, and posterior visual cortex in one app.** Rejected for this milestone: incompatible modalities and endpoints would dilute the evidence of one complete model experiment.

## Goals

- Train and evaluate **one** transparent PyTorch baseline that predicts optic-disc and optic-cup masks from a fundus image **without expert masks as inference inputs**.
- Keep the current non-ML measurement and candidate-only QC workflows intact and independently labeled.
- Show experiment design, leakage controls, training behavior, held-out errors, cross-domain limitations, and a reproducible run path.
- Produce an honest portfolio artifact: code, protocol, environment, aggregate tables, failure analysis, and a concise account of what would be changed in the next training run.
- Preserve the existing research-only and no-clinical-use boundary.

## Non-goals and anti-goals

- No glaucoma diagnosis, progression forecasting, patient-specific recommendation, or clinical deployment.
- No visual-cortex or brain-imaging module in this milestone.
- No fabricated accuracy, synthetic-data result labeled as real-data validation, or performance claim before authorized original-data execution.
- No claim that expert 1 is objective disease truth; expert masks are annotation references.
- No tuning on an external test set followed by calling that same set independent confirmation.
- No raw fundus images, masks, clinical spreadsheets, case identifiers, or unreviewed model weights in the public repository.

## Data and access gate (must pass before training)

1. Review the current distributor's version, license, access terms, attribution, redistribution, and compute-location permissions for each dataset. Keep original archives outside Git and document the exact source URLs, versions, local SHA-256, and approval/usage notes. Do not assume the software repository's as-yet-unselected license grants data rights.
2. Obtain and run the existing full PAPILA source inventory and real-data compatibility checks. Verify patient IDs and both-eye pairing. Resolve parser or contour defects **before** fitting a model. A synthetic CI pass does not clear this gate.
3. Reuse the repository's patient-disjoint 60/20/20 PAPILA split manifest if its identity and integrity are verified. Both eyes of one patient stay in one partition. Freeze the split with a hash.
4. Record which outside datasets and outputs the project has already inspected. In particular, Chákṣu has an existing QC-evaluation protocol; do not describe a new model's Chákṣu result as untouched independent confirmation without documenting the prior exposure and locking this new protocol before any new external model evaluation.
5. If a suitable lawful, genuinely untouched external set cannot be secured, report only internal held-out results and a clearly **exploratory** cross-dataset analysis.

## Model and training design

- **Primary task:** three-class per-pixel output (background, optic disc outside cup, cup) from color fundus images. The inference API accepts an image only.
- **First baseline:** a modest U-Net-style encoder/decoder implemented in PyTorch, with an explicit training loop, optimizer/scheduler, loss, validation, checkpoint selection, and inference path. A published baseline architecture is an implementation starting point, not a novelty claim.
- Use PAPILA expert-1 disc/cup annotations as training targets. Keep expert-2 labels out of training and checkpoint selection; use them only in predeclared reader-sensitivity reporting. Do not let derived expert-2 features leak through preprocessing, crops, or metadata.
- Define a deterministic image-resize/crop and mask-rasterization convention once. Any optic-disc localization/cropping at inference must be image-only or use a separately trained image-only component; never use a reference mask to find the crop for test inference.
- Predeclare augmentations that are plausible for fundus acquisition, together with interpolation rules for image versus mask. Record seed, package versions, device, epoch count, batch size, optimizer settings, model-selection rule, and training-set class balance.
- Save best checkpoint by **validation** segmentation Dice under a fixed rule; evaluate the internal holdout once after selection. Preserve the final configuration and checkpoint/hash. If changes follow holdout inspection, label later runs exploratory and obtain a new untouched test for confirmatory claims.
- Implement a tiny CPU/synthetic fixture for CI and a separate full-data run that is explicitly opt-in. Synthetic tests validate mechanics only.

## Predeclared evaluation

**Primary internal endpoint:** per-image optic-cup Dice on patient-disjoint PAPILA holdout against expert 1, with disc Dice alongside it. Report medians and distributions, not just one aggregate score. Undefined or failed predictions are counted and explained, not dropped silently.

**Measurement consequence:** derive vertical cup-to-disc ratio (vCDR) from predicted masks using the repository's existing pixel convention; report absolute vCDR error and the fraction exceeding a predeclared *research-only* 0.10 absolute-vCDR-error threshold. Do not imply diagnostic sensitivity or disease risk.

**Human-reference sensitivity:** compare the same frozen predictions separately with expert 1 and expert 2; report expert-1-versus-expert-2 agreement as context, not as a universal performance ceiling. No majority mask is silently treated as clinical truth.

**Robustness:** stratify by verified acquisition/device information when available and adequately sized; assess degradation on one preselected external dataset under its actual annotation definitions. Dataset, cameras, mask conventions, and exclusions must be recorded before opening external labels. If labels differ materially, compare only compatible endpoints and say so.

**Uncertainty and failures:** retain all evaluable cases and summarize the worst errors with privacy-safe aggregate categories (poor image quality, boundary ambiguity, crop failure, device shift, mask geometry). Any proposed confidence score must have an explicit target and calibration test; softmax confidence is not automatically calibrated uncertainty.

**Statistical unit:** PAPILA has paired eyes, so use patient-level grouping for bootstrap intervals or paired comparisons. Do not use an independent-image bootstrap when patient linkage is known. Do not invent patient clusters in Chákṣu where linkage is unverified. Report negative and null results.

## Architecture and integration boundaries

- Add a self-contained model-training package/CLI under the HyunOptic repository; keep raw data paths local and configurable. Do not make Streamlit import PyTorch or download checkpoints by default.
- Separate: dataset adapter and manifest; preprocessing; model/loss; trainer; evaluator; aggregate report; optional UI inference viewer.
- Existing expert measurement functions should compute vCDR from both human and predicted masks to avoid divergent definitions, with tests for geometry and resize behavior.
- The current app may display a predicted overlay only after a real checkpoint is locally supplied. It must show model version, source, research-only status, and whether the displayed example is synthetic or original-data-derived. Do not present demo graphics as measured performance.
- Public repository artifacts: code, configuration, synthetic fixtures, instructions, aggregated results only after data/ethics/license review. Keep per-image reports and original archives local by default.

## Implementation and evidence milestones

1. **Baseline integrity:** existing tests pass; real PAPILA inventory and parser compatibility are verified; immutable split/manifest and source hashes are recorded. If real data is unavailable, stop at software scaffolding and say model training has not occurred.
2. **PyTorch pipeline:** synthetic fixture trains/overfits a few cases; inference is image-only; mask alignment and patient split/leakage tests pass; full experiment configuration is captured.
3. **Real source experiment:** train on PAPILA development, select on validation, then run the frozen internal holdout once. Publish exact sample counts, all predeclared metrics, failure counts, and compute details.
4. **External analysis:** verify and document a lawful external set; freeze mapping and model before test. Treat previously exposed Chákṣu as exploratory unless an independent untouched confirmation is established.
5. **Portfolio review:** independent code/evidence review checks leakage, claims, reproducibility, data rights, and whether another researcher can rerun from lawfully obtained originals. Only then update README, project profile, and application materials.

A milestone is not reached by adding a dashboard or passing synthetic tests alone. If real-data training is incomplete, the honest portfolio description is “PyTorch training/evaluation pipeline implemented; real-data results pending.”

## Application narrative and limits

The project should enable a concrete answer to the hiring question, “Tell us about a model you built, and what you would change if you trained it again.” That answer must name the actual dataset and split, architecture and training decision, observed held-out failure mode, and a justified next experiment. It must not assert CT, distributed training, clinical validation, or superiority unless separately demonstrated. A strong negative or mixed result with rigorous failure analysis is acceptable evidence of research judgment.

## Open decisions for implementation planning

- Compute budget and available GPU determine image resolution, batch size, and whether a second architecture is feasible.
- Confirm original PAPILA and candidate external archive access, terms, and integrity before choosing the full-run environment.
- Decide whether the optional UI viewer is needed only after the trained model and evaluator are trustworthy.
- Seek an independent clinical/vision-science reviewer before making clinical-facing interpretations.

## References

- Existing HyunOptic protocol and caveats: [README](../../../README.md), [v0.7 external protocol](../../../docs/V07_EXTERNAL_VALIDATION_PROTOCOL.md), [rc3 source holdout](../../../docs/V10_RC3_SOURCE_MASK_HOLDOUT.md). (Paths are relative to this design document.)
- PAPILA official dataset: https://figshare.com/articles/dataset/PAPILA/14798004
- REFUGE challenge task definitions: https://refuge.grand-challenge.org/Details/
- a2z role: https://a2zradiology.ai/careers/ml-research-engineer-scientist-remote-international/
