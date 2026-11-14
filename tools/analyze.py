"""Compare building growth before and after the boost switches on.

Reads the SPEC lines the mod writes to debug.log (one per game month) and prints, per building,
levels added per year in the control phase and in the boost phase, and the ratio between them.
Usage: py -3 tools/analyze.py <file with SPEC lines> [boost_month] [lag_months]
"""
import re
import sys

rows = {}
for line in open(sys.argv[1], encoding="utf-8"):
    kv = dict(re.findall(r"(\w+)=(-?[\d.]+)", line))
    if "m" in kv and "wood_slow" in kv:  # skip lines caught half written
        rows[int(float(kv["m"]))] = {k: float(v) for k, v in kv.items()}

boost = int(sys.argv[2]) if len(sys.argv) > 2 else 24
lag = int(sys.argv[3]) if len(sys.argv) > 3 else 6  # private construction takes months to finish
first, last = min(rows), max(rows)
start_b = boost + lag
buildings = [k for k in rows[first] if k not in ("m", "boost") and not k.startswith("wood_")]


def per_year(k, a, b):
    return (rows[b][k] - rows[a][k]) * 12 / (b - a)


print(f"control m{first}-m{boost}, boost m{start_b}-m{last}")
print(f"{'building':26}{'ctrl/yr':>9}{'boost/yr':>10}{'ratio':>8}")
for k in buildings:
    c, b = per_year(k, first, boost), per_year(k, start_b, last)
    ratio = f"{b / c:.1f}x" if c > 0 else "n/a"
    print(f"{k:26}{c:9.1f}{b:10.1f}{ratio:>8}")
for k in ("wood_pricier", "wood_fast", "wood_slow"):
    print(k, " ".join(f"{rows[m][k]:.2f}" for m in range(first, last + 1, 6)))
