Get-Content tools\tuning.json -Encoding utf8; "---"; $code = @'
import sys; sys.path.insert(0, r"G:\GameDev\speculative-markets\tools\tuner")
import engine, lab
cur = lab.current()
for s in engine.TUNABLE:
    print(s[0], cur.get(s[0]), s[1:] if len(str(s[1:]))<170 else str(s[1:])[:170])
'@; $p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\keys.py"; Set-Content $p $code -Encoding utf8; py -3 -B $p
