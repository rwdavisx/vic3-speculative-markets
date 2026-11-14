# Journal redesign build state (started 2026-11-01)
Objective: build both stages of JOURNAL_DESIGN.md (user approved "Build both stages").
Gründerzeit clash: flagged only, not in scope.

## Done
- (nothing yet)

## Decisions
- Generator only (tools/*.py); never edit mod/ by hand. Release build: py -3 tools/generate.py; check: py -3 tools/check.py
- Test: new game only, back up and restore user files (scratchpad mk_backup), game in front before input.

## Remaining
1 stages/status/text  2 excess bar + confidence factors tooltip  3 decisions  4 reforms + inquiry
5 AI rules  6 rebuild/check/in-game test  7 calibration runs (tools/observe.py, 3 x 1836-1906)
## Progress 2026-11-01
- tools/journal.py written and wired into generate.py (backup of generate.py before: scratchpad/generate_before_journal.py)
- Free Banking changed from "panic line 22" to boom-ending losses x1.1 (the tab's bands assume 20)
- Bar tooltip itemizing confidence factors skipped: the tab already itemizes them
- Release build + check.py pass; next: in-game test with --log build, then rebuild release
- UI pass (user asked for better UI, narrative, visuals, tooltips): header widget (stage painting in confidence ring,
  je_icon slot), history chart widget (container 4), itemized bar tooltips (monthly_progress, bars re-set in the JE's
  on_monthly_pulse), richer stage text with the capital's name, institution lines with effects
- Fixed: status text used JournalEntry context; outliner has only ROOT (error.log spam). Now ROOT.GetCountry.
- STATE NOW: mod/ is the --log build. content_load.json = only this mod (user's playset 8daf... in scratchpad mk_backup).
  User was at the PC playing the test game (cursor moving) at 01:38, so input stopped.
- Not yet verified in game: header picture, chart, bar tooltips, decisions, inquiry event, reforms, AI rules.
- Still to do: in-game test, release rebuild, calibration runs, restore user files.
- 2026-11-01 user feedback fixed (not yet seen in game): confidence bar tooltip skips factors under 0.05;
  credit tooltips use IG texticons (@industrialists!) not hands; header/history widgets use [GetPlayer] context
  (JournalEntry.GetCountry left ring and pictures blank); stance trigger's raw "script_value_equal" line wrapped
  in custom_tooltip spec_stance_current_tt. credit_ai self-check updated to AI_TIGHT (was stale at 76).
- Verified in game (new game, France 1836): header picture + ring (frame was drawn over them; now drawn first),
  IG icons, no 0.0 factors (threshold 0.1, tooltip cuts to one decimal), Excess line hides "costs 0", credit
  buttons show "Credit Policy becomes X", concepts spec_speculative_excess / spec_sound_finance explain the bars.
- Still untested in game: panic stage, Relief Works, Suspend the Bank Act, Convert Debt, inquiry event, reforms,
  Sound Finance completion. Calibration runs pending. mod/ is still the --log build; user files not yet restored.
- 2026-11-01 PUBLISHED to Steam Workshop at the user's request: id 3831434383, set Public, tags Economy And
  Buildings / Events / Journal Entries. Uploaded via launcher Upload mod from the junction
  Documents/.../Victoria 3/mod/Speculative Markets -> G:/GameDev/speculative-markets/mod (keep it for updates;
  enter the Mod ID 3831434383 to update). Gallery images not added yet (workshop/gallery).
- 2026-11-01 panic side TESTED in game (debug, France, forced states via a temporary events/zz_spec_test.txt, now deleted):
  Convert Debt, Relief Works, Suspend the Bank Act, panic stage, inquiry event (options filter correctly), all three
  reforms, Sound Finance event + modifier (+10 prestige, -10% loan interest), natural burst (excess reset to 0).
  Bugs fixed in tools/journal.py: "Rentiers' Income Cut" apostrophe broke vanilla's ADD_MODIFIER tooltip (renamed
  Rentier Income Cut); spec_reform_done read var:spec_reforms before it existed (error spam) -> spec_reform_count;
  Suspend's raw triggers wrapped in custom_tooltips; Relief IG modifier days match the country modifiers (1 year);
  excess bar value clamped to EXCESS_MAX (set_bar_progress over max logged each month).
  New raw/je_markets.png (May 1839, Buoyant, Excess 113, 3/3, full history); card 11 rebuilt. NOT yet uploaded:
  card 11 to the Workshop gallery, and the mod update itself (the fixes above are local only).
- 2026-11-01 UPLOADED 0.3.1 to Workshop 3831434383 (user approved "Yes both"): mod files with the fixes, version 0.3.1
  in mod/.metadata, and a rewritten, shorter description (workshop/description.bbcode) with a Feedback section.
  Card 11 replaced in the gallery (live image matches gallery/11_journal.jpg).

## Alerts (2026-11-01, not yet on the Workshop)
- `common/alert_types/spec_alert_types.txt` from `alerts(k)` in tools/journal.py; loc `alert_<key>_name/_desc/_hint/_action`.
- Panic Risk (red): booms at risk would drop confidence below PANIC (script value `spec_after_collapse`). `script_context = player_market` (the market panel opens only from a market, as vanilla's famine alert); opens `market|speculation`.
- Speculative Bubble (yellow): `spec_burst_now >= BUBBLE_ALERT` (10); opens the journal.
- Tested in a debug new game: both show, tooltips and hints correct, both clicks open the right panel, no log errors. No topbar.gui change.
- 2026-11-01 UPLOADED 0.3.2 to Workshop 3831434383 (user approved): the two alerts; description gained an Alerts bullet and the 0.3.2 Updates line. Live page verified.

## 2026-11-01, after 0.3.2 (not uploaded)
- "Financial institutions" renamed Banking Reforms; Note Issue renamed Banknote Rules. New concept concept_spec_banking_reforms (concepts.py, loc in journal.py) holds each reform's effect via the reform tooltips. Tested in game.
- Goods panel: spec_goods_levers row (goods_panel.py) under the player's own Investor Interest block, with levers.strip(). Tested: enables.
- Bug fixed in levers._item: vanilla's selected icon button sat on top with no click, so a lever in effect could not be lifted (tab and goods panel). blockoverride "selected_texture_size" now carries the onclick. Tested on the tab.
- Tech ties in tooltips: tools/tech_ties.py copies vanilla's 30_society.txt and appends display-only modifiers (script_only, ai_value 0) to each finance tech; generate.tech_table() reads the values from the same constants the scripts use, so tooltips follow tuning. Scripts still test has_technology_researched. Checked in game (Central Banking, Stock Exchange, Currency Standards, Banking, Corporate Charters, International Trade).
- Two new ties (generate.py): FLIGHT_BASE 0.5 + FLIGHT_TECHS (International Trade 0.5, International Exchange Standards 1) for capital flight; UNSTANDARD (Currency Standards, x1.25 foreign panic losses without it). Both hold the tuned figures for countries with tier 3 starting techs.
- Baseline tune8 to 1876 (all / top 40): panics 4.0 / 3.5 per 100, months in panic 1.4% / 1.3%, length 4, Mania 5.0% / 5.2%, Mania to panic 26% / 34%.
- Tuning check, runs/20261101_121907_techties (one run to 1876, 0 errors), against tune8 to 1876 (all / top 40): panics 3.9 / 3.6 per 100 (4.0 / 3.5), months in panic 1.3% / 1.2%, length 4, Mania 4.9% / 4.1% (5.0 / 5.2), Mania to panic 26% / 29% (26 / 34), foreign driver -0.042 (-0.040). Within history's ranges and run-to-run noise: no constants changed. No Long Depression began by 1876 in this run (d_world 0).
- Release rebuilt without --log, check.py clean. User files restored, md5 verified. 0.3.3 NOT uploaded: needs approval; description needs an Updates line (rename, goods panel buttons, lever fix, tech tooltips).
- Goods panel redesigned as one row like vanilla's Consumption Taxes | Tariffs above it (goods_panel.py): Investor Interest on the left with the tab's goods list bar at a larger size (interest_list.sized(): the same tier icon, name, bar, chevrons, pulse and crash animations; name in fontsize_large), title and throughput line centred on the bar; vertical_divider_full; in the player's own market an Intervention column (new concept concept_spec_intervention) with levers.strip(). Tested in a new game: layout, Encourage on and lifted, Restrain greyed at Calm, concept tooltip. The tab's own rows are unchanged.
- Government Measures on the Speculation tab (user approved): journal.RESPONSES is the one list of the journal's four responses; journal.sguis() writes common/scripted_guis/spec_response_sguis.txt and market_tab.responses() shows one row per response while it applies (name, tooltip with the journal button's desc and BuildTooltip, a verb button). Section hidden when none apply (any_of, since GUI Or takes 2 args). Tested: Relief Works executes and shows its cooldown; Commission of Inquiry shows in Mania. Suspend the Bank Act row untested (same trigger and effect as the tested journal button).
- Marketing images: new raw shots (tab_mania, goods_mania, tt_goods_eager, je_mania, tt_tech_central_banking); make_cards.py: 01_tab, 04_goods, 11_journal re-shot, new 13_tech card, thumbnail from tab_mania. 13 cards plus thumbnail.png. Not uploaded.
- Release rebuilt without --log, check.py clean.
- 2026-11-01 UPLOADED 0.3.3 to Workshop 3831434383 (user approved "Yes"): mod files, description with the 0.3.3 line, thumbnail (mod/thumbnail.png copied from workshop/thumbnail.png). Gallery: 01_tab, 04_goods, 11_journal replaced, 13_tech added (13 images). Live page verified. The launcher sets tags from metadata.json, so the page shows only "Economy" (flagged to the user). Steam managepreviews takes one file per pick; a second Upload click gives "file upload failed: 29" (duplicate), harmless.
- Tags fixed (user: "Economy, events, journal entries"): mod/.metadata/metadata.json tags are now "Economy And Buildings", "Events", "Journal Entries"; re-uploaded, live page shows Events, Economy and Buildings, Journal Entries. The launcher uploads the tags from metadata.json as read at launcher start (ticking boxes in the form did nothing), so restart the launcher after editing metadata.json.
- Mod compatibility (user: least invasive, keep every feature): buildings and tech lines are no longer copies of vanilla files. generate.building_inject writes common/buildings/zzz_spec_investors.txt (INJECT:building_x ai_value = vanilla's + hype ops); tech_ties writes common/technology/technologies/zzz_spec_techs.txt (INJECT:tech modifier = our lines, merged as PEC's own INJECTs assume). zzz names should load after other mods' files (PEC pec_*, Chains of Industry moim_*/zz_moim_*, Production Method Rework 01_industry.txt), so ours hold. Only gui/market_panel.gui and gui/goods_panel.gui still override vanilla (none of those three mods touch them). UNTESTED in game: stopped because the user was playing another game. To test: new game, our mod alone, then with PEC; banking and stock_exchange tooltips should show vanilla's lines, PEC's and ours; error.log clean.
- Tested in game (new games): our mod alone, no errors from the zzz files, Banking tooltip shows vanilla's lines and ours. With PEC (both load orders): Banking shows vanilla's, PEC's (+0.50 Market Volatility) and ours, so INJECT merges. Stock Exchange, which PEC REPLACEs, shows only PEC's: a REPLACE beats our INJECT whatever the mod order and file name. So buildings or techs another mod REPLACEs (PEC: 7 buildings + stock_exchange; Chains of Industry: 19 buildings) lose our lines, as they did before; only a compatch can win those. Production Method Rework defines its buildings plainly, so our INJECT should apply on top (untested). Not uploaded.
- UPLOADED 0.3.4 (user approved): files updated Nov 2 9:57pm, description with the 0.3.4 line live, tags unchanged. The launcher upload form is its own window, Paradox Mods Uploader: focus it (not Paradox Launcher) before pasting the description, and read it back with Ctrl+A, Ctrl+C.
- 2026-11-03 credit check (tune8_mid run, 40 largest economies, 57 years): credit flows in 39% of months, median 0.0076% of GDP a month (max 0.17%); outstanding credit median 0.04% of GDP (90th pct 0.25%). Small next to vanilla investment; the ipi=/ip= log fields (investment pool income and balance) need a new --log run to compare directly. Script: scratchpad credit_share.py. Hype is a direct function of the price trend (1 + (fast - slow) x gain x mult), so a 'hype ahead of price' marker would mean nothing; asked the user whether to drop it or make hype accumulate on its own.
- 2026-11-08 0.9.0 ready, NOT uploaded: VERSION 0.9.0, 0.9.0 line in workshop/description.bbcode, release rebuilt, check.py and i18n clean. Exposure softened (0.1/month, max 1.5). In game (1921 autosave, dev_user): Banking tab, collapsible Charts, Leverage History and Bank Loans by Good all work; no errors from the mod. Fix: the pie kept goods at 1%+ of loans, but boom lending spreads under 1% a good, so it showed "none" beside "4% in booms"; charts.CHART_MIN 0.001, shares to 0.1%.
- 2026-11-08 pre-release review (2 Opus + Codex, read-only) of 0.8 -> 0.9. Fixed: Bank Loans tooltip read x0.00 in a good's first exposed month (exposure.loc tests spec_ui_expx); spec_crash_top cleared each month (a February crash could be named in March); spec_note_bank per good (two endings in one month kept their own multiplier); Leverage History sampled after repayment and lending; bank pie legend shows every good (maxverticalslots), dead show_more overrides removed; description: budget panel in Compatibility, Banking tab mentioned. Rebuilt, check/i18n clean, game starts with no mod errors; not re-run on a save after these fixes.
  Not fixed (flagged): pie has no General slice (slices are boom loans only); "Our Trade" text shows on foreign markets; "in booms" counts loans whose boom ended; Panic Risk alert says tighten Credit Policy but opens the Speculation tab; Investor Interest chart empty until the first month; Restrain tooltip "halves what banks lend" is approximate.

