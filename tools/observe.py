"""Unattended test runs, after the testbed in yurcick1992/victoria3-pm-tech-rehaul (MODDING_NOTES, "Automated headless
runs"): the game starts an AI-only observer game at the 1836 bookmark (-handsoff), plays to a date and quits by itself
(-run_until), so nothing is clicked and the player's screen is not needed.

For each run it switches on only our mod (content_load.json, restored afterwards), copies debug.log as it is written
(the game keeps about 3 MB before overwriting, so a long run loses its start otherwise), checks the build's start
marker (generate.py's SPEC_MARKETS init line, in --log builds), keeps this run's own errors, and summarises the
monthly SPEC lines.

Both builds log probe.py's PROBE line (GDP, living standards, debt, investment, war, default), so --vanilla runs only
that logging-only mod as a control to set beside ours.

Usage: py -3 tools/observe.py --until 1837.1.1 [--runs 3] [--label name] [--vanilla] [--keep-mods] [--timeout 60]
Build the mod with `generate.py --log` first. Results go to runs/<stamp>_<label>/runNN/.
py -3 tools/observe.py --compare <session> <session>... sets sessions' runs side by side (mean, then range), at the
end and every ten years. A file named STOP in runs/ ends a batch cleanly: the game is closed and everything restored."""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import probe

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "mod"
GAME = Path("G:/SteamLibrary/steamapps/common/Victoria 3/binaries")
STEAM_APP_ID = "529340"  # without this the game cannot reach Steam, so every DLC feature reads as not owned
DOCS = Path.home() / "OneDrive/Documents/Paradox Interactive/Victoria 3"
LOGS = DOCS / "logs"
MARKER = "SPEC_MARKETS init OK"
ARGS = ["-gdpr-compliant", "-handsoff", "-disable_renderframeifneeded"]
FROZEN_MINUTES = 5   # no new in-game month for this long: the run is stuck
DATA = ROOT / "data"  # tuner.py lists the runs it finds here
PROBE_MOD = ROOT / "build_probe"
STOP = ROOT / "runs" / "STOP"
# an observer game autosaves like any other, over the player's autosaves and Continue entry: they wait here meanwhile
SAVES = DOCS / "save games"
HOLD = DOCS / "observe_hold"


def running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq victoria3.exe"], capture_output=True, text=True).stdout
    return "victoria3.exe" in out


class Mirror:
    """Copies a log the game rotates (renamed away, a new file started) as it grows."""

    def __init__(self, src, dst, since):
        # what the file holds already is the previous game's (a game started right after another finds it seconds
        # old): skip it, and start over when the game rotates the file
        self.src, self.dst, self.since = src, dst, since
        self.pos = src.stat().st_size if src.exists() else None
        self.identity = (src.stat().st_dev, src.stat().st_ino) if src.exists() else None

    def poll(self):
        try:
            st = self.src.stat()
        except OSError:  # missing, or held for a moment while the game rotates it: try again next poll
            return ""
        if self.pos is None:
            if st.st_mtime < self.since:  # the previous session's file, before the game rotates it
                return ""
            self.pos = 0
        identity = (st.st_dev, st.st_ino)
        tail = b""
        if self.identity is not None and identity != self.identity:
            # Drain the old file after its rename. Comparing sizes alone loses
            # the unread tail, or misses rotation when the new file is larger.
            rotated = []
            for path in self.src.parent.glob(f"{self.src.stem}.*{self.src.suffix}"):
                number = path.name[len(self.src.stem) + 1:-len(self.src.suffix)]
                if number.isdigit():
                    rotated.append((int(number), path))
            for number, path in sorted(rotated, reverse=True):
                try:
                    old = path.stat()
                    if (old.st_dev, old.st_ino) == self.identity:
                        tail = path.read_bytes()[self.pos:]
                        for newer, newer_path in sorted(rotated, reverse=True):
                            if newer < number:
                                tail += newer_path.read_bytes()
                        break
                except OSError:
                    continue
            self.pos = 0
        self.identity = identity
        if st.st_size < self.pos:  # rotated: the new file starts over
            self.pos = 0
        if st.st_size == self.pos and not tail:
            return ""
        try:
            with open(self.src, "rb") as f:
                f.seek(self.pos)
                data = f.read()
        except OSError:
            return ""
        self.pos += len(data)
        text = (tail + data).decode("utf-8", "replace")
        with open(self.dst, "a", encoding="utf-8") as out:
            out.write(text)
        return text


