# Speculative Markets

Victoria 3 mod. `tools/generate.py` writes it into `mod/`; `py -3 tools/generate.py --log` adds a monthly `SPEC` log
line per country for `tools/analyze_cycle.py`. Balance constants sit at the top of the tools' modules and can be
overridden from the tuner (see Tuner). Everything after "Calibration" is development history; where it differs from
"Version 0.6", Version 0.6 is current; where that differs from "Version 0.8", Version 0.8 is current.

## Version 0.8 (built, not uploaded): what changed from 0.7

`mod/` is now 0.8.0, built but not uploaded. Shipped 0.7.0 is in `snapshots/v0.7.0_workshop`. `generate.py` `VERSION` sets the version on the live build.

- Leverage: credit owed in months of pool income. Rules and reasons are in `tools/leverage.py`'s header. In short: +2%
  throughput a whole month, up to +24%, none in a panic or with Bad Debts; past 3 months the panic line rises from 20 to at
  most 60 at 12 months; a panic then leaves Bad Debts of up to 40 points (each -1% throughput, -2% investment, -0.25 a
  month), banks lend nothing until they clear, and a rescue does not clear them. The panic takes half of what is owed.
- A panic that starts above 20 drops confidence to 19.9, so it sits in the Panic band and not on the Wary line.
- Lending: 150% of pool income x (confidence - 60) / 40, capped at 40% of pool income, so the cap is reached at confidence
  about 71 under Normal credit. 0.7 reached 30% only at 100 and capped at 60%.
- Credit limit: 3 months of pool income, 3 more with each of three finance techs (0.7: 12 always). So most countries sit at or under the
  3 month safe line until Central Banking, which is also when the credit stance unlocks.
- AI: turns Tight past 3, 8 or 12 months by temperament, and stays Tight until half that. A Mania can carry it away (below).
- Saves from 0.7: on the first month, debt above 3 months of pool income is written down to it, with no penalty.
- Market Mood: `fixed_range` gives every country that updates on the same day the same roll, so each country's roll now
  also hashes its population and pool income (`spec_mood_roll`).
- Long Depression: earliest start rolled once a game, 1868 to 1878 (0.7: 1870).

Test status (2026-11-07): every game before that date ran with DLC off (the game could not reach Steam), including all
baselines. Never compare those with games from fin0 on, which ran with DLC on. `runs/checklist.json` has the release list.

### The fast rules model (tools/fastsim.py)

Runs confidence, panics, credit, leverage, Bad Debts, the bubble and the AI's stance on the inputs logged in real games, in
seconds. `fastsim.py check` tests it; `try` and `rank` test other values. It covers 38 dials, not the 190 in `workshop/values.html`.
Hype, wars, the Long Depression and interventions stay as logged, contagion only scales with the panic count, and there is no GDP.

- Month by month (about 43,000 country-months, current build): typical error 0 for drift, Tight, easy money, debt, leverage and
  bursts; no month where the rules called for a panic the game didn't start. Only 2 months tested the AI's Tight line.
- Whole games, values it never saw (panics per 100 country-years, played / predicted): prudent from mix 1.6 / 1.6; reckless from
  mix 3.2 / 2.5 and 3.2 / 2.7; mix from base, which has no Leverage, 1.9 and 2.4 / 1.8, debt 1.3 / 1.3 months. So it runs about
  20% low at the reckless extreme. Mix alone played 1.9 and 2.4, so differences under 0.3 mean nothing. It is replay on logged
  inputs, not independent prediction.
- Bubble values: an early test said it was four times too small. That test was wrong: tune7 and tune8 ran with no soft landing
  (their logs fit a heat cool of 1, not today's 0.9) and with booms at 0.64 and 0.72. On their real rules it gives 3.65 panics for
  tune8's played 3.83, and 2.89 for tune7's 2.62 the other way.
- `fastsim.py exam`: six older games with bubble lines from 72 to 80, sizes 0.15 to 0.25, Tight a cap or a pull, each predicted
  from every other on recorded rules, 30 predictions. Typical miss against guessing no change: panics 0.61 / 1.47, months in panic
  0.20 / 0.55, manias ending in a panic 5.2 / 10.6, Mania 0.97 / 1.33, months in Tight 1.75 / 1.22. Real and modelled change
  correlate 0.95 for panics and it finds about two thirds of the size. Mania: 0.52, a third of the size, so a rough guide. Tight
  fails, and it feeds hype, lending and debt: moving the AI's line so Tight shifts 2.6 points moves panics 0.4 and Mania 1.2, so a
  miss of 1.75 could be about 0.3 and 0.8. That stays inside history's range, but Tight is unsized. 18 of 30 panic predictions sit in a range that should catch 27.
- What fixed Mania: the logs lose 6.2% of reports in the current build and 2.6 to 3.7% in older ones while the game runs on, so
  `filled` rebuilds those months; the Mania event's hit of 10 or 5 confidence was missing; temperaments are 42/33/25 once the +20
  Cautious from most starting laws counts, which predicts the event choices played (46/33/21, played 46/35/19). Market Mood is
  exact: no tie to booms, confidence or stance, and countries don't share it.
- A foreign hit was the largest push behind 2 to 4% of panics, and scaling foreign hits changes the exam by 0.02. Bursts were the
  largest behind 37% in tune7, 58% in tune8, 25% in the current build. Contagion doesn't need a fuller model for this.
- The current build's logs are 20-year slices from saves: 1836 to 1856 twice, 1850 to 1870, 1864 to 1885. sweep_fin3's two logs were
  one game (same save, same seed), so `arm` drops the copy: 4 games, not 5. Compare them with tune8 by year, never "to 1869".
- The soft landing, from `exam` and a test of its own: tune6 to tune8 ran with no cooling (three in four bursts match their recorded
  size to 0.005 at a cool of 1, one in four at 0.995). tune8 has the same bubble as 0.8 but no cooling, so it isolates the dial.
  Same years, tune8 played less 0.8 played, against the model's cool 1 less cool 0.9: panics +0.86 / +1.12, +1.19 / +1.01,
  +2.74 / +1.60; manias ending in a panic +9 / +9, +13 / +6, +25 / +13 points. Supporting evidence, not a clean test: 2, 1 and 1
  games on the 0.8 side, overlapping stretches of one game on the other, and 0.8 has Leverage and a different history.
- Round values, so what we tell players is easy to say: drift 4.2% to 4%, Wary 34 to 35, booms 0.72 to 0.7, collapse 5.1 to 5,
  bubble from 74 to 75, income average 15.4% to 15%, Long Depression recovery 2.1 to 2 (50 months, not 48), Heightened 72 and 42 to
  70 and 45. Panic length 189 to 195 days: `spec_panic_months` rounds up, so 189 already ran as 7 months while the panel said 6. 195 keeps
  every law's months (4, 5, 6, 7, 8); 180 cuts one at x0.8 and x1, and 210 adds one at x0.6 and x1.2. Left alone: Encourage 2.2 (just above Keen at 2), 0.167 (one
  sixth), the war rows (parts of 0.6), thresholds no player reads.
- HEAT_COOL 0.9 to 0.98, a bubble losing 2% a month. Replayed on the 4 current build games, nothing adjusted: 3.46 panics, 1.35%,
  18%, Heightened 4.38, 1.74%, 25%, Mania 5.3%, debt unmoved. At the played values the same replay gives 2.60, 0.98%, 12%, Mania 5.3%
  and length 4.6, against 2.47, 0.85%, 12%, 4.7% and 4.2 played, so it reads Mania and length a little high. Not yet played. The
  real games bracket it: 0.9 played 1.8 to 3.1 panics and 6 to 18%, no cooling 3.3 to 4.6 and 21 to 31%. `PLAYED` in fastsim keeps
  what the logged games ran, so `check` and `exam` still replay them truly.
