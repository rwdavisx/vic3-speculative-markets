"""The game's side, read off the headless games we already have, so the engine's input streams look like the game's.

py -3 -B tools/tuner/fit.py

Reads the DLC-on mod games (telemetry since 2026-11-07) through fastsim.load (cached; the 40 largest countries of each
game) and their real GDP off each game's probe.log, on every core. No game is run. Then:
  1. measures the game's side in them: GDP growth and noise, recessions, pool income, the boom and crash pushes on
     confidence, foreign panics, wars and turmoil, government debt drag, business mood;
  2. sets the engine's INPUTS ranges to the middle 80% of countries (clamped to INPUTS' bounds);
  3. searches the boom model (rate, peak, length, each good's share) until the engine's pushes look like the logged ones;
  4. saves tools/tuner/inputs.json: the fitted inputs, the logs' figures and the engine's, for the page's comparison.
engine.defaults() uses inputs.json from then on.
"""
import json
import multiprocessing as mp
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

import engine

RUNS = engine.TOOLS.parent / "runs" / (sys.argv[1] if len(sys.argv) > 1 else "")  # fit.py [runs subfolder]: one set of games only
SINCE = "2026-11-07"  # games before this ran with every DLC feature off
OUT = engine.FITTED
CONTAGION = engine.current()["CONTAGION"]
APPROVAL_SD = 1 / (1 - 0.95 ** 2) ** 0.5  # the engine's approval is x * 0.95 + noise: its spread is about 3.2 x the noise
BUSINESS_AT = 5  # economy.BUSINESS: approval of 5 or more (or -5 or less) moves confidence
STATS = {  # name: (label, unit, per country or pooled over events)
    "growth": ("GDP growth a year", "%", "country"), "gdp_noise": ("GDP noise a month", "%", "country"),
    "recessions": ("Years of falling GDP (over 3%) a century", "", "country"), "recession_depth": ("A falling year's drop", "%", "event"),
    "pool_share": ("Pool income a month, share of GDP", "%", "country"), "pool_noise": ("Pool income noise a month", "%", "country"),
    "boom_share": ("Months booms push confidence", "%", "country"), "boom_size": ("Booms' push in such a month", "", "event"),
    "crash_share": ("Months a boom ends", "%", "country"), "crash_size": ("A month's endings, at resting confidence", "", "event"),
    "foreign_rate": ("Foreign panics reaching us a century", "", "country"), "foreign_size": ("A foreign panic's hit, share of Contagion", "", "event"),
    "war_rate": ("Wars and turmoil a century", "", "country"), "war_months": ("Months they last", "", "event"),
    "war_cost": ("Confidence they take a month", "", "event"), "debt_drag": ("Government debt drag a month", "", "country"),
    "business_share": ("Months business mood moves confidence", "%", "country"),
    "flight_share": ("Countries capital flight reaches", "%", "country"), "flight_rate": ("Capital flights a century, where it reaches", "", "country"),
    "flight_size": ("A capital flight's gain", "", "event"),
    "foreign_total": ("Foreign panics' hits a century", "", "country"), "war_total": ("Turmoil's hits a century", "", "country"),
    "boom_mean": ("A country's boom push, a month's mean", "", "country"), "crash_mean": ("A country's boom endings, a month's mean", "", "country"),
    "boom_year": ("A year's boom push", "", "event"), "crash_year": ("A year's boom endings", "", "event"),
    "levers_on": ("Months the AI holds a lever", "%", "country"), "levers_two": ("Months it holds two or more", "%", "country"),
    "restrain_share": ("Months a restrained boom winds down", "%", "country"),
    "convert_rate": ("Debt conversions a century", "", "country"),
    "panic_rate": ("Panics a century", "", "country"), "panic_share": ("Months in panic", "%", "country"),
    "mania_share": ("Months in Mania", "%", "country"), "conf_level": ("Confidence, a month", "", "event"),
    "repanic": ("Panics back within 13 months of one's end", "%", "event"),
}
MANIA = engine.current()["MANIA"]
KEYS = ("conf", "gdp", "pool", "boom", "crash", "foreign", "turmoil", "business", "debt", "panic", "levers", "restrain", "convert")


# ---------- reading the logs ----------
def games():
    since = time.mktime(time.strptime(SINCE, "%Y-%m-%d"))
    out = []
    for p in RUNS.rglob("telemetry.log"):
        st = p.stat()
        if st.st_mtime >= since and st.st_size > 1_000_000:
            with open(p, "rb") as f:
                if b"SPEC tag=" in f.read(400_000):
                    out.append(str(p))
    return sorted(out)


PROBE = re.compile(r"PROBE tag=(\w+) date=(\w+) (\d+), (\d+) gdp=([-\d.e]+)")


