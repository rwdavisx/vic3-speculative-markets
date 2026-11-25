$S='G:\GameDev\_claude_scratch\v130\infographic'; $D='G:\GameDev\_claude_scratch\v130\infographic131'
robocopy $S $D /E /XD chrome_hl /NFL /NDL /NJH /NJS | Out-Null
robocopy G:\GameDev\speculative-markets\tools "$D\sim\tools" /E /XD __pycache__ /NFL /NDL /NJH /NJS | Out-Null
Select-String "$D\build.py" -Pattern 'G:|infographic|chrome|1\.3' | % {"$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(200,$_.Line.Trim().Length)))"}
cd "$D\sim"; py -3 -B run_sim.py 2>&1 | Select-Object -Last 8
