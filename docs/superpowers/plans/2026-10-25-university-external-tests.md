# University external-data tests

User instruction: execute all previously identified university-data tests.

- [x] Acquire official Harvard FairSeg, Georgia Tech OLIVES, Duke DME; inspect Iowa request and Columbia availability.
- [x] Freeze protocol and four original model hashes before prediction. No retraining, model selection, annotation repair or changed postprocessing.
- [x] FairSeg: identify official split and class encoding; evaluate all official test cases at original resolution. Replicate grayscale to RGB without learned adaptation. Report Dice, conditional vCDR error, paired error and failed predictions separately.
- [x] OLIVES: evaluate all accessible fundus images for pipeline execution/geometry only. No invented disc/cup reference metrics; repeated visits are not independent patients.
- [x] Duke: audit OCT files and manual layer annotations. Current fundus OD/OC model is not an OCT layer model; report task incompatibility instead of meaningless scores.
- [x] Iowa/Columbia: inspect legitimate access route; do not submit identity/agreements or contact researchers without appropriate user authorization. Record concrete access blockers.
- [x] Verify aggregate arithmetic against private rows, unchanged model hashes, source checksums, and generate a readable local report. Raw images, identifiers, source annotations and model weights remain ignored/private. No LinkedIn publication.

Implementation uses standalone experiment scripts under reports/university_20261025, existing verified Predictor and measurement code; production code stays unchanged. Acquisition metadata and test outcomes remain local pending evidence verification.

Ruling before prediction: OLIVES full archive is 33.9 GB and the lighter official Hugging Face release exposes OCT rather than fundus. Use all complete fundus TIFFs in the first 128 MiB compressed stream of EACH original inner archive (TREX DME and PRIME). This is an archive-order convenience pilot, never full-cohort performance. Verify exact HTTP ranges, extracted entry CRC32 and individual SHA256; do not claim the full source ZIP MD5 was checked.

Ruling before prediction: FairSeg official publisher Hugging Face mirror supplies the official 2,000-case Test split and individual LFS SHA256 hashes. Use the pinned revision and verify all hashes; stop redundant slow full ZIP transfer after Duke finishes. No claim of full Zenodo ZIP checksum verification.

Completion: all acquired/testable sources processed under the recorded scope. Harvard official Test2000 x4 complete; OLIVES bounded30-file pilot x4 complete (full1268 not evaluated); Iowa all60 original stereo views x4 complete; Duke10 subject files integrity audit and supplied-boundary re-analysis complete. Columbia remains unavailable for model testing because no public patient-data download was verified. Six adapter tests and independent arithmetic/hash/privacy reviews passed. No production code or original checkpoint modified. Results: reports/university_20261025/evidence/index.html.
