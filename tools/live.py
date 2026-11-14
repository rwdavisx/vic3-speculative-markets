"""What is running now, for the tuner: every Victoria 3 game, how far it has got and how it compares so far.

Everything here only reads, except stop() and start_test(). Games are found by their process, so a game shows up
whoever started it; test games also have a status.json from sweep.py that names them. Only games under sweep.WORK can
be stopped: a game elsewhere belongs to the player or another session.

Usage: py -3 tools/live.py   prints what is running."""
import ctypes
import functools
import json
import math
import os
import re
import shutil
import statistics as st
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import score
import sweep

MAX_GAMES = 1   # more at once slows the whole machine too much
STUCK_MINUTES = sweep.FROZEN_MINUTES
MIN_REFRESH = 4   # seconds; the page asks every 5, and nothing is read while nobody is looking
NO_WINDOW = 0x08000000   # no console flashes over whatever the player is doing
DETACHED = 0x00000008 | 0x00000200   # a test keeps running when the tuner closes
RUNS = score.RUNS
CHECKLIST = RUNS / "checklist.json"
TOOLS = Path(__file__).resolve().parent
LINE = re.compile(r"(PROBE|SPEC) tag=(\S+) date=(\w+) \d+, (\d{4}) (.*)")
JOBS = re.compile(r"sweep|autotune|generate\.py|check\.py|i18n\.py|lev\d|seed_", re.I)   # scripts worth showing
SCAN = ("Get-CimInstance Win32_Process -Filter \"Name='victoria3.exe' or Name='python.exe' or Name='codex.exe'\" | "
        "Select-Object ProcessId,Name,CommandLine,WorkingSetSize,KernelModeTime,UserModeTime,"
        "@{n='Start';e={$_.CreationDate.ToString('o')}} | ConvertTo-Json -Compress")


def processes():
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", SCAN], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, timeout=60).stdout
    rows = json.loads(out or "[]")
    return [rows] if isinstance(rows, dict) else rows


def arg(cmd, name):
    m = re.search(rf"-{name}=(.+?)(?= -\w|$)", cmd or "")
    return m.group(1).strip().strip('"') if m else None


@functools.lru_cache(maxsize=1)
def country_names():
    """Tag to English name, from the game's own file."""
    text = (sweep.observe.GAME.parent / "game/localization/english/countries_l_english.yml").read_text(encoding="utf-8-sig")
    return dict(re.findall(r'^ ([A-Z0-9]{3}):\d* "(.+?)"', text, re.M))


class Tail:
    """The lines added to a file since last asked."""

    def __init__(self, path):
        self.path, self.pos, self.rest = path, 0, b""

    def lines(self):
        try:
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                data = f.read()
                self.pos = f.tell()
        except OSError:
            return []
        parts = (self.rest + data).split(b"\n")
        self.rest = parts.pop()
        return parts


