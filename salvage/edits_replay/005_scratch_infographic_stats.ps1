cd G:\GameDev\_claude_scratch\v130\infographic\sim
$t=@'
import json
d=json.load(open('results.json'))['bots']
import statistics as s
def m(b,k): return s.mean(v['sum'][k] for v in d[b].values() if isinstance(v['sum'].get(k),(int,float)))
ks=['growth_edge','panics_per_century','lev_mean','lev_max','conf_mean','tight_pct','loose_pct','rescues_per_century','spend_pct_gdp','mania_pct','crunch_months_pct','crunch_max','output_pct','pool_pct']
print('%-22s'%'', *['%9s'%b for b in d])
for k in ks: print('%-22s'%k, *['%9.2f'%m(b,k) for b in d])
for g in ('calm','allm'):
    for k in next(iter(d['careful'].values()))[g]: print('%-22s'%(g+'.'+k), *['%9.4f'%s.mean(v[g][k] for v in d[b].values()) for b in d])
'@
[IO.File]::WriteAllText("$env:TEMP\zz.py",$t); py -3 -B $env:TEMP\zz.py
