$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"; [IO.File]::WriteAllText("$sp\st.json",'[{},{"FIN_BOOM_BASE":1.0,"CREDIT_RUNOFF_TIGHT":0.0095,"LEV_PANIC_SPAN":55,"LEV_INCOME_FLOOR":0.009,"LEV_RECORD_GAIN":0.01,"LEV_CRUNCH_BUILD":0.05}]'); foreach($s in 9001,9002,9003){"== $s (beta.3, then 1.3 values; AI column on line 2 uses the NEW AI rule)"; py -3 -B "$sp\mania.py" x 1000 $s "$sp\st.json" | Select-Object -Skip 2}
# the 1.3 engine itself, for the old AI rule
$o="$sp\v13"; New-Item -ItemType Directory -Force $o | Out-Null; git archive --format=zip -o "$sp\v13.zip" 25020bb tools; Expand-Archive "$sp\v13.zip" $o -Force
$code=@'
import sys, json, multiprocessing as mp
sys.path.insert(0, sys.argv[1] if len(sys.argv)>1 else r"C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\v13\tools\tuner")
import lab
if __name__ == "__main__":
    print(lab.__file__)
    cur = lab.current(); base = lab.candidates(cur, {}, {}, 1, 1)[0]
    print({k: base.get(k) for k in ("FIN_BOOM_BASE","LEV_PANIC_SPAN","LEV_INCOME_FLOOR","AI_TIGHT")})
    with mp.get_context("spawn").Pool(lab.CORES) as pool:
        for s in (9001, 9002, 9003):
            r = lab.sweep({"list": [base], "economies": 1000, "seed": s, "save": False, "bot": "ai", "targets": [{"metric":"mania_pct","who":"ai","aim":1,"lo":0,"hi":9,"weight":1}]}, pool, cur)
            M = r["cands"][0]["metrics"]["ai"]
            n = lambda x: x.get("mean") if isinstance(x, dict) else x
            print(s, {k: round(n(M[k]), 2) for k in ("mania_pct","panics_per_century","lev_mean","up_pct","growth_core","growth_edge","output_pct") if k in M and n(M[k]) is not None})
'@; [IO.File]::WriteAllText("$sp\old_ai.py",$code); py -3 -B "$sp\old_ai.py"; "== beta.3 AI"; py -3 -B "$sp\old_ai.py" G:\GameDev\speculative-markets\tools\tuner
