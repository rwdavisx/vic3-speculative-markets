"""Level 3 of the tuning method: real-game 10-year windows beside the tuner's AI preset cut into the same windows.

py -3 -B tools/tuner/windows.py run       three headless AI-only games, 1836, 1866 and 1896 for 10 years each, in parallel
py -3 -B tools/tuner/windows.py campaign  one headless AI-only game from the 1836 bookmark to the end of 1905 (runs/windows_120/campaign),
                                          keeping its Jan 1866 and Jan 1896 autosaves in campaign/saves and its SPECRV rival acts in rivals.log
py -3 -B tools/tuner/windows.py compare   the same metrics from those logs and from the tuner, into tools/tuner/windows.json; with a campaign
                                          log it cuts the windows (and the whole run, 1836-1906) from it, with driver statistics

The game runs a --log build of the generators (build_scratch/windows_120/build), checked against the staged 1.2.0 release
before any game starts: every staged file must be byte-identical, or the log build may only add lines to it. Each game
gets its own -userdir under build_scratch/windows_120/user, DLC on (sweep.start sets SteamAppId). Logs go to
runs/windows_120/<era>/.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import engine  # noqa: E402
import fastsim  # noqa: E402

BUILD_NAME = "1.2.0"
RELEASE = ROOT / "workshop/upload_staging/beta"  # gameplay bytes match stable 1.2.0
SCRATCH = ROOT / "build_scratch/windows_120"
BUILD = SCRATCH / "build"
RUNS = ROOT / "runs/windows_120"
OUT = HERE / "windows.json"
# ponytail: the 1866 and 1896 starts are one DLC-on campaign of the 1.2.0 release candidate (sweep feedback_120_release_candidate,
# 2026-11-21), so each window opens on decades of 1.2 rules. PARITY.md's fiscal saves (full2_b_big2_1_*) are a Nov 7 build.
SAVES = {"1836": None, "1866": "feedback_120_release_candidate_candidate_1_1866", "1896": "feedback_120_release_candidate_candidate_1_1896"}
YEARS = 10
MIN_MONTHS = 96  # a country with fewer logged months in its window is left out
TUNER_N, TUNER_SEED = 1000, 1


# ---------- the game ----------
def build():
    env = {**os.environ, "SPEC_MOD_OUT": str(BUILD), "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("SPEC_TUNING", None)
    subprocess.run([sys.executable, "-B", str(TOOLS / "generate.py"), "--log"], cwd=TOOLS, env=env, check=True, stdout=subprocess.DEVNULL)
    bad = []
    for p in RELEASE.rglob("*"):
        rel = p.relative_to(RELEASE).as_posix()
        if not p.is_file() or rel in ("thumbnail.png", ".metadata/metadata.json"):
            continue
        q = BUILD / rel
        if not q.exists():
            bad.append(f"missing {rel}")
        elif q.read_bytes() != p.read_bytes():
            have = {l.strip().lstrip("﻿") for l in q.read_text("utf-8", "replace").splitlines()}
            if any(l.strip().lstrip("﻿") not in have for l in p.read_text("utf-8", "replace").splitlines()):
                bad.append(f"changed {rel}")
    if bad:
        raise SystemExit("The log build is not 1.2.0 plus logging: " + "; ".join(bad[:10]))


def keep_rivals(sweep):
    """sweep keeps only SPEC tag= lines; this also writes each game's SPECRV acts to rivals.log."""
    finish = sweep.finish

    def wrapped(job, status, folder):
        game = finish(job, status, folder)
        (folder / "rivals.log").write_text("\n".join(l for l in job["seen"] if "SPECRV act=" in l), encoding="utf-8")
        # newer --log builds: every trust change with its cause (SPECTR) and each AI rival look (SPECRVA)
        for name, mark in (("trust.log", "SPECTR tag="), ("rvai.log", "SPECRVA tag=")):
            (folder / name).write_text("\n".join(l for l in job["seen"] if mark in l), encoding="utf-8")
        return game
    sweep.finish = wrapped


