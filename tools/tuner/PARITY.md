# What a tuner run measures

The tuner steps a synthetic country through the monthly financial scripts. A candidate and the baseline receive the same seeded input draws. Changing the seed samples different economies and different Great Power histories. A passing score measures agreement with the design targets. Forecast accuracy also needs a comparison with a campaign on the same build.

## Player feedback candidate

The rolling Favoured and Shunned prototype in beta.32 uses the same six-month price condition, weighted draw, slot limits, twelve monthly effects and fresh qualification after expiry in the tuner and the game. The game reads native sell orders and the premium over base price. The tuner supplies a bounded synthetic premium for each good. It retains 93% of the previous premium, adds price momentum from its existing boom model and a five-percentage-point standard deviation monthly shock, and clamps prices to 25–175% of base. Basket shares approximate the base-price value of sell orders. These inputs are assumptions. The earlier beta.16 and nine-sector scores do not validate beta.32's balance.

The unpublished 1.2.0-beta.16 uses [six experimental settings](../../beta/feedback_120/tuning.json). Selection used seed 19. The scored confirmation used three fresh seeds, 500 paired starting economies per seed and strategy, and 100 years per economy. The six presets kept their own purchase and credit decisions. GDP effects below are the average modeled output effect after the cost of rescues and bad-loan purchases. Averages across the three seeds are rounded.

| Strategy | GDP effect | Investment pool effect | Panics per century |
| --- | ---: | ---: | ---: |
| Passive | +1.53% | +4.53% | 5.67 |
| Careful | +2.24% | +5.25% | 1.10 |
| Strategic | +2.72% | +5.45% | 1.97 |
| Reckless | +0.64% | +5.59% | 10.31 |

Strategic lets lending run longer than Careful, tightens before a mania and pays for recovery. It beat Passive in 1,363 of 1,500 matched starts, Reckless in 1,421, and both in 1,336. Careful beat Passive in 1,128. The candidate met all 18 targets on seeds 911, 1123 and 1301. With the corrected mechanics and original tuning values, the same seeds met 13, 12 and 13 targets.

The previous month's turnover-weighted category reading modulates each good's price impulse using the same bounded confirmation as the generator. The simulated good retains its own episode, intervention, loans and crash. Synthetic episode peaks and endpoints are neutral inputs. A regression applies the same falling price path under two credit policies and checks that the raw category reading stays identical. The game supplies actual market prices. An individual building and its production-method changes still have no direct representation in the simulator.

In **Player finance policy**, select Money Market and Hold Tight to replay the reported style. Banking gates the charter, Central Banking gates the credit policy, and the six-month switch lock still applies. **Watch one country** shows Exchange Trust under Lending Standards. In a separate matched comparison of 900 passive countries choosing Money Market, mean Trust during eligible country-months was 89.0–89.6% under sustained Tight Credit and 31.4–36.7% under Normal Credit. An economy can still lose Trust through collapses or panics. Computer-controlled countries retain their own policy choices and their charter selection is outside the simulator.

From the repository root, set `SPEC_TUNING` to `beta/feedback_120/tuning.json` to inspect this candidate in the tuning UI. To repeat the target comparison against the original values, use the default tuning file and run the command below for each seed. The [verification record](../../tests/mechanics/verification_feedback_120.json) includes native evidence separately.

```powershell
py -3 -B tools/tuner/lab.py check LEV_PANIC_SPAN=50 LEV_REWARD=0.018 LEV_CRUNCH_RAMP=2 LEV_CRUNCH_FADE=0.47 LEV_BAD_STOP=11 PANIC_SHALLOW=14 --n 500 --seed 911
```

## Decisions and constraints

The five player presets benchmark choices a human can make. The sixth preset, **AI**, follows the game's country decision rules. Design targets score simulation results and are never exported to Victoria 3. Each AI country rolls a lasting Cautious, Balanced or Bold temperament, influenced by its ruler, heir and economic law. Succession leaves the stored temperament in place. Governing Industrialists and Intelligentsia can shift current credit thresholds as governments change. In beta.16 the three leverage thresholds are 5, 8 and 9.5 months. Eligible bank-rescue chances per month are 15%, 30% and 50%, respectively. The tuner includes the economic-law weights and uses sampled government inputs. Individual ruler and heir traits are absent from its input data.