## 2026-11-08 chart polish (0.9.0, NOT uploaded)
- Bank + Investor Interest charts: chart left, scrollable goods list right (swatch, good, interest word, share). Bank chart adds booms-vs-general split bar. Leverage History: shaded zones, credit-limit line, axis labels, legend. Verified in game (Britain, June 1916).
- Fixed: diplomacy.py war-loss lookup errored when last month's enemy warleader was annexed (added exists guard). Not verified in game (on_actions need restart).
- Next: user go-ahead to upload 0.9.0.

## 2026-11-09 chart redo (0.9.0, NOT uploaded)
- Vanilla charts sort largest first and list only a few (legend shows top 3, "Show more" for the rest). Ours now follow that.
- Bank chart: top 5 goods by boom loans, largest first, plus a grey "Other goods" slice and row (6th-largest good stands in, marked spec_bank_oth_<g>). No scroll. List built after lending (with history_shift) so shares and Other add up.
- Investor Interest: treemap of every good replaced by one bar split by level (hot left) + 3x2 key of all six levels (spec_iw_lvl1..6 from interest_script). spec_goods_iw list dropped.
- Leverage History: zone shading removed.
- 10 new strings translated (v090e.json, all languages 0 missing).
- 2026-11-09 later: booms/general split bar removed; Investor Interest is now the bank-style box chart, a slice per level (list spec_iw_levels: one good per level >= 0.5% of trade, its word picks the level figures). Levels under 0.5% hidden (threshold not yet seen in game).
- Investor Interest slices now ordered largest share first; cutoff raised to 1% (game rounds % down). Seen in game, no spec_ errors.

