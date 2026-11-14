**Speculative Markets 1.0.1 — local hotfix, November 13, 2026**

The release is assembled and validated locally in `mod/` and [Speculative_Markets_1.0.1.zip](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.1.zip). Both final five-year campaigns completed with no mod runtime errors. Nothing has been uploaded to Steam Workshop. The original 1.0 files are preserved in [the baseline snapshot](G:/GameDev/speculative-markets/snapshots/hotfix_1_0_baseline).

Gameplay fixes:

- Rescuing banks no longer makes a fresh panic appear older by shortening its remaining duration. Actual elapsed months preserve the two-month minimum.
- Closing markets removes Panic Relief expenses, Long Depression effects and Exchange bonuses. Monthly repair also clears leftovers in existing saves while preserving historical depression origins, reforms and applicable cooldowns.
- Pending confidence effects and foreign-panic responses cannot restart closed markets or refer to a country that has disappeared.
- Frequent tier changes in one good no longer postpone the full building refresh indefinitely. Newly built or acquired producers receive the current effects of other goods.
- Exchange seat searches no longer reuse another country's candidate. Missing, merged, foreign and annexed-country seats are cleared safely; capital fallback requires domestic ownership.
- Rankings handle short lists without duplicate positions or out-of-range requests. Missing and annexed leaders are replaced; invalid rivals are removed safely.
- War-end confidence and foreign-panic source tracking resolve cached references safely. Valid opponents retain their existing stakes and confidence effects.
- Five inherited plantation AI formulas safely skip country-specific conditions when no building owner exists. Their other vanilla terms and Production Method Rework overrides are preserved.

Interface fixes:

- Finance uses its own category selection, shows consistent empty results, and includes Great Issues in intervention filtering.
- Opening another information panel closes Finance and disarms a pending speciality selection. Reopening works repeatedly.
- Panic tooltips show national throughput and tax penalties, and explain that rescues do not reduce ongoing relief expenses or undo the initial radicalization. All ten translated languages have the new strings.
- Exchange, rivalry and Renown labels guard invalid saved objects; journal map tooltips use the current valid owner.

Balance constants and tuning defaults are unchanged. These are correctness fixes; the campaign samples do not establish a general balance improvement.

Validation:

| Check | Result |
| --- | --- |
| Original 1.0 with the initial 13 engine assertions | 11 failed, 2 passed; proves the suite detects the original defects |
| Same initial assertions on the first hotfix | 13 passed |
| Final expanded engine suite | All 21 passed; no mod/harness runtime errors; [gate report](G:/GameDev/speculative-markets/runs/hotfix_1_0/reports/final_scenario_gate.json) |
| Python unit checks | 20 passed |
| Generator/static checks | Pass; 75 script/GUI files, 2,992 localization keys, no missing referenced keys |
| Translation validation | No missing or broken translations in any supported language |
| Reproducibility | All 154 generated release files match a separate clean build byte for byte; original thumbnail is unchanged |
| Release archive | 155 files; ZIP integrity and every archived byte verified; no debug logs, probes or regression events |
| Intermediate hotfix, same 1840 save through 1849 | Completed; no mod runtime errors in cumulative log |
| Intermediate hotfix, same 1916 save through 1920 | Completed; no mod runtime errors in cumulative log |
| Final frozen scripts, new 1836 game through 1840 | Completed through December 31, 1840; 16,196 country observations, confidence in 0–100, no mod runtime errors in cumulative log |
| Final frozen scripts, 1916 save through 1920 | Completed through December 31, 1920; 11,196 country observations, confidence in 0–100, no mod runtime errors in cumulative log |
| Exact release files without debug instrumentation | Exited successfully; no mod runtime errors; no debug-event orphan warnings |

The engine tests cover cleanup after law changes, legacy repairs, delayed responses, building refresh, seat ownership and annexation, leader/rival removal, short rankings, panic minimum and recovery, and preserved war-end stakes. The report gate checks the error log as well as PASS markers. Earlier candidate failures and fixture corrections are retained in `runs/`; they are not counted as clean final results.

The [completed run report](G:/GameDev/speculative-markets/runs/hotfix_1_0/reports/final.txt) records the observed dates, confidence bounds and error categories. Vanilla/headless diagnostics and known unused-variable/debug-event warnings remain; they are distinguished from mod runtime failures. An additional [final gate](G:/GameDev/speculative-markets/runs/hotfix_1_0/reports/final_validation.json) checks every shipping script/GUI path against otherwise unclassified errors, including overrides without a `spec_` filename.

The live debug-game checks verified Finance filters and empty states, repeated Finance-to-state-panel navigation, and the actual Bank Rescue button. The rescue changed five months remaining to two, disabled a second rescue, and displayed reduced throughput/tax penalties with the relief explanation. [Rescue screenshot](G:/GameDev/speculative-markets/runs/hotfix_1_0/ui_evidence/rescue_verified.png).

All game runs used separate user directories and disposable builds, and all test game processes have exited. Normal saves, playset and settings were not modified. The five other enabled mods were inspected for direct file/localization collisions; none were found. The combined playset and multiplayer were not exercised at runtime.

Existing saves have a migration fallback for panic age. An old save does not record the exact pre-hotfix elapsed age after a rescue, so that historical information cannot be reconstructed precisely. Fresh panics record it explicitly.

Build/test tooling now rejects malformed strings instead of hanging, handles escaped quotes, protects the release from debug output paths, removes stale generated files by an explicit output list, records scratch-build provenance, and preserves complete assertions and error-log rotations. Relative sweep paths are resolved before the game starts from its own binaries directory.

The local Workshop description now reflects the Finance panel and current GUI/building compatibility, identifies the tested game version, and includes the hotfix notes. An unsupported historical panic-frequency claim was removed.

Rebuild and validate:

~~~powershell
py -3 -B tools/generate.py
py -3 -B tools/check.py
py -3 -B -m unittest discover -s tests -p "test_*.py"
py -3 -B tools/i18n.py check
~~~

For engine regressions, prepare a separate build with [hotfix_testbed.py](G:/GameDev/speculative-markets/tools/hotfix_testbed.py), run it through April 1836 with [sweep.py](G:/GameDev/speculative-markets/tools/sweep.py), then use `--report <assertions.log> --error-log <error.log>`. Debug generation requires `SPEC_MOD_OUT` outside `mod/`; test builds must not be uploaded.

Review artifacts: [change inventory](G:/GameDev/speculative-markets/runs/hotfix_1_0/change_inventory.txt), [source diff](G:/GameDev/speculative-markets/runs/hotfix_1_0/reports/source_diff.txt), [archive hashes](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.1.manifest.json), and [Workshop description](G:/GameDev/speculative-markets/workshop/description.bbcode).
