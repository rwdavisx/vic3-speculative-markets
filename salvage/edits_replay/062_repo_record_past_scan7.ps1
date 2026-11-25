$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
R = Path(r"G:\GameDev\speculative-markets\tools")
def ed(f, *pairs):
    p = R/f; raw = p.read_bytes(); crlf = b"\r\n" in raw; t = raw.decode("utf-8").replace("\r\n", "\n")
    for a, b in pairs:
        assert t.count(a) == 1, (f, t.count(a), a); t = t.replace(a, b)
    p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
ed("leverage.py",
 ('RECORD = bool(ON and RECORD_BUILD > 0)\n', '# each month past RECORD_FROM counts 1 + RECORD_PAST times: the far end of a run-up is worth its risk\nRECORD_FROM, RECORD_PAST = tuning.get("LEV_RECORD_FROM", 6), tuning.get("LEV_RECORD_PAST", 0)\nRECORD = bool(ON and RECORD_BUILD > 0)\n'),
 ('spec_lev_record_gap = {{\\n\\tvalue = spec_lev_adj\\n\\tmultiply', 'spec_lev_record_gap = {{\\n\\tvalue = spec_lev_adj\\n" + (f"\\tadd = {{\\n\\t\\tvalue = spec_lev_adj\\n\\t\\tsubtract = {RECORD_FROM:g}\\n\\t\\tmin = 0\\n\\t\\tmultiply = {RECORD_PAST:g}\\n\\t}}\\n" if RECORD_PAST else "") + f"\\tmultiply'))
ed("tuner/engine.py",
 ('    ("LEV_RECORD_LOSS", lv,', '    ("LEV_RECORD_PAST", lv, "RECORD_PAST", "Leverage", "Sound Credit: how much more each month of leverage past 6 counts"),\n    ("LEV_RECORD_LOSS", lv,'),
 ('gap = lev2 * (K["LEV_RECORD_BUILD"]', 'gap = (lev2 + np.maximum(lev2 - lv.RECORD_FROM, 0) * K["LEV_RECORD_PAST"]) * (K["LEV_RECORD_BUILD"]'))
t = (Path(__file__).parent/"r12.py").read_text(encoding="utf-8")
i = t.index("        print(json.dumps(moves[c[\"id\"]]))")
t = t[:i] + '''        print(json.dumps(moves[c["id"]]).replace("LEV_",""), "| " + " ".join(f"{b} {G[b]:.2f}" for b in ("careful","hold6","run10","run12","blind12","reckless","ai","passive")) + f" | 12-C {G['run12']-G['careful']:+.2f} 12-6 {G['run12']-G['hold6']:+.2f} pan12 {g('run12','panics_per_century'):.1f} ups {g('run12','runs10_per_century'):.2f} out {g('run12','runs10_out_pct'):.0f} beat {g('run12','beaten_pct'):.0f} lev8 {g('run12','lev8_pct'):.1f} | AI pan {g('ai','panics_per_century'):.1f} mania P {g('passive','mania_pct'):.1f} 12 {g('run12','mania_pct'):.1f} AI {g('ai','mania_pct'):.1f}")
if __name__ == "__main__":
    mp.freeze_support(); main(int(sys.argv[1]), int(sys.argv[2]), json.loads(open(sys.argv[3]).read()))
'''
(Path(__file__).parent/"r12b.py").write_text(t, encoding="utf-8")
'@ | Set-Content -Encoding utf8 $s\past.py
py -3 -B $s\past.py; if(-not $?){ return }; py -3 -B tools\leverage.py | select -Last 1
@'
import sys, json, os, subprocess
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(LEV_PANIC_SPAN=sp, LEV_RECORD_FADE=f, LEV_RECORD_GAIN=g, LEV_RECORD_PAST=p) for sp in (15,20,25) for f, g, p in ((.02,.02,1),(.02,.02,2),(.02,.03,1),(.02,.03,2),(.005,.03,1))]
json.dump(moves, open(S/"l7.json","w"))
for lad in ([3,8,10,12],[3,9,11,12]):
    for loose in (2.0,2.5):
        tf = S/f"tunc_{lad[1]}_{loose}.json"; json.dump(T|{"LEV_LADDER":lad,"LOOSE_CREDIT":loose,"FIN_BOOM_BASE":2.1}, open(tf,"w"))
        r = subprocess.run([sys.executable,"-B",str(S/"r12b.py"),"250","1",str(S/"l7.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
        print("#### ladder", lad, "loose", loose, r.stderr[-400:] if r.returncode else ""); print(r.stdout, flush=True)
'@ | Set-Content -Encoding utf8 $s\scan7.py
py -3 -B $s\scan7.py 2>&1 | Out-File -Encoding utf8 $s\scan7.txt; Get-Content $s\scan7.txt