| System | What the offline model enforces | What is estimated |
| --- | --- | --- |
| Credit policy | Central Banking, six monthly pulses between switches, threshold order, leverage, speculative fever, government preferences and credit-stance approval | Ruler and heir traits, changes of government between observations, and the player bots' strategies |
| Research | The installed vanilla prerequisite tree, including dependencies through technologies outside the simulation. By default observed research also bounds the eleven modeled unlocks for each sampled country. Fiat law changes require Central Banking. | The month of research between observations, future law changes and each country's economic and monetary law mix |
| Goods interventions | Per-good Authority cost at the generated rounding step, the AI's double-cost test, one encouraged good, the strict surplus test, lifting in deficit or default, word hysteresis, and automatic lifting when a boom can bust | Each good's domestic output, prices and market share. Each simulated basket uses distinct real goods and its shares sum to at most 100%. Political reactions to individual goods and Great Issue conflicts are outside these scenarios. |
| Player goods buttons | Optional dated orders use the selected good, available Authority, market and boom eligibility, and the three-pulse wait after either toggle. An active lever can be undone during its seven-day grace period. An undo restarts the wait. | The player presets leave these buttons alone until a scenario supplies orders. Their economic feedback uses the monthly state. |
| Bank rescues and loan buy-ups | Banking, panic or Bad Debts eligibility, purchase locks and the £1,000 rounding step. The AI checks cash, scaled debt and near-bankruptcy. The treasury records each payment before checking the next purchase. Suspending the Bank Act keeps the full panic penalties. | Credit capacity for countries without debt, replenishment after spending, exchange specialities and international pledges |
| Long Depression | The global opening window, an active panic in an eligible AI Great Power, the prior-origin exclusion, repeat chance, post-recovery cooldown and two-occurrence limit | The focal country observes an external panel of powers. Close ties and phase duration use sampled conditions. Diplomatic networks, event-driven recovery and prestige changes between observations are outside the model. |

In the tuner's **Player goods orders**, enter one click per line, such as `1836-02-01 grain encourage`. Repeat it on a later date to request lifting the lever. The same orders apply to each player strategy in the comparison. A country needs the named good in its simulated basket. **Watch one country** shows the resulting counts under Booms.

## Observed inputs

The fiscal probe ran in an isolated copy of 1.2.0-beta.4 on Victoria 3 1.15.2. It recorded a fresh 1836 start and two saves from the same campaign in 1866 and 1896. The checked-in CSV contains the largest 40 economies by GDP each March, one row per tag per date. The sample represents large economies, with limited coverage of minors and fiscal distress.

Each fiscal row keeps GDP, cash, principal, scaled debt, weekly balance, Authority, bankruptcy flags, Great Power status, governing Industrialists and Intelligentsia, and finance technologies together. The extractor adds back Authority and subsidy spending already committed to goods interventions and removes existing levy receipts before a simulated policy spends anything. For borrowers, principal divided by scaled debt gives the native credit limit. Other countries use the median observed credit capacity relative to GDP.

Ordinary simulated economies retain their GDP percentile when moving to a later fiscal snapshot. Their research bounds follow their starting tag wherever it was also observed later. Each simulated world instead follows distinct Great Power tags, eligible only in periods when their recorded rank and simulated financial state permit it. Fiscal transitions occur between observations. After the final one, the model keeps its last fiscal ratios while simulated GDP and intervention spending continue to move. At most eight external worlds are shared by the focal economies per candidate. Their count matters when interpreting rare events.

The fiscal and research inputs can be switched off in the scenario controls for counterfactual tests. The financial observations do not determine a good's price path, the makeup of an individual market, future wars, law enactment or GDP's response to throughput. The existing model uses fitted input ranges, sampled game logs and feedback assumptions for those. Additional systems outside the score include Exchange specialities and contests, rivalries, power-bloc effects, Relief Works and political reactions to individual goods.

## Frozen 1.2 check, November 21, 2026

Across the three snapshots, 5, 29 and 39 of the 40 countries had Central Banking. Britain already had it in March 1836. The old model placed its earliest possible unlock in 1841. The captures contained 7, 8 and 8 Great Powers. No selected country was in default or nearly bankrupt. The highest observed debt was 36.4% of the native borrowing limit. Tests for fiscal distress therefore use controlled scenarios.

Both frozen-value runs used 500 focal economies per strategy for 100 years, with six strategies. The same five targets missed on both seeds.

| Metric | Design band | Seed 7 | Seed 19 |
| --- | ---: | ---: | ---: |
| AI panics per century | 3–6 | 2.83 | 2.67 |
| Passive panics per century | 4–7 | 4.40 | 4.22 |
| Reckless panics that freeze lending | 35–90% | 30.01% | 30.16% |
| Reckless minus careful GDP outcome | −8 to −1 points | −0.27 | −0.28 |
| Careful minus passive GDP outcome | +0.5 to +5 points | −0.07 | −0.04 |
| Skilled minus AI GDP outcome | +0.2 to +4 points | +0.01 | +0.02 |
| All targets met | 18 | 13 | 13 |

