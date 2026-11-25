$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
Select-String -Path build_scratch\rc_1.3.1\localization\english\*.yml -Pattern 'SPEC_WHY_END_|concept_spec_correction_desc|concept_spec_bust_desc' | % { $l=$_.Line.Trim(); $l.Substring(0,[Math]::Min(700,$l.Length)) }
@'
import re, difflib
def get(p,k):
    for l in open(p,encoding="utf-8-sig"):
        if l.strip().startswith(k+":"): return re.findall(r"[^\s\[\]#]+", l)
A=r"beta\release_131\mod\localization\english\spec_markets_l_english.yml"; B=r"build_scratch\rc_1.3.1\localization\english\spec_markets_l_english.yml"
for k in ("spec_rv_lure_fx","SPEC_RV_LURE_TT","SPEC_LEV_MONTHS_TT"):
    a,b=get(A,k),get(B,k)
    print(k,[(a[i:j],b[m:n]) for t,i,j,m,n in difflib.SequenceMatcher(None,a,b,False).get_opcodes() if t!="equal"])
for k in ("SPEC_LEV_TIER_1_TT","SPEC_LEV_TIER_2_TT","SPEC_LEV_TIER_3_TT","concept_spec_outstanding_credit_desc"): print(" ".join(get(B,k))[:900])
'@ | Set-Content -Encoding utf8 $s\d.py; py -3 -B $s\d.py
git diff --no-index -U0 beta\release_131\mod\gui build_scratch\rc_1.3.1\gui 2>$null | Select-String '^[-+][^-+]' | select -First 24 | % { $_.Line.Trim().Substring(0,[Math]::Min(130,$_.Line.Trim().Length)) }; exit 0
