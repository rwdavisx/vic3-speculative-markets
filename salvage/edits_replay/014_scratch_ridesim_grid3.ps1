cd G:\GameDev\_claude_scratch\v130\ridesim
$s=[IO.File]::ReadAllText("$pwd\grid2.py")
$s=$s.Replace("flow,span,safe,rt,bot=a","loose,span,seed,rt,bot=a").Replace("K['CREDIT_FLOW_MAX']=flow; K['LEV_PANIC_SPAN']=span; K['LEV_SAFE']=safe","K['LEV_PANIC_SPAN']=span; engine.g.STANCE_CREDIT['loose']=loose")
$s=$s.Replace("bot,400,7)","bot,1000,seed)").Replace("for X in (8,11) for c in (3,10,18)","for X in (11,) for c in (10,18)")
$s=$s.Replace("jobs=[(f,sp,3,rt,b) for f in (.15,.25,.4) for sp in (55,40) for rt in (.06,.1) for b in bots]","jobs=[(f,sp,s,rt,b) for f in (1.6,2.5) for sp in (55,50,45) for rt in (.05,.1) for s in (7,) for b in bots]")
[IO.File]::WriteAllText("$pwd\grid3.py",$s); Select-String grid3.py -Pattern 'jobs=|STANCE|RIDERS=' | % Line
py -3 -B grid3.py 2>&1 | Out-File grid3_out.txt -Encoding utf8; Get-Content grid3_out.txt
