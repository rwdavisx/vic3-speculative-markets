$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuner\engine.py"); t = p.read_bytes().decode("utf-8"); nl = "\r\n" if "\r\n" in t else "\n"
a = 'self.build = pm * K["PANIC_BUILD"] - self.bite * K["LEV_CRUNCH_BUILD"] + self.record_held * lv.RECORD_STEP'
i = t.index(a); j = t.index(nl, i); print(t[i:j+200])
assert t.count(a) == 1
t = t[:i] + 'self.build = np.maximum(' + t[i:j][len('self.build = '):].rstrip() + ', -1)  # construction cannot go below none' + t[j:]
p.write_bytes(t.encode("utf-8"))
'@ | Set-Content -Encoding utf8 $s\clamp.py
py -3 -B $s\clamp.py
@'
import sys, json, os, subprocess, itertools
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(LEV_CRUNCH_BUILD=cb, BUST_PER_HYPE=b, LEV_CRUNCH_FADE=cf, AI_LEV_SCALE=a) for cb, b, cf, a in itertools.product((.06,.08,.1),(2.0,2.25),(.3,.35),(1.0,1.2))]
json.dump(moves, open(S/"l9.json","w"))
tf = S/"tune.json"; json.dump(T|{"LEV_LADDER":[3,9,11,12],"LOOSE_CREDIT":2.5,"FIN_BOOM_BASE":2.1,"LEV_RECORD_PAST":2,"LEV_PANIC_SPAN":20}, open(tf,"w"))
r = subprocess.run([sys.executable,"-B",str(S/"r12b.py"),"300","1",str(S/"l9.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
print(r.stdout, r.stderr[-800:] if r.returncode else "")
'@ | Set-Content -Encoding utf8 $s\scan9.py
py -3 -B $s\scan9.py
