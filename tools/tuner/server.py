"""The tuner's command center: http://localhost:8765, one command.

py -3 -B tools/tuner/server.py [port]          this PC only
py -3 -B tools/tuner/server.py --lan [port]    also the phone, over Wi-Fi: prints the link to open on it once

The page only draws; every number comes from engine.py. Checks and sweeps (lab.py, from the page or the command line)
run on every core; each streams its tries to the page as it goes (runs/<id>.live.jsonl) and is kept in
build_scratch/tuner/runs/, latest.json the newest. Apply writes tools/tuning.json (or SPEC_TUNING), prints each change
old -> new, regenerates into the dev stage and syncs the live folder, then reruns the engine's self-check.
SPEC_TUNER_STAGE / SPEC_TUNER_LIVE move the stage and live folders (default build_scratch/rivals_stage and rivals_live).

The key: every request from another address needs it, and every change (runs, stop, targets, apply) needs it from
anywhere, so no other web page can drive the tuner. It is kept in build_scratch/tuner/key.txt; the link sets it as a
cookie, so the phone opens the link once. Windows may ask once to let Python through on private networks.
"""
import argparse
import hmac
import json
import multiprocessing as mp
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import engine
import lab
import tuning

HERE = lab.HERE
REPO = lab.REPO
KEY_FILE = lab.LATEST.parent / "key.txt"
LOCAL = {"127.0.0.1", "::1"}
HOSTS = {"localhost", "127.0.0.1", "::1"}  # plus the LAN address with --lan: a page on another name (DNS rebinding) is refused
STAGE = Path(os.environ.get("SPEC_TUNER_STAGE") or REPO / "build_scratch" / "rivals_stage").resolve()
LIVE = Path(os.environ.get("SPEC_TUNER_LIVE") or REPO / "build_scratch" / "rivals_live").resolve()
for p in (STAGE, LIVE):  # never the stable release
    assert not p.is_relative_to((REPO / "mod").resolve()), f"{p} is inside mod/"
KEYS = lab.KEYS
FILES = {"/": ("command.html", "text/html"), "/works.css": ("works.css", "text/css"), "/works.json": ("works.json", "application/json")}

LOCK = threading.Condition()
EVENTS = []  # every event since the server started; the page's EventSource resumes by index
STOP = threading.Event()
CURRENT = lab.current()
POOL = None


def dumps(o):
    return json.dumps(o, default=lambda x: x.item() if hasattr(x, "item") else str(x))


def emit(ev):
    with LOCK:
        EVENTS.append(ev)
        LOCK.notify_all()


def pool():
    global POOL
    if POOL is None:
        POOL = mp.get_context("spawn").Pool(os.cpu_count())
    return POOL


def run_sweep(spec):
    STOP.clear()
    try:
        lab.sweep(spec | {"origin": "page"}, pool(), CURRENT, stop=STOP)  # its events reach the page through its live file
    except Exception as e:  # shown on the page, not lost in a thread
        emit({"type": "error", "msg": repr(e)})


def mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return 0


def watch():
    """Every run's live file, from here or the command line, streamed to the page as it grows; a new kept run or a new
    latest.json tells the page too. Files already there at start are read from their end."""
    seen, kept = mtime(lab.LATEST), set(lab.RUNS.glob("*.json"))
    at = {p: p.stat().st_size for p in lab.RUNS.glob("*.live.jsonl")}
    while True:
        time.sleep(0.4)
        for p in lab.RUNS.glob("*.live.jsonl"):
            try:
                size, pos = p.stat().st_size, at.get(p, 0)
            except OSError:
                continue
            if size <= pos:
                continue
            with open(p, "rb") as f:
                f.seek(pos)
                chunk = f.read(size - pos)
            cut = chunk.rfind(b"\n") + 1  # whole lines only; the rest waits for the next look
            at[p] = pos + cut
            for line in chunk[:cut].splitlines():
                try:
                    emit(json.loads(line))
                except ValueError:
                    pass
        now = set(lab.RUNS.glob("*.json"))
        if now - kept:
            emit({"type": "runs"})
        kept = now
        m = mtime(lab.LATEST)
        if m != seen:
            seen = m
            emit({"type": "latest"})


def stop():
    global POOL
    STOP.set()
    if POOL is not None:
        POOL.terminate()
        POOL = None
    emit({"type": "stopped"})