In eight external worlds per seed, the Britain proxies spent 14.0% and 13.2% of January 1868 through December 1899 in Tight Credit. The longest uninterrupted spell was 19 months on seed 7 and 41 on seed 19. By January 1900, 7/8 and 8/8 worlds had experienced a Long Depression. The previously reported in-game campaign used the earlier mechanics and saw Britain remain Tight throughout that interval. In the archived one-year beta.4 game check, Britain registered one month Loose, seven Normal and four Tight. A full held-out campaign on the repaired beta is still needed to measure the forecast gap. [Beta.4 game evidence](../../tests/mechanics/verification_review_120.json)

All 18 targeted simulator tests passed. The tuner self-check matched 66 constants to the generators. Each short game capture had zero blocking errors under the repository's full error-log gate. The candidate-source quick check passed Python, generated content and CMF. The default stable-source check still flags its 1.1.6 / 1.15.1 metadata against the 1.2.0 / 1.15.2 development source. The local tuner Watch endpoint accepted a dated order and its grace-period undo, and returned an input error for an invalid date.

## Reproducing the checks

Run `py -3 -B -m unittest discover -s tests -p test_tuner_parity.py` for the controlled boundaries. Run `py -3 -B tools/tuner/engine.py` for the generator checks. Run `py -3 -B tools/tuner/lab.py check --n 500 --seed 7` and repeat with seed 19 for the frozen balance comparison.

To refresh the observations, install the files returned by `tools/probe.py`'s `files(fiscal=True)` into a scratch copy of the candidate and run each snapshot through March. Pass the three resulting `probe.log` paths in year order to `py -3 -B tools/tuner/fiscal.py`. The regular probe and release build do not enable this instrumentation.

## Offline 1.2 retune after the lending and trust corrections

Restrain halves the selected good’s share of new boom loans before the total exposure cap applies. Gold Standard and other monetary laws scale the Exchange’s trust losses on monthly lending, Bad Debts, boom endings and panics. Two regression cases cover the restrained-good allocation and the Gold Standard loss. A third checks what happens when a candidate’s lending ceiling cuts off a technology tier. The tuner records the seed for new results and flags this ceiling in its results panel and command-line report.

The frozen beta values met 13 of the 18 design targets on each of five 500-economy seeds. An initial four-setting candidate improved the score but capped lending at ten months, so the final twelve-month technology tier became unreachable. The following candidate preserves the lending ladder at 3, 8, 10 and 12 months and the maximum Bad Debts penalty at 20 points and 40% throughput. These five overrides remain an offline experiment.

| Setting | Frozen beta | Offline candidate | Effect |
| --- | ---: | ---: | --- |
| `LEV_PANIC_SPAN` | 30 | 50 | A highly leveraged country can panic at higher confidence. |
| `LEV_REWARD` | 2% | 1.8% | Each whole month of leverage adds less throughput, up to four rewarded months. |
| `LEV_CRUNCH_RAMP` | 1 | 2 | Two points of an existing debt penalty take effect each month until its full size is felt. |
| `LEV_CRUNCH_FADE` | 1 | 0.43 | Debts fade more slowly under Normal or Loose Credit. Tight Credit still clears 1.5 points per month. |
| `LEV_BAD_STOP` | 15 | 12 | At Sound lending standards, banks stop lending at twelve points of Bad Debts. |

Each run used 500 economies per strategy over 100 simulated years. Seeds 61, 179 and 223 were held out when choosing this candidate. The same target definitions were used for selection and confirmation.

| Seed | Frozen targets met | Candidate targets met | Careful minus passive GDP outcome | AI panics per century |
| --- | ---: | ---: | ---: | ---: |
| 61 | 13/18 | 18/18 | +0.582 points | 4.04 |
| 179 | 13/18 | 18/18 | +0.542 points | 3.91 |
| 223 | 13/18 | 17/18 | +0.425 points | 3.84 |
| 7, earlier comparison | 13/18 | 18/18 | +0.502 points | 4.21 |
| 19, selection seed at larger size | 13/18 | 18/18 | +0.522 points | 3.98 |

The one held-out miss was the +0.5-point minimum for careful over passive. On the three fresh seeds, careful beat reckless by 1.33–1.51 points on average. In the same 1,500 paired economies, skilled beat passive 1,274 times, reckless 1,372 times and both together 1,233 times. Careful beat passive 1,003 times. The comparison uses each economy’s average modeled GDP effect after bank-rescue and buy-up costs. The six strategies are presets. Country inputs and Great Power worlds are sampled. The lending limit omits the focal Exchange and power bloc bonuses.

