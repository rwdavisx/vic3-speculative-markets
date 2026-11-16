# 1.0.6-beta.11: Rival Exchanges

The Rival Exchanges redesign in `design_rivals.md`, build steps 1 to 4. The user lifted the balance freeze for this
feature on November 15, 2026.

- **Rivalries come from vanilla:** a rival pair is any vanilla rivalry, in either direction, where both countries have
  an Exchange.
- **Removed:** the old one-rival system (`spec_rival`, the Choose button, the 5-year lock and the End button). Old
  saves drop `spec_rival`, `spec_rival_lock` and `spec_rival_last` without creating vanilla rivalries.
- **Yearly contest:**
  - It settles once per pair.
  - The stake is 3 trust, multiplied by (1 + Standing gap) for an upset and divided by it for the expected result.
  - The loser loses 1.5 times as much on poor relations.
  - The first contest runs a year after the first monthly pass, not on it.
- **Four actions:** Bear Raid, Lure Their Capital, Press Campaign and Shore Up, at the numbers in the design table.
  The first three have a one-year cooldown per target. Shore Up has a 2-year cooldown.
- **AI:** acts once per rivalry a year with a 25% chance, ±15% by temper, and shores up first after being hit.
- **Event `spec_rival.1`:** fires for a targeted player. Its choices are Answer in kind, Shore up, or Keep calm (+2 trust).
- **UI:** the Rivalries section in Finance: rows, direction, scores, last year's result, running effects, the last move,
  and four dimmed-when-invalid action buttons with one-line effect previews. The World list shows a rivalry icon on
  rival rows.
- **Debug:** two buttons appear only in `-debug_mode`. One runs the yearly contest; the other makes every AI act at
  100% chance.
- **Translations:** all 10 languages are fully translated (`i18n.py check`: 0 missing and 0 broken in each).

**Archive:** `releases/Speculative_Markets_Beta_1.0.6-beta.11.zip`

**SHA-256:** `9f28a4da047921726cfc415f4ae33189e73aeca8c7c80fef9d54ba1e26da25e3`

**Generated from:** `build_scratch/beta_rivals_r11`

**Unpublished intermediate archives:** kept immutable, never uploaded.

| Revision | Archive | SHA-256 | Notes |
|---|---|---|---|
| beta.9 | `beta/rivals` | `b174f2f1…30e950c5` | Early iteration. |
| beta.10 | `beta/rivals_r10` | `633a7d95…fadd495e0` | The live check on it found 6 UI bugs, fixed in beta.11. |

**CMF:** `information_panel_bar.gui` is byte-identical to the beta.8 build. Only `spec_market_tab.gui` changed, so the
CMF compatibility patch needs no rebuild.

## Automated gate: not a single complete pass

**This beta did not pass one complete gate run.** The user chose to upload it without another full run.

- **Full run** `runs/release_gate/rivals_r11_full/report.json`: **71 of 75 suites passed**, with 1085 pass
  observations. The Python tests exited 0. The 4 failures:
  - **`issue_reload`:** failed `issue_active_day_680`, `issue_expires_day_740_cooldown_remains` and
    `issue_cooldown_expires_day_1105`, all in the after-reload stage. The generated Great Issue code
    (`spec_lever_effects.txt` and `spec_lever_triggers.txt`) is byte-identical to beta.8, where this suite passed, and
    no rival code touches it. The cause is not established.
  - **`legacy_hotfix`:** failed `exchange_annexed_rival_cleared`. The assertion was stale: it required `spec_rival_lock`
    to survive an annexation, but the redesign removes all three old variables on purpose.
    `tests/hotfix_economy_events.txt` was updated after this run to require all three gone. That is a test change
    only.
  - **`company_strength`:** blocking diagnostics at 19:20:20.
  - **`blue_chips`:** the game crashed on 1836.3.19.
  - Both of the last two ran while a separate one-suite run from another session overlapped this gate (19:18:47 to
    19:20:50). That run was later voided.
- **Rerun alone** `runs/release_gate/rivals_r11_recheck5/report.json`: **all 4 failed suites passed**
  (`issue_reload`, `legacy_hotfix` with the updated assertion, `company_strength`, `blue_chips`). The beta source was
  the same. The test inputs differ from the full run only in `tests/hotfix_economy_events.txt`.
- **Targeted runs on beta.11:**
  - `rivals_r11_subset`: 13 of 14 passed. The 11 rival suites, `capital_flight`, `owner_strata` and
    `campaign_repeated` were run; `rival_ai` failed.
  - `rivals_r11_ai`: `rival_ai` passed after the test fix below.

### New and rewritten suites

