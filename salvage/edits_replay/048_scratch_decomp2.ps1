$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import pickle, sys, numpy as np
G, tags, S = pickle.load(open(sys.argv[1], "rb"))
def ac(x, l):
    a, b = x[:, :-l], x[:, l:]; m = np.isfinite(a) & np.isfinite(b); return np.corrcoef(a[m], b[m])[0, 1]
for nm, A in (("game", G), ("sim", S)):
    c = A["conf"]; print("##", nm)
    for e in range(3):
        sl = slice(e*120, (e+1)*120); cc = c[:, sl]
        print(f" {36+10*e}s conf {np.nanmean(cc):.1f} boom {np.nanmean(A['boom'][:,sl]):.2f} braw {np.nanmean(A['braw'][:,sl]):.2f} capped {np.nanmean(A['braw'][:,sl]>=3)*100:.0f}% braw>0 {np.nanmean(A['braw'][:,sl]>0)*100:.0f}% boom when capped {np.nanmean(A['boom'][:,sl][A['braw'][:,sl]>=3]):.2f} p95 {np.nanpercentile(A['boom'][:,sl],95):.2f} p99 {np.nanpercentile(A['boom'][:,sl],99):.2f} 75+ {np.nanmean(cc>=75)*100:.1f} 80+ {np.nanmean(cc>=80)*100:.2f}")
    cr = A["d_crash"] if nm == "game" else A["crash"] * c / 50
    cr = cr[np.isfinite(cr)]; print(" crash: mean", cr.mean().round(3), "share of months <-0.1", (cr < -.1).mean().round(3), "size when", cr[cr < -.1].mean().round(2), "p1", np.percentile(cr, 1).round(2), "p0.1", np.percentile(cr, .1).round(2))
    print(" ends/yr s1,s2,s3", [round(float(np.nanmean(A[f'end{k}'])*12), 2) for k in (1,2,3)])
    print(" between-country sd of mean conf", np.nanstd(np.nanmean(c, 1)).round(2), "sd over time", np.nanmean(np.nanstd(c, 1)).round(2), "conf ac 1/6/12/24", [round(ac(c, l), 2) for l in (1,6,12,24)], "boom ac", [round(ac(A['boom'], l), 2) for l in (1,6,12,24)])
    print(" mood sd", np.nanstd(A["d_mood"]).round(2), "fin-ish cap: boom/min(braw,3) pct 5/25/50/75/95", np.nanpercentile((A["boom"]/np.minimum(A["braw"],3))[A["braw"]>.5], [5,25,50,75,95]).round(2))
    oth = sum(np.nan_to_num(A[k]) for k in ("foreign","turmoil","restrain","d_debt","d_mood","d_growth","d_business","d_world","d_tight")) + (np.nan_to_num(A.get("d_rough", 0)) if nm == "sim" else 0)
    print(" sum of other monthly drivers sd", oth.std().round(2), "ac1", round(ac(oth, 1), 2), "ac12", round(ac(oth,12),2))
    hot = c >= 75; print(" at 75+: wsum", np.nanmean(A['wsum'][hot]).round(1), "boom sd", np.nanstd(A['boom'][hot]).round(2))
# game: fin and steady of the largest, and unexplained residual
r = G["conf"][:,1:]-G["conf"][:,:-1]-sum(G[k][:,1:] for k in ("boom","d_crash","foreign","turmoil","restrain","d_debt","d_mood","d_drift","d_growth","d_business","d_world","d_tight","d_burst","d_drop","d_rescue","d_caution","d_warend","d_limit","d_rival"))
print("game residual mean/sd", np.nanmean(r).round(3), np.nanstd(r).round(3), "pct", np.nanpercentile(r,[.5,1,5,50,95,99,99.5]).round(2))
for lo in (50,70,75,80,85):
    m=(G["conf"][:,:-1]>=lo)&(G["conf"][:,:-1]<lo+5); print(lo, "resid", np.nanmean(r[m]).round(2), np.nanstd(r[m]).round(2))
print("fin", np.nanpercentile(G["fin"],[5,50,95]), "steady", np.nanpercentile(G["steady"],[5,50,95]).round(3))
# months after first crossing 80: path
for nm, A in (("game", G), ("sim", S)):
    c=A["conf"]; P=[]
    for row in c:
        for k in range(2, 350):
            if row[k]>=80 and row[k-1]<80 and np.all(row[max(0,k-6):k]<80): P.append(row[k-2:k+8])
    P=np.array(P); print(nm, len(P), "path around crossing", np.nanmean(P,0).round(1), "sd", np.nanstd(P,0).round(1))
'@ | Set-Content -Encoding utf8 $s\decomp2.py
py -3 -B $s\decomp2.py $s\decomp.pkl