def probe_gdp(path):
    """{tag: (days, gdp)} off the game's probe.log, every 30 days. The SPEC line's gdp= is the rescue cost (GDP x a share that
    moves with Lending Standards, reforms, Central Banking and panics), so GDP comes from here."""
    import fastsim
    per = defaultdict(dict)
    p = Path(path).with_name("probe.log")
    if not p.exists():
        return {}
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "PROBE tag=" in line and (m := PROBE.search(line)):
                day = int(m[4]) * 365 + fastsim.BEFORE[fastsim.MONTHS.index(m[2])] + int(m[3])
                per[m[1]][day] = max(per[m[1]].get(day, 0.0), float(m[5]))  # a breakaway under the same tag: the larger
    return {t: (np.array(sorted(d)), np.array([d[k] for k in sorted(d)])) for t, d in per.items()}


def read(path):
    """One game: each large country's months as arrays (fastsim's rows, its lost months rebuilt), GDP from probe.log."""
    import fastsim
    out, probe = [], probe_gdp(path)
    for tag, c in fastsim.load(Path(path)).items():
        r = c["rows"]
        if len(r) < 24 or len(probe.get(tag, ((),))[0]) < 24:
            continue
        col = lambda k: np.array([x.get(k, 0.0) for x in r], float)
        days, gd = probe[tag]
        want = np.array([fastsim.day_of(x["when"]) for x in r])
        i = np.clip(np.searchsorted(days, want), 1, len(days) - 1)
        i -= (want - days[i - 1]) < (days[i] - want)  # the nearer report
        gdp = np.where(np.abs(days[i] - want) <= 20, gd[i], 0.0)
        out.append(dict(conf=col("conf"), gdp=gdp, pool=col("pool"), boom=col("boom"), crash=col("crash"), foreign=col("foreign"), turmoil=col("d_turmoil"),
                        business=col("d_business"), debt=col("d_debt"), panic=col("left") > 0, levers=col("levers"), restrain=col("restrain"), warend=col("warend"),
                        convert=(np.abs(col("caution") + engine.journal.CONVERT_CONF) < 0.5) * 1.0, year=col("when") / 12))
    return out


# ---------- the figures, the same for the logs and the engine ----------
def spells(mask, gap=0):
    """[start, end) of each run of months, runs no more than `gap` months apart joined."""
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    out = []
    for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if out and s - out[-1][1] <= gap:
            out[-1][1] = e
        else:
            out.append([s, e])
    return out


def robust_sd(x):
    return 1.4826 * float(np.median(np.abs(x - np.median(x)))) if len(x) else 0.0


def q(vals, mean=None):
    v = np.asarray(vals, float)
    if not len(v):
        return {"p10": 0, "p50": 0, "p90": 0, "mean": 0, "n": 0}
    p = np.percentile(v, [10, 50, 90])
    return {"p10": round(float(p[0]), 4), "p50": round(float(p[1]), 4), "p90": round(float(p[2]), 4),
            "mean": round(float(np.mean(v) if mean is None else mean), 4), "n": int(len(v))}


