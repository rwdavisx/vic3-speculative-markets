# Improvement design after 0.9.0

Written 2026-11-09 from three fresh-context reviews (player experience, engineering, simulation design).
I checked each main claim against the code; anything I could not check is listed under "Not yet measured".
Foreign Lending / Sovereign Debt / Hot Money is out of scope.

Guard rails for everything below:
- The mod must stay recognisable. Simulation changes are re-tuned to today's rhythm
  (about 66-70% of months Steady, 3-5% Mania, 2% Panic).
- UI changes go into the panels that already exist. No new windows.

## Stage A - fix before uploading 0.9.0 (all small)

| # | Problem | Fix | Where |
|---|---------|-----|-------|
| A1 | Panic event has a choice that is always worse. Pick "runs its full course" (Industrialists +2), then press Lend to the Banks: same rescue, no approval cost. | Put the approval cost inside the rescue itself. Reword option A as "No rescue for now". | events `spec_markets.2`, `spec_rescue`, `spec_sgui_rescue` |
| A2 | Speculative Excess says "above 70" in one tooltip and "above 75" in the journal. The real figure is 75. | One figure everywhere. | loc `spec_excess_from_conf`, `spec_heat_from` |
| A3 | Confidence strip says a panic starts "below 20". The real line is 25, rising to 65 with Leverage. | Tooltips quote the live panic line (the panic bar already does). | loc `SPEC_TIER_PANIC_TT`, `SPEC_TIER_WARY_TT`, `spec_panic_at` |
| A4 | The lowest band has three names (Panic, Shaken, Shaken Investors) next to the separate "Financial Panic". The rescue has five names. | One name each: band "Shaken", action "Lend to the Banks", result "Bank Rescue". | loc only |
| A5 | Changelog wording inside the game ("Now in the Budget panel"). Tab tooltip still lists Credit Policy. | Remove both. | loc L517-518, L221 |
| A6 | Two Workshop gallery pictures show buttons that no longer exist. | Retake `01_tab.jpg` and `11_journal.jpg`. Needs your go-ahead with the upload. | workshop/gallery |
| A7 | `check.py` cannot fail: it prints problems and exits 0. | Exit 1 on any problem. Add a release guard: no debug script in mod/, version matches in all three places. | tools/check.py |

## Stage B - clearer for the player (0.9.1)

| # | Problem | Fix | Size |
|---|---------|-----|------|
| B1 | Turning points pass silently: panic ends, bubble bursts, Leverage passes the safe line, Bad Debts can be bought up, a panic runs with the rescue unused. | Two alerts (rescue available, Bad Debts can be bought up) and three toasts. | Medium |
| B2 | Every Correction, Bust, Collapse or Feverish good toasts the player, however small the good. | Toast only goods above a share of the market's trade. Measure toast count first. | Small |
| B3 | No marker for the panic line on the confidence strip. | A tick on the strip at the live panic line. | Medium |
| B4 | Leverage is shown in "months" with nothing to anchor it. | Add an Outstanding Credit row on the Banking tab: "N = M months of investment pool income". | Medium |
| B5 | Four tooltips run past 800 characters. | Cut to the vanilla length; move history notes to the concept page. | Medium |
| B6 | Jargon: "glut", "Crashed", "Crashes turn severe" (means panics). | Use the panel's own words. | Small |

Keep as is: the "N from X" breakdowns, alerts that open the right panel, event text that names the player's goods.

## Stage C - a cycle the player can read and answer (1.0)

How it works today, in one line each:
1. Prices set a good's Investor Interest. Real.
2. Hot goods lift Market Confidence; ending booms cut it. Real.
3. High confidence makes banks lend. Mostly for show: the investment pool is already full in about three of four country-months.
4. Low confidence starts a panic that lasts a fixed time, then jumps back to 40.
5. Confidence never feeds back into interest, so a mania cannot feed itself.
6. Random Market Mood is the largest single push on confidence.