def run(dest="parallel"):
    """The three windows in parallel (sweep kills only its own games). With the campaign's saves: the 1836 bookmark and the
    campaign's Jan 1866 and Jan 1896, logs to runs/windows_120/<dest>/<era> (default parallel; parallel2 keeps the first sample);
    without them the old release-candidate saves."""
    import sweep
    build()
    sweep.WORK = SCRATCH / "user"  # private user folders, nowhere near the player's
    fresh = all((CAMPAIGN / "saves" / f"campaign_{y}.v3").exists() for y in KEEP_SAVES)
    if fresh:
        arms = {era: (BUILD, CAMPAIGN / "saves" / f"campaign_{era}.v3" if era != "1836" else None) for era in SAVES}
    else:
        arms = {era: (BUILD, sweep.SAVES / f"{s}.v3" if s else None) for era, s in SAVES.items()}
    for era, (_, save) in arms.items():
        if save and not save.exists():
            raise SystemExit(f"{era}: no save {save}")
    keep_rivals(sweep)
    t = time.time()
    sweep.run("windows_120", arms, 1, YEARS, len(arms), timeout=180, log=lambda s: print(s, flush=True))
    for era in SAVES:
        src, dst = ROOT / "runs/sweep_windows_120" / f"{era}_01", (RUNS / dest if fresh else RUNS) / era
        if src.exists():
            shutil.rmtree(dst, ignore_errors=True)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
    print(f"wall {(time.time() - t) / 60:.1f} min")


