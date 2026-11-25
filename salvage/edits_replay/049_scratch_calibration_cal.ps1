$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import sys, pickle, itertools, json
from pathlib import Path
import numpy as np, multiprocessing as mp, os
R = Path(r"G:\GameDev\speculative-markets"); sys.path[:0] = [str(R/"tools"), str(R/"tools/tuner")]
DEC = [slice(0,120), slice(120,240), slice(240,360)]
def stats(A, game):
    c = A["conf"] if game else A["conf"] - A["d_caution"]  # as the log has it: before the Mania event lands
    cr = A["d_crash"] if game else A["crash"] * np.concatenate([np.full((len(c),1),50.), A["conf"][:,:-1]],1) / 50
    f = lambda x: [round(float(np.nanmean(x[:, d])), 2) for d in DEC]
    o = {}
    o["mania"] = [round(x, 2) for x in f((c >= 80) * 100.)] ; o["m75"] = f((c >= 75) * 100.); o["conf"] = f(c)
    o["pct10/50/90/99"] = [round(float(np.nanpercentile(c, p)), 1) for p in (10,50,90,99)]
    o["boom"] = f(A["boom"]); o["cap%"] = f((A["braw"] >= 3) * 100.); o["pos%"] = f((A["braw"] > 0) * 100.); o["nboom"] = f(A["nboom"])
    hit = cr < -.1; o["crash"] = f(cr); o["hit%"] = round(float(np.nanmean(hit[np.isfinite(cr)]) * 100), 1); o["size"] = round(float(np.nanmean(cr[hit])), 2)
    o["p1/p.1"] = [round(float(np.nanpercentile(cr, p)), 1) for p in (1, .1)]
    o["ends/yr"] = [round(float(np.nanmean(A[f"end{k}"]) * 12), 2) for k in (1,2,3)]
    p = np.nan_to_num(A["panic"]) > 0; st = (p[:,1:] & ~p[:,:-1])
    n = np.isfinite(c[:,1:]).sum(); o["panics/100y"] = round(float(st.sum() / n * 1200), 2); o["inpanic%"] = round(float(p.mean()*100), 2)
    keys = ("foreign","turmoil","restrain","d_debt","d_mood","d_growth","d_business","d_world","d_tight") + (() if game else ("d_rough",))
    o["othersd"] = round(float(sum(np.nan_to_num(A[k]) for k in keys).std()), 2)
    o["lev"] = round(float(np.nanmean(A["lev"])), 2); o["lev8%"] = round(float(np.nanmean(A["lev"] >= 8) * 100), 2)
    cc = c.copy(); x = np.diff(cc, axis=1); o["dsd"] = [round(float(np.nanstd(x[(cc[:,:-1]>=a)&(cc[:,:-1]<a+10)])),2) for a in (50,60,70)]
    return o
def sim(a):
    import windows as w, engine
    for k, v in a.get("mod", {}).items(): setattr(engine, k, v)
    cfg = engine.defaults(); cfg["inputs"]["years"] = 31; cfg["inputs"].update(a.get("inp", {})); engine.SNAP = 1
    K = engine.current(); 
    if engine.lv.LADDER[0] == engine.lv.SAFE: K["LADDER"] = (K["LEV_SAFE"], *engine.lv.LADDER[1:])
    K.update(a.get("K", {}))
    n = a.get("n", 600); e = w.Recorded(K, cfg, "ai", n, a.get("seed", w.TUNER_SEED), False, n); e.rec = []; e.run()
    S = {k: np.array([x[k] for x in e.kept]).T[:, :360].astype(float) for k in e.kept[0]}
    S["lev"] = np.array([s[2] for s in e.snap]).T[:, :360]; S["nboom"] = np.array([s[6] for s in e.snap]).T[:, :360].astype(float)
    S["d_debt"], S["d_business"] = S["debt"], S["business"]
    return stats(S, False)
def go(named):
    G, tags, _ = pickle.load(open(Path(__file__).with_name("decomp.pkl"), "rb"))
    g = stats(G, True)
    with mp.get_context("spawn").Pool(min(len(named), 20)) as pool: res = pool.map(sim, list(named.values()), chunksize=1)
    for k in g: 
        print(f"{k:15s} game {g[k]}")
        for nm, r in zip(named, res): print(f"{'':15s} {nm:22s} {r[k]}")
if __name__ == "__main__":
    z = {"rough_sd": [0,0], "rough_skew": 0}
    go({"now": {}, "rough0": {"inp": z}, "rough0 common.25": {"inp": z, "mod": {"PRICE_COMMON": .25}}, "rough0 common.5": {"inp": z, "mod": {"PRICE_COMMON": .5}},
        "rough0 spread.9": {"inp": z, "mod": {"PRICE_SPREAD": .9}}, "rough0 sd x1.25": {"inp": {**z, "price_sd": [.0395,.0395]}},
        "rough0 months14": {"inp": {**z, "price_months": [14,14]}}, "rough0 c.25 m10": {"inp": {**z, "price_months": [10,10]}, "mod": {"PRICE_COMMON": .25}}})
'@ | Set-Content -Encoding utf8 $s\cal.py
py -3 -B $s\cal.py
