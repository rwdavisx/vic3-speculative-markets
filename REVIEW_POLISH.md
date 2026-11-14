# Speculative Markets — Polish Review

The reviewers confirmed 162 findings. Many were the same problem seen from different angles, so they merge into about 105 separate issues. The most serious is that the generator can no longer rebuild the mod you ship. After that, the main themes are:
- tooltips and alerts that describe older versions of the mod;
- a few balance loopholes in the Exchange (rivals, charters, trust);
- about a third of the text still being in English in every translation;
- leftover code from retired features.

## Fix first (bugs and wrong information)

1. **Rebuilding the mod today would delete whole features** (high). The file that held your feature switches (`tools/tuning.json`) is gone, and every switch now defaults to "off". A normal `generate.py` run would quietly remove Paths to Renown, charters, rivals, the Pledge, Great Issues, the credit brake and the trust links. `check.py` would still say OK. Set the defaults to 1 in the source. Keep the Rules switch on too, because Paths to Renown and the Pledge depend on it. Then add a check that fails if the built mod contains these features while their switches are off. `tools/centres.py:46,49,96,104,111,435,1409`, `tools/levers.py:42`, `tools/diplomacy.py:90`, `tools/notify.py:81-91`, `tools/check.py`
2. **Clicking a good in the Speculation list does nothing** (high). The click asks for "the market in view", and the Finance window doesn't know which market that is. Use the player's own market instead, written the way vanilla does it. This fixes all 78 rows. `tools/interest_list.py:555`
3. **Alerts and the journal send players to tabs that no longer exist** (medium). The texts say "Budget panel's Banking tab" and "Speculation tab of the Market panel", and the alert buttons open vanilla panels at tabs that aren't there. Point the text to the Finance window. Remove or redirect the `open_panel` lines, and delete the leftover tab labels. `tools/journal.py:751,770,779,792,876,904,915,920`, `tools/market_tab.py:1599-1600,1724-1725`
4. **The Exchange encyclopedia entry describes the old "names" system** (medium). It says an Exchange holds 1 to 3 names that it wins and loses. The real rule is 1 to 4 specialities that you choose and keep for at least 5 years. It is also longer than any vanilla concept, and it switches to "us/our" partway through. Keep the charter sentence and replace the rest with a short third-person summary that points to the Paths to Renown rule. `tools/centres.py:1216-1220, 3295-3315, 3177`
5. **Standing bar fills up wrongly early in the game** (medium). It reads the 1st and 5th ranking places before they exist. As a result, every country shows a full World Centre bar in the first month, and a full National bar while fewer than 5 markets are ranked. Guard each read and give a fallback value that leaves the bar empty. `tools/centres.py:2745`
6. **The lending gauge says "Banks lend" when they can't** (medium). Lending is actually blocked during Bad Debts and the World Crash. Add those two cases to the gauge and to the Credit Lent tooltip. The World Crash needs a flag the UI can read. `tools/market_tab.py:1615,1741,1745`, `tools/depression.py:191-195`
7. **The Credit Lent breakdown leaves out three of its own factors** (medium). Missing rows: the Exchange (charter and specialities), Lending Standards and banking reforms. The "Lending rate" word can also disagree with the amount shown. Add the rows and a full-rate value for the word. `tools/market_tab.py:1745`, `tools/generate.py:401`
8. **The Shaken tooltip understates how long a panic lasts** (medium). It shows the base length, but legitimacy and the Currency School change the real length by up to 1.5 times. Show `spec_panic_months_trust` instead. `tools/market_tab.py:1685`
9. **The World Centre requirement leaves out Central Banking** (medium). Add ", with [Central Banking]" to match the International line. The same edit fixes both tooltips. `tools/centres.py:3202`
10. **Journal stages always say "above 75"** (medium). The Heightened rule moves the threshold to 70, and the script actually triggers at 75 or more. Use the live value and say "at X or more", as the alert already does. `tools/journal.py:855,859` (and the same lines in the translations)
11. **The Bad Debts trust drain is cancelled out** (medium). The normal +1 a month gain still runs while there are Bad Debts, so trust doesn't fall the way the tooltip says. Stop the quiet-month gain while Bad Debts last. `tools/centres.py:1952-1954, 2114-2120`
12. **Changing charter costs 25% of trust, not the 50% the rule promises** (medium). The cost goes through the "losses of trust" multiplier, which Deposit Banks halves. Cut trust directly instead. `tools/centres.py:604`
13. **Capital-flight bonuses promise flight a country can't receive** (medium). Below International, only Great Powers receive capital flight. But the Pledge, Safe Harbour and Open Door all promise more flight with no condition. Add the condition that the Exchange panel already uses. `tools/centres.py:37, 3016-3017` and the speciality effect lines
14. **Leaving the market economy leaves Exchange modifiers behind for good** (medium). Trust and speciality modifiers stay on the country, and trust and charter carry over when it comes back. Clean them up in the monthly "no market" branch, and add the variables to the shut-down list. `tools/centres.py:2188-2190`, `tools/generate.py:575`
15. **AI charter changes keep specialities the new charter forbids** (medium). Those specialities then block a slot and keep their modifier forever. Run the same "stop" loop the player's charter change uses. Don't add the trust cost or lock for the AI. `tools/centres.py:1857-1862`; also fix the comment at `:601`
16. **Opening a goods, country or company panel from Finance leaves Finance open** (medium). You end up with two windows stacked on the left, and Finance pops back when the other one closes. Clear `spec_finance` on those clicks. `tools/interest_list.py:555`, `tools/centres.py:1712, 2518`, `tools/company_section.py:202`
17. **"Choose a speciality" mode survives closing the window** (low). The slot stays highlighted and armed, so one stray click starts a path. Clear it when Finance opens and when it closes. `tools/generate.py:1853`, `tools/goods_panel.py:165`, `tools/market_tab.py:1414`
18. **Speciality bar tooltip shows "1st, : 0" before any leader exists** (low). Show "No Exchange leads in this yet" until a leader exists. `tools/centres.py:1309-1312`
19. **A path's leader is never cleared when nobody qualifies** (low). The bar keeps naming a country that is out of the running. Add an "else, clear" branch. `tools/centres.py:546-581, 590`
20. **Automatic rival endings skip the cleanup, and dead rivals are never caught** (low). Call `spec_rival_end` instead, and end the rivalry if the rival no longer exists. Keep the 5-year lock. `tools/centres.py:1625-1631`
21. **The selected Great Issue icon is clickable but does nothing** (low). Make it a passive marker. `tools/levers.py:450-454, 485`
22. **Clicking "Investor Interest" twice sorts the list back by Goods** (low). Make the click set the sort, not toggle it, and update the self-check. `tools/interest_list.py:638, 786`
23. **The "Show Interventions" filter leaves empty groups and a blank list** (low). Hide categories with no intervention, and add a "No goods have an intervention in effect" line. `tools/interest_list.py:656-663`
24. **Tooltips that leave out or round off real effects** (low):
    - the score description ("6 months of income" should mention the square root);
    - first place's credit-limit bonus;
    - the panic's living-standard hit and radicals;
    - Bad Debts trust loss shown as "1" instead of 0.8%;
    - rival losses shown as 8% instead of 7.5%, before modifiers;
    - the company slump growing with corporate technologies;
    - Long Depression status lines missing loan interest.

    `tools/centres.py:3116-3119, 3144, 3191, 1814`, `tools/market_tab.py:1700-1701`, `tools/concepts.py:65`, `tools/depression.py:810`