def parse(path, start, months, keys=None):
    """{tag: {month 0..months-1: SPEC fields}} for every country; keys: keep only these, as numbers (a long log)."""
    seen = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SPEC tag=" in line and (m := fastsim.LOG.search(line)):
                d = dict(p.split("=", 1) for p in m[5].split() if "=" in p)
                k = (int(m[4]) - start) * 12 + fastsim.MONTHS.index(m[2])
                if "conf" in d and 0 <= k < months and (k not in seen[m[1]] or fastsim.num(d, "gdp") > fastsim.num(seen[m[1]][k], "gdp")):
                    seen[m[1]][k] = {x: fastsim.num(d, x) for x in keys} if keys else d  # a breakaway under the same tag: the larger keeps it
    # the SPEC line's gdp= is spec_rescue_cost (GDP x a share that grows with Lending Standards and without Central
    # Banking), so ranking by it picks Reckless lenders: rank by the real GDP probe.log reports beside it (rgdp)
    probe = Path(path).with_name("probe.log")
    if probe.exists():
        with open(probe, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "PROBE tag=" in line and (m := PROBE.search(line)):
                    k = (int(m[4]) - start) * 12 + fastsim.MONTHS.index(m[2])
                    if (r := seen.get(m[1], {}).get(k)) is not None:
                        r["rgdp"] = max(fastsim.num(r, "rgdp"), float(m[5]))
    return seen


PROBE = re.compile(r"PROBE tag=(\w+) date=(\w+) (\d+), (\d+) gdp=([-\d.e]+)")


def top(seen, a, T):
    """The months a to a+T of the 40 largest economies by real GDP (probe.log; else the SPEC line's gdp=) in their first
    month there (fastsim.TOP), counted from 0."""
    rows = {t: {k - a: r for k, r in s.items() if a <= k < a + T} for t, s in seen.items()}
    rows = {t: r for t, r in rows.items() if r}
    probed = any("rgdp" in r for s in rows.values() for r in s.values())
    # probe.log reports every 30 days, so a month can lack one: the earliest report in the window
    first = lambda t: next((r["rgdp"] for k, r in sorted(rows[t].items()) if "rgdp" in r), 0.0) if probed else fastsim.num(rows[t][min(rows[t])], "gdp")
    return {t: rows[t] for t in sorted(rows, key=first, reverse=True)[:fastsim.TOP]}


def game_months(path, start, years=YEARS):
    """{tag: {month 0..: SPEC fields}} for the 40 largest economies in the window's first month (fastsim.TOP)."""
    return top(parse(path, start, years * 12), 0, years * 12)


# ---------- the metrics, one value per country-decade, the same for both sides ----------
K = engine.current()
WARY = engine.TIER["steady"][0]


def frozen(crunch, lax):  # engine.crunch_lend <= 0, the mod's spec_crunch_lend
    return crunch >= K["LEV_BAD_STOP"] * ((lax - 0.5) * 2 * K["LAX_BADSTOP"] + 1)


def metrics(conf, panic, lev, crunch, lax):
    """Each a (countries x months) array for one window; a month a country didn't log is NaN in conf."""
    ok = ~np.isnan(conf)
    onset = panic[:, 1:] & ~panic[:, :-1] & ok[:, 1:] & ok[:, :-1]  # a panic already running at the window's start isn't one of its own
    share = lambda x: (x & ok).sum(1) / ok.sum(1) * 100
    return {"panics_per_decade": onset.sum(1) * 120 / ok.sum(1),
            "mania_pct": share(conf >= K["MANIA"]), "low_pct": share((conf < WARY) | panic),
            "lev_mean": np.nansum(np.where(ok, lev, 0), 1) / ok.sum(1), "frozen_months_pct": share(frozen(crunch, lax)),
            "panic_months_pct": share(panic), "crunch_months_pct": share(crunch > 0), "conf_mean": np.nanmean(conf, 1)}


LABELS = {"panics_per_decade": ("Panics per country per decade", ""), "mania_pct": ("Months in Mania", "%"),
          "low_pct": ("Months Wary or in Panic", "%"), "lev_mean": ("Leverage, mean months", ""),
          "frozen_months_pct": ("Months with lending frozen", "%"), "panic_months_pct": ("Months in panic", "%"),
          "crunch_months_pct": ("Months with Bad Debts", "%"), "conf_mean": ("Confidence, mean", "")}


# ---------- the campaign: one game from the 1836 bookmark to the end of 1905, cut into the same windows ----------
CAMPAIGN = RUNS / "campaign"
CAMPAIGN_YEARS = 70
WINDOWS = {"1836": (0, YEARS), "1866": (30, YEARS), "1896": (60, YEARS), "1836-1906": (0, CAMPAIGN_YEARS)}  # era: (years after 1836, years)
KEEP_SAVES = (1866, 1896)
KEYS = ("gdp", "conf", "panic", "lev", "crunch", "lax", "trust", "boom", "braw", "pool", "ipi", "climit", "econ", "money", "techs", "stance")
RV = re.compile(r"SPECRV act=(lure|raid) by=(\S+) on=(\S+) date=(\w+) \d+, (\d{4}) .*?ok=(\S+)(?:.*? amt=(\S+) cost=([-\d.]+))?")


def era_name(era):
    a, y = WINDOWS[era]
    return f"{1836 + a}-{1836 + a + y}"


def campaign():
    import sweep
    build()
    busy = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"name='victoria3.exe'\" | "
                           "Where-Object { $_.CommandLine -like '*-handsoff*' -and $_.CommandLine -like '*windows_120*' } | Measure-Object | % Count"],
                          capture_output=True, text=True).stdout.strip()
    if busy not in ("", "0"):
        raise SystemExit(f"{busy} headless game(s) of windows_120 already running: one at a time")
    sweep.WORK = SCRATCH / "user"
    sweep.SAVES = SCRATCH / "campaign_saves"  # sweep.keep_saves copies the yearly autosave here when the game reaches each year
    keep_rivals(sweep)
    t = time.time()
    sweep.run("windows_campaign", {"campaign": BUILD}, 1, CAMPAIGN_YEARS, 1, timeout=480, log=lambda s: print(s, flush=True), keep=KEEP_SAVES)
    src = ROOT / "runs/sweep_windows_campaign/campaign_01"
    if src.exists():
        shutil.rmtree(CAMPAIGN, ignore_errors=True)
        CAMPAIGN.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, CAMPAIGN)
        (CAMPAIGN / "saves").mkdir(exist_ok=True)
        for y in KEEP_SAVES:
            if (p := sweep.SAVES / f"windows_campaign_campaign_1_{y}.v3").exists():
                shutil.move(p, CAMPAIGN / "saves" / f"campaign_{y}.v3")
    print(f"wall {(time.time() - t) / 60:.1f} min")


def arrays(rows, T):
    """Each logged field a (countries x T) array, NaN where a month is missing; countries with under 80% of the months left out."""
    rows = [r for r in rows.values() if len(r) >= T * 0.8]
    if not rows:
        return None
    return {key: np.array([[fastsim.num(r[k], key) if k in r else np.nan for k in range(T)] for r in rows]) for key in KEYS}


def game_side(A):
    return metrics(A["conf"], np.nan_to_num(A["panic"]) > 0, A["lev"], np.nan_to_num(A["crunch"]), np.nan_to_num(A["lax"], nan=0.5))


TRUST_LOW = 30  # Distrusted: the first quarter of centres.CALM
LEND_CONF = (60, 70)
ECON_CODES = ["none"] + engine.g.LOG_ECON
MONEY_CODES = ["none"] + __import__("monetary").LAWS
assert engine.g.LOG_TECHS == list(engine.TECH_YEARS), "the log's tech bitmask and the tuner's techs differ"


