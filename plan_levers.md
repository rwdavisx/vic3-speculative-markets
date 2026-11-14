# Exchange levers: implementation plan (2026-11-11, plan only, nothing built)

Source: design_levers.md (merged proposal) + design_levers_a.md (detail). Anchors are today's files (generate.py is
2080 lines, not ~1960). "c." = centres.py, "g." = generate.py, "mt." = market_tab.py.

## Decisions

**(a) Vehicle for Exchange Rules: a mod policy row in Budget > Banking, built from the Credit Policy pattern.**
- Decrees (common/decrees/00_decree.txt:1-8) give only a static *state* modifier, an Authority cost and unlock lists:
  no effect block, no 12-month delay, no lock (the player can revoke any time), and three exclusive choices would need
  state_trigger tricks. Our multipliers are country script values, so a decree would also need a capital-state read.
- Credit Policy already has the whole shape: STANCES (g.217), spec_can_stance_* triggers with custom_tooltip reasons
  (g.1471-1483), spec_sgui_* (g.1500-1506), set_level_bar_item buttons (mt.640-663). Copy it with a pending timer.

**(b) Unverified reads, checked against vanilla 1.15 (game/common):**

| Read | Exists? | Evidence | Use |
|---|---|---|---|
| Company prosperity | yes, company-scope trigger `prosperity >= N` | common/achievements/ip2_pivot_of_empire_achievements.txt:13-14 (`any_company = { prosperity >= 100 }`) | Phase 4/5. Scale assumed 0-100 (only >= 100 seen): log it before tuning |
| Company owned levels | yes, `company_owned_levels` in company scope | common/script_values/ep2_japan_values.txt:279-283 (`every_company` ... `add = this.company_owned_levels`) | not needed; `num_companies` (common/alert_types/00_alert_types.txt:120) not needed either. Cut |
| Institution level | yes, `institution_investment_level = { institution = X value = N }` | common/achievements/base_achievements.txt:208 | only for the dropped Social Security link. Cut |
| Industrialists modifier | yes, `interest_group_ig_industrialists_pol_str_mult` | common/amendments/00_amendments_enactment_04.txt:39; common/company_types/00_companies_cots.txt:445 | Phase 5, default 0 (see Q2) |
| Trade Centre levels | yes, `building_trade_center` | common/buildings/11_private_infrastructure.txt:334; level read as vanilla_ties.levels() already does for Financial Districts (`b:X.level` in every_scope_state, vanilla_ties.py:29-32) | Phase 4 |

## Conventions for every phase

- One switch per phase, each `= centres.ON and tuning.get(..., 0)`: `EXCH_BRAKE_ON`, `EXCH_RULES_ON`, `EXCH_PLEDGE_ON`,
  `EXCH_ISSUE_ON`, `EXCH_EARN_ON`, `EXCH_LINKS_ON`. Default 0 while in development; flip the default to 1 only after
  the phase's acceptance passes. Hooks follow c.43-47: a string that is `""` when off.
- Tunables via `tuning.get`, names `EXCH_*` (c.31-39 style), dicts keyed by stance like `EXCH_HYPE`.
- Log fields go in `centres.LOG` (c.46) and use `ScriptValue`, never `Var`, for anything that can be unset (cycle.py:46:
  an unset Var ends the log line).
- New loc lives in centres.loc()/_exch_loc() (c.519, 572), i.e. generated; English only, other languages show missing
  (expected, design_exchange.md:62). No new concepts (ponytail: plain text in tooltips; add a concept if three or more
  places start linking it).
- No change to debt.py, debt_run.py or anything Sovereign Debt / Hot Money / Foreign Lending.

