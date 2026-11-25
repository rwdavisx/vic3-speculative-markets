$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import sys, pickle
import cal, hold, cal2
from cal import *
if __name__ == "__main__":
    import windows as w
    num = w.fastsim.num
    F = ["conf","boom","braw","crash","foreign","turmoil","restrain","d_crash","d_debt","d_mood","d_drift","d_growth","d_business","d_world","d_tight","lev","nboom","end1","end2","end3","panic"]
    seen = w.parse(cal.R / "runs/sweep_rc122/rc122_01/telemetry.log", 1836, 360); rows = {t: r for t, r in w.top(seen, 0, 360).items() if len(r) >= 288}
    A = {k: np.full((len(rows), 360), np.nan) for k in F}
    for i, r in enumerate(rows.values()):
        for m, d in r.items():
            for k in F: A[k][i, m] = num(d, k)
    gh = stats(A, True); G, tags, _ = pickle.load(open(Path(__file__).with_name("decomp.pkl"), "rb")); gb = stats(G, True)
    named = {}
    for com in (.3, .4, .5):
      for sp in (.45, .55, .65, .75):
        for ps in (.027, .029, .031, .033):
          named[f"c{com} s{sp} p{ps}"] = {"inp": {"rough_sd": [.5,.5], "rough_months": [6,6], "rough_skew": 0, "price_sd": [ps]*2}, "mod": {"PRICE_COMMON": com, "PRICE_SPREAD": sp}, "n": 400}
    with mp.get_context("spawn").Pool(20, maxtasksperchild=1) as pool: rb = pool.map(cal.sim, list(named.values()), chunksize=1)
    with mp.get_context("spawn").Pool(20, maxtasksperchild=1) as pool: rh = pool.map(hold.simold, list(named.values()), chunksize=1)
    out = sorted((cal2.score(gb, b) + cal2.score(gh, h), nm) for nm, b, h in zip(named, rb, rh)); Rb, Rh = dict(zip(named, rb)), dict(zip(named, rh))
    ks = ("mania","m75","pct10/50/90/99","boom","pos%","crash","hit%","size","p1/p.1","ends/yr","panics/100y","lev","dsd")
    for x, nm in out[:6]:
        print(round(x,3), nm); print("   b3 ", {k: Rb[nm][k] for k in ks}); print("   122", {k: Rh[nm][k] for k in ks})
    print("game b3 ", {k: gb[k] for k in ks}); print("game 122", {k: gh[k] for k in ks})
'@ | Set-Content -Encoding utf8 $s\cal3.py
py -3 -B $s\cal3.py
