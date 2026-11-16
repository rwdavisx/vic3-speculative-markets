# Rival Exchanges: vanilla rivalries, rival actions

Requested by the user on November 15, 2026, after beta 1.0.6-beta.7/8. The balance freeze is lifted for this feature
only, as for Home of Great Companies. It is built as its own beta after beta.8, with its own suites and the full
release gate.

Revised on November 15, 2026: the user chose to tie rival Exchanges to vanilla rivalries ("seems weird to have two
different types of rivals"). Shipped in beta.11.

Revised again on November 16, 2026, for beta.12: the user chose to separate Exchange rivals from vanilla rivalries again.
The forced tie made Britain's only rival Russia, a contest Britain won 144 to 19 every year. Section 1 below is the
beta.12 rule; sections 2 and 3 are unchanged apart from where noted.

Revised late on November 16, 2026, for beta.12, after the user's in-game review of the UI: Shore Up is per rival;
costs and effects scale with the two Exchanges' sizes; the AI picks rivals it can beat and plays each contest; the UI
was rebuilt (section 4). The user asked for each of these; balance numbers are starting points, not measured.

Revised on November 16, 2026, for beta.12, at the user's request: the yearly contest became a tug of war settled every
5 years, in five bands, that actions push; actions work against Exchanges rivaling us too; Hold the Line added;
maintenance by the rival's Standing and a relations cost. The balance freeze is lifted for these rules (the user's call).

## Problem

- A country names one rival (`var:spec_rival`) through its own Choose button, apart from vanilla's rivalries. Nothing
  happens between the yearly results.
- A player cannot see who has named *them*.

## 1. Exchanges name their rivals (beta.12)

- An Exchange names its rivals itself, in the variable list `spec_rv_chosen`. Vanilla rivalries play no part.
- A rival Exchange pair exists when either country named the other and both have an Exchange (`spec_exch_stand`,
  score and trust set).
