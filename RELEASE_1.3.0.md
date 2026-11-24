# 1.3.0 release state

Published 2026-11-24 20:16 to 20:17 UTC, public, every upload verified by Steam query. Contains all of 1.2.2, which was never
published (`RELEASE_1.2.2.md`). Receipts are in `workshop/upload_receipts/`.

| Item | Version | Archive SHA256 | Receipt |
|---|---|---|---|
| Beta 3839275304 | 1.3.0-beta.1 | dd3b341f9955262d4106a1e9e767e821ba735d094db0f8b2ff6012965a217394 | `20261124T201658.223846Z_beta_update_verified_b222b8da` |
| Stable 3831434383 | 1.3.0 | 9db534cafa2431ad702d5d7cdcfc00ce13b2d0036539d79f0f4a2431c1b0fd06 | `20261124T201702.565511Z_stable_update_verified_fef6b9f9` |
| Morgenroete 3839705018 | 1.3.0 | 760f8b163c6f352f40e16fc5d958e9c47e956c5dbfa1bba27da83bec2e23264f | `20261124T201708.563656Z_morgenroete_update_verified_bbd5fad1` |
| TechRes 3841713072 | 1.2.0 | 5b64009147dc8089bbe4b74fa19b2d5404d58037ba3a5728c8d976bdbe533ed9 | `20261124T201714.811219Z_techres_update_verified_564b22a3` |
| BPM 3844392018 | 1.1.0 | 395278e5dbcb6e68f78e1e46f83a7a55d3c0872968f0ec98615513eb1c40548e | `20261124T201720.857682Z_bpm_update_verified_f38e4da5` |
| CMF 3839275348 | 1.0.4, description only | unchanged | `20261124T201722.136688Z_cmf_update_verified_dfa7daa0` |

The Beta archive is in `beta/release_130/releases/`; the others are in `releases/`. Patches were built against `mod/` 1.3.0 into
`runs/<patch>/v130`. CMF rebuilt against 1.3.0 is byte-identical to 1.0.4. TechRes is 12 files smaller: building-scope throughput
modifiers mean it no longer declares T&R's missing per-building modifier types. `tools/package_release.py` now knows BPM.

## Balance, 1.2.1 -> 1.3.0
- `tools/tuning.json`: LEV_PANIC_SPAN 50 -> 55, LEV_CRUNCH_FADE 0.3 -> 0.35, LEV_BAILOUT_CUT 0.3 -> 0.25, LEV_INCOME_FLOOR
  unset (0.01) -> 0.009, LEV_CRUNCH_BUILD unset -> 0.05, PANIC_BUILD unset -> -0.3, LEV_RECORD_BUILD unset -> 0.0167,
  LEV_RECORD_GAIN unset -> 0.01, LEV_RECORD_LOSS unset -> 0.3, BB_STEP (boom construction per step) -> 0.15 (10/20% -> 15/30%).
- `cycle.py`: LAX_RESCUE 0.25 -> 0; a rescued panic still cuts standards by half of LAX_PANIC; Bad Debts lower standards.
- Soft landing caps boom endings; Lure debt 6 pool-months at once -> 0.5 a month for 12 months.
- Not taken: FIN_BOOM_BASE 1 -> 1.5, TRUST_RECKLESS 0 -> -1 (the user's call).

## Checks run
- `tools/check.py` OK on `mod/`; `mod/` equals the tested worktree build byte for byte apart from `built_against.txt`.
- `i18n.py check`: 0 missing, 0 broken in all 10 languages. Not viewed in game in languages other than English.
- Full engine batch: 304/313 (`sm13/runs/quick_20261124_200211_750620`). The 9 failures are the 9 that 1.2.1 and 1.2.2 fail.
- Contest batch: 89/109 (`sm13/runs/quick_20261124_200329_513005`); 19 of the 20 failures also fail in the last 1.2.2 batch.
  The other is `press_exposure_price`. It passed when `rival_press` ran alone (7/8). It probably needs no mod fix: the fixture expects an
  exposed press campaign to cost exactly 2 trust and Britain's monetary law cuts trust losses, so it fails whenever the random
  roll exposes (not confirmed). `press_exposure_odds` expects 35 to 85 of 200; France's 20% speech law gives 33 to 34.
- Static unit tests: 26 failures against 29 at commit 526be2b, the same ones but for
  `test_observer_shares_competition_rows_and_uses_the_viewed_pair`, which looks for the old contest rows.
- In game (dev build, Britain 1857, English): contest bar and action tooltips, industry construction tooltips, the Lending Standards
  row, Company of the Year event. No new mod errors beyond the usual load warnings.
- Not run: a game with any compatibility patch; a headless century of 1.3.

## Open
- The Workshop "How the AI plays" chart is from 1.2.1; the text says so and gives 1.3 simulation numbers.
- Translation wording mismatches reported by the translators (old strings): Spanish lending level names; the `spec_rv_press_fx`
  trust word in French, Spanish and Portuguese; Japanese and Polish "Poor" relations; y/m/d countdown letters in East Asian
  languages; the "each Blue Chips" plural in English `SPEC_RIVAL_RULE`.
