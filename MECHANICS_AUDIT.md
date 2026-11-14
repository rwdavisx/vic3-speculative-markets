# Mechanics correctness audit

Balance is frozen at 1.0.3. The isolated and integration passes now have **644 passing engine
assertions in 56 suites**, plus **45 Python tests** and **9 CMF source tests**.
These are contract results, not a claim that every possible campaign works.
The open checks below remain prerequisites to the broader balance pass.

**Published:** Stable **1.0.5**, Beta **1.0.5-beta.1**, and Morgenroete patch **1.0.0** on November 14. Stable now includes the tested beta fixes. The patch has 76 inherited engine assertions plus 9 passing existing-Morgenroete-save migration assertions; all three added goods passed release UI checks. Current Python checks: 45 plus 9 CMF checks. See `HOTFIX_1.0.5.md` and `tests/mechanics/verification_release_105.json`. Full reporter playset and long campaigns remain outside coverage.

[Machine-readable results](tests/mechanics/verification_2026-11-14.json) record
assertion names, fixture/build manifests, log hashes, and error classifications.
Raw evidence stays in `runs/` and is not committed.

## Reproduced bugs and fixes

1. **Confidence labels disagreed.** At 55 and 59.99 the journal/map said Buoyant,
   while the Finance band remained Steady until 60. Both boundary assertions
   failed on the unchanged beta. `tools/journal.py` now uses the band threshold.
   The journal suite passes all 13 cases. The lending threshold remains 55.
2. **An older save could insert the Financial Markets journal twice.** The game
   can retain an inactive journal object while `has_journal_entry` returns false.
   The old insertion produced a duplicate-entry engine diagnostic. The monthly
   generator now checks `exists = je:je_spec_markets` before insertion, while
   preserving its existing flag. All four presence cases pass, and the entry
   remained visible and usable in the loaded 1840 save.
3. **The log gate missed that duplicate.** Its name matcher recognized `spec_`
   but missed `je_spec_`. A Python regression failed before the matcher fix and
   passes afterward. Duplicate journal diagnostics now fail the gate.
4. **Pressures/Risks rows sat above their vertical centers.** The inherited
   budget-row label margin and a separate -3 chip offset caused the mismatch.
   The generator now uses a plain row with centered labels and chips. The
   native beta was inspected in-game and the corrected screenshot was saved.

Red evidence: `runs/sweep_mechanics_cycle_journal_baseline/journal_01` (two
label failures), and `runs/sweep_mechanics_journal_duplicate_red_r2/journal_01`
(one duplicate-entry diagnostic). Green evidence: the final beta4 journal and
presence runs in the verification file. Beta5 changes only metadata and
`gui/spec_market_tab.gui` relative to beta4; every gameplay byte is identical.

## Isolated coverage ledger

“Passed” below applies to the listed contracts. The last column explicitly
limits it; untested behavior is not being classified as either correct or broken.

