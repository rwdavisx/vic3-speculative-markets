$p='G:\GameDev\_claude_scratch\v130\ridesim\tools\tuner\engine.py'; $s=[IO.File]::ReadAllText($p)
$a='        new = _first([to_tight, to_normal_t, to_loose, to_normal_l]'; if(!$s.Contains($a)){'MISS'}
$nl = if($s.Contains("`r`n")){"`r`n"}else{"`n"}
if(!$s.Contains('P.get("cushion")')){ $s=$s.Replace($a,'        if P.get("cushion") is not None:'+$nl+'            to_tight |= can & (self.stance != -1) & (lev > engine_safe + 1) & (self.conf - self.panic_at(lev) < P["cushion"])'+$nl+$a) }
$s=$s.Replace('RT = 0'+"`n",'RT = 0'+"`n"+'engine_safe = 3'+"`n"); [IO.File]::WriteAllText($p,$s)
$t=@'
import sys, json, multiprocessing as mp, numpy as np
from pathlib import Path
H=Path(r'G:\GameDev\_claude_scratch\v130\ridesim')
sys.path[:0]=[str(H/'tools'/'tuner'),str(H/'tools')]
import engine
INF=1e9
RIDERS={f'ride{X:g}c{c}{"L" if lo else "N"}':(X,c,lo) for X in (8,11.5) for c in (8,18) for lo in (0,1)}
def job(a):
    fb,rec,span,rt,bot=a
    engine.RT=rt
    K=dict(engine.current()); K['FIN_BOOM_BASE']=fb; K['CONF_RECOVER']=rec; K['LEV_PANIC_SPAN']=span
    if bot in RIDERS:
        X,c,lo=RIDERS[bot]; b=dict(engine.BOTS['skilled']); b.update(ride=1,tight_conf=INF,tight_lev=X,untight_conf=INF,untight_lev=4,cushion=c)
        if lo: b.update(loose_conf=INF,loose_lev=5,unloose_conf=INF)
        engine.BOTS['x']=b
    s=engine.summarize(engine.Economies(K,engine.defaults(),'x' if bot in RIDERS else bot,400,7).run())
    return a,[s[k]['mean'] for k in ('growth_edge','panics_per_century','crunch_months_pct','mania_pct','up_pct','lev_max')]
if __name__=='__main__':
    bots=['careful','passive','ai','reckless',*RIDERS]
    jobs=[(fb,rec,span,rt,b) for fb in (1,1.5,2) for rec in (.2,.15) for span in (55,40) for rt in (0,.03,.06) for b in bots]
    r={}
    with mp.get_context('spawn').Pool(22) as p:
        for k,v in p.imap_unordered(job,jobs): r[k]=v
    json.dump([[*k,*v] for k,v in r.items()],open(H/'grid.json','w'))
    for c in sorted({k[:4] for k in r}):
        best=max(RIDERS,key=lambda b:r[(*c,b)][0])
        print(c,'|',*[f'{b}: {r[(*c,b)][0]:+.2f} p{r[(*c,b)][1]:.1f} m{r[(*c,b)][3]:.1f}' for b in ('careful','passive','ai','reckless')],'|| best',best,*['%.2f'%x for x in r[(*c,best)]])
'@
[IO.File]::WriteAllText('G:\GameDev\_claude_scratch\v130\ridesim\grid.py',$t); 'ok'