def stats(series):
    """series: [{gdp, pool, boom, crash, foreign, turmoil, business, debt, panic}], monthly arrays of one country each.
    Rates are per country over countries with ten years or more; their mean is pooled over every month."""
    per, ev, count = defaultdict(list), defaultdict(list), defaultdict(float)
    months = 0
    for s in series:
        n, gdp = len(s["gdp"]), s["gdp"]
        ok = np.where(gdp > 0)[0]
        if len(ok) < 24:
            continue
        months += n
        long = n >= 120
        g = gdp[ok]
        per["growth"].append((np.log(g[-1] / g[0]) / ((ok[-1] - ok[0]) / 12)) * 100)
        lg = np.diff(np.log(g))
        per["gdp_noise"].append(robust_sd(lg[np.abs(lg) < 0.5]) * 100)
        yoy = g[12::12] / g[:-12:12] - 1
        falls = yoy[yoy < -0.03]
        count["recessions"] += len(falls)
        ev["recession_depth"] += list(-falls * 100)
        if long:
            per["recessions"].append(len(falls) / max(len(yoy), 1) * 100)
        pk = (s["pool"] > 0) & (gdp > 0)
        if pk.sum() >= 24:
            per["pool_share"].append(float(np.median(s["pool"][pk] / gdp[pk])) * 100)
            lp = np.diff(np.log(s["pool"][pk]))
            per["pool_noise"].append(robust_sd(lp[np.abs(lp) < 1]) * 100)
        calm = ~s["panic"]
        b = s["boom"][calm]
        per["boom_share"].append(float(np.mean(b > 1e-6)) * 100)
        per["boom_mean"].append(float(s["boom"].mean()))
        per["crash_mean"].append(float(-s["crash"].mean()))
        # a year's sums: booms and endings bunch up, which is what carries confidence into a Mania or a panic
        ev["boom_year"] += list(np.convolve(s["boom"], np.ones(12), "valid")[::12])
        ev["crash_year"] += list(-np.convolve(s["crash"], np.ones(12), "valid")[::12])
        ev["boom_size"] += list(b[b > 1e-6])
        c = s["crash"]
        per["crash_share"].append(float(np.mean(c < -1e-6)) * 100)
        ev["crash_size"] += list(-c[c < -1e-6])
        sp = spells(s["foreign"] < -1e-6)
        count["foreign_rate"] += len(sp)
        ev["foreign_size"] += [-s["foreign"][a:e].sum() / CONTAGION for a, e in sp]
        if long:
            per["foreign_rate"].append(len(sp) / n * 1200)
        sp = spells(s["foreign"] > 1e-6)  # capital flight: the mod adds a safe haven's gain to the same figure (diplomacy.MONTHLY)
        count["flight_rate"] += len(sp)
        ev["flight_size"] += [float(s["foreign"][a:e].sum()) for a, e in sp]
        if long:
            per["flight_share"].append(100.0 if sp else 0.0)
            if sp:
                per["flight_rate"].append(len(sp) / n * 1200)
        sp = spells(s["turmoil"] < -1e-6, gap=1)
        count["war_rate"] += len(sp)
        ev["war_months"] += [e - a for a, e in sp]
        ev["war_cost"] += [float(-s["turmoil"][a:e].mean()) for a, e in sp]
        if long:
            per["war_rate"].append(len(sp) / n * 1200)
        per["debt_drag"].append(float(-s["debt"].mean()))
        per["business_share"].append(float(np.mean(np.abs(s["business"]) > 1e-6)) * 100)
        per["foreign_total"].append(float(-s["foreign"][s["foreign"] < 0].sum()) / n * 1200)
        per["war_total"].append(float(-s["turmoil"][s["turmoil"] < 0].sum()) / n * 1200)
        per["levers_on"].append(float(np.mean(s["levers"] >= 1)) * 100)
        per["levers_two"].append(float(np.mean(s["levers"] >= 2)) * 100)
        per["restrain_share"].append(float(np.mean(s["restrain"] < -1e-6)) * 100)
        if long:
            per["convert_rate"].append(float(s["convert"].sum()) / n * 1200)
        p = s["panic"].astype(bool)
        st, en = np.flatnonzero(p & ~np.r_[False, p[:-1]]), np.flatnonzero(~p & np.r_[False, p[:-1]])
        if long:
            per["panic_rate"].append(len(st) / n * 1200)
        per["panic_share"].append(float(p.mean()) * 100)
        per["mania_share"].append(float(np.mean(s["conf"] >= MANIA)) * 100)
        ev["conf_level"] += list(s["conf"][::3])  # every third month is plenty for its 10% and 90%
        ev["repanic"] += [float(np.any((st > e) & (st <= e + 13))) * 100 for e in en]
    out = {}
    for k, (_, _, kind) in STATS.items():
        pooled = count[k] / max(months, 1) * 1200 if k in count else None  # a century is 1200 months
        out[k] = q(per[k] if kind == "country" else ev[k], pooled)
    return out


ERAS = ((1836, 1846), (1866, 1876), (1896, 1906))  # windows.py's decades


def era_stats(series):
    """fit.py --boom: a country's mean boom push and boom endings a month in each of ERAS, as q() gives them."""
    per = defaultdict(list)
    for s in series:
        for j, (a, b) in enumerate(ERAS):
            sel = (s["year"] >= a) & (s["year"] < b)
            if sel.sum() >= 96:
                per[f"boom_e{j}"].append(float(s["boom"][sel].mean()))
                per[f"crash_e{j}"].append(float(-s["crash"][sel].mean()))
                if "braw" in s:  # the push's shape: months at the cap (CONF_BOOM_MAX) and months with nothing hot
                    per[f"cap_e{j}"].append(float((s["braw"][sel] >= engine.g.CONF_BOOM_MAX).mean()))
                    per[f"zero_e{j}"].append(float((s["braw"][sel] < 0.01).mean()))
                    per[f"wsum_e{j}"].append(float(s["wsum"][sel].mean()))  # the goods' summed weights, generate's spec_weight_<g>
                    for v in (1, 2, 3) if "end1" in s else ():  # endings a year by severity (generate.UNWINDS: Correction, Bust, Collapse)
                        per[f"end{v}_e{j}"].append(float(s[f"end{v}"][sel].mean() * 12))
    return {k: q(v) for k, v in per.items()}


def kept_series(e):
    """The engine's kept months, one series per economy, as the logs give them."""
    keys = KEYS + tuple(k for k in ("braw", "wsum", "end1", "end2", "end3") if k in e.kept[0])
    arr = {k: np.stack([m[k] for m in e.kept]) for k in keys}
    year = 1836 + np.arange(len(e.kept)) / 12
    return [{**{k: arr[k][:, i] for k in keys}, "year": year} for i in range(e.keep)]