| System | Passed contracts | Still needs coverage |
| --- | --- | --- |
| Market lifecycle | command/cooperative shutdown, full monthly reopening, idempotent cleanup, reforms survive, second-month bounds | tag switches and more legacy saves |
| Confidence | 20/40/60/80 bands, clamps, story deltas, panic modifier exclusivity | additional campaign interactions beyond calm/tight/floor/ceiling/simultaneous-shock cases |
| Investor Interest | trend direction, reciprocal response, clamps, severity thresholds, peak decay, one ending per boom, all 49 collapse paths together | building and production-method combinations beyond the goods-state paths |
| Recovery | actual 90/180/360-day expiration, checks before and after each deadline in GBR/FRA/PRU, actual save/reload across all three durations | overlapping interventions beyond the tested open/closed/reopened law sequence |
| Lending | safe/stressed leverage boundaries, policy ceilings, repayment bounds, zero credit, panic/Bad Debts blocks, exact repayment/new-credit pool transfers | longer crisis chains beyond the tested panic/depression overlaps |
| Bank exposure | 60% new-loan allocation cap, dilution, conservation, empty/new credit, write-off once, restrained share, simultaneous endings, post-lending tooltip consistency | loan transfers through war/secession; live credit tooltip agreement now checked |
| Lending standards | drift gates, crisis-loss floor, upper/lower bounds, action multipliers | long-run combinations of overlapping interventions |
| Overbuilding / construction / owners | supply-loss neutrality, doubled-supply amplification cap, construction tiers 4/5/6, small-boom exclusion, bonus removal | each building group and PM beyond the tested steel-collapse population strata |
| Leverage / Bad Debts | ramp/fade/expiry, bailout lock cleanup, old-loan land-loss relief, repeated loss, new-loan exclusion, relief expiry | peace-deal integration; real state transfer and release-country initialization now covered |
| Financial Panic | minimum elapsed age, deadline, recovery, no repeated rescue, cooldown state, legacy clock migration | longer chains beyond the tested pledged-rescue reload and panic/depression cash flows |
| Credit policy / AI | same stance actions and cooldown, mania tightening, debt tightening, low-confidence loosening, recovery, fever/panic gates | probabilistic rescue frequency; actual ruling-IG turnover now covered |
| Goods interventions / Great Issues | eligibility, mutual exclusion, toggle/cancellation, shutdown, issue cooldown | additional combinations beyond tested actual costs and saved Great Issue deadlines |
| Exchanges | actions/charters, pursuit ordering, pledge notice, monthly trust gates/cap, Bad Debts prevents promotion, seat ownership, annexed/missing ranks and rivals | larger networks and repeat-year interactions; reach/size, score factors, standing boundaries and ordinary/hostile three-way transfers including floor/cap now covered |
| Domestic economy / politics | growth bounds and stagnation, depth/trade multipliers, fixed AI temperament, mania goodwill, panic blame, cooling/cleanup | revolutions and additional building strata; ruling-IG changes and steel-owner population totals now covered |
| Foreign transmission / wars | real GBR-to-FRA hit, weaker hit cannot stack, stronger replaces, closed economy ignores; war-end live/missing opponent safety | actual war start-to-end campaign; treaty-chain recursion and capital-flight exclusions now covered |
| Long Depression | join/tie gates, repeat join, crash phase deadline, own/world recovery, clamps, cleanup/history, delayed safety | more treaty/trade networks; option population totals and IG modifier routing now covered, modifier magnitude/duration and live event buttons remain |
| Journal / reforms / stories | stage priority, reform combinations, debt conversion and lock, delayed missing-source/shutdown safety, journal insertion | player-tag journal persistence and live inquiry choices; actual one/five-year movement decay now covered; inquiry eligibility/options and immediate player-switch UI refresh covered |
| UI / notifications / localization | native beta5 and CMF beta4 journal/goods shortcuts select Speculation; native transitions; numeric posts; row alignment; static localization checks | scales beyond tested 100%/120% and all translated languages live; English filters and empty/reset states verified |
| Distribution | distinct IDs, frozen-source hashes, fixture exclusion, immutable beta archives, beta4/5 gameplay equality, regenerated CMF patch byte equality | beta-first promotion verified; see release receipts |

## Engine suites

| Suite | Assertions | Final evidence |
| --- | ---: | --- |
| banking | 13 | final_beta4/banking |
| confidence | 14 | final_beta4/confidence |
| contagion | 4 | mechanics_contagion_beta104_r2/contagion (replaces invalid original fixture) |
| credit_cycle | 19 | final_beta4/credit_cycle |
| depression | 12 | final_beta4/depression |
| economy | 10 | final_beta4/economy |
| exchange | 9 | final_beta4/exchange |
| goods | 17 | final_beta4/goods |
| interventions | 13 | final_beta4/interventions |
| journal | 13 | final_beta4/journal |
| journal_presence | 4 | final_beta4/journal_presence |
| lifecycle | 5 | final_beta4/lifecycle |
| panic | 12 | final_beta4/panic |
| politics | 5 | final_beta4/politics |
| construction | 5 | extended_beta5/construction |
| recovery | 9 | recovery_beta5/recovery |
| exchange_monthly | 8 | policy_final_beta5/exchange |
| ai_policy | 8 | policy_final_beta5/ai |
| legacy_hotfix | 21 | legacy_beta5/legacy |
| pledge_cash | 6 | rival_fix_beta104/cash |
| pledge_default | 5 | rival_fix_beta104/default |
| rival_year | 7 | rival_final_beta104/rival |
| technology | 7 | technology_beta104/tech |
| bank_display | 4 | bank_fix_beta104/display |
| cashflow | 6 | bank_fix_beta104/cash |
| recovery_reload | 9 | recovery_save_beta104/recovery + recovery_reload_beta104/recovery |
| all_goods_endings | 49 | all_goods_endings_beta104/goods |