class Game:
    """One running game, followed through mirror.log: sweep.py's copy of the game's log."""

    def __init__(self, user):
        self.log, self.err = Tail(user / "mirror.log"), Tail(user / "logs" / "error.log")
        self.tags, self.state, self.watch, self.events = {}, {}, {}, []
        self.first = self.month = self.date = None
        self.errors, self.moved, self.pace, self.cpu = 0, time.time(), deque(maxlen=300), None

    def update(self):
        for raw in self.log.lines():
            if b" tag=" in raw and (m := LINE.search(raw.decode("utf-8", "replace"))) and m.group(3) in score.MON:
                self.read(m.group(1), m.group(2).split("#")[0], int(m.group(4)) * 12 + score.MON[m.group(3)], m.group(5))
        self.errors += sum(b"spec_" in l.lower() for l in self.err.lines())
        if self.month:
            self.pace.append((time.time(), self.month))

    def read(self, kind, tag, k, rest):
        if self.month is None or k > self.month:
            self.month, self.moved = k, time.time()
            self.date = f"{list(score.MON)[k % 12]} {k // 12}"
            self.first = self.first or k
        if kind == "PROBE":
            g = re.match(r"gdp=([\d.]+)", rest)
            if g:
                c = self.tags.setdefault(tag, {})
                c[k] = max(c.get(k, 0), float(g.group(1)))
            return
        now = {a: float(b) for a, b in score.FIELD.findall(rest)}
        started, crash = self.watch.setdefault(tag, score.Watch()).see(k, now)
        if started:
            self.events.append({"month": k, "date": self.date, "tag": tag, "kind": "panic", "size": 0})
        if crash:
            self.events.append({"month": k, "date": self.date, "tag": tag, "kind": "bad debts", "size": round(crash, 1)})
        if now.get("crunch", 0) >= self.state.get(tag, {}).get("crunch", 0) or k > self.state.get(tag, {}).get("month", 0) + 1:
            self.state[tag] = {**now, "month": k}   # two countries can share a tag: the one in trouble shows

    def months_per_hour(self, started):
        """From the last 20 minutes when there is that much to go on, else the whole game so far: games slow as they age."""
        now = time.time()
        old = next(((t, m) for t, m in self.pace if now - t < 1200), None)
        if old and now - old[0] > 90 and self.month > old[1]:
            return 3600 * (self.month - old[1]) / (now - old[0])
        return 3600 * (self.month - self.first) / max(now - started, 60) if self.first else None

    def top(self):
        last = {t: c[max(c)] for t, c in self.tags.items() if c}
        return set(sorted(last, key=lambda t: -last[t])[:score.TOP])

    def leaders(self, n=10):
        """The largest countries at the current date. Each reports monthly, so one silent for longer has gone."""
        now = {t: c[max(c)] for t, c in self.tags.items() if c and max(c) >= self.month - 2}
        names = country_names()
        return [{"tag": t, "name": names.get(t, t), "gdp": round(now[t]), "lev": self.state.get(t, {}).get("lev"), "conf": self.state.get(t, {}).get("conf"),
                 "crunch": self.state.get(t, {}).get("crunch"), "panic": self.state.get(t, {}).get("panic", 0) > 0}
                for t in sorted(now, key=now.get, reverse=True)[:n]]

    def against_baseline(self, save):
        """World GDP now against baseline games at the same date: noisy, but it shows a game going wrong early."""
        paths = score.baseline(save)[0] if save else []
        offs = [o for o in map(score.gdp, paths) if o]
        k = (self.month or 0) - 6
        if not offs or not self.tags:
            return None
        w, ws = score.world_at(self.tags, k), [score.world_at(o, k) for o in offs]
        return round(score.against(w, ws), 1) if w and all(ws) else None


_games, _lock, _last = {}, threading.Lock(), (0, None)
_cpu = None   # the last reading of GetSystemTimes


def machine():
    global _cpu

    class Mem(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in "abcdefg"]

    k = ctypes.windll.kernel32
    m = Mem(size=ctypes.sizeof(Mem))
    k.GlobalMemoryStatusEx(ctypes.byref(m))
    idle, kern, user = (ctypes.c_ulonglong() for _ in range(3))
    k.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))   # kernel time counts idle
    now = (idle.value, kern.value + user.value)
    cpu = None
    if _cpu and now[1] > _cpu[1]:
        cpu = round(100 * (1 - (now[0] - _cpu[0]) / (now[1] - _cpu[1])))
    _cpu = now
    return {"cpu": cpu, "memory": m.load, "memory_gb": round(m.a / 2**30), "disk_free_gb": round(shutil.disk_usage(sweep.WORK).free / 2**30),
            "cores": os.cpu_count(), "max_games": MAX_GAMES}


def build_of(user):
    try:
        mods = json.loads((user / "content_load.json").read_text(encoding="utf-8"))["enabledMods"]
        return Path(mods[0]["path"]).name
    except (OSError, ValueError, KeyError, IndexError):
        return None


def active_tests(pids):
    """The status.json of each test whose runner is alive."""
    out = {}
    for f in RUNS.glob("sweep_*/status.json"):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if s.get("pid") in pids:
            out[s["name"]] = s
    return out


