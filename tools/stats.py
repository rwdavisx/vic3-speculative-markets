"""Batch statistics for the tuner's Stats tab: our mod's runs set against a vanilla baseline, year by year.

Each reading (observe.py's by_year, from the PROBE line both builds log) is compared at every year: the baseline's
median and range, the mod's median, the change, a permutation test on the medians (exact for small batches), a
bootstrap 90% interval for the change, and the smallest change the batch sizes can tell from noise. Confidence
(spec_by_year, our mod only) is held against the calibration targets in generate.py's notes.

Usage: py -3 tools/stats.py <baseline session[+session]> <mod session[+session]> prints the verdict table."""
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"

# key, name, unit; the unit scales the numbers the page shows
VANILLA = [("gdp_world", "World GDP", "M"), ("gdp_median", "Typical country's GDP", "M"),
           ("growth_10y_median", "Typical 10-year GDP growth", "%"), ("growth_10y_small", "10-year growth, small economies", "%"),
           ("growth_10y_medium", "10-year growth, medium economies", "%"), ("growth_10y_large", "10-year growth, large economies", "%"),
           ("sol_median", "Typical living standards", ""),
           ("debt_world", "World debt", "M"), ("in_debt", "Countries in debt", ""),
           ("at_war", "Countries at war", ""), ("in_default", "Countries in default", "")]
# targets from generate.py's calibration notes (replaying the 40-year run): confidence deciles about 36 to 76, Mania
# 6 to 7% of country months, panic 1.5%; CONF_START 55 is where confidence drifts back to
SPEC = [("conf_median", "Typical confidence", "", (50, 60)), ("conf_p10", "Low confidence (10th percentile)", "", (31, 41)),
        ("conf_p90", "High confidence (90th percentile)", "", (71, 81)), ("mania_share", "Country months in Mania", "%", (0.05, 0.08)),
        ("panic_share", "Country months in panic", "%", (0.01, 0.02)), ("crash_months", "Months a collapse cost confidence", "", None)]
# our mod's own readings (observe.mod_readings): key, name, unit, the range wanted, where that range comes from. A
# design range is what the mod is built to do; a reference is what the calibrated 20-year runs of 1836 did
# (FINDINGS.md, Calibration), so a reading outside it has moved since, not necessarily gone wrong
CALIB = "the calibrated 20-year runs (FINDINGS.md)"
# history, for the 40 largest economies (observe.TOP), the closest match to the samples the figures come from:
# (low, high, centre). A tuned mod's runs should spread around the centre, so the table shows where it falls in them
HISTORY_PANICS = ("Bordo and Eichengreen 1999: 22 crises in 510 country years, 4.3 per 100, in 15 emerging markets "
                  "1880 to 1913, 17 of them banking or twin crises (3.3 per 100); Schularick and Taylor 2012: about "
                  "4 per 100 in 14 advanced economies 1870 to 2008")
HISTORY_ACUTE = ("acute phases of the panics of 1857 (August to December), 1866 (May to August), 1873 (September to "
                 "early 1874), 1893 (May to August) and 1907 (October to January): 3 to 6 months")
HISTORY_BOOMS = ("Goetzmann 2015 (NBER w21693), world stock markets in the 20th century: a market doubled within a "
                 "year in 2.1% of market years, within three years in 14%; a Mania here is the euphoric peak, so "
                 "between the two, nearer the first")
HISTORY_BUSTS = ("Goetzmann 2015: 15% of one-year doublings were followed by a halving within 5 years, 26% of booms "
                 "doubled again; most 19th century banking panics followed a boom (Kindleberger), but most booms "
                 "did not end in one")
MOD = [("top.panic_starts_per100", "40 largest: panics started per 100 country years", "", (2.5, 5.5, 4), HISTORY_PANICS),
       ("top.panic_share", "40 largest: country months in panic", "%", (0.008, 0.025, 0.015),
        "the panics above times an acute phase of 3 to 6 months: " + HISTORY_ACUTE),
       ("top.panic_length", "40 largest: typical panic length, months", "", (3, 6, 4.5), HISTORY_ACUTE),
       ("top.mania_share", "40 largest: country months in Mania", "%", (0.02, 0.08, 0.04), HISTORY_BOOMS),
       ("top.mania_to_panic", "40 largest: Manias followed by a panic within 3 years", "%", (0.1, 0.35, 0.2), HISTORY_BUSTS),
       ("conf_median", "Typical confidence", "", (50, 60), "design: drifts back to 55"),
       ("pinned_share", "Countries stuck within 10 points for a decade", "%", (0, 0.1), "design: confidence should move"),
       ("panic_starts_per100", "Panics started per 100 country years", "", None, ""),
       ("panic_share", "Country months in panic", "%", None, ""),
       ("panic_length", "Typical panic length, months", "", None, ""),
       ("world_panic_peak", "Worst month: share of countries in panic", "%", None, ""),
       ("mania_starts_per100", "Manias started per 100 country years", "", None, ""),
       ("mania_share", "Country months in Mania", "%", None, ""),
       ("mania_to_panic", "Manias followed by a panic within 3 years", "%", None, ""),
       ("crash_share", "Country months with a boom-ending loss", "%", None, ""),
       ("worst_month", "Worst month's loss (1 country month in 1000)", "", None, ""),
       ("rescues_per100", "Bank rescues per 100 country years", "", None, ""),
       ("tight_share", "Months under Tight credit", "%", (0.004, 0.009), "reference: " + CALIB),
       ("loose_share", "Months under Loose credit", "%", (0.016, 0.03), "reference: " + CALIB),
       ("levers_share", "Months with an intervention", "%", (0.17, 0.22), "reference: " + CALIB),
       ("credit_pct_gdp", "Credit given a month, share of GDP", "%", None, ""),
       ("debt_pct_gdp", "Credit owed, share of GDP", "%", None, ""),
       ("ld_share", "Months in a Long Depression", "%", None, ""),
       ("gdp_after_panic", "GDP a year after a panic starts, against the world", "%", None, ""),
       ("gdp_after_mania", "GDP a year after a Mania starts, against the world", "%", None, "")]