Evidence abbreviations expand to `runs/sweep_mechanics_<batch>/<arm>_01`.
All accepted runs completed their assertion sequence and had **zero blocking
mod/harness diagnostics**. Existing engine/base-game diagnostics and variable
load warnings are recorded separately; this is not a claim of empty error logs.
The base-game scope errors in some observer runs point to vanilla
`00_ai_triggers.txt` from `paralegal_discrimination_events.txt`, not a
Speculative Markets call chain.

Two test-development mistakes were rejected rather than called green: early
helper files lacked a UTF-8 BOM, and the first Exchange monthly fixture invoked
the whole ranking pass, allowing annual rival rewards and AI pursuits to change
trust. The final Exchange fixture exposes exact production trust/notice/crunch
blocks separately. An intermediate edit also left a stale modifier assertion;
that failed run is retained. No production balance fix was inferred from these
fixture errors. Only accepted final runs contribute to the 201 count.

## Live UI evidence

- `runs/notification_scope_repro/mechanics_beta4_cmf`: GBR, 1840 save,
  CMF plus patch 1.0.1. Journal and ammunition-panel Open Finance selected
  Speculation. Finance yielded to the native Market panel. Observed numeric
  Grain/Coal posts rendered their multipliers. The retained debug log has no
  fixture-completion marker, so this run is not counted as a complete
  nine-notification regression.
- `runs/notification_scope_repro/mechanics_beta5_native`: GBR, same source save,
  no CMF. Ran into July 1840, paused; journal and grain-panel Open Finance
  selected Speculation. The journal remained present. Observed Steel, Iron,
  Tools and Fish notification variants rendered text and numbers. The full
  fixture completed. Both live logs passed the mod error gate.
- [Corrected row screenshot](runs/notification_scope_repro/mechanics_beta5_native/pressure_risk_alignment.png).
- The CMF builder was rerun against the beta5 source GUI into
  `build_scratch/mechanics_cmf_r5/mod`; all three patch files matched the
  existing 1.0.1 patch byte-for-byte. A further beta5 CMF session was stopped
  at country selection after the user deprioritized CMF. It is not a passed
  UI run. No CMF update was published or required by changed patch content.

## Running a contract suite

Use a fresh output name each time; test builds preserve the actual beta bytes.

```powershell
py -3 -B tools/mechanics_testbed.py --suite banking --out runs/mechanics/banking_next
py -3 -B tools/sweep.py --name banking_next --games 1 --jobs 1 --until 1836.4.1 --timeout 20 --arm banking=runs/mechanics/banking_next
py -3 -B tools/mechanics_testbed.py --out runs/mechanics/banking_next --report runs/sweep_banking_next/banking_01/assertions.log --error-log runs/sweep_banking_next/banking_01/error.log
```

The recovery suite must run until **1837.3.1**; the other isolated suites can
run until **1836.4.1**. Each suite needs its own fresh 1836 game. The existing
21-case hotfix suite can now use `tools/hotfix_testbed.py --source beta/mod`
so it tests the packaged beta rather than a regenerated approximation.

Cases are under `tests/mechanics/`. Optional helper specifications extract
complete, uniquely identified production blocks from the frozen beta and
record their hashes. They do not replace formulas with Python models.
Missing assertions, explicit failures, incomplete sequences and mod/harness
errors fail the report gate. Run the report after the sweep; sweep process
completion alone is not an assertion gate. These runs do not certify
multiplayer or arbitrary third-party mod combinations.

