"""Does building follow hype? Compare a loop run with a control run.

For every country and building, pairs the average hype of the good the building sells with the levels the
country added over the run, and compares how strongly the two go together in each run.
Usage: py -3 tools/analyze_loop.py <loop run file> <control run file>
"""
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate import SELLS  # noqa: E402

SELLS_FLAT = {b: g for m in SELLS.values() for b, g in m.items()}
LAST_KEY = f"l_{list(SELLS_FLAT)[-1]}"


def load(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        tag = re.match(r"tag=(.*?) m=", line)
        kv = dict(re.findall(r" (\w+)=(-?[\d.]+)", line))
        # skip lines caught half written, or whose tag failed to print
        if tag and "ERROR" not in tag.group(1) and LAST_KEY in kv:
            rows[(tag.group(1), int(float(kv["m"])))] = {k: float(v) for k, v in kv.items() if k != "m"}
    return rows


def pairs(rows):
    """(mean hype, levels added) per country and building, over each country's logged months."""
    months = {}
    for tag, m in rows:
        months.setdefault(tag, []).append(m)
    out = []
    for tag, ms in months.items():
        ms.sort()
        if len(ms) < 24:
            continue
        first, last = rows[(tag, ms[0])], rows[(tag, ms[-1])]
        for b, g in SELLS_FLAT.items():
            hype = statistics.mean(rows[(tag, m)][f"h_{g}"] for m in ms)
            out.append((hype, last[f"l_{b}"] - first[f"l_{b}"], first[f"l_{b}"]))
    return out, len(months)


def report(name, rows):
    p, countries = pairs(rows)
    active = [x for x in p if x[2] > 0 or x[1] != 0]  # buildings the country has or built
    hype = [x[0] for x in active]
    added = [x[1] for x in active]
    hot = [a for h, a in zip(hype, added) if h > 1.1]
    cold = [a for h, a in zip(hype, added) if h < 0.9]
    print(f"{name}: {countries} countries, {len(active)} country-building pairs, "
          f"{sum(added):.0f} levels added")
    print(f"  corr(mean hype, levels added) = {statistics.correlation(hype, added):.3f}")
    print(f"  levels added per pair: hype > 1.1 {statistics.mean(hot):.2f} ({len(hot)}), "
          f"hype < 0.9 {statistics.mean(cold):.2f} ({len(cold)})")


if __name__ == "__main__":
    report("loop", load(sys.argv[1]))
    report("control", load(sys.argv[2]))
