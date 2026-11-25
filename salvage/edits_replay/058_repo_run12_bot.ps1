$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuner\engine.py"); t = p.read_text(encoding="utf-8")
def sub(a, b):
    global t
    assert t.count(a) == 1, (t.count(a), a); t = t.replace(a, b)
sub('''    # the same run, watching nothing but leverage
''', '''    # up to 12 months, the ruin line (11.8: lending stops at 12), as the user asked for on 2026-11-25; the limit reaches 12 only
    # with the last LADDER_TECHS, so early run-ups stop at 8 or 10
    "run12": dict(plan=dict(hi=11.8, lo=4, m_in=8, m_out=12, loose_lev=11.5, loose_m=11), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    "blind12": dict(plan=dict(hi=11.8, lo=4, loose_lev=11.5, loose_m=-99), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    # the same run, watching nothing but leverage
''')
sub("        up = ~self.run10 & (self.lev_prev < 9.5) & (lev4 >= 9.5) & ~start\n",
    "        run_at = self.pol[\"plan\"][\"hi\"] - 0.5 if self.pol.get(\"plan\", {}).get(\"hi\", 0) > 10 else 9.5\n        up = ~self.run10 & (self.lev_prev < run_at) & (lev4 >= run_at) & ~start\n")
sub("# a run-up: leverage crosses 9.5 months;", "# a run-up: leverage crosses 9.5 months (run12: 11.3);")
p.write_text(t, encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\bot.py
py -3 -B $s\bot.py
@'
import sys, json, multiprocessing as mp
sys.path[:0] = [r"G:\GameDev\speculative-markets\tools", r"G:\GameDev\speculative-markets\tools\tuner"]
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
'@ | Set-Content -Encoding utf8 $s\r12.py
[IO.File]::WriteAllText("$s\l4.json",'[{},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":25},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":20},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":15}]')
$sw=[Diagnostics.Stopwatch]::StartNew(); py -3 -B $s\r12.py 500 1 $s\l4.json; $sw.Elapsed.TotalSeconds
