# Submission source and distribution audit

**Goal:** Verify the exact Git submission source and packaged execution from a genuinely isolated environment, then fix only reproduced defects.

**Baseline:** `35ee360b9edbca97b52b88b04a1e674783fcf909`, clean dedicated checkout; existing 390-test suite and prior experimental evidence remain historical facts.

**Approach:** Use an anonymous clean clone, build a wheel, install it non-editably in a new virtual environment without system site-packages, and exercise installed entry points outside the source directory. Separately inspect review lifecycle/integrity contracts and Git/segmentation/submission boundaries. Minimal bounded probes establish actual defects before any fix. Published evidence is aggregate-only; private datasets, models, logs and source image identifiers remain local.

## Checks

- [x] Compare remote heads and ancestry against main, confirm no omitted branch contribution, inspect tracked submission assets.
- [x] Build the clean-source distribution and run base-wheel CLI checks in an isolated environment, including optional-dependency behavior.
- [x] Install UI/dev dependencies separately, exercise public preparation/relaunch and source tests from the clean tree with explicit ML coverage scope.
- [x] Independently audit lifecycle and evaluation contracts, reproduce any findings with synthetic probes, add failing regression tests and minimal corrections.
- [x] Verify the completed implementation, frozen evidence/media and distribution; review the final diff independently and publish with matching CI.

No new model training policy, clinical claims, human-review attestations, event contributions, third-party redistribution or branch deletion is authorized by this audit. Existing design and submission scope are retained.

Measured verification: 404 development tests and 404 installed-wheel CPU tests; default two-seed/80-epoch synthetic demo and installed-package API path passed. Independent review approved. See the linked experiment audit for immutable receipts. GitHub integration follows only after required CI succeeds.
