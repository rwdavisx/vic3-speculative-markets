"""Summarise a logged run: how confidence moves, how often manias and panics happen, how much credit flows.

Usage: py -3 tools/analyze_cycle.py <file of SPEC lines>
"""
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime

LINE = re.compile(r"tag=(\S+) date=([A-Z][a-z]+ [0-9]+, [0-9]{4}) conf=(\S+) boom=\S+ crash=(\S+)(?: foreign=\S+)? turmoil=\S+ "
                  r"panic=(\d) pool=(\S+)(?: .*stance=(-?\d) .*rescued=(\d))?")

# the log is not in date order and lines can run together when it rotates: parse what is whole,
# key by date to drop repeats, then sort each country's months before counting transitions
by_tag = defaultdict(dict)  # tag -> date -> (date, conf, panic, credit, crash, stance, rescued)
for line in open(sys.argv[1], encoding="utf-8"):
    m = LINE.match(line)
    if not m:
        continue
    tag, date, conf, crash, panic, pool, stance, rescued = m.groups()
    try:
        d = datetime.strptime(date, "%B %d, %Y")
        by_tag[tag][d] = (d, float(conf), int(panic), float(pool), float(crash),
                          None if stance is None else int(stance), int(rescued or 0))
    except ValueError:
        pass
runs = {tag: sorted(v.values()) for tag, v in by_tag.items()}

months = sum(len(v) for v in runs.values())
confs = [r[1] for v in runs.values() for r in v]
panic_starts = sum(1 for v in runs.values() for a, b in zip(v, v[1:]) if b[2] and not a[2])
mania = sum(1 for c in confs if c >= 80)
panic = sum(1 for v in runs.values() for r in v if r[2])
crashes = sum(1 for v in runs.values() for r in v if r[4] < 0)
print(f"{len(runs)} countries, {months} country months")
print(f"confidence: mean {statistics.mean(confs):.1f}, median {statistics.median(confs):.1f}, "
      f"min {min(confs):.1f}, max {max(confs):.1f}")
print(f"months in mania (>=80): {mania / months:.1%}, in panic: {panic / months:.1%}")
print(f"panics started: {panic_starts}, one per {months / 12 / max(panic_starts, 1):.0f} country years")
print(f"months with a crash shock: {crashes / months:.1%}")
print("confidence deciles:", " ".join(f"{d:.0f}" for d in statistics.quantiles(confs, n=10)))
for tag in ("AUS", "GBR", "FRA", "PRU", "RUS", "USA"):
    if tag in runs:
        print(f"{tag}: " + " ".join(f"{r[1]:.0f}{'P' if r[2] else ''}" for r in runs[tag][::3]))

# version 0.3 lines also carry the credit stance and whether the banks were rescued
flat = [r for v in runs.values() for r in v if r[5] is not None]
if flat:
    for name, n in (("tight", -1), ("normal", 0), ("loose", 1)):
        print(f"months {name}: {sum(1 for r in flat if r[5] == n) / len(flat):.1%}")
    # only Central Banking can change the stance: count each country from its first change on
    banked = [r for v in runs.values() for i in [next((i for i, r in enumerate(v) if r[5]), None)] if i is not None for r in v[i:]]
    changes = sum(1 for v in runs.values() for a, b in zip(v, v[1:]) if a[5] is not None and b[5] != a[5])
    if banked:
        print(f"after a country's first change ({len(banked)} months): tight {sum(r[5] == -1 for r in banked) / len(banked):.1%}, "
              f"loose {sum(r[5] == 1 for r in banked) / len(banked):.1%}, changes per country decade {changes / len(banked) * 120:.2f}")
    rescues = sum(1 for v in runs.values() for a, b in zip(v, v[1:]) if b[6] and not a[6])
    print(f"rescues: {rescues}")

# version 0.5 lines add debt, speculation depth, interventions and the Long Depression phase
EXTRA = re.compile(r"tag=(\S+) date=([A-Z][a-z]+ [0-9]+, [0-9]{4}) .*?debt=(\S+) .*?gdp=(\S+) depth=(\S+) steady=(\S+) "
                   r"fd=\S+ levers=(\S+) ld=(\S+)")
extra = defaultdict(dict)
for line in open(sys.argv[1], encoding="utf-8"):
    m = EXTRA.match(line)
    if m:
        try:
            d = datetime.strptime(m.group(2), "%B %d, %Y")
            extra[m.group(1)][d] = tuple(float(x) for x in m.groups()[2:])
        except ValueError:
            pass
rows = [r for v in extra.values() for r in v.values()]
if rows:
    print(f"\n{len(rows)} country months with the 0.5 fields")
    depth = [r[2] for r in rows]
    print(f"depth: mean {statistics.mean(depth):.2f}, deciles", " ".join(f"{x:.2f}" for x in statistics.quantiles(depth, n=10)))
    steady = [r[3] for r in rows]
    print(f"steady: mean {statistics.mean(steady):.2f}, min {min(steady):.2f}, max {max(steady):.2f}")
    print(f"months with an intervention: {sum(1 for r in rows if r[4] > 0) / len(rows):.1%}, "
          f"mean active when any: {statistics.mean([r[4] for r in rows if r[4] > 0] or [0]):.1f}")
    debt_share = [r[0] / r[1] for r in rows if r[1] > 0]  # gdp= logs the rescue cost, 2% of GDP
    print(f"debt over 2% of GDP: mean {statistics.mean(debt_share):.2f}, max {max(debt_share):.2f}")
    for p, name in ((1, "Crash"), (2, "Depression"), (3, "Recovery")):
        print(f"Long Depression {name}: {sum(1 for r in rows if r[5] == p) / len(rows):.1%} of country months")
    ld_dates = sorted({d for v in extra.values() for d, r in v.items() if r[5] > 0})
    print(f"Long Depression months: {ld_dates[0]:%b %Y} to {ld_dates[-1]:%b %Y}" if ld_dates else "no Long Depression")
    ld_tags = {t for t, v in extra.items() if any(r[5] > 0 for r in v.values())}
    print(f"countries in a Long Depression: {len(ld_tags)} of {len(extra)}")

# version 0.6 lines add the Market Mood
mood = [float(x) for x in re.findall(r" mood=(-?[0-9.]+)", open(sys.argv[1], encoding="utf-8").read())]
if mood:
    print(f"market mood: deciles", " ".join(f"{x:.1f}" for x in statistics.quantiles(mood, n=10)))