For a new bug: write the expectation, reproduce red on unchanged beta, fix the
generator, package a new beta revision, rerun that contract and related suites,
then check interactions/live UI before promotion. Keep balance work separate.

## Follow-up after stable 1.0.4 publication

Four new suites add 25 distinct assertions, for 226 across 23 suites. Six follow-up
runs (including Exchange action/monthly regressions) passed 42 assertions with zero
blocking mod/harness diagnostics. Details: `tests/mechanics/verification_followup_2026-11-14.json`.

- Rescue cash: exact manual/pledged treasury charges, pledge discount with identical
  lending standards, no double charge, an unfunded promise remains in force, later funding.
- Default: real treasury deficit put the test country into default; pledge rescue refused,
  trust cleared, confidence fell by 15, notice ended and the penalty applied only once.
- Technology: Sokoto began without Banking/Central Banking. Rescue/bailout and AI policy
  gates stayed closed, Banking unlocked rescue/bailout, and Central Banking unlocked policy.
- Annual rivalry: winner reward, mutual-rival deduplication, cap, loss and tie cases.
  Both tie-after-win and tie-after-loss failed on unchanged beta5: the old result remained.
  The generator now stores zero for a tie and selects a translated "Tied last year" label.
  No trust changes on ties. All seven cases pass in the final beta2. Stable does not yet
  include this new fix. Localized text passed static validation, not live rendering.

The first cash fixture compared a pledge against a pre-rescue price while leaving the
rescue's lending-standard increase in place. That invalid comparison failed; resetting
standards fixed the fixture without a production change. Internal beta1 was not uploaded:
it lacked the source preview and had English fallback for the new label. Final beta2
restores the preview and translates the label in all ten additional languages; gameplay
and English UI bytes match beta1. Immutable artifacts and failed evidence are retained.

## Cash flow, bank display, and save/reload follow-up

68 new assertions bring coverage to 294 assertions across 27 suites. Including the
19-case credit-cycle regression, this batch passed 87 assertions with zero blocking
mod/harness diagnostics. Evidence: `tests/mechanics/verification_cashflow_2026-11-14.json`.

**Proven bug:** goods/bank tooltip months-of-income and loss multipliers were cached
before the monthly repayment/lending, while the share and Banking chart were current.
All four full-month data-consistency assertions failed on published beta2. The generator
now caches those values alongside the chart after credit and leverage updates. The four
assertions pass on beta3. Removing that same 49-good cache block from the old and new
monthly files leaves byte-identical logic: no economic formulas or balance changed.
This verifies the values the GUI reads, not a new live visual inspection.

Cash-flow assertions pass for exact funded repayments, unpaid runoff written off when
the pool is exhausted, matching new-credit pool/debt increases, two simultaneous endings,
and no repeated losses. All 49 supported goods also pass collapse/recovery/exposure
assertions in a single full monthly update; this is not every building/PM/population test.

An actual annual autosave captured the three 90/180/360-day recovery timers after they
started in late 1836. A separate game loaded it, ran through January 1838, and passed all
before/after deadline assertions. Both complete error logs passed the gate. This test
uses frozen beta2; beta3 only moves the bank display cache. Save hash and paths are in the
verification record. Do not replace these runs with a fresh-game-only expiry claim.

Beta 1.0.4-beta.3 was published and verified at 13:52:58 UTC on November 14.
Stable remains 1.0.4 and does not yet include either later beta fix. No CMF patch GUI
changed. Balance stays frozen; the ledger retains the remaining interaction checks.

## Accounting and extended contracts (beta4)

101 new assertions pass across eight additional suites. The candidate fixes one
proven display-accounting bug: at zero or near-zero confidence, a burst reported
more confidence loss than was actually possible. Four targeted assertions and the
full-month floor assertion failed on unchanged beta3. The generator now caps the
reported burst contribution to available confidence. The resulting confidence and
balance formulas are unchanged. Twelve full-month accounting checks and six
focused burst checks pass on the candidate.