- Codex's second review (2026-11-07, static, before these fixes): 210 days added a month at x0.6 too; rescaling a modelled change by
  1 / 0.65 isn't valid, as noise in the real changes shrinks that slope and 30 linked comparisons give no multiplier that carries
  over; candidates mixed DLC-off games with a played figure from the current build; the reader and parity still used today's drift,
  hidden by the cache. All fixed or withdrawn, and a fresh parse gave identical `check` and `exam`. Still true: the reader rebuilds
  confidence from later drift and `kept` absorbs what's unexplained, so a close replay is weaker evidence than it looks. The exam
  doesn't leak the predicted game's answer.
- Credit limit: 3, 6, 9, 12 (`LADDER`), a step for each of Central Banking, then Investment Banks and International Exchange
  Standards in either order. In normal play it cuts medium crashes from 0.12 to 0.04 and changes nothing else visible, but of 37,490
  logged country-months 172 had Investment Banks and none Exchange Standards, so that is blindness, not safety. Stress test, every
  country given the limit and techs from the start and never tightening, throughput bonus less Bad Debts: 0.94, 1.31, 1.15, 1.04 at
  3, 6, 9, 12. Only part of the trade-off: no investment effects, no gain from what the money builds, and raw leverage, not the
  mod's land-adjusted figure. Twenty moods on four histories aren't twenty economies, and 6 to 9 improves one source game. Leverage
  averages about 2 months even so: lending needs confidence above 60 and panics halve debt. Flat income levels off near 10 months at
  30% and 3%; 1% income growth gives about 7.6.
- Bonus and danger doubled at the owner's call, higher risk for higher reward: +2% a month to 12 (was +1% to 8), danger to 12
  months (10), worst Bad Debts 40 (25), panic line up to +40 (+30), Bad Debts fade 0.25 (0.2), lending cap 40% (30%), so 12 can be
  reached. The curves match the old ones up to 10 months (24 points against 25; Severe still starts near 8.5 months), and the bonus
  overtakes nothing: a crash costs more than the boom pays from about 9 months. Nothing in fastsim limited the bonus: it reads
  panics, and the bonus doesn't feed them there, so it can't see what +24% does to an economy. Normal play is unmoved: panics 3.46,
  1.35% of months, length 4.76, Mania 5.30, 17.3%, leverage 1.30, average bonus 0.86 to 1.79. Riding to the limit: bonus less Bad
  Debts 1.90, 2.83, 2.69, 2.26 at 3, 6, 9, 12; severe 0, .06, .31, .84. The earlier verdict against 40% lending compared those riders
  with history's .3 to .5, which is for all countries, and normal play is still near 0.
- Bold AI now rides to 12 (was 10), and each Mania has a 50% chance (Bold) or 10% (Balanced) of carrying an AI away: it stops tightening
  until the Mania passes or a panic comes (`FEVER`). Without that, Bold's confidence rule stopped it long before the limit. With every
  tech from the start, severe goes .05 to .16 and medium .26 to .38, toward history's .3 to .5, and panics stay near 2.5; on real tech
  dates nothing visible moves. Telemetry logs `fever=`.
- Old games and the replay still use the old values (`PLAYED`). Lending from 55 is the strongest lever left (average bonus up about
  40%, panics unmoved), but it changes every country all game. tools/replay.py still models the old limit.
- Every dial it covers, swept across a real range, then wars, slumps, foreign panics, growth, business mood and government debt as
  whole groups: `workshop/model_status.html`. The other strong dials also move Mania, which sits inside history's 2 to 8.
- Against history, 0.8 played: panics 2.47 (2.5 to 5.5), months in panic 0.85% (0.8 to 2.5), length 4.2 (3 to 6), Mania 4.7% (2 to
  8), manias ending in a panic 12% (10 to 35). The first two and the last on the low side, which is why cooling moved.
- Leverage's rules barely change how many panics come (2.6 without, 2.7 with). They change how far debt runs: months past 5 of
  income 7.3% without, 1.6% with, and that is the 3 month limit before Central Banking: with a limit of 12 from the start, 6.6%
  and medium crashes go from 0.1 to 0.5.
- Moved 10% either way, these change nothing visible here: the 12 month limit, panic clawback, Rescue confidence (the panic's
  reset to 40 usually overrides it), easy money, stance cooldown. Bad Debts size and fade act on the economy, which it can't see.
- Codex's review (2026-11-07) found a wrong source share in one check, Leverage-off clawback, rescue odds (15 in 85, 30 in 100,
  50 in 120) and a boom fill off by a month, all fixed. Still open: Tight and Loose scale logged booms in a straight line, which
  can't reproduce thresholds; rescues ignore gold and debt limits; no land-loss relief; AI temperament is rolled at base odds.
- A country reports every 30 days, so some calendar months hold two rows, and a revolt's breakaway logs under the parent's tag on its own days. The reader slots rows by 30 days and keeps the larger country.
- The log's `panic=` is on or off, not months left. Finance techs aren't logged: Central Banking is inferred from stance
  changes, Macroeconomics from the drift, Investment Banks from `fin`, and Exchange Standards is a guess. The full logs stop near
  1885: of 520 countries, 11 reach Investment Banks, so the upper steps of a credit ladder can't be tested from them.

### How far to trust a test

Two independent reviews of the test method (2026-11-07) set these limits:

- Two 20-year games from one save differ by about 4.1% in world GDP by chance alone (`sweep_noise`), so four pairs can show
  harm of about 5% and no less. They can't show that one version beats another by 2%, which would take about 33 pairs.
- Severe crashes come in clumps, so four games can't settle a rate like 0.3 to 0.5 per 100 country years.
- Countries grouped by their outcome (leverage, crash) show what happened, not why: income falling raises leverage.
- `b_v080off` is not 0.7: it keeps the new Market Mood and Long Depression rolls. `b_v070` is `mod/` plus log lines.
- `tools/replay.py` freezes confidence and income, so it answers how far debt runs and nothing else. It can't rank values for
  panics, crashes or GDP. An earlier what-if that said safe, ruin and span barely matter was wrong: it held the list of
  panics fixed, though panics rise with leverage (about 6 per 100 country years at 3 to 4 months, 50 past 10, in lev7).
- AI countries stop near their limits, so ordinary games barely reach a severe crash, which needs 8.4 months at the current
  values. fin1's first game had no panic start past 3 months. Whether risk bites needs countries that ignore the limit.

Tests written before the results, in `runs/sweep_fin2/plan.json` and the first pair of fin1:

- Harm: 0.8 against a baseline on four starts (two from 1836, two from saves). Holds if the mean world GDP change is no worse
  than -4%, no pair is worse than -9%, the typical country no worse than -3%, living standards no worse than -0.3 points,
  and severe crashes no more than 1 per 100 country years.
- Risk: `b_hot`, a test build where a population hash splits countries for good: half never tighten, half tighten at 3
  months. Holds if the hot half reaches past 8.4 months, has clearly more severe crashes, its crashed countries end clearly
  behind its uncrashed ones, and the hot half doesn't beat the prudent half by more than chance (+5%).
- Any game that ends by itself gets looked at. A value changed after a failed test needs that test run again.

Risk test results (fin2, 2 games of 20 years, 40 largest countries, hot against prudent):

- Reached past 8.4 months: yes, 1% and 3% of hot months. Prudent 0% and 0.2%.
- Panics per 100 country years: 6.0 against 1.5, and 4.5 against 2.9, about 2.5 times as many. Medium crashes 7 against 1,
  severe 3 against 0.
- Hot against prudent growth: +1.4%, chance about 27%. Riding hot shows no gain.
- Crashed hot countries ended behind uncrashed ones: failed as written. They ended ahead (44 against 32, 64 against 53, 4
  and 6 countries). This was a poor test, since it compares outcome groups, which the list above warns about, and the
  countries that borrow hardest tend to be the ones growing fastest.
- The better measure, GDP against the median big country over the same years: a plain panic -2% after 1 year and -4% after
  3; medium crash -14% and -14%; severe -16% and -20% (3 crashes). By 5 years most were back level (7 crashes, wide spread).

No value changed: crashes clearly hurt for about 3 years and riding hot shows no gain, so nothing calls for one.

