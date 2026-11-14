# 1.0.4 release - November 14, 2026

Published beta first, then stable. No balance changes. Fixed duplicate legacy journal insertion,
journal confidence labels, and vertical alignment of Pressures/Risks rows.

- Beta 1.0.3-beta.5, item 3839275304: verified public at 06:10:25 UTC.
  Receipt: `workshop/upload_receipts/20261114T061025.742628Z_beta_update_verified_87802156.json`.
  Archive SHA256: `6c28e23d1fdd6fb5110f775b3f8f045bb76584ebb9b3e31ae624ddaf31cd14c4`.
- Stable 1.0.4, item 3831434383: verified public at 06:11:28 UTC.
  Receipt: `workshop/upload_receipts/20261114T061128.512707Z_stable_update_verified_15683ca1.json`.
  Archive SHA256: `a1358785c67b3fd54fbc0fa436e2f79656072d8505fb31d6d857f15dc3897003`.
- CMF 1.0.1 unchanged; regenerated patch bytes were identical. No upload needed.

Validation: 201 engine assertions in 19 isolated beta suites; 38 Python tests;
static script/localization checks; live native beta5 Finance shortcuts, notification
variants and row alignment. CMF beta4 shortcuts verified; its notification run did
not retain a completion marker. See MECHANICS_AUDIT.md for exact limits.

Stable was regenerated from the tested generators with version 1.0.4. Comparing
all file hashes to the frozen beta5 found only `.metadata/metadata.json` and the
beta-only `.metadata/built_against.txt`; the latter matches the root build version.
The initial strict single-file-difference assertion rejected this extra beta marker;
inspection established the distinction before uploading. Every gameplay/UI byte matches.
The immutable stable archive passed integrity/output verification. Both Steam uploads
returned success and the subsequent query verified public visibility and description hashes.
The stable description includes the user's earlier natural-language rewrite and links
to beta and CMF. No fixture/debug files were packaged.

## Follow-up Beta 1.0.4-beta.2

Published and verified public at 06:20:30 UTC, item 3839275304.
Receipt: `workshop/upload_receipts/20261114T062030.542158Z_beta_update_verified_c212b285.json`.
Archive SHA256: `1adcffce14ac96c1901137f18ac1ed40fff9c06895813ddc3f71b7a280748e50`.
Fixes an annual tie retaining a previous win/loss. Red: two engine assertions on beta5;
green: seven rivalry assertions on the final beta2, plus related Exchange/pledge regressions.
Stable remains 1.0.4; this follow-up is beta-only. No GUI structure or navigation changed.

At the user's request, both descriptions were shortened to current version plus plain
change bullets. Description-only updates verified at 06:21:25 (stable) and 06:21:26 (beta),
with unchanged content sizes. Receipts:
`20261114T062125.208476Z_stable_description_verified_2d13f41a.json` and
`20261114T062126.402501Z_beta_description_verified_731742d9.json` in the receipt directory.

## Follow-up Beta 1.0.4-beta.3

Published and verified public at 13:52:58 UTC, item 3839275304.
Receipt: `workshop/upload_receipts/20261114T135258.987066Z_beta_update_verified_ea4c134a.json`.
Archive SHA256: `f0a15d5b5f568a4d708073d3388a7105e427c7bf347a5277c9fb9ce858fdc7e4`.
Fixes bank tooltip values cached before the month's repayment and lending. Four red
engine assertions pass after moving the unchanged cache block alongside the bank chart.
Cash flow, 49 goods endings, and credit-cycle regression gates pass; 38 Python tests pass.
A separate frozen-beta2 save/reload check passed all recovery deadlines. No new live GUI
session is claimed. No economic formulas, GUI layout or navigation changed. Stable untouched.

## Follow-up Beta 1.0.4-beta.4

Published and verified public at 14:23:52 UTC, November 14, item 3839275304.
Receipt: `workshop/upload_receipts/20261114T142352.503370Z_beta_update_verified_48d4f209.json`.
Archive SHA256: `b0c66b01bbcb99f60e65a8d8246de86a126335014c516a85ffb9d8e10a4d2f82`.
Fixes burst losses overstated in the confidence breakdown when confidence hits zero.
The resulting confidence and balance are unchanged. Red/green accounting tests and
37 related regression assertions pass full log gates. Description lists the latest
version and concise change bullets. Stable and CMF are unchanged. Detailed evidence:
`tests/mechanics/verification_accounting_2026-11-14.json`; open checks remain in the audit.
