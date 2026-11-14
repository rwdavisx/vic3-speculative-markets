# Speculative Markets 0.9 design

Agreed after four rounds with Codex, 2026-11-08 (round 4 was adversarial). Nothing built yet.
Rule: existing players and saves come first, so the goods engine stays and every current identifier is kept.
0.9 changes no balance. Every item below is display, text or navigation.

## 1. Banking tab (Budget panel)
- Patch vanilla `gui/budget_panel.gui` at generate time, the way `market_panel()` patches the Market panel (generate.py ~1744). A game patch then costs a regenerate, not a re-diff.
- It adds a 4th tab (vanilla has Overview, States, Assets via `InformationPanel.SelectTab`, line 65-129) bound to `GetPlayer`.
- It holds Credit Policy, Leverage + Credit Limit, Bad Debts + Buy Up Bad Loans, Lend to the Banks, journal measures in effect, and new lending vs repayment this month.
- Patch anchors (`third_button_selected` and `scrollarea_content` near line 144 are fragile): each must match exactly once and the 4th tab slot must be free. Otherwise generate.py fails loudly.
- To check in game: whether a custom tab key selects correctly.

## 2. Discovery (Speculation tab)
- It keeps a one-line credit summary, with the visible sentence "Credit Policy and Leverage are now under Budget > Banking" all through 0.9. It is a link if a navigation API allows it.
- Lend to the Banks stays next to the panic bar as a shortcut (same scripted GUI).
- When viewing a foreign market, the summary describes the viewed country. The Banking tab always describes the player.

## 3. Names and history
- All names stay. Tooltips gain one history line after the cost and effects, for example "Inspired by the Bank of England's emergency discounts in 1847, 1857 and 1866".
- Buy Up Bad Loans text: "The Treasury purchases impaired bills and claims from distressed banking houses, taking their losses onto the public account." Then the existing cost, the halving, and once per spell. No promise of repayment or recovery.
- Text separates emergency lending (Lend to the Banks) from buying bad loans.

## 4. Sector chips (display and filter only)
- A row of sector chips sits above the unchanged Investor Interest board, plus "All sectors". Each good has one fixed primary sector, and there is "Other production".
- Clicking a chip filters the board. The board's rows already test filters themselves (interest_board.py `shown_by_filters`), so this adds a sector test next to the category test, in both the fixed-order and the sorted view. Sector and category filters intersect, and an empty result says why.
- Each chip shows:
  - breadth = 100 x trade value of the sector's Eager/Feverish goods / trade value of all the sector's traded goods (reuses `spec_mv_<good>`)
  - the top risk good in the sector
  - active gluts
  - "No activity" when the sector has no traded goods
- Chip figures are always sector-wide and ignore other filters.
- Cache them after the monthly goods update. The sector ID per good is fixed at generate time.

## 5. Crash story
- At each ending, keep the largest realized contributor by `spec_risk_raw_<good>` (pulse-local max, deterministic tie-break). Capture its peak, weight and severity before any reset. Build the story after all endings.
- The text calls it the largest contributor, not the sole cause. Any named house is clearly fictional flavour.
- Correction/Bust/Collapse tooltips explain the ending from the peak, the market weight and the glut length.

## 6. Saves
- Keep all variable, modifier, event and scripted-GUI identifiers. Do not touch `spec_lev_ready`.
- New state is display caches only, built on first update.

## Railways: research spike during 0.9, ships later
- Transportation is `local = yes`, so the market-price engine cannot see it. Railway and port are both `bg_private_infrastructure`, so a group modifier would be too broad.
- Spike: `sg:transportation` from a state, then `state_goods_pricier` (triggers.log: "Output Scopes: value"), read numerically with `add = state_goods_pricier`. Go if it matches the UI in two states, has the right sign above and below base, responds to supply, and is safe with no activity.
- Even on go, it ships only once these are designed:
  - exposure weights
  - crash behaviour
  - the producer effect: a `building_railway`-only modifier on the existing tier schedule, or none
  - lazy initialization of fast/slow/peak, so loading a save cannot trigger a crash
  - a profile of the monthly per-state pass in a developed late game

## Cut
- Sector contagion: vanilla demand (panics halve construction, so steel demand falls) and the mod's credit/panic channels already carry it. Its effect is unproven and adds calibration. If revived, it needs a named driver showing the actual post-cap loss.
- From the first draft: share indexes and sector throughput, the renames, moving Buy Up Bad Loans late, and treasury repayment / moral hazard.

## Tests
- Check that the mechanics are unchanged: same values and same monthly results before and after on a fixed save.
- Checks:
  - chip and category filter intersections, sorted and fixed views
  - foreign-market viewing
  - Banking tab scope and buttons
  - migrated saves
  - simultaneous endings for the crash story
- 2 test games (early and developed economy), checking that the UI and buttons work. No balance pairs are needed, since balance doesn't change.