Over all 6 final-rule games (fin1 to fin3, one 1850 rerun, both hot games), for the infographic: panics per 100 country years
by the month's leverage were 2.2 under 1 month, 2.4 at 1 to 3, 3.8 at 3 to 5, 13.3 at 5 to 8, and 24.1 past 8 (5 panics in 21
country years). A plain panic costs about 1% against peers at 3 years here (85 panics), not the 4% of the hot games alone.

Harm test results (fin1, fin2, fin3; 20 years, 40 largest countries): all limits held.

| Start | Against | World GDP | Typical country | Living standards | Panics per 100 country years |
|---|---|---|---|---|---|
| 1865 save | `b_v080off` | +3.7% | -0.7% | +0.13 | 1.27 against 1.15 |
| 1836, a | `b_v070` | +11.7% | +7.1% | +0.34 | together 2.43 against 2.31 |
| 1836, b | `b_v070` | +0.7% | -3.0% | -0.05 | |
| 1850 save | `b_v070` | -1.3% | -3.1% | -0.22 | 2.79 against 2.18 |
| Mean | | +3.7% | +0.1% | +0.05 | |

No severe crash in any of these games. The chance range on the mean is about 4.7%, so this rules out large harm and shows no
gain. The 1850 start ran twice and the two came out almost the same, so they count as one. Migration from older saves: debt
written down to 3 months on load, no panic or Bad Debts from it. Mod errors in all these games: only the old
`spec_wp` war memory reading a country that no longer exists, which 0.7 logs too.

The live build was made from this source. It has changed since `b_v080` was tested: the full game `sweep_full2` tests build `b_big2`.

Game crashes: `b_v080` from the 1850 save crashed by itself on 24 February 1851 (fin2), with nobody at the computer, so not
every crash was a game closed by hand. Ten crash reports exist since 6 November, all EXCEPTION_ACCESS_VIOLATION inside
victoria3.exe, at three spots (last digits CEAB 6, 74F1 3, 8358 1). CEAB and 74F1 also hit builds from before Leverage
(`b_base`, `b_r2_AI_LOOSE-26`), so 0.8 did not bring them. The last script errors differ each time and are vanilla's. Whether
the mod plays any part is still open: no vanilla game has crashed, but too few have run to say.
Another at the CEAB spot: `b_early` (full4) from the start, 18 July 1855. 15 of 243 test games have crashed so far; the invalid country script errors just before it also appear in games that finished.
Six of the 12 crash reports on disk came within 8 seconds of the `NAVAL_BATTLE` loc error, three more within about 3 minutes (`b_early` twice: 8 and 5 seconds). The error comes from vanilla text; 148 of 237 games without a crash logged it too, so it marks the moment rather than proves the cause. Points to vanilla naval battle code, not proved.

## Version 0.6: how it works now

Each country runs the system on its monthly pulse while its economic system law allows speculation. Command economy
and cooperative ownership switch it off: every variable and modifier is cleared and the tab shows an off notice.
Coming back starts fresh at 55 confidence.

### Investor interest (per good)

48 goods and 45 buildings are tracked (`generate.SELLS`, `generate.UPGRADES`). Buildings that switch output follow the
average of their goods, counted once the tech is researched.

- Each month a fast (15%, `FAST`; was 30%, which let interest jitter month to month) and a slow (5%) moving average
  of the price's distance from base price in the country's market. Trend = 60 x (fast - slow) x hype multiplier. Interest (hype) = 1 + trend when rising, 1 / (1 - trend) when
  falling, kept within 0.05 to 20.
- Hype multiplier = economic system law (table at the end of this section) x credit policy (Tight 0.5, Loose 1.3)
  x Joint-Stock Companies (1.1) x depth (0.8 to 1.2).
- Each building's `ai_value` is multiplied by the interest of the good it sells, so private investors and AI
  governments both build toward rising prices. `ai_value` is only the base term of the AI's building score, so x20
  moved building by about +30%, not x20.
- Six interest words. Throughput applies to the good's buildings in that country (`companies.INTEREST_THROUGHPUT`,
  one `spec_investor_<g>` modifier per good):

| word | interest | price trend (fast - slow) at multiplier 1 | throughput | also |
|---|---|---|---|---|
| Feverish | 6 and up | +8.3% of base | +8% | lifts confidence; can end in a Collapse |
| Eager | 3 to 6 | +3.3% | +5% | lifts confidence; can end in a Bust |
| Keen | 2 to 3 | +1.7% | +3% | can end in a Correction |
| Calm | 0.5 to 2 | | 0 | |
| Doubtful | 1/6 to 0.5 | -1.7% | -5% | a glut holds a good here |
| Fleeing | below 1/6 | -8.3% | -10% | a Feverish boom that falls here Collapses |

Words hold near a cut (`WORD_BUFFER`, 4%): a good moves to another word only once its interest is past the cut by 4%
of it (above 1: x1.04 up, x0.96 down; below 1 the same on the 1/x side: /0.96 up, /1.04 down), else it keeps last
month's word, so Keen starts at 2.08 coming up from Calm and ends below 1.92 coming down. A good's first month (or its
first month traded again) takes the plain word. Boom endings (Correction, Bust, Collapse), booming (3 and up) and the
AI's lifting of a restraint read raw interest, not the word; throughput, the levers, the tab's bands and the AI's choice
of a Calm good to encourage read the word.

Logging camps, oil rigs and banana plantations get no interest throughput: the game has no throughput modifier for
those building types.

### Boom endings and gluts

A good's peak is its highest interest, drifting 3% a month back toward 1. The peak decides how the boom would end
(`generate.UNWINDS`):

| ending | peak needed | ends when interest falls below | confidence per point of peak above 1 | glut |
|---|---|---|---|---|
| Collapse | 6 (Feverish) | 1/6 (Fleeing) | 5.1 | 12 months |
| Bust | 3 (Eager) | 0.5 (Doubtful) | 2.5 | 6 months |
| Correction | 2 (Keen) | 0.5 (Doubtful) | 1.25 | 3 months |

- The loss is weighted by the good's share of the market's trade (full weight at 3%). A month's losses are summed,
  scaled by confidence / 55 x depth x steadiness, then capped at 40.
- After the ending the peak resets to 1 and the good is in a glut: interest is held at Doubtful (0.4) for the glut's
  months, and Encourage Investment is not allowed.
- If the country has a company whose building types make the good, those buildings also lose throughput: -10% for a
  year after a Collapse, -5% for 180 days after a Bust, -2.5% for 90 days after a Correction, each x1.25 per Corporate
  Charters and per Corporate Management. A Collapse replaces a running glut modifier; a milder ending leaves one alone.
  The modifier reaches every building of those types in the country, not only the company's.

### Market confidence

0 to 100, starting at and drifting back to 55. The monthly change:

- Booming goods: +0.72 per Eager or Feverish good, weighted by trade share, at most +3, then x steadiness and x the
  finance techs' boom size (see Financial research). None during a panic.
- Bubble bursts: with a Stock Exchange, each month at 74 or more adds confidence - 70 to the boom's heat; when
  confidence falls below 60, -0.2 x the heat, at most -40. A one-off jump, shown in the tab for the month.
- Boom endings: as above, at most -40.
- Foreign panics: a tied country's panic (Contagion); capital flight into a Great Power.
- Growth: 10 x (GDP against its average over about a year, less 2%), within -0.6 to +0.6 (`economy.py`).
- Business Mood: Industrialists' approval 10 or more +0.4, 5 or more +0.2, -5 or less -0.2, -10 or less -0.4.
- Easy Money: +0.2 under Loose credit.
- The Long Depression: its phase's pull, and partners' tariffs.
- Turmoil: wars by how each is going, -4 to +0.5 a month in all (`diplomacy.WAR_ROWS`), or a diplomatic play short of
  war -0.5; default -5; revolution -2. A war's end is a one-off: won +4, lost -8, drawn -1 at full stakes (`WAR_END`).
