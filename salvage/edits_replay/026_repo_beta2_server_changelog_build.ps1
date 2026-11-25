cd G:\GameDev\speculative-markets
$u=New-Object Text.UTF8Encoding($false)
$f="$pwd\tools\tuner\server.py"; $s=[IO.File]::ReadAllText($f); $a='"summary": engine.summarize(e),'; if(([regex]::Matches($s,[regex]::Escape($a))).Count -eq 1){[IO.File]::WriteAllText($f,$s.Replace($a,'"summary": {k: v for k, v in engine.summarize(e).items() if k != "_core"},'),$u)}else{'SERVER?'}
py -3 -B -c "import ast;ast.parse(open(r'tools/tuner/server.py',encoding='utf-8').read())"
$cl=@'
A test of 1.3.1, for players who like to run high leverage. Stable stays on 1.3.

[b]High leverage[/b]
[list]
[*]Tight credit now gets you out of debt. Each month under it, 10% of Outstanding Credit is paid back from the investment pool (was 0.95%). The pool never pays out more than it holds, and loans it cannot pay stay owed.
[*]High leverage lifts the confidence a panic starts at by up to 35 points (was 55).
[*]A country's income counts as at least 0.7% of its GDP a month when working out leverage (was 0.9%).
[*]Sound Credit grows twice as fast.
[*]Each point of Bad Debts now cuts construction efficiency by 6% (was 5%).
[/list]

[b]Booms[/b]
[list]
[*]Booms lift Market Confidence more, so Mania comes around more often. Their size before finance technologies is 1.75 (was 1).
[*]Under High Market Volatility, booms are no longer 10% larger on top of that, and Speculative Excess builds from 75 confidence (was 70).
[/list]

[b]AI countries[/b]
[list]
[*]AI countries now use leverage. They go Loose while their confidence is far above the Panic Threshold, and Tight as it nears or while they have Bad Debts. Before, they went Tight above 80 confidence. Bold countries and those with Industrialists in government run closer to the edge, Cautious ones and those with Intelligentsia in government keep further from it.
[*]They still go Tight at a leverage limit, 6.5, 8 or 9.5 months by temperament (was 5, 8 and 9.5).
[/list]

In our simulations, running leverage up to 10 months and getting out now beats careful play in about four worlds in five, and about a third of those runs end in a panic. Holding a steady 6 still earns a little more.

Saves from 1.3 carry on. New text is English only for now. The Morgenroete, Tech & Res and Better Politics Mod patches are still built for 1.3, so test this beta without them.
'@
[IO.File]::WriteAllText("$pwd\beta\changelog_1.3.1-beta.2.bbcode",$cl.Replace("`r`n","`n"),$u)
$d="$pwd\beta\workshop_description.bbcode"; $s=[IO.File]::ReadAllText($d)
$m=[regex]::Match($s,'\[b\]1\.3\.1-beta\.1\[/b\] tests[^\r\n]*')
$s=$s.Replace($m.Value,'[b]1.3.1-beta.2[/b] tests riding high leverage: Tight credit pays loans off about ten times faster, the Panic Threshold rises less, Mania comes around more often, and AI countries use leverage too. New text is English only, and the compatibility patches are still built for 1.3. See the change notes.').Replace('so test 1.3.1-beta.1 without them','so test 1.3.1-beta.2 without them')
[IO.File]::WriteAllText($d,$s,$u); (Get-Item $d).Length
Get-ChildItem build_scratch\rc_1.3.1\.metadata; Test-Path build_scratch\rc_1.3.1\thumbnail.png
if(Test-Path build_scratch\rc_1.3.1\.metadata\built_against.txt){Move-Item -Force build_scratch\rc_1.3.1\.metadata\built_against.txt build_scratch\built_against_rc_1.3.1.txt}
py -3 -B beta/build.py --source build_scratch\rc_1.3.1 --out beta\release_131 --revision 2 2>&1 | Select-Object -Last 3
$z="beta\release_131\releases\Speculative_Markets_Beta_1.3.1-beta.2.zip"; (Get-Item $z).Length; (Get-FileHash $z).Hash
py -3 -B tools/stage_workshop.py beta $z 2>&1 | Select-Object -Last 3
$v=Get-Process victoria3 -ErrorAction SilentlyContinue; if(!$v){py -3 build_scratch\sync_live.py build_scratch\rc_1.3.1 build_scratch\rivals_live | Select -First 12}else{"victoria3 running"}
(Get-Content mod\.metadata\metadata.json -Raw | ConvertFrom-Json).version; git status --short
