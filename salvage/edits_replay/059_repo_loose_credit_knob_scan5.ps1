$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
(Get-Content tools\generate.py -Raw).Contains('STANCE_CREDIT = {"tight": 0, "loose": 1.6}')
py -3 -B -c "
p=r'G:\GameDev\speculative-markets\tools\generate.py'
t=open(p,encoding='utf-8',newline='').read()
a='STANCE_CREDIT = {\"tight\": 0, \"loose\": 1.6}'
assert t.count(a)==1
open(p,'w',encoding='utf-8',newline='').write(t.replace(a,'STANCE_CREDIT = {\"tight\": 0, \"loose\": tuning.get(\"LOOSE_CREDIT\", 1.6)}'))
"
@'
import sys, json, os, subprocess
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(FIN_BOOM_BASE=2.1, LEV_PANIC_SPAN=sp, LEV_REWARD_CURVE=c, LEV_REWARD_TP_FULL=f, LEV_REWARD_INV_FULL=round(f/4,3)) for sp in (20,25,30) for c, f in ((1,.24),(1.5,.24),(1.5,.3),(2,.3))]
json.dump(moves, open(S/"l5.json","w"))
for lad in ([3,8,10,12],[3,9,11,12],[3,10,12,12]):
    for loose in (1.6,2.0,2.5):
        tf = S/f"tun_{lad[1]}_{lad[2]}_{loose}.json"; json.dump(T|{"LEV_LADDER":lad,"LOOSE_CREDIT":loose,"FIN_BOOM_BASE":2.1}, open(tf,"w"))
        r = subprocess.run([sys.executable,"-B",str(S/"r12.py"),"300","1",str(S/"l5.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
        print("#### ladder", lad, "loose", loose, r.stderr[-300:] if r.returncode else ""); print(r.stdout, flush=True)
'@ | Set-Content -Encoding utf8 $s\scan5.py
py -3 -B $s\scan5.py *> $s\scan5.txt
