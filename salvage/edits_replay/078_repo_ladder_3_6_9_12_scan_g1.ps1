$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import json; from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuning.json"); d = json.loads(p.read_text(encoding="utf-8"))
d["LEV_LADDER"]=[3,6,9,12]
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
L=[{}]
for sp in (25,30,35):
    for past in (2,3):
        for bust in (1.5,2):
            if (sp,past,bust)!=(25,2,1.5): L.append({"LEV_PANIC_SPAN":sp,"LEV_RECORD_PAST":past,"BUST_PER_HYPE":bust})
L += [{"LEV_CRUNCH_BUILD":0.06},{"LEV_INCOME_FLOOR":0.005},{"LEV_INCOME_FLOOR":0.007}]
Path(r"C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\g1.json").write_text(json.dumps(L))
'@ | Set-Content -Encoding utf8 $s\g.py; py -3 -B $s\g.py
py -3 -B $s\r12b.py 800 2 $s\g1.json
"---"; py -3 -B $s\mania12.py one 800 2 $s\g1.json | ? { $_ -match '/30' } | % { $_.Substring([Math]::Max(0,$_.IndexOf('/30')-3)) }
Get-Content tools\tuner\targets.json | Select-String 'lo|hi|metric|bot' | select -First 3
