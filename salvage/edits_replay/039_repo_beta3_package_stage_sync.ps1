Move-Item build_scratch\rc_1.3.1\.metadata\built_against.txt build_scratch\built_against_rc_1.3.1.txt -Force
Select-String -Path build_scratch\rc_1.3.1\common\script_values\*.txt -Pattern "^spec_boom_rule|^spec_heat_from" -Context 0,6 | ForEach-Object { $_.Line; $_.Context.PostContext }
Select-String -Path build_scratch\rc_1.3.1\localization\english\*.yml -Pattern "\+1[0-9](\.\d)?%" | Where-Object { $_.Line -match "boom" } | Select-Object -First 4 | ForEach-Object { $_.Line.Substring(0,[Math]::Min(200,$_.Line.Length)) }
py -3 -B beta/build.py --source build_scratch\rc_1.3.1 --out beta\release_131 --revision 3 2>&1 | Select-Object -Last 5; "build $LASTEXITCODE"
Get-ChildItem beta\release_131\releases | Select-Object Name,Length; $z="beta\release_131\releases\Speculative_Markets_Beta_1.3.1-beta.3.zip"; (Get-FileHash $z).Hash
py -3 -B tools/stage_workshop.py beta $z 2>&1 | Select-Object -Last 3; "stage $LASTEXITCODE"
if(Get-Process victoria3 -ErrorAction SilentlyContinue){"GAME RUNNING, no sync"}else{py -3 build_scratch\sync_live.py build_scratch\rc_1.3.1 build_scratch\rivals_live 2>&1 | Select-Object -Last 3}
py -3 -B tools/steam_upload.py plan beta | Select-Object -First 1 | ForEach-Object { $j=$_ | ConvertFrom-Json; "$($j.version) $($j.file_count) $($j.source_archive_sha256)" }
"--- beta2 vs beta3"; $d=(New-Item -ItemType Directory -Force "C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\cmp$(Get-Random)").FullName; Expand-Archive beta\release_131\releases\Speculative_Markets_Beta_1.3.1-beta.2.zip "$d\a"; Expand-Archive $z "$d\b"; git --no-pager diff --no-index --stat "$d\a" "$d\b" | ForEach-Object { $_ -replace '.*(\\|/)(?=[^\\/]+\|)','' }
