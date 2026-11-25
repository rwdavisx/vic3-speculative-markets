$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
import json
R = Path(r"G:\GameDev\speculative-markets\tools")
p = R/"leverage.py"; raw = p.read_bytes(); crlf = b"\r\n" in raw; t = raw.decode("utf-8").replace("\r\n", "\n")
a = "    f' slowly toward #P {RECORD_BUILD * 100:+g}%#! construction efficiency for each month of [concept_spec_leverage].'\n"
assert t.count(a) == 1
b = ("    f' slowly toward #P {RECORD_BUILD * 100:+.2g}%#! construction efficiency for each month of [concept_spec_leverage]'\n"
     "    + (f', and #P {RECORD_BUILD * (1 + RECORD_PAST) * 100:+.2g}%#! for each month past #v {RECORD_FROM:g}#!.' if RECORD_PAST else '.') +\n")
t = t.replace(a, b); p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
p = R/"tuning.json"; d = json.loads(p.read_text(encoding="utf-8")); d.pop("AI_LEV_SCALE", None); d["AI_LEV_LIMIT"] = {"-1": 8, "0": 9.5, "1": 11.5}
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\txt.py
py -3 -B $s\txt.py; py -3 -B -c "import sys;sys.path[:0]=['tools'];import leverage as l;print(l.AI_LIMIT, l.AI_LIMIT_BASE);print([x for x in l.RECORD_LOC.split(chr(10)) if 'desc' in x])"
[IO.File]::WriteAllText("$s\l0.json",'[{}]')
foreach($k in 1,2,3){ "seed $k"; py -3 -B $s\r12b.py 1000 $k $s\l0.json }
(Get-Content $s\mania.py -Raw).Replace("'run10'","'run12'").Replace('"blind10"','"blind12"').Replace('"run10"','"run12"') | Set-Content -Encoding utf8 $s\mania12.py
(Get-Content $s\mania_h2.py -Raw).Replace("'run10'","'run12'").Replace('"blind10"','"blind12"').Replace('"run10"','"run12"') | Set-Content -Encoding utf8 $s\mania12_h.py
"targets"; foreach($k in 1,2){ py -3 -B $s\mania12.py one 1000 $k $s\l0.json | select -Skip 2 }
"High volatility now (heat 78, per .25, boom 1)"; Select-String tools\generate.py -Pattern '"heightened":|VOLATILITY =' | % Line
$env:HV='78,0.25,1'; py -3 -B $s\mania12_h.py one 600 1 $s\l0.json | select -Skip 2
$env:HV='80,0.25,1'; py -3 -B $s\mania12_h.py one 600 1 $s\l0.json | select -Skip 2