To repeat the comparison with the frozen beta values as the control, run `py -3 -B tools/tuner/lab.py check LEV_PANIC_SPAN=50 LEV_REWARD=0.018 LEV_CRUNCH_RAMP=2 LEV_CRUNCH_FADE=0.43 LEV_BAD_STOP=12 --n 500 --seed 61`. Change only the seed to reproduce the other runs. The five overrides have not been promoted into the beta or stable tuning file.

## Matching the clean 1.2.0 game, November 22, 2026

The reference is `runs/windows_120/campaign`, one AI game from 1836 to 1905. The hold-out sample is `runs/windows_120/parallel`. `py -3 -B tools/tuner/windows.py compare` checks the campaign and `compare parallel` checks the hold-out. Each window is the 40 largest economies.

- The comparison now ranks countries by real GDP from `probe.log`. The `gdp=` field in SPEC lines is the bank-rescue cost. Ranking by it picked reckless lenders, so earlier game-side figures for 1866 and 1896 were biased.
- With `observed_research` on, `fit.py --history` stores the campaign's history in `world.npz`. This covers laws, technologies, exchange depth and steadiness, and world turmoil, foreign and war-end shocks. Each tuner country follows the campaign country of the same GDP rank. After 1906 the last 30 years repeat. Extraction economy comes from this history. The depth and steadiness input ranges are not used while history is on.
- Booms come from each good's price, as the game builds them. See the third sample below. `share_trend` is gone.
- `lure_vs` follows the logged rival scores. Most Lures sit at `VS_LO`, so a typical Lure is 4.5 pool months, not 7. `fit.py --windows` refits `lure_rate` per eligible month.
- Bear Raids are not modeled. They cost the top 40 about 0.1 confidence a country-year. Press campaigns are also not modeled. They cost about 2 trust a year.
- The core monthly math is unchanged.

### Second sample and cause logging, November 22, 2026

`generate.py --log` now writes three more line types. A build without `--log` is byte-identical (240 files hashed). `windows.py run parallel2` keeps them as `trust.log`, `rvai.log` and the SPEC line.

- SPECTR is a line for every trust change, with its cause and size.
- SPECRVA is a line for every AI rival look.
- The SPEC line gains `iapp` and `igov` for the Industrialists.

`runs/windows_120/parallel2` holds the second sample. Its 1866 game crashed in March 1870, with no script error from the new lines, so its 1866 window is too short for `compare parallel2`.

- **Trust:** low trust after 1866 comes from Lending Standards. The game spends 32-39% of months at Reckless, against 10-20% in the tuner. Reckless drains trust every month and blocks the monthly gain. Press campaigns, contests and blue chips net about -0.3 trust a country-year, so they are not modeled. The game's spread of Lending Standards across countries is wider (p90 country mean 0.93-0.97, against 0.79-0.87). Countries with almost no boom-ending losses drift to Reckless.
- **Booms:** the game runs about 10 goods at risk at once, with good weights summing to about 20 and about 2 endings a year. The tuner's boom model is far shorter and lighter. `share_trend` is a stand-in that matches the decades' means. A refit with the game's weights made the push rise over the century, so it was rejected. The Mania gap and the Lending Standards spread trace to this boom model. The third sample replaces it.
- **Lures:** per eligible AI look, Lures run at about 0.05 in both 1836 and 1896 in this sample. The campaign's rising rate does not repeat.
- **Business Mood:** with history on, the engine replays the followed country's logged `d_business` (`fit.py --history` stores `h_business`). In the game, Industrialists' approval averages +3 in 1836 and -2.3 by 1896.

### Third sample and the price-driven boom model, November 22, 2026

`generate.py --log` now writes a line for every boom ending and fade (SPECBE, SPECBF). It also writes each market owner's goods prices and weights (SPECPX), and the SPEC line gains `hm`, `hmd`, `nboom`, `wrisk` and `wd1`-`wd6`. A build without `--log` is byte-identical (240 files). `runs/windows_120/parallel3` holds all three games complete, with `booms.log` and `prices.log`.

The tuner's boom episodes are replaced by the game's own chain. Each good has a price, its fast and slow averages (`FAST`, `SLOW`), and their gap times `HYPE_GAIN`. Sector support, interest, peak, severity, endings and the cap follow `generate.py` as before.

