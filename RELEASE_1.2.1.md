# 1.2.1 release state (prepared 2026-11-23 overnight)

Published 2026-11-23 23:50 UTC, public, both verified:
- Stable 1.2.1, item 3831434383. Archive `releases/Speculative_Markets_1.2.1.zip`, SHA256 6012c6a59dfe77b811b77d84c1588f06fa94f2457e93d6689b31905a4cd798c5.
  Receipt `workshop/upload_receipts/20261123T235025.165958Z_stable_update_verified_199db318.json`.
- BPM patch 1.0.1, item 3844392018, built against `mod/` 1.2.1 (`runs/bpm/v121_release`). Archive
  `releases/Speculative_Markets_BPM_Compatibility_1.0.1.zip`, SHA256 b37bc7f4792501fd83335da68d269dc26757b5ec2ed0f661c60c6758d21287bc.
  Receipt `workshop/upload_receipts/20261123T235041.966458Z_bpm_update_verified_276af695.json`.
- Correction, 2026-11-24 01:20 UTC: the Morgenroete and TechRes patches ship generated copies of the parent's script values,
  English text and the market tab GUI (TechRes also spec_modifiers.txt), so from 23:50 their users ran 1.2.0 values and text
  over 1.2.1. Rebuilt against `mod/` 1.2.1 and published, verified, not run in game:
  - Morgenroete 1.2.1, item 3839705018, `runs/morgenroete/v121`, SHA256 f899a656daaba2b9eca0a839c7e15f498757bc4b0414241f3a5edb2c5ca5641f,
    receipt `20261124T011957.883114Z_morgenroete_update_verified_df819d22.json`.
  - TechRes 1.1.1, item 3841713072, `runs/techres/v121`, SHA256 5c9f555b988692975f9019ad8a0871272a3fb1aeddf40ab7ca33c063df94a407,
    receipt `20261124T012003.382837Z_techres_update_verified_3c5e3966.json`.
  - CMF needs no rebuild: its patch holds only CMF and vanilla GUI files.
  Any parent change to a generator that these builders rerun needs both patches rebuilt, not only GUI changes.
- Beta 1.2.1-beta.1, item 3839275304, gameplay bytes equal to `mod/`. Archive SHA256
  42924a4360f2f9f93f913b427d37190276e5cfc0007da7dd7ba5481116740ad7, receipt `20261124T012050.070880Z_beta_update_verified_7c37ad19.json`.
- The stable description now carries the version (`__VERSION__`, filled by `tools/steam_upload.py`); description-only update
  verified, receipt `20261124T002858.265020Z_stable_update_verified_50080e6d.json`.

## In 1.2.1
- Domestic Market News redesign (names goods and interest groups by sector; no English literals left, all 10 languages).
- Panic Risk alert: fires when the Risks floor (`spec_after_risks`) is below the panic line.
- BPM economic ideologies take Monetary Standard views (`monetary.py`, TRY_INJECT; not in the 1.2.0 `mod/`).
- Balance: TRUST_RECKLESS -1 -> 0; TRUST_PRESTIGE 0 -> 0.05 (`tools/tuning.json`).
- Leverage rework (`tools/tuning.json`): LEV_REWARD 0.035 -> 0.025; LEV_REWARD_MAX 4 -> 12; LEV_CRUNCH_FADE 0.47 -> 0.3;
  LEV_CRUNCH_INVEST 0.0075 -> 0.03 (was the leverage.py default). LEV_CRUNCH_MAX 20 and LEV_BAD_STOP 11 are unchanged.
  LEV_REWARD_TAPER unset -> 0: the bonus counts tenths of a month instead of whole months. Tuner (n 500, seeds 19 / 7) against
  whole months: reckless-careful -0.87 -> -0.94 / -0.98 -> -1.07; skilled-careful 0.59 -> 0.56 / 0.55 -> 0.56; panic loss
  12.0 -> 11.6 / 12.5 -> 11.9. Not run in headless games: the tenths only move the bonus by up to 2.5%.
- Scaled toward vanilla (user's pick, 2026-11-23): LEV_REWARD 0.025 -> 0.02 (+24% at 12 months; vanilla's country-wide
  throughput tops out near +10%, a decree gives +25% to one group in one state), with the penalty scaled alike:
  LEV_CRUNCH_THROUGHPUT 0.035 -> 0.03, LEV_CRUNCH_INVEST 0.03 -> 0.025. Tuner (n 500, seeds 19 / 7): reckless-careful
  -0.84 / -0.95, skilled-careful 0.47 / 0.47 (band 0.5 to 3), skilled-ai 0.69 / 0.80, panic loss 10.1 / 10.4.
