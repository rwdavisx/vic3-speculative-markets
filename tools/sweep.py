"""Fast tuning games: many AI-only observer games at once, with no window, no sound and a private user folder each, so
the player's saves, settings and screen are never touched and nothing has to be restored.

The flags come from the game itself: -nographics, -nosounds, -userdir=, -run_until=, -handsoff. Games run at normal
priority: below it they got about 1 CPU thread each beside anything else busy. Each game's PROBE and SPEC lines go to runs/sweep_<name>/<arm>_<n>/.

As a tool: sweep.run(name, {arm: mod folder}, games per arm, until, jobs) returns {arm: [game]}, a game being
{"status", "tags": {tag: {month: gdp}}, "spec": raw lines}. The largest country on a shared tag keeps the reading, so
a civil war's rebels don't split a country (FINDINGS, AI impact).

Usage: py -3 tools/sweep.py --name noise --games 6 --jobs 6 --until 1837.1.1 [--arm label=folder ...]
With no --arm it runs vanilla (the probe mod) alone."""
import argparse
import ctypes
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

import observe
import probe

ROOT = Path(__file__).resolve().parent.parent
WORK = Path("G:/GameDev/_claude_scratch/vic")   # user folders and probe mod: throwaway
SAVES = WORK / "saves"
FROZEN_MINUTES = 15   # a loading game logs nothing, and with the computer busy loading takes over 5 minutes
NORMAL = 0x20
# ponytail: this machine's i7-13700K, whose 8 fast cores are logical processors 0 to 15. Windows left windowless games on
# the slow cores: about 1.5 threads and 43 s a game month there, 4 threads and 8 s here. Another CPU needs its own mask.
FAST_CORES = 0xFFFF
MON = {m: i for i, m in enumerate("January February March April May June July August September October November December".split())}
LINE = re.compile(r"tag=(\S+) date=(\w+) \d+, (\d{4}) gdp=([\d.]+)")


def vanilla():
    return probe.standalone(WORK / "probe_mod")


