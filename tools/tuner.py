"""The Speculative Markets tuner: watch test games live, read their results, start or stop them, change balance values, build.

Usage: py -3 tools/tuner.py   then open http://localhost:8765
Stdlib only. Listens on 127.0.0.1. live.py finds running games, score.py scores finished ones. The tuner writes only
tools/tuning.json, test builds under sweep.WORK, runs/sweep_<test>/ for a test it starts, and mod/ after an explicit
confirmation with no game running.
"""
import ast
import json
import math
import os
import re
import statistics
import subprocess
import sys
import threading
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import debt
import live
import score
import sweep

PORT = 8765
TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
TUNING = TOOLS / "tuning.json"
PAGE = TOOLS / "tuner" / "index.html"
SELF_TESTS = ["tuning.py", "levers.py", "companies.py", "credit_ai.py", "company_section.py", "interest_board.py", "score.py", "debt.py", "centres.py"]

# name, group, label, description. Defaults come from the source: each is read through tuning.get(NAME, default).
CONSTANTS = [
    ("HYPE_GAIN", "Hype", "Hype gain", "Hype trend = gain x (fast - slow price average); higher swings investors harder"),
    ("FAST", "Hype", "Fast average weight", "Weight of this month's price in the fast price average; lower is smoother"),
    ("WORD_BUFFER", "Hype", "Word buffer", "A good changes interest word only once past the cut by this share of it (1/x side below 1)"),
    ("HYPE_MAX", "Hype", "Hype cap", "Hype clamp; the floor is 1 / cap"),
    ("HOT_HYPE", "Hype", "Booming at", "Hype at which a good counts as booming (Eager) and lifts confidence"),
    ("RISING_HYPE", "Hype", "Keen at", "Hype where the Keen word starts; Doubtful is below 1 / this"),
    ("PEAK_FOR_CRASH", "Unwinds", "Collapse peak", "A good that peaked this high and falls below 1 / this has Collapsed"),
    ("CONF_PER_CRASH_HYPE", "Unwinds", "Collapse cost", "Confidence lost per point of peak above 1 in a Collapse, at full weight"),
    ("BUST_PER_HYPE", "Unwinds", "Bust cost", "Confidence lost per point of peak above 1 in a Bust (Eager to Doubtful)"),
    ("CORRECTION_PER_HYPE", "Unwinds", "Correction cost", "Confidence lost per point of peak above 1 in a Correction (Keen to Doubtful)"),
    ("CONF_CRASH_MAX", "Unwinds", "Crash cap", "Most confidence one month of crashes can take, after scaling by confidence and depth"),
    ("CONF_START", "Confidence", "Resting confidence", "Confidence drifts back to this"),
    ("CONF_RECOVER", "Confidence", "Drift back", "Share of the gap to resting confidence closed each month"),
    ("MOOD_SHOCK", "Confidence", "Mood shock", "Largest random monthly change in Market Mood"),
    ("MOOD_KEEP", "Confidence", "Mood memory", "Share of last month's Market Mood kept each month; higher gives longer swings"),
    ("CONF_PER_HOT", "Confidence", "Confidence per boom", "Confidence a month per booming good at full weight"),
    ("MANIA", "Confidence", "Mania line", "Confidence at or above this is a Speculative Mania"),
    ("PANIC", "Confidence", "Panic line", "Confidence below this starts a Financial Panic"),
    ("PANIC_DAYS", "Confidence", "Panic length (days)", "How long a panic lasts before law scaling"),
    ("PANIC_ENDS_AT", "Confidence", "Panic ends at", "Confidence at which a panic ends before its months run out"),
    ("CONTAGION", "Confidence", "Contagion", "Confidence a linked country loses when a panic starts, before weighting"),
    ("CREDIT_FROM", "Credit", "Credit from", "Credit flows into the investment pool above this confidence"),
    ("CREDIT_SHARE", "Credit", "Credit share", "Monthly credit at full confidence, share of a month of investment pool income"),
    ("CREDIT_FLOW_MAX", "Credit", "Credit flow cap", "Most of a month's credit that comes from confidence, as a share of pool income, before the lending rate"),
    ("CREDIT_RUNOFF", "Credit", "Repayment", "Share of outstanding credit repaid each month"),
    ("CLAWBACK", "Credit", "Panic clawback", "Share of outstanding credit a panic pulls out of the investment pool"),
    ("DEBT_MAX", "Credit", "Debt drag", "Confidence lost a month at the credit limit"),
    ("LEV_ON", "Leverage", "Leverage system", "1 builds it in, 0 leaves it out"),
    ("LEV_SAFE", "Leverage", "Safe limit (months)", "Past this much debt, in months of pool income, stress starts, and credit stops until Central Banking"),
    ("LEV_RUIN", "Leverage", "Full stress at (months)", "Stress reaches 1 at this much debt"),
    ("LEV_PANIC_SPAN", "Leverage", "Panic line rise", "Points full stress adds to the panic line"),
    ("LEV_REWARD", "Leverage", "Credit Boom per month", "Throughput per whole month of leverage"),
    ("LEV_REWARD_MAX", "Leverage", "Credit Boom cap (months)", "Months of leverage that still add throughput"),
    ("LEV_CRUNCH_MAX", "Leverage", "Worst Bad Debts", "Points of Bad Debts a panic at full stress leaves; less stress leaves that share of this"),
    ("LEV_CRUNCH_FADE", "Leverage", "Bad Debts fade", "Points of Bad Debts lost a month, once felt in full"),
    ("LEV_CRUNCH_FADE_TIGHT", "Leverage", "Bad Debts fade, Tight", "Points of Bad Debts lost a month under Tight credit"),
    ("LEV_CRUNCH_INVEST", "Leverage", "Bad Debts investment loss", "Investment lost per point of Bad Debts, on top of the throughput loss"),
    ("LEV_CRUNCH_THROUGHPUT", "Leverage", "Bad Debts throughput loss", "Throughput lost per point of Bad Debts"),
    ("LEV_LAND_LOST", "Leverage", "Lost land starts at", "Losing this share of its people in a month counts as losing land"),
    ("LEV_RELIEF_MONTHS", "Leverage", "Lost land relief, months", "Months over which Bad Debts move from the old loans' measure to real leverage"),
    ("AI_LEV_LIMIT", "Leverage", "AI goes Tight at (months)", "Leverage at which an AI turns to Tight credit, by temperament"),
    ("LEVER_TAX_SHARE", "Levers", "Lever Authority", "Share of the good's consumption tax cost paid in Authority a month"),
    ("LEVER_THROUGHPUT", "Levers", "Lever throughput", "Throughput Encourage adds and Restrain takes from the good's producers"),
    ("SUBSIDY_SHARE", "Levers", "Encourage subsidy", "Weekly subsidy the state pays, as a share of the good's weekly output at base price"),
    ("LEVY_SHARE", "Levers", "Restrain levy", "Weekly levy the state collects, as a share of the good's weekly output at base price"),
    ("INTEREST_THROUGHPUT", "Levers", "Interest throughput ladder", "Throughput % by interest word, 1 Fleeing to 6 Feverish"),
    ("COMPANY_BUST", "Levers", "Company bust", "Throughput loss of the industry after its boom Collapses"),
    ("DEPTH_MIN", "Depth", "Depth min", "Speculation depth with no Financial Districts (scales hype and crash loss)"),
    ("DEPTH_MAX", "Depth", "Depth max", "Speculation depth cap"),
    ("STEADY_MIN", "Depth", "Steady min", "Steadiness clamp, low end (landed economies move less)"),
    ("STEADY_MAX", "Depth", "Steady max", "Steadiness clamp, high end"),
    ("EARLIEST_YEAR", "Long Depression", "Earliest year", "No Long Depression starts before this year"),
    ("EARLIEST_SPREAD", "Long Depression", "Earliest year spread", "Each game adds up to this many years to the earliest year"),
    ("SECOND_CHANCE", "Long Depression", "Second chance %", "Percent of games where a second can follow, from a different Great Power"),
    ("WORLD_DRIFT", "Long Depression", "World recovery drift", "World recovery a month in the Depression, out of 100"),
    ("SPREAD_MIN", "Long Depression", "Crash spread tie", "Tie weight at or above which the Crash passes to a partner (market 1, subject 0.8, investment 0.6, trade 0.4 x trade law)"),
    ("DEPRESSION_MAX", "Long Depression", "Depression max (months)", "Backstop length of the Depression phase"),
    ("TIGHT_PULL", "AI", "Tight credit pull", "Share of confidence above 60 that Tight credit takes off each month"),
    ("AI_TIGHT", "AI", "AI tightens above", "A Balanced AI tightens credit above this confidence"),
    ("WARY", "AI", "AI loosens below", "AI loosens credit below this confidence"),
    ("AI_CONF", "AI", "AI restrains at", "AI restrains its riskiest boom at this confidence or above"),
    ("AI_RISK", "AI", "AI restrain risk", "...and only when the boom's end would cost this much confidence"),
    ("TEMPER_SHIFT", "AI", "Temperament shift", "Confidence points a Bold or Cautious AI moves its thresholds by"),
]
SOURCES = ["generate.py", "leverage.py", "levers.py", "companies.py", "vanilla_ties.py", "depression.py", "credit_ai.py"]
_build_lock = threading.Lock()


