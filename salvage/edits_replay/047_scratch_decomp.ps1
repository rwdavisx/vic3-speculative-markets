$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import sys
from pathlib import Path
import numpy as np
R = Path(r"G:\GameDev\speculative-markets"); sys.path[:0] = [str(R/"tools"), str(R/"tools/tuner")]
import windows as w, engine, pickle
num = w.fastsim.num
F = ["conf","boom","braw","crash","foreign","turmoil","restrain","d_crash","d_debt","d_mood","d_drift","d_growth","d_business","d_world","d_tight","d_burst","d_drop","d_rescue","d_caution","d_warend","d_limit","d_rival","stance","lev","wsum","nboom","end1","end2","end3","heat","panic","fin","steady","levers","mood"]
def game(f):
    seen = w.parse(Path(f), 1836, 360); rows = {t: r for t, r in w.top(seen, 0, 360).items() if len(r) >= 288}
    out = {k: np.full((len(rows), 360), np.nan) for k in F}
    for i, r in enumerate(rows.values()):
        for m, d in r.items():
            for k in F: out[k][i, m] = num(d, k)
    return out, list(rows)
G, tags = game(R / "runs/sweep_beta3/beta3_01/telemetry.log")
KEEP = {}
o = w.Recorded.run
def run(self):
    o(self); 
    for k in self.kept[0]: KEEP[k] = np.array([x[k] for x in self.kept]).T[:, :360].astype(float)
    KEEP["lev"] = np.array([s[2] for s in self.snap]).T[:, :360]; KEEP["stance"] = np.array([s[2] for s in self.rec]).T[:, :360].astype(float); KEEP["nboom"] = np.array([s[6] for s in self.snap]).T[:, :360].astype(float)
w.Recorded.run = run
w.tuner_side(["1836"])
S = KEEP
S["d_debt"] = S["debt"]; S["d_business"] = S["business"]
S["d_crash"] = S["crash"] * np.nan
pickle.dump((G, tags, S), open(sys.argv[1], "wb"))
def dec(A, name):
    c0 = A["conf"][:, :-1]; print("##", name)
    keys = [k for k in ("boom","braw","d_crash" if name=="game" else "crash","foreign","turmoil","restrain","d_debt","d_mood","d_drift","d_growth","d_business","d_world","d_rough","d_tight","d_burst","d_drop","d_rescue","d_caution","d_warend","d_limit","d_rival","stance","lev","wsum","nboom","levers") if k in A]
    print("band n ", " ".join(keys))
    for lo, hi in ((0,40),(40,50),(50,60),(60,65),(65,70),(70,75),(75,80),(80,85),(85,101)):
        m = (c0 >= lo) & (c0 < hi); n = m.sum()
        if not n: continue
        dc = (A["conf"][:, 1:] - c0)[m]
        print(lo, f"{n/np.isfinite(c0).sum()*100:.2f}%", f"dconf {np.nanmean(dc):.2f} sd {np.nanstd(dc):.2f}", " ".join(f"{k}={np.nanmean(A[k][:, 1:][m]):.2f}" for k in keys))
dec(G, "game"); dec(S, "sim")
'@ | Set-Content -Encoding utf8 $s\decomp.py
py -3 -B $s\decomp.py $s\decomp.pkl
