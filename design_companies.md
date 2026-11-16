# Home of Great Companies: deeper design (proposal)

Status: proposal only. Balance is frozen while `MECHANICS_AUDIT.md` has open checks; nothing here is built.
Source: a Steam suggestion that the honour ties too often because it only counts companies at 50+ prosperity.

## Problem

Today the score is `spec_log_kco`: the number of our companies with prosperity >= 50, times pursuit bonuses
(`tools/centres.py:422`). Company slots are capped by technology, so countries at the same tech with healthy
companies tie, and `order_by` breaks the tie, not the player. A company at 51 counts the same as one at 95,
and there is nothing to do with the honour except wait.

## Engine limits that shape the design

- Script cannot set a company's prosperity, and companies take no modifiers (`tools/companies.py`).
- Our levers are building throughput (per good and per building) and `country_company_throughput_bonus_add`.
  Prosperity's target follows productivity, so throughput moves it slowly.
- **Probe result (Nov 15, beta 1.0.6-beta.1, live 1836 game):** prosperity *is* readable as a number in company
  scope (`change_global_variable = { ... add = { value = prosperity } }` summed 87.35 over 12 companies, no errors).
  The same read inside an inline value evaluated from country scope produced a number but logged
  "Invalid scope types for event target link", so production must read it from company scope.
  Evidence: `runs/sweep_prosperity_probe_r1/probe_01`.
- The probe also shows why the current honour ties: three months in, **no company in the world was at 50+**,
  so every country scored 0.

## 1. A score that measures quality (fixes the ties)

**Company Strength** replaces the count: the sum of our companies' prosperity, divided by 20
(so one company at 100 is worth 5). Every point of prosperity counts, from the first month.

Fallback, only if reading prosperity proves unreliable later, is scoring by band:

| Prosperity | Points |
| --- | --- |
| 50-59 | 1 |
| 60-69 | 2 |
| 70-79 | 3 |
| 80-89 | 4 |
| 90+ | 5 |

Blue chips (section 3) add +2 either way.

**Tie-break:** the country whose Strength rose most since last year ranks first, then the higher total
prosperity band count. Overtaking becomes possible by running companies better, not only by having more of them.

## 2. Listings: a choice per company

From the Companies section, the player can **list** a company on their Exchange (limit: 1 per Exchange standing level).

- A listed company's goods draw more Investor Interest: its buildings get the boom throughput earlier, so prosperity
  climbs faster while the good is in favour.
- The cost is exposure: when that good's boom ends, a listed company's glut is half as large again, and
  confidence takes a small hit if a listed company falls below 30 prosperity.
- Listed companies count 1.5x toward Company Strength.
- Delisting is free but locked for 2 years after listing, so the choice matters.

This turns the honour from a passive count into portfolio management: list steady companies for safe points, or
list the ones in a hot good for fast gains and crash risk.

## 3. Blue chips: reward for holding steady

A company that stays at 70+ prosperity for 24 consecutive months becomes a **blue chip** (shown with a badge on its row).

- +2 Company Strength.
- ~~Its buildings ignore half of the panic cut to company throughput.~~ Not buildable: the panic cut is the
  country-wide `country_company_throughput_bonus_add`, and companies take no modifiers of their own.
  Replacement: while a panic runs, each blue chip softens the country's confidence loss slightly (country-level, so it works).

Probe (Nov 15, beta.3, `runs/sweep_company_vars_probe_r1`): companies keep plain and timed variables
(13 of 13 companies, 30 days later, no errors), so the 24-month counter lives on the company itself.
- Losing 70+ for 3 consecutive months removes the status; regaining it takes another 24 months.

This rewards the long game and gives a reason to protect specific companies during a panic.

## 4. Company stories: moments to react to

Built on the existing story system, at most one per country per year.

- **Scandal:** a listed company falls from 60+ to below 40 within a year. Choices:
  bail it out (treasury cost; confidence held), let it fail (delisted, trust -6), or open an inquiry
  (delisted, lending standards tighten, no trust loss).
- **Market darling:** a listed company reaches 90+. Choices: issue new shares (credit pool up, more glut exposure on
  its goods) or hold (Company Strength +1 for a year).

## 5. Company of the Year: something to compete for

Each year the world's single highest-scoring company (by band, listed first, then blue chip) is announced.
Its home Exchange gains +3 trust and a notification goes to every player. This is a visible, contested prize
even for countries that are not leading the honour.

## Build order and tests

Each step ships to beta alone, with its own suite and the full release gate.

1. **Probe: done.** Prosperity is readable in company scope (see above).
2. **Company Strength: built as 1.0.6-beta.3** (`beta/company_strength/`, not published). Tie-break by yearly
   gain skipped: ties fell from 110 country pairs to 0-2 in live tests; add it if real games still tie.
   Original plan: This is the Steam fix; it changes the honour's scale, so the top marks and the 1.5 cap on
   the companies tally move with it. Tests: band edges at 49/50/59/60/89/90, ties broken by yearly gain, rank order.
3. **Blue chips.** Tests: 24-month gain, 3-month loss, panic exemption, save/reload of the counters.
4. **Listings.** Tests: slot limit by standing, 2-year lock, glut multiplier, 1.5x scoring, delisting.
   Also GUI: buttons on the Companies rows; live check of the panel per `AGENTS.md`.
5. **Stories and Company of the Year.** Tests: once per year, each option's effect, live event buttons.

Every new string is needed in all 11 languages.

## Open questions

- Should Company Strength fold in company count at all, or only quality? (Proposal: quality only; count is already in the bands' sum.)
- Should listing be AI-usable from the start? (Proposal: yes, with a simple rule: list the highest-prosperity unlisted company.)
- Lift the balance freeze for step 2 only, or wait for the audit to close?
