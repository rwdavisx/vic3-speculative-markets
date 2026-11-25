import sys, json, multiprocessing as mp
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import lab, engine
lists = {
 "one": [dict(), dict(FIN_BOOM_BASE=2.0), dict(FIN_BOOM_BASE=2.25), dict(FIN_BOOM_BASE=2.5), dict(CONF_PER_HOT=7.0), dict(CONF_PER_HOT=8.0),
   dict(CONF_START=55), dict(CONF_RECOVER=0.15), dict(CONF_RECOVER=0.1), dict(MOOD_KEEP=0.96), dict(MOOD_KEEP=0.97), dict(MOOD_SHOCK=1.0),
   dict(HEAT_FROM=85), dict(BURST_PER_HEAT=0.15), dict(CONF_PER_CRASH_HYPE=6), dict(CONF_PER_CRASH_HYPE=5), dict(CONF_CRASH_MAX=30),
   dict(BUST_PER_HYPE=2.0), dict(MANIA=75), dict(EXP_PER_MONTH=0.05), dict(LAX_PULL=0.75), dict(HEAT_COOL=0.97)],
}
HCFG = engine.defaults(); HCFG["inputs"]["heightened"] = 1
def num(x):
    if isinstance(x, dict): x = x.get("mean", x.get("avg", next(iter(x.values()))))
    return float("nan") if x is None else x
def main(name, n, seed, extra):
    cur = lab.current()
    moves = extra or lists[name]
    base = lab.candidates(cur, {}, {}, 1, 1)[0]
    vals = [base | m for m in moves]
    with mp.get_context("spawn").Pool(lab.CORES) as pool:
        r = lab.sweep({"list": vals, "economies": n, "seed": seed, "save": False, "cfg": HCFG, "label": "mania scan"}, pool, cur)
    print("mania P/C/6/10/AI | m2p | panics P C 10 AI | growth P C 6 10 bl rk AI | 10-C 10-6 ups out beat | losses | in/30")
    for c in sorted(r["cands"], key=lambda c: c["id"]):
        M = c["metrics"]; g = lambda b, k: num(M[b].get(k))
        G = {b: g(b, "growth_core") for b in M}
        if c["id"] == 0: print({k: v for k, v in M["passive"].items() if k in ("mania_pct", "growth_core", "mania_to_panic_pct")})
        ins = sum(p["in"] for p in c["parts"]); out = [f"{p['metric']}({p['who']})={p['value']:.2f}" for p in c["parts"] if not p["in"]]
        print(f"{json.dumps(moves[c['id']]):42s} {g('passive','mania_pct'):.1f} {g('careful','mania_pct'):.1f} {g('hold6','mania_pct'):.1f} {g('run10','mania_pct'):.1f} {g('ai','mania_pct'):.1f} | {g('passive','mania_to_panic_pct'):.0f} | "
              f"{g('passive','panics_per_century'):.1f} {g('careful','panics_per_century'):.1f} {g('run10','panics_per_century'):.1f} {g('ai','panics_per_century'):.1f} | "
              + " ".join(f"{G[b]:.2f}" for b in ("passive","careful","hold6","run10","blind10","reckless","ai"))
              + f" | {G['run10']-G['careful']:+.2f} {G['run10']-G['hold6']:+.2f} {g('run10','runs10_per_century'):.1f} {g('run10','runs10_out_pct'):.0f} {g('run10','beaten_pct'):.0f} | {ins}/30 {' '.join(out)}")
if __name__ == "__main__":
    mp.freeze_support()
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), json.loads(open(sys.argv[4]).read()) if len(sys.argv) > 4 else None)