cd G:\GameDev\_claude_scratch\v130\infographic
$s=[IO.File]::ReadAllText("$pwd\build.py").Replace('"Tight at 4 months"','"leverage to 4"').Replace('"Tight at 6 months"','"leverage to 6"'); [IO.File]::WriteAllText("$pwd\build.py",$s); py -3 -B build.py 2>&1 | Select-Object -Last 1
