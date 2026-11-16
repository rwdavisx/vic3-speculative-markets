# 1.0.6-beta.4: local candidate, not published

Home of Great Companies, steps 2 and 3 of `design_companies.md` (balance freeze lifted for this feature by the user,
November 15, 2026). Also contains the unpublished revolution-journal fix from beta.2.

- **Company Strength:** the honour scores the sum of our companies' prosperity / 20, not the count at 50+.
  The Share Market charter still uses the count.
- **Blue chips:** 24 months running at 70+ prosperity; 3 months running below loses it; +2 Company Strength each;
  a closed market keeps none. Shown as a count in the honour tooltip, all 11 languages.

Archive SHA-256: `e11e7a748a42cb309d4533c1fe24e8ecd01b050f16678e75dac803cf4032ff72`.
Intermediate beta.3 (Company Strength only, its gate failed once on `issue_reload`):
`310a442ab794e711f7d580e164f9673287c083225098628bef6763e0a2eff01c`.

## Automated gate

`runs/release_gate/blue_chips_106b4_r1/report.json`: all **68 suites pass, 996 observations**, 60 Python tests,
verified with `tools/release_gate.py verify` against this candidate. Includes the five-year campaign that crashed on
beta.2 (passed; the beta.2 crash stays unexplained) and three new suites:

- `company_strength` (5): strength = prosperity / 20, no companies scores 0, honour ranks by it,
  ties at least 90% rarer (live: 110 tied pairs before, 0 after, 11 countries).
- `blue_chips` (9): +2 strength exactly, 1-2 low months keep status, 3rd removes it, a low month resets the climb,
  the real monthly update applies the rules, a closed market clears them.
- `rival_large_network` (7), `exposure_transfer` (30): audit gaps, unrelated to this feature.

Red: beta.1 fails `company_strength` (2/5 plus engine errors); `blue_chips` cannot be prepared against beta.3
(the production block is absent).

## Test corrections (no production change)

- `state_transfer`, `exposure_transfer`: tracked the moved state object, which the engine merges away when the receiver
  already owns part of the region; now track the state region. Failed run kept: `runs/release_gate/company_strength_106b3_r1`.
- `company_strength`: "no ties at all" was wrong; exact equal prosperity can tie. Failed run: `runs/sweep_company_strength_r1`.
- `blue_chips`: first version used an invalid inline comparison (caught by the error gate). Run: `runs/sweep_blue_chips_r1`.
- `issue_reload`: diagnostic INFO logging added. It failed both one-day-margin expiry checks once
  (`runs/release_gate/company_strength_106b3_r2`) and passed 6 other runs. **Cause unexplained; open.**

## Not covered

- A real 24-month climb to 70+ (no company is near 70 early; the test sets the status directly).
- Live in-game look at the changed honour tooltip, and no blue chip badge on company rows yet.
- Panic confidence protection for blue chips (design substitute) not built.
- No Workshop upload was performed.