def apply(values):
    """tuning.json <- values, then regenerate into the stage, sync live, self-check. Returns (ok, log)."""
    global CURRENT
    values = {k: v for k, v in values.items() if k in KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)}
    log = [f"{k} ({KEYS[k][4]}): {CURRENT[k]:g} → {v:g}" for k, v in sorted(values.items()) if v != CURRENT[k]]
    if not log:
        return True, "Nothing changed."
    old = json.loads(tuning.PATH.read_text(encoding="utf-8")) if tuning.PATH.exists() else {}
    tuning.PATH.write_text(json.dumps(old | values, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    log.insert(0, f"Wrote {tuning.PATH}")
    env = os.environ | {"SPEC_MOD_OUT": str(STAGE), "SPEC_TUNING": str(tuning.PATH), "PYTHONIOENCODING": "utf-8"}
    steps = [("Regenerate", [sys.executable, "-B", "tools/generate.py"]),
             ("Sync live", [sys.executable, "-B", "build_scratch/sync_live.py", str(STAGE), str(LIVE)]),
             ("Self-check", [sys.executable, "-B", "tools/tuner/engine.py"])]
    for name, cmd in steps:
        r = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        log.append(f"{name}: {'ok' if r.returncode == 0 else 'FAILED'}" + "".join("\n   " + t for t in tail))
        if r.returncode:
            return False, "\n".join(log)
    r = subprocess.run([sys.executable, "-B", "tools/tuner/engine.py", "--json"], cwd=REPO, env=env, capture_output=True, text=True)
    CURRENT = json.loads(r.stdout)
    return True, "\n".join(log)


def config():
    return {"spec": [{"key": k, "group": s[3], "label": s[4], "value": CURRENT[k], "int": isinstance(CURRENT[k], int)} for k, s in KEYS.items()],
            "inputs": {k: list(v) for k, v in engine.INPUTS.items()}, "cfg": engine.defaults(), "bots": list(engine.BOTS),
            "consts": engine.current() | CURRENT, "targets": lab.targets(), "metrics": engine.METRICS, "calc": engine.CALC,
            "bands": engine.BANDS, "replay": {"fields": engine.REPLAY_FIELDS, "fragment": engine.log_fragment()},
            "cores": os.cpu_count(), "paths": {"tuning": str(tuning.PATH), "stage": str(STAGE), "live": str(LIVE)},
            "fit": json.loads(engine.FITTED.read_text(encoding="utf-8")) if engine.FITTED.exists() else None}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200, cookie=False):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        if cookie:
            self.key_cookie()
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- the key ----
    def keyed(self):
        c = SimpleCookie()
        try:
            c.load(self.headers.get("Cookie") or "")
        except Exception:
            return False
        return "tk" in c and hmac.compare_digest(c["tk"].value.encode(), KEY.encode())

    def key_cookie(self):
        self.send_header("Set-Cookie", f"tk={KEY}; Max-Age=31536000; Path=/; SameSite=Strict; HttpOnly")

    def allowed(self, url, change):
        """True to go on; otherwise the answer is sent. A link with the key sets the cookie and drops the key from the address."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in HOSTS:
            self.send("Unknown host.", "text/plain", 403)
            return False
        key = parse_qs(url.query).get("key", [""])[0]
        if key and hmac.compare_digest(key.encode(), KEY.encode()):
            self.send_response(303)
            self.key_cookie()
            self.send_header("Location", url.path or "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        if (self.client_address[0] in LOCAL and not change) or self.keyed():
            return True
        self.send("Open the link the tuner printed (it carries the key).", "text/plain", 403)
        return False

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        if not self.allowed(url, False):
            return
        if path in FILES:
            name, ctype = FILES[path]
            if path == "/" and not self.keyed():  # this PC's own page gets the key for its changes
                return self.send((HERE / name).read_bytes(), ctype, cookie=True)
            return self.send((HERE / name).read_bytes(), ctype)
        if path == "/api/config":
            return self.send(dumps(config()))
        if path == "/api/latest":
            if not lab.LATEST.exists():
                return self.send("null")
            return self.send(dumps(lab.rescore(json.loads(lab.LATEST.read_text(encoding="utf-8")))))
        if path == "/api/live":  # a page opened mid-run catches up: the events of every run touched in the last ten minutes
            out = []
            for p in sorted(lab.RUNS.glob("*.live.jsonl")):
                if time.time() - mtime(p) < 600:
                    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                        try:
                            out.append(json.loads(line))
                        except ValueError:
                            pass
            return self.send(dumps(out))
        if path == "/api/runs":
            return self.send(dumps(lab.saved_runs()))
        if path == "/api/run":
            r = lab.load_run(parse_qs(url.query).get("id", [""])[0])
            return self.send(dumps(r)) if r else self.send("no such run", "text/plain", 404)
        if path == "/api/events":
            return self.events()
        self.send("not found", "text/plain", 404)

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        last = self.headers.get("Last-Event-ID")
        with LOCK:
            i = int(last) + 1 if last else len(EVENTS)
        try:
            while True:
                with LOCK:
                    LOCK.wait_for(lambda: len(EVENTS) > i, timeout=15)
                    new = EVENTS[i:]
                out = "".join(f"id: {i + j}\ndata: {dumps(e)}\n\n" for j, e in enumerate(new)) or ": keepalive\n\n"
                i += len(new)
                self.wfile.write(out.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def do_POST(self):
        url = urlparse(self.path)
        if not self.allowed(url, True):
            return
        path, b = url.path, self.body()
        if path in ("/api/sweep", "/api/watch"):
            try:
                cfg = b.get("cfg") or {}
                engine.player_finance_orders(cfg)
                engine.player_lever_orders(cfg.get("player_lever_orders", ()))
            except (TypeError, ValueError) as err:
                return self.send(str(err), "text/plain", 400)
        if path == "/api/sweep":
            threading.Thread(target=run_sweep, args=(b,), daemon=True).start()
            return self.send("{}")
        if path == "/api/stop":
            stop()
            return self.send("{}")
        if path == "/api/targets":
            try:
                ts = lab.save_targets(b.get("targets") or [])
            except (AssertionError, KeyError, ValueError) as e:
                return self.send(dumps({"ok": False, "msg": repr(e)}))
            emit({"type": "latest"})  # the board rescores against the new targets
            return self.send(dumps({"ok": True, "targets": ts}))
        if path == "/api/watch":
            values = CURRENT | {k: v for k, v in (b.get("values") or {}).items() if k in KEYS}
            e = engine.run(values, b.get("cfg") or engine.defaults(), b.get("bot", "passive"), 1, int(b.get("seed", 1)), trace=True)
            return self.send(dumps({"frames": e.hist, "summary": engine.summarize(e), "money": str(e.money[0]), "econ": str(e.econ[0]),
                                    "temper": int(e.temper[0])}))
        if path == "/api/apply":
            ok, log = apply(b.get("values") or {})
            print(log, flush=True)
            return self.send(dumps({"ok": ok, "log": log, "config": config()}))
        self.send("not found", "text/plain", 404)


def the_key():
    if not KEY_FILE.exists():
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(secrets.token_urlsafe(18), encoding="utf-8")
    return KEY_FILE.read_text(encoding="utf-8").strip()


def lan_address():
    """The address this PC has on its network: the one the default route leaves by. A UDP connect sends nothing."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("10.254.254.254", 1))
        return s.getsockname()[0]


KEY = the_key()

if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="The tuner's command center.")
    ap.add_argument("port", nargs="?", type=int, default=8765)
    ap.add_argument("--lan", action="store_true", help="also serve this PC's Wi-Fi address, for a phone")
    a = ap.parse_args()
    addrs = ["127.0.0.1"]
    if a.lan:
        ip = lan_address()
        assert not ip.startswith("127."), "no network address found"
        addrs.append(ip)
        HOSTS.add(ip)
    servers = [ThreadingHTTPServer((ad, a.port), H) for ad in addrs]
    for s in servers:
        s.daemon_threads = True
    threading.Thread(target=watch, daemon=True).start()
    print(f"Tuner on http://localhost:{a.port}  ({os.cpu_count()} cores, tuning file {tuning.PATH})", flush=True)
    if a.lan:
        print(f"On your phone (same Wi-Fi), open once: http://{addrs[1]}:{a.port}/?key={KEY}", flush=True)
        print("If Windows asks whether Python may use private networks, click Allow.", flush=True)
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