def engine_stats(a):
    cfg, n, seed = a
    s = kept_series(engine.run({}, cfg, "ai", n, seed, keep=n))
    return stats(s) | era_stats(s)


# ---------- the fit ----------
def clamp_range(k, lo, hi):
    _, blo, bhi, _ = engine.INPUTS[k]
    lo, hi = min(max(lo, blo), bhi), min(max(hi, blo), bhi)
    return [round(float(lo), 5), round(float(max(hi, lo)), 5)]


def direct(L):
    """INPUTS read straight off the logs' middle 80%."""
    r = lambda k, f=1.0: (L[k]["p10"] * f, L[k]["p90"] * f)
    fit = {"growth": clamp_range("growth", *r("growth", 0.01)), "gdp_noise": clamp_range("gdp_noise", *r("gdp_noise", 0.01)),
           "recessions": clamp_range("recessions", *r("recessions")), "recession_depth": clamp_range("recession_depth", *r("recession_depth", 0.01)),
           "pool_share": clamp_range("pool_share", *r("pool_share", 0.01)),
           "pool_noise": clamp_range("pool_noise", *r("pool_noise", 0.01 / (2 / 1.8) ** 0.5)),  # the engine's AR(0.8) spreads a month's noise
           "foreign_rate": clamp_range("foreign_rate", *r("foreign_rate")), "foreign_size": clamp_range("foreign_size", *r("foreign_size")),
           "war_rate": clamp_range("war_rate", *r("war_rate")), "war_months": clamp_range("war_months", *r("war_months")),
           "war_cost": clamp_range("war_cost", *r("war_cost")),
           "flight_share": clamp_range("flight_share", L["flight_share"]["mean"] / 100, L["flight_share"]["mean"] / 100),
           "flight_rate": clamp_range("flight_rate", *r("flight_rate")), "flight_size": clamp_range("flight_size", *r("flight_size"))}
    # government debt: a drag shows past half the credit line, so the share of countries with one sets the range's top
    with_drag = L["debt_drag"]  # per country; the share of them above zero
    share = with_drag["_with"]
    fit["scaled_debt"] = clamp_range("scaled_debt", 0, 0.5 / max(1 - share, 1e-3))
    # business mood: the share of months it moves confidence sets the approval noise (P(|approval| >= 5))
    nd = statistics.NormalDist()
    sd = lambda s: BUSINESS_AT / (APPROVAL_SD * nd.inv_cdf(1 - min(max(s, 1e-4), 0.9999) / 2))
    fit["approval_sd"] = clamp_range("approval_sd", sd(L["business_share"]["p10"] / 100), sd(L["business_share"]["p90"] / 100))
    return fit


# how many levers the AI holds depends on how many booms are risky enough to restrain, and the booms on the restraints
AUTHORITY = ("Authority", ("ai_authority",), (("levers_on", "mean"), ("levers_two", "mean"), ("restrain_share", "mean")))
BLOCKS = (  # what the direct reading can't set: (name, the inputs scaled together, the logged figures they must match)
    # the engine's GDP noise is a random walk and vanilla's swings back, so falling years, not a month's noise, set it
    ("GDP", ("gdp_noise", "recessions", "recession_depth"),
     (("growth", "p50"), ("recessions", "p50"), ("recessions", "p90"), ("recession_depth", "p50"), ("recession_depth", "p90"))),
    # a country's total over the run, since its wars' rate, length and cost go together in the logs (bigger wars last longer)
    ("turmoil", ("war_rate", "war_months", "war_cost"), (("war_rate", "p50"), ("war_months", "p50"), ("war_cost", "p50"), ("war_total", "p50"), ("war_total", "p90"))),
    ("foreign panics", ("foreign_rate", "foreign_size"), (("foreign_rate", "p50"), ("foreign_size", "p50"), ("foreign_total", "p50"), ("foreign_total", "p90"))),
    AUTHORITY,
    ("boom model", ("price_sd", "price_months"),
     (("boom_share", "mean"), ("boom_size", "p50"), ("boom_size", "p90"), ("crash_share", "mean"), ("crash_size", "p50"), ("crash_size", "p90"),
      ("boom_mean", "p10"), ("boom_mean", "p90"), ("crash_mean", "p10"), ("crash_mean", "p90"),
      ("boom_year", "p50"), ("boom_year", "p90"), ("crash_year", "p50"), ("crash_year", "p90"))),
    AUTHORITY,  # again, for the booms the restraints now leave
    # the AI converts its debt when confident with scaled_debt at CONVERT_DEBT or more: how often sets how much it owes
    ("government debt", ("scaled_debt",), (("convert_rate", "mean"),)),
    # last, with every logged driver set: the stand-ins for what is left, the panics, Manias and confidence's spread
    ("roughness", ("after_panic", "rough_sd", "rough_months"),
     (("panic_rate", "mean"), ("panic_share", "mean"), ("mania_share", "mean"), ("conf_level", "p10"), ("conf_level", "p90"), ("repanic", "mean"))))