## UI and layout

1. **The goods panel row is about 42px wider than the panel in your own market** (medium). Narrow the bar segments (34 to 30), the spacers (12 to 8) and the risk column (90 to 80), and add a width check. `tools/goods_panel.py:39, 69, 100-143`
2. **Choosing a speciality is a hidden two-step mode** (medium). Rows give no sign that they have become clickable. Drop the pick mode: let a valid row be chosen directly and highlight the rows you can pick. `tools/centres.py:943-969, 1112-1130, 1328, 1367`
3. **You can't see what a speciality gives at 1st, 2nd or 3rd place until after you choose it** (medium). Put the place rewards in the row tooltip and delete the orphaned "Choose" tooltip. `tools/centres.py:1322-1323, 1334-1340`
4. **"Drop" is disabled for 5 years with no time remaining shown** (medium). Count the lock down monthly, as the Credit Policy cooldown does, and show "Can be dropped in N months". `tools/centres.py:698, 1375`, `tools/generate.py:1021-1025`
5. **Specialities lost to a Standing fall disappear without a word** (medium). Say which one was given up in the Standing-down notification. `tools/centres.py:770-772`, `notification_spec_exch_down_desc`
6. **The rival section shows "Our score" with no rival, and both bars stay full above 100** (low). Hide our bar when there is no rival, and scale both bars to the larger score. `tools/centres.py:1733, 1757`
7. **The Pledge button breaks the Banking button column** (low). Right-align it at -20 and give it 5px of space from the panic card. `tools/centres.py:2993-3010`
8. **Locked speciality slots show only a padlock** (low). Show the existing "Opens at National Standing" text on the card itself. `tools/centres.py:974`
9. **Money tallies overflow their 90px box in Paths to Renown** (low). Set BW to 112 and add an elide. `tools/centres.py:991, 1170-1178`
10. **Exchange tab sections end with uneven 20, 16 and 10px gaps** (low). Remove the three trailing spacers. Keep the one between the score bar and the trust bar. `tools/centres.py:2782-2784, 862-864, 1208-1210`
11. **Rankings Standing bands look like buttons but do nothing** (low). Make them plain widgets with the same background. Also hide "Markets: 0" when the band already says "No market holds this Standing". `tools/centres.py:2541-2582`
12. **German "Pressures" runs under the chips on the mood card** (low). Cap the label width and shorten the German word. `tools/market_tab.py:526-552`, `tools/i18n/german/2.json:34`
13. **The Banking tab doesn't show where the Charts section ends** (low). "Credit Policy" looks like a third chart. Make Credit Policy and Bank Rescue collapsible sections too. `tools/market_tab.py:1356-1358`
14. **The Finance window opens on the slow Exchange tab** (low). Put Speculation first. `tools/market_tab.py:1346-1361`
15. **The score label is left-aligned and the trust label under it is centred** (polish). Centre both, with the same offset. `tools/centres.py:2741-2785`
16. **Bar side margins differ (12, 20 and 24px)** (polish). Add one `BAR_W = W - 40` constant and use it everywhere. `tools/market_tab.py:25, 465, 805, 912-919`, `tools/centres.py:2762, 2782`
17. **The Standing rungs touch each other, while every other card row has 10px gaps** (polish). `tools/centres.py:2853-2880`
18. **Rankings headings** (polish): "Country" sits over the rank numbers, and the speciality icons aren't centred under their heading. `tools/centres.py:2451, 796-804`
19. **Three heading styles in one window** (polish). Paths to Renown uses plain small text, and the interest list asks for a 20px header that renders at 30. `tools/centres.py:1189-1201`, `tools/interest_list.py:629-641`
20. **The journal header is 128px tall; vanilla's is 120** (polish). `tools/journal.py:532, 539, 546`
21. **Smaller items** (polish):
    - The back button is disabled on Exchange. Make it close the window and give it the back key.
    - Leverage months are shown twice in a row. Trim the "Owed" line.
    - The Exchange header repeats the Standing. Show world place instead.
    - The "Open Finance" button has no tooltip.
    - The panic block's comment is out of date.

    `tools/market_tab.py:1406-1412, 1748, 1348, 626`, `tools/goods_panel.py:186`

