# Seed Stability Experiment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for this local experiment. Steps use checkbox syntax for tracking.

**Goal:** Execute the user's selected two additional training seeds and report all three runs' stability without changing the baseline.

**Architecture:** Invoke the existing training and evaluation APIs, with new immutable local bundles for training seeds 43 and 44 and the original split seed 42. Freeze both new validation-selected checkpoints before comparing follow-up holdout/external metrics. Export only aggregate evidence and keep the original baseline unchanged.

**Tech Stack:** Existing PyTorch U-Net, CUDA training, CPU evaluation, Python/NumPy/Matplotlib.

**Spec:** User selected “다른 seed 2회로 안정성 확인”; the fixed baseline configuration is `docs/experiments/2026-10-25-real-data-baseline/config.json`.

## Global Constraints

- Change only training seed to 43/44; split seed stays 42, image size 384, epochs 40, batch 4, AdamW lr 0.001/weight decay 0.0001, existing augmentation and cosine schedule unchanged.
- Use real PAPILA, same patient-disjoint splits and source-content hash; train on development expert 1 only and select using validation only.
- Preserve seed 42 bundle/results. No seed selection based on internal holdout or Chákṣu; publish every run, all failures and all metric denominators.
- Follow-up internal evaluations are exploratory because the cohort was already inspected; external evaluations remain exploratory. No claim of three independent clinical cohorts.
- Local data, identifiers, per-case rows, split manifests and weights remain excluded from Git.
- Summarize mean, sample SD (ddof=1), min/max over three run-level metrics. This describes training-seed variation on one fixed split, not a patient-population confidence interval.

## Review Focus

- Training seed must not accidentally change patient split; verify split hash against baseline.
- Checkpoint must be validation-selected before evaluation; verify selected epoch is validation argmax.
- Invalid predictions must remain in available Dice metrics and missing vCDR denominators must stay explicit.
- Distinguish genuine reference-mask failures from model failures; no source-mask repair.
- Public manifest hashes must match committed bytes, with no case identifiers or absolute user paths.

## Execution

- [ ] Record timestamped protocol, code/source hashes and baseline identity before training.
- [ ] Train seed 43 and seed 44 in new bundles; verify config equality except seed, full data, same source/split hashes, 40 finite epochs and validation selection.
- [ ] Freeze both checkpoints, then evaluate each once internally and externally, labeling follow-up analyses exploratory. Retain progress and private rows locally.
- [ ] Recompute aggregates from private rows without rerunning inference; compare seed 42/43/44 and produce charts, per-run CSV and descriptive mean/SD/range.
- [ ] Review public evidence independently, verify hashes/links/privacy and publish follow-up PR. No product-code changes are planned.

## Verification

Existing training/evaluation APIs are unchanged. Use runtime assertions for bundle/config/split provenance, independent NumPy arithmetic against private case rows, checks of all seeds/report flags/counts, and public manifest verification. Do not add tests that merely mirror this reversible experiment orchestration. Retain the existing CUDA nondeterminism limitation.