def seconds(stamp):
    h, m, s = map(int, stamp.split(":"))
    return h * 3600 + m * 60 + s


def own_errors(path, start, end):
    """error.log lines stamped from start to end (seconds of day, wrap safe), unstamped lines inheriting the stamp
    above; counted by shape, since the game repeats a line thousands of times."""
    shapes, keep = {}, False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\[(\d\d:\d\d:\d\d)\]", line)
        if m:
            t = seconds(m.group(1))
            keep = start <= t <= end if start <= end else (t >= start or t <= end)
            line = line[m.end():]
        if keep:
            shape = re.sub(r"\d+", "#", line.strip())[:200]
            shapes[shape] = shapes.get(shape, 0) + 1
    return shapes


def parse(lines, kind="SPEC"):
    """The SPEC (or PROBE) lines as {tag: [{field: value}]}, months in order."""
    rows, key = {}, f"{kind} tag="
    for line in lines:
        if key not in line:
            continue
        kv = dict(re.findall(r"(\w+)=([^\s]+)", line[line.index(key):]))
        when = re.search(r"date=(.+?) \w+=", line)  # the date has spaces, so the field regex keeps its month only
        if when:
            kv["when"] = when.group(1)
            kv["year"] = when.group(1)[-4:]
        rows.setdefault(kv.get("tag"), []).append(kv)
    return {k: v for t, r in rows.items() for k, v in streams(t, r).items()}


def streams(tag, records):
    """A tag's records split into one list per country: a civil war's revolutionaries share their parent's tag, and
    each logs once a month on its own day, so a record joins the list last logged 20 to 45 days before (nearest to
    a month), else starts a list of its own (TAG, TAG#2, ...); records without a readable date stay with the first."""
    out, last = [[]], [None]
    for kv in records:
        try:
            d = datetime.strptime(kv.get("when", ""), "%B %d, %Y")
        except ValueError:
            out[0].append(kv)
            continue
        gaps = [(abs((d - x).days - 30), i) for i, x in enumerate(last) if x and 20 <= (d - x).days <= 45]
        if gaps:
            i = min(gaps)[1]
        elif last[0] is None:
            i = 0
        elif any(x and (d - x).days < 20 for x in last):  # another country logged under this tag days ago
            i = len(out)
            out.append([]), last.append(None)
        else:
            i = max((x, i) for i, x in enumerate(last) if x)[1]  # after a gap in the log: the latest list
        out[i].append(kv)
        last[i] = d
    return {tag if i == 0 else f"{tag}#{i + 1}": r for i, r in enumerate(out) if r}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarise(rows):
    """World-level readings: confidence's spread at the end, months in panic, collapse months."""
    ends = [num(r[-1].get("conf")) for r in rows.values() if r and num(r[-1].get("conf")) is not None]
    panic_months = sum(1 for r in rows.values() for m in r if num(m.get("panic")) == 1)
    crash_months = sum(1 for r in rows.values() for m in r if (num(m.get("crash")) or 0) < 0)
    bands = {name: sum(1 for c in ends if lo <= c < hi) for name, lo, hi in
             (("panic", 0, 20), ("wary", 20, 40), ("steady", 40, 60), ("buoyant", 60, 80), ("mania", 80, 101))}
    gbr = [num(m.get("conf")) for m in rows.get("GBR", [])]
    return {"countries": len(rows), "months_logged": max((len(r) for r in rows.values()), default=0),
            "conf_median_end": statistics.median(ends) if ends else None, "bands_at_end": bands,
            "panic_country_months": panic_months, "collapse_country_months": crash_months,
            "gbr_conf": [c for c in gbr if c is not None][-12:]}


