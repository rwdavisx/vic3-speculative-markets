$t=@'
import difflib,re
a=open(r'C:\Users\rwdav\.claude\projects\G--GameDev-speculative-markets\9c1684c5-3088-47d7-b848-def38336bbe9\tool-results\artifact-c4e0c686-1795372349-1375.html',encoding='utf-8').read()
a=a[a.index('<title>'):]; a=re.sub(r'\s*</body></html>\s*$','\n',a)
b=open(r'G:\GameDev\_claude_scratch\v130\waterworks.html',encoding='utf-8').read()
A=a.split('\n');B=b.split('\n')
print(len(A),len(B))
out=[l if len(l)<900 else l[:150]+'<<CUT>>' for l in difflib.unified_diff(A,B,lineterm='',n=0)]
open(r'C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\ww.diff','w',encoding='utf-8').write('\n'.join(out))
print(len(out),sum(map(len,out)))
'@
[IO.File]::WriteAllText("$env:TEMP\zz.py",$t); py -3 -B $env:TEMP\zz.py
