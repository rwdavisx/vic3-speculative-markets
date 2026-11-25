$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import json; from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuning.json"); d = json.loads(p.read_text(encoding="utf-8"))
d.update({"LEV_LADDER":[3,10,11,12],"LEV_CRUNCH_BUILD":0.05,"LEV_CRUNCH_FADE":0.2,"LEV_RECORD_PAST":1.5})
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\t2.py; py -3 -B $s\t2.py
[IO.File]::WriteAllText("$s\l11.json",'[{},{"LEV_RECORD_PAST":1},{"LEV_RECORD_PAST":1,"LEV_CRUNCH_FADE":0.15},{"LEV_RECORD_PAST":1,"LEV_PANIC_SPAN":25},{"LEV_RECORD_PAST":1.5,"LEV_CRUNCH_FADE":0.15},{"LEV_RECORD_PAST":1.5,"LEV_PANIC_SPAN":25},{"LEV_RECORD_PAST":2,"LEV_PANIC_SPAN":25},{"LEV_RECORD_PAST":2,"LEV_PANIC_SPAN":25,"BUST_PER_HYPE":1.75},{"LEV_RECORD_PAST":1.5,"LEV_PANIC_SPAN":25,"BUST_PER_HYPE":1.75},{"LEV_RECORD_PAST":1.5,"LEV_PANIC_SPAN":25,"LEV_INCOME_FLOOR":0.006}]')
py -3 -B $s\mania12.py one 600 1 $s\l11.json | select -Skip 2
