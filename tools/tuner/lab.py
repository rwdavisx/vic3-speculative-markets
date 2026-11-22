"""Checks and sweeps on every core, the targets file, and the latest result the page shows.

py -3 -B tools/tuner/lab.py check [KEY=value ...] [--note text] [--n 1000] [--seed 1]
py -3 -B tools/tuner/lab.py sweep KEY=lo:hi [KEY=lo:hi ...] [KEY=value ...] [--cands 48] [--n 1000] [--note text]

Each run is kept in build_scratch/tuner/runs/<id>.json, and latest.json is the newest. While it runs, its events go to
runs/<id>.live.jsonl, which the server streams to an open page, so a run from here shows live too.
"""
import json
import math
import multiprocessing as mp
import os
import random
import re
import secrets
import sys
import time
from pathlib import Path

import engine

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TARGETS = HERE / "targets.json"
LATEST = REPO / "build_scratch" / "tuner" / "latest.json"
RUNS = LATEST.parent / "runs"
RUN_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{4}$")
KEYS = {s[0]: s for s in engine.TUNABLE}
CORES = int(os.environ.get("SPEC_TUNER_CORES") or os.cpu_count() or 1)  # set lower to leave the game room
KEEP_BANDS = 12  # candidates whose charts the saved result keeps, best first
FIELDS = ("metric", "who", "aim", "lo", "hi", "weight")


def targets():
    if TARGETS.exists():
        return json.loads(TARGETS.read_text(encoding="utf-8"))
    return [dict(zip(FIELDS, t)) for t in engine.TARGETS]


def save_targets(ts):
    clean = []
    for t in ts:
        assert t["metric"] in engine.METRICS, t["metric"]
        assert all(b in engine.BOTS for b in t["who"].split("-")), t["who"]
        clean.append({"metric": t["metric"], "who": t["who"], **{k: float(t[k]) for k in ("aim", "lo", "hi")},
                      "weight": float(t.get("weight", 1)), "why": str(t.get("why", ""))})
    TARGETS.write_text("[\n" + ",\n".join(" " + json.dumps(t) for t in clean) + "\n]\n", encoding="utf-8", newline="\n")
    return clean


def rows(ts):
    return [[t[k] if k != "weight" else t.get("weight", 1) for k in FIELDS] for t in ts]


def current():
    return {k: v for k, v in engine.current().items() if k in KEYS}


def credit_tier_note(values):
    ceiling = values.get("LEV_RUIN", engine.lv.RUIN)
    top = engine.lv.LADDER[-1]
    if ceiling < top:
        return (f"The {ceiling:g}-month lending ceiling cuts off the top of the "
                f"{top:g}-month technology tier.")
    return ""


def rescore(result, ts=None):
    """Score a saved result against the targets as they are now (the page edits them after a run)."""
    tr = rows(ts or targets())
    for c in result["cands"]:
        c["score"], c["parts"] = engine.score(c["metrics"], tr)
        c["score"] = round(c["score"], 4)
    result["cands"].sort(key=lambda c: c["score"])
    return result


# the confidence bar's tiers (market_tab.TIERS, 20/40/60/80): these sit on a tier's edge and move only with the scale
BATCH_ECON = 500  # economies a worker steps at once: a job batches candidates up to this (engine.batch). On every core
# at once memory is the limit, so batching pays only for small runs: 125 economies x 4 halves a sweep, 500 x 4 is slower
ON_TIERS = {"MANIA", "PANIC_ENDS_AT"}
# moved together, follower: leader. Confidence rests where the banks start lending (generate.CREDIT_FROM's note)
LINKED = {"CREDIT_FROM": "CONF_START"}
STEP = {"PANIC_DAYS": 15}  # half months


def snap(k, x, whole):
    """A round value: steps of 5, 0.5, 0.05 ... by the value's own size; whole numbers at least 1 apart."""
    if x == 0:
        return 0 if whole else 0.0
    step = STEP.get(k) or 5 * 10 ** (math.floor(math.log10(abs(x))) - 1)
    if whole:
        step = max(round(step), 1)
    v = round(x / step) * step
    return int(round(v)) if whole else float(f"{v:.6g}")