## 2026-11-09 review (design only, no code changed)
- Three fresh-context reviews (player, engineering, simulation) merged into design_1.0.md: Stage A pre-upload fixes, B clarity, C cycle changes, D tooling.
- Next: user picks where to start. 0.9.0 upload still waits for go-ahead.

## 2026-11-09 design_1.0 Stages A-D, harder Long Depression, ideas 1-3 (built, NOT uploaded)
- Long Depression: PRESSURE {1: -4, 2: -0.6, 3: +1}, WORLD_DRIFT 2; CONF_PER_HOT 0.85, CONF_PER_CRASH_HYPE 6. Numbers: see depression.py comment and runs/sweep_cmp1, sweep_cmp2. cmp2 (final, 3 games, 0 mod errors): Depression 43 months, confidence 60 -> 43 (Crash) -> 34 (Depression) -> 53 (Recovery), 10% of Depression months in a panic (0.9: 6%), 50% of panics begin in Crash/Depression (0.9: 22%), 7.9 panics per 100 country-years (0.9: 7.1), median GDP -12..-15% over Crash+Depression.
- Idea 1 Crisis Ledger (tools/ledger.py), idea 2 trade follows the market (BAND_TRADE in generate.py), idea 3 Financial Centres ranking (tools/centres.py). All at the bottom of Market > Speculation. Ideas 4 and 5 not approved.
- Seen in game: ranking, place modifier, ledger rows, world line, tooltips. Not seen: the two Financial Centre toasts; the calm-years reset at panic start (Britain fell off the list before it could be read).
- Fixed on the way: blank Bad Debts figures on the journal line (GetPlayer scope), ledger header alignment, double flag in ranking, calm counter not reset by a 1-month rescued panic.
- Translations: 874 strings, 0 missing/broken/stale in all 10 languages. Pre-prune copy: G:/GameDev/_claude_scratch/i18n_backup_2026-11-09.
- Testing trick: the Vic3 console cannot run effects. To force a panic, add `spec_start_panic = yes` to a button's effect in the BUILT mod (e.g. spec_sguis.txt spec_sgui_bailout), wait 25 s for the hot reload, click, then regenerate. Hovering the hooked button logs harmless "spec_foreign_hit not set" errors (tooltip dry run).
- Open: one-off "Invalid right side during comparison 'none'" at spec_on_actions.txt:9296 (steamers boom-crash note) in a 1921 dev game; "ends in 1 months" plural on the journal line; fastsim.py has a stale hardcoded value; ~290 leftover test-game folders (8.9 GB) in G:/GameDev/_claude_scratch/vic and runs/ older than Nov 8 (~10.5 GB) are for the user to delete (hook blocks recursive deletes).

