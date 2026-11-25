$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"; Get-Content "C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\tasks\bhol5s358.output"; $r="G:\GameDev\speculative-markets\runs\sweep_beta3\beta3_01"; Get-ChildItem $r | Select-Object Name,Length; py -3 -B "$sp\cmp_game.py" "$r\telemetry.log" | Select-Object -First 7; "--- runtime errors naming our files"; Get-Content "$r\error.log" | Where-Object { $_ -match "spec_" -and $_ -notmatch "jomini_effect.cpp:114[04]|is orphaned" } | ForEach-Object { $_.Substring(0,[Math]::Min(220,$_.Length)) } | Select-Object -First 10
$code=@'
import sys
from pathlib import Path
import numpy as np
R = Path(r"G:\GameDev\speculative-markets"); sys.path[:0] = [str(R/"tools"), str(R/"tools/tuner")]
import windows as w
def spells(A):
    # leverage run-ups to 8+ : how they end
    up = out = pan = 0; nm = []; mp = 0
    for lev, conf, p in zip(A["lev"], A["conf"], np.nan_to_num(A["panic"]) > 0):
        on = False
        for k in range(len(lev)):
            if not on and lev[k] >= 8: on = True; up += 1
            if on and p[k]: pan += 1; on = False
            elif on and lev[k] < 5: out += 1; on = False
        k = 0
        while k < len(conf):
            if conf[k] >= 80:
                s = k
                while k < len(conf) and conf[k] >= 80: k += 1
                nm.append(k - s); mp += bool(p[k:k + 24].any())
            else: k += 1
    return f"run-ups to 8+: {up}, down to 5 without panic {out}, panic {pan}; Manias {len(nm)}, mean length {np.mean(nm) if nm else 0:.1f} mo, panic within 24 mo {mp}"
for f in sys.argv[1:]:
    seen = w.parse(Path(f), 1836, 360, w.KEYS)
    rows = {t: r for t, r in w.top(seen, 0, 360).items() if len(r) >= 288}
    A = w.arrays(rows, 360); c = A["conf"]
    print(f[-50:], spells(A)); print("  conf pctiles 5/50/90/95/99:", np.round(np.nanpercentile(c, [5, 50, 90, 95, 99]), 1), "share 70+:", round(float(np.nanmean(c >= 70) * 100), 1), "boom mean:", np.round([np.nanmean(A["boom"][:, i:i + 120]) for i in (0, 120, 240)], 3), "braw:", np.round([np.nanmean(A["braw"][:, i:i + 120]) for i in (0, 120, 240)], 3))
'@; [IO.File]::WriteAllText("$sp\spells.py",$code); py -3 -B "$sp\spells.py" "$r\telemetry.log" G:\GameDev\speculative-markets\runs\sweep_rc122\rc122_01\telemetry.log
