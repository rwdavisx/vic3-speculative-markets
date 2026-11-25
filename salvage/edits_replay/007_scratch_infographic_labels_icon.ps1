cd G:\GameDev\_claude_scratch\v130\infographic
Select-String -Path build.py -Pattern 'mod_loose|event_panic|\.dds|def icon' | % {"$($_.LineNumber): $($_.Line.Trim())"}
$s=[IO.File]::ReadAllText("$pwd\build.py")
$s=$s.Replace('"Tight early"','"Tight at 4 months"').Replace('"Tight late"','"Tight at 6 months"').Replace('"always Loose", "mod_loose"','"always Loose", "event_mania"').Replace('"mod_loose"','"event_mania"')
[IO.File]::WriteAllText("$pwd\build.py",$s)
gci G:\GameDev\speculative-markets\mod\gfx -Recurse -Filter event_mania.dds | select FullName
py -3 -B build.py 2>&1 | Select-Object -Last 4; gi does_it_pay.png | select LastWriteTime
