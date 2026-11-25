$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"; $G=Get-Content tools\generate.py -Encoding utf8; $G[100..146]; Select-String -Path tools\*.py -Pattern "overheat sooner|VOLATILITY" | ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(330,$_.Line.Trim().Length)))" }
[IO.File]::WriteAllText("$sp\h.json",'[{"FIN_BOOM_BASE":2.0}]')
$t=[IO.File]::ReadAllText("$sp\mania_h.py").Replace('HCFG =','import os
_h, _p, _b = (float(x) for x in os.environ["HV"].split(","))
engine.g.VOLATILITY["heightened"].update(heat=_h, per=_p, boom=_b)
HCFG ='); [IO.File]::WriteAllText("$sp\mania_h2.py",$t)
foreach($hv in "75,0.25,1","80,0.25,1","78,0.25,1","80,0.3,1","80,0.35,1"){ $env:HV=$hv; "== heat,per,boom $hv"; py -3 -B "$sp\mania_h2.py" x 1000 9004 "$sp\h.json" | Select-Object -Skip 2 }
