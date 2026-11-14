# Speculative Markets: mechanics map (2026-11-11)

Read-only survey of the generator (tools/*.py) as of today, defaults `CYCLE_ON=1`, `LEV_ON=1`, `EXCHANGE_ON=1`.
Evidence is file:line in tools/. "g." = generate.py. Everything runs in `spec_monthly` (g.791, country monthly pulse)
unless noted; Financial Centres rank on the global monthly pulse (centres.py:361).

## 1. Mechanics

| # | Mechanic | Player-facing | Key variables / modifiers | Player CAN do | Merely happens |
|---|---|---|---|---|---|
| M1 | **Investor Interest** (per good) | Each good's interest word Fleeing..Feverish from its price trend | `spec_hype_<g>` = 1 + (fast-slow price avg of `market_goods_pricier`) x 60 x `spec_hype_mult` (g.490-504); words `spec_word_<g>` (g.590); `spec_hype_mult` = econ law x stance x joint_stock x depth x conf band x Exchange (g.384) | Restrain/Encourage (M4); Credit Policy scales it; build Financial Districts | price trend, law, techs |
| M2 | **Booms & boom endings** | A good at Eager+ is a boom; when it falls it ends as Correction/Bust/Collapse by its peak | `spec_peak_<g>` (decays 3%/mo, g.507), `spec_sev_<g>`, `spec_risk_<g>`, `spec_glut_<g>` (interest held at Doubtful 3/6/12 months, g.665); UNWINDS g.129 | Restrain freezes and winds it down | ending is automatic when interest falls below the line (g.657) |
| M3 | **Market Confidence** (0-100) + bands | One gauge; bands Panic/Wary/Steady/Buoyant/Mania | `spec_conf`; inputs summed in `spec_conf_pre` (g.470): recover, boom, crash, restrain, turmoil, debt, foreign, world, mood, growth, business; then tight pull (g.473). Band modifier `spec_conf_<band>` (g.1166, 1540) | Credit Policy Tight (pull), mania event options, rescue/suspend jumps | most inputs |
| M4 | **Interventions** (Restrain / Encourage per good) | Buttons on goods rows and the vanilla goods panel | `spec_restrain_<g>`/`spec_encourage_<g>`; Authority cost like a consumption tax, levy/subsidy via `country_tax_income_add`/`country_expenses_add`, producers' throughput +-10% (levers.py:22-46) | yes, direct (Authority-limited) | AI uses them by rule (levers.ai_block, g.1119) |
| M5 | **Market Mood** | Random lasting swing in confidence | `spec_c_mood` = mood x 0.75 + roll +-0.75, halved without Financial Districts (g.876-884) | nothing | pure noise |
| M6 | **Speculative Excess / bubble burst** | Heat builds while confidence >= 75 (with Stock Exchange); bursts below 60 | `spec_heat`, `spec_c_burst` (g.963-1009); game rule Market Volatility (g.448) | Tight credit lowers conf; Currency School reform x0.75 heat | yes |
| M7 | **Mania** | conf >= 80: event, loyalists | `spec_mania`; event spec_markets.1 (g.949-961, 1625) | event: ride it / warn (-10 conf) / levy (treasury + , -5 conf) | trigger |
| M8 | **Financial Panic** | conf < panic line: 4-8 months of crisis | `spec_panic` clock = 6.5 mo x law x legitimacy x reforms (g.467, 549-551); line = 25 + leverage stress x40 - shallow x5 (leverage.py:90); modifiers `spec_panic`, `spec_panic_crunch` (g.1180-1210, 1550-1564); 12-mo cooldown | event spec_markets.2: leave alone / rescue / blame speculators (g.1668) | start/end automatic |
| M9 | **Contagion & capital flight** | A panic hits tied countries; calm Great Powers (or International+ Exchanges) gain | ties: same market, subject/overlord, foreign_investment_rights treaty, GDP owned, trade reliance >0.2 w/o embargo (g.1214-1255); hit = 20 x tie x GDP ratio x reach(rank) x currency-standard (g.1258-1293); flight diplomacy.py:89-115 | none direct (only via laws/techs/treaties) | yes |
| M10 | **Credit Policy** (stance) | Tight / Normal / Loose | `spec_stance`; needs Central Banking, 6-mo cooldown (g.1471-1483, 1448); Tight: no credit, hype x0.5, conf pull; Loose: credit x1.6, hype x1.3 (g.376, 397); IG approval +2/-1 Industrialists vs Intelligentsia (credit_ai.py:5,41,58; g.1566-1575) | yes, direct | AI by temperament + IGs in government (g.1064-1104) |
| M11 | **Credit / investment pool / Outstanding Credit** | Banks pour money into the vanilla investment pool above conf 55 | `spec_credit` (g.415-417) = (conf-55)/45 x pool income x 1.5 x law x credit techs x stance x reforms x Lending Standards x Exchange(known=3), capped 40%/mo and by credit limit; `add_investment_pool` (g.935); repay 2%/mo (g.925); panic clawback 50% (g.1195) | Credit Policy only | flow automatic |
| M12 | **Leverage / credit limit** | Months of pool income owed; reward and risk | `spec_lev`; limit 3/8/10/12 by Central Banking, Investment Banks, Intl Exchange Standards (leverage.py:58-62,113); reward `spec_lev_boom` +2% throughput per month up to 12 (leverage.py:128); stress lifts panic line | indirect (stance) | yes |
| M13 | **Bad Debts (credit crunch)** | Panic with stress leaves throughput/investment loss for years; no lending | `spec_crunch` = stress^2 x 40, fades 0.25/mo (leverage.py:44,106-108, 263-289); modifier `spec_credit_crunch` -1% throughput, -2% investment per point | **Buy up bad loans** (halves it, ~0.25% GDP x crunch, Banking, once per spell) leverage.py:337-395 | yes |
| M14 | **Bank Rescue** | Once per panic: shorten it, +20 conf | `spec_rescue` (g.1410-1436): cost 2% GDP (3% w/o Central Banking) x months-left scale x LLR reform x Lending Standards (g.439-463); halves panic modifiers; TU + Rural Folk -2 approval (stories.py:72) | yes (tab, journal, event); needs Banking | AI rolls (g.1105-1118) |
| M15 | **Lending Standards** (cycle A) | Strict..Reckless word in Budget > Banking | `spec_lax` 0..1: +1/240 per quiet month, +0.25 per rescue/bailout, -0.02 per conf point of boom-end loss, -0.4 on unrescued panic end (cycle.py:18-27, 117-152); scales credit x0.75-1.25, boom pull, rescue cost | nothing direct (rescue raises it) | yes; Credit Policy does NOT move it (JOURNAL_STATE:158) |
| M16 | **Booms build** (cycle B) | Booming good's building group builds faster; overbuilding deepens the ending | `spec_boom_build_<grp>`: +0.1/+0.2 construction efficiency (cycle.py:30,216-219); `over_mult` from supply growth since boom start (cycle.py:31,107,154) | indirect (build or not) | yes |
| M17 | **Busts land on people** (cycle C) | Bust/Collapse radicalises states with the industry (level>=3), strata by economic law | `add_radicals_in_state` (cycle.py:164-186) | none | yes |
| M18 | **Bank exposure** | Share of credit lent into each boom; makes that boom's ending costlier | `spec_exp_<g>`, `spec_exp_mult_<g>` (exposure.py; used g.513, 520, 936) | Encourage raises pull; Restrain halves it | yes |
| M19 | **Investor throughput by interest tier** + **company glut** | Buildings making a good get -10..+8% throughput by the owner's interest word; companies whose types make an ended boom lose up to -10% for a year | `spec_investor_<g>_<tier>` (companies.py:35, 169-197); glut modifiers (companies.py:36-41, 147; g.663); panic: company throughput bonus -0.05 (companies.py:42,50) | none direct | yes |
| M20 | **AI investment hype** | AI builds more of hyped goods | `ai_value` x `spec_hype_<g>` injected into vanilla buildings (g.318-343) | none | yes |
| M21 | **Financial Centres** (top 5) | Ranked list; place gives prestige and cheaper loans | score = (6 x pool income + Outstanding Credit) x (0.5..1.5 by trust/calm), leader = 100 (centres.py:76-113, 271-357); `spec_financial_centre` +-0.02/step prestige/loan rate (centres.py:370-374) | nothing direct | yes |
| M22 | **The Exchange** (trial) | Standing Provincial/National/International/World Centre; trust; "known for" | `spec_centre_trust` 0-120: +1/mo under sound Lending Standards, -1 Reckless, boom end +2/-6/-18, panic halves, unrescued end halves again (centres.py:36,60-73,134-147); `spec_exch_stand` (International+ needs Central Banking, centres.py:150-262); hype x1.05-1.15, flight received x1-3 (centres.py:33-34); known: Commodity Exch hype x1.1, Deposit Banks trust loss x0.5, Share Market credit x1.1 (centres.py:37-39, 126-131) | **choose "known for"** in event spec_exchange.1 on each new best Standing (centres.py:385-425) | everything else |
| M23 | **Journal: stages, responses, Banking Reforms** | Permanent JE; buttons; Sound Finance | Suspend Bank Act (needs Currency School, panic): +15 conf, panic <=2 mo, legitimacy -10, moral-hazard heat x1.25 for 10y (journal.py:31-32,239-256); Relief Works (12 mo; welfare, construction +10%, fewer movement radicals, cost; TU +2) (journal.py:222-235, 297-303); Convert Debt (conf>=60, scaled_debt>=0.2: loan rate -20% 5y, rentiers -2) (journal.py:27-29,149-163); Commission of Inquiry -> reform event (journal.py:258-268, 672-700). Reforms: Currency School credit/heat x0.75, panic len x1.25; Free Banking credit x1.25, boom x1.1, risk x1.1; LLR rescue cost x0.5, -1 month; Company Law risk x0.7 (journal.py:36-41); all three = Sound Finance prestige +10, loan -10% | yes, all four buttons + reform choice | AI by rule (journal.py:600-641) |
| M24 | **Long Depression** | Rare world crisis from a Great Power panic after 1868-78; Crash/Depression/Recovery | global phase; spreads along ties (depression.py:1-60); pressure -4/-0.6/+1 conf (52); modifiers invest, loan rate, construction, trade, radicals-from-SoL, FD SoL (67-77); no credit during Crash (133); events with choices (tariffs hit tied partners' conf, relief, money policy) moving world recovery (60-63, 614) | event choices only | onset, spread |
| M25 | **Economy drivers** | Growth, Industrialists' mood, debt, default, bankruptcy | `spec_c_growth` (GDP vs ~1y avg, +-0.6, economy.py:24-35); `spec_c_business` (Industrialists approval, +-0.4, economy.py:36-41); `spec_c_debt` (scaled_debt >0.5, up to -1, vanilla_ties.py:50); default -5, nearly broke up to -3 (g.854, economy.py:110-123) | indirect (vanilla budget) | yes |
| M26 | **War & plays** | Wars move conf by how they go; plays -0.5/mo; war end jump | diplomacy.py WAR_ROWS (13-31), WAR_END (34) via on_won/lost/inconclusive_war (235); play g.846 | indirect (vanilla diplomacy) | yes |
| M27 | **Political movements** | Panic boosts labour/socialist/communist/corporatist/bonapartist; long mania boosts Orleanists | `spec_panic_movements`, `spec_mania_movements` decaying 5y (movements.py) | none | yes |
| M28 | **Story events** | Random small events (8%/mo, 2y gap) with IG and money options | stories.py:7-60 | choose options | firing |
| M29 | **Depth / steadiness** | Financial Districts deepen hype and crashes; Manor Houses steady | `spec_depth` 0.8-1.2 (FD share of levels), `spec_steady` 0.85-1.1 (vanilla_ties.py:12-62) | build FDs / Manor Houses | |
| M30 | **AI temperament** | Hidden: Cautious/Balanced/Bold | `spec_temper` from ruler/heir traits + econ law (credit_ai.py:18-25); shifts stance thresholds, rescue odds, fever (leverage.py:52-57) | n/a | AI only |
| — | Display only | Market Heat shares, charts, War/Default risk, Booms at Risk, alerts, notifications, tech-tooltip lines | market_visual.py, charts.py, economy.py:42-79, journal alerts, notify.py, tech_ties.py (display-only modifiers) | | |

"World Market": no mechanic of its own. The "world" confidence driver (`spec_c_world`) is only the Long Depression
pressure plus tariff hits (depression.py:134-158).

## 2. Link matrix (mod -> mod)

| From | To | How | Evidence | Dir |
|---|---|---|---|---|
| Interest (M1) | Booms (M2) | hype >= 3 is a boom; peak tracks hype | g.646, 507-510 | -> |
| Booms (M2) | Confidence (M3) | +0.85/mo x trade weight per boom, cap 3, x steady x fin techs | g.647, 818-835 | -> |
| Boom endings (M2) | Confidence (M3) | loss = (peak-1) x rate x weight x exposure x overbuild, x crash_scale, cap 40 | g.518-521, 659, 822-826 | -> |
| Confidence (M3) | Interest (M1) | band gain x0.8 Wary .. x1.3 Mania on rising prices | g.380-384 | <-> (loop) |
| Confidence (M3) | Crash size | crash_scale = conf/55 x depth x steady x fin_risk | g.476 | -> |
| Confidence (M3) | Credit (M11) | linear above 55 | g.415, 930 | -> |
| Confidence (M3) | Panic (M8), Mania (M7), Heat (M6) | thresholds | g.949-1053 | -> |
| Credit Policy (M10) | Interest, Credit, Confidence | hype x0.5/x1.3; credit 0/x1.6; Tight pull | g.376, 397, 473, 886 | -> |
| Credit (M11) | Leverage (M12) | debt / pool income | leverage.py:77 | -> |
| Leverage (M12) | Panic line (M8) | stress x40 raises line | leverage.py:89-90; g.1049 | -> |
| Leverage (M12) | Bad Debts (M13) | stress^2 x40 at panic | leverage.py:106-108, 276-288 | -> |
| Bad Debts (M13) | Credit (M11) | no lending while crunch | leverage.py:259; g.933 | -> |
| Panic (M8) | Credit (M11) | no lending; clawback 50% | g.931, 1195-1197 | -> |
| Panic (M8) | Contagion/flight (M9) | spec_every_tied, spec_capital_flight | g.1205-1208 | -> other countries' M3 |
| Contagion (M9) | Confidence (M3) abroad | spec_c_foreign next month | g.866-874; diplomacy.py:118-124 | <-> between countries |
| Rescue (M14) | Panic (M8), Confidence | panic <= 2-6 mo, +20 conf, modifiers halved | g.1427-1432 | -> |
| Rescue / bailout | Lending Standards (M15) | +0.25 | g.1434; leverage.py:370; cycle.py:140 | -> |
| Boom endings (M2) | Lending Standards (M15) | -0.02 per conf point | cycle.py:127 | -> |
| Unrescued panic end | Lending Standards | -0.4 | cycle.py:146-152; g.1402 | -> |
| Lending Standards (M15) | Credit, Exposure pull, Rescue cost | x0.75-1.25 etc. | g.417, 440; cycle.py:41-43 | -> |
| Lending Standards (M15) | Exchange trust (M22) | +1 / 0 / -1 a month | centres.py:141-144 | -> |
| Credit + pool (M11) | Financial Centres (M21) | score = 6 x income + debt | centres.py:89-98 | -> |
| Trust (M22) | Centres score | x0.5..1.5 | centres.py:78-87 | -> |
| Boom endings, Panic | Trust (M22) | +2/-6/-18; halve; halve again unrescued | g.663, 1199, 1402; centres.py:60-73 | -> |
| Exchange Standing (M22) | Interest (M1), Flight received (M9) | hype x1.05-1.15; flight x1-3; Intl+ counts as safe haven | g.384, 456; centres.py:33-34; diplomacy.py:55-56 | -> |
| Exchange known-for | Interest / Trust / Credit | x1.1 / x0.5 loss / x1.1 | centres.py:37-39, 126-131 | -> |
| Interest (M1) | Exposure (M18) | lending pull by trade share x heat | exposure.py docstring; g.936 | -> |
| Exposure (M18) | Boom-end loss | x(1 + per-month x share x leverage) | g.513, 520 | -> |
| Interest (M1) | Building throughput (M19), AI ai_value (M20), construction (M16) | tier modifiers; hype multiplier; group bonus at Eager+ | companies.py:169-197; g.342; cycle.py:216-219 | -> vanilla only |
| Supply growth in boom (M16) | Boom-end loss | over_mult | g.520; cycle.py:107, 154 | -> |
| Boom endings | Radicals (M17), company glut (M19) | | g.663 | -> vanilla only |
| Interventions (M4) | Interest, Booms, Confidence | clamp hype; restrained boom cannot end, pays spec_c_restrain | g.504, 512-513, 643-644 | -> |
| Reforms (M23) | Credit, heat, boom, risk, panic length, rescue | spec_reform_* multipliers | journal.py:36-41, 84-97; g.400, 445-447, 551, 972 | -> |
| Suspend Act | Heat (moral hazard x1.25, 10y) | | journal.py:32, 85, 252 | -> |
| GP panic | Long Depression (M24) | onset; spreads on ties; world pressure on conf; blocks credit in Crash | depression.py:1-60, 129-158; g.933 | -> |
| Heat (M6) | Confidence | burst -0.2 x heat (max 40) | g.993-1001 | -> |
| Mania/Panic | Movements (M27) | | g.1010, 1209 | -> vanilla only |

One-way / isolated:
- **Market Mood (M5)**: input only, from nothing (pseudo-random roll; g.407, 881-884).
- **Financial Centres ranking (M21)**: fed by credit, pool and trust; its output (place modifier) goes only to vanilla prestige and loan rate. Nothing in the mod reads `spec_centre_rank` (grep: only centres.py).
- **Lending Standards (M15)** and **Trust (M22)**: read only by cycle.py/centres.py/diplomacy.py (grep `spec_lax`, `spec_exch_stand`). Trust never touches confidence directly.
- **Companies (M19), Movements (M27), cycle C radicals (M17), AI hype (M20)**: pure outputs to vanilla; nothing reads them back.
- **Stories (M28)**: read state, output IG/money/legitimacy modifiers; no mod variable changes except caution conf step (stories.py:286-291).
- **AI temperament (M30)**: AI only; players are never gated by it.

## 3. Vanilla inputs (what pushes the mod)

| Vanilla thing | Feeds | Evidence |
|---|---|---|
| Market prices (`market_goods_pricier`) | Interest trend: the core input | g.485, 490-497 |
| Market sell orders x good cost | trade weight of each good; overbuilding | g.486-489; cycle.py:154 |
| Economic system law | hype x0-1.5, panic length x0-1.2, private construction cut size; off under Command/Cooperative; AI temperament; cycle C strata | g.213-215, 293-300, 370-372; credit_ai.py:21-25; cycle.py:178-183 |
| Trade policy law | trade tie x0.1-1.5 | vanilla_ties.py:7, 37 |
| Technologies | stock_exchange, investment_banks, mutual_funds, modern_financial_instruments (credit, boom size, risk); joint_stock_companies (hype x1.1, Company Law); macroeconomics (recovery x1.5); central_banking (Credit Policy gate, rescue, credit limit, International+); banking (rescue, bailout, Banknote Rules); international_trade / international_exchange_standards (flight; ties x1.25; credit limit); currency_standards (foreign loss x1.25 without); corporate_charters / corporate_management (company glut); PM techs for goods baskets | g.93-104, 216, 394-457, 1473, 1489; leverage.py:62; vanilla_ties.py:39,47; companies.py:40; g.249-254 |
| Buildings | Financial District and Manor House levels (depth, steadiness) | vanilla_ties.py:24-62 |
| Investment pool income / balance | credit size, repay cap, leverage, centres score | g.404, 435-437; leverage.py:73 |
| GDP | growth driver; contagion/flight size; rescue/bailout/levy cost; leverage floor | economy.py:24-35; g.1202, 1267, 463-466 |
| Government debt (`scaled_debt`, `in_default`, `weeks_until_bankruptcy`) | debt drag, default -5, broke slide; AI rescue limits; Convert Debt | vanilla_ties.py:50; g.854; economy.py:84-123; journal.py:158 |
| Legitimacy | panic length x0.8-1.2 | g.549-551 |
| Industrialists' approval | business driver +-0.4 | economy.py:14, 36-41 |
| IGs in government (Industrialists, Intelligentsia) | AI stance thresholds; credit approval modifier refresh | credit_ai.py:41, 58-63 |
| Ruler / heir traits | AI temperament | credit_ai.py:20-25 |
| Wars (casualties, GDP change, occupation, war pressure, land lost, length, stalemate) and war end | monthly war cost, end jump | diplomacy.py:13-37 |
| Diplomatic plays, revolution, default | turmoil | g.846-863 |
| Market membership, subjects, foreign_investment_rights treaties, `gdp_owned_by`, `market_trade_reliance`, embargoes | contagion ties | g.1214-1255; diplomacy.py:63-66 |
| Country rank | contagion reach; flight safe haven; Long Depression origin | g.423-425; diplomacy.py:55; depression.py:181 |
| Population loss (land lost) | leverage relief | leverage.py:142-153 |
| Company types present | company glut applies | companies.py:104, 115 |
| Gold reserves | AI rescue / AI suspend | g.1111; journal.py:637 |
| Authority | intervention gate | levers.py:219-220 |
| Game rule | Market Volatility | g.448-452 |

## 4. Vanilla outputs (what the mod changes)

- **Investment pool**: credit in, repayment and clawback out (g.926, 935, 1196).
- **Investment pool efficiency** (capitalists, aristocrats, shopkeepers): bands -0.2..+0.2 (g.156, 1541), panic -0.4 (g.1552), crunch -2%/pt (leverage.py:127), Long Depression -0.3/-0.15 (depression.py:67-76).
- **Private construction allocation**: panic halves it, rescue to a quarter (g.1185-1188, 1422-1425, 1563).
- **Construction**: boom group efficiency +0.1/+0.2 (cycle.py:216); Relief Works +10% (journal.py:298); Long Depression -10/-15% (depression.py:71,75).
- **Throughput**: interest tier -10..+8% per building (companies.py:35); company glut up to -10% (36); company throughput bonus -0.05 in panic (42); interventions +-10% (levers.py:26); Credit Boom +2%/month leverage (leverage.py:128); Bad Debts -1%/pt (129).
- **AI building choice**: ai_value x hype (g.318-343).
- **Loan interest rate**: bands +0.2/+0.1/-0.1 (g.157); Financial Centre -0.02/step (centres.py:373); Converted Debt -0.2; Sound Finance -0.1 (journal.py:292,315); Long Depression +0.35/+0.2.
- **Trade quantity**: bands -0.1..+0.1 (g.158); Long Depression -0.15.
- **Prestige**: Financial Centre +0.02/step, National +0.02 (centres.py:372,378); Sound Finance +10.
- **IG approval**: panic -2 Industrialists, Petty Bourgeoisie (g.1556-1557); Credit Policy +2/-1 (g.1566-1575); event, journal, story and depression timed modifiers (g.187-196; journal.py:44-51; stories.py:29-50; depression.py:80-102); rescue -2 Trade Unions, Rural Folk.
- **Pops**: radicals on panic (g.1191-1193), loyalists on mania (g.956-957) and blame option (g.1701); state radicals on Bust/Collapse (cycle.py:173); movement support (movements.py:7-12); Financial District SoL +1 mania, -2 panic (companies.py:47).
- **Treasury / budget**: rescue, bailout, levy (+), intervention levy/subsidy, relief and story expenses, share duty income.
- **Legitimacy / Authority**: Suspend -10 legitimacy, Inquiry -10% authority, story/depression legitimacy +5; interventions cost Authority.
- **Welfare / movement radicals**: Relief Works (journal.py:297-299).
- Tech tooltips: display-only lines (tech_ties.py:1-5).

## 5. Gaps

Player only observes (no lever, or the lever is the same Credit Policy / rescue pair):
- Confidence drivers from mood, growth, business, debt, war, contagion, Long Depression: no player action targets them directly.
- Lending Standards: no way to tighten banks; Credit Policy deliberately does not move it (JOURNAL_STATE.md:158). Only rescues (up) and pain (down).
- Financial Centres / Exchange Standing and trust: no lever except the one-time "known for" choice; trust is a by-product.
- Leverage: managed only through stance; the credit limit is tech-set.
- Contagion ties: shaped by vanilla diplomacy, but no mod choice (e.g. ring-fence, lender of last resort abroad).
- Companies section: shows throughput effects; companies cannot act and their prosperity is never read.
- Market Heat, Booms at Risk, War/Default risk, charts: display.

Mod mechanics with no vanilla input:
- Market Mood (random); Exchange trust (only mod variables + Lending Standards); Lending Standards (only mod events); heat/burst (only confidence + Stock Exchange gate); Bad Debts size (only leverage); "known for" (event pick, AI random).

Vanilla systems the mod ignores (grep found no reads):
- **Institutions** (no `has_institution`/institution investment): e.g. none of Banking-ish or Social Security.
- **Power blocs** (no `power_bloc` reads) despite being natural contagion/finance ties.
- **Tax level / taxes** (only consumption-tax cost reused for lever pricing), **SoL / radicals / turmoil** never fed back into confidence (only output).
- **Interest groups for players**: only Industrialists' approval and AI IG-in-government; IG clout, ideology, party in power do not gate Credit Policy or reforms for players.
- **Company prosperity / company charters / building ownership** (except cycle C strata by law) not read; Financial Districts counted only as levels.
- **Construction sector / government spending / investment pool spending choices** not read; overbuilding only via sell orders.
- **Elections, laws other than economic system and trade policy** (e.g. colonial, labor, welfare) not read; reforms are mod variables, not vanilla laws.
- **Trade routes / customs unions** beyond market membership and reliance; **migration, literacy, population** (only land loss) not read.
- **Prices are read but never written**: confidence does not move vanilla prices or demand except via trade quantity and throughput.

## Off-limits for now: Sovereign Debt / Hot Money / Foreign Lending

Owner instruction: do not change. Facts found:
- Not part of this generator or `mod/` (grep `sdt_|SDT|hot_money` in mod/: 0 hits). It is a separate mod, tested from here.
- tools/debt_run.py:1-6 runs "a Sovereign Debt mod" headless and saves `SDT*` log lines to runs/debt/; tools/debt.py:1-12 parses them for the tuner's Debt tab (tools/tuner/index.html).
- Links to Speculative Markets today: none in script. centres.py:8 states Financial Centres are "Separate from Foreign Lending". design_exchange.md:65 and design_1.0.md:5 exclude it from scope.
- Planned (memory note, 2026-11-07): will merge into Speculative Markets eventually; prototype workshop/hot_money.html. Not verified further.
