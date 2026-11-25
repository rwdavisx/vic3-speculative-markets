$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
import json
R = Path(r"G:\GameDev\speculative-markets\tools\tuner")
p = R/"engine.py"; t = p.read_text(encoding="utf-8"); 
a = "SHARE_SD, PRICE_W_EXP, PRICE_GDP_EXP, PRICE_GDP_AT, PRICE_SPREAD = 1.1, 0.192, 0.168, 1e7, 0.55\nPRICE_NOISE, PRICE_COMMON, PRICE_START, PRICE_START_MONTHS = 0.25, 0.065, 0.9, 6"
assert t.count(a) == 1
b = "# 2026-11-25: PRICE_SPREAD 0.55 -> 0.75 and PRICE_COMMON 0.065 -> 0.4, refit with price_sd and the roughness to two games'\n# confidence and boom endings (beta.3 and 1.2.2, 1836-66): endings fall together and harder than the measured prices give.\n" + a.replace("0.55\n", "0.75\n").replace("0.065", "0.4")
p.write_text(t.replace(a, b), encoding="utf-8", newline="\n")
q = R/"inputs.json"; d = json.loads(q.read_text(encoding="utf-8"))
new = {"rough_sd": [0.5, 0.5], "rough_months": [6, 6], "rough_skew": 0, "price_sd": [0.032, 0.032]}
d["source"]["game_refit_20261125"] = {"logs": ["runs/sweep_beta3/beta3_01", "runs/sweep_rc122/rc122_01"], "was": {k: d["inputs"].get(k) for k in new} | {"PRICE_SPREAD": 0.55, "PRICE_COMMON": 0.065},
  "why": "the recentred falls-only roughness pushed confidence up to +2 a month, so simulated Mania was 3x the game's"}
d["inputs"].update(new); q.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\apply.py
py -3 -B $s\apply.py; git diff --stat tools/tuner; Get-Content $s\mania_h2.py; Get-Content tools\tuner\lab.py -TotalCount 60 | % { $_.Substring(0,[Math]::Min(220,$_.Length)) }; Get-Content tools\tuner\targets.json | select -First 60
