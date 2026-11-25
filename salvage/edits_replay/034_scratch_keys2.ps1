$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"
$code = @'
import sys, json, multiprocessing as mp
sys.path.insert(0, r"G:\GameDev\speculative-markets\tools\tuner"); sys.path.insert(0, r"G:\GameDev\_claude_scratch\tune_fresh")
import engine, lab
d = engine.defaults()
print(json.dumps({k: v for k, v in d.items() if k != "inputs"}, default=str)[:800]); print(list(d.get("inputs", {}).items())[:40])
if __name__ == "__main__":
    cur = lab.current(); base = lab.candidates(cur, {}, {}, 1, 1)[0]
    with mp.get_context("spawn").Pool(lab.CORES) as pool:
        r = lab.sweep({"list": [base], "economies": 100, "seed": 5, "save": False}, pool, cur)
    c = r["cands"][0]
    print(sorted(c["metrics"]["passive"])); print(sorted(c["bands"]["passive"]) if c["bands"] else None)
'@; [IO.File]::WriteAllText("$sp\keys2.py",$code); py -3 -B "$sp\keys2.py" | Select-Object -Last 4; Select-String -Path tools\tuner\engine.py -Pattern "eighten|volatil" | Select-Object -First 12 | ForEach-Object { "$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(160,$_.Line.Trim().Length)))" }; Get-ChildItem G:\GameDev\_claude_scratch\tune_fresh | Select-Object Name; Select-String -Path G:\GameDev\_claude_scratch\tune_fresh\*.py -Pattern "eighten|HEIGHT" | Select-Object -First 8 | ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(200,$_.Line.Trim().Length)))" }; Select-String -Path tools\*.py -Pattern "BUST_PER_HYPE|BURST_PER_HEAT" | ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(160,$_.Line.Trim().Length)))" }