- Government debt: from principal at 50% of credit, down to -1 a month at the credit limit (not while in default).
- Market Mood: each month mood x 0.75 plus a random draw between -1.5 and +1.5 (`MOOD_KEEP`, `MOOD_SHOCK`), so a
  shift lingers for some months and gives swings of a year or more. Countries that update on the same day share the
  draw (the game's random numbers are per day), so mood moves in groups of 10 to 25 countries.
- Drift: 4.2% of the gap to 55.
- Tight credit takes 10% of its height above 60 each month (-2.5 at 85). The result stays within 0 to 100.

Bands (`market_tab.TIERS`), one modifier each (`generate.BAND_INVEST`, `BAND_RATE`):

| band | confidence | investment by Capitalists, Aristocrats, Shopkeepers | loan interest | also |
|---|---|---|---|---|
| Panic | below 20 | -20% | +20% | a Financial Panic starts here |
| Wary | 20 to 40 | -10% | +10% | |
| Steady | 40 to 60 | 0 | -10% | |
| Buoyant | 60 to 80 | +10% | | credit flows |
| Mania | 80 and up | +20% | | Financial District employees +1 SoL; mania event |

During a panic its own modifier carries the investment loss, so the Panic band keeps only its loan rate.

### Credit and repayment

- Above 60 confidence, outside a panic, not under Tight credit and not in the Long Depression's Crash phase, the
  investment pool gets (confidence - 60) / 40 x GDP x 0.05% x law x finance techs x credit policy each month.
- Finance techs: 0.5, plus 0.5 each for Stock Exchange, Investment Banks, Mutual Funds and Modern Financial
  Instruments (up to 2.5). Credit policy: Tight 0, Normal 1, Loose 1.6.
- Credit stays outstanding until repaid: 4% of it a month leaves the investment pool, never more than the pool holds;
  the rest stays owed. A panic calls back half of what is outstanding.

### Financial Panic and bank support

- Starts when confidence is below 20, unless a panic ended in the last 12 months.
- Length: 9 months x the law's panic factor x government trust (x1.2 at 0 legitimacy, x1 at 50, x0.8 at 100), rounded
  up. AI countries' panics are 30% shorter.
- Effects: private construction halved (half the law's own allocation is taken away); Capitalists, Aristocrats and
  Shopkeepers invest 40% less; Industrialists and Petty Bourgeoisie -2 approval; company throughput bonus -5%;
  Financial District employees -2 SoL; radicals among Capitalists (10%), Aristocrats (5%) and Shopkeepers (5%); half
  the outstanding credit is called back; labour, socialist, communist, corporatist and Bonapartist movements gain
  support for five years, decaying; no boom bonus and no credit.
- It spreads to tied countries (Contagion), and players tied to it get a toast.
- The panic event: let it run (Industrialists +2), support the banks, or blame the speculators (Industrialists -2,
  Trade Unions and Intelligentsia +2, lower strata loyalists).
- Support the Banks (Banking, once per panic, from the tab, the journal entry or the event): 3% of GDP from the
  treasury and the panic ends within 6 months; with Central Banking 2% and 3 months. The share is for a panic with 6
  months left, scaled by the months it has left (x0.5 to x2): about 3% early in a 9 month panic, 1% with 3 left; its effects are halved (private construction -25%, investment -20%)
  and confidence +15. Chosen in the event, Trade Unions and Rural Folk -2 approval.
- When it ends confidence is at least 40, and no new panic can start for 12 months.

### Mania

At 80 a warning event fires once, and again only after confidence has fallen below 65. Capitalists (5%) and
Shopkeepers (2%) become loyalists. Options: ride it (Industrialists +2), warn investors (-10 confidence, Industrialists
-1, Intelligentsia +2), or levy the speculators (1% of GDP into the treasury, -5 confidence, Industrialists -2). A long
or high mania (each month at 80 or more adds confidence - 70, 120 in total) gives the Orléanist movement support and
takes some from labour and socialist movements. Players tied to the country get a toast.

### Financial research

| tech | era | effect |
|---|---|---|
| Banking | 1 | Support the Banks, at 3% of GDP, the panic ending within 6 months |
| Stock Exchange | 1 | credit +0.5 of the base; booms' size +0.25 (from 0.7) |
| Central Banking | 2 | Credit Policy; Support the Banks at 2% and 3 months |
| Joint-Stock Companies | 2 | investors react more strongly to prices (hype) |
| Investment Banks | 3 | credit +0.5 of the base; booms' size +0.3 |
| Mutual Funds | 3 | credit +0.5 of the base; boom-ending losses x0.85 |
| International Exchange Standards | 4 | market and investment ties x1.25 (contagion and the Long Depression spread further); capital flight into a safe Great Power x2 |
| Macroeconomics | 5 | the drift back to 55 and a country's own Long Depression recovery x1.5 |
| Modern Financial Instruments | 5 | credit +0.5 of the base; booms and boom-ending losses x1.1 |

The boom and loss sizes show in the tab's Booming Goods and Collapsed Booms tooltips, the drift in Return to Baseline,
the rescue's cost and months in Support the Banks, the flight in Foreign Panics.

### Credit Policy

Needs Central Banking; can change once every 6 months.

| policy | interest | credit | confidence | approval of interest groups in government |
|---|---|---|---|---|
| Tight | x0.5 | none | -10% of the height above 60 a month | Intelligentsia +2, Industrialists -2 |
| Normal | x1 | x1 | none | none |
| Loose | x1.3 | x1.6 | none | Industrialists +2, Intelligentsia -2 |

### Market interventions

Per good, at most one of the two at a time. No tech needed; Authority is the only limit on how many.

- Restrain Speculation: interest held at Calm, so the boom can neither grow nor end while restrained, and its peak
  and risk fade. Producers' throughput -10%. The state collects a levy of 10% (`LEVY_SHARE`) of the country's weekly
  output of the good at base price (Additional Income). Allowed at Eager or Feverish, or when the boom's end would cost 2 or more
  confidence.
- Encourage Investment: interest at least Keen. Producers' throughput +10%. The state pays 20% (`SUBSIDY_SHARE`) of the
  weekly output at base price (Additional Expenses). Allowed below Keen and outside a glut.
- The levy is half the subsidy so that Restrain is not a money machine. Example: weekly steel output of 1,000 at base
  price 50 is 50,000: Encourage costs 10,000 a week, Restrain brings in 5,000 (both were 2,500 at the old 5%). The AI
  encourages only with a weekly surplus of twice the subsidy.
- Authority a month: half the good's vanilla consumption tax cost (100 where it has none), from 50% of that for a good
  with no trade share up to all of it at a 3% share. Steel 25 to 50, grain 125 to 250.
- Clicking the one in effect lifts it. Interventions do not change approval.

### Depth and steadiness

- Depth: Financial District levels as a share of all building levels. No districts 0.8, a 3% share 1.0, 6% or more
  1.2 (the cap). It multiplies interest and boom-ending losses, so its effect compounds.
- Steadiness: from the Manor House share of Manor House plus Financial District levels. At the typical 90% it is 1;
  more landed economies move less, more financial ones more, within 0.85 to 1.1. It multiplies the boom bonus and
  boom-ending losses.

### Contagion

When a panic starts, each tied country loses 12 x tie weight x reach x min(1, the panicking country's GDP / its own)
confidence at its next monthly update. Reach is the panicking country's rank: Great Power 1, major power (recognized or
not) 0.5, others 0.15 (`REACH`). A panic that starts within 90 days of a hit of 3 or more was caught, not home grown,
and passes nothing on (`CAUGHT_DAYS`, `CAUGHT_FROM`); if several hits arrive, the largest counts. Ties: same market 1, subject or overlord 0.8,
investment rights treaty 0.6 (both x1.25 with International Exchange Standards), a market relying more than 20% on
trade with the panicking market 0.4 (x1.5 free trade, x0.7 protectionism or mercantilism, x0.1 isolationism; none
under an embargo), and ownership from 10% of a country's GDP owned by the panicking country (`gdp_owned_by`, new in
1.15), growing to 0.9 at 30% (`OWNED_FROM`, `OWNED_FULL`). Other Great Powers at 40 or more, not at war, not panicking
and not hit gain up to 2 (capital flight, by the same GDP ratio).

Ownership tie, one 1836 to 1881 observer game (`runs/20261105_145118_v060_own`) against the 1.15 baseline: hits of 3 or
more rose from 8 to 40 country months, median confidence 51.3 (56.1), panic country months 933 (1342), GDP growth 3.31
(4.08). No Great Power panicked after 1868, so that game had no Long Depression, which accounts for much of the gap in
panics. The figures sit near the 1.14 run (52.5, 1681, 3.39), so no retune. Logged each year for Britain and at each
panic for the panicking country, 7 to 29 countries a decade were 10% or more owned, mostly subjects, with Spain, Serbia
and the Papal States among the independents.

### The Long Depression

- Starts when a Great Power falls into a Financial Panic, from 1870 on. That Great Power is remembered: a second can
  follow only from a different Great Power, 25 years after the first Recovery ends, and only in 50% of games (rolled
  then). At most two per game.
- Affected at the start: every country in a panic or whose panic began in the last year, and the origin's strong ties.
- During the Crash it spreads in chains. Each month every country that joined the month before passes it on once to
  its partners whose tie weight (as in Contagion) is at least `SPREAD_MIN` 0.5: a shared market and subject or overlord
  ties always, investment rights always (0.6), heavy trade only under free trade (0.6; protectionism 0.28 and
  isolationism 0.04 never), none under an embargo. A country reached joins once; one joining after the Crash does not
  pass it on. So it can reach a country four links away, and countries with few close ties escape it. The first Long
  Depression of the 40 year run (1845) reached only 5 of 310 countries.
- Phases, world-wide:

| phase | length | confidence a month | modifier |
|---|---|---|---|
| Crash | 4 months | -5 | investment -20%, loan interest +25%, construction -5%, Financial District SoL -2; no credit |
| Depression | until world recovery reaches 100, at most 60 months | -1 | investment -10%, loan interest +10%, construction -10%, trade quantity -10%, radicals and loyalists from SoL change +25%, Financial District SoL -1 |
| Recovery | 12 months | +0.75 | none |

- World recovery rises 2.1 a month in the Depression (full after 48 months with no choices). A country's own recovery
  rises 1 a month; when it is full that country moves to Recovery early.
- Affected countries in the Depression get an event about every 20 months (10% a month, 300 days apart): A Wall of
  Tariffs, Relief Works, Run on the Banks, The Currency Question, March of the Unemployed, Calls for Reform. Choices add
  to the country's own and the world's recovery (a Great Power's choice 3 or 6, another country's 0.5 or 1; some
  subtract), and tariffs cost tie partners 4 x tie weight, by the GDP ratio. Start and end events, toasts, and a
  journal entry for players.
- During a panic the phase modifier applies at half strength.
- Not yet seen in a run (see Calibration).

### AI behaviour

- Credit temperament, rolled once per country: Cautious, Balanced or Bold, weighted by ruler and heir traits and the
  economic system law. Lean = +8 Bold or -8 Cautious, +4 with Industrialists in government, -4 with Intelligentsia.
- Credit policy: Tight above 80 + lean (`AI_TIGHT`, the Mania line; 76 held the AI Tight 11 to 12% of months late); back to Normal below 65 + lean (at least 58); Loose below 40 + lean outside a
  panic; back to Normal at 60 + lean (at most 54) or in a panic.
- Bank support: with more than 3 months of panic left, not in default, debt under 60% of credit and the cost in gold
  reserves, a monthly chance of 15%, 30% or 50% by temperament.
- Restrain: at 60 confidence or more, the boom whose end would cost the most, if 5 or more, with twice its Authority
  cost to spare. Lifted once the peak is below Keen, or once interest without the restraint is below Eager and at
  least Calm.
- Encourage: while confidence is below the AI's Loose point, the most favoured Calm good, one at a time, if the weekly
  surplus covers twice the subsidy and Authority covers twice the cost. Lifted at the AI's back-to-Normal point, in a
  panic, in deficit or in default.
- Mania event choices are weighted by temperament.

### Speculation tab (Market panel)

Shown for the market the player trades in; another market's tab shows its owner's figures.

1. Confidence card: a ring gauge with the state icon, the band name (Shaken for the Panic band outside a panic), the
   value and this month's change (its tooltip lists every driver), a line on what the band does, and the band scale.
   Under it, when they apply: Booms at Risk (where confidence would fall if every boom collapsed this month, shown
   from a possible loss of 2) and Panic Abroad (the tied country, Wary or worse or in a mania, whose panic would cost
   the most). During a panic a block shows the loans called in, the months left and Support the Banks.
2. Credit Policy: credit lent this month in the header; a Tight, Normal, Loose level bar with the current policy and
   its status (lending, or why not; the cooldown; Central Banking needed); the investment pool; what a panic would
   withdraw.
3. Investor Interest (interest_list.py): interventions in use and their Authority cost in the header; a Filters
   section with vanilla's goods category filters and, under a divider, one Investor Interest filter per tier (one at a
   time, GetVariableSystem value spec_il_tier; the others dim); sort buttons (Goods, Investor Interest, Intervention);
   then one 52 px row per traded good in a fixed order (vanilla category order, then key), static per good
   (datacontext GetGoods('<g>'), visible while spec_word_<g> > 0; a category group with no row shown is hidden whole,
   so filtering does not move the sections below). A row copies vanilla's Interests list (strategic_region_panel.gui
   country_involvement_bar_with_label): the tier icon, as tall as the name and bar beside it; the tier's name and the
   price trend after it (hidden at 0%); vanilla's levels bar of six tier segments, the tiers below filled in their
   interest_board.HEAT colour with vanilla's white progressbar fill, the current one lit to spec_ui_pos_<g> with
   vanilla's glow and active level frame, the tiers above empty. While spec_ui_move_<g> is not 0, vanilla's changed
   value chevrons run through the lit part, right when rising, left when falling. Everything that depends on the tier
   sits in that tier's own widget, so a frame tests one tier's parts.
   `spec_ui_state_<g>`: 0 normal; 1 turning (a boom that peaked at PEAK_FOR_CRASH or more and fell below NEAR_PEAK of
   it): the icon pulses and the Fleeing segment pulses red as the collapse zone, whose tooltip gives the confidence a
   Collapse would cost; 2 the month a boom ended: the crash_risk icon fades in and shakes, the name reads Crashed and
   the bar flashes vanilla's red fill once; 3 recovering: the same icon, the name Recovering, the fills at half alpha.
   The Investor Interest sort button (GetVariableSystem flag spec_il_sort) shows the monthly word lists
   spec_goods_w<w> instead, hottest first and larger trade first within a word. A fixed row writes 117 data bound
   properties, of which a frame updates about 28.
