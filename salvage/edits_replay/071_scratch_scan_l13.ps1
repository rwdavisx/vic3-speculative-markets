$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
'[{"LEV_CRUNCH_FADE":0.35},{"LEV_CRUNCH_FADE":0.35,"LEV_RECORD_PAST":2},{"LEV_CRUNCH_FADE":0.35,"LEV_RECORD_PAST":2,"BUST_PER_HYPE":1.5}]' | Set-Content -Encoding ascii $s\l13.json
foreach($k in 1,2){ "seed $k"; py -3 -B $s\mania12.py one 1000 $k $s\l13.json | select -Skip 1 }
Get-Content $s\l13.json; git diff --stat; Get-ChildItem beta\release_131 -Recurse -Depth 1 | select -Expand FullName; Get-Content beta\changelog_1.3.1-beta.3.bbcode; Select-String -Path beta\workshop_description.bbcode -Pattern '1\.3\.1' | % Line