## Wording and language

1. **Two encyclopedia entries are both called "Exchange"** (medium). Rename the ranking concept "Leading Exchange". Keep the "Exchange score" links reading the same by giving them their own display text. `tools/centres.py:3112` and every `[concept_spec_financial_centre] score` (`:1815, 2810, 3058, 3238, 3240, 3277, 3297`)
2. **Exchange trust reuses Market Confidence words** (medium). Shaken, Wary and Steady mean two different meters. "Wary Investors" can sit next to "Shaken Exchange". Rename the trust levels Distrusted, Doubted, Respected, Trusted. Leave "Sound" alone, because it means the same idea everywhere. `tools/centres.py:2650, 3318-3319`
3. **Old wording survives: "name", "won by", "known as"** (medium). Use one set of words: a "path to renown" is ranked, a "speciality" is a path the state has chosen, a charter is "granted". `tools/centres.py:1259-1260, 1335, 1393-1402`, the source of `notification_spec_names_new_desc`
4. **Effects are worded two ways on one row** (low). "Booms run hotter" and "Boom heat" are the same effect. Use one set of short labels. `tools/centres.py:1214, 1223, 1291`
5. **The old term "Financial Centres" is still in the Great Issue tooltip and the sidebar button** (low). Its numbers aren't highlighted either. `tools/levers.py:539`, `tools/market_tab.py:1714`
6. **The top confidence modifier is "Reckless Investors"** (low). It should be "Manic Investors", to match the other bands and stop clashing with "Reckless" Lending Standards. `tools/generate.py:1790`
7. **The bank rescue is also called "supporting the banks"** (low). Use "lend to the banks" throughout. `tools/journal.py:849, 891, 975`, `tools/generate.py:1773`, `tools/tech_ties.py:42`
8. **"Stand Behind the Exchange" is really a bank-rescue pledge** (low). Rename it "Pledge to Rescue the Banks", reword the broken-pledge texts, and add that each rescue loosens Lending Standards. `tools/centres.py:3013-3038`
9. **"which also ends this Approval" is unclear** (low). Name the Industrialists. `tools/generate.py:1817`
10. **"Safe harbor" and "Safe Harbour" both appear** (low). At minimum fix `tools/journal.py:994`. Decide on British or American spelling for Centre, Harbour and Speciality, and change display text only, never keys.
11. **Plurals written as "[concept]s"** (low). The "s" sits outside the link and comes out unstyled. Use the plural forms, or reword. `tools/journal.py:971`, `tools/centres.py:2819`, `tools/market_tab.py:1640`
12. **`#low` is a frontend-only format, so the dimming never shows in game** (low). Use `#lore` for history notes and `#grey` for dim labels. `tools/centres.py:1293-1372`, `tools/market_tab.py:1707`
13. **Awkward sentences** (low) in confidence and excess texts, notifications and Capital Flight. `tools/journal.py:895, 976`, `tools/concepts.py:84`, `tools/notify.py:85, 96`, `tools/market_tab.py:1820, 1828, 1440`
14. **Interest group and pop names are typed in by hand** (low), including "Petty Bourgeoisie" where vanilla says "Petite Bourgeoisie". Use the vanilla keys (`_no_icon` for pops). `tools/market_tab.py:1471, 1700-1701`, `tools/generate.py:1616`
15. **Whole clauses in Title Case, and negative multipliers like "x-0.6"** (low). `tools/market_tab.py:1283, 1652, 1659, 1789, 1812, 1818`, `tools/diplomacy.py:28`
16. **"Leverage" has the same name as vanilla's power bloc Leverage** (low). Use "Credit Leverage". `tools/concepts.py:16`
17. **The Intervention concept doesn't mention the ±10% throughput effect** (low). Don't add the Great Issue to it. `tools/levers.py:529`
18. **Polish**:
    - "a month" vs "per month": use "per month" for rates.
    - Missing hyphens: "long-run", "half-built".
    - Maths jargon: "square root of it, times 10".
    - "No contest yet" should be "No result yet".
    - Write "[Exchange] Standing" as a link outside the Exchange tab.

    `tools/market_tab.py`, `tools/centres.py:2828-2834, 1828`, `tools/interest_list.py:726`, `tools/concepts.py:84`, `tools/journal.py:851`

