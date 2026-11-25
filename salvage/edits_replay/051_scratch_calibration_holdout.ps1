$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
New-Item -ItemType Directory -Force $s\old130 | Out-Null
git archive --format=zip -o $s\old130.zip HEAD tools; Expand-Archive -Force $s\old130.zip $s\old130
@'
import sys, pickle, json
from pathlib import Path
import cal
import numpy as np, multiprocessing as mp
OLD = Path(__file__).parent / "old130"
def simold(a):
    import sys; sys.path[:0] = [str(OLD/"tools"), str(OLD/"tools/tuner")]
    import engine; assert "old130" in engine.__file__, engine.__file__
    return cal.sim(a)
if __name__ == "__main__":
    import windows as w
    num = w.fastsim.num
    F = ["conf","boom","braw","crash","foreign","turmoil","restrain","d_crash","d_debt","d_mood","d_drift","d_growth","d_business","d_world","d_tight","lev","nboom","end1","end2","end3","panic"]
    f = cal.R / "runs/sweep_rc122/rc122_01/telemetry.log"
    seen = w.parse(f, 1836, 360); rows = {t: r for t, r in w.top(seen, 0, 360).items() if len(r) >= 288}
    A = {k: np.full((len(rows), 360), np.nan) for k in F}
    for i, r in enumerate(rows.values()):
        for m, d in r.items():
            for k in F: A[k][i, m] = num(d, k)
    g = cal.stats(A, True)
    new = lambda sd, ps: {"inp": {"rough_sd": [sd,sd], "rough_months": [6,6], "rough_skew": 0, "price_sd": [ps]*2}, "mod": {"PRICE_COMMON": .4, "PRICE_SPREAD": .9}}
    named = {"old calibration": {}, "r0 p.030": new(0,.03), "r.5 p.030": new(.5,.03), "r0 p.0316": new(0,.0316), "r.8 p.03": new(.8,.03)}
    with mp.get_context("spawn").Pool(len(named), maxtasksperchild=1) as pool: res = pool.map(simold, list(named.values()), chunksize=1); 
    with mp.get_context("spawn").Pool(len(named), maxtasksperchild=1) as pool: res2 = pool.map(cal.sim, list(named.values()), chunksize=1)
    G, tags, _ = pickle.load(open(Path(__file__).with_name("decomp.pkl"), "rb")); g2 = cal.stats(G, True)
    for k in g:
        print(f"{k:14s} HOLDOUT 1.2.2 game {g[k]}   || beta3 game {g2[k]}")
        for nm, r, r2 in zip(named, res, res2): print(f"{'':14s} {nm:18s} {r[k]}   || {r2[k]}")
'@ | Set-Content -Encoding utf8 $s\hold.py
py -3 -B $s\hold.py