def drivers(ok, trust, lax, boom, lend, econ, money, techs, lures, lure_size, raids=None, raid_size=None, raid_ok=None, braw=None):
    """One era's driver statistics, the same on both sides. ok, trust, lax, boom: (countries x months); lend: the eligible months'
    lending per pool month; econ, money: law names a month; techs: (countries x months x 11) bools; lures, raids: counts."""
    per = lambda x: float(np.mean(np.nansum(np.where(ok, x, 0), 1) / ok.sum(1)))
    months = ok.sum()
    out = {"trust_low_pct": per(trust < TRUST_LOW) * 100, "lax_mean": per(lax), "boom_mean": per(boom),
           "lend_per_pool_month": float(np.mean(lend)) if len(lend) else None, "lend_months": int(len(lend)),
           "lures_per_country_decade": lures / (months / 120), "lure_size_pool_months": float(np.median(lure_size)) if len(lure_size) else None,
           "econ_pct": {k: float((econ[ok] == k).mean() * 100) for k in ECON_CODES if (econ[ok] == k).any()},
           "money_pct": {k: float((money[ok] == k).mean() * 100) for k in MONEY_CODES if (money[ok] == k).any()},
           "tech_pct": {t: float(techs[..., i][ok].mean() * 100) for i, t in enumerate(engine.TECH_YEARS)}}
    if braw is not None:
        out["boom_raw_mean"] = per(braw)
    if raids is not None:
        out |= {"raids_per_country_decade": raids / (months / 120), "raid_size_conf": float(np.median(raid_size)) if len(raid_size) else None,
                "raid_ok_pct": float(np.mean(raid_ok) * 100) if len(raid_ok) else None}
    return out


def lend_months(conf, panic, stance, crunch, lax, lev, climit, lent):
    """Lending per pool month in the months a lender could lend at confidence 60 to 70: not in panic, not Tight, not frozen,
    and at least a month of pool income below the credit limit."""
    e = (conf >= LEND_CONF[0]) & (conf < LEND_CONF[1]) & ~panic & (stance != -1) & ~frozen(crunch, lax) & (lev <= climit - 1) & np.isfinite(lent)
    return lent[e]


def game_drivers(A, tags, a, T, rv):
    ok = ~np.isnan(A["conf"])
    pm = A["ipi"] * engine.g.WEEKS_PER_MONTH
    lent = np.where(pm > 0, A["pool"] / np.where(pm > 0, pm, 1), np.nan)
    panic = np.nan_to_num(A["panic"]) > 0
    lend = lend_months(A["conf"], panic, A["stance"], np.nan_to_num(A["crunch"]), np.nan_to_num(A["lax"], nan=0.5), A["lev"], A["climit"], lent)
    code = lambda x, names: np.array(names, dtype=object)[np.clip(np.nan_to_num(x).astype(int), 0, len(names) - 1)]
    bits = np.nan_to_num(A["techs"]).astype(int)
    techs = np.stack([(bits >> i) & 1 > 0 for i in range(len(engine.TECH_YEARS))], -1)
    row = {t: i for i, t in enumerate(tags)}
    acts = [r for r in rv if r[1] in row and a <= r[2] < a + T]
    lure = [r for r in acts if r[0] == "lure"]
    raid = [r for r in acts if r[0] == "raid"]
    size = [r[4] / pm[row[r[1]], r[2] - a] for r in lure if r[4] is not None and np.isfinite(pm[row[r[1]], r[2] - a]) and pm[row[r[1]], r[2] - a] > 0]
    return drivers(ok, A["trust"], A["lax"], A["boom"], lend, code(A["econ"], ECON_CODES), code(A["money"], MONEY_CODES), techs,
                   len(lure), size, len(raid), [r[3] for r in raid if r[3] is not None], [r[5] for r in raid], braw=A["braw"])


def rival_acts(path):
    """[(act, actor, month after Jan 1836, amt, cost, worked)] from rivals.log."""
    out = []
    if path.exists():
        for line in open(path, encoding="utf-8", errors="replace"):
            if m := RV.search(line):
                f = lambda s: float(s) if s not in (None, "") and re.fullmatch(r"[-\d.]+", s) else None
                out.append((m[1], m[2], (int(m[5]) - 1836) * 12 + fastsim.MONTHS.index(m[4]), f(m[7]), f(m[8]), f(m[6]) == 1))
    return out