BY_SIZE = ["conf_median", "panic_starts_per100", "mania_share", "crash_share", "levers_share"]
P_DIFFERS, P_MAYBE = 0.05, 0.2


def sessions():
    """Every session under runs/ with its finished runs: vanilla (the probe mod alone) or ours."""
    out = []
    for d in sorted(RUNS.glob("*_*"), reverse=True):
        metas = [json.loads(m.read_text(encoding="utf-8")) for m in sorted(d.glob("run*/meta.json"))]
        done = [m for m in metas if m.get("status") == "done"]
        if not done:
            continue
        kind = "vanilla" if "SPEC_PROBE" in (done[0].get("marker") or "") else "mod"
        out.append({"name": d.name, "kind": kind, "runs": len(done), "until": done[0].get("until"),
                    "yearly": any(m.get("by_year") for m in done),
                    "minutes": round(statistics.mean(m["wall_minutes"] for m in done), 1)})
    return out


def load(names):
    """The finished runs of these sessions, pooled."""
    metas = []
    for n in names:
        metas += [json.loads(m.read_text(encoding="utf-8")) for m in sorted((RUNS / n).glob("run*/meta.json"))]
    return [m for m in metas if m.get("status") == "done"]


def series(metas, field, key, count):
    """{year: [one value per run]}, full years only: a run ends on 1 January, so its last year holds a country or two."""
    out = {}
    for m in metas:
        years = m.get(field) or {}
        full = max((y[count] for y in years.values()), default=0)
        for y, row in years.items():
            if row[count] >= full / 2 and row.get(key) is not None:
                out.setdefault(int(y), []).append(row[key])
    return out


def perm_p(a, b, draws=5000):
    """Two-sided permutation test on the difference of medians: exact when the splits are few, sampled otherwise."""
    obs = abs(statistics.median(b) - statistics.median(a))
    pool, n = a + b, len(a)
    total = math.comb(len(pool), n)
    if total <= draws:
        splits = (set(c) for c in itertools.combinations(range(len(pool)), n))
    else:
        rng = random.Random(1)
        splits = (set(rng.sample(range(len(pool)), n)) for _ in range(draws))
        total = draws
    hits = 0
    for s in splits:
        x = [pool[i] for i in s]
        y = [pool[i] for i in range(len(pool)) if i not in s]
        hits += abs(statistics.median(y) - statistics.median(x)) >= obs - 1e-12
    return hits / total


def boot_ci(a, b, draws=2000):
    """Bootstrap 90% interval for median(b) - median(a)."""
    rng = random.Random(2)
    d = sorted(statistics.median(rng.choices(b, k=len(b))) - statistics.median(rng.choices(a, k=len(a))) for _ in range(draws))
    return d[int(0.05 * draws)], d[int(0.95 * draws) - 1]


def compare(a, b):
    """One reading at one year: baseline runs a, mod runs b."""
    ma, mb = statistics.median(a), statistics.median(b)
    out = {"base_median": ma, "base_lo": min(a), "base_hi": max(a), "test_median": mb, "n_base": len(a), "n_test": len(b),
           "change": (mb - ma) / abs(ma) if ma else None}
    if len(a) >= 2 and len(b) >= 2:
        sd = statistics.stdev(a)
        p = perm_p(a, b)
        out.update(p=round(p, 4), ci=boot_ci(a, b), outside=not min(a) <= mb <= max(a),
                   verdict="differs" if p < P_DIFFERS else "maybe" if p < P_MAYBE else "same",
                   # smallest change these batch sizes would usually catch (80% power, 5% two-sided), as a share
                   detectable=2.8 * sd * math.sqrt(1 / len(a) + 1 / len(b)) / abs(ma) if ma else None)
    return out


def reading(block, key):
    """A mod reading from a run's block; the GDP readings are {n, median}."""
    if "." in key:  # top.<key>: the largest economies' block
        group, key = key.split(".", 1)
        block = (block or {}).get(group)
    v = (block or {}).get(key)
    return v.get("median") if isinstance(v, dict) else v


