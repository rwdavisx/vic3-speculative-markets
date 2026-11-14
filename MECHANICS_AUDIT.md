# Mechanics correctness audit

Balance is frozen at 1.0.3. The first isolated pass now has **201 passing engine
assertions in 19 suites**, plus **38 Python tests** and **9 CMF source tests**.
These are contract results, not a claim that every possible campaign works.
The open checks below remain prerequisites to the broader balance pass.

**Published:** Beta 1.0.3-beta.5 at 06:10 UTC and stable 1.0.4 at 06:11 UTC on November 14.
Stable gameplay and UI bytes match the tested beta. See `HOTFIX_1.0.4.md` for receipts and hashes.
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
| Confidence | 20/40/60/80 bands, clamps, story deltas, panic modifier exclusivity | complete driver sum and monthly ordering under simultaneous shocks |
| Investor Interest | trend direction, reciprocal response, clamps, severity thresholds, peak decay, one ending per boom | all 49 goods and production-method combinations |
| Recovery | actual 90/180/360-day expiration, checks before and after each deadline in GBR/FRA/PRU | save/reload during recovery |
| Lending | safe/stressed leverage boundaries, policy ceilings, repayment bounds, zero credit, panic/Bad Debts blocks | exact pool cash transfers during simultaneous crises |
| Bank exposure | 60% new-loan allocation cap, dilution, conservation, empty/new credit, write-off once, restrained share | simultaneous endings in several goods and UI reconciliation |
| Lending standards | drift gates, crisis-loss floor, upper/lower bounds, action multipliers | long-run combinations of overlapping interventions |
| Overbuilding / construction / owners | supply-loss neutrality, doubled-supply amplification cap, construction tiers 4/5/6, small-boom exclusion, bonus removal | actual ownership-stratum radical counts, each building group and PM |
| Leverage / Bad Debts | ramp/fade/expiry, bailout lock cleanup, old-loan land-loss relief, repeated loss, new-loan exclusion, relief expiry | real secession/peace-deal integration beyond the controlled population cache |
| Financial Panic | minimum elapsed age, deadline, recovery, no repeated rescue, cooldown state, legacy clock migration | exact treasury cost and pledged-rescue/default paths |
| Credit policy / AI | same stance actions and cooldown, mania tightening, debt tightening, low-confidence loosening, recovery, fever/panic gates | technology-negative cases, government turnover and probabilistic rescue frequency |
| Goods interventions / Great Issues | eligibility, mutual exclusion, toggle/cancellation, shutdown, issue cooldown | actual cash cost and modifier duration through save/reload |
| Exchanges | actions/charters, pursuit ordering, pledge notice, monthly trust gates/cap, Bad Debts prevents promotion, seat ownership, annexed/missing ranks and rivals | Renown weight accounting, annual rival rewards, complete score/standing boundaries, pledge funding/default |
| Domestic economy / politics | growth bounds and stagnation, depth/trade multipliers, fixed AI temperament, mania goodwill, panic blame, cooling/cleanup | revolutions, government changes and exact affected pop totals |
| Foreign transmission / wars | real GBR-to-FRA hit, weaker hit cannot stack, stronger replaces, closed economy ignores; war-end live/missing opponent safety | multi-hop recursion/capital flight and actual war start-to-end campaign |
| Long Depression | join/tie gates, repeat join, crash phase deadline, own/world recovery, clamps, cleanup/history, delayed safety | spread chains, second crisis and all event-option paths |
| Journal / reforms / stories | stage priority, reform combinations, debt conversion and lock, delayed missing-source/shutdown safety, journal insertion | every inquiry/political movement branch and player tag switching |
| UI / notifications / localization | native beta5 and CMF beta4 journal/goods shortcuts select Speculation; native transitions; numeric posts; row alignment; static localization checks | filters/empty states at different UI scales and all translated languages live |
| Distribution | distinct IDs, frozen-source hashes, fixture exclusion, immutable beta archives, beta4/5 gameplay equality, regenerated CMF patch byte equality | beta-first promotion verified; see release receipts |

## Engine suites

| Suite | Assertions | Final evidence |
| --- | ---: | --- |
| banking | 13 | final_beta4/banking |
| confidence | 14 | final_beta4/confidence |
| contagion | 4 | final_beta4/contagion |
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
