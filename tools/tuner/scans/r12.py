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
        print(json.dumps(moves[c["id"]])); 
        for b in ("careful","hold6","run10","run12","blind12","reckless","ai","passive"):
            if b in M: print(f"    {b:9s} growth {G[b]:.2f} (vs careful {G[b]-G['careful']:+.2f}, vs 6 {G[b]-G['hold6']:+.2f}) panics {g(b,'panics_per_century'):.1f} mania {g(b,'mania_pct'):.1f} lev8% {g(b,'lev8_pct'):.1f} run-ups {g(b,'runs10_per_century'):.2f} out {g(b,'runs10_out_pct'):.0f}% beaten {g(b,'beaten_pct'):.0f}%")
if __name__ == "__main__":
    mp.freeze_support(); main(int(sys.argv[1]), int(sys.argv[2]), json.loads(open(sys.argv[3]).read()))