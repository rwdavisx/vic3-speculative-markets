"""Scorecards for finished tests: each game under runs/sweep_<test>/ against baseline games from the same start.

One game is one random draw: the baseline is the mean of every baseline game from that start, and one pair says little
alone, so read the mean over pairs and its chance range (FINDINGS, How far to trust a test). Only games played to the end
are scored. Countries are the 40 largest at the start, each against itself.
A crash is a rise in Bad Debts; severe means 15 points or more.

Usage: py -3 tools/score.py <test>   prints the scorecard. No argument runs the self-test."""
import json
import math
import re
import statistics as st
import sys
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
MON = {m: i for i, m in enumerate("January February March April May June July August September October November December".split())}
GDP = re.compile(r"tag=([^\s#]+)\S* date=(\w+) \d+, (\d{4}) gdp=([\d.]+)")
PROBE = re.compile(r"tag=([^\s#]+)\S* date=(\w+) \d+, (\d{4}) gdp=([\d.]+) sol=(-?[\d.]+)")
SPEC = re.compile(r"SPEC tag=([^\s#]+)\S* date=(\w+) \d+, (\d{4}) (.*)")
FIELD = re.compile(r"\b(conf|panic|lev|crunch)=(-?[\d.]+)")
TOP = 40
SEVERE, MEDIUM = 15, 5
AFTER = (1, 3, 5, 8)   # years after a crash
NOISE = 4.1   # world GDP: how far two 20-year games from one start differ by chance alone (rms of same-start pairs in sweep_noise)
CHANCE = 2.3   # about 95%, for a spread measured on few games
# the __0 to __3 of the older tests; newer folders carry the save's own name
FORK_SAVES = ["base115_mod_1_1850", "base115_mod_2_1850", "base115_mod_1_1865", "base115_mod_2_1865"]
OFF_ARMS = {"b_v080off", "b_v070"}   # b_v070 is shipped 0.7 plus log lines; b_v080off is 0.8 with leverage off. DLC on, as older baselines were not (FINDINGS, Version 0.8)
BASELINE_ARMS = {"base", "noiseA", "noiseB", "vanilla", *OFF_ARMS}
SCAN_SECONDS = 30


# -- finding games -------------------------------------------------------------------------------------------------

def identify(test, folder, meta):
    """(arm, start save) from a game's folder name: <arm>__<save>_01, or the seed tests' seed1_01, mod1_01, van1_01."""
    label = re.sub(r"_\d\d$", "", folder)
    if m := re.fullmatch(r"(.+)__(.+)", label):
        arm, start = m.groups()
        if start.isdigit():   # only these tests numbered those four saves; others numbered games from 1836
            start = FORK_SAVES[int(start)] if test.startswith(("lev", "noise")) and int(start) < len(FORK_SAVES) else None
    elif m := re.fullmatch(r"(seed|mod|van)(\d+)", label):
        arm, start = "vanilla" if m.group(1) == "van" or "van" in test else "mod", f"seed_{m.group(2)}"
    else:
        arm, start = label, None
    if meta.get("build") == "probe_mod":
        arm = "vanilla"
    return arm, meta.get("save") or start


_scan = (0, [])


def games():
    """Every finished game: {test, folder, arm, start, status, date, minutes, errors, path, when}."""
    global _scan
    if time.time() - _scan[0] < SCAN_SECONDS:
        return _scan[1]
    out = []
    for f in RUNS.glob("sweep_*/*/meta.json"):
        try:
            meta = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        test = f.parent.parent.name[len("sweep_"):]
        arm, start = identify(test, f.parent.name, meta)
        out.append({"test": test, "folder": f.parent.name, "arm": arm, "start": start, "status": meta.get("status"),
                    "date": meta.get("date"), "minutes": meta.get("minutes"), "errors": meta.get("our_errors"),
                    "build": meta.get("build"), "path": str(f.parent), "when": f.stat().st_mtime})
    _scan = (time.time(), out)
    return out


def rescan():
    global _scan
    _scan = (0, [])


