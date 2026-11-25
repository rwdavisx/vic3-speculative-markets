$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
from pathlib import Path
p=Path("beta/changelog_1.3.1-beta.4.bbcode"); t=p.read_text(encoding="utf-8"); a=" (was 6%), so it can no longer pass 100%."
assert a in t; p.write_text(t.replace(a," (was 6%)."),encoding="utf-8",newline="\n")
'@ | Set-Content -Encoding utf8 $s\n2.py; py -3 -B $s\n2.py
py -3 -B tools/steam_upload.py plan beta 2>&1 | select -First 25