- **Price swing:** measured from `prices.log`. A good's monthly swing falls with its weight (exponent -0.19) and its economy's GDP (-0.17). With GDP in, no decade effect is left. This is why fewer goods are hot late in the century: larger economies have calmer prices.
- **Price shape:** each good keeps its own volatility factor (log spread 0.55). A month's noise adds 0.25 of the slow part's spread. In markets of 25 goods or more, 6.5% of the movement is shared. Prices move more in 1836-37 (1 + 0.9 e^(-month/6)).
- **Basket:** 29 traded goods in 1841, plus 17 a century. Shares of trade are log-normal (width 1.1). This gives weights summing to 18-21, as in the logs.
- **Fitted by `fit.py --boom` (2 inputs):** `price_sd` 0.0316 and `price_months` 7.6. The logs' autocorrelation suggests about 14 months, but the campaign fit prefers 7.6. Rerunning `--boom` rewrites both and removes the retired episode inputs.
- **Hold-out result:** the headline metrics miss less on all four samples (campaign 12.2 to 5.9, parallel 5.5 to 4.6, parallel2 3.5 to 2.3, parallel3 6.9 to 4.2). Late-century Manias, Reckless share and trust below 30 move toward the game. 1836 is weaker: Busts are 26% of endings against about 48% in the game, so 1836 crashes and panics are too small.
- **Design targets:** 23 of 30 on seeds 19 and 7, up from 19. Scores fall from 37.6 and 35.7 to 27.3 and 25.4.

### AI behaviour keys and the AI's event choices, November 22, 2026

The AI's own numbers are now tuning keys, each read through `tuning.get` with its released value, and swept from `K` in the engine. A build without `--log` is byte-identical (240 files against `build_scratch/windows_120/nolog_r3_after2`). The per-temperament tables move as one scale each (`tuning.scaled`, values back on the 5 / 0.5 / 0.05 grid, whole numbers for percents and weights): `AI_LEV_SCALE` (leverage.AI_LIMIT), `AI_FEVER_SCALE` (leverage.FEVER) and `RESCUE_SCALE` (credit_ai.RESCUE_CHANCE). `TEMPER_TILT` moves base weight from Cautious to Bold. `AI_LEV_BACK` (0.5), `AI_BAILOUT_CHANCE` (15), `AI_CONF`, `AI_RISK` and `AI_FUNDS` are plain keys. The mania event's six `ai_chance` numbers are `MANIA_AI_*`.

- **Two engine fixes.** The Bold leverage limit ran at 9 instead of 9.5: `np.vectorize` took an integer type from the first economy. `WARY` was sweepable but did nothing: the engine kept the import-time loose point. The released baseline moves from 27.28 / 25.39 to 27.18 / 25.22 (seeds 19 / 7, 500 economies), still 24 of 31.
- **Event model.** `spec_markets.1` (the Mania warning) was already in the engine with hard-coded weights; it now reads the keys. `spec_markets.2` (the panic) changes only approval and loyalists, and its rescue option has weight 0, so the engine leaves it out. Story events go to players only. Depression events fire once a campaign, move confidence 3 to 10 points once, and their own-recovery effect is replaced by the fitted Depression length, so they are left out. Blue chips are not modeled at all, so their events are left out too.
- **Logging.** A `--log` build writes `SPECEV tag= date= ev= opt= temper=` for each AI choice in `spec_markets.1` and `.2`. `windows.py` keeps them in `events.log`.
- **Parity of the choices.** A fresh released-values batch (`runs/windows_120/ai_parity`, all three windows complete, no script errors) logged 45 Mania choices and 236 panic choices. Mania choices: ride 56%, warning 20%, levy 24%, against the model's 52 / 29 / 19 for the logged temperaments. That is inside the noise (chi-square 2.0, 2 degrees of freedom). In the panic event the AI picked Speculators Blamed 70% of the time, against 29% from its weights. Market Left Alone is hidden once the panic is already rescued.
- **Rescue gap, found here.** The AI makes the Exchange's rescue pledge whenever it can (centres `_pledge_month`: not in default, scaled debt below 0.3, reserves at least a rescue's cost). A pledged country is rescued as its panic starts. In the logs 53-71% of all countries' panics are rescued in their first month, and only 1-6% later by the AI's monthly roll (`RESCUE_CHANCE`). The engine has no pledge. The tuner's AI rescues 17-25% of panics in 1866-1906, against 31-68% for the game's top 40. The miss on "Panics rescued (ai)" is this gap, not AI behaviour. More rescues also mean laxer Lending Standards, which fits the tuner's low Reckless share.
- **Games are repeatable.** The `ai_parity` 1866 and 1896 windows match `parallel3` figure for figure: the same build and save give the same game. 1836 starts from the bookmark and differs.
- **Game check of the AI-only winner (see the pledge section below for the backtest)** (`build_scratch/candidates/ai_20261122.json`: AI_TIGHT 80 to 70, AI_LEV_SCALE 1 to 1.3, RESCUE_SCALE 1 to 1.6, AI_BAILOUT_CHANCE 15 to 0, TEMPER_TILT 0 to 15; `runs/windows_120/ai_check`, all three windows complete, with 1896 rerun once after a base-game access violation in 1905). In both later decades, Reckless months and trust below 30 fall further than the tuner predicted. In 1866 Reckless falls from a baseline mean of 30.6 (range 28.4 to 31.9) to 13.6 against a predicted 2.7-point drop, and trust below 30 from 44.2 to 35.6. In 1896 Reckless falls from 35.8 to 28.6 and trust below 30 from 53.3 to 50.1, which is inside the noise. The share of panics rescued stays inside the baseline range, as the missing pledge model predicts. The candidate fails the side checks. Buoyant or Mania rises to 40.9% in 1866, above the range of 23.4 to 35.9, and falls to 33.6% in 1896, below the range of 35.4 to 41.9. Mean confidence is 55.97 in 1866, above its range, and 54.79 in 1896, below it. Panics per country per decade are 0.86 in 1866, above the range, and 0.69 in 1896, below it. In 1896 the 90th-percentile frozen spell is 31.7 months, against a range of 16.9 to 26.4 and a target band of 12 to 27. The tuner predicted all four of these would stay level. The tuner's AI lever effects are too weak, and it does not model the effect of AI behaviour on the market cycle.

