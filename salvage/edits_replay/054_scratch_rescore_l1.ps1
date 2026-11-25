$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
import json, subprocess, sys
sys.path[:0] = [r"G:\GameDev\speculative-markets\tools", r"G:\GameDev\speculative-markets\tools\tuner"]
import lab
cur = lab.current()
old = json.loads(subprocess.run(["git","show","HEAD:tools/tuning.json"],capture_output=True,text=True,cwd=r"G:\GameDev\speculative-markets").stdout)
new = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
diff = {k: (old.get(k), new.get(k)) for k in set(old)|set(new) if old.get(k) != new.get(k)}
print(diff, file=sys.stderr); print([k for k in cur if "BOOM" in k], {k: cur[k] for k in cur if "BOOM" in k}, file=sys.stderr)
D = {"FIN_BOOM_BASE":1.0,"CREDIT_RUNOFF_TIGHT":None,"LEV_PANIC_SPAN":55,"LEV_INCOME_FLOOR":0.009,"LEV_RECORD_GAIN":0.01,"LEV_CRUNCH_BUILD":0.05}
st = {k: v[0] for k, v in diff.items() if v[0] is not None and k in cur}
print("stable", st, file=sys.stderr)
L = [{}, st, {"FIN_BOOM_BASE":1.75}, {"FIN_BOOM_BASE":2.25}, {"FIN_BOOM_BASE":2.5}, {"FIN_BOOM_BASE":2.75}, {"FIN_BOOM_BASE":3.0}]
print(json.dumps(L))
'@ | Set-Content -Encoding utf8 $s\mk.py
$j = py -3 -B $s\mk.py; [IO.File]::WriteAllText("$s\l1.json", ($j -join "`n"))
Get-Content $s\l1.json; Select-String -Path $s\mania.py -Pattern 'argv|environ' 
py -3 -B $s\mania.py one 1000 1 $s\l1.json
