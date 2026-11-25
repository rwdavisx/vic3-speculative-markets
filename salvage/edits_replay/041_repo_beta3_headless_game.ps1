$sp="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad"
$code=@'
import os, subprocess, sys
from pathlib import Path
ROOT = Path(r"G:\GameDev\speculative-markets"); T = ROOT / "tools"
sys.path[:0] = [str(T), str(T / "tuner")]
import windows, sweep
windows.BUILD = ROOT / "build_scratch/beta3_test/build"          # --log build of the staged beta.3
windows.build()                                                  # stops unless it is beta.3 plus logging only
sweep.WORK = ROOT / "build_scratch/beta3_test/user"; sweep.WORK.mkdir(parents=True, exist_ok=True)
windows.keep_rivals(sweep)
print("build ok, starting", flush=True)
sweep.run("beta3", {"beta3": windows.BUILD}, 1, 30, 1, timeout=150, log=lambda s: print(s, flush=True))
'@; [IO.File]::WriteAllText("$sp\beta3_game.py",$code)
py -3 -B "$sp\beta3_game.py"