**Off-identity check (every phase).** Once, before Phase 1: build today's mod to a baseline folder twice and diff the
two (proves the build is deterministic). After each phase: build with every new switch 0 and diff against baseline.
```
$env:SPEC_MOD_OUT="G:\GameDev\_claude_scratch\vic\base"; py -3 -B tools/generate.py
$env:SPEC_MOD_OUT="G:\GameDev\_claude_scratch\vic\off"; $env:SPEC_TUNING="G:\GameDev\_claude_scratch\vic\off.json"; py -3 -B tools/generate.py
py -3 -c "import filecmp as f,sys;a,b=sys.argv[1:];d=lambda c:c.diff_files+c.left_only+c.right_only+[x for s in c.subdirs.values() for x in d(s)];r=d(f.dircmp(a,b));print(r or 'IDENTICAL')" G:\GameDev\_claude_scratch\vic\base G:\GameDev\_claude_scratch\vic\off
```
off.json = `{"EXCH_BRAKE_ON":0,"EXCH_RULES_ON":0,...}` (SPEC_TUNING replaces tools/tuning.json; there is none today).
Must print `IDENTICAL`. on.json sets the phase's switch to 1.

**Standard static checks (every phase):** `py -3 -B tools/centres.py` prints `ok`; `py -3 -B tools/generate.py`;
`py -3 -B tools/check.py` ends in `OK` (with on.json and with off.json).

**Standard short sweep:** both arms built with `--log` to their own SPEC_MOD_OUT, started from the same save, 10 years:
`py -3 -B tools/sweep.py --name <ph> --games 3 --jobs 6 --save G:\GameDev\_claude_scratch\vic\saves\base115_mod_1_1865.v3 --until 1876.1.1 --arm off=<off build> --arm on=<on build>`,
then `py -3 -B tools/analyze_cycle.py runs/sweep_<ph>/<arm>_<n>/telemetry.log` per game. 20-year runs only for the
final balance pass (Phase 6).

## Build order

| Phase | What | Depends on | Files |
|---|---|---|---|
| 0 | Find why Exchange on had 261 panic starts vs 481 off | none | analyze_cycle.py |
| 1 | Brake (credit out of score; rank gives credit limit only when Sound) + Exchange Rules | 0 | centres.py, leverage.py, generate.py (2 one-line hooks), market_tab.py |
| 2 | Stand Behind the Exchange (pledge) | 1 (its block) | centres.py, generate.py (3 hooks) |
| 3 | Float a Great Issue | 1 | levers.py, exposure.py, generate.py (1 hook), centres.py (boom_end only) |
| 4 | Known for, earned by building | 1 | centres.py (_standing, events, loc), vanilla_ties.py, notify.py |
| 5 | Cross-links (trust -> mood/recovery, Bad Debts freeze, prosperity -> mood, Industrialists) | 1, 4 | centres.py, generate.py (2 hooks), leverage.py |
| 6 | Balance pass, 20-year paired sweep, flip defaults | all | tuning defaults only |

