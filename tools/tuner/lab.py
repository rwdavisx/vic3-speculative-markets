"""Checks and sweeps on every core, the targets file, and the latest result the page shows.

py -3 -B tools/tuner/lab.py check [KEY=value ...] [--note text] [--n 1000] [--seed 1]
py -3 -B tools/tuner/lab.py sweep KEY=lo:hi [KEY=lo:hi ...] [KEY=value ...] [--cands 48] [--n 1000] [--note text] [--halving [--rung 111]]
py -3 -B tools/tuner/lab.py map [KEY ...] [--n 125] [--seed 1]   each key one grid step down and up -> tools/tuner/keymap.json

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
import statistics
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
    label = spec.get("label") or (("Sweep of " + ", ".join(vary) + f" ({len(cands)} candidates)") if vary else
        ("Check: " + ", ".join(f"{k} {cur[k]:g} → {v:g}" for k, v in fixed.items())) if fixed else "Check: the current numbers")
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
        if spec.get("save", True):  # a halving rung or the key map keeps its own record
            save_run(result)
        tell({"type": "done", "run": rid, "secs": result["secs"]})
        return result
    finally:
        live.close()


def save_run(result):
    body = dumps(result)
    write(RUNS / f"{result['id']}.json", body)
    write(LATEST, body)


def halving(spec, pool, cur=None, emit=lambda e: None, stop=None):
    """Successive halving: every candidate at the first rung's economies (n/9 unless spec rung), the best third on at three
    times that, the best third of those at full n. Same seed every rung; the baseline (id 0) always goes on. The saved run
    is a normal one of the finalists, plus "dropped" (each with the rung it fell at and its score there) and "rungs"."""
    n = int(spec.get("economies", 1000))
    first = int(spec.get("rung") or max(n // 9, 1))
    sizes = [first, min(first * 3, n), n] if first * 3 < n else [first, n]
    vals, ids, dropped, rungs, scores, label = None, None, [], [], {}, None
    for r, size in enumerate(sizes):
        step = dict(spec, economies=size, save=False, label=f"{label} (rung {r + 1} of {len(sizes)}, {size} economies)" if label else None)
        if vals is not None:
            step |= {"list": vals, "fixed": {}, "vary": {}}
        res = sweep(step, pool, cur, emit, stop)
        if res is None:
            return None
        if label is None:
            label = res["label"]
        for c in res["cands"]:  # ids back to the first rung's numbering
            c["id"] = ids[c["id"]] if ids else c["id"]
            scores.setdefault(c["id"], []).append(c["score"])
            c["rung_scores"] = scores[c["id"]]
        rungs.append({"economies": size, "candidates": len(res["cands"]), "secs": res["secs"]})
        if size == n:
            break
        on = {c["id"] for c in res["cands"][:max(1, math.ceil(len(res["cands"]) / 3))]} | {0}  # sorted best first
        dropped += [{k: c[k] for k in ("id", "score", "values", "changed")} | {"rung": r + 1, "economies": size}
                    for c in res["cands"] if c["id"] not in on]
        keep = sorted((c for c in res["cands"] if c["id"] in on), key=lambda c: c["id"])  # the baseline first: the next id 0
        ids, vals = [c["id"] for c in keep], [c["values"] for c in keep]
    every = sorted([c["id"] for c in res["cands"]] + [d["id"] for d in dropped])
    assert every == sorted(scores) and len(every) == len(set(every)), "halving lost or doubled a candidate"
    assert any(c["id"] == 0 for c in res["cands"]), "the baseline fell out"
    res |= {"label": label + " (halving)", "secs": round(sum(x["secs"] for x in rungs), 1), "dropped": dropped, "rungs": rungs}
    save_run(res)
    return res


def keymap(spec, pool, cur=None):
    """Each tunable key alone, one grid step down and up (a linked follower moves with its leader), at a modest size,
    against the baseline on the same seed; the baseline again on two more seeds for the noise. Writes keymap.json."""
    cur = cur or current()
    n, seed, ts = int(spec.get("economies", 125)), int(spec.get("seed", 1)), targets()
    keys = spec.get("keys") or list(KEYS)
    base = candidates(cur, {}, {}, 1, seed)[0]
    vals, moves = [base], []
    skipped = [f"{k}: moves with {LINKED[k]}" if k in LINKED else f"{k}: pinned to a confidence tier"
               for k in keys if k in ON_TIERS or k in LINKED]
    for k in (k for k in keys if k not in ON_TIERS and k not in LINKED):
        x, whole = base[k], isinstance(base[k], int)
        s = (1 if whole else 0.5) if x == 0 else STEP.get(k) or 5 * 10 ** (math.floor(math.log10(abs(x))) - 1)
        s = max(round(s), 1) if whole else s
        pair = [snap(k, x - s, whole), snap(k, x + s, whole)]
        if x in pair:
            skipped.append(f"{k} {x:g}: a step lands back on it")
            continue
        for v in pair:
            vals.append(base | {k: v} | {f: v for f, lead in LINKED.items() if lead == k})
        moves.append((k, x, *pair))
    run = lambda sd, vs, lab_: {c["id"]: c for c in sweep({"list": vs, "economies": n, "seed": sd, "save": False, "label": lab_,
                                                            "bot": spec.get("bot", "passive")}, pool, cur)["cands"]}
    got = run(seed, vals, f"Key map of {len(moves)} keys ({n} economies)")
    val = lambda c: [p["value"] for p in c["parts"]]
    b = val(got[0])
    seeds = [b] + [val(run(sd, [base], f"Key map noise, seed {sd}")[0]) for sd in (seed + 1, seed + 2)]
    noise = [None if None in col else round(statistics.pstdev(col), 4) for col in zip(*seeds)]
    years = (engine.defaults().get("inputs") or {}).get("years", engine.INPUTS["years"][0])
    d = lambda c: [None if v is None or w is None else round(v - w, 4) for v, w in zip(val(c), b)]
    out = {"made": time.strftime("%Y-%m-%d"), "n": n, "years": years, "seed": seed,
           "targets": [{"id": i, "metric": t["metric"], "label": f"{engine.METRICS[t['metric']][0]} ({t['who']})",
                        "lo": t["lo"], "hi": t["hi"], "base": None if b[i] is None else round(b[i], 4)} for i, t in enumerate(ts)],
           "keys": [{"key": k, "base": x, "down": lo, "up": hi, "effect_down": d(got[1 + 2 * i]), "effect_up": d(got[2 + 2 * i]),
                     "score_down": got[1 + 2 * i]["score"], "score_up": got[2 + 2 * i]["score"]} for i, (k, x, lo, hi) in enumerate(moves)],
           "base_score": got[0]["score"], "noise": noise, "skipped": skipped}
    write(HERE / "keymap.json", json.dumps(out, indent=1))
    return out


def keymap_table(m):
    """Per key, the three targets it moves most in band widths (beyond noise), and whether a move pulls one target in while
    pushing another out."""
    T, noise, lines = m["targets"], m["noise"], []
    off = lambda t, v: max(t["lo"] - v, v - t["hi"], 0)
    for k in m["keys"]:
        size, conflict = {}, []
        for side in ("down", "up"):
            toward = away = False
            for t, e, z in zip(T, k["effect_" + side], noise):
                w = max(t["hi"] - t["lo"], 1e-9)
                if e is None or t["base"] is None or abs(e) <= max(z or 0, 0.02 * w):  # some metrics barely move with the seed
                    continue
                size[t["id"]] = max(size.get(t["id"], 0), abs(e) / w)
                gap = off(t, t["base"] + e) - off(t, t["base"])
                toward, away = toward or gap < 0, away or gap > 0
            if toward and away:
                conflict.append(side)
        top = sorted(size, key=size.get, reverse=True)[:3]
        lines.append(f"{k['key']:<22} {k['base']:g} -> {k['down']:g}/{k['up']:g}  score {k['score_down']:.2f}/{k['score_up']:.2f}  " +
                     ("; ".join(f"{T[i]['label']} {size[i]:.2f}" for i in top) or "nothing beyond noise") +
                     (f"  CONFLICT ({'/'.join(conflict)})" if conflict else ""))
    return f"Baseline score {m['base_score']:.2f}; moves in band widths, beyond the baseline's seed spread\n" + "\n".join(lines)


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


_HIST = {}  # run file -> (its mtime, the targets' mtime, its record): the kept runs are read once, then only the new ones


def history():
    """The kept runs, oldest first, for the dashboard: what each was for (note), what it tried (label, and tried: each key
    it moved as [was, lowest, highest]), and every candidate's value on each target as the targets are now, best first.
    The base candidate is the numbers the run started from; only the best of the others carries its changes.
    The note may carry the goal and the targets it is after: "name | goal sentence | metric:who, metric:who"."""
    ts, tm, out = rows(targets()), TARGETS.stat().st_mtime if TARGETS.exists() else 0, []
    for p in sorted(RUNS.glob("*.json")):
        try:
            m = p.stat().st_mtime
            if _HIST.get(p, (0, 0))[:2] != (m, tm):
                r, cands, tried = json.loads(p.read_text(encoding="utf-8")), [], {}
                for c in r["cands"]:
                    score, parts = engine.score(c["metrics"], ts)
                    ch = c.get("changed") or {}
                    for k, (was, new) in ch.items():
                        lo, hi = tried.get(k, (was, new, new))[1:]
                        tried[k] = [was, min(lo, new), max(hi, new)]
                    cands.append({"id": c["id"], "score": round(score, 3), "base": c["id"] == 0 and not ch, "changed": ch,
                                  "v": [None if q["value"] is None else round(q["value"], 3) for q in parts]})
                cands.sort(key=lambda c: c["score"])
                best = next((c for c in cands if not c["base"]), None)
                for c in cands:
                    if c is not best:
                        del c["changed"]
                _HIST[p] = (m, tm, {"id": p.stem, **{k: r.get(k) for k in ("label", "note", "time", "secs", "economies", "years", "seed", "rungs")},
                                    "dropped": len(r.get("dropped") or ()), "tried": tried, "cands": cands})
            out.append(_HIST[p][2])
        except (OSError, ValueError, KeyError):
            continue
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
    spec, opts, i = {"fixed": {}, "vary": {}, "keys": []}, {"--n": "economies", "--seed": "seed", "--cands": "candidates", "--note": "note",
                                                          "--bot": "bot", "--rung": "rung"}, 0
    while i < len(argv):
        a = argv[i]
        if a == "--halving":
            spec["halving"], i = True, i + 1
            continue
        if a in KEYS:  # a bare key: the map's
            spec["keys"].append(a)
            i += 1
            continue
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
    assert cmd in ("check", "sweep", "map"), "check, sweep or map"
    if cmd == "check":
        spec["vary"] = {}
    with mp.get_context("spawn").Pool(CORES) as pool:
        if cmd == "map":
            print(keymap_table(keymap(spec, pool)))
        else:
            print(report((halving if spec.get("halving") else sweep)(spec, pool)))