### The AI's rescue pledge, the journal keys and a backtest, November 22, 2026

The engine now models the Exchange's rescue pledge for AI economies, as `centres._pledge_month` and `PLEDGE_RESCUE` script it (`Economies.pledge_month`, `rescue_now`, `stand_ok`).

- **Who pledges.** An AI economy pledges when it has Banking, a National Standing or higher, scaled debt under `AI_PLEDGE_DEBT` (0.3), no default, no panic, and reserves of at least a rescue's full cost. It rolls `AI_PLEDGE_CHANCE` (100, so whenever it can) each month. It gives notice when scaled debt passes `AI_PLEDGE_LEAVE` (0.4) or reserves fall below the pledged cost. The pledge holds for `EXCH_PLEDGE_NOTICE` (24) more months. A default breaks it: all trust and 15 confidence. The Broken Pledge's legitimacy hit is left out; the logs show one break in all the games.
- **Standing.** The engine does not model the Exchange score, so `fit.py --history` now stores the campaign's logged Standing (`h_stand`). Each economy reads the Standing of the campaign country it follows. Without that history every economy counts as National. In the logs 70-85% of the top 40 are National or higher. Nothing else in `world.npz` changed.
- **What it does.** While pledged, a rescue costs `EXCH_PLEDGE_COST` (0.75) of the usual share, before the floor. A pledged panic is rescued in its first month, after the trust cut and the clawback, if the country has Banking, is not in default and can pay from reserves. Otherwise the panic runs and the pledge stands. The panic's trust cut is `EXCH_PLEDGE_PANIC` (0.5) as large. The extra capital flight a pledged country receives (`EXCH_PLEDGE_FLIGHT`) stays in the fitted or replayed flight.
- **Journal keys.** `journal.MONTHLY_AI` and `spec_reform.1` now read `AI_INQUIRY_CHANCE` (10), `AI_CONVERT_CHANCE` (10), `AI_RELIEF_CHANCE` (20), `REFORM_AI_CURRENCY` (10), `REFORM_AI_FREE` (10), `REFORM_AI_TEMPER` (30, added for Cautious to the first and for Bold to the second), `REFORM_AI_LLR` (25), `REFORM_AI_COMPANY` (15) and `REFORM_AI_SHELVE` (5). `engine.ai_journal` reads them from `K`. Relief Works is still not modeled, so `AI_RELIEF_CHANCE` moves nothing in the tuner.
- **Logging.** A `--log` build adds `SPECPL tag= date= act=make|notice|kept|unmet [reason=] sdebt= cost=` and `SPECJ tag= date= act=inquiry|convert|relief|suspend|reform [opt=a-e] temper=`. `windows.py` keeps them in `pledges.log` and `journal.log`. A build without `--log` is byte-identical: all 240 files match `build_scratch/windows_120/nolog_r3_after2`. No game has run with these lines yet.
- **What the existing logs confirm.** The SPEC line's `pledge=` and `rescued=` give the share of months pledged, the share under notice, and whether a pledged panic was rescued in its first month. They show 6-12 of each window's 8-15 pledged panics rescued at once. Unpledged panics are also often rescued in their first month (2-8 of 10-22) by the AI's monthly roll. The logs cannot show the AI's reserves or debt when it decides, or why a pledged rescue failed. The new `SPECPL` line records those.

Parity on the released samples (top 40, `build_scratch/candidates/game_decades.py` and `tuner_decades.py`, 1000 economies, seed 1):

