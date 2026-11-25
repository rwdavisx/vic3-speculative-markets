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
ed("generate.py", ('"loose": 1.6}', '"loose": tuning.get("LOOSE_CREDIT", 1.6)}'))
ed("leverage.py",
 ('RECORD = bool(ON and RECORD_BUILD > 0)\n', 'RECORD_FADE = tuning.get("LEV_RECORD_FADE", RECORD_GAIN)  # the same share when leverage is below it: a clean way down keeps it longer\nRECORD = bool(ON and RECORD_BUILD > 0)\n'),
 ('''    ] + ([f"spec_lev_record_keep =''', '''    ] + ([f"spec_lev_record_gap = {{\\n\\tvalue = spec_lev_adj\\n\\tmultiply = {round(RECORD_BUILD / RECORD_STEP, 4):g}\\n\\tsubtract = var:spec_lev_record\\n}}",
          f"spec_lev_record_keep ='''),
 ('''f"spec_lev_record_to = {{\\n\\tvalue = spec_lev_adj\\n\\tmultiply = {round(RECORD_BUILD / RECORD_STEP, 4):g}\\n\\tsubtract = var:spec_lev_record\\n\\tmultiply = {RECORD_GAIN:g}\\n}}",''',
  '''f"spec_lev_record_to = {{\\n\\tvalue = spec_lev_record_gap\\n\\tif = {{\\n\\t\\tlimit = {{ spec_lev_record_gap < 0 }}\\n\\t\\tmultiply = {RECORD_FADE:g}\\n\\t}}\\n\\telse = {{\\n\\t\\tmultiply = {RECORD_GAIN:g}\\n\\t}}\\n}}",'''))
ed("tuner/engine.py",
 ('"Sound Credit: share of the way closed a calm month"),\n', '"Sound Credit: share of the way closed a calm month"),\n    ("LEV_RECORD_FADE", lv, "RECORD_FADE", "Leverage", "Sound Credit: share of the way closed a calm month while leverage is below it"),\n'),
 ('''        built = self.record + (lev2 * (K["LEV_RECORD_BUILD"] / lv.RECORD_STEP) - self.record) * K["LEV_RECORD_GAIN"]  # in RECORD_STEPs\n''',
  '''        gap = lev2 * (K["LEV_RECORD_BUILD"] / lv.RECORD_STEP) - self.record  # in RECORD_STEPs (spec_lev_record_gap)\n        built = self.record + gap * np.where(gap < 0, K["LEV_RECORD_FADE"], K["LEV_RECORD_GAIN"])\n'''))
'@ | Set-Content -Encoding utf8 $s\fade.py
py -3 -B $s\fade.py; if($?){ Select-String tools\generate.py -Pattern '^STANCE_CREDIT' | % Line; py -3 -B tools\leverage.py 2>&1 | select -Last 2; Select-String tools\leverage.py -Pattern 'lev_record' | select -First 6 | % { "$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(120,$_.Line.Trim().Length)))" } }
@'
import sys, json, os, subprocess
from pathlib import Path
S = Path(__file__).parent; T = json.loads(open(r"G:\GameDev\speculative-markets\tools\tuning.json").read())
moves = [dict(FIN_BOOM_BASE=2.1, LEV_PANIC_SPAN=sp, LEV_RECORD_FADE=f, LEV_RECORD_GAIN=g) for sp in (25,30) for f, g in ((.02,.02),(.005,.02),(.005,.04),(.0025,.04))]
json.dump(moves, open(S/"l6.json","w"))
for lad in ([3,8,10,12],[3,9,11,12]):
    for loose in (1.6,2.0,2.5):
        tf = S/f"tunb_{lad[1]}_{loose}.json"; json.dump(T|{"LEV_LADDER":lad,"LOOSE_CREDIT":loose}, open(tf,"w"))
        r = subprocess.run([sys.executable,"-B",str(S/"r12.py"),"250","1",str(S/"l6.json")],env=os.environ|{"SPEC_TUNING":str(tf)},capture_output=True,text=True)
        print("#### ladder", lad, "loose", loose, r.stderr[-400:] if r.returncode else ""); print(r.stdout, flush=True)
'@ | Set-Content -Encoding utf8 $s\scan6.py
py -3 -B $s\scan6.py 2>&1 | Out-File -Encoding utf8 $s\scan6.txt
$t = Get-Content $s\scan6.txt; $t | Select-String '####|^\{|hold6|run12|reckless|   ai' | % { $_.Line -replace 'growth','g' -replace '"FIN_BOOM_BASE": 2.1, ','' -replace 'LEV_','' -replace 'mania [\d.]+ ','' }
