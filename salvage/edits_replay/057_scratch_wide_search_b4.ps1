$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import sys, json, random, multiprocessing as mp
sys.path[:0] = [r"G:\GameDev\speculative-markets\tools", r"G:\GameDev\speculative-markets\tools\tuner"]
import lab
def num(x):
    if isinstance(x, dict): x = x.get("mean", next(iter(x.values())))
    return float("nan") if x is None else x
OPT = dict(FIN_BOOM_BASE=[2.05,2.1,2.15,2.2], LEV_PANIC_SPAN=[25,30,30,35], BUST_PER_HYPE=[2.0,2.25,2.5], LEV_RECORD_GAIN=[.02,.025,.03], LEV_RECORD_LOSS=[.3,.4,.5],
  LEV_CRUNCH_BUILD=[.06,.08,.1], LEV_CRUNCH_FADE=[.3,.35], LEV_RECORD_BUILD=[.0167,.02,.025], CREDIT_RUNOFF_TIGHT=[.1,.15], LEV_INCOME_FLOOR=[.006,.007], CORRECTION_PER_HYPE=[1.0,1.25], CLAWBACK=[.6,.75])
def main(n, seed, cnt, fixed):
    cur = lab.current(); base = lab.candidates(cur, {}, {}, 1, 1)[0]
    if fixed: moves = fixed
    else:
        rng = random.Random(7); moves = [{}, dict(FIN_BOOM_BASE=2.1, LEV_PANIC_SPAN=30)]
        while len(moves) < cnt:
            m = dict(FIN_BOOM_BASE=rng.choice(OPT["FIN_BOOM_BASE"]), LEV_PANIC_SPAN=rng.choice(OPT["LEV_PANIC_SPAN"]), BUST_PER_HYPE=rng.choice(OPT["BUST_PER_HYPE"]))
            for k in rng.sample([k for k in OPT if k not in m], rng.choice([1,2,3,4])): m[k] = rng.choice(OPT[k])
            m = {k: v for k, v in m.items() if v != cur[k] }
            if m not in moves: moves.append(m)
    with mp.get_context("spawn").Pool(lab.CORES) as pool:
        r = lab.sweep({"list": [base | m for m in moves], "economies": n, "seed": seed, "save": False, "label": "b4"}, pool, cur)
    rows = []
    for c in r["cands"]:
        M = c["metrics"]; g = lambda b, k: num(M[b].get(k)); G = {b: g(b, "growth_core") for b in M}
        off = sum(abs(p["value"]-p["aim"])/(max(p["hi"]-p["lo"],1e-9)/2) if "aim" in p else 0 for p in c["parts"])
        rows.append((sum(p["in"] for p in c["parts"]), off, moves[c["id"]], G, g, [f"{p['metric']}({p['who']})={p['value']:.2f}" for p in c["parts"] if not p["in"]]))
    for ins, off, m, G, g, out in sorted(rows, key=lambda x: (-(x[0]), x[1]))[:16 if not fixed else 99]:
        print(f"{ins}/30 off {off:.1f} {json.dumps(m)}\n     mania {g('passive','mania_pct'):.1f}/{g('run10','mania_pct'):.1f}/{g('ai','mania_pct'):.1f} panics P {g('passive','panics_per_century'):.1f} C {g('careful','panics_per_century'):.1f} 6 {g('hold6','panics_per_century'):.1f} 10 {g('run10','panics_per_century'):.1f} AI {g('ai','panics_per_century'):.1f} | growth P C 6 10 bl rk AI " + " ".join(f"{G[b]:.2f}" for b in ("passive","careful","hold6","run10","blind10","reckless","ai")) + f" | 10-C {G['run10']-G['careful']:+.2f} 10-6 {G['run10']-G['hold6']:+.2f} ups {g('run10','runs10_per_century'):.1f} out {g('run10','runs10_out_pct'):.0f} beat {g('run10','beaten_pct'):.0f} | {' '.join(out)}")
if __name__ == "__main__":
    mp.freeze_support(); main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), json.loads(open(sys.argv[4]).read()) if len(sys.argv) > 4 else None)
'@ | Set-Content -Encoding utf8 $s\b4.py
py -3 -B $s\b4.py 500 1 80