def scaled(cfg, keys, f):
    c = json.loads(json.dumps(cfg))
    for k, x in zip(keys, f):
        lo, hi = cfg["inputs"][k]
        c["inputs"][k] = clamp_range(k, lo * x, hi * x)
    return c


def miss(E, L, aims):
    return sum(np.log((max(E[s][p], 0) + 0.01) / (max(L[s][p], 0) + 0.01)) ** 2 for s, p in aims)


def search(pool, cfg, L, name, keys, aims, n=300, seed=11):
    """Scale factors on the block's inputs, log-uniform in 0.1 to 10, then closer looks around the best. Returns the cfg."""
    rng = np.random.default_rng(5)
    one = (1.0,) * len(keys)
    best, tried = one, []
    for spread, count in ((100, 96), (4, 48), (2, 48), (1.4, 48)):  # wide, then closing in on the best
        cands = [best] + [tuple(b * np.exp(rng.uniform(-np.log(spread) / 2, np.log(spread) / 2)) for b in best) for _ in range(count - 1)]
        res = pool.map(engine_stats, [(scaled(cfg, keys, f), n, seed) for f in cands])
        tried += [(miss(E, L, aims), f) for E, f in zip(res, cands)]
        best = min(tried)[1]
        print(f"  {name}: {len(tried)} tried, miss {tried[0][0]:.3f} -> {min(tried)[0]:.3f} at x"
              + ", ".join(f"{k} {x:.2f}" for k, x in zip(keys, best)), flush=True)
    return scaled(cfg, keys, best)


