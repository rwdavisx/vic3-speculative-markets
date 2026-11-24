# 1.2.2 release state (prepared 2026-11-24 overnight, NOT published, NOT committed)

Release candidate: `build_scratch/rc_1.2.2` (stable id, VERSION 1.2.2). `mod/` is untouched and still 1.2.1.
Changelog: `workshop/changelog_1.2.2.bbcode`.

## In 1.2.2
- Soft landing (Reddit report: building to meet real demand was punished as a Collapse). `generate.py`: when a boom
  begins, `spec_start_<g>` = the slow price average. `spec_sev_next_<g>` caps the ending at Correction while the price is at
  or above the start, and at Bust above start - LAND_DEEP (0.1 of base price). `spec_risk_raw_<g>` is tiered by the capped
  severity. Concept and unwind loc say so. The tuner engine mirrors it (`self.start`, LAND_DEEP).
- Contest moves act over months (`rivals.py`, `notify.py`): monthly costs and pushes. Lure debt arrives at 0.5 pool-months
  a month for 12 months, and a panic ends the Lure. An unpaid Raid gives back the rest of its hit (exploit fix). Toasts
  when a player's campaign ends early. The AI affordability gate is 3x the monthly cost.
- Banking fix (`cycle.py`): LAX_RESCUE 0.25 -> 0; a rescued panic still cuts standards by LAX_PANIC x 0.5; Bad Debts
  lower standards 1/20 a year (twice under Tight) instead of freezing them.
- Earlier in the 1.2.2 work: Leading Exchanges tier folds and the Provincials list (`centres.py`); building-scope good
  modifiers (`companies.py`, `levers.py`); outliner Investor Interest and ending icons (`goods_panel.py`); Exchange
  Score/Trust monthly deltas; contest tooltip breakdown.
- Balance (`tools/tuning.json`), chosen from the tuning agent's candidate:
  LEV_PANIC_SPAN 50 -> 55, LEV_CRUNCH_FADE 0.3 -> 0.35, LEV_BAILOUT_CUT 0.3 -> 0.25, LEV_INCOME_FLOOR unset (0.01) -> 0.009.
  Tuner (targets met / score): seed 19 n500 23/31 26.22 -> 25/31 18.49; seed 7 n500 24/31 23.46 -> 25/31 19.05;
  seed 1 n1000 24/31 23.89 -> 24/31 19.11. reckless-careful -0.60 -> -1.17 (seed 19), AI freeze p90 28 -> about 23,
  output lost per panic stays in band. skilled-careful falls 0.26 -> 0.15 (was already out of band).
- Not taken from the candidate (user to decide): FIN_BOOM_BASE 1 -> 1.5 (bigger booms; against the Reddit complaint, and
  the Mania target it meets sits above what real AI games show) and TRUST_RECKLESS 0 -> -1 (reverses the 1.2.1 change).
  With both, the tuner meets 29/31 on seed 19 (candidate in the session scratchpad, `tune_122_candidate.json`).
- Translations: 42 new strings in all 10 languages, `tools/i18n/<language>/v122.json`.
- Saved per-country numbers (`rivals.py`, `spec_rv_put`): the game does not overwrite an existing map key, so an unpaid raid could
  give back the first raid's amount (new in 1.2.2) and Shore Up dates kept the first date (live since 1.2.1). Test `rival_put` 4/4.
  Added 2026-11-24 after the candidates below were built: `rc_1.2.2` is rebuilt, the patches and the Beta zip are NOT.
- VERSION 1.2.1 -> 1.2.2.

## Checks run
- `tools/check.py` OK on `build_scratch/rc_1.2.2`. `i18n.py check`: 0 missing, 0 broken in all 10 languages.
- In-game mechanics batch (beta-id copy `build_scratch/test_beta_rc122`, `quick_test.engine_batch`, IMMEDIATE):
  304/313, `runs/quick_20261124_075552_785338`. The 9 failures are the same 9 the 1.2.1 Beta fails
  (`runs/quick_20261124_073251_597255`): leverage_ruin_boundary, leverage_caps_and_no_credit_room, standards_floor,
  charter_change_halves_trust, 3 exchange_monthly, 2 player_feedback. No mod error line that the 1.2.1 Beta run lacks.
- Fixtures updated to the intended new behaviour: `tests/mechanics/banking.txt` (bailout: 25% cut, standards unchanged),
  `tests/mechanics/credit_cycle.txt` (3 Lending Standards cases: Bad Debts now sober banks), and the
  `finance_priority.helpers.json` rival-month boundary comment.
- Headless AI game (`tools/sweep.py --name rc122 --games 1`, `runs/sweep_rc122`, log build `build_scratch/rc_1.2.2_log`):
  hit the 60-minute timeout at January 1878, so compared up to 1877 against the 1.2.1-equivalent games `runs/sweep_lev12c`
  C_01 / C_02 (script `cmp_games.py` in the session scratchpad):
  - boom endings Correction / Bust / Collapse: 6513 / 3704 / 153 against 5831 / 4313 / 258 and 6000 / 4250 / 355
  - panic starts, all countries: 358 against 270 / 299; the 25 largest economies 2.1 a century against 1.7 / 3.0
  - world GDP growth 1840-1877, the same ~200 countries, yearly mean of telemetry gdp: 1.6%/yr (x1.8) against 1.7 (x1.9)
    and 1.6 (x1.8). (An earlier probe.log figure summed the ~10 countries probed on January 2 and was not world GDP.)
  - 25 largest: Reckless standards 30.8% of months against 26.5 / 25.4; Bad Debts 3.3% against 2.2 / 4.1; trust under 25
    5.3% against 6.0 / 10.5
  - no game crash; 193 mod error lines (1.2.1 games: 193); no error type the 1.2.1 games lack.
  One game per side: differences under about 30% are within game-to-game spread.
- No live UI check was done. Still worth a look in game: the outliner icons, the contest tooltip, campaign toasts.

## Candidates built (not uploaded)
- Morgenroete 1.2.2: `runs/morgenroete/v122_rc` (parent rc_1.2.2).
- TechRes 1.1.2: `runs/techres/v122_rc` (parent rc_1.2.2).
- BPM 1.0.2: `runs/bpm/v122_rc` (parent rc_1.2.2, BPM 2.5).
- CMF: no rebuild. Its patch holds only CMF and vanilla GUI files, and CMF does not override `outliner_pinnable_types.gui`.
  The Great Rework (2880441881) does override it, so with TGR loaded after us the outliner icons would not show.
- Beta 1.2.2-beta.1: `beta/candidate_122/releases/Speculative_Markets_Beta_1.2.2-beta.1.zip`, gameplay bytes equal to
  rc_1.2.2. Built in a candidate folder so no immutable archive exists in `beta/releases` before the go.

## Release steps (on the user's go)
1. Stable output: `Remove-Item Env:SPEC_MOD_OUT -ErrorAction SilentlyContinue; py -3 -B tools/generate.py`, then
   `py -3 -B tools/check.py`. Confirm `mod/` matches `build_scratch/rc_1.2.2`.
2. Package: `py -3 -B tools/package_release.py`.
3. Stage: `py -3 -B tools/stage_workshop.py speculative_markets releases/Speculative_Markets_1.2.2.zip`.
4. Upload: `tools/steam_upload.py`, dry run first, then `--execute`, with `workshop/changelog_1.2.2.bbcode`.
5. Patches: rebuild against `mod/` (`--parent mod`) with the versions above, then upload all three.
6. Beta: `py -3 -B beta/build.py --revision 1` (from `mod/`), then upload to the Beta item.
