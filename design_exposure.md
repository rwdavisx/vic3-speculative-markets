# Bank Exposure: draft 3 (after Codex rounds 1 and 2)

## Goal
Join the two halves of the mod. Today banks lend into one national pot (`spec_debt`), and a boom ending costs the same
whether or not the banks financed it. With exposure, the player sees which goods the banks have lent into, and a crash in
a good the banks are deep in shakes Market Confidence harder, which is what tips a market into a panic and Bad Debts.

Recognizable: same goods, Investor Interest, buttons, Bad Debts bar and panic. No new source of Bad Debts.
The chain stays: boom ends -> confidence falls -> below the panic line -> panic -> Bad Debts (sized by leverage, as now).

## Historical basis
Banks lent against whatever was booming: railway shares (1840s Britain, 1873 USA), cotton (1837), building land (Vienna 1873).
A crash in a sector the banks had financed became a banking scare; one financed from savings did not. In peacetime governments
mostly steered lending indirectly, by making a sector more or less attractive (railway guarantees; the Bubble Act); direct
guarantees of particular loans came with the 1914 war. The ledger is a proxy for loans, underwriting and collateral together.

## Mechanic
State per country: `spec_exp_<g>`, the **share** of outstanding credit lent into good g (0 to 1; the rest is general lending).
Storing a share, not money, means every place that shrinks `spec_debt` (repayment, panic clawback, depression recall, the
legacy-save write-down) leaves the shares right without touching them. Codex checked: the only place that adds credit is
generate.py:886 (leverage.py:292 only rebuilds pre-clawback debt before halving it).

1. **Lending** (generate.py:886): pull_g = market-value share (`spec_mv_<g>` / market value) x heat, heat = how far
   `spec_hype_<g>` sits above Calm, capped. Encourage needs no extra rule: it already raises heat. A restrained good's pull is
   halved (harder to raise money, not forbidden; restraint also eases heat toward Calm, so its pull falls to nothing over months).
   Into booms: boom_share = min(total pull, EXP_SHARE_MAX), and new_g = credit x boom_share x pull_g / total pull.
   With D = debt after this month's repayment, before lending: share_g = (share_g x D + new_g) / (D + credit), every month there
   is new credit, including all-general months. Missing shares count as 0. When debt reaches 0, clear the shares. Shares go in
   the shutdown cleanup list.
2. **No fade:** loans into a good stay until repaid. Banks could not pull out of a troubled sector smoothly (1873 railroads);
   a restrained good's share only shrinks as new lending goes elsewhere.
3. **Exposure in months:** exp_months_g = share_g x `spec_lev` (leverage is already measured against the stabilized income).
4. **Boom ends:** the confidence loss today is `spec_risk_raw_<g>`. It becomes
   `spec_risk_raw_<g>` x (1 + EXP_PER_MONTH x exp_months_g), at most EXP_MULT_MAX, applied inside spec_risk_raw itself
   (generate.py:494), so every forecast, Booms at Risk "all at once" and the AI ranking inherit it; then the existing sum,
   `spec_crash_scale` and monthly cap, unchanged. Starting values: +0.1 per month, max 1.5 (exp1: +0.25 and max 2 doubled panics). Unfinanced booms hit as today; a boom
   financed with 2 months of income hits 1.5x. Old saves and early games are unchanged until banks lend.
5. **Restraint is not immunity:** the monthly cost of a restrained deflation (`spec_restrain_cost_<g>`) takes the same
   multiplier. Today that cost sits outside the monthly crash cap (generate.py:777-781); restraint and crashes now share it, so a
   month's confidence loss from booms has one ceiling. A restrained boom still escapes the crash's damage to its companies
   (companies.py:118): that stays the reward for restraining.
6. **Panic and Bad Debts:** unchanged.

Worked example: Britain has 6 months of income lent, a third of it in steel (2 months). If steel Collapses, its confidence hit is
1.5x today's, enough to push a Steady market below 25 into a panic, and the panic's Bad Debts follow from 6 months of leverage as
now. If Britain restrains steel, the crash and its damage to steel companies are avoided, but the wind-down drains confidence at
1.5x a Correction's rate for about a year: safer, not free.

## Player decisions it creates
- **Which boom to cool:** the one the banks are deepest in, not just the hottest one. A hot but unfinanced boom is less dangerous.
- **Priorities:** with Authority for one intervention, one player restrains heavily financed steel to protect the banks; another,
  preparing for war, keeps steel running and restrains grain, accepting the financial risk.
- **Credit Policy and booms connect:** Loose credit while a few goods are hot concentrates the banks in them.
- **Timing:** restrain before the banks pile in and the wind-down is cheap; after, it costs more.

## AI
The AI already restrains its riskiest affordable boom (levers.py ai). It ranks by spec_risk_raw, so it inherits financed risk.
Let a heavily financed boom qualify below the confidence-60 gate. Keep its affordability and release rules.

## UI
- Investor Interest row tooltip: "Bank loans: X% of credit (Y months of income). Bank loans make its ending xM as hard."
  A multiplier, not a "because of the loans" amount: under the monthly cap that amount is not well defined.
- Boom-end notification: the same line.
- No badge on the goods rows.

## Charts
Vanilla chart types only, inside sections that already exist, so they read as part of the game's UI. Charts show; the
actions stay on the existing buttons. The goods list stays the main view, with the charts as a summary above it.

1. **Banking tab, "Where the Banks Have Lent"** (vanilla pie chart + list, as World Market's importers/exporters).
   One slice per good with a share, plus General. Beside it, vanilla's list: good icon, share of credit, months of income.
   Data: a script variable list of the exposed goods, the way interest_list already feeds its rows
   (`GetList('spec_goods_w...')`); slice value = the good's `spec_exp_<g>`, colour = the good's colour if it has one, else a
   fixed palette.
2. **Banking tab, "Credit History"** (bars, the same pattern as the Speculation tab's Market Confidence History,
   spec_hist1..N). Leverage month by month, each bar coloured by the Leverage bar's zones: safe (to 3), risky (to 8),
   dangerous.
3. **Speculation tab, Investor Interest section, "How Much of Our Trade Is Booming"** (vanilla pie chart). Four slices: the
   share of trade Calm, Keen, Eager and Feverish (from `spec_mv_<g>` by `spec_word_<g>`). Clicking a slice sets the existing
   Investor Interest filter to that level.

Not doing: charts inside tooltips (too small; a text line says more), line graphs (vanilla plotlines only take the
engine's own trends, not script values; bars replace them).

First build step: a test pie chart fed from a script variable list, checked in game, before the rest. If the pie chart can't
take script values, fall back to a stacked horizontal bar built from widgets (the History pattern).

## Cut from 0.9
The Sectors filter row.

## Saves
Shares start at 0: all existing credit is general. Exposure builds from the first month of lending.

## Open questions
1. Constants: EXP_SHARE_MAX, EXP_PER_MONTH, EXP_MULT_MAX, restrained pull.
2. One shared cap for crashes and restraint: check in sweeps that it doesn't make restraint cheaper in crisis months.
3. Script cost: 48 shares per country, updated in months with new credit. Measure in a sweep.

## Tests
- Sweep against 0.8: panics per country per decade, Bad Debts totals, AI restraint use (tools/sweep.py).
- Self-check in the generator: shares stay in 0..1 and sum to at most 1.
- In game: tooltips, notification, the three charts (slices add up, colours readable, click-to-filter works).
