$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"
$code=@'
import sys
from pathlib import Path
import numpy as np
R = Path(r"G:\GameDev\speculative-markets"); sys.path[:0] = [str(R/"tools"), str(R/"tools/tuner")]
import windows as w, engine
KEEP = {}
o = w.Recorded.run
def run(self):
    o(self); KEEP["conf"] = np.array([s[0] for s in self.snap]).T; KEEP["boom"] = np.array([k["boom"] for k in self.kept]).T
w.Recorded.run = run
w.tuner_side(["1836"])
c = KEEP["conf"][:, :360]; b = KEEP["boom"][:, :360]
pr = lambda n, c: print(n, "pct 5/50/90/95/99", np.round(np.nanpercentile(c, [5, 50, 90, 95, 99]), 1), "70+", round(float(np.nanmean(c >= 70)*100), 1), "80+", round(float(np.nanmean(c >= 80)*100), 2))
pr("sim", c); print("  boom by decade", np.round([b[:, i:i+120].mean() for i in (0, 120, 240)], 2))
# when confidence is 70 to 79, what is the next month's change made of?
f = R / "runs/sweep_beta3/beta3_01/telemetry.log"
seen = w.parse(f, 1836, 360); rows = {t: r for t, r in w.top(seen, 0, 360).items() if len(r) >= 288}
num = w.fastsim.num
hist = {}; acc = {}
for r in rows.values():
    for k in r:
        if k + 1 in r and k - 1 in r:
            x = num(r[k], "conf"); d = num(r[k + 1], "conf") - x
            key = int(x // 5 * 5); hist.setdefault(key, []).append((d, num(r[k], "boom"), num(r[k], "crash"), num(r[k], "mood"), num(r[k], "foreign"), num(r[k], "turmoil"), num(r[k], "stance"), num(r[k],"restrain"), num(r[k],"heat"), num(r[k],"fever")))
print("game: conf band, n, mean next change, sd, boom, crash, mood, foreign, turmoil, stance, restrain, heat, fever")
for k in sorted(hist):
    a = np.array(hist[k]); print(k, len(a), np.round(a[:, 0].mean(), 2), np.round(a[:, 0].std(), 2), np.round(a[:, 1:].mean(0), 2))
cs = {}
for row in c:
    for k in range(359):
        cs.setdefault(int(row[k] // 5 * 5), []).append(row[k + 1] - row[k])
print("sim: band, share%, mean change, sd"); n = c.size
for k in sorted(cs): print(k, round(len(cs[k]) / n * 100, 1), round(float(np.mean(cs[k])), 2), round(float(np.std(cs[k])), 2))
'@; [IO.File]::WriteAllText("$sp\why.py",$code); py -3 -B "$sp\why.py"; Select-String -Path tools\generate.py -Pattern "CONF_BOOM_MAX|spec_conf_aim|spec_conf_step" | Select-Object -First 25 | ForEach-Object { "$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(210,$_.Line.Trim().Length)))" }
