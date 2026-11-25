import sys, json, multiprocessing as mp
_T = __import__("pathlib").Path(__file__).resolve().parents[2]; sys.path[:0] = [str(_T), str(_T / "tuner")]
import lab, engine, numpy as np
def num(x):
    if isinstance(x, dict): x = x.get("mean", next(iter(x.values())))
    return float("nan") if x is None else x
def main(n, seed, moves):
    cur = lab.current(); base = lab.candidates(cur, {}, {}, 1, 1)[0]
    ts = lab.targets(); B = ["run12", "blind12", "run10", "hold6", "careful", "reckless", "ai", "passive"]
    ts = ts + [dict(metric="growth_core", who=b, aim=0, lo=-9, hi=9, weight=0.0001, why="") for b in B]
    import os
    lab.targets = lambda: ts
    with mp.get_context("spawn").Pool(lab.CORES) as pool:
        r = lab.sweep({"list": [base | m for m in moves], "economies": n, "seed": seed, "save": False, "label": "r12", "targets": ts}, pool, cur)
    for c in sorted(r["cands"], key=lambda c: c["id"]):
        M = c["metrics"]; g = lambda b, k: num(M[b].get(k)) if b in M else float("nan"); G = {b: g(b, "growth_core") for b in M}
        print(json.dumps(moves[c["id"]]).replace("LEV_",""), "| " + " ".join(f"{b} {G[b]:.2f}" for b in ("careful","hold6","run10","run12","blind12","reckless","ai","passive")) + f" | 12-C {G['run12']-G['careful']:+.2f} 12-6 {G['run12']-G['hold6']:+.2f} pan12 {g('run12','panics_per_century'):.1f} ups {g('run12','runs10_per_century'):.2f} out {g('run12','runs10_out_pct'):.0f} beat {g('run12','beaten_pct'):.0f} lev8 {g('run12','lev8_pct'):.1f} | AI pan {g('ai','panics_per_century'):.1f} mania P {g('passive','mania_pct'):.1f} 12 {g('run12','mania_pct'):.1f} AI {g('ai','mania_pct'):.1f}")
if __name__ == "__main__":
    mp.freeze_support(); main(int(sys.argv[1]), int(sys.argv[2]), json.loads(open(sys.argv[3]).read()))