- **Any number, any Exchange (beta.12 rework, the user's call after seeing it in game):** a player may rival any
  country with an Exchange, with no slot cap and no Standing reach.
- **Upkeep:** influence maintenance by the rival's Standing: 25, 50, 100 or 150 (`UPKEEP`, as vanilla pacts). One
  static modifier `spec_rv_upkeep` (`country_influence_add = -1`) re-added by `spec_rv_count` with
  `multiplier = spec_rv_upkeep_total`. The AI pays it too.
- **Relations:** naming a rival costs -10 relations at once, then -1 a month down to Poor (`REL_HIT`, `REL_DRIFT`; vanilla's
  rivalry drifts to -20).
- **Kept a year:** a new rival cannot be ended for 365 days (`spec_rv_keep`). This stops rivalling just before the
  contest and ending it after.
- **Ending:** the toggle in the Leading Exchanges list (the rows no longer carry it). A rival who named us cannot be ended by us. Dead countries are
  removed from the list each month.
- **Where:** a rivalry icon button (`spec_sgui_rv_toggle`, vanilla `button_icon_round_action` with the rivalry
  icon, lit while we rival them) in the Rival column of the Leading Exchanges list, with a small lock in a rivalry's
  first year. Its tooltip: the monthly cost and the relations cost.
- **The contest, a tug of war settled every 5 years** (`ROUND`, global `spec_rv_round` counts the years), once per pair:
  - The bar (`spec_rv_rope`, -1 to 1 from one side) starts from the score lead as a share of the higher score.
  - Each action that works pushes it 0.1 toward the actor (`PUSH`), at most 5 pushes a side (`PUSHES`), stored as
    unary lists `spec_rv_push_1..5` on the pusher. A failed Bear Raid or an exposed Press Campaign pushes it the other
    way. Hold the Line undoes one of theirs. Every push is cleared when the round settles.
  - Five bands: within 0.1 a draw (nothing); past 0.1 a win, 2 x the stake; past 0.4 a decisive win, 4 x the stake and
    10% of the loser's investment pool income for 12 months (unless already lured). `DRAW`, `DECISIVE`, `WIN_X`, `BIG_X`.
  - The base stake (**3** trust) is scaled by the Standing gap: an upset gives 3 x (1 + gap), the expected result
    3 / (1 + gap). The loser loses 1.5x on poor relations.
  - A pair where either side has no Exchange is skipped. Results: lists `spec_rv_won`, `spec_rv_lost`, `spec_rv_tied`,
    and `spec_rv_big` for a decisive one.
- **Old saves:**
  - Stable 1.0.6 and beta.8 saves named one rival in `spec_rival`. It becomes a named rival, if that country is alive.
    `spec_rival_lock` and `spec_rival_last` are removed.
  - Beta.11 took its pairs from vanilla rivalries and stored none, so its pairs simply stop counting. The AI names new
    rivals on the first pass. A player names theirs by hand.
  - No vanilla rivalry is created or removed.

## 2. Rival actions

Target: a rival Exchange pair, in either direction (section 1). Each action has its
own cooldown per target. The numbers are starting points, at two Exchanges of equal size.

- **Size (beta.12):** `spec_rv_vs`, their Exchange score over ours, clamped 0.5 to 2 (`VS_LO`, `VS_HI`). Gold and credit
  costs are multiplied by it, so a larger rival costs more to act against or shore up against. The effects of Bear
  Raid, Lure and Press are multiplied by its inverse (`spec_rv_heft`), so a larger Exchange hits harder. Press's
  influence cost and Shore Up's halving are not scaled. Tooltips show this pair's numbers.

| Action | Cost | Effect | Risk / cooldown |
|---|---|---|---|
| **Bear Raid** | 0.5% of our GDP from the treasury | Their Market Confidence -6 over 6 months (-1/month), doubled in a Speculative Mania | Fails 20% of the time, plus up to 60% more as their score exceeds ours. On failure we take the hit instead. 1 year. |
| **Lure Their Capital** | +2 months of our pool income to our Outstanding Credit, so our leverage rises | For 12 months, 10% of their monthly Investment Pool income moves to ours | Our panic threshold rises with the leverage (existing rule). 1 year. |
| **Press Campaign** | -25 influence for 12 months | Their Exchange trust -6 | 30% exposure: relations -20 and our trust -6. 1 year. |
| **Hold the Line** | 0.5% of our GDP from the treasury | Undoes one of their pushes in our contest | Only when they have pushed. 1 year. |
| **Shore Up** | 0.5% of our GDP from the treasury | Halves this rival's actions against us for 12 months (list `spec_rv_shield`; Safe Harbour 17 months) | Not while already shored up against them. 2-year cooldown per rival. |

- Bear Raid, Lure and Press also push the contest bar (section 1). Every action works against Exchanges we rival and
  Exchanges rivaling us, from either table.

- The last action against each country is logged: what it was, by whom, and its result. The rivalry row shows the
  last action between the two of them.

## 3. AI, both ways

- **Naming (beta.12):** once a year, before the contest, each AI Exchange:
  - keeps its own limits: 1 rival, or 2 from International Standing (`spec_rv_slots`), within one Standing (`REACH`)
  - drops named rivals that are dead, out of reach or without an Exchange
  - early in a round (years 0 to 1), drops a rival it is 0.65 or more behind on the bar (`AI_CUT`), unless kept
  - fills its free slots with Exchanges within reach that it starts no more than 0.3 behind (`AI_REACH`), the best
    first by `spec_rv_ai_pick_v`: its side of the bar plus 0.15 a Standing above it (a bigger prize)
  - Players are valid targets. It also runs on the first monthly pass, so rivals exist before the first contest.

- Once a year, each AI with an Exchange may act against each rival pair: at most one action per rivalry per year.
  - Base chance: 25%. Bold +15%, Cautious -15% (`credit_ai` tempers).
  - Plus 15% a year of the round gone (`AI_URGENCY`), so it acts most in the year before the contest settles.
  - In order: Shore Up against the rival that just hit it; nothing while already past the decisive line by a push
    (keeps its money); Hold the Line when pushed; else push, weighted Lure 3, Press 2, Bear Raid 1, or 3 when its
    score is the higher (a raid fails less then).
  - Not yet: it ignores the size scaling and whether a push would cross a band; calibrate from logs or headless runs.
  - It names no Exchange that `AI_CAP` (3) already rival, and drops one rivalled by more, so minors do not pile on.
- **A player who is targeted gets an event.** It names the action and its effect, with three choices:
  - **Retaliate:** the same action against them, paid as usual, ignoring the cooldown. From beta.12 the tooltip names
    the action and shows its cost and effect.
  - **Shore up against them:** if it is available.
  - **Ignore:** +2 trust for keeping calm.

## 4. UI: the Rivalries section (Finance, World tab)

- Rebuilt after the user's in-game reviews: vanilla tables, icons, terse tooltips; rules once, in the header tooltip.
- **Header** (`default_header_2texts`): Rivalries, with the influence upkeep on the right.
- **Rival Actions on Us** (folding section, "Contests settle in N years" on the right): one 44px row per action
  running on us (Bear Raid by whom, `spec_rv_raider`; Capital Lured by whom, `spec_rv_lurer`), with what it does and
  its months left on a bar; then the last move against us that left nothing running (a Press Campaign, worked or
  exposed, or a failed Bear Raid), from `spec_rv_hit`, `_hit_by`, `_hit_ok`, for the year `spec_rv_hit_recent` lasts;
  else a line saying none is.
- **Exchanges We Rival / Exchanges Rivaling Us**, folding tables with one layout (`section_header_button`,
  `sort_button` heads, 44px rows, vanilla dividers, a hover highlight): Country | Contest | Actions.
  - **Contest:** drawn as the Market Confidence bar (`market_tab.tier_scale`): fill sliding from the centre, green
    toward us and red toward them, vanilla's glow and the changed-value chevrons running toward whoever has pushed
    more; dividers at the five results, decisive ends tinted, vanilla's active-level frame on the current one, its
    name above. Each result's section has its own tooltip: what that result does with this pair's numbers, then
    where it stands (scores, pushes, years left, last result).
  - The bar and pushes are stored on each row's country by `spec_rv_ui` (monthly and on every push), so the screen
    reads three numbers rather than a few hundred scripted-GUI checks a row each frame. In multiplayer, two players
    rivalling the same Exchange share them.
  - **Actions:** Bear Raid, Lure, Press, Hold the Line, Shore Up as vanilla tariff-style buttons; framed while running
    on them (Raid and Lure with a months badge), while shored up against them, or while used and cooling down.
  - A shield after a rival's name: they have shored up against us.
- **Leading Exchanges list:** the rivalry toggle, a vanilla subsidize-style button (silhouette off, lit on, upkeep
  and relations in its tooltip, a lock in the first year), plus a shield when they rival us.
- **Notifications:** one for a won contest and one for a lost one; the event for a raid, lure or smear against us.

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