Other accepted checks: six real expense/Authority/modifier contracts; five Great
Issue duration/cooldown checks across an actual save/reload; seventeen standing
boundaries; nine pursuit buildup/fade/modifier checks; ten overlapping crisis and
second-crisis contracts; and thirty-six depression-option/rank checks. Event-option
coverage checks confidence, recovery, selected modifiers and treasury costs, not
all political-group/population consequences. Evidence and hashes:
`tests/mechanics/verification_accounting_2026-11-14.json`.

The stricter error gate now recognizes mechanics event paths even when an error
contains no mod symbol. Rechecking all 33 previously archived error logs exposed
one invalid arithmetic comparison in the old contagion fixture. Its old pass is
withdrawn; the corrected four-assertion suite passed on local beta4 with no blocking
errors. Historical evidence remains intact. Owner-population and treaty-chain
fixtures remain under investigation and are not included in the passing count.

Rejected fixtures are retained: the first lever-cost fixture read engine modifiers
before their update tick; the first depression-option fixture omitted the world
clock; early owner fixtures used an invalid building name, ignored engine radical
gain modifiers, or attempted unsupported pop variables. These are test defects,
not proven gameplay bugs. Stable and published beta remain unchanged.

Population and transmission follow-up: ten steel-collapse strata checks now pass,
comparing affected population totals with direct engine effects under identical
citizenship/loyalty conditions. Private ownership targets upper/middle strata;
cooperative ownership targets lower strata; command ownership leaves all unchanged.
This exercises the branch directly, not natural booms under closed-market laws.
Six treaty-chain checks pass after moving the fixture away from the normal monthly
pulse: Sokoto reaches Zulu first, Madagascar waits for the next controlled tick,
and the chain does not echo. Nine capital-flight checks pass for source-size caps,
both directions of rivalry, and closed/panicking/low-confidence recipients.

Beta 1.0.4-beta.4 published and verified at **14:23:52 UTC** November 14.
Receipt: `workshop/upload_receipts/20261114T142352.503370Z_beta_update_verified_48d4f209.json`.
Archive SHA256: `b0c66b01bbcb99f60e65a8d8246de86a126335014c516a85ffb9d8e10a4d2f82`.
The 37 confidence/credit-cycle/bank-display regression assertions passed the full
error gate on this exact beta. Stable remains 1.0.4; no CMF GUI files changed.
Pledged-rescue save/reload and actual war fixtures are still under investigation;
they are excluded from the coverage count.

The pledged-rescue save/reload suite now passes three assertions: the payment occurs
before the actual January 1837 autosave, pledge/rescue state survives loading, and
rechecking the rescue cannot charge again. Both full logs pass. The earlier fixture
scheduled its rescue after the save and checked after normal panic expiration; it is
rejected rather than counted as a save test.

The runner's debug-log reader now drains unread rotated files before reading their
replacement. A real war run proved that three assertion lines existed in debug.1.log
but were missing from the saved report. A rotation regression covers an unread tail
and a replacement larger than the previous read offset. Forty Python tests pass.
The old incomplete war runs remain rejected; no missing assertion is counted as pass.

Recovery/law overlap: six checks pass on the published beta4. Open-market law changes preserve an active collapse recovery; command-economy shutdown removes its state; reopening does not resurrect it, while the lender-of-last-resort reform survives. Six three-country rivalry checks also pass: each pair transfers the expected trust once, including the 1.5 hostile-loss multiplier. These cases avoid the trust floor/cap, whose multi-pair ordering is still untested.

Fifteen Exchange score checks pass for trust weighting/cap, missing trust, Great Issue bonus/removal, wealth multiplication, zero size and economic-law factors. This does not yet cover the upstream square-root/reach calculation. Live English UI checks passed at 100% and 120% scale, including empty/reset filters, credit tooltip agreement and immediate GBR-to-FRA panel refresh; screenshots and full log gate are recorded in `tests/mechanics/verification_ui_beta104_4.json`. The real-war fixture remains experimental: its imposed war-support loss does not reliably end the war by the asserted deadline. Its peace assertions are not accepted coverage or a proven mod defect.

Thirteen inquiry contracts pass: 119/120-month eligibility, active-panic exclusion, fresh/used aftermath, the four reform option effects and their IG modifiers, completion counting, actual Sound Finance event reward, and no further inquiry once all reforms exist. The option effects are extracted unchanged from production; this does not claim live event-button or random AI-frequency coverage.

