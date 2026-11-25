$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
$py=@'
from cal import *
import math
def score(g, r):
    t = 0
    for k, wt in (("m75",1),("conf",0),("boom",1),("pos%",.5),("crash",1),("hit%",1),("size",2),("p1/p.1",1),("ends/yr",.5),("panics/100y",2),("othersd",1),("lev",1),("lev8%",.5),("dsd",1),("mania",1)):
        a, b = np.atleast_1d(g[k]), np.atleast_1d(r[k])
        if k in ("m75","mania","boom","crash","pos%"): a, b = a.mean(keepdims=True), b.mean(keepdims=True)
        if k == "ends/yr": a, b = a[:2], b[:2]
        t += wt * np.mean(np.log((np.abs(b)+.05)/(np.abs(a)+.05))**2)
    t += sum(((x-y)/3)**2 for x, y in zip(g["pct10/50/90/99"], r["pct10/50/90/99"])) / 4
    return t
if __name__ == "__main__":
    G, tags, _ = pickle.load(open(Path(__file__).with_name("decomp.pkl"), "rb")); g = stats(G, True)
    named = {}
    for sd in (0, .8, 1.2):
      for com in (.065, .25, .4):
        for sp in (.55, .75, .9, 1.1):
          for ps in (.8, .9, 1.0):
            named[f"r{sd} c{com} s{sp} p{ps}"] = {"inp": {"rough_sd": [sd,sd], "rough_months": [6,6], "rough_skew": 0, "price_sd": [.0316*ps]*2}, "mod": {"PRICE_COMMON": com, "PRICE_SPREAD": sp}, "n": 400}
    with mp.get_context("spawn").Pool(20, maxtasksperchild=1) as pool: res = pool.map(sim, list(named.values()), chunksize=1)
    out = sorted((score(g, r), nm) for nm, r in zip(named, res)); R_ = dict(zip(named, res))
    for x, nm in out[:8]:
        r = R_[nm]; print(round(x,3), nm, {k: r[k] for k in ("mania","m75","pct10/50/90/99","boom","pos%","crash","hit%","size","p1/p.1","ends/yr","panics/100y","othersd","lev","lev8%","dsd","nboom")})
    print("game", {k: g[k] for k in ("mania","m75","pct10/50/90/99","boom","pos%","crash","hit%","size","p1/p.1","ends/yr","panics/100y","othersd","lev","lev8%","dsd","nboom")})
'@
$py | Set-Content -Encoding utf8 $s\cal2.py
py -3 -B $s\cal2.py