def summarise_probe(rows):
    """World-level readings vanilla has too: GDP growth from the first month to the last, living standards, debt,
    wars and defaults at the end."""
    # countries still there at the end: a country annexed decades ago keeps its last reading otherwise
    last = max((num(r[-1].get("year")) or 0 for r in rows.values() if r), default=0)
    live = {t: (r[0], r[-1]) for t, r in rows.items()
            if r and (num(r[-1].get("gdp")) or 0) > 0 and (num(r[-1].get("year")) or last) >= last - 1}
    growth = [num(b["gdp"]) / num(a["gdp"]) - 1 for a, b in live.values() if (num(a.get("gdp")) or 0) > 0]
    end = [b for a, b in live.values()]
    total = lambda f: sum(num(b.get(f)) or 0 for b in end)
    return {"probe_countries": len(live), "gdp_world_end": round(total("gdp")),
            "gdp_growth_median": round(statistics.median(growth), 4) if growth else None,
            "sol_median_end": statistics.median([num(b.get("sol")) or 0 for b in end]) if end else None,
            "debt_world_end": round(total("debt")), "in_debt_end": sum(1 for b in end if (num(b.get("debt")) or 0) > 0),
            "at_war_end": int(total("war")), "in_default_end": int(total("default")),
            "default_country_months": sum(1 for r in rows.values() for m in r if num(m.get("default")) == 1)}


