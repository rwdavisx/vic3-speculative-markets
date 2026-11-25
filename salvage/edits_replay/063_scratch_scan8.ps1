$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import sys, json, os, subprocess, itertools, re
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(LEV_PANIC_SPAN=sp, LEV_CRUNCH_BUILD=cb, LEV_RECORD_LOSS=l, BUST_PER_HYPE=b, LEV_CRUNCH_FADE=cf) for sp, cb, l, b, cf in itertools.product((20,25),(.06,.1,.15),(.3,.5),(2.0,2.5),(.35,.25))]
json.dump(moves, open(S/"l8.json","w"))
tf = S/"tund.json"; json.dump(T|{"LEV_LADDER":[3,9,11,12],"LOOSE_CREDIT":2.5,"FIN_BOOM_BASE":2.1,"LEV_RECORD_PAST":2}, open(tf,"w"))
r = subprocess.run([sys.executable,"-B",str(S/"r12b.py"),"250","1",str(S/"l8.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
if r.returncode: print(r.stderr[-800:])
rows = []
for line in r.stdout.splitlines():
    g = lambda k: float(re.search(rf"{k} ([-+\d.]+)", line)[1])
    bad = max(0, g("passive")-g("careful")+.03)*3 + max(0, g("reckless")-.05)*2 + max(0, .18-g("12-C"))*2 + max(0, .02-g("12-6"))*3 + max(0, g("pan12")-6)*.05 + max(0, 60-g("out"))*.01 + max(0, g("ai")-.55)
    rows.append((bad, line))
for b, l in sorted(rows)[:10]: print(round(b,3), l)
'@ | Set-Content -Encoding utf8 $s\scan8.py
py -3 -B $s\scan8.py