Serial: 0 -> 1 -> ... -> 5 -> 6. Parallel after Phase 1: **2, 3 and 4 can be built by different people at once** if
they keep to this ownership (no git here, so a shared file is edited only inside the owner's functions):
- Phase 2 owns c.values()/_exch_values, c.PANIC/PANIC_OVER, new c.pledge_*(); in generate.py only g.440, g.1199, g.1402.
- Phase 3 owns levers.py, exposure.py, c.boom_end (c.60-66); in generate.py only g.663.
- Phase 4 owns c._standing (c.150-262), c.events (c.385-426), vanilla_ties.py, notify.py.
- Shared, coordinate by hand: c._exch_loc (each phase adds its own loc keys in a separate function), centres.LOG,
  the Exchange block in mt.banking_body. Phase 5 must be serial (reads Phase 4's tallies, touches g.875-885).

---

## Phase 0: why the Exchange halved panic starts (before adding anything)

Facts: runs/sweep_exchA and sweep_exchB have one off and one on game each (1 game per arm: noise is unknown).
Candidate causes, from the code:
1. Flight: International+ receive capital flight x2/x3 and count as safe havens without being Great Powers
   (c.34, diplomacy.py:55-56, 89-110). More +confidence right when neighbours panic.
2. Hotter booms (c.33, hype x1.05-1.15) should raise panics, not lower them: if on has fewer, look elsewhere.
3. Run noise: a different world after the first divergent roll.
4. Trust feeds only the score (c.76-98), nothing that drives confidence: unlikely to touch panics.

Steps:
1. Noise floor: rerun the pair from a save, 3 games each, 10 years (standard sweep, arms = today's build with
   `EXCHANGE_ON` 0 and 1). Also off-vs-off: the spread between the 3 off games.
2. Add `--why` to analyze_cycle.py (one function, ~30 lines): for each panic start (panic 0 -> 1), record that
   month's and the prior 3 months' `d_foreign`, `d_boom`, `d_crash`, `d_mood`, `d_burst`, plus `stand`, `trust`,
   `lev`, `debt`, `gdp`. Print per file: starts split as contagion (start month `d_foreign` <= -5) vs home-grown;
   starts by `stand` 0/1/2/3; sum of positive `d_foreign` (flight received) by `stand`; mean `hot` and `expo`;
   the 10 tags with the largest start-count difference between the two files.
3. Read: if contagion starts fall and positive `d_foreign` at stand >= 2 rises, cause = flight. Fix candidate:
   `EXCH_FLIGHT` {2: 1.5, 3: 2} or keep flight to Great Powers only (owner call, Q5). If on-vs-off gap is inside the
   off-vs-off spread, cause = noise; record and move on.
Acceptance: a short note in JOURNAL_STATE.md with the per-arm table and the named cause; no generator change.

---

## Phase 1: brake + Exchange Rules (one real decision)

### 1a. Brake (`EXCH_BRAKE_ON`)
- c.89-98 `spec_centre_size`: when BRAKE, drop the `add = var:spec_debt` block. Score = 6 months of pool income x
  trust x Rules (below). Update c.531-533 concept text ("A market's score is 6 months of Investment Pool income,
  counted at half ... ") under the switch.
- Rank gives credit only while Lending Standards are Sound or stricter: new value in c._exch_values
  `spec_exch_limit` = 0; if `has_variable = spec_centre_rank` and `var:spec_lax < LAX_CUTS[2]` (0.6, the same cut
  c._trust uses at c.142): `value = PLACES + 1 - rank` x `EXCH_LIMIT_STEP` (1 month), so +5 months for first place.
- leverage.py:115-117 `limit()` gains `extra=""` appended before the closing brace; g.411 passes
  `centres.LIMIT_REF` (`"\tadd = spec_exch_limit\n"` or ""). Without LEV_ON there is no limit: no link (ponytail:
  intended, LEV_ON 0 is a test build).
- Credit-limit tooltip: one AddLocalizationIf line "Our place among the Financial Centres: +N months, while Lending
  Standards are Sound or stricter" in the leverage row loc (SPEC_EFFECT_LEV_TT).

### 1b. Exchange Rules (`EXCH_RULES_ON`)
State: `spec_rules` (-1 Strict, 0 Ordinary, 1 Open; unset = Ordinary), `spec_rules_next`, `spec_rules_wait`
(months to take effect), `spec_rules_lock` (months locked). Script value `spec_rules_value` (as g.547).
Tunables: `EXCH_RULES_WAIT` 12, `EXCH_RULES_LOCK` 36, `EXCH_RULES_SCORE` {1: 1.25, -1: 1},
`EXCH_RULES_HYPE` {1: 1.1, -1: 0.9}, `EXCH_RULES_CREDIT` {1: 1.1, -1: 0.85}, `EXCH_RULES_DRIFT` {1: 1, -1: -2}
(extra quiet-month Lending Standards drift, in units of cycle.py's 1/240: Open doubles it, Strict reverses it),
`EXCH_RULES_TRUST` {-1: 1} (extra trust a quiet month). Cut from A: Industrialists +-1, Interventionism halving the
wait (ponytail: add if playtests want a political cost).

Script (all centres.py):
- c._by_stand (c.116): add `var="spec_exch_stand"` param (default keeps output identical); build `spec_rules_score`,
  `spec_rules_hype`, `spec_rules_credit` with `var="spec_rules"`.
- Hooks: `HYPE_REF` (c.43) also multiplies `spec_rules_hype`; `CREDIT` (c.44) also `spec_rules_credit`;
  `spec_centre_size` multiplies `spec_rules_score`. These already reach g.384 and g.417/419 (no generate edit).
- c._trust (c.134-147), inside the existing not-in-panic block: (1) extra drift
  `change_variable spec_lax add = drift/240` then clamp 0..1 (cycle.ON only); (2) Strict: `_gain(EXCH_RULES_TRUST)`;
  (3) timers: count `spec_rules_wait` down; at 0 set `spec_rules = spec_rules_next`, `spec_rules_lock = 36`,
  toast `spec_rules_done` for the player; count `spec_rules_lock` down and remove at 0. Timers count in panics too
  (put them outside the panic block). (4) Open without Laissez-faire (`has_law = law_type:law_laissez_faire`) falls
  back to Ordinary at once, no lock. (5) AI rule, `is_player = no`, only when no wait and no lock:
  - Lending Standards Lax or Reckless (`spec_lax >= 0.6`) -> Strict;
  - Strict or Cautious (`spec_lax < 0.4`), Laissez-faire, `spec_conf >= 40`, not in panic -> Open;
  - otherwise -> Ordinary. Only sets `spec_rules_next` if it differs from `spec_rules_value`.
  ponytail: ranking pass is global monthly (c.361), so AI and timers live there, not in g.1066.
- Effects `spec_rules_to_open/ordinary/strict`: set next, wait = EXCH_RULES_WAIT.
- Triggers `spec_can_rules_<k>` copied from g.1472-1482: `has_technology_researched = banking`; custom_tooltip
  "This is not already the rule" (`NOT spec_rules_value = n`); "No change is waiting to take effect"
  (`NOT has_variable spec_rules_wait`); "The rules have not changed in the last 3 years" (`NOT has_variable
  spec_rules_lock`); Open adds "Needs Laissez-faire".
- sguis `spec_sgui_rules_<k>` as g.1501-1505. c.build() (c.429) writes them to
  common/scripted_triggers/spec_centre_triggers.txt and common/scripted_guis/spec_centre_sguis.txt only when ON
  (new files: off build unchanged).

UI (Budget > Banking):
- mt.640-663: extract the set_level_bar_item loop into `level_items(icons, current, sg_prefix)`; Credit Policy calls
  it with today's arguments (output must stay byte-identical: the off diff proves it).
- mt.1297: when RULES_ON, a second block after Credit Policy:
  `block(header("SPEC_H_EXCH", "SPEC_EFFECT_EXCH_VALUE", "SPEC_EFFECT_EXCH_TT", ...), centres.rules_row())` via
  `__import__("centres")` as at mt.685, and drop "exch" from the rows at mt.685 (it moves into this header).
  `rules_row()` = a `tax_exp_frame_coin` as mt.686-709: upper text "Exchange Rules: Strict", lower text
  "Becomes Open in 7 months" / "Locked for 22 more months" / "Can be changed", three level-bar buttons
  (budget_set_very_low / medium / very_high, Strict / Ordinary / Open). Buttons are always visible; disabled
  ones show the trigger's reasons (as SPEC_STANCE_*_WHY, mt.1503-1507).
- Tooltip (each button adds its own numbers below a delimiter):
  1. "Exchange Rules decide how our banks behave for years; Credit Policy decides this year's lending."
  2. "Open brings more dealing and credit, but banks grow careless twice as fast. Strict makes banks careful and builds trust, with a little less credit."
  3. "A change takes 12 months to take effect, and then the rules cannot change for 3 years."

Telemetry (c.46): ` rules=[ScriptValue spec_rules_value] rnext=[ScriptValue spec_log_rnext] climit=[ScriptValue spec_credit_limit] elimit=[ScriptValue spec_exch_limit]`.

Acceptance:
- centres.py self-check: new strings brace-balanced; a model of the timers (choose at month 0 -> in effect at 12 ->
  next choice allowed at 48); BRAKE: `"spec_debt" not in values()`; RULES: `script.count("spec_rules_next") >= 4`.
- Off diff `IDENTICAL`; generate + check `OK` with on.json (both switches 1).
- Short sweep: (i) among countries with Banking, each rule holds >= 5% of country-months (the AI uses all three);
  (ii) `elimit > 0` only in months with `lax < 0.6` (grep, must be 0 violations); (iii) correlation of `cscore` with
  `debt` falls versus off; (iv) Balance guard limits below.

---

## Phase 2: Stand Behind the Exchange (`EXCH_PLEDGE_ON`)

State: `spec_pledge` (set), `spec_pledge_leave` (months of notice left), `spec_pledge_broken` (count, telemetry).
Tunables: `EXCH_PLEDGE_PANIC` 0.25 (trust share lost at a panic start, instead of 0.5), `EXCH_PLEDGE_FLIGHT` 1.5,
`EXCH_PLEDGE_COST` 0.75, `EXCH_PLEDGE_NOTICE` 24, `EXCH_PLEDGE_DEBT` 0.5, `EXCH_PLEDGE_BREAK` {conf: 15, legit: 10}.
- c.69-71 PANIC: HALF becomes a value `spec_exch_panic_cut` (0.5, or EXCH_PLEDGE_PANIC with the pledge). Off: the
  literal stays.
- c.129 `spec_exch_flight`: tail `if has_variable spec_pledge multiply 1.5`.
- g.440 `spec_rescue_share`: add `centres.PLEDGE_COST` hook (`multiply = spec_pledge_cost`).
- g.1199 after the panic event: `centres.PLEDGE_RESCUE` = `if = { limit = { has_variable = spec_pledge spec_can_rescue = yes } spec_rescue = yes }`.
  The automatic rescue always pays, borrowing if needed (ponytail: no "cannot pay" case; default is the break).
  The event's rescue option is then already disabled by `spec_rescued` (g.1491-1493).
- Break, in the ranking pass: pledged and `in_default = yes` -> trust 0, `spec_cool_conf` 15 (g.1440), legitimacy
  -10 timed modifier `spec_pledge_broken` (5 years), remove pledge, toast. Leaving: button starts notice; at 0 remove.
- Gate (triggers with reasons): Banking; Standing National or higher; `scaled_debt <= 0.5`; not in panic; not
  already pledged. Withdraw: pledged and no notice running.
- UI: one vanilla button in the Exchange block under the Rules row, same style as the rescue button (mt.620-628):
  "Stand Behind the Exchange" / "Withdraw the Pledge" / disabled "Withdrawing: 14 months left".
- Tooltip:
  1. "Promise to rescue our banks in every panic: the rescue comes at once and costs a quarter less."
  2. "A panic then costs a quarter of the Exchange's trust, not half, and half again as much capital flight comes to us."
  3. "If we default, the promise is broken and trust is lost; withdrawing it takes 24 months' notice."
- AI: pledge when Standing >= National, `gold_reserves >= spec_rescue_cost`, `scaled_debt < 0.3`, not in default;
  give notice when `scaled_debt > 0.4` or gold below one rescue.
- Telemetry: ` pledge=[ScriptValue spec_log_pledge] pbroke=[ScriptValue spec_log_pbroke]`.
- Acceptance: self-check model (pledged panic leaves 3/4 of trust, unrescued case impossible while pledged);
  off diff IDENTICAL; short sweep: every pledged panic has `rescued=1` in its first month; AI broken pledges <= 1 per
  game; panic months with pledge on within the guard.
- In-game test (owner): rescue on the tick the panic starts; the event popup shows the rescue as done.

---

## Phase 3: Float a Great Issue (`EXCH_ISSUE_ON`)

Lives in levers.py: it is a goods-row button like Restrain / Encourage (levers.strip, levers.py:387).
State: `spec_issue_<g>` (`days = 730`), `spec_issue` (country: one at a time), `spec_issue_cool` (`days = 365`
after an issue ends, ponytail: stops AI chaining issues; drop if not needed).
Tunables: `EXCH_ISSUE_SCORE` 1.25, `EXCH_ISSUE_EXPO` 1.5, `EXCH_ISSUE_TRUST` 2 (multiplier on c.TRUST_END).
Cut from A: Industrialists +2 (same reason as Rules).
- Score: c.spec_centre_size multiplies `spec_issue_score` (1, or 1.25 while `spec_issue` set).
- Exposure: exposure.py:34 `spec_exp_mult_<g>` multiplies `spec_issue_expo_<g>` before its `max` (hook "" off).
- Boom end: c.60-66 `boom_end` applies `d` once more when `has_variable = spec_issue_<g>`, then removes
  `spec_issue_<g>` and `spec_issue` and sets the cooldown. An issue that expires without an ending does nothing.
- Gate: Standing National+, the good at Eager or hotter (`var:spec_word_<g> >= 5`, as cycle._hot), no issue, no cooldown.
- UI: a fourth item in the goods-row lever strip, built with levers._item (levers.py:354), always visible, disabled
  with reasons.
- Tooltip:
  1. "Stake the Exchange's name on this boom for 2 years: its score rises and banks lend more into the good."
  2. "When the boom ends, its effect on trust counts double: a gentle end earns twice, a bust costs twice."
  3. "One issue at a time, for a National Exchange or higher, on a good at Eager interest or hotter."
- AI (in levers.ai_block, levers.py:284): Standing National+, `spec_conf >= 40`, no issue or cooldown: float on the
  good with the largest `spec_weight_<g>` at Eager or hotter. ponytail: deterministic, no 30% roll; the cooldown paces it.
- Telemetry: ` issue=[ScriptValue spec_log_issue]` (1 while an issue runs) and the boom-end sev already in `end1..3`.
- Acceptance: self-check (doubled Correction +4, Bust -12, Collapse -36 from the default TRUST_END); off diff
  IDENTICAL; short sweep: share of AI issues ending Correction / Bust / Collapse reported; trust mean of issuing
  countries not below off by more than 10.

---

## Phase 4: known for, earned by building (`EXCH_EARN_ON`)

Replaces the one-off choice event (c.234-244 trigger, c.385-426 event): when EARN_ON the event file is not written.
- Yearly (ranking pass, `spec_exch_tally` timer `days = 365`): three tallies, each divided by its threshold:
  - Commodity Exchange: Trade Centre levels (`vanilla_ties.levels("building_trade_center")`), `EXCH_EARN_TC` 20;
  - Share Market: companies with `prosperity >= EXCH_EARN_PROSPER` (50) via `every_company` count, `EXCH_EARN_CO` 4;
  - Deposit Banks: months with `spec_lax < 0.6` outside panic, `spec_exch_sound` (reset by an unrescued panic),
    `EXCH_EARN_SOUND` 120.
  The largest tally at or above 1 sets `spec_exch_known`; below 1 everywhere keeps the current value (save
  compatible: chosen values stay until earned otherwise). Effects are the existing ones (c.37-39); no new effects.
  Cut from A: "+2% score per Trade Centre level" style bonuses (the known-for effects already reward it).
- UI: in the Exchange row tooltip (SPEC_EFFECT_EXCH_TT, c.608-616) three lines "Trade Centre levels: 12 of 20";
  a toast `spec_exch_known_new` (notify.py, pattern at notify.py:69-72) when it changes.
- Tooltip:
  1. "Our Exchange becomes known for what the country builds, checked once a year."
  2. "Commodity Exchange: Trade Centres. Share Market: prosperous companies. Deposit Banks: years of sound lending."
  3. "The one furthest past its mark wins; until one is reached, the Exchange keeps its name."
- AI: same rule, no choice to make; the AI "uses" it by building (vanilla AI already builds Trade Centres).
- Telemetry: ` ktc=[...] kco=[...] ksnd=[...]` (the three tallies x100, ScriptValue).
- Acceptance: self-check (tally model: ties keep current; all below 1 keeps current); off diff IDENTICAL; check.py
  OK with no missing loc for removed event keys; short sweep: `kco` is non-zero somewhere (proves the prosperity read
  and scale; if all 0, retune EXCH_EARN_PROSPER from a logged company prosperity probe); each known value appears.

---

## Phase 5: cross-links (`EXCH_LINKS_ON`, each link its own tunable, 0 = link off)

- Trust shrinks Market Mood: g.883 `spec_mood_scale` multiplies `spec_exch_mood` = 1.5 - trust/CALM
  (x1.5 at trust 0, x0.5 full). Tunable `EXCH_LINK_MOOD` 1.
- Trust speeds recovery: g.469 `spec_conf_recover` multiplies `spec_exch_recover` = 0.75 + 0.75 x trust/CALM.
  Tunable `EXCH_LINK_RECOVER` 1.
- Bad Debts freeze Standing: c._standing (c.178-211): while `spec_crunch > 0`, Standing cannot rise (keep
  `spec_exch_was` as cap) and trust -1 a month. Tunable `EXCH_LINK_CRUNCH` 1.
- Company prosperity leans mood: reuse Phase 4's `kco` tally: `spec_c_mood` add (kco - 1) x 0.2, clamp +-0.3.
  Tunable `EXCH_LINK_PROSPER` 0.2.
- Industrialists: `spec_exch_industry` static modifier, `interest_group_ig_industrialists_pol_str_mult = 0.05`,
  `multiplier = stand`. Tunable `EXCH_LINK_IND` 0 (off by default, Q2).
- Cut: World Centre nudges other exchanges' mood (needs a global read each month for a +-0.3 effect; add later if
  World Centre needs more weight). Social Security link (dropped in the proposal).
- Tooltip lines go into the existing Exchange tooltip, no new UI.
- Acceptance: off diff IDENTICAL; short sweep with each link on alone (5 one-tunable arms against links-off) for
  the guard numbers.

---

## Balance guard (paired sweeps, every phase; full 20-year pass in Phase 6)

Read per arm with analyze_cycle.py (+ `--why`) and sweep.py's world GDP. Set the noise band first (Phase 0, off vs
off). "Stop and retune" if any of these breaks, on the mean of 3 games per arm:

| Number | Field / source | Limit |
|---|---|---|
| Panic starts | `panic` 0 -> 1, per 100 country-years | within +-25% of off and outside the off-off spread -> stop; history band 3 to 5 per 100 (JOURNAL_STATE:68 has 3.9) |
| Months in panic | `panic=1` share | within +-25% of off; absolute 0.8% to 2% |
| Contagion share of starts | `--why` | moves > 15 points -> stop (flight / safe-haven effect) |
| World GDP at end | sweep.py `world GDP` | on/off within -1% .. +2% |
| Standing changes | `stand` transitions | mean <= 1 per country per decade; first place held > 15 of 20 years in 2 of 3 games -> runaway, stop |
| Credit | `debt`, `lev`, `climit` | top-5 markets' mean `lev` up > 20% or `debt`/GDP up > 25% vs off -> stop |
| Trust | `trust` | share of Banking countries at CALM (120) > 50% -> too easy |
| Rules use (P1) | `rules` | any rule < 5% of country-months among Banking countries -> AI rule broken |
| Pledges (P2) | `pbroke` | > 1 broken AI pledge per game -> tighten AI gate |
| Mania | analyze_cycle "months in mania" | within +-25% of off |

## Risks and open questions (with recommended answers)

1. **Rules and Credit Policy read as two overlapping dials.** Recommend: separate "Exchange" header block, first
   tooltip line says "years vs this year", and Rules never change this month's credit preview figure.
2. **Industrialists' political strength by Standing (verified modifier, big AI side effects on laws).** Recommend:
   build the link but ship at 0; turn on only after a sweep shows no rush of Laissez-faire enactments.
3. **What breaks the pledge?** Recommend: default only (`in_default`); the automatic rescue always pays, borrowing
   if it must. Simpler and visible; "cannot pay" has no clean vanilla read.
4. **Known-for: earned only, or still a choice?** Recommend: earned only, no popup, existing saves keep their choice
   until a tally reaches its mark. The event text can be reused later in the Finance window.
5. **If Phase 0 blames capital flight for the halved panics, cut it before the levers?** Recommend: yes, retune
   `EXCH_FLIGHT` to {2: 1.5, 3: 2} (or Great Powers only) first, then rebuild the baseline used by every off diff.

Not verified (needs the game): company prosperity's scale (only `>= 100` seen in vanilla); the automatic rescue on
the panic's first tick; the Rules timers through save and load; the Industrialists modifier showing in a country
modifier tooltip. Not planned: the Finance window (all new UI is in market_tab/centres functions that a window can call).
