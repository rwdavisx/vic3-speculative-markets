"""Fast what-if outside the game: replays logged months through the lending, leverage and panic rules with other values.

py -3 tools/replay.py <telemetry.log> ...        checks it against the log, then tries other values

Takes each country's logged confidence, pool income, stance and lending rate as given, and recomputes its debt, leverage,
panics and Bad Debts. A country's lending rate (law x techs x stance x reforms) isn't logged, so it is read back from the
months banks lent under the cap. Central Banking isn't logged either: a country has it from its first month lending past
3 months of income.
ponytail: no feedback. Confidence and income stay as logged, so it answers "how far would debt run", never "what would
this do to GDP". Trust it only after check() agrees with the log, and test whatever it picks in real games."""
import re
import statistics
import sys
from collections import defaultdict

ROW = re.compile(r"SPEC tag=(\S+) date=(\S+ \d+, \d{4}) conf=([0-9.-]+) .*? panic=(\S+) pool=([0-9.-]+) je=\S+ stance=(\S+) debt=([0-9.-]+) .*?"
                 r" ipi=([0-9.-]+) ip=([0-9.-]+) .*? lev=([0-9.]+) crunch=([0-9.]+)")
MONTHS = "January February March April May June July August September October November December".split()
BASE = dict(share=1.5, flow=0.3, runoff=0.03, safe=3, ruin=10, span=30, crunch=25, fade=0.2, cap=12, smooth=0.154, panic_at=20, panic_len=7, cooldown=12)


def load(path):
    """{tag: [month row]}, one row a month: of two rows under one tag (a civil war), the one with more income."""
    months = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = ROW.search(line)
            if not m:
                continue
            tag, date, conf, panic, given, stance, debt, ipi, ip, lev, crunch = m.groups()
            mon, _, year = date.split()
            key = (tag, int(year) * 12 + MONTHS.index(mon))
            row = dict(conf=float(conf), panic=float(panic) > 0, given=float(given), stance=float(stance), debt=float(debt),
                       pool=float(ipi) * 4.3, ip=float(ip), lev=float(lev), crunch=float(crunch), month=key[1])
            if key not in months or row["pool"] > months[key]["pool"]:
                months[key] = row
    out = defaultdict(list)
    for (tag, _), row in sorted(months.items(), key=lambda x: x[0][1]):
        out[tag].append(row)
    return out


def rate_of(row, p):
    """The lending rate behind a logged month, or None when the cap hid it."""
    base = (row["conf"] - 60) / 40 * row["pool"] * BASE["share"]
    if row["given"] <= 0 or base <= 0 or row["given"] >= row["pool"] * BASE["flow"] * 0.99:
        return None
    return row["given"] / base


def replay(rows, p):
    """Returns (leverage by month, starts of panics as (month, leverage, Bad Debts))."""
    # the first logged month is the start: its debt already has that month's lending and repayment in it
    debt, avg, crunch, left, cool, rate, banking = rows[0]["debt"], rows[0]["pool"], rows[0]["crunch"], 0, 0, 1.0, False
    lev_out, panics = [rows[0]["lev"]], []
    for r in rows[1:]:
        rate = rate_of(r, p) or rate
        banking = banking or (r["given"] > 0 and r["debt"] > 3.05 * r["pool"] > 0)
        income = max(r["pool"], avg)
        debt -= min(debt * p["runoff"], max(r["ip"], 0))
        lending = r["conf"] > 60 and not left and crunch <= 0 and r["stance"] >= 0
        if lending:
            room = max(r["pool"] * (p["cap"] if banking else p["safe"]) - debt, 0)
            debt += max(min((r["conf"] - 60) / 40 * r["pool"] * p["share"] * rate, r["pool"] * p["flow"], room), 0)
        avg += (r["pool"] - avg) * p["smooth"]
        crunch = max(crunch - p["fade"], 0)
        lev = debt / income if income > 1 else lev_out[-1]
        stress = min(max((lev - p["safe"]) / (p["ruin"] - p["safe"]), 0), 1)
        if left:
            left -= 1
            cool = p["cooldown"] if not left else 0
        elif cool:
            cool -= 1
        elif r["conf"] < p["panic_at"] + stress * p["span"]:
            crunch = max(crunch, stress ** 2 * p["crunch"])
            panics.append((r["month"], lev, stress ** 2 * p["crunch"]))
            debt *= 0.5
            left = p["panic_len"]
            lev = debt / income if income > 1 else lev
        lev_out.append(lev)
    return lev_out, panics