| 1866-1876 / 1896-1906 | game (campaign, parallel, parallel2, parallel3) | old engine | new engine |
| --- | --- | --- | --- |
| Pledged months % | 34-37 / 35-45 | 0 / 0 | 43.1 / 33.9 |
| Panics rescued % | 31-68 / 41-53 | 48.8 / 46.0 | 62.5 / 54.6 |
| Rescued in the first month % | 31-68 / 41-52 | 37.4 / 39.2 | 61.7 / 54.5 |
| Reckless months % | 28.4-31.9 / 31.5-38.9 | 23.5 / 24.5 | 25.4 / 28.3 |
| Trust below 30 % | 42.9-45.4 / 49.9-56.5 | 32.2 / 41.3 | 32.9 / 42.9 |
| Buoyant or Mania % | 23.4-35.9 / 35.4-41.9 | 31.7 / 38.6 | 31.8 / 38.9 |
| Confidence, mean | 52.1-55.4 / 55.0-57.2 | 55.1 / 56.2 | 55.2 / 56.3 |
| Panics a decade | 0.62-0.77 / 0.77-0.96 | 0.38 / 0.67 | 0.37 / 0.68 |
| Lending-frozen spell p90 (months) | 2-19.6 / 16.9-26.4 | 12.9 / 20.0 | 13.5 / 21.8 |

In 1836-1846 the new engine pledges 38% of months against 12-16% in the game, so it rescues 49% of that decade's few panics against 0-40%. The tuner's reserves follow the 1836 fiscal snapshot, where about half the top 40 hold a rescue's cost, and do not fall as the game's do. The pledge moves months in panic down (1866 0.94 to 0.79, game 1.0-1.7), which the roughness block (`after_panic`, `rough_sd`, `rough_months`) was fitted against. That block was not refitted, because the backtest below failed on the AI levers' effect on the cycle, which a level refit does not touch.

**Backtest.** `build_scratch/candidates/backtest_table.py bt2` compares each candidate's game move (against the released samples' mean, outside their range or not) with each engine's predicted move (candidate against released on the same seed). The candidate is switched on at each window's start, as the 1866 and 1896 games started from the released campaign's saves. The old engine is `build_scratch/tuner_frozen_prepledge`.

- `ai_check`: both engines get Reckless falling, but by 2.3 points against 17 (1866) and 7.3 (1896). Trust below 30 falls 1.8 against 8.6 (1866). In 1866 the game's market runs hotter (Buoyant or Mania +11.3, confidence +2.4, panics +0.17); both engines predict it slightly cooler. The 1896 cooling is right in direction (Buoyant or Mania -0.8 against -5.2). The 1896 freeze p90 rise (+8.7) is predicted at +2.0 (old) and +0.2 (new).
- `joint`: both engines get the hotter booms (Buoyant or Mania +13 to +16 against +12 to +20) and the longer freezes (+8 to +10 months against +7 to +19) right in direction.
- Real game moves with the direction right: old 19 of 26, new 20 of 26. **The backtest fails**: the 1866 market swing is wrong in both engines, and the new engine is not clearly better than the old. The sweep was not rerun.

**Design targets with the released numbers** (500 economies, 100 years): 25 of 31 on seeds 19 and 7, scores 26.76 and 24.74 (24 of 31, 27.18 and 25.22 before). Panics rescued (ai) moves into its band (28.3 and 29.3). Reckless months (ai) stay out (27.3 and 26.0). In the 100-year runs most AI panics come after 1906, when reserves follow the 1896 snapshot, so few countries can pledge.

**Key map** (`keymap.json`, 125 economies, seed 1, all keys on the new engine): the pledge keys move nothing beyond noise at one grid step. Scaled debt seldom sits between 0.25 and 0.45, and a 50% monthly roll pledges within a few months anyway. Of the journal keys, `REFORM_AI_FREE` moves Reckless months (ai) by 0.09 band widths and trust by 0.03. `AI_INQUIRY_CHANCE` and `REFORM_AI_CURRENCY` move the freeze p90 by 0.07. The rest move nothing beyond noise.

## Smooth leverage reward and investment growth, November 23, 2026

**Panic-timing bot.** `skilled_timing` borrows with the Balanced AI's thresholds, rescues and buys up as `skilled` does, and goes Tight while the Panic Risk alert's condition holds (`Economies.after_risks` below `panic_at`, as in `journal.alerts`). It returns to its normal stance once the condition clears. `after_risks` counts the costliest unrestrained boom ending and the bubble bursting now. It leaves out the panic-source, war and default chips, because the engine draws those shocks without warning. On the trust-fix baseline with the old level-only model (500 economies), it gains 4.01% / 4.08% of GDP (seeds 19 / 7) against the AI's 4.63% / 4.61%, at 2.8 months of mean leverage against the AI's 3.6.