def tests():
    """Finished tests, newest first."""
    by = defaultdict(list)
    for g in games():
        by[g["test"]].append(g)
    rows = [{"name": n, "when": max(g["when"] for g in gs), "games": len(gs), "arms": sorted({g["arm"] for g in gs}),
             "bad": sum(g["status"] != "done" for g in gs)} for n, gs in by.items()]
    return sorted(rows, key=lambda r: -r["when"])


def baseline(start):
    """(paths, plain words) of the baseline games for a start: leverage off for forks, vanilla for seeds."""
    gs = [g for g in games() if g["start"] == start and g["status"] == "done"]
    off = [g for g in gs if g["arm"] in OFF_ARMS]
    if off:
        return [g["path"] for g in off], f"{len(off)} games with leverage off"
    van = [g for g in gs if g["arm"] == "vanilla"]
    return [g["path"] for g in van], f"{len(van)} vanilla game{'s' * (len(van) != 1)}"


# -- reading logs --------------------------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _gdp(path, stamp):
    out = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = GDP.search(line)
            if m and m.group(2) in MON:
                k = int(m.group(3)) * 12 + MON[m.group(2)]
                c = out[m.group(1)]
                c[k] = max(c.get(k, 0), float(m.group(4)))
    return dict(out)


@lru_cache(maxsize=256)
def _sol(path, stamp):
    out = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = PROBE.search(line)
            if m and m.group(2) in MON:
                k, c = int(m.group(3)) * 12 + MON[m.group(2)], out[m.group(1)]
                if float(m.group(4)) >= c.get(k, (0, 0))[0]:   # the larger country on a shared tag, as with GDP
                    c[k] = (float(m.group(4)), float(m.group(5)))
    return {t: {k: v[1] for k, v in c.items()} for t, c in out.items()}


@lru_cache(maxsize=256)
def _spec(path, stamp):
    out = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = SPEC.search(line)
            if m and m.group(2) in MON:
                row, c, k = {a: float(b) for a, b in FIELD.findall(m.group(4))}, out[m.group(1)], int(m.group(3)) * 12 + MON[m.group(2)]
                old = c.get(k, {})
                row["panic"] = max(row.get("panic", 0), old.get("panic", 0))
                if (row.get("crunch", 0), row.get("lev", 0)) >= (old.get("crunch", 0), old.get("lev", 0)):
                    c[k] = row   # two countries can share a tag after a civil war: the one in trouble keeps the month
                else:
                    old["panic"] = row["panic"]
    return dict(out)


class Watch:
    """Finds panics and crashes in one tag's rows. After a civil war two countries can log under one tag, one of them with
    zeros, so a zero must not look like Bad Debts ending: the peak fades no faster than Bad Debts do, and a panic only
    counts as new after three clear months."""

    def __init__(self):
        self.peak, self.panic = 0, -99

    def see(self, k, row):
        """(a panic started, the size of a new crash or 0)"""
        crunch, crash, started = row.get("crunch", 0), 0, False
        if crunch > self.peak + .5:
            crash = crunch
        self.peak = max(crunch, self.peak - .2)
        if row.get("panic"):
            started = k - self.panic > 3
            self.panic = k
        return started, crash


def gdp(folder):
    p = Path(folder) / "probe.log"
    return _gdp(str(p), p.stat().st_mtime) if p.exists() else {}


def sol(folder):
    p = Path(folder) / "probe.log"
    return _sol(str(p), p.stat().st_mtime) if p.exists() else {}


def spec(folder):
    p = Path(folder) / "telemetry.log"
    return _spec(str(p), p.stat().st_mtime) if p.exists() else {}


def avg(c, k, w=6):
    """A country's GDP around month k: countries log every 30 days and GDP jitters month to month."""
    xs = [c[j] for j in range(k - w, k + w) if j in c]
    return sum(xs) / len(xs) if xs else None


def world_at(tags, k):
    return sum(avg(c, k) or 0 for c in tags.values())


def span(tags):
    return min(min(c) for c in tags.values() if c), max(max(c) for c in tags.values() if c)


# -- comparing -----------------------------------------------------------------------------------------------------

def against(x, ys):
    """Percent difference from the mean of the baseline games, on logs so a doubling and a halving weigh the same."""
    return 100 * (math.log(x) - st.mean(math.log(y) for y in ys))


