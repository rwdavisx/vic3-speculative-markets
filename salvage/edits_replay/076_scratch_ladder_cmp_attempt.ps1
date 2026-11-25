$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
'[{},{"LEV_LADDER":[3,8,10,12]},{"LEV_LADDER":[3,6,9,12]}]' | Set-Content -Encoding ascii $s\lad.json
foreach($k in 1,2){ "seed $k"; py -3 -B $s\mania12.py one 800 $k $s\lad.json | select -Skip 2 }
Select-String -Path tools\tuner\engine.py -Pattern 'LADDER' | % { "$($_.LineNumber) $($_.Line.Trim())" }