**Smooth reward (generator).** Setting `LEV_REWARD_TP_FULL` or `LEV_REWARD_INV_FULL` switches on the smooth bonus (`leverage.SMOOTH`). The bonus follows leverage in tenths of a month, up to `LEV_RUIN`. At 12 months it gives `TP_FULL` throughput and `INV_FULL` investment-pool efficiency for Capitalists, Aristocrats and Shopkeepers, which is the modifier Bad Debts cut. Its shape is `(months / RUIN) ** LEV_REWARD_CURVE`. Script has no power function, so the curve is straight between nodes at 0, 1, 2, 3, 4, 6, 8, 10 and 12 twelfths of RUIN (`spec_lev_boom_mult`), and the engine reads the same nodes (`lev_shape`). The modifier is added with `multiplier = spec_lev_boom_mult`. The game itself does this in `common/decisions/india_decisions.txt` with `multiplier = money_amount_multiplier_small`. When neither key is set, the build is byte-identical: all 240 files match a build made before the change.

Pool efficiency was chosen over `country_private_construction_allocation_mult`. Allocation only moves construction between the state and the private queue, so a bonus on it would cost the state its own building. Pool efficiency adds money to the pool. In the logs, pool income passes into construction used with an elasticity of 0.5-0.7, within country and year on year, on every sample.

**Investment growth (engine).** `Economies.cap` compounds the pool income that the mod adds or takes. Each month it grows by `inv_growth / 12 x pool_share x pool_base_x x (pool_inv - 1)`, and GDP is `gdp_base x cap x (1 + e_gdp x tp)`. This applies to every investment effect: confidence tiers, panics, Bad Debts and the leverage bonus. `inv_growth` 0 reproduces the old model exactly. The fit is `build_scratch/candidates/calib_growth.py`, a within-country and within-year OLS of next year's log GDP growth on the year's monthly pool income over GDP, for the 40 largest countries in each sample.

| Sample | Country-years | Growth per unit of pool share | Pass-through to construction |
| --- | ---: | ---: | ---: |
| campaign (70 years) | 2,220 | 3.47 +- 1.03 | 0.68 |
| windows pooled (1836, 1866, 1896, parallel 1-3, ai_parity) | 4,951 | 0.14 +- 1.33 | 0.71 |
| candidate games pooled (ai_check, joint) | 1,998 | 15.1 +- 1.0 | 0.47 |

`inv_growth` is set to the campaign's 3.5. **This is not a credible calibration.** The 10-year windows give no measurable effect, the candidate games give four times the campaign's figure, and the estimate is not causal, since a growing economy also earns more pool income. The size of every result below depends on this one input. Turning growth on raises every style's GDP by about 2.5 points on the baseline, and it moves reckless against careful from -0.86 to -0.04 (seed 19).

**Sweep.** Halving ran at 56 and 168 economies on seed 19. The first pass used the full grid of TP_FULL and INV_FULL from 0.15 to 0.45 and CURVE 1, 0.75 and 0.5 (147 candidates). At every grid point reckless beat careful, so the second pass added `LEV_CRUNCH_INVEST`, `LEV_PANIC_SPAN` and `AI_LEV_SCALE` (240 random draws). The finalists were then checked at 500 economies on seeds 19 and 7. No separate one-step key map was run, because the new keys start from off. Over the finalists, front-loaded shapes keep reckless below careful most often (CURVE 0.5: 55% of finalists, against 6-8% for 0.75 and 1), but moderate leads careful by less. The tuner's reckless bot carries only about 3.1 months of leverage, and its outcomes spread less than skilled's, so the model cannot show heavy leverage as a gamble.

Winner (`build_scratch/candidates/smooth_20261123.json`): LEV_REWARD_TP_FULL unset -> 0.15, LEV_REWARD_INV_FULL unset -> 0.25, LEV_REWARD_CURVE unset -> 0.75, LEV_CRUNCH_INVEST 0.0075 -> 0.03, LEV_PANIC_SPAN 50 -> 70. At 500 economies on seeds 19 / 7: skilled-careful +0.62 / +0.56, skilled-ai +0.27 / +0.42, skilled_timing-ai -0.13 / +0.06, reckless-careful -0.66 / -0.88. It meets 23 and 21 of 33 targets, against 25 and 24 for the baseline with growth on. AI panics rise from 3.4 to 4.8 a century, and AI distrust from 9.6 to 14.4%. Mean confidence moves by +0.06 and Buoyant-or-Mania months by +0.9 points. "Output lost over one panic" reads -7 and leaves its band, because the compounding level makes it negative. No game has run with these values.