## Design and logic

1. **Rivals are a free trust gain that never touches the other side** (high). Naming the weakest market at your Standing wins +5% trust every year. The named market loses nothing unless it named you back, even though the rule says it does. A World Centre can't take part at all. Apply results to both sides. Only allow naming a market that scores at least as high as yours. Say that a World Centre answers challengers. `tools/centres.py:1553-1586, 1644-1683`, loc `SPEC_RIVAL_RULE`
2. **Loan interest cuts stack to about -45% from the mod alone** (medium). On top of vanilla's -50% for Great Powers, loans become nearly free. Reduce Sound Lending (-20%), Sound Finance (-10%) and the Steady band. Aim for a total of about -25%. `tools/centres.py:466`, `tools/journal.py:314`, `tools/generate.py:158`
3. **Every country starts at 0 trust ("Shaken")** (medium). That means +10% loan interest and -2 Industrialist approval from 1836 for about 30 months. Start trust at Steady (half of the maximum). `tools/centres.py:1956`
4. **Deposit Banks is the only charter with no downside** (medium). It halves every trust loss, stacks to x0.375 with Sound Lending, and protects its own Safe Harbour title. Change `KNOWN_LOSS` to 0.75 and fix the self-check. `tools/centres.py:41, 3370`
5. **A Great Issue on a restrained good gives +25% score for 2 years with no risk** (medium). Restrain stops the boom from ending, so the issue never resolves, and when it lapses there is no cooldown. Set the cooldown when the issue is floated, and block Restrain and the Issue on the same good. `tools/levers.py:213-238, 265-290`
6. **Speciality drawbacks start at full strength while benefits build up over 12 months** (low). Benefits also keep paying for up to a year after you drop a speciality. Make the drawbacks build up and fade the same way. `tools/centres.py:486`
7. **AI Exchanges pick specialities in list order** (low). Every AI takes Busy Floor, then Sound Lending. Order the picks by how close the AI is to each leader. `tools/centres.py:787-793`
8. **Safe Harbour leaders tie at maximum trust** (low). The winner then depends on list order. Use quiet months as a tie-breaker. `tools/centres.py:449`
9. **An unlisted International Exchange gets less prestige than a National one** (low). Give the +2% to every Standing above Provincial that isn't listed. `tools/centres.py:2067, 2076, 3216, 3299-3301`

