cd G:\GameDev\speculative-markets
Test-Path mod\thumbnail.png; Test-Path mod\.metadata\built_against.txt; Select-String beta\build.py,tools\*.py -Pattern 'built_against' | % {"$($_.Filename):$($_.LineNumber) $($_.Line.Trim())"}
Copy-Item mod\thumbnail.png build_scratch\rc_1.3.1\thumbnail.png
Move-Item build_scratch\rc_1.3.1\.metadata\built_against.txt build_scratch\built_against_rc_1.3.1.txt
Move-Item beta\candidate_131 build_scratch\candidate_131_nothumb
py -3 -B beta/build.py --source build_scratch\rc_1.3.1 --out beta\release_131 --revision 1 2>&1 | Select-Object -Last 3
$z="beta\release_131\releases\Speculative_Markets_Beta_1.3.1-beta.1.zip"
(Get-Item $z).Length; (Get-FileHash $z).Hash
py -3 -B tools/stage_workshop.py beta $z 2>&1 | Select-Object -Last 5
py -3 -B tools/check.py 2>&1 | Select-Object -Last 2
"--- live"; py -3 build_scratch\sync_live.py build_scratch\rc_1.3.1 build_scratch\rivals_live
git status --short; Get-Process victoria3 -ErrorAction SilentlyContinue
