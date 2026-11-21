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
