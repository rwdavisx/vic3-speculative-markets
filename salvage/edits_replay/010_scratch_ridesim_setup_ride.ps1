cd G:\GameDev\_claude_scratch\v130
robocopy infographic\sim\tools ridesim\tools /E /NJH /NJS /NFL /NDL | Out-Null
$p='G:\GameDev\_claude_scratch\v130\ridesim\tools\tuner\engine.py'; $s=[IO.File]::ReadAllText($p)
$a='runoff = np.maximum(self.debt * K["CREDIT_RUNOFF"], 0)'; if(!$s.Contains($a)){'MISS1'}
$s=$s.Replace($a,'runoff = np.maximum(self.debt * np.where(self.stance == -1, RT or K["CREDIT_RUNOFF"], K["CREDIT_RUNOFF"]), 0)')
$a='to_tight &= self.stance == 0 if P["tight_conf"] < INF or P["tight_lev"] < INF else to_tight'; if(!$s.Contains($a)){'MISS2'}
$s=$s.Replace($a,'to_tight &= (self.stance == 0) | bool(P.get("ride"))')
$s=$s.Replace('# ---------- player bots: one threshold policy','RT = 0'+"`n"+'# ---------- player bots: one threshold policy'); [IO.File]::WriteAllText($p,$s)
$t=@'
import sys, multiprocessing as mp, numpy as np
from pathlib import Path
H=Path(r'G:\GameDev\_claude_scratch\v130\ridesim')
sys.path[:0]=[str(H/'tools'/'tuner'),str(H/'tools')]
import engine
INF=1e9
class Rec(engine.Economies):
    def step(self,*a,**k):
        super().step(*a,**k)
        if not hasattr(self,'L'): self.L,self.P=[],[]
        self.L.append(self.lev(self.pool_month()).astype(np.float32)); self.P.append(self.in_panic.copy())
def job(a):
    name,X,Y,loose,rt,seed=a
    engine.RT=rt
    if name=='careful': bot='careful'
    elif name=='skilled': bot='skilled'
    else:
        b=dict(engine.BOTS['skilled']); b.update(ride=1,tight_conf=INF,tight_lev=X,untight_conf=INF,untight_lev=Y)
        if loose: b.update(loose_conf=INF,loose_lev=Y,unloose_conf=INF)
        engine.BOTS['x']=b; bot='x'
    e=Rec(engine.current(),engine.defaults(),bot,1000,seed).run()
    s=engine.summarize(e); L=np.array(e.L); P=np.array(e.P)
    out=[s[k]['mean'] for k in ('growth_edge','panics_per_century','crunch_months_pct','lev_mean','tight_pct')]
    ep={}
    for th in (6,8,10):
        n=b_=esc=0; tb=[]; te=[]
        for i in range(L.shape[1]):
            l,p=L[:,i],P[:,i]; j=1
            while j<len(l):
                if l[j]>=th and not p[j]:
                    n+=1; k=j
                    while k<len(l) and not p[k] and l[k]>4: k+=1
                    if k<len(l):
                        if p[k]: b_+=1; tb.append(k-j)
                        else: esc+=1; te.append(k-j)
                    j=k
                    while j<len(l) and (p[j] or l[j]>4): j+=1
                else: j+=1
        ep[th]=(n/L.shape[1],b_,esc,float(np.median(tb)) if tb else 0,float(np.median(te)) if te else 0)
    return (name,X,Y,loose,rt),out,ep
if __name__=='__main__':
    jobs=[('careful',0,0,0,rt,s) for rt in (0,.03,.05) for s in (1,2)]+[('skilled',0,0,0,rt,s) for rt in (0,.03,.05) for s in (1,2)]
    for rt in (0,.02,.03,.05,.08):
        for X in (6,8,10,11.5):
            for Y in (3,5):
                for loose in (0,1):
                    jobs+=[('ride',X,Y,loose,rt,s) for s in (1,2)]
    r={}; ee={}
    with mp.get_context('spawn').Pool(22) as p:
        for k,v,ep in p.imap_unordered(job,jobs): r.setdefault(k,[]).append(v); ee.setdefault(k,[]).append(ep)
    print('name X Y loose rt | edge panics bad% lev tight% | th: per-economy, burned%, med months to burn / escape')
    for k in sorted(r,key=lambda k:(k[4],k[0],k[3],k[1],k[2])):
        v=np.mean(r[k],0); t=''
        for th in (6,8,10):
            n=np.mean([q[th][0] for q in ee[k]]); b=sum(q[th][1] for q in ee[k]); es=sum(q[th][2] for q in ee[k])
            t+=f" | {th}: {n:.2f} {100*b/max(b+es,1):.0f}% {np.mean([q[th][3] for q in ee[k]]):.0f}/{np.mean([q[th][4] for q in ee[k]]):.0f}"
        print(*k,'|',*['%.2f'%x for x in v],t)
'@
[IO.File]::WriteAllText('G:\GameDev\_claude_scratch\v130\ridesim\ride.py',$t)
cd ridesim; py -3 -B ride.py > ride_out.txt 2>&1; Get-Content ride_out.txt