def view(p, tests):
    """One row of the page for a game process."""
    cmd = p.get("CommandLine") or ""
    folder = arg(cmd, "userdir")
    user = Path(folder) if folder else None
    ours = bool(user) and user.parent == sweep.WORK
    started = datetime.fromisoformat(p["Start"][:26]).timestamp()
    row = {"pid": p["ProcessId"], "ours": ours, "memory_gb": round(p["WorkingSetSize"] / 2**30, 1), "running_minutes": round((time.time() - started) / 60),
           "save": arg(cmd, "loadsave"), "until": arg(cmd, "run_until"), "build": build_of(user) if user else None, "test": None, "label": None, "cpu": None}
    if not ours:
        row["owner"] = "another session" if user else "the player"
        return row
    for name, s in tests.items():
        for label, g in s["games"].items():
            if g.get("user") == folder:
                row.update(test=name, label=label)
    g = _games.setdefault(row["pid"], Game(user))
    g.update()
    used = (p["KernelModeTime"] + p["UserModeTime"]) / 1e7
    if g.cpu:
        row["cpu"] = round(100 * (used - g.cpu[0]) / max(time.time() - g.cpu[1], 1) / os.cpu_count(), 1)
    g.cpu = (used, time.time())
    end = None
    if m := re.match(r"(\d+)\.(\d+)", row["until"] or ""):
        end = int(m.group(1)) * 12 + int(m.group(2)) - 1
    top, stuck = g.top(), (time.time() - g.moved) / 60
    hits = [e for e in g.events if e["tag"] in top]
    pace = g.months_per_hour(started) if g.month else None
    state = "loading" if not g.month else "stuck" if stuck > STUCK_MINUTES else "running"
    row.update(leaders=g.leaders() if g.month else [], state=state, date=g.date, errors=g.errors, stuck_minutes=round(stuck, 1), world=g.against_baseline(row["save"]) if row["build"] != "probe_mod" else None,
               percent=round(100 * (g.month - g.first) / (end - g.first), 1) if g.month and end and end > g.first else 0,
               hours_left=round((end - g.month) / pace, 2) if pace and end and g.month else None, years_per_hour=round(pace / 12, 1) if pace else None,
               panics=sum(e["kind"] == "panic" for e in hits), crashes=sum(e["kind"] == "bad debts" and e["size"] >= score.MEDIUM for e in hits),
               severe=sum(e["kind"] == "bad debts" and e["size"] >= score.SEVERE for e in hits),
               hot=sum(s.get("lev", 0) >= 3 for t, s in g.state.items() if t in top),
               in_bad_debts=sum(s.get("crunch", 0) >= 1 for t, s in g.state.items() if t in top),
               events=[e for e in hits if e["kind"] == "bad debts" and e["size"] >= score.MEDIUM or e["kind"] == "panic"][-40:])
    return row


def snapshot():
    """All the Now page shows, at most once every few seconds however many pages ask."""
    global _last
    with _lock:
        if time.time() - _last[0] < MIN_REFRESH:
            return _last[1]
        ps = processes()
        pids = {p["ProcessId"] for p in ps}
        tests = active_tests(pids)
        rows = [view(p, tests) for p in ps if p["Name"] == "victoria3.exe"]
        for pid in set(_games) - pids:
            del _games[pid]   # finished: the test's folder under runs/ has it now
        others = [{"pid": p["ProcessId"], "name": p["Name"], "what": short(p["CommandLine"])} for p in ps
                  if p["Name"] != "victoria3.exe" and JOBS.search(p.get("CommandLine") or "") and p["ProcessId"] != os.getpid()]
        others = [o for o in others if not any(o["pid"] == t["pid"] for t in tests.values())]
        ended = sorted((g for g in score.games() if time.time() - g["when"] < 86400), key=lambda g: -g["when"])[:12]
        ours = [r for r in rows if r["ours"]]
        data = {"machine": machine(), "games": rows, "others": others, "ended": ended, "checklist": checklist(), "at": time.time(),
                "test_games": len(ours),
                "tests": [{"name": n, "pid": t["pid"], "waiting": sum(g["state"] == "waiting" for g in t["games"].values()),
                           "finished": sum(g["state"] not in ("waiting", "running") for g in t["games"].values()), "total": len(t["games"])}
                          for n, t in tests.items()]}
        _last = (time.time(), data)
        return data


def short(cmd):
    return re.sub(r'^"?[^"]*python\w*(\.exe)?"?\s*', "", cmd or "")[:120]


def checklist():
    try:
        return json.loads(CHECKLIST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def running_builds():
    """Build folders in use, and how many games of any kind are running: nothing may rebuild under a game."""
    rows = [p for p in processes() if p["Name"] == "victoria3.exe"]
    users = [arg(p.get("CommandLine"), "userdir") for p in rows]
    return {build_of(Path(u)) for u in users if u}, len(rows)


def stop_game(pid):
    """A game of ours ends through its test, so what it logged is kept; one with no test to save it is simply closed."""
    p = next((p for p in processes() if p["ProcessId"] == pid and p["Name"] == "victoria3.exe"), None)
    folder = arg(p.get("CommandLine"), "userdir") if p else None
    if not folder or Path(folder).parent != sweep.WORK:
        raise ValueError("not one of our test games")
    labelled = any(g.get("user") == folder for t in active_tests({x["ProcessId"] for x in processes()}).values() for g in t["games"].values())
    (Path(folder) / "stop").touch()
    if not labelled:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, creationflags=NO_WINDOW)


