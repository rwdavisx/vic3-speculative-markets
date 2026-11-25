cd G:\GameDev\speculative-markets
Select-String tools\tuner\lab.py -Pattern 'score' | Select-Object -First 25 | % {"$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(190,$_.Line.Trim().Length)))"}
Select-String tools\*.py -Pattern 'INCOME_FLOOR' | % {"$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(220,$_.Line.Trim().Length)))"}
Select-String tools\tuner\engine.py -Pattern 'INCOME_FLOOR|def pool_month|def lev\(' -Context 0,4 | Out-String
$p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\spot.py"
@'
import sys, multiprocessing as mp, numpy as np
R=r'G:\GameDev\speculative-markets\tools'; sys.path[:0]=[R+r'\tuner',R]
import engine
V={'1.3.0':dict(CREDIT_RUNOFF_TIGHT=.0095,FIN_BOOM_BASE=1,LEV_PANIC_SPAN=55),'beta':{},
 'K5':dict(LEV_PANIC_SPAN=35,FIN_BOOM_BASE=1.75,LEV_INCOME_FLOOR=.007,LEV_RECORD_GAIN=.02,LEV_CRUNCH_BUILD=.06)}
# own riders: run to 10, tight, back under 4, stays on Loose up to 6; 'six' = threshold 6 untight 5
B={'run10':dict(tight_lev=10,untight_lev=4,loose_lev=6),'cut4':dict(tight_lev=4,untight_lev=3),'six':dict(tight_lev=6,untight_lev=5)}
class Rec(engine.Economies):
    def step(self,*a,**k):
        super().step(*a,**k); pm=self.pool_month(); l=self.lev(pm)
        if not hasattr(self,'mx'): self.mx=l*0; self.h8=0; self.mm=0
        self.mx=np.maximum(self.mx,l); self.h8+=(l>=8).mean(); self.mm+=1
        if self.m in (12,360,720,1080): self.__dict__.setdefault('fl',{})[self.m]=None
def job(a):
    v,b=a; K=dict(engine.current())
    for k,x in V[v].items():
        assert k in K,k; K[k]=x
    bot=b
    if b in B:
        d=dict(engine.BOTS['skilled']); d.update(tight_conf=1e9,untight_conf=1e9,loose_conf=1e9,unloose_conf=1e9,**B[b]); engine.BOTS['x']=d; bot='x'
        if b!='run10': d['loose_lev']=-1
    e=Rec(K,engine.defaults(),bot,1000,501).run(); s=engine.summarize(e)
    return a,[s[k]['mean'] for k in('growth_edge','panics_per_century','mania_pct')]+[float(e.mx.mean()),100*e.h8/e.mm]
if __name__=='__main__':
    with mp.get_context('spawn').Pool(20) as p:
        r=dict(p.map(job,[(v,b) for v in V for b in('passive','careful','skilled','ai','reckless',*B)],chunksize=1))
    for (v,b),x in r.items(): print(f'{v:6}{b:9} edge {x[0]:+.2f} panics {x[1]:.1f} mania {x[2]:.1f} peak {x[3]:.1f} mo8+ {x[4]:.1f}%')
'@ | Set-Content -Encoding utf8 $p
$env:OMP_NUM_THREADS=1; py -3 -B $p
