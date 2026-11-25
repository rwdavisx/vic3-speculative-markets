$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"
$code=@'
import sys, json
from pathlib import Path
import numpy as np
R = Path(r"G:\GameDev\speculative-markets"); sys.path[:0] = [str(R/"tools"), str(R/"tools/tuner")]
import windows as w, engine
w.WINDOWS.update({"36-46": (0, 10), "46-56": (10, 10), "56-66": (20, 10), "36-66": (0, 30)})
ERAS = ["36-46", "46-56", "56-66", "36-66"]
mean = lambda m: {k: round(float(np.nanmean(v)), 2) for k, v in m.items()}
def game(f, name):
    seen = w.parse(f, 1836, 30 * 12, w.KEYS); last = max(max(s) for s in seen.values() if s)
    print(f"## {name}: {len(seen)} tags, last month {1836 + last // 12}")
    for e in ERAS:
        a, y = w.WINDOWS[e]
        if a * 12 + y * 12 * .8 > last: continue
        rows = {t: r for t, r in w.top(seen, a * 12, y * 12).items() if len(r) >= y * 12 * .8}
        A = w.arrays(rows, y * 12); m = mean(w.game_side(A)); lev = A["lev"]
        mt = list(rows)[:8]
        m["lev8%"] = round(float(np.nanmean(lev >= 8) * 100), 2); m["lev_max"] = round(float(np.nanmax(lev)), 1)
        m["per100y"] = round(m["panics_per_decade"] * 10, 1)
        m["mania_countries"] = int((np.nansum(A["conf"] >= 80, 1) > 0).sum()); m["n"] = len(rows)
        st = A["stance"]; u, c = np.unique(st[~np.isnan(st)], return_counts=True); m["stance"] = {str(int(x)): round(100 * k / c.sum()) for x, k in zip(u, c)}
        print(e, json.dumps(m))
        if e == "36-66": 
            top8 = mt; print("top8 mania%:", {t: round(float(np.nanmean(A["conf"][i] >= 80) * 100), 1) for i, t in enumerate(list(rows)[:8])}, "lev:", {t: round(float(np.nanmean(lev[i])), 1) for i, t in enumerate(list(rows)[:8])})
game(Path(sys.argv[1]), sys.argv[1])
if len(sys.argv) > 2: game(Path(sys.argv[2]), sys.argv[2])
T = w.tuner_side(ERAS)
print("## simulator AI")
for e in ERAS:
    m = mean(T[e][0]); m["per100y"] = round(m["panics_per_decade"] * 10, 1); print(e, json.dumps(m))
'@; [IO.File]::WriteAllText("$sp\cmp_game.py",$code)
Get-Content runs\sweep_rc122\rc122_01\meta.json; Get-Content runs\sweep_exp2\con_up_a_01\meta.json; ""; Select-String -Path runs\sweep_rc122\rc122_01\telemetry.log -Pattern "stance=" | Select-Object -First 1 | ForEach-Object { $_.Line.Substring(0,[Math]::Min(700,$_.Line.Length)) }
py -3 -B "$sp\cmp_game.py" G:\GameDev\speculative-markets\runs\windows_120\campaign\telemetry.log