def stop_test(name):
    if name not in active_tests({p["ProcessId"] for p in processes()}):
        raise ValueError("that test is not running")
    (RUNS / f"sweep_{name}" / "stop").touch()


# -- starting tests ------------------------------------------------------------------------------------------------

KINDS = {"full": {"label": "Full game to 1906", "until": "1906.1.1", "timeout": 300, "hours": 2.1},
         "fork": {"label": "20 years from the save", "until": 20, "timeout": 150, "hours": .7},
         "smoke": {"label": "1 year, quick check", "until": 1, "timeout": 30, "hours": .05}}


def options():
    """What the Start form offers: builds newest first, the saves tests start from."""
    builds = sorted((d for d in sweep.WORK.glob("b_*") if d.is_dir()), key=lambda d: -d.stat().st_mtime)[:15]
    return {"builds": [{"name": "probe_mod", "label": "Vanilla (no mod)"}] + [{"name": d.name, "label": d.name} for d in builds],
            "saves": sorted(f.stem for f in sweep.SAVES.glob("*.v3") if f.stem != "seed_test"),
            "kinds": [{"name": k, **v} for k, v in KINDS.items()], "max_games": MAX_GAMES}


def start_test(body):
    """Starts sweep.py on its own, so the games outlive the tuner. Each build plays each save."""
    name, kind, builds, saves = body.get("name", ""), KINDS.get(body.get("kind")), body.get("builds") or [], body.get("saves") or []
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        raise ValueError("name the test with letters, numbers, - or _")
    folder = RUNS / f"sweep_{name}"
    if folder.exists():
        raise ValueError(f"there is already a test called {name}")
    known = options()
    if not kind or not builds or not saves or not set(builds) <= {b["name"] for b in known["builds"]} or not set(saves) <= set(known["saves"]):
        raise ValueError("pick a kind of test, at least one build and at least one save")
    running = sum(1 for p in processes() if p["Name"] == "victoria3.exe")
    jobs = min(int(body.get("jobs") or 1), len(builds) * len(saves))
    if jobs < 1 or running + jobs > MAX_GAMES:
        raise ValueError(f"{running} games are running and the limit is {MAX_GAMES}: lower the games at once")
    games = {f"{b}__{s}": [str(sweep.WORK / b), s] for s in saves for b in builds}
    folder.mkdir(parents=True)
    plan = folder / "plan.json"
    plan.write_text(json.dumps({"name": name, "until": kind["until"], "jobs": jobs, "timeout": kind["timeout"], "games": games}), encoding="utf-8")
    with open(folder / "sweep.log", "ab") as log:
        subprocess.Popen([sys.executable, str(TOOLS / "sweep.py"), "--plan", str(plan)], cwd=TOOLS, stdout=log, stderr=log,
                         stdin=subprocess.DEVNULL, creationflags=DETACHED | NO_WINDOW)
    return {"name": name, "games": len(games), "jobs": jobs}


def selftest():
    cmd = r'"G:\x\victoria3.exe" -handsoff -userdir=G:\a b\g1 -run_until=1870.1.1 -loadsave=base115_mod_1_1850'
    assert arg(cmd, "userdir") == r"G:\a b\g1" and arg(cmd, "run_until") == "1870.1.1" and arg(cmd, "loadsave") == "base115_mod_1_1850", cmd
    g = Game(Path("nowhere"))
    g.read("SPEC", "AAA", 22000, "conf=50 panic=0 lev=4 crunch=0")
    g.read("SPEC", "AAA", 22001, "conf=10 panic=1 lev=4 crunch=20")
    g.read("PROBE", "AAA", 22001, "gdp=100.5 sol=1")
    assert [e["kind"] for e in g.events] == ["panic", "bad debts"] and g.events[1]["size"] == 20 and g.tags["AAA"][22001] == 100.5
    assert g.date == "June 1833" and g.top() == {"AAA"}
    g.read("PROBE", "BBB", 21990, "gdp=900 sol=1")   # gone for years: must not rank
    g.read("PROBE", "USA", 22001, "gdp=200 sol=1")
    assert [(c["tag"], c["name"]) for c in g.leaders()] == [("USA", "America"), ("AAA", "AAA")] and g.leaders()[1]["panic"]
    print("live ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        for r in snapshot()["games"]:
            print({k: v for k, v in r.items() if k != "events"})
