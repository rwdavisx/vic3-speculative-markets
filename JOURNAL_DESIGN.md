# Financial Markets journal entry: redesign (draft for approval, 2026-11-01)

## Why it needs one

Today the entry is a permanent copy of the Speculation tab: a confidence bar, credit buttons, the most and least
favored goods. It has no stages, no goal, no choices the tab lacks, and nothing new to say most months.

Vanilla does keep long running entries (`je_autocracy`, `je_canada_gbr`), but its best ones give a story, a risk to
manage and choices with a price. The models used below:

| vanilla entry | file | pattern taken |
|---|---|---|
| Gründerzeit | `05_grunderzeit.txt` | status by tier (Booming to Crashed), a commitment choice that scales boom and crash, outcome previews |
| Uneasy Raj | `04_sepoy_mutiny.txt`, its bars | a bar whose tooltip lists every monthly factor, event results as lasting lines |
| Indian Famines | `04_indian_famines.txt` | paid relief buttons: a 12 month expense modifier scaled to GDP, 365 day cooldown, `selected` |
| Grand Collapse | `05_the_grand_collapse.txt` | stance buttons with a tradeoff, readable cooldowns |
| Meiji Restoration, Sick Man | `00_meiji_restoration.txt`, `00_sick_man.txt` | a hub with milestones (`current_value`, `goal_add_value`) |

## The design: a market cycle you live through, and the institutions you build from it

The entry stays permanent for players, like `je_autocracy`. It gains three things the tab does not have.

### 1. Stages that tell the story

`status_desc` and the description change with the market's state, in the Gründerzeit way:

| stage | when | what the text says |
|---|---|---|
| Steady | 40 to 60, no panic | what is booming, what to watch |
| Buoyant | 60 to 80 | credit is flowing; the bubble is building |
| Mania | 80 or more | investors have lost their heads; the higher it climbs, the harder the fall |
| Panic | in a panic | months left, credit called in, what support costs |
| Aftermath | 12 months after a panic | the inquiry: what the country learns from it |
| Long Depression | in the world depression | its phase and the country's own recovery |

The most and least favored goods move to the Steady and Buoyant text only.

### 2. Two bars

- **Market Confidence** (kept, double sided gold). Its tooltip lists this month's factors the Uneasy Raj way
  (booming goods, collapsed booms, mood, growth, turmoil, debt, credit, drift), read from the drivers the monthly
  update already stores (`spec_c_*`).
- **Speculative Excess** (new, `default_bad`, 0 to 120). The bubble's heat (`spec_heat`): each month at 74 or more
  adds to it, and when confidence falls below 60 it bursts for 0.2 x heat, at most 40. The player cannot see this
  number today. With it, the entry shows how hard the next fall will be, and Restrain, Tight credit and the mania
  event's warning gain a visible target. During a panic it shows the months left.

### 3. Choices with a price, by stage

Costs follow vanilla: a timed expense modifier scaled to GDP (`money_amount_multiplier_*`), approval, legitimacy,
authority. Cooldowns use `cooldown` and a readable variable; an active choice is `selected`.

| decision | stage | effect | price | history |
|---|---|---|---|---|
| Convert the National Debt | Buoyant or Mania, with debt | loan interest -10% for 5 years, ending early once debt falls below 20% of the credit limit | confidence -5, Aristocrats -2 approval; once per 10 years | Goschen 1888, France 1852 |
| Support the Banks | Panic, Banking | as now | as now | Bank of England 1866 |
| Suspend the Bank Act | Panic, after the Note Issue reform chose the Currency School | panic ends in 3 months, no treasury cost | legitimacy -10; Speculative Excess builds 25% faster for 10 years | Treasury letters 1847, 1857, 1866 |
| Relief Works | Panic or Depression | radicals from the panic halved, Trade Unions +2 | expense modifier for 12 months (medium); cooldown 365 days | Ateliers nationaux 1848 |
| Commission of Inquiry | Aftermath | opens the reform event below | authority for 6 months | Select Committees after 1847, 1857 |

The tab keeps credit policy and the per good interventions; the entry keeps the credit buttons too, as now.

### The goal: Sound Finance

A hub in the Meiji way: three institutions, each unlocked by a technology and enacted through the Commission of
Inquiry after a panic (or, without a panic, after 10 years with the tech, so a lucky country is not locked out).

| institution | tech | choice | effect |
|---|---|---|---|
| Note Issue | Banking | Currency School (Bank Charter Act 1844) | credit -25%, Speculative Excess builds 25% slower; panics last 25% longer unless the Act is suspended |
| | | Free Banking | credit +25%, booms 10% bigger, boom ending losses 10% bigger |
| Lender of Last Resort | Central Banking | Bagehot's rule | Support the Banks costs 30% less and ends the panic a month sooner |
| Company Law | Joint-Stock Companies | Disclosure and audit | boom ending losses -15% |

The progress bar of the goal is the count of institutions (0 to 3). With all three: an event, prestige and loan
interest -10% for good. The entry stays after that; only the goal is met.

## AI parity

AI countries never use journal entries. Each new lever gets a rule in the AI block, weighted by the credit
temperament already rolled: Bold leans Free Banking, Cautious the Currency School; the AI converts debt in Buoyant
markets with debt over 20% of its credit limit; Relief Works under 25% radicals growth and a surplus. Without these,
players alone get the rewards.

## Balance

Note Issue and Lender of Last Resort change panic frequency and length, which the full game runs are calibrated on.
After building: three 1836 to 1906 observer runs on the Historical rule, and the Stats tab's benchmarks (panics per
century, months in panic, Mania to panic share) must stay inside the historical ranges in FINDINGS.

## Also found

Vanilla's Gründerzeit (German states, Mutual Funds and railways) runs its own boom and its Gründerkrach crash:
investment -20% for 5 years. The mod does not know about it, so a German state can take both that crash and a
Financial Panic. Separate fix: skip the mod's panic investment loss while `modifier_grunderkrach` is active, or
count the Gründerkrach as the panic.

## Build order

1. Stages, the two bars, the panic and debt decisions. The entry earns its place here.
2. The Sound Finance goal and its reforms, then AI rules, then the calibration runs.