class Recorded(engine.Economies):
    """The tuner's economies, with what the drivers need recorded each month (engine.py itself unchanged)."""
    def step(self, global_crisis=None):
        before = self.stats["lent_sum"].copy()
        super().step(global_crisis)
        self.rec.append((self.stats["lent_sum"] - before, self.credit_limit(), self.stance.copy(), self.econ.copy(), self.money_base.copy(),
                         np.stack([self.has(t) for t in engine.TECH_YEARS], -1), self.lured.copy()))


def tuner_side(eras):
    """The AI preset (lab's defaults, bot "ai") over 1836 to 1906, a snapshot every month, cut into the windows: (metrics, drivers)."""
    cfg = engine.defaults()
    cfg["inputs"]["years"] = 71
    engine.SNAP = 1  # bands() reads the same snapshots every 6 months by default; monthly here, nothing else changes
    K = engine.current()  # engine.run's three lines, with the recording subclass
    if engine.lv.LADDER[0] == engine.lv.SAFE:
        K["LADDER"] = (K["LEV_SAFE"], *engine.lv.LADDER[1:])
    e = Recorded(K, cfg, "ai", TUNER_N, TUNER_SEED, False, TUNER_N)
    e.rec = []
    e.run()
    conf, panic, lev, crunch, lax, trust = (np.array(a).T for a in list(zip(*e.snap))[:6])
    trust = trust * engine.centres.CALM
    boom = np.array([k["boom"] for k in e.kept]).T
    pm = np.array([k["pool"] for k in e.kept]).T
    lent, climit, stance, econ, money, techs, lured = (np.array(a).swapaxes(0, 1) for a in zip(*e.rec))
    out = {}
    for era in eras:
        a, y = WINDOWS[era]
        w = slice(a * 12, (a + y) * 12)
        panic_w = panic[:, w].astype(bool)
        ok = np.ones_like(conf[:, w], bool)
        lend = lend_months(conf[:, w], panic_w, stance[:, w], crunch[:, w], lax[:, w], lev[:, w], climit[:, w], lent[:, w])
        lu = lured[:, w] > 0
        out[era] = (metrics(conf[:, w], panic_w, lev[:, w], crunch[:, w], lax[:, w]),
                    drivers(ok, trust[:, w], lax[:, w], boom[:, w], lend, econ[:, w], money[:, w], techs[:, w], int(lu.sum()),
                            (lured[:, w] / np.maximum(pm[:, w], 1))[lu]))
    return out


def game_eras(eras, folder):
    """(metrics, drivers) per era from the logs in folder(era), dated from Jan 1836 like the campaign."""
    G, D, cache, reached = {}, {}, {}, -1
    for era in eras:
        f = folder(era)
        if f not in cache:
            cache[f] = (parse(f / "telemetry.log", 1836, CAMPAIGN_YEARS * 12, KEYS), rival_acts(f / "rivals.log"))
        seen, rv = cache[f]
        reached = max([reached] + [max(s) for s in seen.values() if s])
        a, y = WINDOWS[era]
        rows = top(seen, a * 12, y * 12)
        rows = {t: r for t, r in rows.items() if len(r) >= y * 12 * 0.8}
        A = arrays(rows, y * 12)
        G[era] = game_side(A) if A else None
        D[era] = game_drivers(A, list(rows), a * 12, y * 12, rv) if A else None
    return G, D, reached


