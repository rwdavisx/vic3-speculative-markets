$f='G:\GameDev\_claude_scratch\v130\waterworks.html'
$l=[IO.File]::ReadAllLines($f); "$($l.Count) lines; long: " + (($l | ? {$_.Length -gt 2000}).Count)
$out="$env:TEMP\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\ww_short.txt"
[IO.File]::WriteAllLines($out, ($l | % { if($_.Length -gt 2000){ $_.Substring(0,200)+' <<CUT '+$_.Length+'>>' } else { $_ } }))
(gi $out).Length
# external refs anywhere, incl. long lines
[regex]::Matches(($l -join "`n"),'https?://[^\s"''<>)]{1,80}') | % Value | group | select Count,Name
($l | ? {$_.Length -gt 2000}) | % { [regex]::Matches($_,'data:[a-z]+/[a-z+]+') | % Value } | group | select Count,Name
