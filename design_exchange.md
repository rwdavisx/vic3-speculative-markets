# The Exchange: a goal to build toward (trial, not uploaded)

Purpose: give the player something to want. Today the only goal is "avoid a panic".
Picture shown to the owner: `runs/shots/exchange_goal.png`.

## What already exists (reuse it, do not rebuild it)
- `tools/centres.py`: Financial Centres. Every month it scores each market (Investment Pool income + Outstanding Credit,
  times 0.5 to 1.5 by quiet months), scales the leader to 100, lists the top 5 (global vars `spec_centre_1..5`,
  `var:spec_centre_rank`), gives places a prestige / loan interest modifier, and posts gained / lost toasts (`notify.py`).
- `tools/diplomacy.py`: capital flight to safe Great Powers when a panic starts (`spec_capital_flight`, `spec_flight_mult`).
- `tools/cycle.py`: Lending Standards `spec_lax` (0 strict to 1 reckless), rescue and panic-over hooks, boom-ending hook `burn`.
- `tools/vanilla_ties.py`: `spec_fd`, `spec_depth` (Financial Districts).

## The rule set to add (all behind `EXCHANGE_ON`, default 1; with 0 the generated mod must be identical to before)
Extend `centres.py`. Keep the diff small. Tuning numbers via `tuning.get`, like `cycle.py`.

### 1. Trust replaces quiet months in the score
`var:spec_centre_trust`, 0 to CALM (120). Score multiplier becomes 0.5 + trust / CALM. `spec_centre_calm` and
"Years of Calm" stay as they are and stay truthful.
- Each month outside a panic: +1 when Lending Standards are Strict, Cautious or Sound; 0 when Lax; -1 when Reckless
  (always +1 when `cycle.ON` is 0).
- A boom's ending, for goods that matter to the market (the same gate `cycle.burn` / the boom-end toast uses):
  Correction +2, Bust -6, Collapse -18.
- A panic starting halves it. A panic ending without a rescue halves it again. (So Support the Banks keeps trust.)
- Starts from the existing `spec_centre_calm` value.

### 2. A standing for every market
`var:spec_exch_stand`: 0 Provincial, 1 National, 2 International, 3 World Centre. Set in the monthly ranking pass.
- World Centre: place 1. International: places 2 to 5. Both also need the gate below; without it the market is National.
- National: scaled score >= EXCH_NATIONAL (default 8), or listed. Some hysteresis so a market on the line does not flap.
- Provincial: every other market.
- Gate for International and above: the same condition that unlocks Credit Policy (central banking). Reuse that trigger.
- Effects by standing (one static modifier per standing, on top of the existing place modifier), all tunable:
  - booms run hotter: `spec_hype_mult` x 1.00 / 1.05 / 1.10 / 1.15. Because a boom's fall scales with its rise, the
    higher a market stands the more a crash costs it. That is intended.
  - capital flight received when another country panics: x 1 / 1 / 2 / 3. International and above receive flight even
    when not a Great Power, if that is a small change; otherwise only scale it and report.
  - a small prestige bonus for National (the listed places already have theirs).

### 3. What the Exchange is known for (the player's choice)
`var:spec_exch_known`: 1, 2 or 3. Chosen the first time a market reaches National, and offered again the first time
it reaches International and World Centre. AI picks at random. Kept if the market later falls.
1. Commodity Exchange: its booms run hotter still (`spec_hype_mult` x 1.10).
2. Deposit Banks: every loss of trust is halved.
3. Stock Exchange: +10% credit lent each month (the mod's own credit flow, as `cycle.CREDIT` does it).
The player chooses in an event written the way vanilla events are written. No button anywhere raises the standing.

### 4. Where the player sees it
- Budget > Banking, a row under Lending Standards (built like `SPEC_EFFECT_LAX` in `cycle.py`): the Exchange's name
  ("London Exchange": capital name + Exchange, if the engine can give the capital's name there, else "Our Exchange"),
  its standing and place, and a tooltip: score, trust, what it is known for, its effects, what the next standing needs,
  and in plain words what raises and lowers trust.
- Speculation tab, Financial Centres section: the listed rows and own row show standing.
- Toasts when the standing rises or falls. They replace the two existing Financial Centre toasts when EXCHANGE_ON.
- Player-facing nouns: "Exchange" for a country's market, "Standing" for its level; the list keeps "Financial Centres".

### 5. Telemetry and checks
- Add `stand=`, `trust=`, `cscore=`, `known=` to the monthly SPEC log line (see `cycle.LOG`).
- `py -3 -B tools/centres.py` self-check extended: brace balance, and a small model of trust (120 quiet months fill it,
  an unrescued panic leaves a quarter, a rescued one a half).
- `py -3 -B tools/generate.py` then `py -3 -B tools/check.py` must print OK. New English strings will show as missing
  in the other languages: expected, do not translate.

## Hard limits
- Do not touch Sovereign Debt, Hot Money or Foreign Lending (`debt.py`, `debt_run.py` and their strings).
- Do not start the game, upload anything, or delete folders. No git here.
- In script triggers, write numbers with at most 3 decimals (6-decimal literals fail to compare).
- Mod UI buttons stay visible and are disabled until usable. Text and layout must read like vanilla.
- Change nothing that this design does not need. Flag other problems in the report instead of fixing them.
