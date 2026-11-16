# 1.0.6-beta.8 validation (published to the beta item, 2026-11-15)

- Archive: `releases/Speculative_Markets_Beta_1.0.6-beta.8.zip`,
  sha256 `a433085c8e71fb6a11e2fb9bab9c4fef43037f91e0fde334e44140c397178778`, 157 files, built from
  `build_scratch/beta_r9`.
- Workshop: item 3839275304, public, `update_result` result 1, verified. Receipts:
  `workshop/upload_receipts/20261115T2200*_beta_update_*`.

## Gate: NOT a complete pass (the user chose to upload anyway)

- Full gate `runs/release_gate/issue_clock_106b8_full` was stopped at 44 of 69 suites.
  - 43 passed.
  - `crisis_overlap` failed. The game crashed (EXCEPTION_ACCESS_VIOLATION) on 1836.2.26, after all of its assertions
    and SUITE COMPLETE had passed.
  - The suite passed on its own when rerun (`runs/release_gate/crisis_recheck_b8_r1`), and in all 8 earlier full
    gates.
- The upload went through `scratchpad/upload_override.py`, which replaced `release_gate.verify_report` once.
  `tools/steam_upload.py` is unchanged. Its log line `"automatic_pass": true` is an artefact of that override, not a
  real result.
- Targeted suites that passed on this archive (`runs/release_gate/issue_clock_b8_r1`):
  - issue_reload
  - interventions
  - renown_score
  - all_goods_endings

## Changes since the last published beta

See `beta/changelog_1.0.6-beta.8.bbcode`. New in beta.8 over the unpublished beta.7:

- Great Issue and cooldown timers are now monthly counters (`levers.spec_issue_clock`). Engine `days =` timers on
  `spec_issue` and `spec_issue_cool` sometimes survived a save reload. Beta.7's gate `pool_perf_106b7_r1` failed
  `issue_reload` this way.
- The Companies header has a tooltip.
- The rival Exchange button is shown greyed out instead of hidden.
- Old saves: an issue or cooldown that is already running ends within a month.

## Not checked

- Live UI: the header tooltip, the rival button and the blue chip badge. The user is checking these.
- The 25 suites the stopped gate never reached.