- Construction bonus (user's call, 2026-11-23): the bonus moves to the smooth mode with an investment part.
  LEV_REWARD_TP_FULL unset -> 0.24 (the same 2% a month to 12, so LEV_REWARD / LEV_REWARD_TAPER no longer apply),
  LEV_REWARD_INV_FULL unset -> 0.06 (0.5% pool efficiency a month for capitalists, aristocrats and shopkeepers),
  LEV_CRUNCH_INVEST 0.025 -> 0.035 (worst Bad Debts cost 70% investment). Built capacity outlasts Bad Debts, so the investment
  penalty has to grow faster than the bonus. The growth link can't be calibrated (campaign 3.5, candidate games 15, not
  causal), and two headless games per side can't resolve it either (game-to-game spread about 10% of world GDP), so the pair was
  chosen to hold at both links. Tuner (n 500, seeds 19 and 7 averaged; reckless-careful / skilled-careful / skilled-ai):
  link 3.5: -1.04 / +0.63 / +0.75; link 10: -0.90 / +1.29 / +1.76. Rejected: 10% needs 4% and still gives -0.54 at link 10;
  5% with 2.5% lets reckless win at link 10 (+0.37). Grid: scratchpad inv_grid.py. Not run in headless games.
- Tooltips under the smooth mode: band tooltips give investment as a range too; SPEC_LEV_STEP names the investment gained and
  the investment Bad Debts take each month. The bonus-off build is byte-identical to the build before this change.
- Leverage tooltips: the band tooltips give each band's range ("+7.5% to +20%"), and the main tooltip adds SPEC_LEV_STEP,
  what one more month adds and risks (`tools/market_tab.py`).
  - Tuner (n 500, seeds 19 and 7): reckless-careful -0.1 -> -0.93; careful-passive +0.9 -> +1.45; skilled-ai +0.2 -> +0.77;
    panic loss 10% -> 12.3%; AI longest freeze p90 21 -> 29 months. The skilled bot does best going Tight at about 6 months.
  - Headless, 2 games each to 1880 (runs/sweep_lev12 A, runs/sweep_lev12c C): median country growth 2.61/2.83 -> 2.78/2.74 %/yr;
    panics 2.3/2.8 -> 2.3/3.1 a century; world GDP 1879 1264/1391 -> 1199/1285 (about -6%, mostly the smaller bonus at the AI's
    usual 3 months); GBR Bad Debts 6/7 years -> 5/4. No game crashed. A deeper ceiling (CRUNCH_MAX 35, BAD_STOP 20) was rejected:
    world GDP -13% and Britain collapsed.
- VERSION 1.2.0 -> 1.2.1. Changelog: `workshop/changelog_1.2.1.bbcode`.

## Not in 1.2.1
LEV_REWARD_CURVE stays 1 (straight). SPEC_LEV_STEP assumes it; a front-loaded curve would need per-section text.

## Checks run
- `tools/check.py` OK on the stage build (rerun after the leverage rework). Its gameplay files match the tested lev12_C build
  apart from the headless logging.
- `i18n.py check`: 0 missing and 0 broken in all 10 languages.
- `centres.py` self-check OK (a stale assert was fixed).
- The default build is byte-identical to the build made before the inactive leverage keys.
- No game was launched. These still need an in-game look:
  - the bulletin: hover tooltip, layout and stutter
  - the Panic Risk alert
  - old-save "Earlier News"

## Release steps (on the user's go)
1. Stable output: `Remove-Item Env:SPEC_MOD_OUT -ErrorAction SilentlyContinue; py -3 -B tools/generate.py`, then
   `py -3 -B tools/check.py`.
2. Package: `py -3 -B tools/package_release.py`, which writes `releases/Speculative_Markets_1.2.1.zip` and its manifest.
3. Stage: `py -3 -B tools/stage_workshop.py speculative_markets releases/Speculative_Markets_1.2.1.zip`.
4. Upload: `tools/steam_upload.py`, dry run first, then `--execute` (see `workshop/new_items.md`).
5. No GUI files changed, so the CMF, Morgenroete and TechRes patches need no rebuild. The BPM patch does need one: it ships a
   full copy of the localization, so the 1.0.0 patch shows 1.2.0 text (seen in game: the old +14% leverage tooltip). A
   candidate built against the stage build (with the construction bonus and its translations) is in `runs/bpm/v121_dev4` (`--version 1.0.1`); rebuild it against `mod/` at release
   and upload it with the main mod.
