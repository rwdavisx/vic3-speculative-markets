# Rival Exchanges: vanilla rivalries, rival actions

Requested by the user on November 15, 2026, after beta 1.0.6-beta.7/8. The balance freeze is lifted for this feature
only, as for Home of Great Companies. It is built as its own beta after beta.8, with its own suites and the full
release gate.

Revised on November 15, 2026: the user chose to tie rival Exchanges to vanilla rivalries ("seems weird to have two
different types of rivals").

## Problem

- A country names one rival (`var:spec_rival`) through its own Choose button, apart from vanilla's rivalries. Nothing
  happens between the yearly results.
- A player cannot see who has named *them*.

## 1. Rivalries come from vanilla

- A rival Exchange pair is any vanilla rivalry (`rivalry` diplomatic action) where both countries have an Exchange
  (`spec_exch_stand` set). It counts in either direction: we rival them (`every_rival_country`), or they rival us
  (`every_rivaling_country`).
- Removed: `spec_rival`, the Choose button, the 5-year lock, slot limits and the End button. Declaring and ending a
  rivalry is vanilla's job. Vanilla already forbids rivalry with an ally or a defensive-pact partner. Investment
  rights do not end a rivalry: vanilla allows both, and the Exchange rivalry follows vanilla.
- **Yearly contest, once per pair:**
  - The higher Financial Centre score gains trust and the lower one loses it.
  - The base stake is small (**3** trust). It is scaled by the standing gap: an upset (the lower standing wins) gives
    3 × (1 + gap), and the expected result (the higher standing wins) gives 3 ÷ (1 + gap).
  - The loser loses 1.5× on poor relations, as before.
  - A pair where either side has no Exchange is skipped.
- **Old saves:** `spec_rival`, `spec_rival_lock` and `spec_rival_last` are removed on load. No vanilla rivalry is
  created from them.

## 2. Rival actions

Target: a country in a rivalry with us, in either direction, where both of us have an Exchange. Each action has its
own cooldown per target. The numbers are starting points.

| Action | Cost | Effect | Risk / cooldown |
|---|---|---|---|
| **Bear Raid** | 0.5% of our GDP from the treasury | Their Market Confidence -6 over 6 months (-1/month), doubled in a Speculative Mania | Fails 20% of the time, plus up to 60% more as their score exceeds ours. On failure we take the hit instead. 1 year. |
| **Lure Their Capital** | +2 months of our pool income to our Outstanding Credit, so our leverage rises | For 12 months, 10% of their monthly Investment Pool income moves to ours | Our panic threshold rises with the leverage (existing rule). 1 year. |
| **Press Campaign** | -25 influence for 12 months | Their Exchange trust -6 | 30% exposure: relations -20 and our trust -6. 1 year. |
| **Shore Up** | 0.5% of our GDP from the treasury | Halves every rival action against us for 12 months | None. 2-year cooldown, not per target. |

- The last action against each country is logged: what it was, by whom, and its result. The rivalry row shows the
  last action between the two of them.

## 3. AI, both ways

- Once a year, each AI with an Exchange may act against each rival pair: at most one action per rivalry per year.
  - Base chance: 25%. Bold +15%, Cautious -15% (`credit_ai` tempers).
  - The AI picks an action it can afford and that is off cooldown. It Shores Up first when it was hit this year.
- **A player who is targeted gets an event.** It names the action and its effect, with three choices:
  - **Retaliate:** the same action against them, paid as usual, ignoring the cooldown.
  - **Shore up:** if it is available.
  - **Ignore:** +2 trust for keeping calm.

## 4. UI: the Rivalries section (Finance, World tab)

- **Header:** how many countries we rival and how many rival us, counting both vanilla directions.
- **One row per rival country**, rebuilt monthly from vanilla rivalries:
  - the flag and name, plus a direction marker ("we rival" / "rivals us" / both)
  - our score against theirs, and last year's result
  - effects running on either side (raided, lured, shored up), each with months left
  - the last action between us
  - the four action buttons, greyed out with the reason in the tooltip
  - a rival without an Exchange is shown greyed, with that reason
- **World list:** the Choose button goes. The rival column shows the rivalry icon on rival rows. Its tooltip points to
  vanilla's Declare Rivalry.
- **Notifications:**
  - one for wins and one for losses each year, kept as now
  - the event for a raid, lure or smear against us

## Build order and tests

1. **Pairs from vanilla, plus migration cleanup:**
   - rival_network, rival_year, rival_bounds, rival_large_network and rival_notifications rewritten for vanilla pacts
   - rival_migration: the old variables are removed without errors
2. **Player-side actions:** a suite for each action's cost, effect, cooldown, failure and exposure, and Shore Up halving.
3. **AI use and the targeted-player event:** frequency bounds, the event's choices, and a live event check.
4. **Rivalries UI:** static checks, then a live UI check of rows, greyed buttons, tooltips and translations. Rebuild CMF
   if the sidebar changes.

## Open questions

- Whether an action's cost should scale with the target's size, or with ours (now: ours).