| # | Problem | Change | Risk | Sure? |
|---|---------|--------|------|-------|
| C1 | Random mood leads the cycle (about a third of all movement, and the top cause of a quarter of panics). The player cannot read or answer it. | Halve `MOOD_SHOCK` (1.5). Raise boom and crash weights to keep the panic rate. | Fewer panics until re-tuned. | High |
| C2 | Manias do not feed themselves. | Rising interest is multiplied by the confidence band (Wary 0.8, Buoyant 1.15, Mania 1.3). | More manias and bursts; needs tuning. | Medium-high |
| C3 | A panic is a clock: `PANIC_DAYS` 195, reset to 40, 12 months immune. The reset wipes out the rescue's +20. | A panic ends when confidence climbs back past Wary. Minimum 2 months, today's length as the cap, no reset. The rescue then shortens the panic. | Months in panic shift. | Medium |
| C4 | The smallest countries panic most (12.7 per 100 years under 3k GDP, 1.8 for the largest). Their panics spread. | Scale mood and panic eligibility by financial depth. | Fewer world panics. | Medium-high |
| C5 | Credit lands in a full pool, so Leverage matters only for the largest economies. | Lend only where the pool is under about 12 months of income; raise `CREDIT_SHARE`. | More great-power panics. | Medium - measure first |
| C6 | AI cannot buy up Bad Debts (player button only) and carries them for years. | A monthly AI roll for the same action. | AI recovers faster. | High |
| C7 | Choices with no real cost: Convert Debt (-50% loan interest, 5 years in 10), Buy Up Bad Loans (flat price), mania event option C (pays 1% of GDP and cools the mania). | Convert Debt -20% or priced by debt; bailout price rises with size; option C pays 0.25%. | Low. | Medium |
| C8 | Three confidence drivers move almost nothing (easy money, debt drag, limit). Investment penalties stack four deep. | Remove the three; cap the summed penalty. | Low. | Medium |

Reviewers disagree on Restrain. One: it costs Authority and output, a fair trade. The other: the levy is new tax income
and a restrained boom can never end, so a player leaves it on. Do not change it until the levy is measured against the lost output.

Order inside Stage C: C1 and C4 first (less noise), then C2 and C3 (the cycle itself), then re-tune once, then C5-C8.

## Stage D - under the hood (before Stage C)

| # | Problem | Fix | Size |
|---|---------|-----|------|
| D1 | No regression test. | Build to a scratch folder and compare byte-for-byte before and after any refactor. | Small |
| D2 | The game's own error log is the best scope check and is not used as a gate. | One short headless run before upload; require zero `spec_` errors. | Small |
| D3 | `generate.py` never empties mod/; `--log` can write debug script into the live mod. | Delete generated folders first; `--log` refuses the live folder. | Small |
| D4 | Country-wide multipliers are recalculated about 50 times a month per country. | Work each out once per month and store it. Estimated 37% less monthly script. | Small-medium |
| D5 | Log-only variables ship in the release. | Write them only in `--log` builds. | Small |
| D6 | Goods a market does not trade are still updated. | Skip them. | Medium |
| D7 | Three whole vanilla GUI files are patched at build time against game 1.15.0. | Record the game version built against; `check.py` warns on a mismatch. | Small |
| D8 | 20 unused tool modules, 12 GB of old runs, 97 stale translation keys. | Delete or archive. | Small |

Old runs show a game to 1906 takes about the same wall-clock time with the mod as without (94 against 96 minutes),
so D4-D6 are tidiness, not a slowdown players feel.

## Not yet measured

- Nothing in the reviews was seen in game.
- The simulation numbers come from an older AI-only test build (1866-1885), not 0.9.0. Take a fresh sample before Stage C.
- How often the player actually gets toasts (B2).
- Whether Restrain pays for itself.
- Game time at 0.9.0; cost of the Speculation tab per frame.

## Suggested order

A (then upload 0.9.0) -> D1-D3 -> B -> fresh measurement run -> C -> D4-D8 as convenient.
