"""Runs a Sovereign Debt mod in one private headless game and saves its log lines where the tuner's Debt tab reads them.

Usage: py -3 tools/debt_run.py "<mod folder name>" <test name> <run until, e.g. 1837.1.1> "<title>" ["old text=>new text" ...]
Each change is applied to a private copy of the mod, so tuning variants can run side by side.
The game runs from a throwaway user folder, so the player's settings, saves and logs are untouched.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import debt

GAME = Path("G:/SteamLibrary/steamapps/common/Victoria 3/binaries")
DOCS = Path.home() / "OneDrive/Documents/Paradox Interactive/Victoria 3"
RUNS = Path(__file__).resolve().parent.parent / "runs" / "debt"
WORK_ROOT = Path("G:/GameDev/_claude_scratch/vic")
TIMEOUT_SECONDS = 3 * 3600
CHECK_SECONDS = 20
STEAM_APP_ID = "529340"  # without this the game cannot reach Steam, so every DLC feature reads as not owned


def apply_change(mod_copy, old, new):
    """Replaces text across the copied mod's scripts; a change that matches nothing would silently test the wrong thing."""
    hits = 0
    for path in mod_copy.rglob("*.txt"):
        text = path.read_bytes().decode("utf-8")
        if old in text:
            hits += 1
            path.write_bytes(text.replace(old, new).encode("utf-8"))
    if not hits:
        raise SystemExit(f"change matched nothing: {old}")


def read_logs(work):
    """Returns the mod's log lines and script errors. The game rotates its logs, so every numbered file holds part of the run."""
    def read(pattern):
        return [line for path in sorted((work / "logs").glob(pattern))
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]

    errors = [line for line in read("error*.log") if "sd_" in line or "sdt_" in line or "SDT" in line]
    return [line for line in read("debug*.log") if " SD" in line], errors


def save(work, test_name, title, mod_name, run_until, started, status, stopped=None, changes=()):
    """Writes a game's results where the Debt tab reads them; runs on every check, so a running game shows there too."""
    lines, errors = read_logs(work)
    folder = RUNS / test_name
    folder.mkdir(parents=True, exist_ok=True)
    if changes:
        (folder / "changes.txt").write_text("\n".join(changes), encoding="utf-8")
    (folder / "lines.log").write_text("\n".join(lines), encoding="utf-8")
    (folder / "errors.log").write_text("\n".join(errors), encoding="utf-8")
    game = {"start": "New game", "version": mod_name, "status": status, "until": run_until, "stopped": stopped,
            "minutes": round((time.time() - started) / 60, 1), "errors": len(errors)}
    debt.rescore(test_name, {"title": title, "game": game})
    return lines, errors


def run(mod_name, test_name, run_until, title, *changes):
    # Several games at once slow the whole machine too much
    if "victoria3.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq victoria3.exe"], capture_output=True, text=True).stdout:
        raise SystemExit("Another game is running; only one at a time.")
    work = WORK_ROOT / f"sd_{test_name}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    mod_copy = work / "sd_mod"
    shutil.copytree(DOCS / "mod" / mod_name, mod_copy)
    for change in changes:
        apply_change(mod_copy, *change.split("=>"))
    (work / "content_load.json").write_text(json.dumps(
        {"enabledMods": [{"path": str(mod_copy)}], "disabledDLC": [], "enabledUGC": []}))
    settings = json.loads((DOCS / "pdx_settings.json").read_text(encoding="utf-8"))
    settings.setdefault("game", {})["pause_on_event"] = False
    settings["game"]["save_to_cloud"] = False
    (work / "pdx_settings.json").write_text(json.dumps(settings, indent="\t"))

    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 7
    game = subprocess.Popen(
        [str(GAME / "victoria3.exe"), "-gdpr-compliant", "-handsoff", "-nographics", "-nosounds", "-nofilewatcher",
         "-disable_renderframeifneeded", "-no_crash_reporter", "-no_notifications",
         f"-userdir={work}", f"-run_until={run_until}"],
        cwd=str(GAME), startupinfo=startup, env={**os.environ, "SteamAppId": STEAM_APP_ID, "SteamGameId": STEAM_APP_ID})
    started = time.time()
    stopped = None
    while game.poll() is None and time.time() - started < TIMEOUT_SECONDS and not stopped:
        time.sleep(CHECK_SECONDS)
        try:
            lines, errors = save(work, test_name, title, mod_name, run_until, started, "running", None, changes)
            stopped = debt.stop_reason(lines, errors)
        except (ValueError, KeyError):
            pass  # caught the game mid-write; the next check reads the whole line
    timed_out = game.poll() is None and not stopped
    if game.poll() is None:
        game.kill()
        game.wait()

    status = "timeout" if timed_out else "stopped early" if stopped else "done"
    lines, errors = save(work, test_name, title, mod_name, run_until, started, status, stopped, changes)
    shutil.rmtree(work, ignore_errors=True)
    print(f"exit {game.poll()} stopped {stopped} timed_out {timed_out} minutes {(time.time() - started) / 60:.1f} lines {len(lines)} mod errors {len(errors)}")


if __name__ == "__main__":
    run(*sys.argv[1:])