## 2026-11-10 vanilla-style pass on the 0.9.0 additions (built, NOT uploaded)
- Crisis Ledger and Financial Centres redrawn with vanilla parts: `sort_button_bg` column heads in Title Case
  (`heads()` in market_tab.py), `divider_clean` rows, `empty_state`, ranked country rows as the diplomatic overview
  draws them (tiny_flag, clean_button name opening the country panel, paper_bg on the player's row).
- Wording to vanilla voice: toasts "We are now / are no longer a Financial Centre" (we/our descriptions), modifier
  desc "Effects of the [concept_country] being ...", "Traded Quantity", tooltips header / body / delimiter / details.
- `[concept_interest]` is the DIPLOMATIC interest: never link it for loan interest (plain word instead).
- Checked in the dev game (1916 save): both empty states, both tables, own unplaced row, World Average row,
  green/red figures, row tooltips, gained toast. Translations (round v090i, 10 languages) pass the checker but
  were not looked at in game.
- Left alone, still not vanilla-like: older toast titles in Title Case ("Confidence Near Panic", "Treasury Running
  Out"), older section tooltips, values_table.py "Trade volume" line, depression.py label "Trade".

## 2026-11-10 Crisis Ledger removed (user: "I don't think we need to track historical events in the mod..")
- Gone: the Crisis Ledger panel in the Speculation tab, its recording script (spec_led_* effects, country and global variables), its text and its 24 translations per language (pruned; backup G:/GameDev/_claude_scratch/i18n_backup_2026-11-10b).
- tools/ledger.py moved to G:/GameDev/_claude_scratch/removed/ledger.py (not deleted). Hooks removed from generate.py, journal.py, leverage.py, market_tab.py, tuner.py.
- Kept, not asked about: Financial Centres with "Years of Calm" (it drives the score), the confidence History sparkline.
- 0.9.0 still NOT uploaded.

## 2026-11-10 design direction (user, NOT yet approved to build)
- User's goal: DLC feel; regular, interesting decisions; indirect levers pulled over time toward a planned future state, "no single button".
- Judged the core on 7 tests: strong = tied to vanilla, historical fit; weak = readability (about 17 inputs to confidence, 25 concepts), pacing (panic 1.3% of months, mania 5%); unmeasured = agency (no with/without test), stakes since Leverage.
- User agreed to: stance from day one, boom moments, political price on choices. Then asked for deeper, indirect mechanics first.
- Proposed (awaiting answer): (1) banks learn from rescues (one number, more lending and exposure after each rescue, fades over ~20 years); (2) Credit Policy gated and priced by interest groups in government, weak range before Central Banking; (3) market temperament shown as one steerable line (ownership mix, economic law, trade concentration), absorbing Market Conditions; (4) boom rows show the patient vanilla route (add supply), Restrain/Encourage stay as the costly shortcut. Rule: each new piece absorbs an existing concept, the concept count must not rise.
- Checked: rescue leaves no memory today (spec_rescued is cleared when the panic ends); reforms exist as the regime layer; few interest-group hooks.

## 2026-11-10 Slow Levers design drawn up (user said "All"; NOT yet approved to build)
- design_levers.html: one page + mock-up of the Speculation tab. Four changes: (1) Moral Hazard 0-4, +1 per rescue, in the Bank Rescue section; (2) Credit Policy from day one at half strength, needs a backing interest group in government before Central Banking (vanilla's law rule), add Rural Folk = Loose, Landowners = Tight; (3) Temperament word on the card, replaces Market Conditions, display only; (4) goods row tooltip shows the slow-cooling route, display only.
- Found while checking: Credit Policy ALREADY gives +2/-2 approval (credit_ai.py PREFS: industrialists loose, intelligentsia tight) and rescues already anger trade unions and rural folk (stories.BAILOUT_IGS); a boom's peak already decays 3% a month (generate.py spec_peak_next), so slow cooling already softens endings. Temperament inputs already exist: spec_law_mult, spec_depth, spec_steady, spec_fin_risk, spec_tech_hype.
- Proposed build order: 3 and 4 (no balance change), then 2, then 1 with test games before and after. Concepts 25 -> 23 (merge Correction/Bust/Collapse tooltips into Boom End).

## 2026-11-10 Slow Levers: user verdict and second proposal (NOT approved to build)
- User: only change 1 (banks remember rescues) is worth adding. Changes 2 (credit policy through politics), 3 (temperament word), 4 (boom tooltip) are "surface level and boring". Dropped.
- Diagnosis given: everything feeds one gauge; more inputs or labels on one gauge is not depth.
- Proposed instead, as one loop through base-game things:
  A. Bank carelessness: rises with rescues (old change 1) AND with quiet years; falls only when banks eat a loss. Makes the middle of the gauge matter.
  B. Booms build: a boom makes that industry cheaper to build; levels built in the boom deepen its ending. NOT checked that the game allows a per-industry construction discount.
  C. Busts land on places and people: states holding the industry, owners first, savers too in a mania; who owns is set by vanilla economic law.
- Checked today: credit goes into the investment pool and is clawed back in a panic; boom effects are building throughput by interest tier; radicals only in stories.py and depression.py; no quiet-years timer found.

## 2026-11-10 Mechanics A, B, C built for trial (user: "Let's try it"; in mod/, NOT uploaded)
- All in tools/cycle.py behind tuning CYCLE_ON (default 1; `{"CYCLE_ON": 0}` gives the old behaviour). Checks: `py -3 -B tools/cycle.py` -> "cycle ok".
- A (spec_lax 0..1, shown as Lending Standards: Strict/Cautious/Sound/Lax/Reckless in Budget > Banking): starts 0.4, +1/240 a month without a panic, +0.25 per rescue, falls 0.02 per confidence point lost to boom endings. Scales credit (x0.75..1.25), pull into hot goods and crash cost (x0.5..1.5).
- B: while a group has a booming good, modifier spec_boom_build_<grp> gives building_group_bg_<grp>_construction_efficiency_add 0.1 per step. Overbuilding (market growth since the boom began) deepens the ending (OVER_PER 0.5).
- C: on a Bust/Collapse, radicals in states with a maker building level >= 3: upper strata (lower under cooperative ownership); savers too on a Collapse, or a Bust under laissez-faire; nothing under command economy.
- ENGINE BUG FOUND: a comparison whose right side is a literal with 6 decimals (`>= 0.333333`) logs "Invalid right side during comparison 'none'" and is false. Fixed with `:.3f` in cycle.py (2) and generate.py lines 667, 681 (0.9.0-only toasts; live 0.8.0 unaffected).
- Crashes: ON games crashed at Oct 1869 (cycA) and Dec 1905 (cycB), EXCEPTION_ACCESS_VIOLATION at ...CEAB. NOT ours: the same code offset is in 13 crash dumps from 6-9 Nov (before this code existed), and two reruns of the 1866 save with the mechanics on (cycA2) passed 1869 without crashing.
- Known limits: B's bonus is group-wide and services/electricity/art get none; C leaves no labelled state modifier; conquest reads as overbuilding; 14 new strings untranslated (round v090j deferred); Credit Policy does not move Lending Standards (left out on purpose).
- Scratch tools (session scratchpad, not in repo): cyccmp.py, probecmp.py, crashdist.py. Test builds: _claude_scratch/vic/b_cyc_on, b_cyc_off.
- Trial results (1866-1886, cycA off_01 vs cycA2 on): both cycA2 ON games ran the full 20 years, 0 mod errors. NOTE: on_01 and on_02 are the SAME game (identical GDP per country) - a rerun from one save with one build is deterministic, so this is 1 ON vs 1 OFF sample. For independent samples use different saves (saves/seed_1..8.v3).
  - All countries OFF/ON: panics per 100 country-years 10.0/11.7, conf 54.2/52.6, mania months 6.1%/4.8%, collapses per 100y 5.7/8.0. Top 8: panics 9.1/5.2, conf 55.3/60.4, mania 6.8%/13.9%, leverage 1.55/2.10.
  - End of 1885, 170 countries present in both: world GDP 1388M off / 1420M on, living standard 11.62 / 12.10. GBR 189 / 213, CHI 160 / 213, GER 112 / 144.
  - 1886-1905 (cycB, ON crashed Dec 1905 on the game's own crash): panics 9.2 off / 6.2 on, world GDP ahead with ON most years.
- TUNING PROBLEM (not changed yet): spec_lax saturates. GBR by year: 0.40 (1866) -> 0.006 (1869) -> 0.54 (1871) -> 0 (1874-77) -> stays under 0.1 to 1885. All countries: p10 0.02, p90 0.94. Cause: LAX_PER_CONF 0.02 per confidence point is far stronger than the +0.05/yr quiet rise, and one rescue is +0.25. The "slow lever" is not slow. Building bonus is on 33-50% of months (too common to feel like an event).
- In-game look (dev game, GBR 1916): Budget > Banking shows "Lending Standards - Sound" row with bar and tooltip (runs/shots/lending_standards.png). NOT yet seen in game: tile lines for overbuilding / building bonus, boom-end notification sentences, radicals from C.
- Scratch: endcmp.py (end-1885 GDP on common countries).

## 2026-11-11 Design direction (nothing built)
- Five "advanced ideas" (price vs worth, speculators hoard, one pot of money, booms from player actions, wreckage for sale) did NOT resonate. Reason given: nothing to build toward, it is all reacting.
- Proposed instead: the Exchange - a standing for the capital money market (Provincial/National/International/World Centre, limited seats, rivals), grown by size (Financial Districts, already read as spec_depth), trust (quiet years, soft boom endings, careful banks) and reach; set back by panics and collapses. Existing levers get a growth-vs-safety meaning. Picture: runs/shots/exchange_goal.png. Awaiting the verdict; not designed in detail, not tested for feasibility.

## 2026-11-11 Exchange: go-ahead to implement (owner: "You are orchestrator. Use opus 5.5 subagents to implement")
- Spec: design_exchange.md. Extends tools/centres.py (Financial Centres already ranked the top 5 with prestige and cheaper loans; diplomacy.py already had capital flight). Flag EXCHANGE_ON.
- Baseline build before any change: G:\GameDev\_claude_scratch\vic\b_exch_base (EXCHANGE_ON=0 must match it byte for byte).
- Order: Opus agent 1 rules (spec 1,2,3,5) -> Opus agent 2 screens (spec 4) -> Opus reviewer -> build, checks, on/off sweep on different saves, screenshots. No upload.

## 2026-11-11 Exchange: built (trial, not uploaded)
- Built by two Opus agents, reviewed by a third, fixes by the orchestrator. All behind EXCHANGE_ON (tuning, default 1); with 0 the build is byte-identical to b_exch_base (scratch samedir.py: "138 138 IDENTICAL").
- Rules (tools/centres.py): spec_centre_trust 0..120 replaces quiet months in the score; spec_exch_stand 0..3 (Provincial/National/International/World Centre); spec_exch_known 1..3 (Commodity Exchange / Deposit Banks / Share Market) chosen in event spec_exchange.1 each time a new best standing is reached; spec_exch_national modifier (+2% prestige, National and unlisted only). Hooks in generate.py (hype, flight, credit, boom end, panic, panic over, LOG), diplomacy.py (International+ receive flight without being a Great Power).
- Screens: Budget > Banking row "[capital] Exchange" with tooltip; Financial Centres list third column is now Standing (Years of Calm moved to row tooltips); toasts Our Exchange Rises / Falls replace the Financial Centre gained / lost toasts; concept_spec_exchange.
- Changed from the pitch: "Reach" is not built; "Stock Exchange" became "Share Market" (vanilla has a technology called Stock Exchange); only National has a static modifier (listed places keep the existing place modifiers).
- Reviewer findings fixed: flight text double-counted the multiplier; National prestige stacked on listed places; "+10% credit" untrue at the credit cap (now "up to"); the name clash. Left: no hysteresis for International / World Centre (measure first); toasts use GetPlayer (multiplayer shows the wrong capital, same limit as the other mod notifications).
- Smoke game (runs/sweep_exchS/on_01, 1866-1869): no crash. Script errors in error.log are the base game's or older (same kinds in the 2026-11-10 games); none name spec_exch / spec_exchange. 23 "spec_" load lines also appear with the Exchange off (old: buttongfx, spec_centre_yrs unused, orphaned events spec_depression.90-92, spec_markets.90-102).
- Smoke numbers (scratch exstat.py): 20 of 231 countries reached National, 4 International, 1 World Centre (GBR, lost it to a panic: trust 10, China took place 1 but has no central bank so it stays National and nobody is World Centre). 22 standing changes in 4 years, most per country 3 (KOR). Trust stayed inside 0..120.
- Running: runs/sweep_exchA (1846-1866) and runs/sweep_exchB (1866-1886), on = b_exch_on, off = b_exch_off (both log builds).