## Realism

1. **Bad Debts can cut a whole country's output by about 37% and last about 13 years** (medium). Even the Great Depression was barely worse. Make throughput a setting (about 0.4% per point), and speed up the fade (about 0.6) so recovery takes 2 to 5 years. `tools/leverage.py:44, 129`
2. **Loans get dearer as confidence rises** (medium). Steady gives -10%, but Buoyant and Mania give nothing. Make the rate fall steadily as confidence climbs. `tools/generate.py:158`
3. **Every Exchange is named after the capital** (medium). This gives "Washington Exchange", "Bern Exchange", "Ottawa Exchange". Name it after the state with the most Financial District levels, with a margin before switching so the name doesn't flip back and forth. `tools/centres.py:3039, 3092, 3165, 3271`, `tools/notify.py:70`
4. **"Deposit Banks" isn't a kind of Exchange** (low). "Chartered as Deposit Banks" doesn't read right. Rename it "Money Market" and keep its effects. `tools/centres.py:3204` plus the hand-written prose
5. **A Share Market can be chartered without the Stock Exchange technology** (low). Gate the charter on it, for both the player and the AI. `tools/centres.py:612-625, 1857-1862`
6. **A second crisis around 1929 is still called "The Long Depression"** (low). Call the second one "The Great Depression", using the existing crisis counter. `tools/depression.py:78, 112, 759, 801`
7. **A trade agreement ends a rivalry** (low). Historically, London and Paris stayed rivals through their 1860 trade treaty. Use an alliance, defensive pact or investment rights instead. `tools/centres.py:1548-1550, 1818`
8. **Power plants are missing from investor interest** (low). Add electricity. Do not add gold, because its price is fixed and could never boom. `tools/generate.py:244`
9. **The tariff event leaves out landowners** (polish), although landowners drove the 1879 and 1892 tariffs. `tools/depression.py:664-667, 767-770`

## Performance

1. **One large total is recalculated 96 times in every lending month, for every country** (medium). Store it once in a local variable. `tools/exposure.py:53-60`
2. **Decentralized countries run the whole monthly engine** (medium). That is about 199 countries doing work that has no effect. Give them a market multiplier of 0. No divide-by-zero guard is needed, because a minimum of 1 already prevents it. `tools/generate.py:371`
3. **Risk values for quiet goods are worked out in full only to give 0** (low). Do the multiplications only when a good is active. `tools/generate.py:519-521, 663-667`
4. **The sorted Speculation view copies the same 40 KB row 30 times** (low). That is 1.2 MB of the GUI file. Make it one type. `tools/interest_list.py:666-683`
5. **The company building pass re-checks 41 building types twice** (low). Drop the duplicate check. Only skip goods whose interest didn't change on runs that aren't sweeps. `tools/companies.py:168-194`
6. **Small savings, worth doing only if the game slows down** (low/polish):
    - a guard on the diplomatic-play scan;
    - AI market owners building Finance figures nobody sees;
    - four separate passes over the goods for the tab;
    - a law check in AI building scoring;
    - lever sums worked out twice;
    - the bank chart running with no debt;
    - debug-only values shipping in the release.

    `tools/economy.py:45`, `tools/generate.py:321-323, 529-533, 723`, `tools/levers.py:182-183`, `tools/charts.py:27-47`, `tools/cycle.py:97,103`, `tools/exposure.py:42`

