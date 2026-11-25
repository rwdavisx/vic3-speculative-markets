cd G:\GameDev\_claude_scratch\v130\infographic\sim
$t=@'
import sys, multiprocessing as mp, numpy as np
from pathlib import Path
H=Path(r'G:\GameDev\_claude_scratch\v130\infographic\sim')
sys.path[:0]=[str(H/'tools'/'tuner'),str(H/'tools')]
import engine
def job(a):
    lev,gap,conf,seed=a
    b=dict(engine.BOTS['skilled']); b.update(tight_conf=conf,tight_lev=lev,untight_lev=lev-gap,untight_conf=60)
    engine.BOTS['x']=b
    s=engine.summarize(engine.Economies(engine.current(),engine.defaults(),'x',1000,seed).run())
    return (lev,gap,conf),[s[k]['mean'] for k in ('growth_edge','panics_per_century','crunch_months_pct','lev_mean','tight_pct')]
if __name__=='__main__':
    print({k:v for k,v in engine.BOTS['careful'].items()}); print(engine.BOTS['skilled'])
    grid=[(l,1,c,s) for l in (2,3,3.5,4,4.5,5,6,7,8) for c in (72,200) for s in (1,2)]
    r={}
    with mp.get_context('spawn').Pool(22) as p:
        for k,v in p.imap_unordered(job,grid): r.setdefault(k,[]).append(v)
    print('tight_lev conf | edge panics baddebt% lev tight%')
    for k in sorted(r,key=lambda k:(k[2],k[0])): print(k[0],k[2],np.round(np.mean(r[k],0),3))
'@
[IO.File]::WriteAllText("$pwd\sweep.py",$t); py -3 -B sweep.py
gci G:\GameDev\speculative-markets\mod\gfx -Recurse -Include *.dds,*.png | ? { $_.Name -match 'mania|reckless|loose|warn|collapse|fever|panic|lax' } | select Name -Unique