def compare(g, s, offs):
    """One test game (g GDP, s telemetry) against its baseline games (offs, GDP each)."""
    first = span(offs[0])[0]
    last = min(span(x)[1] for x in [*offs, g])
    start = {t: avg(c, first + 6) for t, c in offs[0].items()}
    top = sorted((t for t in start if start[t]), key=lambda t: -start[t])[:TOP]
    years = range(0, (last - 6 - first) // 12 + 1)   # the last 6 months would read a half empty window
    r = {"years": (last - first) / 12, "world": against(world_at(g, last - 6), [world_at(o, last - 6) for o in offs]),
         "rel": [], "lev": [], "crashes": [], "panics": 0, "country_years": 0, "groups": [], "top": top, "last": last,
         "gone": sum(not avg(g.get(t, {}), last - 6) for t in top), "gone_off": st.mean(sum(not avg(o.get(t, {}), last - 6) for t in top) for o in offs),
         "series": [(y, against(w, ws)) for y in years
                    if (w := world_at(g, first + 12 * y)) and all(ws := [world_at(o, first + 12 * y) for o in offs])]}
    if len(offs) > 1:
        r["off_series"] = [(y, [against(world_at(o, first + 12 * y), [world_at(x, first + 12 * y) for x in offs]) for o in offs]) for y in years]
    for t in top:
        end, ends = avg(g.get(t, {}), last - 6), [avg(o.get(t, {}), last - 6) for o in offs]
        v = against(end, ends) if end and all(ends) else None
        if v is not None:
            r["rel"].append(v)
        ms = s.get(t, {})
        if not ms:
            continue
        months = sorted(ms)
        r["lev"] += [ms[k].get("lev", 0) for k in months]
        r["country_years"] += len(ms) / 12
        watch = Watch()
        for k in months:
            started, crash = watch.see(k, ms[k])
            r["panics"] += started
            if crash:
                r["crashes"].append({"tag": t, "month": k, "size": crash, "lev": ms[k].get("lev", 0), "after": after_crash(g, offs, t, k, last)})
        if v is not None:
            r["groups"].append((v, st.mean(ms[k].get("lev", 0) for k in months), max(ms[k].get("crunch", 0) for k in months)))
    return r


def after_crash(g, offs, t, k, last):
    """The country's GDP some years on, against what baseline games did over the same years."""
    b, bs = avg(g.get(t, {}), k - 6), [avg(o.get(t, {}), k - 6) for o in offs]
    out = []
    for n in AFTER:
        x, ys = avg(g.get(t, {}), k + 12 * n), [avg(o.get(t, {}), k + 12 * n) for o in offs]
        ok = b and all(bs) and x and all(ys) and k + 12 * n + 6 <= last
        out.append(100 * (math.log(x / b) - st.mean(math.log(y / z) for y, z in zip(ys, bs))) if ok else None)
    return out


def panics_in(s, top):
    """(panics, country years) among these countries, for a baseline game's telemetry."""
    n, months = 0, 0
    for t in top:
        watch = Watch()
        n += sum(watch.see(k, s[t][k])[0] for k in sorted(s.get(t, {})))
        months += len(s.get(t, {}))
    return n, months / 12


def sol_change(g, offs, r):
    """The median big country's standard of living at the end, in points against the baseline games."""
    end, d = r["last"] - 6, []
    for t in r["top"]:
        x, ys = avg(g.get(t, {}), end), [avg(o.get(t, {}), end) for o in offs]
        if x is not None and None not in ys:
            d.append(x - st.mean(ys))
    return st.median(d) if d else None


def group(rows):
    return {"n": len(rows), "median": st.median(rows), "mean": st.mean(rows)} if rows else {"n": 0}


def scorecard_arm(arm, gs):
    """Everything the page shows for one arm of a test."""
    parts, skipped, words = [], [], set()
    for g in gs:
        paths, word = baseline(g["start"]) if g["start"] else ([], "")
        data, offs = gdp(g["path"]), [gdp(p) for p in paths]
        offs = [o for o in offs if o]
        if g["status"] != "done" or not offs or not data or span(data)[1] - span(offs[0])[0] < 24:
            skipped.append(g["folder"])
            continue
        words.add(word)
        r = compare(data, spec(g["path"]), offs)
        r["sol"] = sol_change(sol(g["path"]), [sol(p) for p in paths], r)
        r["off_panics"] = [panics_in(spec(p), r["top"]) for p in paths]
        parts.append((g, r))
    out = {"arm": arm, "games": len(gs), "scored": len(parts), "skipped": skipped, "baseline": ", ".join(sorted(words))}
    if not parts:
        return out
    rs = [r for _, r in parts]
    cy = sum(r["country_years"] for r in rs) or None
    crashes = [c for r in rs for c in r["crashes"]]
    levs = sorted(x for r in rs for x in r["lev"]) or [0]
    groups = [x for r in rs for x in r["groups"]]
    per100 = lambda n: 100 * n / cy if cy else None
    out.update(years=st.mean(r["years"] for r in rs), world=st.mean(r["world"] for r in rs),
               typical=st.mean(st.median(r["rel"]) for r in rs if r["rel"]),
               panics=per100(sum(r["panics"] for r in rs)), medium=per100(sum(c["size"] >= MEDIUM for c in crashes)),
               severe=per100(sum(c["size"] >= SEVERE for c in crashes)), severe_n=sum(c["size"] >= SEVERE for c in crashes),
               country_years=cy, lev_typical=levs[len(levs) // 2], lev_high=levs[int(len(levs) * .9)],
               noise=CHANCE * NOISE / math.sqrt(len(rs)), per_game=[(g["start"], r["world"], st.median(r["rel"]) if r["rel"] else None, r["sol"]) for g, r in parts],
               sol=st.mean(r["sol"] for r in rs if r["sol"] is not None) if any(r["sol"] is not None for r in rs) else None,
               gone=st.mean(r["gone"] for r in rs), gone_off=st.mean(r["gone_off"] for r in rs),
               off_panics=(100 * sum(n for r in rs for n, _ in r["off_panics"]) / y) if (y := sum(c for r in rs for _, c in r["off_panics"])) else None,
               outcomes=[
                   {"name": "Stayed under 1 month of leverage, no crash", **group([v for v, l, c in groups if c < MEDIUM and l < 1])},
                   {"name": "Leverage 1 to 3 months, no crash", **group([v for v, l, c in groups if c < MEDIUM and 1 <= l < 3])},
                   {"name": "Leverage 3 months or more, no crash", **group([v for v, l, c in groups if c < MEDIUM and l >= 3])},
                   {"name": "Medium crash (Bad Debts 5 to 15)", **group([v for v, l, c in groups if MEDIUM <= c < SEVERE])},
                   {"name": "Severe crash (Bad Debts 15 or more)", **group([v for v, l, c in groups if c >= SEVERE])}],
               crashes=[{"name": name, "n": len(cs),
                         "after": [round(st.median(xs), 1) if (xs := [c["after"][i] for c in cs if c["after"][i] is not None]) else None
                                   for i in range(len(AFTER))]}
                        for name, lo, hi in (("Small (1 to 5)", 1, MEDIUM), ("Medium (5 to 15)", MEDIUM, SEVERE), ("Severe (15 or more)", SEVERE, 999))
                        if (cs := [c for c in crashes if lo <= c["size"] < hi])],
               after_years=AFTER, chart=chart(parts))
    return out


def chart(parts):
    """World GDP against baseline by year since the start: each game, their mean, and how far baseline games differ from each other."""
    years = sorted({y for _, r in parts for y, _ in r["series"]})
    games_ = [{"name": g["start"], "data": [dict(r["series"]).get(y) for y in years]} for g, r in parts]
    mean = [st.mean(v) if (v := [x[i] for x in (d["data"] for d in games_) if x[i] is not None]) else None for i, _ in enumerate(years)]
    spread = defaultdict(list)
    for _, r in parts:
        for y, vs in r.get("off_series", []):
            spread[y] += vs
    return {"years": years, "games": games_, "mean": mean, "low": [min(spread[y], default=None) for y in years],
            "high": [max(spread[y], default=None) for y in years]}


def scorecard(test):
    gs = [g for g in games() if g["test"] == test]
    arms = sorted({g["arm"] for g in gs} - BASELINE_ARMS)
    return {"test": test, "games": sorted(gs, key=lambda g: g["folder"]), "severe_target": [.3, .5],
            "arms": [scorecard_arm(a, [g for g in gs if g["arm"] == a]) for a in arms]}


# -- command line --------------------------------------------------------------------------------------------------

def show(test):
    card = scorecard(test)
    for g in card["games"]:
        print(f"{g['folder']:32} {g['status']:8} {g['date'] or '':20} {g['minutes']} min, our errors {g['errors']}")
    f = lambda v, d=1: "-" if v is None else f"{v:.{d}f}"
    for a in card["arms"]:
        print(f"\n{a['arm']}: {a['scored']} of {a['games']} games scored against {a['baseline']}, about {f(a.get('years'), 0)} years")
        if a["scored"]:
            print(f"  world {a['world']:+.1f}%  typical country {a['typical']:+.1f}%  living standards {f(a['sol'], 2)} points  (chance alone about +-{a['noise']:.1f}% on world)")
            for s, w, c, l in a["per_game"]:
                print(f"    {s:22} world {w:+.1f}%  typical {f(c)}%  living standards {f(l, 2)}")
            print(f"  per 100 country years: panics {f(a['panics'], 2)} (baseline {f(a['off_panics'], 2)}), medium or worse {f(a['medium'], 2)}, severe {f(a['severe'], 2)} ({a['severe_n']})")
            print(f"  of the 40 largest, gone by the end: {a['gone']:.1f} (baseline {a['gone_off']:.1f})")
            for o in a["outcomes"]:
                print(f"  by outcome, not cause: {o['name']:44} n {o['n']:3}" + (f"  median {o['median']:+.1f}  mean {o['mean']:+.1f}" if o["n"] else ""))
            for c in a["crashes"]:
                print(f"  crash {c['name']:22} n {c['n']:3}  after {AFTER} years {c['after']}")


def selftest():
    assert identify("lev3", "mix__2_01", {}) == ("mix", FORK_SAVES[2])
    assert identify("seedvan", "seed1_01", {}) == ("vanilla", "seed_1")
    assert identify("seedmod", "seed3_01", {}) == ("mod", "seed_3")
    assert identify("full", "b_080__seed_2_01", {"save": "seed_2"}) == ("b_080", "seed_2")
    assert identify("full", "probe_mod__seed_2_01", {"save": "seed_2", "build": "probe_mod"}) == ("vanilla", "seed_2")
    months = range(1000, 1200)
    off = {t: {k: g for k in months} for t, g in (("AAA", 100.), ("BBB", 50.))}
    test = {t: {k: g * 1.1 for k, g in c.items()} for t, c in off.items()}
    s = {"AAA": {k: {"lev": 2, "crunch": 20 if k >= 1100 else 0, "panic": k == 1100} for k in months}}
    r = compare(test, s, [off, off])
    assert abs(r["world"] - 100 * math.log(1.1)) < 1e-6 and all(abs(x - r["world"]) < 1e-6 for x in r["rel"]), r["world"]
    assert len(r["crashes"]) == 1 and r["crashes"][0]["size"] == 20 and r["panics"] == 1
    assert abs(r["crashes"][0]["after"][0]) < 1e-6, r["crashes"]
    assert r["groups"] == [(r["rel"][0], 2, 20)]
    w = Watch()   # Bad Debts of 25 fading, with a second country's zeros between the rows: one crash, one panic
    seen = [w.see(k, row) for k, row in enumerate([{"crunch": 25, "panic": 1}, {}, {"crunch": 24.8, "panic": 1}, {}, {"crunch": 24.6}, {"crunch": 30}])]
    assert [s[1] for s in seen] == [25, 0, 0, 0, 0, 30] and [s[0] for s in seen] == [True] + [False] * 5, seen
    print("score ok")


if __name__ == "__main__":
    show(sys.argv[1]) if sys.argv[1:] else selftest()
