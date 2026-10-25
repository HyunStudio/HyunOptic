# Camera-Robust Photometric Follow-Up Plan

> **For agentic workers:** Use superpowers:executing-plans and test-driven-development for the optional training policy; independently review before merge.

**Goal:** Address the diagnosed external color/exposure mismatch with one optional training augmentation policy and execute exactly one new 40-epoch run.

**Evidence and hypothesis:** Seed-43 external failures are 16 empty-cup predictions (6 already empty before disc component filtering, 10 removed by disc filtering). Selected diagnostic cases show that keeping only the largest cup component can worsen good cases and does not solve contiguous cup overextension. Image-only samples (32 development, 16/camera external) show mean red/green ratios 2.903 in PAPILA, 1.512 Bosch, 2.390 Forus and 1.359 Remidio. These selected/sampled diagnostics suggest photometric domain mismatch, not proof of causality or performance estimates. Do not fabricate cup masks or repair original references.

**Design:** Keep the existing `baseline_v1` policy byte-for-byte compatible in operations, RNG draws and config output. Add explicit opt-in `camera_robust_v2`: brightness and contrast factors uniform 0.7–1.3, independent RGB gains 0.65–1.35 and gamma 0.7–1.5, applied before fixed normalization. Retain black background/padding. Preserve legacy main-generator draws for geometry, shuffle and the two brightness/contrast variates; use a separate generator seeded training_seed+1000003 for extra RGB/gamma draws. Targets receive only the existing spatial transforms. Record the new policy/settings in the immutable bundle config and expose the policy in the training CLI.

**Alternatives:** A cup-component-only postprocess changes vCDR in opposite directions across diagnostic groups and leaves major errors. Class-weighted loss could promote cup predictions but does not directly address the observed overextended cups and color shift. Test the photometric policy alone; leave loss, postprocessing, inference and geometry unchanged.

**Fixed experiment:** Same real PAPILA inventory, source and patient split hash; training seed **43** to challenge the known failure-prone baseline, split seed 42; 384px/base16/depth4, 40 epochs, batch4, AdamW lr .001/weight decay .0001/cosine. Expert1 development targets only; validation selects checkpoint before evaluation. Exactly one new model, with no setting changes or additional runs in response to outcomes.

**Evaluation:** Internal98 and external336 using existing evaluators, with follow-up exploratory flags. Preserve the same 25 reference failures and all model failures/metric denominators. Compare to the original seed43 run, also show the original three-seed range. Report paired vCDR errors on the common measurable cases and a separately labeled descriptive research penalty (invalid prediction=1) on all reference-valid cases, so changes in vCDR coverage cannot masquerade as improvement. This penalty is not measured MAE or clinical utility.

**Predeclared decision:** Promising external result requires fewer than16 model-geometry failures and lower conditional vCDR MAE than .25531009, with cup Dice no more than .02 below .57487019. Inspect internal deterioration (disc/cup drop >.02 or >6 failures) as a tradeoff, not a reason to retune. Report unfavorable outcomes unchanged. All follow-up results remain exploratory; no causal, clinical or untouched confirmation claim.

## Tasks

- [x] Add failing tests for deterministic bounded photometric transforms, preserved black pixels/targets/main RNG, default backward compatibility, invalid policy rejection and config/CLI policy provenance.
- [x] Implement optional policy, run targeted tests then full suite, and independently review the implementation. Preserve all existing bundles/results.
- [ ] Save a timestamped protocol before the one real run; train once, freeze/hash checkpoint, then evaluate once internally/externally.
- [ ] Independently recompute aggregate and paired/penalized metrics; render plots; verify public hashes, privacy and reproduction instructions.
- [ ] Publish the complete result, including failures/tradeoffs, and merge only after review/CI pass.
