$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
[IO.File]::WriteAllText("$s\l3.json",'[{},{"FIN_BOOM_BASE":2.1},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30,"CONF_CRASH_MAX":25}]')
foreach($k in 2,3){ "seed $k"; py -3 -B $s\mania.py one 1000 $k $s\l3.json | select -Skip 2 }
@'
import cal
from cal import *
if __name__ == "__main__":
    named = {"2.0": {"n":1500}, "2.1": {"K": {"FIN_BOOM_BASE": 2.1},"n":1500}, "2.1 s30": {"K": {"FIN_BOOM_BASE": 2.1, "LEV_PANIC_SPAN": 30},"n":1500}}
    with mp.get_context("spawn").Pool(3) as pool: res = pool.map(cal.sim, list(named.values()), chunksize=1)
    for nm, r in zip(named, res): print(nm, {k: r[k] for k in ("mania","m75","pct10/50/90/99","panics/100y","lev","lev8%")})
'@ | Set-Content -Encoding utf8 $s\era.py
py -3 -B $s\era.py; py -3 -B tools\tuner\engine.py 2>&1 | select -Last 4; Get-Process victoria3 -ErrorAction SilentlyContinue | select Id
