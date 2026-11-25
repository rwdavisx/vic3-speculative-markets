$code = @'
import json
m = json.load(open(r"G:\GameDev\speculative-markets\tools\tuner\keymap.json", encoding="utf-8"))
print(m.keys() if isinstance(m, dict) else type(m)); print(m.get("made"), m.get("n"))
print(json.dumps(m)[:1500])
'@; $p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\km.py"; Set-Content $p $code -Encoding utf8; py -3 -B $p; Select-String -Path tools\generate.py,tools\cycle.py -Pattern "mania" -CaseSensitive:$false | Select-Object -First 60 | ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(170,$_.Line.Trim().Length)))" }
