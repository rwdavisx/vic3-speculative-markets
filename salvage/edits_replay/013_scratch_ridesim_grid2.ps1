$t=@'
import sys, json, multiprocessing as mp, numpy as np
from pathlib import Path
H=Path(r'G:\GameDev\_claude_scratch\v130\ridesim')
sys.path[:0]=[str(H/'tools'/'tuner'),str(H/'tools')]
import engine
INF=1e9
RIDERS={f'ride{X:g}c{c}':(X,c) for X in (8,11) for c in (3,10,18)}
class Rec(engine.Economies):
    def step(self,*a,**k):
        super().step(*a,**k)
        if not hasattr(self,'L'): self.L,self.P=[],[]
        self.L.append(self.lev(self.pool_month()).astype(np.float32)); self.P.append(self.in_panic.copy())
def job(a):
    flow,span,safe,rt,bot=a
    engine.RT=rt
    K=dict(engine.current()); K['FIN_BOOM_BASE']=1.5; K['CREDIT_FLOW_MAX']=flow; K['LEV_PANIC_SPAN']=span; K['LEV_SAFE']=safe
    if bot in RIDERS:
        X,c=RIDERS[bot]; b=dict(engine.BOTS['skilled']); b.update(ride=1,tight_conf=INF,tight_lev=X,untight_conf=INF,untight_lev=4,cushion=c,loose_conf=INF,loose_lev=6,unloose_conf=INF)
        engine.BOTS['x']=b
    e=Rec(K,engine.defaults(),'x' if bot in RIDERS else bot,400,7).run()
    s=engine.summarize(e); L=np.array(e.L); P=np.array(e.P)
    n=b_=0
    for i in range(L.shape[1]):
        l,p=L[:,i],P[:,i]; j=0
        while j<len(l):
            if l[j]>=9 and not p[j]:
                k=j
                while k<len(l) and not p[k] and l[k]>4.5: k+=1
                if k<len(l): n+=1; b_+=p[k]
                j=k
                while j<len(l) and (p[j] or l[j]>4.5): j+=1
            else: j+=1
    return a,[s[k]['mean'] for k in ('growth_edge','panics_per_century','crunch_months_pct','mania_pct')]+[n/L.shape[1],100*b_/max(n,1),float(L.max(0).mean())]
if __name__=='__main__':
    bots=['careful','passive','ai','reckless',*RIDERS]
    jobs=[(f,sp,3,rt,b) for f in (.15,.25,.4) for sp in (55,40) for rt in (.06,.1) for b in bots]
    r={}
    with mp.get_context('spawn').Pool(22) as p:
        for k,v in p.imap_unordered(job,jobs): r[k]=v
    for c in sorted({k[:4] for k in r}):
        print(c,'|',*[f'{b}: {r[(*c,b)][0]:+.2f} p{r[(*c,b)][1]:.1f} m{r[(*c,b)][3]:.1f}' for b in ('careful','passive','ai','reckless')])
        for b in RIDERS: print('    ',b,'edge %.2f panics %.1f bad%% %.1f mania %.1f | tops>=9: %.2f burned %.0f%% peak %.1f'%tuple(r[(*c,b)]))
'@
[IO.File]::WriteAllText('G:\GameDev\_claude_scratch\v130\ridesim\grid2.py',$t)
cd G:\GameDev\_claude_scratch\v130\ridesim; py -3 -B grid2.py 2>&1 | Out-File grid2_out.txt -Encoding utf8; Get-Content grid2_out.txt