def candidates(cur, fixed, vary, n, seed):
    base = cur | {k: v for k, v in fixed.items() if k in KEYS}
    for f, lead in LINKED.items():
        base[f] = base[lead]
    vary = {k: r for k, r in vary.items() if k not in ON_TIERS and k not in LINKED}
    rng = random.Random(seed)
    out, seen = [base], {json.dumps(base, sort_keys=True)}
    for _ in range(n * 20):  # on the grid, draws repeat: keep the distinct ones
        if len(out) >= n:
            break
        v = dict(base)
        for k, (lo, hi) in vary.items():
            v[k] = snap(k, rng.uniform(float(lo), float(hi)), isinstance(cur[k], int))
        for f, lead in LINKED.items():
            v[f] = v[lead]
        key = json.dumps(v, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def sweep(spec, pool, cur=None, emit=lambda e: None, stop=None):
    """spec: fixed {key: v}, vary {key: [lo, hi]}, candidates, economies, seed, bot, cfg, note; or list: the candidates' full
    values, to run as they are. Saves and returns the result."""
    cur = cur or current()
    ts = spec.get("targets") or targets()
    tr = rows(ts)
    cfg, n, seed = spec.get("cfg") or engine.defaults(), int(spec.get("economies", 1000)), int(spec.get("seed", 1))
    vary = {k: v for k, v in (spec.get("vary") or {}).items() if k in KEYS}
    fixed = {k: v for k, v in (spec.get("fixed") or {}).items() if k in KEYS and v != cur[k]}
    cands = [dict(c) for c in spec["list"]] if spec.get("list") else candidates(cur, fixed, vary, int(spec.get("candidates", 48)) if vary else 1, seed)
    if fixed:  # a check of new numbers also runs the current ones, for the ghost marks
        cands.insert(0, dict(cur))
    bots = sorted({spec.get("bot", "passive"), *(b for t in tr for b in t[1].split("-"))})
    B = max(1, min(8, BATCH_ECON // n, -(-len(cands) * len(bots) // (2 * CORES))))  # two jobs a core at least
    jobs = [(list(range(i, min(i + B, len(cands)))), b, cands[i:i + B], cfg, n, seed) for i in range(0, len(cands), B) for b in bots]
    total = len(cands) * len(bots)
    label = ("Sweep of " + ", ".join(vary) + f" ({len(cands)} candidates)") if vary else \
        ("Check: " + ", ".join(f"{k} {cur[k]:g} → {v:g}" for k, v in fixed.items())) if fixed else "Check: the current numbers"
    rid = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)  # two runs at once never share a file
    RUNS.mkdir(parents=True, exist_ok=True)
    for old in RUNS.glob("*.live.jsonl"):  # finished runs' live files, a day on
        if time.time() - old.stat().st_mtime > 86400:
            old.unlink(missing_ok=True)
    live = open(RUNS / f"{rid}.live.jsonl", "a", encoding="utf-8")

    def tell(ev):  # to the server's own page (emit), and to the live file any server streams
        emit(ev)
        live.write(dumps(ev) + "\n")
        live.flush()

    tell({"type": "start", "run": rid, "origin": spec.get("origin", "command line"), "total": total, "cores": CORES, "bots": bots,
          "candidates": len(cands), "label": label, "note": spec.get("note", "")})
    got, done, t0, out, shown = {}, 0, time.time(), [], 0.0
    try:
        for cid, bot, summ, bnd in (x for res in pool.imap_unordered(engine.batch, jobs) for x in res):
            if stop is not None and stop.is_set():
                tell({"type": "stopped", "run": rid})
                return None
            got.setdefault(cid, {})[bot] = (summ, bnd)
            done += 1
            if time.time() - shown > 0.5 or done == total:
                shown = time.time()
                tell({"type": "progress", "run": rid, "done": done, "total": total, "secs": round(time.time() - t0, 1)})
            if len(got[cid]) == len(bots):
                res = {b: s for b, (s, _) in got[cid].items()}
                score, parts = engine.score(res, tr)
                c = {"id": cid, "score": round(score, 4), "parts": parts, "metrics": res, "bands": {b: bd for b, (_, bd) in got[cid].items()},
                     "values": cands[cid], "credit_tier_note": credit_tier_note(cands[cid]),
                     "changed": {k: [cur[k], v] for k, v in cands[cid].items() if v != cur[k]}}
                out.append(c)
                tell({"type": "candidate", "run": rid, "id": cid, "score": c["score"], "changed": c["changed"],
                      "parts": [{k: p[k] for k in ("metric", "who", "value", "in")} for p in parts]})
        out.sort(key=lambda c: c["score"])
        for c in out[KEEP_BANDS:]:
            if c["id"] != 0:
                c["bands"] = None
        result = {"id": rid, "label": label, "note": spec.get("note", ""), "time": time.strftime("%Y-%m-%d %H:%M"), "secs": round(time.time() - t0, 1),
                  "economies": n, "seed": seed, "years": (cfg.get("inputs") or {}).get("years", engine.INPUTS["years"][0]), "bots": bots,
                  "cfg": cfg, "baseline": 0, "cands": out}
        body = dumps(result)
        write(RUNS / f"{rid}.json", body)
        write(LATEST, body)
        tell({"type": "done", "run": rid, "secs": result["secs"]})
        return result
    finally:
        live.close()


def dumps(o):
    return json.dumps(o, default=lambda x: x.item() if hasattr(x, "item") else str(x))


def write(path, text):
    """Whole or not at all: a page reading the file never sees half of it."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(2)}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def saved_runs():
    """The kept runs, newest first: id, its note (its name), label, time, and its best against the targets as they are now."""
    ts, out = rows(targets()), []
    for p in sorted(RUNS.glob("*.json"), reverse=True):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        best = min((engine.score(c["metrics"], ts) for c in r["cands"]), key=lambda s: s[0], default=None)
        out.append({"id": p.stem, "note": r.get("note", ""), "label": r["label"], "time": r["time"], "economies": r["economies"],
                    "candidates": len(r["cands"]), "score": round(best[0], 2) if best else None,
                    "met": sum(q["in"] for q in best[1]) if best else 0, "of": len(best[1]) if best else 0})
    return out


def load_run(rid):
    if not RUN_ID.match(rid or ""):
        return None
    p = RUNS / f"{rid}.json"
    return rescore(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else None


def report(result):
    """The result as a few lines: each target in or out for the best candidate, then the runners-up."""
    best, M = result["cands"][0], engine.METRICS
    seed = f", seed {result['seed']}" if "seed" in result else ""
    lines = [f"{result['label']}  ({result['economies']} economies x {result['years']} years{seed}, {', '.join(result['bots'])}, {result['secs']}s)"]
    if best["changed"]:
        lines.append("Best: " + ", ".join(f"{k} {o:g} -> {n:g}" for k, (o, n) in best["changed"].items()))
    if best.get("credit_tier_note"):
        lines.append(best["credit_tier_note"])
    for p in best["parts"]:
        m = best["metrics"].get(p["who"], {}).get(p["metric"], {})
        rng = f"  (10-90%: {m['p10']:.1f}-{m['p90']:.1f})" if "p10" in m else ""
        v = "not run" if p["value"] is None else f"{p['value']:.2f}"
        lines.append(f"  {'in ' if p['in'] else 'OUT'} {M[p['metric']][0]} ({p['who']}): {v}, band {p['lo']:g} to {p['hi']:g}{rng}")
    lines.append(f"{sum(p['in'] for p in best['parts'])} of {len(best['parts'])} targets met. Score {best['score']:.2f}.")
    for c in result["cands"][1:6] if len(result["cands"]) > 2 else []:
        lines.append(f"  #{c['id']} score {c['score']:.2f}, {sum(p['in'] for p in c['parts'])} met: " +
                     (", ".join(f"{k} {n:g}" for k, (o, n) in c["changed"].items()) or "the current numbers"))
        if c.get("credit_tier_note"):
            lines.append("    " + c["credit_tier_note"])
    return "\n".join(lines)


def _args(argv):
    spec, opts, i = {"fixed": {}, "vary": {}}, {"--n": "economies", "--seed": "seed", "--cands": "candidates", "--note": "note", "--bot": "bot"}, 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            spec[opts[a]] = argv[i + 1] if a in ("--note", "--bot") else int(argv[i + 1])
            i += 2
            continue
        k, v = a.split("=", 1)
        assert k in KEYS, f"{k}: not a tunable constant"
        if ":" in v:
            spec["vary"][k] = [float(x) for x in v.split(":")]
        else:
            spec["fixed"][k] = float(v) if "." in v else int(v)
        i += 1
    return spec


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    cmd, spec = sys.argv[1], _args(sys.argv[2:])
    assert cmd in ("check", "sweep"), "check or sweep"
    if cmd == "check":
        spec["vary"] = {}
    with mp.get_context("spawn").Pool(CORES) as pool:
        print(report(sweep(spec, pool)))