def study(data, p):
    lev, panics, rows = [], [], 0
    for runs in data:
        for tag, r in runs.items():
            if len(r) < 24:
                continue
            a, b = replay(r, p)
            lev += a
            panics += b
            rows += len(r)
    cy = rows / 12
    return {"over3": 100 * sum(x > 3 for x in lev) / len(lev), "over5": 100 * sum(x > 5 for x in lev) / len(lev),
            "panics": 100 * len(panics) / cy, "any": 100 * sum(c > 0 for _, _, c in panics) / cy,
            "medium": 100 * sum(c >= 5 for _, _, c in panics) / cy, "severe": 100 * sum(c >= 15 for _, _, c in panics) / cy}


def check(data):
    """Replay with the game's own values against the log: every number here should sit close to its logged twin."""
    logged, mine, started, seen, dated = [], [], 0, 0, 0
    for runs in data:
        for tag, r in runs.items():
            if len(r) < 24:
                continue
            lev, panics = replay(r, BASE)
            logged += [row["lev"] for row in r]
            mine += lev
            real = [b["month"] for a, b in zip(r, r[1:]) if b["panic"] and not a["panic"]]
            started += len(real)
            seen += len(panics)
            dated += sum(any(abs(m - x) <= 1 for x in real) for m, _, _ in panics)
    n = len(logged)
    off = sorted(abs(a - b) for a, b in zip(logged, mine))
    print(f"months {n}  leverage correlation {statistics.correlation(logged, mine):.3f}  mean logged {statistics.mean(logged):.2f} replay {statistics.mean(mine):.2f}"
          f"  off by: median {off[n // 2]:.3f}, 1 in 10 over {off[n * 9 // 10]:.2f}")
    print(f"over 3: logged {100 * sum(x > 3 for x in logged) / n:.1f}% replay {100 * sum(x > 3 for x in mine) / n:.1f}%   "
          f"over 5: logged {100 * sum(x > 5 for x in logged) / n:.1f}% replay {100 * sum(x > 5 for x in mine) / n:.1f}%")
    print(f"panics: logged {started} replay {seen}, of which within a month of a real one {dated}")


def selftest():
    rows = [dict(conf=70, panic=False, given=0, stance=0, debt=0, pool=100, ip=1000, lev=0, crunch=0, month=i) for i in range(60)]
    lev, panics = replay(rows, dict(BASE, share=1.5))
    assert abs(lev[1] - 0.3) < 1e-9 and max(lev) <= 3.0001 and not panics, (lev[:3], max(lev))
    rows[50]["conf"] = 30   # held at the safe line, 30 is no panic; with Central Banking debt runs on and it is
    assert not replay(rows, BASE)[1]
    rows[1].update(given=30, debt=400)
    assert replay(rows, BASE)[1]
    print("replay ok")


if __name__ == "__main__":
    if sys.argv[1:]:
        data = [load(p) for p in sys.argv[1:]]
        check(data)
        for label, change in [("as built", {}), ("flow 0.2", {"flow": .2}), ("flow 0.4", {"flow": .4}), ("share 0.75", {"share": .75}), ("share 3", {"share": 3}),
                              ("runoff 2%", {"runoff": .02}), ("runoff 4%", {"runoff": .04}), ("safe 2", {"safe": 2}), ("ruin 6", {"ruin": 6}), ("ruin 8", {"ruin": 8}),
                              ("span 20", {"span": 20}), ("span 40", {"span": 40}), ("max 15", {"crunch": 15})]:
            r = study(data, dict(BASE, **change))
            print(f"{label:12} past 3 {r['over3']:5.1f}%  past 5 {r['over5']:5.1f}%  per 100 years: panics {r['panics']:.2f} with Bad Debts {r['any']:.2f} medium {r['medium']:.2f} severe {r['severe']:.2f}")
    else:
        selftest()