| Suite | What it checks |
|---|---|
| `rival_year` | Winner +3; result lists on both sides; ties; mutual and incoming rivalries settle once; the 120 cap; the expected result divided and the upset multiplied by the gap; no Exchange or no rivalry means no contest. |
| `rival_network`, `rival_bounds`, `rival_large_network` | Three- and five-country cycles, neutral and hostile, at the trust floor and ceiling; neutral networks conserve trust; reversed roles give the same result. |
| `rival_notifications` | One win toast and one loss toast per year across three rivals in either direction; all stakes kept; no toast in a tied year. |
| `rival_migration` | The real monthly pass removes the old variables on both sides and creates no vanilla rivalry. |
| `rival_raid` | Cost, cooldown, and the failure odds over 200 raids: 20–70 failures between equal scores, 98–170 against a stronger rival. On failure the raider takes the hit. The monthly countdown. |
| `rival_lure` | Credit added, target state, cooldown, one lure at a time, blocked during a panic, halved by Shore Up, monthly countdown and clean end. |
| `rival_press` | Influence slots, the trust hit, exposure odds over 200 attempts (35–85 exposures). |
| `rival_shore` | Halving, the 2-year cooldown and gold checks. |
| `rival_ai` | Acting frequency over 200 chances: balanced 53, bold 79, cautious 22 in the last run. Once per rivalry per call; shores up after a hit (38 of 100); never acts without a pair; retaliation ignores the cooldown. |
| `capital_flight` | Now uses vanilla pacts, and adds `rival_without_exchange_gets_no_bonus`. |
| `campaign_repeated` | `rival_state_valid` and `rival_hits_bounded` across the five-year campaign. |

### Test corrections (no production change)

- **Rival action and AI fixtures:** the test countries had an Exchange Standing but no Financial Centre score, so the
  pair check was false. Each test country now gets score 100 when it has none. In real games every country with an
  Exchange has a score.
- **`rival_ai` shore check:** the loop drained France's treasury. The cost is now refilled on each iteration.
- **`legacy_hotfix`:** the assertion was updated as described above.
- **`owner_strata` helper:** the end boundary was updated for beta.8's monthly issue cooldown (`value = 12`).

## Live check (dev game, -debug_mode, GBR 1836, Russia a mutual vanilla rival)

Done by the user with the coordinating session.

**On beta.10:**
- All four actions worked for the player: Raided 6 mo., Lured 12 mo., Press "it worked", Shored up 12 mo.
- Repeat clicks were blocked, with clear reasons.
- The check found 6 bugs, all fixed in beta.11:
  1. A result showed before any contest had run.
  2. The Press preview said 11 months and left out the trust loss.
  3. Lure had no preview line.
  4. Money in the previews was unrounded.
  5. A bare "Us:" label showed with nothing running on our side.
  6. Disabled buttons looked enabled.
- The console has no `effect` command. The debug buttons replace the console walkthrough.

**On beta.11:**
- All 6 fixes confirmed. Previews: Lure "£645K credit, 10% pool income"; Press "12 months, 5% trust".
- The used Press button is dimmed, with its unmet condition in the tooltip.
- The debug yearly contest showed "Won last year" and the "Outshines Its Rivals" toast.
- The debug AI turn: Russia ran a Press Campaign and was exposed.
  - Event `spec_rival.1` fired, with all three choices.
  - The row read "Their last move: Press Campaign, it was exposed".
  - Answering in kind ran our Press Campaign. The row then read "Our last move", and the button dimmed.
- `error.log` showed no mod runtime errors, only two vanilla `has_journal_entry` scope errors.
- Translations were seen only in English during the live check. They are verified by `i18n.py check`, not on screen.

## Open (minor, not fixed in beta.11)

- The "Answer in kind" tooltip doesn't name the action or show its cost and effect.
- A row shows only the latest move between the two countries. This is by design.
- Press Campaign's 12-month influence cost doesn't appear among the running effects, which cover only raid, lure and
  shore. This is by design.
- Design open question: should an action's cost scale with the target's size? It currently scales with ours.

## Publication

**Published** to the beta Workshop item `3839275304` (not stable) on 2026-11-16 at 00:31 UTC, by the coordinating
session at the user's request.

**Receipts** in `workshop/upload_receipts/`:

| Receipt | Recorded result |
|---|---|
| `20261116T003122.665633Z_beta_update_intent_abb9a8eb.json` | The update intent. |
| `20261116T003127.652321Z_beta_update_result_7460738e.json` | `result: 1`. |
| `20261116T003127.854045Z_beta_update_verified_e36cc50e.json` | Title "Speculative Markets - Beta", owned by the current user. |

**What was uploaded**
- The archive SHA-256 above, 163 files.
- The coordinating session reports these files are byte-identical to the `source_sha256` in both `rivals_r11_full`
  and `rivals_r11_recheck5`.

**How it was uploaded**
- The upload went through `scratchpad/upload_override.py --gate rivals_r11_full`, as for beta.8.
  `tools/steam_upload.py` is unchanged.
- Its `"automatic_pass": true` log line is an artefact of the override, not a gate result. See the gate section above:
  there was no single complete pass.

**Note on `legacy_hotfix`:** the assertion was edited after `rivals_r11_full` had ended, not during it.

**Previous staging** is kept at `workshop/upload_staging/beta_prev_1.0.6-beta.8`.

**Not committed:** no commit has been made without the user's OK.
