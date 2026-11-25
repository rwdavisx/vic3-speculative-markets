cd G:\GameDev\speculative-markets; Select-String tools\tuner\*.py,tools\*.py -Pattern 'summarize\(|engine\.batch|engine\.job' | % {"$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(140,$_.Line.Trim().Length)))"}
$p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\heigh.py"
@'
import sys, multiprocessing as mp
R=r'G:\GameDev\speculative-markets\tools'; sys.path[:0]=[R+r'\tuner',R]
import engine
def job(a):
    b,s=a; c=engine.defaults(); c['inputs']=c['inputs']|{'heightened':1}
    x=engine.summarize(engine.run({},c,b,500,s)); return b,s,[round(x[k]['mean'],2) for k in('growth_core','panics_per_century','mania_pct')]
if __name__=='__main__':
    print(engine.g.VOLATILITY)
    with mp.get_context('spawn').Pool(12) as p:
        for r in p.imap(job,[(b,s) for b in('passive','careful','hold6','run10','reckless','ai') for s in(601,602)]): print(*r)
'@ | Set-Content -Encoding utf8 $p
$env:OMP_NUM_THREADS=1; $env:SPEC_MOD_OUT="$pwd\build_scratch\rc_1.3.1"; py -3 -B $p
Select-String build_scratch\rc_1.3.1\localization\english\*.yml -Pattern 'heightened_desc' | % Line
Get-Content beta\workshop_description.bbcode | Select-String '1\.3\.1|AI countr|How the AI' 
