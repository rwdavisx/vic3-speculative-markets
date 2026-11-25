$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
@'
import json, itertools
L=[]
for sp,past,bust in ((25,3,1.5),(30,3,1.5),(25,3,1.75)):
    for x in ({"LEV_CRUNCH_FADE":0.25},{"LEV_RECORD_LOSS":0.4},{"LEV_RECORD_LOSS":0.5},{"LEV_CRUNCH_FADE":0.25,"LEV_RECORD_LOSS":0.4}):
        L.append({"LEV_PANIC_SPAN":sp,"LEV_RECORD_PAST":past,"BUST_PER_HYPE":bust,"LEV_INCOME_FLOOR":0.005,**x})
open(r"C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\g2.json","w").write(json.dumps(L))
'@ | Set-Content -Encoding utf8 $s\g2.py; py -3 -B $s\g2.py
py -3 -B $s\r12b.py 800 2 $s\g2.json
"---"; py -3 -B $s\mania12.py one 800 2 $s\g2.json | ? { $_ -match '/30' -and $_ -match '\{' } | % { $_.Substring([Math]::Max(0,$_.IndexOf('/30')-3)) }
