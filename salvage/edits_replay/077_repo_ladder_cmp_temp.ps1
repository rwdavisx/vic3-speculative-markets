$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import json, subprocess, sys
from pathlib import Path
R=Path(r"G:\GameDev\speculative-markets"); p=R/"tools/tuning.json"; raw=p.read_bytes(); s=Path(sys.argv[0]).parent
try:
    for lad in ([3,10,11,12],[3,8,10,12]):
        d=json.loads(raw); d["LEV_LADDER"]=lad; p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8",newline="\n")
        for k in "12":
            for f in ("mania12.py","r12b.py"):
                a=[sys.executable,"-B",str(s/f)]+(["one"] if f=="mania12.py" else [])+["800",k,str(s/"l0.json")]
                print(lad,k,subprocess.run(a,capture_output=True,text=True,cwd=R).stdout.strip().splitlines()[-1][:330],flush=True)
finally: p.write_bytes(raw)
'@ | Set-Content -Encoding utf8 $s\lad.py; py -3 -B $s\lad.py; Select-String -Path tools\tuning.json -Pattern 'LEV_LADDER' -Context 0,5 | % { $_.Line; $_.Context.PostContext }