def compare(sample="campaign"):
    """sample "parallel" (or "parallel2", ...): a hold-out, the three 10-year games of runs/windows_120/<sample>, into windows_<sample>.json."""
    global OUT
    log = CAMPAIGN / "telemetry.log"
    if sample.startswith("parallel"):
        eras = list(SAVES)
        G, D, _ = game_eras(eras, lambda e: RUNS / sample / e)
        OUT = HERE / f"windows_{sample}.json"
        source = f"Game values: three 10-year headless AI-only 1.2.0 games (runs/windows_120/{sample}), the 1836 bookmark and the campaign's 1866 and 1896 saves."
    elif log.exists():
        eras = list(WINDOWS)
        G, D, reached = game_eras(eras, lambda e: CAMPAIGN)
        source = (f"Game values: one headless AI-only 1.2.0 game (DLC on) from the 1836 bookmark, logged to "
                  f"{fastsim.MONTHS[reached % 12]} {1836 + reached // 12} (runs/windows_120/campaign), cut into the windows.")
    else:
        eras = list(SAVES)
        G, D = {}, {}
        for era in eras:
            p = RUNS / era / "telemetry.log"
            A = arrays(game_months(p, int(era)), YEARS * 12) if p.exists() else None
            G[era], D[era] = (game_side(A) if A else None), None
        source = ("Game values: three 10-year headless AI-only games, the 1836 bookmark and a 1.2.0 release-candidate campaign's "
                  "1866 and 1896 saves (runs/windows_120/<era>).")
    TS = tuner_side(eras)
    T = {e: TS[e][0] for e in eras}
    notes = [source]
    for era in eras:
        if G[era] is None:
            notes.append(f"The {era_name(era)} window has no game log yet, so its game values are null.")
    r = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 3)
    out = []
    for key, (label, unit) in LABELS.items():
        g = [G[e][key] if G[e] is not None else None for e in eras]
        out.append({"key": key, "label": label, "unit": unit,
                    "game": [r(np.mean(x)) if x is not None else None for x in g],
                    "tuner": [r(np.mean(T[e][key])) for e in eras],
                    "game_n": [int(len(x)) if x is not None else None for x in g],
                    # null where the noise is unknown, or the value is 0 and 0 noise would mean nothing
                    "game_se": [r(np.std(x, ddof=1) / len(x) ** 0.5) if x is not None and len(x) > 1 and np.mean(x) != 0 else None for x in g]})
    notes += [
        "The game values cover the 40 largest economies in each window's first month. "
        "game_se is the spread across those countries over the square root of their count. Countries in one game share a world, so it understates run-to-run noise.",
        f"The tuner values come from {TUNER_N} economies of the AI preset (engine.defaults(), bot ai, seed {TUNER_SEED}), run from 1836 and cut into the same months.",
        "A panic already running in a window's first month does not count as one of that window's panics, on both sides.",
        "Lending counts as frozen in a month when Bad Debts are at or above the stop line (spec_crunch_lend at 0), read from the logged crunch and lax.",
    ]
    if not log.exists() and not sample.startswith("parallel"):
        notes.insert(3, "The 1866 and 1896 games start from a 1.2.0 release-candidate campaign's saves, while the tuner reaches those years by its own simulated history.")
    rd = lambda d: None if d is None else {k: (rd(v) if isinstance(v, dict) else r(v) if isinstance(v, float) else v) for k, v in d.items()}
    drv = {era_name(e): {"game": rd(D[e]), "tuner": rd(TS[e][1])} for e in eras}
    OUT.write_text(json.dumps({"build": BUILD_NAME, "made": time.strftime("%Y-%m-%d"), "source": source, "eras": [era_name(e) for e in eras],
                               "metrics": out, "notes": notes, "drivers": drv}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{'':32s}" + "".join(f"{era_name(e):>26s}" for e in eras))
    for m in out:
        cells = "".join(f"{'-' if g is None else g:>9} se {'-' if s is None else s:<6} t {t:<7}" for g, s, t in zip(m["game"], m["game_se"], m["tuner"]))
        print(f"{m['label'][:32]:32s}{cells}")
    print(json.dumps(drv, indent=1))
    print(f"wrote {OUT}")


def selftest():
    conf = np.array([[50, 50, 90, 90, 30, 30.0], [50, np.nan, 50, 50, 50, 50]])
    panic = np.array([[True, False, False, False, True, True], [False] * 6])
    z = np.zeros_like(conf)
    m = metrics(conf, panic, z + 2, z, z + 0.5)
    assert m["panics_per_decade"][0] == 120 / 6, m  # the first month's running panic isn't counted, the fifth month's is
    assert m["mania_pct"][0] == 2 / 6 * 100 and m["low_pct"][0] == 3 / 6 * 100, m
    assert m["low_pct"][1] == 0 and m["lev_mean"][1] == 2, m
    assert frozen(np.array([K["LEV_BAD_STOP"]]), np.array([0.5]))[0] and not frozen(np.array([0.0]), np.array([0.5]))[0]
    print("selftest ok")


if __name__ == "__main__":
    {"run": run, "campaign": campaign, "compare": compare, "selftest": selftest}[sys.argv[1] if len(sys.argv) > 1 else "selftest"](*sys.argv[2:])