def yearly(rows):
    """Each country's last reading of each year, then world-level readings per year, with each country's GDP growth
    over the ten years before."""
    by = {}
    for tag, r in rows.items():
        for m in r:
            if num(m.get("year")) and (num(m.get("gdp")) or 0) > 0:
                by.setdefault(int(m["year"]), {})[tag] = m
    out = {}
    for y, cs in sorted(by.items()):
        prev = by.get(y - 10, {})
        growth = {t: num(m["gdp"]) / num(prev[t]["gdp"]) - 1 for t, m in cs.items() if t in prev}
        # the same growth by size ten years before, in thirds of the countries then: small, medium and large economies
        order = sorted((t for t in growth), key=lambda t: num(prev[t]["gdp"]))
        third = lambda k: [growth[t] for i, t in enumerate(order) if min(2, 3 * i // len(order)) == k]
        med = lambda xs: round(statistics.median(xs), 4) if xs else None
        f = lambda k: [num(m.get(k)) or 0 for m in cs.values()]
        out[y] = {"countries": len(cs), "gdp_world": round(sum(f("gdp"))), "gdp_median": round(statistics.median(f("gdp"))),
                  "growth_10y_median": med(list(growth.values())), "growth_10y_small": med(third(0)),
                  "growth_10y_medium": med(third(1)), "growth_10y_large": med(third(2)),
                  "sol_median": round(statistics.median(f("sol")), 3), "debt_world": round(sum(f("debt"))),
                  "in_debt": sum(1 for d in f("debt") if d > 0), "at_war": int(sum(f("war"))),
                  "in_default": int(sum(f("default")))}
    return out, by


def spec_yearly(rows):
    """Confidence readings per year over all country months: its spread, the shares in Mania (80 and up) and in panic,
    and the months a collapse cost confidence."""
    by = {}
    for r in rows.values():
        for m in r:
            if num(m.get("year")) and num(m.get("conf")) is not None:
                by.setdefault(int(m["year"]), []).append(m)
    out = {}
    for y, ms in sorted(by.items()):
        c = sorted(num(m["conf"]) for m in ms)
        q = lambda f: round(c[min(len(c) - 1, int(f * len(c)))], 2)
        out[y] = {"months": len(ms), "conf_median": q(.5), "conf_p10": q(.1), "conf_p90": q(.9),
                  "mania_share": round(sum(x >= 80 for x in c) / len(c), 4),
                  "panic_share": round(sum(num(m.get("panic")) == 1 for m in ms) / len(ms), 4),
                  "crash_months": sum((num(m.get("crash")) or 0) < 0 for m in ms)}
    return out


TOP = 40


def mod_readings(rows, probe):
    """Our mod's own behaviour in one run (SPEC lines), per decade and over the whole run: panics, Mania, boom endings,
    credit, interventions, the Long Depression and each monthly push on confidence; the same by economy size (thirds
    by first GDP reading); and what a panic or a Mania did to a country's GDP over the next year, against the world's
    growth over the same year (PROBE lines, matched by date)."""
    rows = {t: [m for m in r if num(m.get("year")) and num(m.get("conf")) is not None] for t, r in rows.items()}
    rows = {t: r for t, r in rows.items() if r}
    if not rows:
        return {}
    f = lambda m, k: num(m.get(k)) or 0
    pstart, mstart, plen = {}, {}, {}
    for t, r in rows.items():
        pstart[t] = [i > 0 and f(m, "panic") == 1 and f(r[i - 1], "panic") == 0 for i, m in enumerate(r)]
        mstart[t] = [i > 0 and f(m, "conf") >= 80 > f(r[i - 1], "conf") for i, m in enumerate(r)]
        plen[t] = {i: next((k - i for k in range(i, len(r)) if f(r[k], "panic") == 0), len(r) - i)
                   for i in range(len(r)) if pstart[t][i]}
    drivers = sorted({k for r in rows.values() for k in r[0] if k.startswith("d_")})
    month = lambda m: re.sub(r" \d+,", "", m.get("when", ""))
    med = lambda xs: statistics.median(xs) if xs else None
    share = lambda xs: sum(xs) / len(xs) if xs else None

    def agg(sel):
        ms = [rows[t][i] for t, i in sel]
        if not ms:
            return None
        cy = len(ms) / 12
        ps = [(t, i) for t, i in sel if pstart[t][i]]
        ma = [(t, i) for t, i in sel if mstart[t][i]]
        world = {}
        for m in ms:
            world.setdefault(month(m), []).append(f(m, "panic"))
        hits = sorted(f(m, "crash") + f(m, "foreign") + f(m, "turmoil") for m in ms)
        econ = [m for m in ms if f(m, "gdp") > 0]  # the log's gdp= is the rescue cost, 2% of GDP
        out = {"country_months": len(ms),
               "panic_starts_per100": 100 * len(ps) / cy, "panic_share": share([f(m, "panic") == 1 for m in ms]),
               "panic_length": med([plen[t][i] for t, i in ps]),
               "world_panic_peak": max(share(v) for v in world.values() if len(v) >= 20) if any(len(v) >= 20 for v in world.values()) else None,
               "mania_starts_per100": 100 * len(ma) / cy, "mania_share": share([f(m, "conf") >= 80 for m in ms]),
               "mania_to_panic": share([any(pstart[t][i:i + 37]) for t, i in ma]),
               "crash_share": share([f(m, "crash") < 0 for m in ms]), "worst_month": hits[int(0.001 * len(hits))],
               "rescues_per100": 100 * sum(f(m, "rescued") == 1 and (i == 0 or f(rows[t][i - 1], "rescued") == 0)
                                           for (t, i), m in zip(sel, ms)) / cy,
               "tight_share": share([f(m, "stance") == -1 for m in ms]), "loose_share": share([f(m, "stance") == 1 for m in ms]),
               "levers_share": share([f(m, "levers") > 0 for m in ms]), "ld_share": share([f(m, "ld") > 0 for m in ms]),
               "credit_pct_gdp": share([f(m, "pool") / (50 * f(m, "gdp")) for m in econ]),
               "debt_pct_gdp": share([f(m, "debt") / (50 * f(m, "gdp")) for m in econ]),
               "conf_median": med([f(m, "conf") for m in ms]),
               "drivers": {d[2:]: round(statistics.mean(f(m, d) for m in ms), 4) for d in drivers}}
        return {k: round(v, 5) if isinstance(v, float) else v for k, v in out.items()}

    # economies by first GDP reading: thirds, and the TOP largest, the closest match to the historical crisis
    # samples (stats.HISTORY), which cover the 15 to 21 largest economies with a financial system of the time
    first = {t: num(r[0].get("gdp")) for t, r in probe.items() if r and num(r[0].get("gdp"))}
    order = sorted((t for t in first if t in rows), key=first.get)
    size = {t: ("small", "medium", "large")[min(2, 3 * i // len(order))] for i, t in enumerate(order)}
    top = set(order[-TOP:])

    years = sorted({int(m["year"]) for r in rows.values() for m in r})
    decades = {}
    for d in range(years[0] - (years[0] - 1836) % 10, years[-1] + 1, 10):
        sel = [(t, i) for t, r in rows.items() for i, m in enumerate(r) if d <= int(m["year"]) < d + 10]
        a = agg(sel)
        if a:
            # countries whose confidence stayed within 10 points across a decade they were there for most of
            spans = {}
            for t, i in sel:
                spans.setdefault(t, []).append(f(rows[t][i], "conf"))
            long = [c for c in spans.values() if len(c) >= 60]
            a["pinned_share"] = round(share([max(c) - min(c) < 10 for c in long]), 5) if long else None
            a["top"] = agg([(t, i) for t, i in sel if t in top])
            decades[d] = a
    total = agg([(t, i) for t, r in rows.items() for i in range(len(r))])
    total["top"] = agg([(t, i) for t, r in rows.items() if t in top for i in range(len(r))])
    by_size = {k: agg([(t, i) for t, r in rows.items() if size.get(t) == k for i in range(len(r))]) for k in ("small", "medium", "large")}

    # a year of GDP after each panic and Mania start, less the world's median growth over the same year
    at = {t: {m.get("when"): k for k, m in enumerate(r)} for t, r in probe.items()}

    def g12(t, when):
        k = at.get(t, {}).get(when)
        if k is None or k + 12 >= len(probe[t]):
            return None
        a, b = num(probe[t][k].get("gdp")), num(probe[t][k + 12].get("gdp"))
        return b / a - 1 if a and b else None
    world = {}
    for t, r in probe.items():
        for m in r:
            g = g12(t, m.get("when"))
            if g is not None:
                world.setdefault(month(m), []).append(g)
    world = {k: statistics.median(v) for k, v in world.items() if len(v) >= 20}

    def after(starts):
        xs = [g12(t, rows[t][i].get("when")) - world[month(rows[t][i])] for t, i in starts
              if g12(t, rows[t][i].get("when")) is not None and month(rows[t][i]) in world]
        return {"n": len(xs), "median": round(statistics.median(xs), 4) if xs else None}
    every = [(t, i) for t, r in rows.items() for i in range(len(r))]
    total["gdp_after_panic"] = after([(t, i) for t, i in every if pstart[t][i]])
    total["gdp_after_mania"] = after([(t, i) for t, i in every if mstart[t][i]])
    return {"decades": decades, "total": total, "by_size": by_size}


def run_one(folder, until, timeout_min, marker):
    folder.mkdir(parents=True)
    start_wall = time.time()
    start_day = seconds(datetime.now().strftime("%H:%M:%S"))
    mirror = Mirror(LOGS / "debug.log", folder / "debug_mirror.log", start_wall - 5)
    ticks = Mirror(LOGS / "dedicated_server.log", folder / "ticks.log", start_wall - 5)
    # started minimised and without focus: a click or key in the game window pauses an observer game (his L41)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    proc = subprocess.Popen([str(GAME / "victoria3.exe"), *ARGS, f"-run_until={until}"], cwd=str(GAME), startupinfo=si,
                            env={**os.environ, "SteamAppId": STEAM_APP_ID, "SteamGameId": STEAM_APP_ID})
    seen, last_date, last_move, status = [], None, time.time(), "done"
    while True:
        text = mirror.poll()
        if text:
            seen.extend(l for l in text.splitlines() if "SPEC" in l or "PROBE" in l)
            dates = re.findall(r"(?:SPEC|PROBE) tag=\w+ date=(.+?) \w+=", text)
            if dates and dates[-1] != last_date:
                last_date, last_move = dates[-1], time.time()
        if proc.poll() is not None:
            break
        if "Paused: true" in ticks.poll():
            status = "paused"
        elif STOP.exists():
            status = "stopped"
        elif time.time() - start_wall > timeout_min * 60:
            status = "timeout"
        elif time.time() - last_move > FROZEN_MINUTES * 60:
            status = "frozen"
        if status != "done":
            proc.kill()
            break
        time.sleep(1)
    if status == "done" and proc.returncode:  # the game exited on its own before the date: a crash (a report in crashes/)
        status = "crashed"
    seen.extend(l for l in mirror.poll().splitlines() if "SPEC" in l or "PROBE" in l)
    end_day = seconds(datetime.now().strftime("%H:%M:%S"))
    errors = own_errors(LOGS / "error.log", start_day, end_day) if (LOGS / "error.log").exists() else {}
    ours = {k: n for k, n in errors.items() if "spec_" in k.lower() or "speculative" in k.lower()}
    rows = parse(seen)
    telemetry = "\n".join(l for l in seen if "SPEC tag=" in l)
    (folder / "telemetry.log").write_text(telemetry, encoding="utf-8")
    if telemetry:
        (DATA / f"obs_{folder.parent.name}_{folder.name}.txt").write_text(telemetry, encoding="utf-8")
    (folder / "probe.log").write_text("\n".join(l for l in seen if "PROBE tag=" in l), encoding="utf-8")
    by_year, ends = yearly(parse(seen, "PROBE"))
    keys = ("gdp", "sol", "debt", "inv", "war", "default")
    (folder / "probe_yearly.csv").write_text("year,tag," + ",".join(keys) + "\n" + "".join(
        f"{y},{t}," + ",".join(m.get(k, "") for k in keys) + "\n" for y, cs in ends.items() for t, m in cs.items()),
        encoding="utf-8")
    meta = {"status": status, "until": until, "last_date": last_date, "wall_minutes": round((time.time() - start_wall) / 60, 1),
            "marker": next((l.strip() for l in seen if marker in l), None), "error_shapes": len(errors),
            "our_error_shapes": ours, **summarise(rows), **summarise_probe(parse(seen, "PROBE")), "by_year": by_year,
            "spec_by_year": spec_yearly(rows), "mod": mod_readings(rows, parse(seen, "PROBE"))}
    (folder / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    (folder / "errors.json").write_text(json.dumps(dict(sorted(errors.items(), key=lambda kv: -kv[1])), indent=1), encoding="utf-8")
    return meta


COMPARED = ("wall_minutes", "gdp_growth_median", "gdp_world_end", "sol_median_end", "debt_world_end", "in_debt_end",
            "at_war_end", "in_default_end", "default_country_months", "conf_median_end", "panic_country_months")


def compare(sessions):
    """A table of each session's finished runs: the mean of each reading, with its lowest and highest."""
    cols = []
    for s in sessions:  # a+b pools sessions into one column
        paths = [Path(p) if Path(p).is_dir() else ROOT / "runs" / p for p in s.split("+")]
        metas = [json.loads(m.read_text(encoding="utf-8")) for p in paths for m in sorted(p.glob("run*/meta.json"))]
        cols.append((paths[0].name, [m for m in metas if m["status"] == "done"]))
    print(f"{'':24}" + "".join(f"{name[-28:]:>30}" for name, _ in cols))
    print(f"{'runs':24}" + "".join(f"{len(ms):>30}" for _, ms in cols))
    for key in COMPARED:
        cells = []
        for _, ms in cols:
            xs = [m[key] for m in ms if m.get(key) is not None]
            cells.append(f"{statistics.mean(xs):.4g} ({min(xs):.4g} to {max(xs):.4g})" if xs else "none")
        print(f"{key:24}" + "".join(f"{c:>30}" for c in cells))
    # a run ends on 1 January, so its last year holds a country or two: only years with most countries count
    for _, ms in cols:
        for m in ms:
            full = max((c["countries"] for c in m.get("by_year", {}).values()), default=0)
            m["by_year"] = {y: c for y, c in m.get("by_year", {}).items() if c["countries"] >= full / 2}
    years = sorted({int(y) for _, ms in cols for m in ms for y in m.get("by_year", {})})
    marks = [y for y in years if y == years[0] or y % 10 == 5 or y == years[-1]] if years else []
    for key in ("gdp_world", "gdp_median", "growth_10y_median", "sol_median", "debt_world", "in_debt", "at_war", "in_default"):
        print(f"\n{key} by year")
        for y in marks:
            cells = []
            for _, ms in cols:
                xs = [m["by_year"][str(y)][key] for m in ms if str(y) in m.get("by_year", {})
                      and m["by_year"][str(y)].get(key) is not None]
                cells.append(f"{statistics.mean(xs):.4g} ({min(xs):.4g} to {max(xs):.4g})" if xs else "none")
            print(f"{y:<24}" + "".join(f"{c:>30}" for c in cells))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", required=True, help="in-game date to stop at, e.g. 1837.1.1")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--label", default="probe")
    ap.add_argument("--keep-mods", action="store_true", help="leave the other enabled mods on")
    ap.add_argument("--vanilla", action="store_true", help="run with no mods at all, as a control")
    ap.add_argument("--timeout", type=float, default=60, help="minutes a run may take")
    a = ap.parse_args()
    if running():
        sys.exit("victoria3.exe is running: close it first")
    STOP.unlink(missing_ok=True)
    if HOLD.exists() and any(HOLD.iterdir()):
        sys.exit(f"{HOLD} still holds autosaves from an earlier session: put them back in {SAVES} first")
    session = ROOT / "runs" / f"{datetime.now():%Y%m%d_%H%M%S}_{a.label}"
    session.mkdir(parents=True)
    cfg = DOCS / "content_load.json"
    shutil.copy(cfg, session / "content_load.backup.json")
    prefs = DOCS / "pdx_settings.json"
    shutil.copy(prefs, session / "pdx_settings.backup.json")
    cont = DOCS / "continue_game.json"
    if cont.exists():
        shutil.copy(cont, session / "continue_game.backup.json")
    HOLD.mkdir(exist_ok=True)
    for f in SAVES.glob("autosave*.v3"):
        os.replace(f, HOLD / f.name)
    try:
        mods = json.loads(cfg.read_text(encoding="utf-8"))
        ours = {"path": str(MOD).replace("/", "\\")}
        if a.vanilla:
            mods["enabledMods"] = [{"path": str(probe.standalone(PROBE_MOD)).replace("/", "\\")}]
        elif not a.keep_mods:
            mods["enabledMods"] = [ours]
        cfg.write_text(json.dumps(mods), encoding="utf-8")
        # events still pop up for the observed country (Britain), and with pause_on_event on, the first one pauses the
        # game for good (vanilla, 1836.1.25); the game rewrites this file on exit, so the backup is put back after
        settings = json.loads(prefs.read_text(encoding="utf-8"))
        settings.setdefault("game", {})["pause_on_event"] = False
        settings["game"]["save_to_cloud"] = False  # the run's own autosaves stay off the Steam cloud
        prefs.write_text(json.dumps(settings, indent="\t"), encoding="utf-8")
        for n in range(1, a.runs + 1):
            meta = run_one(session / f"run{n:02}", a.until, a.timeout, probe.MARKER if a.vanilla else MARKER)
            print(f"run {n}: {meta['status']} to {meta['last_date']} in {meta['wall_minutes']} min, marker "
                  f"{'ok' if meta['marker'] else 'MISSING'}, our errors {len(meta['our_error_shapes'])}, "
                  f"median confidence {meta['conf_median_end']}, panic months {meta['panic_country_months']}, "
                  f"GDP growth median {meta['gdp_growth_median']}, SoL median {meta['sol_median_end']}, "
                  f"at war {meta['at_war_end']}, in default {meta['in_default_end']}", flush=True)
            if meta["status"] not in ("done", "crashed") or not meta["marker"]:  # after a crash, on to the next game
                print("stopping: the run did not finish cleanly", flush=True)
                break
    finally:
        if running():  # only ever ours: main refuses to start beside a running game
            subprocess.run(["taskkill", "/IM", "victoria3.exe", "/F"], capture_output=True)
            time.sleep(5)
        shutil.copy(session / "content_load.backup.json", cfg)
        shutil.copy(session / "pdx_settings.backup.json", prefs)
        for f in SAVES.glob("autosave*.v3"):
            f.unlink()
        for f in HOLD.iterdir():
            os.replace(f, SAVES / f.name)
        HOLD.rmdir()
        if (session / "continue_game.backup.json").exists():
            shutil.copy(session / "continue_game.backup.json", cont)
    print(f"session: {session}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        r = parse(["x SPEC tag=GBR date=1836.2.1 conf=55 panic=0 crash=0", "SPEC tag=GBR date=1836.3.1 conf=12 panic=1 crash=-3"])
        s = summarise(r)
        assert s["bands_at_end"]["panic"] == 1 and s["panic_country_months"] == 1 and s["collapse_country_months"] == 1
        assert seconds("01:02:03") == 3723
        q = summarise_probe(parse(["PROBE tag=GBR date=x gdp=100 sol=10 debt=0 inv=1 war=1 default=0",
                                   "PROBE tag=GBR date=y gdp=110 sol=11 debt=5 inv=1 war=0 default=1"], "PROBE"))
        rows = parse([f"PROBE tag=GBR date=December 1, {y} gdp={100 + y - 1836} sol=1 debt=0 inv=0 war=0 default=0"
                      for y in range(1836, 1848)], "PROBE")
        by, _ = yearly(rows)
        sp = spec_yearly(parse([f"SPEC tag=GBR date=May 1, 1840 conf={c} panic={int(c < 20)} crash=0" for c in (10, 50, 85, 90)]))
        assert sp[1840]["mania_share"] == 0.5 and sp[1840]["panic_share"] == 0.25 and sp[1840]["conf_median"] == 85, sp
        two = parse([f"SPEC tag=XXX date={w} conf={c}" for w, c in
                     (("May 7, 1853", 25), ("June 6, 1853", 16), ("June 21, 1853", 53), ("July 6, 1853", 8), ("July 21, 1853", 51),
                      ("May 21, 1861", 55), ("May 27, 1861", 16), ("June 20, 1861", 56), ("June 26, 1861", 15))])
        assert [m["conf"] for m in two["XXX"]] == ["25", "16", "8"] and [m["conf"] for m in two["XXX#2"]][:2] == ["53", "51"], two
        assert [m["conf"] for m in two["XXX#3"]] == ["16", "15"], two  # after a gap in the log, a new pair splits again
        lines = []
        for k in range(30):  # one country: a Mania in month 3, a panic from month 6 to 9, GDP flat but for a dip
            when = f"{('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')[k % 12]} 1, {1840 + k // 12}"
            conf = 85 if k in (3, 4) else 10 if 6 <= k < 9 else 50
            lines += [f"SPEC tag=AAA date={when} conf={conf} panic={int(6 <= k < 9)} crash=0 gdp=10 pool=1 debt=0 d_boom=0.5",
                      f"PROBE tag=AAA date={when} gdp={90 if 6 <= k < 18 else 100} sol=1"]
            lines += [f"PROBE tag=B{n:02} date={when} gdp=100 sol=1" for n in range(25)]
        mr = mod_readings(parse(lines), parse(lines, "PROBE"))
        tot = mr["total"]
        assert tot["panic_length"] == 3 and tot["mania_to_panic"] == 1 and tot["drivers"]["boom"] == 0.5, tot
        assert abs(tot["credit_pct_gdp"] - 0.002) < 1e-9 and tot["gdp_after_panic"]["median"] == round(100 / 90 - 1, 4), tot
        assert mr["decades"][1836]["panic_starts_per100"] == 40.0, mr["decades"]  # one start in 30 months
        assert by[1846]["growth_10y_median"] == 0.1 and by[1840]["growth_10y_median"] is None, by[1846]
        assert q["gdp_growth_median"] == 0.1 and q["in_default_end"] == 1 and q["at_war_end"] == 0 and q["in_debt_end"] == 1, q
        import tempfile
        p = Path(tempfile.mkdtemp()) / "e.log"
        p.write_text("[23:59:00][a.cpp:1]: old 5\n[00:00:10][b.cpp:2]: new 7\ncontinued\n[00:05:00][c.cpp:3]: later\n", encoding="utf-8")
        e = own_errors(p, seconds("23:59:30"), seconds("00:01:00"))
        assert list(e) == ["[b.cpp:#]: new #", "continued"], e
        print("observe ok")
    elif sys.argv[1:2] == ["--compare"]:
        compare(sys.argv[2:])
    else:
        main()
