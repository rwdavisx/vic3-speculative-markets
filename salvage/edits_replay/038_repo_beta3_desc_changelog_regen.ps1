$u=New-Object Text.UTF8Encoding $false
$f="G:\GameDev\speculative-markets\beta\workshop_description.bbcode"; $t=[IO.File]::ReadAllText($f); [IO.File]::WriteAllText($f,$t.Replace("1.3.1-beta.2","1.3.1-beta.3"),$u)
$c=@'
More Mania. Everything else is as in 1.3.1-beta.2, and stable stays on 1.3.

[list]
[*]Booms lift Market Confidence more: their size before finance technologies is now 2 (was 1.75 in beta.2 and 1 in 1.3).
[*]The finance technologies add as much to booms as before, so the percentages they show are lower.
[*]Under High Market Volatility, Speculative Excess builds from 78 confidence (was 75 in beta.2 and 70 in 1.3), so the bigger booms do not make that rule too harsh.
[/list]

In our simulations, a country left alone now spends about 8% of months in Mania (was 5%), AI countries about 5% (was 2.5%), and a country running leverage up to 10 months about 6% (was under 3%). Panics stay about as common. The real game may come in a little under these numbers.

Saves from 1.3 and beta.2 carry on. New text is English only for now. The Morgenroete, Tech & Res and Better Politics Mod patches are still built for 1.3, so test this beta without them.
'@
[IO.File]::WriteAllText("G:\GameDev\speculative-markets\beta\changelog_1.3.1-beta.3.bbcode",$c.Replace("`r`n","`n"),$u)
$env:SPEC_MOD_OUT="build_scratch\rc_1.3.1"; py -3 -B tools/generate.py 2>&1 | Select-Object -Last 4; "gen $LASTEXITCODE"; py -3 -B tools/check.py 2>&1 | Select-Object -Last 4; "check $LASTEXITCODE"; Remove-Item Env:SPEC_MOD_OUT
Get-ChildItem build_scratch\rc_1.3.1\.metadata | Select-Object Name
py -3 -B tools/tuner/engine.py 2>&1 | Select-Object -Last 2
py -3 -B beta/build.py --help | Select-Object -First 14
