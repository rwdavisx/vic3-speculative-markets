$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
from pathlib import Path
Path("beta/changelog_1.3.1-beta.4.bbcode").write_text("""Running leverage up to 12 months now pays. Everything else is as in 1.3.1-beta.3, and stable stays on 1.3.

[b]Reaching 12 months[/b]
[list]
[*]Loose credit lends 150% more (was 60%).
[*]Central Banking raises the Lending Limit to 10 months (was 8). Investment Banks and International Exchange Standards add 1 month each (was 2), so the top is still 12.
[*]A country's income counts as at least 0.6% of its GDP a month when working out leverage (was 0.7%).
[/list]

[b]Reward[/b]
[list]
[*]Sound Credit grows toward 5% construction efficiency for each month of leverage past 6 (was 1.7%). The first 6 months still give 1.7% each.
[/list]

[b]Risk[/b]
[list]
[*]High leverage lifts the confidence a panic starts at by up to 25 points (was 35), so at 12 months a panic starts below 50 (was 60).
[*]A boom that ends in a Bust costs 1.5 times its size in confidence (was 2.5).
[*]Each point of Bad Debts cuts construction efficiency by 5% (was 6%), so it can no longer pass 100%.
[/list]

[b]Booms[/b]
[list]
[*]The size of booms before finance technologies is 2.1 (was 2).
[/list]

[b]AI countries[/b]
[list]
[*]They go Tight at a leverage limit of 8, 9.5 or 11.5 months by temperament (was 6.5, 8 and 9.5).
[/list]

The Mania numbers in the beta.3 notes were too high, because our simulator made confidence rise too easily. We corrected it against two played-out AI games. It now gives beta.3 about 6% of months in Mania for a country left alone and 3% for AI countries. For beta.4 it gives about 8% for a country left alone, 5% for AI countries and 5.5% for a country that runs up to 12 months. Nothing after 1866 has been checked against a real game.

In our simulations, running up to 12 months now beats careful play in almost nine worlds in ten and matches holding a steady 6. Almost two thirds of those runs get out without a panic.

Saves from 1.3 and earlier betas carry on. New text is English only for now. The Morgenroete, Tech & Res and Better Politics Mod patches are still built for 1.3, so test this beta without them.
""", encoding="utf-8", newline="\n")
p=Path("beta/workshop_description.bbcode"); t=p.read_text(encoding="utf-8")
old="Tight credit pays loans off about ten times faster, the Panic Threshold rises less, Mania comes around more often, and AI countries use leverage too."
assert t.count(old)==1
t=t.replace(old,"running leverage up to 12 months pays, Tight credit pays loans off about ten times faster, the Panic Threshold rises less, Mania comes around more often, and AI countries use leverage too.").replace("1.3.1-beta.3","1.3.1-beta.4")
p.write_text(t,encoding="utf-8",newline="\n")
'@ | Set-Content -Encoding utf8 $s\n.py; py -3 -B $s\n.py
git diff --stat beta/workshop_description.bbcode 2>$null
Move-Item build_scratch\rc_1.3.1\.metadata\built_against.txt $s\built_against_b4.txt -Force
py -3 -B beta/build.py --source build_scratch\rc_1.3.1 --out beta\release_131 --revision 4 2>&1 | select -Last 6
$z='beta\release_131\releases\Speculative_Markets_Beta_1.3.1-beta.4.zip'
py -3 -B tools/stage_workshop.py beta $z 2>&1 | select -Last 4
(Get-FileHash $z).Hash
py -3 -B build_scratch\sync_live.py build_scratch\rc_1.3.1 build_scratch\rivals_live 2>&1 | select -Last 2
py -3 -B tools/steam_upload.py --help 2>&1 | select -First 14
