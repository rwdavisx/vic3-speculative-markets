$R='G:\GameDev\_claude_scratch\v130\ridesim'; $f="$R\tools\tuner\engine.py"; $s=[IO.File]::ReadAllText($f)
$a='runoff = np.maximum(self.debt * np.where(self.stance == -1, RT or K["CREDIT_RUNOFF"], K["CREDIT_RUNOFF"]), 0)'
$b='runoff = np.maximum(self.debt * K["CREDIT_RUNOFF"], 0); runoff = np.where(self.stance == -1, np.maximum(runoff, np.minimum(self.debt * RT, self.pool)), runoff)'
[IO.File]::WriteAllText($f,$s.Replace($a,$b))
$g=[IO.File]::ReadAllText("$R\grid3.py").Replace("(1.6,2.5) for sp in (55,50,45) for rt in (.05,.1)","(1.6,) for sp in (50,) for rt in (.1,)"); [IO.File]::WriteAllText("$R\grid4.py",$g)
py -3 -B "$R\grid4.py"
