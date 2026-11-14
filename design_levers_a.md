# Exchange levers, design A

Standing comes from trust and volume; you cannot push both at once.

## A. Levers

**1. Exchange Rules: Open / Ordinary / Strict.** A Budget > Banking policy built like Credit Policy. Needs Banking. A change takes effect after 12 months, then is locked for 3 years.
- **Open** (Laissez-faire only): score x1.25, interest and credit x1.1, Lending Standards slide toward Reckless twice as fast, Industrialists +1.
- **Strict:** interest x0.9, credit x0.85, trust +1 a month, Lending Standards drift toward Strict, Industrialists -1.
- **Payoff:** 5 to 8 years.
- *"Credit Policy sets this year's lending. Exchange Rules set how banks behave for a decade. Open builds volume; Strict builds trust."*

**2. Stand Behind the Exchange.** A pledge. Needs National Standing and scaled debt of 0.5 or less.
- A panic takes a quarter of trust, not half. Capital flight you receive is x1.5.
- Rescue costs x0.75 but fires automatically. Each rescue loosens Lending Standards, which pulls you toward Strict.
- Leaving takes 24 months' notice.
- Breaking the pledge (default, or you can't pay): trust 0, confidence -15, legitimacy -10.
- *"Promise always to rescue the city's banks. Panics cost less trust and capital runs to you. Break it and the Exchange is ruined."*

**3. Float a Great Issue.** A button on the row of any good at Eager or hotter. Needs National Standing. One issue at a time.
- For 24 months: score x1.25, Industrialists +2, and exposure to that good x1.5.
- When that boom ends, its trust result counts double: Correction +4, Bust -12, Collapse -36.
- It rewards landing the boom (say, Restraining at Feverish); it cannot start or protect one.
- **Payoff:** 2 to 4 years.
- *"Stake the Exchange's name on this boom. A gentle ending raises it fast; a bust is remembered twice."*

**4. Specialise.** The "known for" event becomes a journal button. Choosing again halves trust, then a 5-year cooldown.
- **Commodity:** interest x1.1, score +2% per Trade Centre level.
- **Deposit Banks:** trust losses halved, score +1% per Manor House level.
- **Share Market:** credit x1.1, score +3% per company.
- *"Choose what your Exchange is known for: which booms you ride best, and what to build to grow it."*

**AI** (`ai_chance` on existing reads):
- **Rules:** Bold picks Open; Cautious or Lax-lending AIs pick Strict.
- **Pledge:** if gold covers a rescue and scaled debt is below 0.3.
- **Issue:** 30% a year on a heavily traded good at Eager, while confidence is Steady or better.
- **Specialise:** the type it has most of.

## B. Cross-links

1. **Financial Centres rank feeds the credit limit:** +1 to +5 months, by place. Being a centre lets you borrow more and fall harder.
2. **Trust feeds Confidence:** post-panic recovery runs x0.75 (trust 0) to x1.5 (trust 120).
3. **Trust feeds Market Mood:** mood swings run x1.5 to x0.5, so they become a risk you can shrink.
4. **The World Centre feeds Mood:** the leader's confidence band nudges the mood of International exchanges and tied markets by ±0.3. Toppling the leader matters.
5. **Bad Debts feed the Exchange:** while they last, Standing cannot rise and trust falls 1 a month. Buying up bad loans now protects Standing too.

## C. Vanilla links

1. **In:** Financial District levels in the capital (`b:X.level`, verified) give score +2% per level, capped at +40%.
2. **In:** Trade Centre and Manor House levels and company count (`num_companies`, not yet used by the mod) feed Specialise.
3. **In:** `scaled_debt` and `in_default` (verified) gate the pledge and break it.
4. **In:** the economic system law (verified) gates Open. Under Interventionism, switching to Strict takes half the time.
5. **Out:** each Standing step gives Industrialists +5% political strength (`..._pol_str_mult`, **unverified**). The stronger lobby pushes Laissez-faire, and booms run hotter.
6. **Out:** International or higher raises capitalists' pool contribution in the capital (a modifier family the mod uses).

## D. 20 years

- **1855.** Berlin is National, 8th. Trust is 40 and Lending Standards are Lax. The player sets Strict Rules, chooses Share Market and queues Financial Districts.
- **1860.** Lending Standards are Sound. The player floats an issue on iron, then Restrains it at Feverish. It ends as a Correction: Berlin is 6th.
- **1862.** Central Banking. The player pledges and moves to Ordinary to fund companies.
- **Setback, 1866.** A war, then an unrestrained rail Bust, start a panic.
  - The pledge keeps three-quarters of trust, but its automatic rescue makes lending Lax (trust stops growing) and Bad Debts freeze Standing.
- **1868.** The player buys up the bad loans, goes back to Strict, and builds Financial Districts to 15 levels.
- **Payoff, 1873.** Vienna panics. Pledged, trusted Berlin takes the flight and reaches 4th: International.
  - Flight x2, credit limit +2 months; stronger Industrialists pass Laissez-faire, so booms run hotter and holding the place takes discipline.

## E. Cuts

Free Banking and Currency School reforms (Rules replace them); the separate place modifier (merged into Standing); "Years of Calm" in tooltips; the one-off "known for" event; "Mood halved without Financial Districts" (B3).

## F. Risks

- **Balance:** a runaway loop (rank, then credit, then bigger booms, then score) could lock a Great Power at 1st. Test that a crash at 1st still costs the place within 20 years.
- **AI:** over-pledging bankrupts minors; count broken pledges in headless runs.
- **Technical:** the political-strength modifier is unverified. Test in game:
  - the automatic rescue on the tick a panic starts;
  - the doubled trust from an issue being applied when its boom ends;
  - the Rules timer surviving save and load.