# -- tuning --------------------------------------------------------------------------------------------------------

def defaults():
    """NAME -> (default, file) for every tuning.get("NAME", literal) call in the source files."""
    out = {}
    for f in SOURCES:
        for node in ast.walk(ast.parse((TOOLS / f).read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "tuning" and len(node.args) == 2):
                try:
                    out[node.args[0].value] = (ast.literal_eval(node.args[1]), f)
                except ValueError:
                    pass  # a default worked out from another value: not one the page can show
    return out


def read_overrides():
    try:
        v = json.loads(TUNING.read_text(encoding="utf-8") or "{}")
        return v if isinstance(v, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def tuning_state():
    d, over = defaults(), read_overrides()
    rows = []
    for name, group, label, desc in CONSTANTS:
        default, f = d.get(name, (None, "?"))
        value = over.get(name, default)
        if isinstance(default, dict):
            value = {str(k): (value or {}).get(str(k), dv) for k, dv in default.items()}
            default = {str(k): dv for k, dv in default.items()}
        rows.append({"name": name, "group": group, "label": label, "desc": desc, "file": f,
                     "default": default, "value": value, "missing": name not in d})
    return rows


def _num(v, like):
    """v checked against the default's type: ints stay ints, floats take any finite number."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("not a number")
    if isinstance(like, int):
        if v != int(v):
            raise ValueError("needs a whole number")
        return int(v)
    return v


def save_tuning(body):
    if not isinstance(body, dict):
        raise ValueError("expected an object")
    d = defaults()
    known = {c[0] for c in CONSTANTS}
    out = {}
    for name, v in body.items():
        if name not in known or name not in d:
            raise ValueError(f"unknown constant {name}")
        default = d[name][0]
        if isinstance(default, dict):
            if not isinstance(v, dict):
                raise ValueError(f"{name}: expected an object")
            vals = {str(k): _num(v.get(str(k), dv), dv) for k, dv in default.items()}
            if any(vals[str(k)] != dv for k, dv in default.items()):
                out[name] = vals
        else:
            try:
                v = _num(v, default)
            except ValueError as e:
                raise ValueError(f"{name}: {e}")
            if v != default:
                out[name] = v
    TUNING.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


# -- one game's charts ---------------------------------------------------------------------------------------------

# the log is not in date order and lines can run together when it rotates. Key by (tag, date) to drop repeats, sort each
# country's months, and keep a record only if the required fields are there.
SEG = re.compile(r"tag=(\S+) date=([A-Z][a-z]+ [0-9]+, [0-9]{4}) (.*)")
KV = re.compile(r"(\w+)=(\S*)")
REQUIRED = ("conf", "boom", "crash", "turmoil", "panic", "pool")


def parse_log(path):
    recs = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SPEC tag=" not in line:
                continue
            for seg in re.split(r"(?=tag=)", line):
                m = SEG.match(seg)
                if not m:
                    continue
                try:
                    d = datetime.strptime(m.group(2), "%B %d, %Y")
                except ValueError:
                    continue
                r = {}
                for k, v in KV.findall(m.group(3)):
                    try:
                        r[k] = float(v)
                    except ValueError:
                        pass
                if all(k in r for k in REQUIRED):
                    recs[(m.group(1), d)] = r
    runs = defaultdict(list)
    for (tag, d), r in sorted(recs.items()):
        runs[tag].append((d, r))
    return runs


def summarise(runs):
    rows = [r for v in runs.values() for _, r in v]
    if not rows:
        return None
    months = len(rows)
    confs = [r["conf"] for r in rows]
    pairs = [(a, b) for v in runs.values() for (_, a), (_, b) in zip(v, v[1:])]
    starts = sum(1 for a, b in pairs if b["panic"] and not a["panic"])
    return {"countries": len(runs), "country_months": months, "conf_median": statistics.median(confs),
            "mania_pct": 100 * sum(c >= 80 for c in confs) / months, "panic_pct": 100 * sum(1 for r in rows if r["panic"]) / months,
            "panic_starts": starts, "years_per_panic": months / 12 / max(starts, 1),
            "rescues": sum(1 for a, b in pairs if b.get("rescued") and not a.get("rescued")),
            "hot_pct": 100 * sum(r.get("lev", 0) >= 3 for r in rows) / months,
            "debts_pct": 100 * sum(r.get("crunch", 0) >= 1 for r in rows) / months}


@lru_cache(maxsize=8)
def game_data(path, size):
    """Charts for one game. size is in the key so a game still running is read again as it grows."""
    runs = parse_log(path)
    s = summarise(runs)
    if s is None:
        return {"summary": None}
    # world series by calendar month: countries' monthly pulses fall on different days
    by_month = defaultdict(dict)
    for tag, v in runs.items():
        for d, r in v:
            by_month[f"{d:%Y-%m}"][tag] = r
    months = sorted(by_month)
    idx = {m: i for i, m in enumerate(months)}

    def pct(m, test):
        rs = by_month[m].values()
        return round(100 * sum(1 for r in rs if test(r)) / len(rs), 2)

    world = {"panic": [pct(m, lambda r: r["panic"]) for m in months],
             "mania": [pct(m, lambda r: r["conf"] >= 80) for m in months],
             "hot": [pct(m, lambda r: r.get("lev", 0) >= 3) for m in months],
             "debts": [pct(m, lambda r: r.get("crunch", 0) >= 1) for m in months]}
    conf = {}
    for tag, v in runs.items():
        row = [None] * len(months)
        for d, r in v:
            row[idx[f"{d:%Y-%m}"]] = round(r["conf"], 1)
        conf[tag] = row
    return {"summary": s, "months": months, "world": world, "conf": conf}


def game_log(q):
    """The log of a game on the page: a running one by process, a finished one by test and folder, never a path from the request."""
    if "pid" in q:
        for pid, g in live._games.items():
            if str(pid) == q["pid"][0]:
                return g.log.path
        raise FileNotFoundError
    for g in score.games():
        if g["test"] == q.get("test", [""])[0] and g["folder"] == q.get("folder", [""])[0]:
            return Path(g["path"]) / "telemetry.log"
    raise FileNotFoundError


# -- builds --------------------------------------------------------------------------------------------------------

def _run(label, args, env):
    try:
        p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600, creationflags=live.NO_WINDOW)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        code, out, err = -1, "", "timed out after 600 s"
    return {"name": label, "cmd": " ".join(str(a) for a in args), "code": code, "ok": code == 0,
            "stdout": out[-20000:], "stderr": err[-20000:]}


def self_tests():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    steps = []
    for f in SELF_TESTS:
        r = _run(f"self-test {f}", [sys.executable, str(TOOLS / f)], env)
        r["stdout"] = r["stdout"][-1500:]  # credit_ai.py prints its whole effects file
        steps.append(r)
    return steps


def build(body):
    """A test build keeps the logging tests need; the live mod never ships it. Neither is built under a running game."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    in_use, games = live.running_builds()
    if body.get("target") == "live":
        if body.get("confirm") != "live":
            raise ValueError("live build needs confirm=live")
        if games:
            raise ValueError(f"{games} games are running: a game can crash when its mod changes under it")
        env.pop("SPEC_MOD_OUT", None)  # generate.py and check.py then write and read mod/
        target, args = ROOT / "mod", []
    else:
        name = body.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
            raise ValueError("name the build with letters, numbers, - or _")
        target, args = sweep.WORK / f"b_{name}", ["--log"]
        if target.name in in_use:
            raise ValueError(f"a running game is using {target.name}")
        env["SPEC_MOD_OUT"] = str(target)
    steps = [_run(" ".join(["generate.py", *args]), [sys.executable, str(TOOLS / "generate.py"), *args], env)]
    if steps[0]["ok"]:
        steps.append(_run("check.py", [sys.executable, str(TOOLS / "check.py")], env))
    return {"target": str(target), "steps": steps + self_tests()}


# -- server --------------------------------------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _local(self):
        # DNS rebinding and cross-site requests: only our own host names, and a matching Origin when one is sent
        hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (origin is None or origin.split("//", 1)[-1] in hosts)

    def do_GET(self):
        if not self._local():
            return self._send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/":
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/live":
                return self._send(200, live.snapshot())
            if u.path == "/api/options":
                return self._send(200, live.options())
            if u.path == "/api/tests":
                return self._send(200, score.tests())
            if u.path == "/api/score":
                return self._send(200, score.scorecard(q.get("test", [""])[0]))
            if u.path == "/api/game":
                log = game_log(q)
                return self._send(200, game_data(str(log), log.stat().st_size))
            if u.path == "/api/tuning":
                return self._send(200, tuning_state())
            if u.path == "/api/debt":
                name = q.get("test", [""])[0]
                return self._send(200, debt.test(name) if name else debt.tests())
            return self._send(404, {"error": "not found"})
        except FileNotFoundError:
            return self._send(404, {"error": "that game has no log"})

    def do_POST(self):
        if not self._local() or not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._send(403, {"error": "forbidden"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(n, 1_000_000)) or b"{}")
        except ValueError:
            return self._send(400, {"error": "bad json"})
        path = urlparse(self.path).path
        try:
            if path == "/api/tuning":
                return self._send(200, {"saved": save_tuning(body)})
            if path == "/api/start":
                return self._send(200, live.start_test(body))
            if path == "/api/stop":
                live.stop_test(body["test"]) if "test" in body else live.stop_game(int(body["pid"]))
                return self._send(200, {"ok": True})
            if path in ("/api/build", "/api/selftest"):
                if not _build_lock.acquire(blocking=False):
                    return self._send(409, {"error": "a build is already running"})
                try:
                    return self._send(200, {"steps": self_tests()} if path == "/api/selftest" else build(body))
                finally:
                    _build_lock.release()
        except (ValueError, KeyError) as e:
            return self._send(400, {"error": str(e)})
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Speculative Markets tuner on http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
