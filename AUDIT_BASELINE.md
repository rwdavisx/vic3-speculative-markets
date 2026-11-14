# Baseline coverage pass â€” November 14, 2026

User requested one basic test for every remaining audit gap. This is a work ledger, not a pass certificate. Scope updated by the user: continue with Speculative Markets alone; stop Morgenroete/CMF/full-playset testing. Earlier compatibility evidence is retained separately. Balance remains frozen. Production fixes require a failing beta reproduction and a passing rerun.

| Area | Baseline to establish | Status |
| --- | --- | --- |
| Wars | Ally exits, later main peace; actual territorial settlement and finance state | 9 live assertions pass. PRU left May 12; FRA capitulated July 26. Normandy and Ile-de-France transferred. One earlier test-readout warning is explicitly recorded; raw log gate is not clean |
| Successors and saves | Revolution/secession, tag change, journal persistence, older-save load | 12 real revolution/secession assertions and 2 tag-change assertions pass. Older 1.0.4 campaign save runs to January 1843 with 7 existing invariant checks passing |
| Buildings | Representative farm, plantation, mine, port/whaling, art and factory ownership/PM paths | 23 building/PM and 70 ownership assertions pass; full log gates pass |
| Crisis chains | Repeated panic/intervention sequence and a branching treaty network | 14 engine assertions pass; full error gate passes |
| AI | Sample actual rescue rolls for all three temperaments; eligibility regression | Proven relative-weight defect fixed in local beta. 30,000 actual rolls pass, plus 14 eligibility/cash regressions |
| Event effects | Exact approval modifier values and timed expiry | 5 assertions pass, including 912-day presence and 915-day expiry; full error gate passes |
| UI | Live inquiry choices, all translated languages, additional UI scale | All 11 languages' upper Speculation panel checked at 120%; four Finance tabs and Exchange scrolling checked at 140%. Currency, free banking, lender, company law, Sound Finance reward and completed-inquiry dismissal clicked live |
| Compatibility | Reporter playset, old-bridge save migration, longer patched campaign | Removed from current scope by user; earlier migration/campaign results retained |
| Unresolved crash | Fresh unpatched/patched Morgenroete comparison with preserved crash/log evidence | Further MR investigation removed from scope; original crash not reproduced in completed comparison |

Record missing dependencies or unavailable original saves separately from test failures. Never mark a scope covered merely because the game launched.

Baseline coverage is established for every retained category. This adds 141 unique engine assertions across eight suites: **785 assertions in 64 base suites**. Another 21 existing assertions were rerun (AI eligibility/cash and the older-save invariants). The nine live-war assertions are included with the test-warning qualification above. All 46 Python checks pass, including isolation/fingerprinting of test-only uprising modifiers.

One production defect was proved: AI rescue entries were relative weights, but the skip weight stayed fixed. Intended cautious/balanced/bold rates of 15/30/50% became roughly 17.6/30/41.7%. The generator now changes the skip weight too, keeping the total at 100. Actual 10,000-roll samples per temperament changed from 1790/3046/4183 rescues to 1448/2996/5022. The original fails two frequency checks; the candidate passes all six. No balance constants were changed.

The fix is packaged as local **1.0.5-beta.2** under `beta/audit_baseline/`. It has not been uploaded or promoted. Stable `mod/` and published `beta/mod/` remain untouched. The archive hash is `3dd63dd19e8cd384e1bdb76350126c6cef616e26e5f5c02698600e85c8c4ec8a`. Only AI rescue gameplay differs from published beta; metadata and thumbnail also differ.

Evidence: `tests/mechanics/verification_baseline_105.json` records accepted run reports, manifests, hashes, rejected fixtures and UI evidence. Raw logs/screenshots remain under `runs/baseline/` and the named `runs/sweep_baseline_*` directories.

Limits: baseline coverage is not exhaustive. The successor test controls AI countries; player takeover of a revolution/secession is not covered. Every translated tooltip, every event button, every building/PM combination, multiple random seeds and full-length campaigns remain broader testing opportunities. An earlier successor run (`successors_r2`) exited unexpectedly on October 27, 1836. Its cause is unresolved; the completed corrected run reached March 31, 1837 without reproducing it. Rejected fixture failures are not production bugs.

Release follow-up: these tested fixes were promoted to stable 1.0.6 and beta 1.0.6-beta.1 and published November 14, 2026. See `HOTFIX_1.0.6.md`.
