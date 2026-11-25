cd G:\GameDev\speculative-markets
$f="$pwd\tools\concepts.py"; $s=[IO.File]::ReadAllText($f); $old='A little is paid back from the '; $i=$s.IndexOf($old); $s.Substring($i,110)
$m=[regex]::Match($s,'A little is paid back from the (.{0,60}?)each month\.'); $m.Value
$s=$s.Replace($m.Value,$m.Value.TrimEnd('.')+', and much more under $concept_spec_credit_policy_tight$.'); [IO.File]::WriteAllText($f,$s)
Select-String tools\generate.py -Pattern '^FIN_BOOM = ' -Context 0,4 | Out-String
$cl=@'
An early test of 1.3.1, for players who like to run high leverage. Stable stays on 1.3.

[list]
[*]Tight credit now gets you out of debt. Each month under it, 10% of Outstanding Credit is paid back from the investment pool (was 0.95%). The pool never pays out more than it holds, and loans it cannot pay stay owed.
[*]Booms lift Market Confidence more, so Mania comes around more often. Their size before finance technologies is 1.5 (was 1).
[*]High leverage lifts the confidence a panic starts at by up to 50 points (was 55).
[/list]

In our simulations, AI countries panic 3.7 times a century (was 5.5). A country that never uses its credit policy spends 3% of its months in Mania (was 1%).

Saves from 1.3 carry on. New text is English only for now. The Morgenroete, Tech & Res and Better Politics Mod patches are still built for 1.3, so test this beta without them.
'@
[IO.File]::WriteAllText("$pwd\beta\changelog_1.3.1-beta.1.bbcode",$cl.Replace("`r`n","`n"))
$d="$pwd\beta\workshop_description.bbcode"; $s=[IO.File]::ReadAllText($d); $nl= if($s.Contains("`r`n")){"`r`n"}else{"`n"}
$o="[b]1.3.0-beta.1[/b] matches stable 1.3. See the change notes."
$s=$s.Replace($o,"[b]1.3.1-beta.1[/b] tests a way out of high leverage: Tight credit pays loans off about ten times faster, and Mania comes around more often. New text is English only, and the compatibility patches are still built for 1.3. See the change notes.").Replace("[h2]Previous beta updates[/h2]$nl","[h2]Previous beta updates[/h2]$nl$o$nl$nl")
$s=$s.Replace("patches are rebuilt for 1.3, which this beta matches.","patches are built for 1.3, so test 1.3.1-beta.1 without them.")
[IO.File]::WriteAllText($d,$s); (Get-Item $d).Length
$env:SPEC_MOD_OUT="$pwd\build_scratch\rc_1.3.1"; py -3 -B tools/generate.py 2>&1 | Select-Object -Last 1; py -3 -B tools/check.py 2>&1 | Select-Object -Last 2
git diff --stat -- mod tools beta | Select-Object -Last 9
py -3 -B beta/build.py --source build_scratch\rc_1.3.1 --out beta\candidate_131 --revision 1 2>&1 | Select-Object -Last 8
Get-ChildItem beta\candidate_131\releases | select Name,Length
Select-String beta\candidate_131\mod\common\script_values\spec_values.txt -Pattern 'spec_credit_payoff'
Select-String beta\candidate_131\mod\localization\english\spec_markets_l_english.yml -Pattern '^ concept_spec_outstanding_credit_desc' | % { $_.Line.Substring($_.Line.Length-230)}