def start(mod, until, slot, save=None, autosave="yearly"):
    """save: a .v3 file the game starts from instead of the 1836 bookmark"""
    # The game runs from its binaries directory, not the caller's working folder.
    mod = Path(mod).expanduser().resolve()
    if not mod.is_dir():
        raise ValueError(f"Mod folder does not exist: {mod}")
    user = WORK / f"g{time.time_ns()}"   # a fresh folder each game; only its big files are removed afterwards
    user.mkdir(parents=True)
    extra = []
    if save:
        (user / "save games").mkdir()
        shutil.copy(save, user / "save games" / Path(save).name)
        extra = [f"-loadsave={Path(save).stem}"]
    (user / "content_load.json").write_text(json.dumps(
        {"enabledMods": [{"path": str(mod).replace("/", "\\")}], "disabledDLC": [], "enabledUGC": []}))
    prefs = json.loads((observe.DOCS / "pdx_settings.json").read_text(encoding="utf-8"))
    prefs.setdefault("game", {}).update(pause_on_event=False, save_to_cloud=False, autosave=autosave, save_on_exit=autosave != "yearly")
    (user / "pdx_settings.json").write_text(json.dumps(prefs, indent="\t"))
    (user / "logs").mkdir()
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7  # SW_SHOWMINNOACTIVE: never takes focus
    wall = time.time()
    proc = subprocess.Popen([str(observe.GAME / "victoria3.exe"), "-gdpr-compliant", "-handsoff", "-nographics", "-nosounds",
                             "-nofilewatcher", "-disable_renderframeifneeded", "-no_crash_reporter", "-no_notifications",
                             f"-userdir={user}", f"-run_until={until}", *extra],
                            cwd=str(observe.GAME), startupinfo=si, creationflags=NORMAL,
                            env={**os.environ, "SteamAppId": observe.STEAM_APP_ID, "SteamGameId": observe.STEAM_APP_ID},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ctypes.windll.kernel32.SetProcessAffinityMask(int(proc._handle), FAST_CORES)
    return {"proc": proc, "user": user, "wall": wall, "slot": slot, "seen": [], "last": time.time(), "date": None, "keep": set(), "name": "",
            "mirror": observe.Mirror(user / "logs" / "debug.log", user / "mirror.log", wall - 5),
            "error_mirror": observe.Mirror(user / "logs" / "error.log", user / "error_mirror.log", wall - 5)}


def make_seed(mod, name):
    """A save from the first month: a seed that vanilla and modded games can both load, so a pair starts from the same
    world and the same random state. The game's own Custom RNG Seed rule needs the setup screen, which these games skip."""
    job = start(mod, "1836.2.2", 0, autosave="monthly")
    job["proc"].wait(timeout=900)
    newest = max((job["user"] / "save games").glob("*.v3"), key=lambda f: f.stat().st_mtime)
    SAVES.mkdir(exist_ok=True)
    shutil.copy(newest, SAVES / f"{name}.v3")
    newest.unlink()


def poll(job):
    keep_saves(job)
    if "error_mirror" in job:
        job["error_mirror"].poll()
    text = job["mirror"].poll()
    if text:
        # The game may still be writing the last line. Carry it into the next poll;
        # otherwise half a SPEC/PROBE row (or test assertion) is silently lost.
        text = job.pop("pending", "") + text
        text, _, job["pending"] = text.rpartition("\n")
        job["seen"].extend(l for l in text.splitlines() if "SPEC" in l or "PROBE" in l or "HOTFIX " in l)
        dates = re.findall(r"PROBE tag=\w+ date=(.+?) \w+=", text)
        if dates and dates[-1] != job["date"]:
            job["date"], job["last"] = dates[-1], time.time()


def keep_saves(job):
    """Copies a game's yearly autosave out for each year in job["keep"], as a shared start for short tests."""
    year = int(job["date"][-4:]) if job["date"] else 0
    if year not in job["keep"]:
        return
    job["keep"].discard(year)
    saves = sorted((job["user"] / "save games").glob("*.v3"), key=lambda f: f.stat().st_mtime)
    if saves:
        SAVES.mkdir(exist_ok=True)
        shutil.copy(saves[-1], SAVES / f"{job['name']}_{year}.v3")


def tags(lines):
    out = {}
    for l in lines:
        i = l.find("PROBE tag=")
        m = LINE.search(l, i) if i >= 0 else None
        if m and m.group(2) in MON:
            k, g = int(m.group(3)) * 12 + MON[m.group(2)], float(m.group(4))
            c = out.setdefault(m.group(1), {})
            c[k] = max(c.get(k, 0), g)
    return out


def finish(job, status, folder):
    poll(job)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "probe.log").write_text("\n".join(l for l in job["seen"] if "PROBE tag=" in l), encoding="utf-8")
    spec = [l for l in job["seen"] if "SPEC tag=" in l]
    if spec:
        (folder / "telemetry.log").write_text("\n".join(spec), encoding="utf-8")
    assertions = [l for l in job["seen"] if "HOTFIX " in l]
    if assertions:
        (folder / "assertions.log").write_text("\n".join(assertions) + "\n", encoding="utf-8")
    cumulative = job["user"] / "error_mirror.log"
    err = cumulative if cumulative.exists() else job["user"] / "logs" / "error.log"
    ours = 0
    if err.exists():
        shutil.copyfile(err, folder / "error.log")
        ours = sum(1 for l in err.read_text(encoding="utf-8", errors="replace").splitlines() if "spec_" in l.lower())
    game = {"status": status, "date": job["date"], "minutes": round((time.time() - job["wall"]) / 60, 2), "our_errors": ours,
            "build": job.get("build"), "save": job.get("save"), "tags": tags(job["seen"]), "spec": spec,
            "error_log_cumulative": cumulative.exists()}
    (folder / "meta.json").write_text(json.dumps({k: game[k] for k in ("status", "date", "minutes", "our_errors", "build", "save", "error_log_cumulative")}), encoding="utf-8")
    for f in [job["user"] / "mirror.log", *(job["user"] / "save games").glob("*.v3")]:
        f.unlink(missing_ok=True)
    return game