Eleven Renown reach/size checks pass (real investment-rights treaty, equal/larger partner exclusion, square-root size, wealth bounds, zero income). Six movement-support checks verify the actual inherited state modifiers, no double application, one-year decay and five-year expiration. Six actual state-transfer checks pass after transferring non-capital states and allowing eight days for engine updates. Earlier smaller/one-day fixtures did not establish the required population loss and are rejected. Twenty-three output-basket checks cover all ten multi-output building baskets and their technology gates. These baskets intentionally follow unlocked technologies, not each building's currently selected PM; changing that would be a design/balance change.

The continued beta campaign completed through December 31, 1849 with zero blocking mod diagnostics (one campaign, not a universal crash guarantee). Seven integration assertions pass across the active countries in its 1842 checkpoint: confidence, debt, lending standards, each goods exposure, exposure totals and severity remain in bounds. The first invariant run ended before its delayed event and is rejected. Campaign provenance, the intentional telemetry restart, and full error counts are in `tests/mechanics/verification_campaign_beta104_4.json`.

Six government-turnover checks pass after actually replacing the ruling IGs and running the complete monthly action. Temperament, enacted reforms and the active credit-policy cooldown survive both transitions. Probabilistic AI rescue frequency and revolution-created successor countries are separate open checks.

The subsequent live war test **does reproduce a defect**: France manually capitulated on March 25, 1836 after all three wartime checks passed. Britain received its +1 confidence reward, but France never fired `on_lost_war` and received no defeat penalty. Five of six assertions passed; this suite is not added to accepted coverage. The full log has zero blocking diagnostics. Evidence is in `tests/mechanics/verification_capitulation_beta104_4.json`. A separate diagnostic run confirms France instead fires `on_capitulation`, with a diplomatic-play scope but no enemy-country, war or victim-of-wargoal scopes. A fix is under investigation; stable and published beta are unchanged.

Candidate beta5 fixes the confirmed surrender defect using the engine capitulation callback, matched diplomatic-play identity and cached casualty stakes. Goal-target tracking distinguishes the defeated target from an ally; a short settlement list prevents duplicate charges. Twelve isolated accounting/routing checks and all six real-war replay assertions pass, with zero blocking diagnostics. France now falls from 55 to 53 on surrender. Twenty-one existing hotfix assertions also pass. Final logs, screenshots, fixture hashes and archive hash are in `tests/mechanics/verification_capitulation_beta104_5.json`. Stable remains unchanged. Late settlement after an ally leaves an ongoing war remains a separate open case.

Beta5 publication verified at 15:34:05 UTC November 14: `workshop/upload_receipts/20261114T153405.356081Z_beta_update_verified_08697ab8.json`. Archive SHA256 `6a290434d15df8335d74da6d3a1deceb9a35702dafbcc44e86b407792168ced8`.

Eight new-country checks pass after actually releasing Ireland from Britain. Custom debt, confidence/crisis flags, policy cooldown and reforms are not cloned; Britain retains its debt. The next normal monthly pulse initializes Irish finance, goods and the journal. Full error gate passes. This is a release-country test, not a revolution test. The first fixture used boolean values for countdowns and is rejected. Evidence: `tests/mechanics/verification_new_country_beta104_5.json`.

Twelve three-way rivalry boundary checks pass at trust 0/120 with neutral and hostile relations. Winners/losers receive exact bounded amounts; mixed wins and losses remain inside the interval allowed by per-pair clipping. This does not assert that clamping commutes with country iteration order. Evidence: `tests/mechanics/verification_rival_bounds_beta104_5.json`.

Four depression population contracts pass: all states match the engine capitalist radicalism effect, other pop types stay unchanged, and repeat joining does not repeat the hit. Five war save/reload checks pass across an actual yearly autosave: diplomatic-play identity and monthly cache survive, and controlled settlement still routes and deduplicates. Full logs pass. Evidence: `tests/mechanics/verification_depression_pops_beta104_5.json` and `tests/mechanics/verification_war_reload_beta104_5.json`. Rejected fixture versions are recorded in each evidence file.

