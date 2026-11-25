$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import json; from pathlib import Path
p = Path(r"G:\GameDev\speculative-markets\tools\tuning.json"); d = json.loads(p.read_text(encoding="utf-8"))
d.update({"LEV_CRUNCH_FADE":0.35,"LEV_RECORD_PAST":2,"BUST_PER_HYPE":1.5})
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\t4.py; py -3 -B $s\t4.py
py -3 -B tools\tuner\engine.py 2>&1 | select -Last 1
py -3 -B $s\mania12.py one 800 4 $s\l0.json | select -Skip 2
"HV"; $env:HV='78,0.25,1'; py -3 -B $s\mania12_h.py one 600 1 $s\l0.json | select -Skip 2; $env:HV=$null
"victoria3: " + (@(Get-Process victoria3 -ErrorAction SilentlyContinue).Count)
$env:SPEC_MOD_OUT='build_scratch\rc_1.3.1'
py -3 -B tools/generate.py 2>&1 | select -Last 3; "gen $LASTEXITCODE"
py -3 -B tools/check.py 2>&1 | select -Last 3; "check $LASTEXITCODE"
py -3 -B tools/leverage.py 2>&1 | select -Last 1
git status --short mod | select -First 5
Select-String -Path build_scratch\rc_1.3.1\localization\english\*.yml -Pattern 'for each month past|Banks lend|banks lend' | % { $_.Line.Trim().Substring(0,[Math]::Min(300,$_.Line.Trim().Length)) }
Test-Path build_scratch\rc_1.3.1\.metadata\built_against.txt
