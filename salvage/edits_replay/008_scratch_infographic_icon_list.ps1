cd G:\GameDev\_claude_scratch\v130\infographic
$s=[IO.File]::ReadAllText("$pwd\build.py").Replace('state_steady mod_loose")','state_steady mod_loose event_mania")'); [IO.File]::WriteAllText("$pwd\build.py",$s); py -3 -B build.py 2>&1 | Select-Object -Last 1; gci icons | select Name,LastWriteTime | ? Name -match mania; (gi does_it_pay.png).LastWriteTime; Get-Date
