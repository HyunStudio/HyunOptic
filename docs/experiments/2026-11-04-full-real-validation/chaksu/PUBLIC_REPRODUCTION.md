# Chákṣu reproduction and original-protocol scope

Use authorized local `data/Chaksu_Test.zip`, the two exact private model bundles identified in `provenance_public_safe.json`, and the recorded Python environment. The weights, raw archive, individual rows and prediction PNGs are not public assets.

`public_protocol_rules.json` is a reviewed excerpt of the original frozen protocol, with the raw layout omitted. Its `original_protocol_sha256` identifies the complete private original; this excerpt is not claimed to be byte-identical. Historical timestamped analysis addenda are published separately and retain their original dates.

Copy the three own-authored files `harness.py`, `verify_and_supplement.py` and `historical_commoncase_check.py` into a **new empty ignored output folder**, for example `reports/chaksu_fresh`. Do not run the harness in this documentation directory: its own parent directory becomes the private output directory. Do not copy an existing `protocol.json`; the harness creates a new protocol and refuses an existing one.

The supplementary helper compares reader ASTs with Git revision `9cd674e`, so that ancestor must be available locally (a shallow checkout containing only a newer revision is insufficient). Run from the repository root:

```powershell
New-Item -ItemType Directory -Force -Path reports/chaksu_fresh | Out-Null
Copy-Item docs/experiments/2026-11-04-full-real-validation/chaksu/harness.py reports/chaksu_fresh/
Copy-Item docs/experiments/2026-11-04-full-real-validation/chaksu/verify_and_supplement.py reports/chaksu_fresh/
Copy-Item docs/experiments/2026-11-04-full-real-validation/chaksu/historical_commoncase_check.py reports/chaksu_fresh/
.venv/Scripts/python.exe reports/chaksu_fresh/harness.py
```

Before running `verify_and_supplement.py`, create a **new, accurately dated** `technical_event_posthoc_addendum.json` in that private folder, declaring the analysis timing and the research-event thresholds/budgets shown in the historical template. This file's hash is required by the helper. Do not copy a historical timestamp and describe it as a new preregistration. A new rerun after these results are known is exploratory; neither changing a timestamp nor freezing a recipe restores untouched confirmation.

The original analysis added all-returned-mask Dice before reading references and added technical-error queue outcomes after partial reference inspection. Those timing distinctions belong to this original run. A new rerun must record its own timing. Preserve the original successful-only Dice and vCDR unknown-outcome analysis separately.

Run `verify_and_supplement.py` after completing the new inference/reference phases. The optional `historical_commoncase_check.py` additionally requires the preserved October private evaluation rows; it is unavailable from a public source-only checkout. The published fresh verifier supports the original saved private layout and does not produce new predictions.

All newly generated layouts, image IDs, rows, masks and queue orders remain private. Only independently checked aggregate reports may be copied back. The enclosing experiment manifest verifies the public files; no individual source assets are included.
