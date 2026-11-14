# Speculative Markets 1.0.6

Published November 14, 2026: stable **1.0.6** and beta **1.0.6-beta.1**.

- Fixed duplicate rival Exchange notifications.
- Fixed AI rescue chances not matching their intended rates.

Gameplay/UI files match the tested local 1.0.5-beta.3 candidate. Only metadata and artwork differ. Rivalry validation: 32 engine assertions and full log gates pass; AI rescue validation includes 30,000 actual rolls and eligibility/cash regressions. See `RIVAL_NOTIFICATION_FIX.md`, `AUDIT_BASELINE.md` and their machine-readable evidence. This release adds no new live UI or full-playset validation. All 46 Python tests and nine CMF checks pass.

CMF 1.0.1 rebuilt byte-identically. Morgenroete 1.0.0 rebuilt with identical metadata/gameplay/UI files; its release artwork is outside the generator. Neither patch overrides either changed scripted-effect file. Both retain their published content and received description-only updates for the new parent versions. No new Morgenroete runtime test was performed.

Immutable archive SHA-256:

- Stable: `c8fa797a5c9cc080de268ae52ca6ab5b0f6b7e264d9203d95e40606a0be20b4e`
- Beta: `8f32b2ab4c17d2b464912d27c5b9e49deba8c706ed53f0a290f088d701c6f401`

All four Steam updates returned success and were queried afterward. Public visibility and exact description hashes match; compatibility Required Items remain CMF and Morgenroete respectively. Receipts, hashes and comparison evidence: `tests/mechanics/verification_release_106.json`.