4. Companies (company_section.py): one 64 px row per company, built from vanilla's pieces: the company type's art
   faint behind it (as the building browser sets a building type's), its icon and name, vanilla's prosperity line
   under the name (the bar with its changed value animations, the value and target, vanilla's tooltip), then a chip
   for each good its buildings make (the good in the round tinted frame, its tier icon, a recovering warning, and
   the throughput from interest plus intervention). Clicking a row opens the company.

Performance: the game re-evaluates every visible data-bound GUI expression every frame (vanilla's
`common/scripted_guis/scripted_guis.md` says so for scripted GUIs), and the tab used to cost about half the frame rate
(110 to 50 FPS). The tiles now read figures script stores once a month, only for players and market owners (the
countries whose tab can be seen):
- `spec_ui_good` (interest_board.ui_effect, from the monthly tab block): per traded good `spec_ui_bar_<g>` (bar fill 0 to
  1, within the good's word), `spec_ui_pos_<g>` (word - 1 + bar, v3's marker), `spec_ui_move_<g>` (-1, 0, 1), `spec_ui_badge_<g>` (1 when peak >= PEAK_FOR_CRASH and
  interest is below NEAR_PEAK of it), `spec_ui_state_<g>` (v3's row state: 2 if `spec_ui_crash_<g>` is set, else 3 if
  `spec_glut_<g>` is, else 1 if the badge is, else 0; generate.monthly's boom end sets `spec_ui_crash_<g>` = severity
  for 28 days, earlier in the same monthly block), `spec_ui_cat_<g>` (category, for the filters); per band
  `spec_ui_rows_w<w>` (tile rows, picking the label column's height variant).
- `spec_lever_ui` (levers.ui_effect, from `spec_update_levers`, which also runs on every toggle): `spec_ui_r_<g>` and
  `spec_ui_e_<g>` (2 on, 1 can be switched on, 0 neither) and `spec_ui_co_<g>` (the Companies chip's throughput %).
  The lever buttons no longer run the scripted GUIs' `IsValid` each frame; their tooltips still do (hover only), and
  the toggle checks `spec_can_lever` again, since Authority can change within the month.
- One tile went from about 700 function calls and 106 variable lookups a frame to about 110 and 21, with no scripted
  GUI calls (was 4); the band labels from 450 calls to 204; the whole tab from about 5,000 calls to 1,200.
- Not done: the credit policy's three buttons still call their scripted GUIs (6 calls a frame; their tech check has no
  cheap GUI equivalent), and the Companies chips still read the building type's goods from global variables.

### Goods panel

The vanilla goods window gets an Investor Interest block under the taxes and tariffs: the good's interest icon and
word, a six-step scale, and one line: producers' throughput at this interest, or how its boom would end and the
confidence that would cost, or "In a Glut".

### Elsewhere

- Financial Markets journal entry (players): confidence bar, most and least favoured goods, credit added this month,
  one button per credit policy and Support the Banks. Opening it switches the map to the journal entry map mode by
  itself (1.15): states take their owner's stage (`spec_stage`, colours `journal.MAP_COLORS`), stripes mark
  `spec_caught`, and the tooltip names the stage, confidence and the panic's source.
- Events: mania warning and panic, pictures by the capital's region; the Long Depression's events.
- Toasts when a tied country panics or enters a mania.

### Economic system law

| law | interest and credit | panic length |
|---|---|---|
| Laissez-faire | x1.5 | x1.2 |
| Extraction economy | x1 | x0.8 |
| Interventionism | x0.7 | x0.7 |
| Agrarianism, traditionalism | x0.5 | x0.6 |
| Industry banned | x0.3 | x0.6 |
| Command economy, cooperative ownership | off | off |

Each law shows these as modifier lines in its own tooltip: `generate.law_table()` injects display-only modifiers into
`common/laws/zzz_spec_laws.txt`, as `tech_ties` does for techs. Trade policy laws get a Trade Ties line the same way.
Seen in game on Interventionism, Laissez-Faire and Command Economy: vanilla's effects stay and ours follow them. Canton
System and Sakoku have no entry in `vanilla_ties.TRADE_TIE`, so they change nothing, though the Foreign Panic concept
says other trade policies weaken trade ties.

## Calibration: three 20-year observer runs, 1836 to 1856

1836 start, observer mode, about 297 countries, built with `--log`. Logs `data/run_v05b_1836.txt`,
`run_v05c_1836.txt` and `run_v05d_1836.txt`, summarised with `py -3 tools/analyze_cycle.py <file>`. The largest
losses are the logged `crash=` term alone, and `crash=` plus `foreign=` plus `turmoil=`, in one country month.

| | v05b | v05c | v05d |
|---|---|---|---|
| changed before the run | | crash cap 40 applied after scaling, not before; depth 0.6 to 1.5 now 0.8 to 1.2; Collapse cost 2.2 to 1.95 | Collapse cost 1.95 to 2.05 |
| country months | 66,312 | 64,909 | 64,792 |
| mean confidence | 55.6 | 56.4 | 57.3 |
| months in mania / panic | 0.9% / 1.1% | 1.3% / 1.2% | 1.7% / 0.5% |
| panics started | 152, 1 per 36 country years | 186, 1 per 29 | 66, 1 per 82 |
| largest month's boom-ending loss | 87 | 40 | 40 |
| plus foreign panics and turmoil | 99 | 52 | 44 |
| bank rescues | 19 | 9 | 1 |
| months Tight / Loose | 0.4% / 3.0% | 0.9% / 2.4% | 0.7% / 1.6% |
| months with an intervention | 17.1% | 21.4% | 20.8% |
| depth, mean (10th to 90th percentile) | 0.78 (0.60 to 1.47) | 0.88 (0.80 to 1.20) | 0.88 (0.80 to 1.20) |

- v05b capped a month's losses before scaling them by confidence and depth, so a deep market at high confidence lost
  87 in one month. Scaling first, then capping at 40, removed that.
- The narrower depth range with 1.95 a point gave the most panics, 1 per 29 country years; 2.05 brought them down to
  1 per 82, with one bank rescue in 20 years.
- No run started a Long Depression. The trigger was reworked after v05d: the first Great Power panic from 1845 starts
  it, with a possible second from a different Great Power. Not yet tested in a run.

## Tuning: full games, 1836 to 1906 (2026-10-31)

Observer games run by `tools/observe.py` (`runs/`), read in the tuner's Stats tab. `tools/replay.py` reruns a game's
logged monthly pushes under other values. It leaves out the mania event's one-off losses, so it reads Mania about 2
points high; use it for the direction and size of a change, then check in a game. Countries that share a tag
(revolutionaries keep their parent's) are split by their update day (`observe.streams`).

| | tune0 | tune1 | tune2 (to 1875, crashed) |
|---|---|---|---|
| changed before the game | | panics caught from abroad pass nothing on; reach by rank; Growth against 2% a year; Business Mood even | boom endings x2.5, booms 0.65, mood 1.5 |
| typical confidence | 56.7 (61 early, 45 by the 1890s) | 56.3 (53 to 61) | 55.2 |
| panics per 100 country years | 12.6 (29 by the 1890s) | 1.3 | 2.7 |
| months in panic / Mania | 4.2% / 4.6% | 0.5% / 4.2% | 0.95% / 4.8% |
| panics among the 12 largest economies | 3, all after 1900 | 0 | 3 (Russia 1872, Britain 1873, British India 1874) |
| Long Depression | 1896 | none | 1872 |
| a Mania followed by a panic within 3 years | 9% | 1% | 4% |

- tune0: from the 1860s 9 in 10 panics came right after a hit from a tied country's panic. The British market's 70
  members, mostly princely states, took a hit nearly every month and panicked as often as the cooldown allowed.
- tune1: chains gone, but large economies never panicked (typical confidence 59, and boom endings took only about
  0.1 a month against booms' 0.3), so the Long Depression could not start.
- tune2: the game crashed on 12 February 1875 (EXCEPTION_ACCESS_VIOLATION, only vanilla script errors before it:
  invalid capitals in vanilla journal entries). One crash in three mod games; watch for more.
- Still: Mania is about 8% of months in the first decade (1836 prices finding their level) and fades to 1 to 2% late,
  as war turmoil grows from -0.03 to -0.2 a month. AI Tight credit runs 5 to 11% of months, against 0.4 to 0.9% in
  the 20-year calibration runs.

Confirmation, tune2 values: 5 games to 1906 (`runs/20261031_031312_mod_1906_tuned`), 4 finished, run 4 crashed on 21
November 1896 (empty crash report). Range across the 4 finished games, whole game:

| reading | range | wanted |
|---|---|---|
| typical confidence | 54.6 to 56.0 (60.7 in 1836 to 1845, 53 to 55 after) | 50 to 60 |
| panics per 100 country years | 2.5 to 3.2 (large economies 2.1 to 2.9) | 1.2 to 3.5 |
| months in panic | 0.9 to 1.2% | 0.5 to 2% |
| months in Mania | 3.7 to 3.9% (8.7% in the first decade, under 1% by the 1900s) | 5 to 8% |
| a Mania followed by a panic within 3 years | 3.3 to 3.7% | |
| Long Depression | in all 4, 2 to 4.5% of months | |
| months Tight / Loose / with an intervention | 5.0 to 7.6% / 4.6 to 6.3% / 19 to 21% | |

Against the 5 vanilla games (`py -3 tools/stats.py <vanilla sessions> <mod session>`): no economic reading differs
but typical living standards in 1855 (+2.6%). World GDP runs 3 to 11% lower from 1865 and large economies' 10-year
growth 5 to 23% lower, each within what 4 against 5 games can tell apart. Two crashes in 7 full mod games against
none in 6 vanilla: too few to tell; the remaining vanilla runs would show vanilla's own crash rate.

## Historical benchmarks (2026-10-31)

The Stats tab judges panics and Mania against history, measured on the 40 largest economies by 1836 GDP
(`observe.TOP`), the closest match to the samples the figures come from (`stats.MOD`, hover a reading for its source).
It shows each benchmark's centre and range, and where the centre sits in a batch's spread: a tuned mod's runs
should spread around it, so a centre outside the middle 90% of the runs is marked.

| reading, 40 largest economies | centre (range) | source |
|---|---|---|
| panics per 100 country years | 4 (2.5 to 5.5) | Bordo and Eichengreen 1999: 4.3 in 15 emerging markets 1880 to 1913; Schularick and Taylor 2012: about 4 in 14 advanced economies 1870 to 2008 |
| months in panic | 1.5% (0.8 to 2.5%) | the panics above times an acute phase of 3 to 6 months |
| panic length | 4.5 months (3 to 6) | the acute phases of 1857, 1866, 1873, 1893 and 1907 |
| months in Mania | 4% (2 to 8%) | Goetzmann 2015: a stock market doubled within a year in 2.1% of market years, within three in 14% |
| Manias followed by a panic within 3 years | 20% (10 to 35%) | Goetzmann 2015: 15% of one-year doublings halved within 5 years; most 19th century panics followed a boom |

No series measures Mania directly, so its two rows are the loosest. Small countries have no historical series; their
readings are watched but not targeted.

Against them, tune3 (the first finance build): panics 2.2, months in panic 0.9%, length 5, Mania 3.6%, Mania to
panic 20%. The largest economies boomed in the 60s and 70s without reaching Mania, so bubbles that burst only from a
Mania missed them. Bubbles from 72 at 0.25 x heat (tune5) overshot to 6.1 panics and 45% of manias ending in one;
from 76 at 0.15 with booms x0.8 and Tight a cap (tune6) undershot to 1.8, Mania 1.8%: the AI's Tight cap ended the
largest economies' manias within a month. With Tight a pull (tune7): 2.1, Mania 2.4%, 17% of manias ending in a
panic. Now from 74 at 0.2 with booms 0.72 (tune8): to March 1892, when the computer crashed, panics 3.6 per 100,
1.3% of months in panic, length 5, Mania 5.2%, 34% of manias ending in a panic, all within history's ranges, the
last at its edge. Mania runs 9% of months in 1836 to 1845 in every build, as the starting prices settle.

0.8 retune, 2026-11-07 (tune9 to tune12, 1856 or 1850 saves to 1890, the 40 largest each year). Replays from one save are
near copies (three control runs: 3.2 panics per 100 each), so only different saves are separate evidence. At PANIC 20 /
CONTAGION 12 the 40 largest panicked 3.2 per 100 in all three worlds and the 10 largest about 3; PANIC 25 / CONTAGION 20
gave 4.3, 5.7 and 3.7 (in panic 1.0 to 1.6%), the 10 largest 3.8 to 6.1. Lending from 50 doubled debt but cut the 10
largest's panics to 1.5. The AI held little debt (median 0.5 to 0.8 months, past 3 in 8 to 14% of months, in every decade
to the 1920s) because confidence rests at 55 and banks lent only above 60, 35 to 37% of months, with 3% repaid monthly
and a Cautious AI tightening at 3. Debt B (CREDIT_FROM 55, CREDIT_RUNOFF 0.02, Cautious limit 5) on top, stopped at 1873:
median debt 1.15 and 1.38, past 3 in 16 to 18% of months, panics 4.2 and 5.3. Made the defaults; fastsim replay 4.3
panics, 1.6% in panic. The confidence bands stay at 20/40/60/80 (as tested); their tooltips now read TIERS, not the
panic and lending lines. Not yet run past 1890 on these values.

## Feasibility test

Victoria 3 1.14.5, Austria 1841 save, observer mode, 61 game months per run.
Months 1 to 24 unboosted, boost from month 24. Second run from the same save with no boost as control.
Raw monthly data in `data/`, comparison with `tools/analyze.py`.

### Levels added, month 24 to 61

| building | boosted run | control run |
|---|---|---|
| glassworks (ai_value x20) | 33 | 6 |
| logging camp (investment_scores x20) | 74 | 54 |
| iron mine | 22 | 29 |
| tooling workshop | 20 | 20 |
| food industry | 8 | 8 |
| coal mine | 4 | 6 |

### What works

- `ai_value` on a building type (state scope, script value) pulls construction hard: 5.5x the control.
- `investment_scores` on financial districts and manor houses (country scope, per building group) pulls, but weakly: +37% for a 20x weight.
- `market = { mg:wood = { add = market_goods_pricier } }` reads a signed number: negative below base price (-0.18), so `market_goods_cheaper` is not needed.
- Variables on the country hold a fast and slow moving average of price month to month.
- `debug_log` prints script values with `[THIS.ScriptValue('name')]`.

## Private investors only

Same setup, boost from month 12, with `tests/no_government_construction.txt` copied into `mod/common/defines/`
so AI governments build no production buildings. Everything built comes from the investment pool.
Data in `data/private_only_*.txt`.

| building, month 12 to 60 | boosted | control |
|---|---|---|
| glassworks (ai_value x20) | 34 | 8 |
| logging camp (investment_scores x20) | 64 | 20 |
| iron mine | 9 | 19 |
| tooling workshop | 15 | 21 |
| furniture | -5 | 0 |

- Private investors follow `ai_value`: 4x the control.
- `investment_scores` is strong too (3x) once AI governments are not also building; the first test was diluted by them.
- Unboosted sectors lose out. The investment pool is finite, so a boom in one sector starves the others, as it should.

## The speculation loop

`tools/generate.py` builds the mod. Each month every country tracks, for 36 goods, a fast (0.3) and slow (0.05)
moving average of the price's distance from base in its market. Hype = 1 + gain x (fast - slow), clamped.
The ai_value of 40 production buildings is multiplied by the owner's hype for the good the building sells.
(Now 41 goods, and a falling trend gives 1 / (1 - trend); see Version 0.6.)

Test: 1856 save, observer mode, government construction on, 60 months, every country logged (about 250).
For each country and building, average hype over the run against levels added. `tools/analyze_loop.py`.

| levels added per country-building | rising price trend | falling trend | top third by hype | bottom third | total |
|---|---|---|---|---|---|
| control (hype tracked, not applied) | 0.62 | 0.99 | 0.42 | 0.96 | 1437 |
| loop, gain 6, cap 3 | 0.63 | 0.93 | 0.48 | 0.88 | 1415 |
| loop, gain 60, cap 20 | 0.79 | 0.99 | 0.56 | 0.81 | 1558 |

- The loop runs with no script errors across about 250 countries.
- Hype is steady month to month (0.95 correlation), not noise.
- Without the loop, rising prices go with less building: prices rise where supply is not being added.
- A mild loop changes nothing measurable. A strong one moves investment toward rising goods:
  +27% building on rising trends, +33% in the top third, -16% in the bottom third, +8% overall.
- It narrows the gap but does not reverse it, and five years showed no clear boom and crash cycle.
  The generator now defaults to the strong setting.

## Open (from the feasibility test)

- One run per variant; repeat with another save before trusting exact numbers.
- Booms and crashes were not measured directly: whether overbuilt sectors end up idle when prices fall.
- Resolved: the monthly log line per country is only built with `--log`.
- The player's own country was not isolated; the result covers every country's private investment.

## Testing notes

- `debug.log` rotates at 512 KB and other errors flood it; collect lines continuously.
- Hot reloading script values mid run stopped the monthly on_action. Restart instead.
- `is_player` is false for everyone in observer mode; the logger targets `c:AUS`.

## Version 0.2: crashes, credit tools and the report panel

Superseded in part: the report window below was replaced by the Market panel's Speculation tab, the crash numbers and
the AI rules have changed, and a fourth finance tech (Modern Financial Instruments) adds credit. See Version 0.6.

Built by `tools/generate.py` (script, journal entry, events).
`py -3 tools/generate.py --log` adds a monthly log line per country for `tools/analyze_cycle.py`.

- Confidence 0 to 100: hot goods push it up, a good that boomed hard (hype 6+) and then fell below 0.5 knocks it
  down, war, default and revolution too. It drifts back to 55.
- Above 60 confidence adds credit to the investment pool (scaled by GDP, law and finance techs). Mania at 80.
  Below 20 a panic: private construction allocation -50% and investment pool efficiency -40% for about 9 months,
  then confidence resets to at least 40.
- Laws scale everything (laissez-faire strongest, command and cooperative off). Stock Exchange, Investment Banks
  and Mutual Funds grow credit. Central Banking unlocks the credit stance and the bank rescue.
- AI countries use the same tools by rule; players get the journal entry and the report window.
- Report window (removed): a vanilla side panel opened from a top bar badge. Overview tiles, two years of confidence,
  investment pool and GDP charts, a table of all 36 tracked goods (price against base, world price trend, hype,
  crash risk) and the credit policy buttons.

Calibration, 1856 save, 60 months, about 250 countries (`data/cycle_1856.txt`): mean confidence 60,
mania in 2.7% of months, panic in 0.2%. The first count, one panic per country every 40 years, read
the log out of date order. Sorted by date it is 6 panics, one per 207 country years: far too rare.

## Version 0.3: review fixes

After an outside review (Codex). Superseded in part: the tab layout, the goods words and the AI thresholds below have
changed. See Version 0.6. Script:

- One panic clock: a month countdown ends the panic and its modifiers; the 12 month protection starts when it ends.
- A panic halves private construction: the allocation modifier is applied with half the law's own allocation
  as its multiplier, read from the vanilla law file. Law strength now scales duration only.
- Rescue once per panic, everywhere the same rule (tab, journal, event): ends it within 3 months, never later
  than it would have, halves its effects, confidence +15 capped at 100. Paid from the treasury, borrowing if short.
- Tight credit is a hard cap at 75. Credit stance rules live in shared scripted triggers and effects; the journal
  has one button per target stance like the tab.
- AI (since shifted by temperament and the interest groups in government): tighten above 80, back to normal below 65, loosen below 40 outside a panic, back to normal at 60 or in a
  panic. Rescue when more than 3 months of panic remain.
- Leaving the market economy clears every variable and modifier and removes the journal entry; coming back
  starts fresh.
- Confidence weights each good by its share of the market's trade (sell orders at base price; full weight at
  3%), so small goods cannot carry a boom. Broken booms hit harder the higher confidence was.
- Credit is outstanding until repaid at 4% a month; a panic calls half of it back out of the investment pool.
- Shipyards, electrics, automotive and food industry follow the average of their base good and the goods their
  later production methods make once the tech is researched (steamers, radios, aeroplanes, tanks, liquor).
- Decision: hype stays on ai_value, so AI governments build by market signals too. It pulls harder
  (4x against 3x for investment_scores) and the player's own government building is manual anyway.
- History holds only months actually recorded.

Tab at the time (since replaced): confidence, credit policy, goods, then folding sections (what moved it, history,
capital). Goods had names, vanilla price colours, the vanilla filters, Booming (x3+) / Rising / Cooling, Steady folded.
Shown for the market the player trades in, not only one they own.

Calibration, 1856 save, 60 months, about 250 countries, after the fixes. With trade weighting and the old crash
numbers (1.5 a point, cap 15) there were no panics in three years: crashes kept hitting the cap. At 2.5 a point,
cap 35: mean confidence 57, mania in 1.0% of months, panic in 0.9%, 33 panics, one per 36 country years,
6 AI bank rescues, AI tight 0.6% / loose 2.1% of months. No script errors.

In-game tests through debug-only events (`event spec_markets.90 AUS` and so on, built with `--log`): panic event
and rescue from the event, rescue shown as used in the tab, command economy switches the tab to its off notice,
laissez-faire brings it back at 55 with the journal entry.

Map mode: Victoria 3 1.14 can add a map mode but not paint it from script (painting types are fixed in the engine).
A badge-and-glow version was built and then shelved in `tools/mapmode.py`; Patch 1.15 adds journal entry map
modes that can shade states, so the map mode returns then, driven by the Financial Markets journal entry.
It has since shipped in `tools/journal.py` (`MAP_COLORS`); `tools/mapmode.py` is still the unused badge version.

Map colours (2026-11-05): hand picked, no outside source. Wary was orange, too close to Mania's gold at the other end of
confidence, so it is now slate blue: low confidence reads cold, high reads hot, red stays for Panic. A dusty rose would
match the bar better but clashes with Aftermath. The bar itself runs red, teal, green, gold, and was not changed.

Tested 2026-11-06: a map mode of our own with `map_painting_mode = journal_entry_map_data` loads and lists under
`map_mode_lists = { market }`, but paints every state blank. The engine only feeds that painter while a journal entry is
open, so neither a tab nor a list entry can show the stages without opening the journal entry.

Tooltip rewrite (2026-11-05): calculator tooltips reworded in vanilla's style, six new concepts (Market Conditions,
Baseline Confidence, Market Mood, Market Tie, Capital Flight, War News), all translated in `tools/i18n/<language>/v070.json`.
`generate.py` `write()` now adds vanilla's `|q` to `'$key$'` loc values, which cleared 97 log warnings.

## Tuner

`py -3 tools/tuner.py`, then open http://localhost:8765 (stdlib only, 127.0.0.1). Now (`tools/live.py`) finds every running
game by its process, so a game shows whoever started it, and starts or stops tests: a started test is `sweep.py --plan` on its
own, so it outlives the tuner. A game can be stopped only under `sweep.WORK`. `runs/checklist.json` is the release list on that
page. Results (`tools/score.py`, also `py -3 tools/score.py <test>`) scores `runs/sweep_<test>/` against the baseline games from
the same start. Settings writes overrides to `tools/tuning.json`. Build makes a test build with logging in `vic/b_<name>`, or
the release build without logging in `mod/` after a confirmation and only with no game running; both run `check.py` and the
self-tests.

After a civil war two countries can log under one tag on neighbouring days, one of them with zeros. Scripts that took each
month's last row read that as Bad Debts ending and starting again, so `score.Watch` lets the peak fade only as fast as Bad
Debts do. That moved lev3 from .36 to .26 severe crashes per 100 country years (mix) and .59 to .33 (reckless). The typical
country also reads lower than the old scripts, +2.7% for lev3 mix against +3.4%, because it now takes each country against
the mean of the baseline games, not the difference of two medians.

## Decisions (2026-10-28)

- Name: the tab stays "Speculation" and the mod "Speculative Markets" (not "Finance").
- Falling goods keep the softer investment drop from the balanced tiers (a modest fall leaves 67% of normal investment, a steep one 50%), not the old steeper one (50% and 10%).

## Small countries (full game to 1897)
Panics per 100 years by GDP: under 3k 12.7, 3k-10k 4.8, 10k-20k 6.6, 20k-50k 3.9, 50k-200k 2.8, over 200k 1.8. 49 tags were held by more than one country, so anything counting by tag alone overstates tiny-country panics; a country's day in the 30-day cycle tells them apart.
Under 3k, 93 of 246 panics began with no pool income: leverage froze at its last figure (18 months in one case) while the debt ran off, and each panic took the worst Bad Debts. LEV_INCOME_FLOOR (income counts as at least 1% of GDP a month) fixes that. Estimated from the log, not yet played: panics with debts past 3 months 73 -> 20, months past 5 1124 -> 231. It binds 9.9% of months under 3k, 0.12% at 3k-20k, never above.
The rest are slow slides, mostly war and revolution (64% of the months before them), left alone. Tiny panics don't reach big neighbours: the hit scales with source GDP over target GDP.

The sizes above are the log's SPEC gdp=, which is the bank rescue cost (about 1/70 of GDP, halved during a panic), not GDP: 20k is about £1.4M. tools/watch.py now reads the PROBE line's real GDP and keeps two countries on one tag apart. World GDP in reports before this was the rescue cost too: real world GDP was about £3.3B in 1906 and £4.2B in 1914.
