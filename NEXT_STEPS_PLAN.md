# Next steps plan (hardened after two adversarial reviews, 2026-11-03)

Reviews: a Claude review of the core loop, then Claude and Codex (read-only) against the draft of this plan.
Generator: `tools/*.py` writes `mod/`. Test build `py -3 tools/generate.py --log`; observer games `tools/observe.py`.

## What the -40 is
`spec_exposure` sums every boom's ending cost as if all ended in the same month, scaled, capped at `CONF_CRASH_MAX`
(40). Every member of a market reads that market's prices and trade (`spec_mv_<g>` via `market ?=`), so all members
share one set of per-good risks; only `spec_crash_scale` (confidence, depth, steadiness, financial risk) differs, and
at the cap that difference vanishes. Hence most countries show the same -40.

Baseline game (`runs/20261103_140407_expo_base`, 1836 to 1881, all countries): chip at the cap 10 to 28% of months,
median 2 to 17, uncapped 90th percentile 42 to 98; realised boom-ending loss in the following 12 months median 0,
90th percentile 7 to 13. The "40 largest" cut in the first report is unreliable (see Step 0).

## Step 0. Instrumentation and analysis fixes (no balance change)
- expo.py: rank by a real GDP figure (the PROBE line's GDP, not the SPEC `gdp=` field, which is the rescue cost);
  keep revolutionary streams (`TAG#2`) out of the cohort; drop months whose 12-month window runs past the end;
  report paired per-month error (shown vs realised), the upper tail and warning hit/miss rates, not only medians.
- Log line additions: the raw weight total, heat added/cooled/burst, endings by severity and count, installment
  losses (once C exists), and exposure read at one consistent point in the month (now `expo` is cached before the
  confidence update and `expo_raw` is recomputed after it, `generate.py:582` / `:642`).
- Record build and tuning identity in each run's meta.

## Step 1. F: same panic length formula for players and AI
Drop the AI ×0.7 (`generate.py:411`), set `PANIC_DAYS` 270 → 189; both rounding stages stay, so AI panics are
unchanged and new player panics get the AI's length (realised length still varies with laws, reforms, rescues).
Panics already running in a save keep their stored months. Panic text reads its months from PANIC_DAYS
(`market_tab.py:983`); rescue cost and cooldown timing for players shift with it.

## Step 2. B: Booms at Risk becomes "largest boom ending: -X, N goods exposed"
Display only; nothing that moves confidence changes meaning without its own decision:
- Chip and tooltip: the largest single boom's scaled ending cost and the count of goods with `spec_sev > 0`; per-good
  list unchanged. The tooltip keeps the all-at-once stress figure as a secondary line, labelled as a worst case.
- `spec_exposure` itself stays for the Panic Risk alert (`journal.py:95`, an explicit all-at-once test) and the press
  story (`stories.py:243`, moves confidence -6/+2), so the display change is not a balance change.
- Restrained goods: shown as restrained, not as "turning".

## Step 3. E (narrow): Loose no longer deepens falling prices
Only Loose's extra ×1.3 is dropped on a negative fast-minus-slow difference; Tight's ×0.5 stays on both sides
(dropping it would double Tight's downside), law/tech/depth unchanged. Update the interest-threshold and unwind
tooltips that recompute the trend (`generate.py:375`, `:1576`); recheck the AI's stance switching, since a stance
change moves hype with no price move.

## Step 4. C: Restrain — DESIGN DECISION NEEDED
`levers.py:1-2,35` make "a restrained boom fades without ending" the intended soft landing; its price is -10%
throughput, -1 Authority and a levy (income). The AI restrains its riskiest boom at confidence 60+ and releases
before full deflation (`levers.py:281`), so any cost here shifts the whole AI calibration. Options:
1. Keep as designed; raise the price instead (Authority, throughput).
2. Partial cost: each restrained month pay a share of the uncapped raw-risk reduction from that month's peak decay
   (snapshot before the peak overwrite, `generate.py:549`), as its own confidence driver, not a crash (no
   notification, glut or company collapse). Encourage's floor must not become the alternative escape.

## Step 5. D: bubble heat cools, one rate
Mutually exclusive grow / cool / burst branches on post-update confidence: grow at heat_from and above (as now), cool
×0.9 a month between BURST_BELOW and heat_from, burst below. No Tight bonus at first. Update the journal's
growth-only heat text (`journal.py:368`). Watch large-economy panics: bursts were tuned in to reach them (tune8).

## Step 6. A: weight normalisation — only if the evidence asks for it
Diagnosis is right (unnormalised, cap applies before financial and reform multipliers, `generate.py:693`), but B may
answer the complaint. If adopted: scale down only, `w = raw × min(1, W_TOTAL / Σraw)`, Σraw cached once per country
right after `spec_mv_total` (`generate.py:691`), zero-guarded; keep lever costs (`levers.py:133`) on the raw weight.
Decide from Step 0's data: losses by market concentration.

## Validation
- Replicated batches, runs as the unit: baseline ×5 (1 done) and each stage ×5 to 1881, plus a combined build ×5
  to 1906. About 55 min per game to 1881.
- Accept against FINDINGS.md benchmarks (panics, months in panic, length with censored panics handled, Mania,
  Mania-to-panic), plus: no new error.log entries; a current-version save loads and new variables are initialised
  before they are read.
- Order: Step 0 → F → B → E → C → D → A, each validated before the next.