## Release readiness

1. **About a third of the text is still English in all 10 translations** (high). That is 367 strings, roughly 6,000 words, mostly the Exchange, Paths to Renown and Rankings. The tab bar reads "Exchange | Spekulation | Bankwesen | Rankings", and 8 encyclopedia pages have translated titles over English text. Start with the tab names, the Exchange concepts, the Standing tier names and the descriptions. Skip dead or out-of-scope keys first. `tools/i18n/<lang>/*.json`, `tools/i18n.py`
2. **The Workshop page and the version describe the old mod** (medium). The page still says Market panel and Budget panel, lists files the mod no longer changes, and doesn't mention the sidebar override, Finance or the Exchange. Rewrite it, bump everything to 1.0.0 together, and add a 1.0.0 entry to the changelog. `workshop/description.bbcode:29,40`, `tools/generate.py:170`, `mod/.metadata/metadata.json`
3. **Retired code still ships** (low):
    - Exchange Rules: no button can use them, but Paths to Renown and the Pledge depend on their switch.
    - Rival history: still recorded every year with nothing to show it.
    - About 60 to 80 unused text keys.
    - Two notifications that are never posted, and one more that can never fire.
    - Three unused textures.

    Untangle the switches first, then delete. `tools/centres.py:49, 96, 435, 1416-1541, 1861, 1978-1986, 2401, 3253`, `tools/notify.py:81-96`, `tools/generate.py:58, 2091`, `tools/mapmode.py`
4. **`check.py` misses the real release risks** (low). It doesn't check for debug lines, a build that no longer matches the switches, or notifications that are never posted. `tools/check.py:55-75`
5. **The translation tools hide problems** (low). The export is stale. A small English edit silently drops finished translations (30 per language so far). Generation never reports missing strings. `tools/i18n.py:77-78, 161-211`
6. **Exchange good news is filed under "Speculation Warnings"** (low). Players can't mute it without muting panic warnings. Add an "Exchange News" group. `tools/notify.py:72-100`, `tools/centres.py:2414`
7. **Tidy-up** (polish):
    - gameplay values misnamed `spec_log_*`;
    - generated code pasted at column 0;
    - unneeded `is_shown` lines;
    - French spacing and apostrophe slips;
    - stale comments and plan documents.

    `tools/leverage.py:32-39`, `tools/generate.py:1515`, `tools/leverage.py:378`, `tools/i18n/french/*.json`, `tools/centres.py:48, 2201`, `NEXT_STEPS_PLAN.md`, `design_1.0.md`

## Suggested order of work

- Fix the generator defaults (Fix first #1) before any other change, then confirm that a plain rebuild matches today's `mod/`.
- Fix the clickable rows, the dead alert links, the Standing bar and the Finance-window stacking. These are what players hit first.
- Correct the wrong tooltips and the Exchange concept text in one pass. While doing that, settle the vocabulary: "Leading Exchange", the new trust words, path / speciality / charter.
- Close the balance holes: rivals, Deposit Banks, the Issue + Restrain combination, trust starting at 0, loan-interest stacking, Bad Debts severity.
- Clean up the speciality UX: no pick mode, rewards shown before choosing, the lock countdown, the drop notice. Then do the layout and spacing fixes.
- Untangle and delete the retired Rules, rival-history and dead text, so translators don't work on dead strings.
- Translate the remaining strings, starting with the tab bar and concepts. Then rewrite the Workshop page and bump to 1.0.0.
- Do the performance items last, and only the first two unless the game feels slow.