def mod_report(base, test):
    """Our mod's readings: each decade and the whole run for the test batch, the whole run compared with the baseline
    when it ran our mod too (one build against another), by economy size, and the pushes on confidence."""
    has = lambda ms: [m for m in ms if (m.get("mod") or {}).get("total")]
    base, test = has(base), has(test)
    if not test:
        return None
    decades = sorted({int(d) for m in test for d in m["mod"]["decades"]})
    rows = []
    for key, name, unit, target, source in MOD:
        per = {d: [x for m in test if (x := reading(m["mod"]["decades"].get(str(d)), key)) is not None] for d in decades}
        t = [x for m in test if (x := reading(m["mod"]["total"], key)) is not None]
        b = [x for m in base if (x := reading(m["mod"]["total"], key)) is not None]
        # where history sits in the runs: (centre - mean) / sd, about normal, so within 1.64 for 90% of tuned batches
        z = (round((target[2] - statistics.mean(t)) / sd, 2) if target and len(target) > 2 and len(t) > 1
             and (sd := statistics.stdev(t)) > 0 else None)
        rows.append({"key": key, "name": name, "unit": unit, "target": target, "source": source,
                     "decades": {d: v for d, v in per.items() if v}, "test": t, "base": b, "z": z,
                     "cmp": compare(b, t) if b and t else None})
    sizes = {}
    for k in ("small", "medium", "large"):
        sizes[k] = {key: {"test": statistics.median(t) if (t := [x for m in test if (x := reading(m["mod"]["by_size"].get(k), key)) is not None]) else None,
                          "base": statistics.median(b) if (b := [x for m in base if (x := reading(m["mod"]["by_size"].get(k), key)) is not None]) else None}
                    for key in BY_SIZE}
    names = sorted({d for m in test for blk in m["mod"]["decades"].values() for d in blk.get("drivers", {})})
    drivers = {n: {d: statistics.median(v) if (v := [m["mod"]["decades"][str(d)]["drivers"][n] for m in test
                                                      if n in m["mod"]["decades"].get(str(d), {}).get("drivers", {})]) else None
                   for d in decades} for n in names}
    return {"decades": decades, "rows": rows, "by_size": sizes, "size_keys": BY_SIZE, "drivers": drivers,
            "base_runs": len(base), "test_runs": len(test)}


def report(base_names, test_names):
    base, test = load(base_names), load(test_names)
    vanilla = []
    for key, name, unit in VANILLA:
        b, t = series(base, "by_year", key, "countries"), series(test, "by_year", key, "countries")
        years = sorted(set(b) | set(t))
        vanilla.append({"key": key, "name": name, "unit": unit, "years": years,
                        "base": {y: b[y] for y in years if y in b}, "test": {y: t[y] for y in years if y in t},
                        "cmp": {y: compare(b[y], t[y]) for y in years if y in b and y in t}})
    spec = []
    for key, name, unit, target in SPEC:
        t = series(test, "spec_by_year", key, "months")
        spec.append({"key": key, "name": name, "unit": unit, "target": target, "years": sorted(t), "test": t,
                     "median": {y: statistics.median(v) for y, v in t.items()}})
    return {"base": {"sessions": base_names, "runs": len(base)}, "test": {"sessions": test_names, "runs": len(test)},
            "vanilla": vanilla, "spec": spec, "mod": mod_report(base, test)}


def selftest():
    assert perm_p([1, 2, 3], [1, 2, 3]) == 1.0
    assert perm_p([1, 2, 3, 4, 5], [11, 12, 13, 14, 15]) < 0.05
    lo, hi = boot_ci([1, 2, 3, 4, 5], [11, 12, 13, 14, 15])
    assert 7 <= lo <= hi <= 13, (lo, hi)
    c = compare([10, 11, 12, 13, 14], [10.5, 11, 12, 13.5, 14])
    assert c["verdict"] == "same" and not c["outside"], c
    m = [{"by_year": {"1836": {"countries": 100, "x": 1}, "1837": {"countries": 1, "x": 9}}}]
    assert series(m, "by_year", "x", "countries") == {1836: [1]}
    run = {"mod": {"decades": {"1836": {"panic_share": 0.01, "drivers": {"boom": 0.5}}},
                   "total": {"panic_share": 0.01, "gdp_after_panic": {"n": 3, "median": -0.02}},
                   "by_size": {"small": {"conf_median": 50}, "medium": None, "large": None}}}
    mr = mod_report([], [run, run])
    row = next(x for x in mr["rows"] if x["key"] == "gdp_after_panic")
    assert row["test"] == [-0.02, -0.02] and mr["drivers"]["boom"][1836] == 0.5 and mr["by_size"]["small"]["conf_median"]["test"] == 50
    print("stats ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        r = report(sys.argv[1].split("+"), sys.argv[2].split("+"))
        for m in r["vanilla"]:
            print(m["name"])
            for y, c in m["cmp"].items():
                if y % 10 == 5 or y == m["years"][0]:
                    print(f"  {y}  change {c['change'] or 0:+.1%}  p {c.get('p')}  {c.get('verdict')}  "
                          f"detectable {c.get('detectable') or 0:.1%}")
