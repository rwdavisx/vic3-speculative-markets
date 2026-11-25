$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
@'
from pathlib import Path
import json
R = Path(r"G:\GameDev\speculative-markets\tools")
def ed(f, *pairs):
    p = R/f; raw = p.read_bytes(); crlf = b"\r\n" in raw; t = raw.decode("utf-8").replace("\r\n", "\n")
    for a, b in pairs:
        assert t.count(a) == 1, (f, t.count(a), a); t = t.replace(a, b)
    p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
ed("leverage.py",
 ('RECORD_FADE = tuning.get("LEV_RECORD_FADE", RECORD_GAIN)  # the same share when leverage is below it: a clean way down keeps it longer\n', ''),
 ('f"spec_lev_record_to = {{\\n\\tvalue = spec_lev_record_gap\\n\\tif = {{\\n\\t\\tlimit = {{ spec_lev_record_gap < 0 }}\\n\\t\\tmultiply = {RECORD_FADE:g}\\n\\t}}\\n\\telse = {{\\n\\t\\tmultiply = {RECORD_GAIN:g}\\n\\t}}\\n}}",',
  'f"spec_lev_record_to = {{\\n\\tvalue = spec_lev_record_gap\\n\\tmultiply = {RECORD_GAIN:g}\\n}}",'))
ed("tuner/engine.py",
 ('    ("LEV_RECORD_FADE", lv, "RECORD_FADE", "Leverage", "Sound Credit: share of the way closed a calm month while leverage is below it"),\n', ''),
 ('built = self.record + gap * np.where(gap < 0, K["LEV_RECORD_FADE"], K["LEV_RECORD_GAIN"])', 'built = self.record + gap * K["LEV_RECORD_GAIN"]'))
p = R/"tuning.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
d.update({"FIN_BOOM_BASE": 2.1, "LEV_PANIC_SPAN": 20, "LEV_CRUNCH_BUILD": 0.1, "BUST_PER_HYPE": 2.0, "LEV_RECORD_PAST": 2, "LOOSE_CREDIT": 2.5, "LEV_LADDER": [3, 9, 11, 12], "AI_LEV_SCALE": 1.2})
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
p = R/"tuner/targets.json"; t = p.read_text(encoding="utf-8")
t = t.replace('"run10', '"run12').replace('"blind10', '"blind12').replace("up to 10 months", "up to 12 months").replace("reaches 10 months a few times a century", "reaches 12 months from time to time")
p.write_text(t, encoding="utf-8", newline="\n")
'@ | Set-Content -Encoding utf8 $s\final.py
py -3 -B $s\final.py; py -3 -B tools\leverage.py | select -Last 1; Select-String tools\tuner\targets.json -Pattern 'run12|runs12' | % Line
Get-Content tools\leverage.py | Select-Object -Skip 649 -First 16 | % { $_.Substring(0,[Math]::Min(330,$_.Length)) }
Select-String -Path tools\*.py -Pattern "STANCE_CREDIT|'8 months'|8 months|to 12 months|60%" | % { "$($_.Filename):$($_.LineNumber) " + $_.Line.Trim().Substring(0,[Math]::Min(170,$_.Line.Trim().Length)) }
Select-String -Path tools\leverage.py -Pattern 'AI_LEV_SCALE|AI_LIMIT =' | % Line; py -3 -B -c "import sys;sys.path[:0]=['tools'];import leverage as l;print(l.AI_LIMIT,l.LADDER,l.LADDER_STEPS)"
