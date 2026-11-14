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