def run(name, arms, games, until, jobs, timeout=60, log=print, keep=(), save=None):
    """Each arm's games interleaved, so a slow computer treats the arms alike. status.json tells the tuner what this
    run is doing; a file named stop in the session folder ends the run, one in a game's user folder ends that game."""
    todo = [(arm, n) for n in range(games) for arm in arms]
    session = ROOT / "runs" / f"sweep_{name}"
    session.mkdir(parents=True, exist_ok=True)
    (session / "stop").unlink(missing_ok=True)
    start_of = lambda arm: arms[arm] if isinstance(arms[arm], tuple) else (arms[arm], save)   # (folder, save): an arm with its own start
    status_file = {"name": name, "pid": os.getpid(), "started": time.time(), "jobs": jobs,
                   "games": {f"{a}_{n + 1:02}": {"state": "waiting", "build": Path(start_of(a)[0]).name,
                                                 "save": Path(start_of(a)[1]).stem if start_of(a)[1] else None} for a, n in todo}}
    write_status(session, status_file)
    out, live, free = {a: [] for a in arms}, {}, list(range(jobs))
    while todo or live:
        stopping = (session / "stop").exists()
        if stopping:
            todo.clear()
        while todo and free:
            arm, n = todo.pop(0)
            slot = free.pop()
            mod, from_save = start_of(arm)
            live[slot] = (arm, n, start(mod, until_of(until, from_save), slot, from_save))
            live[slot][2].update(keep=set(keep) if arm != "vanilla" else set(), name=f"{name}_{arm}_{n + 1}",
                                 build=Path(mod).name, save=Path(from_save).stem if from_save else None)
            status_file["games"][f"{arm}_{n + 1:02}"].update(state="running", user=str(live[slot][2]["user"]))
            write_status(session, status_file)
            time.sleep(4)   # the load is disk heavy: stagger it
        for slot, (arm, n, job) in list(live.items()):
            poll(job)
            code = job["proc"].poll()
            status = None
            if code is not None:
                status = "done" if code == 0 else "crashed"
            elif stopping or (job["user"] / "stop").exists():
                status = "stopped"
            elif time.time() - job["wall"] > timeout * 60:
                status = "timeout"
            elif time.time() - job["last"] > FROZEN_MINUTES * 60:
                status = "frozen"
            if status:
                if code is None:
                    job["proc"].kill()
                    job["proc"].wait()
                game = finish(job, status, session / f"{arm}_{n + 1:02}")
                out[arm].append(game)
                log(f"{arm} {n + 1}: {status} at {game['date']} in {game['minutes']} min, spec-related log lines {game['our_errors']}")
                status_file["games"][f"{arm}_{n + 1:02}"].update(state=status, date=game["date"])
                write_status(session, status_file)
                del live[slot]
                free.append(slot)
        time.sleep(1)
    return out


def write_status(session, status):
    tmp = session / "status.tmp"
    tmp.write_text(json.dumps(status), encoding="utf-8")
    os.replace(tmp, session / "status.json")   # the tuner never reads half a file


def until_of(until, save):
    """until may be a number of years from the save's year, the digits before .v3; other saves start in 1836"""
    if isinstance(until, int):
        year = re.search(r"(\d{4})\.v3$", str(save))
        return f"{(int(year.group(1)) if year else 1836) + until}.1.1"
    return until


def latest(game):
    """Each living country's GDP over the last 6 months, averaged. Countries log every 30 days, so a calendar month can
    miss one and a single month's total is out by whole countries; GDP also jitters month to month."""
    end = max((max(c) for c in game["tags"].values() if c), default=0)
    out = {}
    for t, c in game["tags"].items():
        if c and max(c) >= end - 2:
            xs = [g for m, g in c.items() if m > end - 6]
            out[t] = sum(xs) / len(xs)
    return out


def world(game):
    return sum(latest(game).values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", help='a json file from the tuner: {"name", "until", "jobs", "timeout", "games": {label: [folder, save]}}')
    ap.add_argument("--name")
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--until")
    ap.add_argument("--arm", action="append", default=[], help="label=mod folder; vanilla if none")
    ap.add_argument("--keep", default="", help="years whose autosave to keep from the mod arms, e.g. 1850,1870")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--save", help="a .v3 to start from")
    a = ap.parse_args()
    if a.plan:
        p = json.loads(Path(a.plan).read_text(encoding="utf-8"))
        arms = {k: (Path(mod), SAVES / f"{s}.v3" if s else None) for k, (mod, s) in p["games"].items()}
        run(p["name"], arms, 1, p["until"], p["jobs"], p["timeout"], lambda s: print(s, flush=True))
        return
    arms = dict(x.split("=", 1) for x in a.arm) or {"vanilla": vanilla()}
    t = time.time()
    res = run(a.name, arms, a.games, a.until, a.jobs, a.timeout, lambda s: print(s, flush=True),
              [int(y) for y in a.keep.split(",") if y], a.save)
    print(f"wall {round((time.time() - t) / 60, 1)} min")
    for arm, gs in res.items():
        w = [world(g) / 1e6 for g in gs if g["tags"]]
        if not w:
            print(arm, "no GDP telemetry captured; inspect status and error logs")
            continue
        print(arm, "world GDP M at the end:", [round(x, 2) for x in w],
              "mean", round(statistics.mean(w), 2), "sd", round(statistics.pstdev(w), 2) if len(w) > 1 else "")


if __name__ == "__main__":
    main()
