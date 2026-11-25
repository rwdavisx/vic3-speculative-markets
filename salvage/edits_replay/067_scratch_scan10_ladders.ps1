$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import sys, json, os, subprocess, itertools
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(LEV_CRUNCH_BUILD=.05, LEV_CRUNCH_FADE=cf, LEV_RECORD_LOSS=l, LEV_PANIC_SPAN=sp) for cf, l, sp in itertools.product((.1,.15,.2,.25),(.3,.5),(20,25))]
json.dump(moves, open(S/"l10.json","w"))
for lad in ([3,10,11,12],[3,8,10,12]):
    tf = S/"tunf.json"; json.dump(T|{"LEV_LADDER":lad}, open(tf,"w"))
    r = subprocess.run([sys.executable,"-B",str(S/"r12b.py"),"300","1",str(S/"l10.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
    print("## ladder", lad); print(r.stdout, r.stderr[-800:] if r.returncode else "", flush=True)
'@ | Set-Content -Encoding utf8 $s\scan10.py
py -3 -B $s\scan10.py
