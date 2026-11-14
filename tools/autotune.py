"""Tunes the AI by short forks from shared mid-game saves: each value of each knob is built on the side (never into
mod/), played a few years from the same saves as the baseline, and scored by how much GDP it adds against that
baseline on the same saves, so the differences between games cancel out.

The score is the mean change in log GDP of the countries alive at the end of both, in %: world (sum) and the typical
country (trimmed mean change of the 40 largest at the start). se is the spread of the per-save changes; a change under 2 se is noise.

Usage: py -3 tools/autotune.py --name r1 --years 1 --games 2 --saves base115_mod_1_1865,... --jobs 10
  --base tuned.json --knob AI_TIGHT=72,76,84 --knob AI_LOOSE=28,40
Results: runs/sweep_<name>/result.json and a table."""
import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import sweep

TOOLS = Path(__file__).resolve().parent


def build(label, values):
    out = sweep.WORK / f"b_{label}"
    tune = sweep.WORK / f"t_{label}.json"
    tune.write_text(json.dumps(values), encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOLS / "generate.py"), "--log"], cwd=TOOLS, capture_output=True, text=True,
                       env={**os.environ, "SPEC_MOD_OUT": str(out), "SPEC_TUNING": str(tune)})
    if r.returncode:
        raise SystemExit(f"{label}: {r.stderr[-400:]}")
    return out


def score(games, base_games):
    """mean world and top 40 log change against the baseline's mean on one save, in %"""
    def stats(gs):
        rs = [sweep.latest(g) for g in gs if g["status"] == "done" and g["tags"]]
        return rs
    a, b = stats(games), stats(base_games)
    if not a or not b:
        return None
    wa = statistics.mean(math.log(sum(r.values())) for r in a)
    wb = statistics.mean(math.log(sum(r.values())) for r in b)
    # the 40 largest at the START: picked at the end, the baseline's lucky countries make every other arm look worse
    tags = next(g for g in base_games if g["tags"])["tags"]
    top = sorted((t for t, c in tags.items() if c), key=lambda t: -tags[t][min(tags[t])])[:40]
    def mean_log(rs, t):
        xs = [math.log(r[t]) for r in rs if t in r]
        return statistics.mean(xs) if xs else None
    d = sorted(mean_log(a, t) - mean_log(b, t) for t in top if mean_log(a, t) is not None and mean_log(b, t) is not None)
    return 100 * (wa - wb), 100 * statistics.mean(d[4:-4])   # trimmed: one country's war can't swing it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--years", type=int, default=1)
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--saves", required=True, help="names in the saves folder, without .v3")
    ap.add_argument("--base", help="json of values every arm starts from")
    ap.add_argument("--knob", action="append", default=[], help="NAME=v1,v2 or NAME=json;json")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--plan", help="json file: {knob: [values]}")
    a = ap.parse_args()
    base = json.loads(Path(a.base).read_text(encoding="utf-8")) if a.base else {}
    saves = [sweep.SAVES / f"{s}.v3" for s in a.saves.split(",")]
    variants = {"base": base}
    for k in a.knob:
        name, vals = k.split("=", 1)
        for v in vals.split(";" if ";" in vals else ","):
            variants[f"{name}-{v}".replace(":", "").replace("{", "").replace("}", "").replace('"', "").replace(" ", "").replace(",", "_")] = {**base, name: json.loads(v)}
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else {}
    # whole arms, several settings at once
    for label, values in plan.pop("arms", {}).items():
        variants[label] = {**base, **values}
    for name, vals in plan.items():
        for v in vals:
            label = re.sub(r"[^\w.-]+", "_", f"{name}-{json.dumps(v)}").strip("_")
            variants[label] = {**base, name: v}
    arms = {}
    for label, values in variants.items():
        folder = build(f"{a.name}_{label}", values)
        for i, s in enumerate(saves):
            arms[f"{label}__{i}"] = (folder, s)
    t = time.time()
    res = sweep.run(a.name, arms, a.games, a.years, a.jobs, a.timeout, lambda s: None)
    rows = []
    for label in variants:
        per = [score(res[f"{label}__{i}"], res[f"base__{i}"]) for i in range(len(saves))]
        per = [p for p in per if p]
        bad = sum(g["status"] != "done" for i in range(len(saves)) for g in res[f"{label}__{i}"])
        errs = max((g["our_errors"] for i in range(len(saves)) for g in res[f"{label}__{i}"]), default=0)
        n = len(per)
        w = [p[0] for p in per]; c = [p[1] for p in per]
        rows.append({"arm": label, "world": statistics.mean(w) if w else None, "se": statistics.stdev(w) / math.sqrt(n) if n > 1 else None,
                     "top40": statistics.mean(c) if c else None, "top_se": statistics.stdev(c) / math.sqrt(n) if n > 1 else None,
                     "per_save": w, "per_save_top": c, "failed": bad, "our_errors": errs})
    rows.sort(key=lambda r: -(r["top40"] or -99))
    print(f"{len(saves)} saves x {a.games} games, {a.years} years, wall {round((time.time() - t) / 60, 1)} min")
    print(f"{'arm':38}{'world %':>9}{'se':>7}{'top40 %':>9}{'se':>7}  failed errors")
    f = lambda x: "" if x is None else f"{x:.2f}"
    for r in rows:
        print(f"{r['arm']:38}{f(r['world']):>9}{f(r['se']):>7}{f(r['top40']):>9}{f(r['top_se']):>7}  {r['failed']} {r['our_errors']}")
    (sweep.ROOT / "runs" / f"sweep_{a.name}" / "result.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