Finance compatibility report: a matched live A/B test on game 1.15.1 confirms that the third-party Speculative Markets+Morgenroete patch (Workshop 3836657389) replaces spec_market_tab.gui with an obsolete copy missing both Finance widget types. With its exact GUI override, the sidebar highlights but never opens; removing only that override restores Finance with CMF and our official CMF patch on the same paused 1840 save. The bridge also replaces nine gameplay files. This is a minimal sufficient reproduction, not verification of the reporter's entire playset or journal shortcut. Their 108 investment-pool missing references do not directly identify Finance. No production changes or new upload. Evidence: `tests/mechanics/verification_mr_gui_conflict_20261114.json`.

Morgenroete replacement candidate: downloaded current Morgenroete 2.9.0e Curie and
the third-party bridge, then generated a separate beta5 compatibility delta from
our maintained source. It adds instruments, uranium and publications, preserves
the current Finance interface, and retains electricity (absent from the old
bridge's 51-good registry). It defines the missing instrument-workshop throughput
modifier type and uses a separate building-map initialization key. No balance
constants, stable output or published beta files changed.

This integration has **76 passing engine assertions across two additional suites**:
24 focused checks and 52 goods-collapse/recovery checks. Keep this count separate
from the base-mod audit total. All 46 Python tests pass. Default generation exactly
matches beta5; candidate_02's patch bytes exactly match tested candidate_01. Live
sidebar, journal and native goods Finance navigation passed, including selected
tabs, native Market transitions and Morgenroete's CMF Sports panel transitions.
The UI seed predates Morgenroete and emits missing Morgenroete-variable errors;
the classifier's upstream-error labels do not establish vanilla responsibility.
The new goods' individual UI rows and an existing Morgenroete-save migration
remain release checks. This does not verify the reporter's full playset.

Candidate archive SHA256:
`63f0399db4a0866480ca19556cf6ad165685265d96b8024b9aefde3003e25c08`.
Not published; targets beta 1.0.4-beta.5 only. Build/maintenance instructions are
in `compatibility/morgenroete/README.md`; exact results and rejected fixtures are
in `tests/mechanics/verification_morgenroete_beta104_5.json`.

User-requested navigation cleanup: local unpublished beta 1.0.4-beta.6 removes
the Open Finance button and its spacer from individual goods views. Live CMF
checks confirm the Grain panel retains its interest/risk/intervention row above
the chart, the sidebar opens Finance, native Market replaces Finance, and the
journal shortcut still selects Speculation. Full logs have zero blocking mod
diagnostics. The 45 remaining Python tests and nine CMF checks pass; the obsolete
goods-button test was removed. Rebuilt CMF and Morgenroete patch files are
byte-identical to their prior versions. No gameplay or balance changes, stable
output unchanged, no Workshop upload. Evidence:
`tests/mechanics/verification_goods_navigation_beta104_6.json`.


## Depression choice population and political effects (1.0.5 beta)

75 new engine assertions pass on unchanged **1.0.5-beta.1**, bringing the base audit to **644 assertions in 56 suites**. This is separate from the Morgenroete integration count. All 17 option bodies were extracted unchanged from the frozen beta. The suite compares radicals and loyalists in every state and each stratum against direct native-engine effects, including unaffected populations. It checks all intended political modifiers and their absence on the other seven interest groups. Six nonzero oracle checks prevent empty-population passes.

A deliberate mutation in a disposable test copy rerouted relief-work loyalists from lower to middle strata and its IG modifier from Trade Unions to Armed Forces. Exactly the expected three assertions failed; the other 72 passed. Both complete logs have zero blocking mod/harness errors. This confirms detection of those injected faults; it is not a production bug. No gameplay change, beta rebuild or Workshop upload was needed. The 45 Python tests also pass.

Evidence: `tests/mechanics/verification_depression_social_105.json`. Raw runs: `runs/sweep_depression_social_105_r1` and `runs/sweep_depression_social_105_mutation`. Option-button UI, random event frequency, aggregate IG approval values and modifier expiry remain outside this suite.
