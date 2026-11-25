$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import json; from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuning.json"); d = json.loads(p.read_text(encoding="utf-8"))
d.update({"LEV_LADDER":[3,10,11,12],"LEV_CRUNCH_BUILD":0.05,"LEV_CRUNCH_FADE":0.3,"LEV_RECORD_PAST":2.5,"LEV_PANIC_SPAN":25,"BUST_PER_HYPE":1.75,"LEV_INCOME_FLOOR":0.006})
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n"); print({k: d[k] for k in ("FIN_BOOM_BASE","LEV_LADDER","LOOSE_CREDIT","AI_LEV_LIMIT")})
'@ | Set-Content -Encoding utf8 $s\t3.py; py -3 -B $s\t3.py
foreach($k in 1,2,3){ "seed $k"; py -3 -B $s\mania12.py one 1000 $k $s\l0.json | select -Skip 2; py -3 -B $s\r12b.py 1000 $k $s\l0.json }
"High volatility 78 / .25"; $env:HV='78,0.25,1'; py -3 -B $s\mania12_h.py one 600 1 $s\l0.json | select -Skip 2
$env:HV=$null; py -3 -B tools\tuner\engine.py 2>&1 | select -Last 1; Get-Process victoria3 -ErrorAction SilentlyContinue | select Id,StartTime