def windows_120():
    """fit.py --windows: three inputs read off the clean 1.2.0 campaign's windows (windows.CAMPAIGN, cut as windows.py
    compares them: the 40 largest at each window's start), written into inputs.json.
    pool_share: pool income a month over GDP, each country's median. The draw is uniform, so its range is set from the
    logs' 10% and 50% (what lev_income's 1%-of-GDP floor turns into leverage); the top is a uniform's, short of the logs' tail.
    lure_rate: the logged Lures (rivals.log) by those countries per month whose previous month left them below
    rivals.AI_LEV and not in panic (rivals.spec_rv_ai_move's test, made before the month's line is logged).
    lure_vs: the Lure's spec_rv_vs, a uniform draw held to rivals.VS_LO..VS_HI, set so the shares at each end are the
    logged Lures' (most Lures fall on weaker rivals, at VS_LO)."""
    import fastsim
    import windows
    seen = windows.parse(windows.CAMPAIGN / "telemetry.log", 1836, windows.CAMPAIGN_YEARS * 12, ("gdp", "conf", "ipi", "lev", "panic"))
    acts = [a for a in windows.rival_acts(windows.CAMPAIGN / "rivals.log") if a[0] == "lure"]
    vs_of = {}  # (actor, month): the logged vs
    for line in open(windows.CAMPAIGN / "rivals.log", encoding="utf-8", errors="replace"):
        if (m := re.search(r"act=lure by=(\S+) on=\S+ date=(\w+) \d+, (\d{4}) vs=([\d.]+)", line)):
            vs_of.setdefault((m[1], (int(m[3]) - 1836) * 12 + fastsim.MONTHS.index(m[2])), []).append(float(m[4]))
    gdp = defaultdict(dict)
    for line in open(windows.CAMPAIGN / "probe.log", encoding="utf-8", errors="replace"):
        if (m := PROBE.search(line)):
            k = (int(m[4]) - 1836) * 12 + fastsim.MONTHS.index(m[2])
            gdp[m[1]][k] = max(gdp[m[1]].get(k, 0.0), float(m[5]))
    shares, lures, eligible, vs = [], 0, 0, []
    for era in windows.SAVES:
        a0, y = windows.WINDOWS[era]
        a0, T = a0 * 12, y * 12
        rows = {t: r for t, r in windows.top(seen, a0, T).items() if len(r) >= windows.MIN_MONTHS}
        for t, r in rows.items():
            s = [r[k]["ipi"] * engine.g.WEEKS_PER_MONTH / gdp[t][a0 + k] for k in r if gdp[t].get(a0 + k)]
            if s:
                shares.append(float(np.median(s)))
            for k in r:
                before = seen[t].get(a0 + k - 1)
                if before and before["lev"] < engine.rivals.AI_LEV and before["panic"] <= 0:
                    eligible += 1
                    n = sum(1 for a in acts if a[1] == t and a[2] == a0 + k)
                    lures += n
                    vs += vs_of.get((t, a0 + k), [])[:n]
    p10, p50 = np.percentile(shares, [10, 50])
    width = (p50 - p10) / 0.4
    lo, hi = engine.rivals.VS_LO, engine.rivals.VS_HI
    at_lo, at_hi = np.mean(np.array(vs) <= lo + 1e-3), np.mean(np.array(vs) >= hi - 1e-3)
    span = (hi - lo) / max(1 - at_lo - at_hi, 1e-3)
    fit = {"pool_share": clamp_range("pool_share", p10 - 0.1 * width, p10 + 0.9 * width),
           "lure_rate": clamp_range("lure_rate", lures / eligible, lures / eligible),
           "lure_vs": clamp_range("lure_vs", lo - at_lo * span, hi + at_hi * span)}
    saved = json.loads(OUT.read_text(encoding="utf-8"))
    for k, v in fit.items():
        print(f"  {engine.INPUTS[k][3]}: {saved['inputs'].get(k, engine.INPUTS[k][0])} -> {v}")
        saved["was"].setdefault(k, saved["inputs"].get(k, engine.INPUTS[k][0]))
        saved["inputs"][k] = v
    saved["source"]["windows_120"] = {"countries": len(shares), "pool_share_p10_p50_pct": [round(p10 * 100, 3), round(p50 * 100, 3)],
                                      "lures": int(lures), "eligible_months": eligible, "lure_vs_at_ends_pct": [round(at_lo * 100, 1), round(at_hi * 100, 1)],
                                      "log": "runs/windows_120/campaign", "made": time.strftime("%Y-%m-%d %H:%M")}
    OUT.write_text(json.dumps(saved, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"Saved {OUT}")


def campaign_history():
    """fit.py --history: laws and techs a month off the clean 1.2.0 campaign (windows.CAMPAIGN), into world.npz beside the
    replayed world (engine.follow_history). h_rank: the 40 largest economies at each of h_start (the fiscal snapshots'
    years, as windows.py cuts them), largest first, as rows of h_tags; the Great Power tags are kept too. A month a tag
    did not log keeps its last state, and h_last is its last logged month (annexed, or the log's end)."""
    import fiscal
    import windows
    M = windows.CAMPAIGN_YEARS * 12
    # engine.world's t, f and w, as read() takes them; and Business Mood (economy.BUSINESS: the Industrialists' approval,
    # which follows laws and politics the engine does not model)
    shocks = {"turmoil": "d_turmoil", "foreign": "d_foreign", "warend": "d_warend", "business": "d_business"}
    seen = windows.parse(windows.CAMPAIGN / "telemetry.log", 1836, M, ("gdp", "econ", "money", "techs", "depth", "steady", "stand", *shocks.values()))
    starts = [(int(y) - 1836) * 12 for y in fiscal.profiles()[0]]
    ranked = [list(windows.top(seen, a, 1)) for a in starts]  # top(): the largest in their first month there
    tags = sorted(set(sum(ranked, [])) | set(fiscal.power_tags()))
    ranks = np.array([[tags.index(t) for t in r] for r in ranked])
    # laws and techs as codes; Financial District depth and Manor House steadiness (generate.values: spec_depth, spec_steady) as they are;
    # the Exchange's Standing (spec_exch_stand, 0 Local to 3 World Centre), which the AI's rescue pledge needs at National (1)
    h = {k: np.zeros((len(tags), M), np.int16 if k in ("econ", "money", "techs", "stand") else np.float32)
         for k in ("econ", "money", "techs", "depth", "steady", "stand")}
    last = np.full(len(tags), -1)
    for i, t in enumerate(tags):
        rows = seen.get(t, {})
        if not rows:
            continue
        last[i] = max(rows)
        for k in h:
            v = np.full(M, np.nan)
            for m, r in rows.items():
                v[m] = r[k]
            ok = ~np.isnan(v)
            fill = np.maximum.accumulate(np.where(ok, np.arange(M), 0))  # forward fill; before the first log, the first
            v = np.where(np.arange(M) < np.argmax(ok), v[np.argmax(ok)], v[fill])
            h[k][i] = v
    for k, key in shocks.items():  # a month not logged: no shock
        h[k] = np.array([[seen.get(t, {}).get(m, {}).get(key, 0.0) for m in range(M)] for t in tags], np.float32)
    with np.load(engine.WORLD) as z:
        keep = {k: z[k] for k in z.files if not k.startswith("h_")}
    np.savez(engine.WORLD, **keep, h_tags=np.array(tags), h_last=last, h_rank=ranks, h_start=np.array(starts), h_contagion=CONTAGION,
             **{f"h_{k}": v for k, v in h.items()})
    print(f"  {len(tags)} tags, ranks {ranks.shape} at months {starts}; saved {engine.WORLD}")


BOOM_KEYS = ("price_sd", "price_months")  # fitted, from the logs' 14 months; the basket and engine.SHARE_SD's constants are measured
BASKET_KEYS = ("goods", "goods_growth")
RETIRED = ("good_share", "share_trend", "boom_rate", "boom_months", "boom_peak", "boom_fall")  # the old boom episodes' inputs
ERA_AIMS = tuple((f"{k}_e{j}", "mean") for j in range(len(ERAS)) for k in ("boom", "crash"))
# the push's shape each decade: the logged push is nearly all or nothing (months at the cap, months with nothing hot)
SHAPE_AIMS = tuple((f"{k}_e{j}", "mean") for j in range(len(ERAS)) for k in ("cap", "zero"))
END_AIMS = tuple((f"end{v}_e{j}", "mean") for j in range(len(ERAS)) for v in (1, 2))  # Collapses are too rare to aim at


def campaign_aims():
    """The clean 1.2.0 campaign's figures for fit.py --boom: stats() pooled, and each decade (ERAS) as windows.py cuts it
    (its own 40 largest, as the engine's economies follow by rank). -> (figures, the campaign's series)"""
    import windows
    series = read(str(windows.CAMPAIGN / "telemetry.log"))
    L = stats(series)
    # each decade as windows.py cuts it (its own 40 largest, as the engine's economies follow by rank): the logged push,
    # and the endings at resting confidence as kept_series has them (crash x CONF_START over last month's confidence)
    seen = windows.parse(windows.CAMPAIGN / "telemetry.log", 1836, windows.CAMPAIGN_YEARS * 12, ("gdp", "conf", "boom", "crash", "braw", "wsum", "end1", "end2", "end3"))
    for j, (a, b) in enumerate(ERAS):
        rows = windows.top(seen, (a - 1836) * 12, (b - a) * 12)
        boom, crash, cap, zero, wsum, ends = [], [], [], [], [], {v: [] for v in (1, 2, 3)}
        for t, r in rows.items():
            if len(r) < (b - a) * 12 * 0.8:
                continue
            ks = sorted(r)
            boom.append(np.mean([r[k]["boom"] for k in ks]))
            crash.append(-np.mean([r[k]["crash"] * engine.current()["CONF_START"] / max(r.get(k - 1, r[k])["conf"], 1) for k in ks]))
            cap.append(np.mean([r[k]["braw"] >= engine.g.CONF_BOOM_MAX for k in ks]))
            zero.append(np.mean([r[k]["braw"] < 0.01 for k in ks]))
            wsum.append(np.mean([r[k]["wsum"] for k in ks]))
            for v in ends:
                ends[v].append(np.mean([r[k][f"end{v}"] for k in ks]) * 12)
        L[f"boom_e{j}"], L[f"crash_e{j}"], L[f"cap_e{j}"], L[f"zero_e{j}"], L[f"wsum_e{j}"] = q(boom), q(crash), q(cap), q(zero), q(wsum)
        for v in ends:
            L[f"end{v}_e{j}"] = q(ends[v])
    return L, series


def boom_aims():
    """The figures fit.py --boom aims at (BLOCKS' boom block, each decade's push, its shape and endings by severity)."""
    return next(b for b in BLOCKS if b[0] == "boom model")[2] + ERA_AIMS + SHAPE_AIMS + END_AIMS


def campaign_boom():
    """fit.py --boom: the boom model's two free inputs (each good's price swing a month and how long a deviation lasts,
    BLOCKS' boom block) refit to the clean 1.2.0 campaign alone: its pooled figures, each decade's mean push and endings
    (ERAS), the push's shape and the endings a year by severity, on the engine as it now stands (history, world). The
    search starts from engine.INPUTS (price_months from the logs' autocorrelation). The goods' basket is measured
    (engine.INPUTS goods and goods_growth, written as they are); the retired episode inputs go."""
    sys.stdout.reconfigure(errors="replace")
    import windows
    L, series = campaign_aims()
    cfg = engine.defaults()
    cfg["inputs"]["years"] = windows.CAMPAIGN_YEARS
    cfg["inputs"] |= {k: list(engine.INPUTS[k][0]) for k in BASKET_KEYS + BOOM_KEYS}
    name, keys, _ = next(b for b in BLOCKS if b[0] == "boom model")
    aims = boom_aims()
    checks = tuple((f"{k}_e{j}", "mean") for j in range(len(ERAS)) for k in ("wsum", "end3"))
    with mp.get_context("spawn").Pool(os.cpu_count()) as pool:
        cfg = search(pool, cfg, L, name, keys, aims)
    E = engine_stats((cfg, 1000, 3))
    saved = json.loads(OUT.read_text(encoding="utf-8"))
    for k in RETIRED:
        saved["inputs"].pop(k, None)
    for k in BOOM_KEYS + BASKET_KEYS:
        print(f"  {engine.INPUTS[k][3]}: {saved['inputs'].get(k, engine.INPUTS[k][0])} -> {cfg['inputs'][k]}")
        saved["was"].setdefault(k, saved["inputs"].get(k, engine.INPUTS[k][0]))
        saved["inputs"][k] = cfg["inputs"][k]
    saved["source"]["campaign_boom"] = {"countries": len(series), "made": time.strftime("%Y-%m-%d %H:%M"),
                                        "aims": {f"{s} {p}": [L[s][p], E[s][p]] for s, p in aims + checks}}
    OUT.write_text(json.dumps(saved, indent=1) + "\n", encoding="utf-8", newline="\n")
    for s, p in aims + checks:
        print(f"  {s:12s} {p}: campaign {L[s][p]:8.3f}  engine {E[s][p]:8.3f}")
    print(f"Saved {OUT}")


if __name__ == "__main__" and "--boom" in sys.argv:
    campaign_boom()
elif __name__ == "__main__" and "--history" in sys.argv:
    campaign_history()
elif __name__ == "__main__" and "--windows" in sys.argv:
    windows_120()
elif __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    t0 = time.time()
    paths = games()
    print(f"{len(paths)} logged games since {SINCE}; reading them on {os.cpu_count()} cores (fastsim's cache makes reruns quick)", flush=True)
    with mp.get_context("spawn").Pool(os.cpu_count()) as pool:
        series = [s for part in pool.imap_unordered(read, paths, chunksize=1) for s in part]
        years = sum(len(s["gdp"]) for s in series) / 12
        span = (int(min(s["year"][0] for s in series)), int(max(s["year"][-1] for s in series)))
        print(f"  {len(series)} country-games, {years:,.0f} country-years, {span[0]} to {span[1]}, read in {time.time() - t0:.0f}s", flush=True)
        L = stats(series)
        # the world the engine replays (engine.world): each country's turmoil, foreign hits and war endings, wrapped to 64 years
        M = 64 * 12
        hist = {}
        if engine.WORLD.exists():  # fit.py --history's laws and techs stay
            with np.load(engine.WORLD) as z:
                hist = {k: z[k] for k in z.files if k.startswith("h_")}
        np.savez(engine.WORLD, contagion=CONTAGION, **hist, **{k: np.array([np.resize(s[c], M) for s in series], np.float32)
                                                        for k, c in (("t", "turmoil"), ("f", "foreign"), ("w", "warend"))})
        dd = np.array([s["debt"].mean() for s in series if len(s["gdp"]) >= 24])
        L["debt_drag"]["_with"] = float(np.mean(dd < -0.01))
        base = engine.defaults(fitted=False)
        cfg = json.loads(json.dumps(base))
        cfg["inputs"]["years"] = 60  # the logs cover 1836 to 1920, most of them before 1890
        measured = {"scaled_debt", "ai_authority"} if cfg["inputs"]["fiscal_profiles"] else set()
        cfg["inputs"].update((k, v) for k, v in direct(L).items() if k not in measured)
        for name, keys, aims in BLOCKS:
            if measured.intersection(keys):
                continue
            cfg = search(pool, cfg, L, name, keys, aims)
        E = engine_stats((cfg, 1000, 3))
        lift = (L["growth"]["p50"] - E["growth"]["p50"]) / 100  # recessions take their part of the growth: give it back
        cfg["inputs"]["growth"] = clamp_range("growth", *(x + lift for x in cfg["inputs"]["growth"]))
        print(f"  growth: the range lifted {lift * 100:+.2f} points for what recessions take", flush=True)
        E = engine_stats((cfg, 1000, 3))
    fitted = {k: cfg["inputs"][k] for k in engine.INPUTS if k != "years" and list(np.atleast_1d(cfg["inputs"][k])) != list(np.atleast_1d(base["inputs"][k]))}
    was = {k: base["inputs"][k] for k in fitted}
    L["debt_drag"].pop("_with")
    OUT.write_text(json.dumps({"source": {"games": len(paths), "country_games": len(series), "country_years": round(years), "since": SINCE,
                                          "years": span, "made": time.strftime("%Y-%m-%d %H:%M"), "player": "ai"},
                               "inputs": fitted, "was": was, "log": L, "engine": E, "stats": STATS}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("\nFitted inputs (old -> new):")
    for k in fitted:
        print(f"  {engine.INPUTS[k][3]}: {was[k]} -> {fitted[k]}")
    print("\nLogs vs engine (10% / median / 90%):")
    for k, (label, unit, _) in STATS.items():
        a, b = L[k], E[k]
        print(f"  {label:44s} logs {a['p10']:7.3f} {a['p50']:7.3f} {a['p90']:7.3f}   engine {b['p10']:7.3f} {b['p50']:7.3f} {b['p90']:7.3f}")
    print(f"\nSaved {OUT} in {time.time() - t0:.0f}s")
