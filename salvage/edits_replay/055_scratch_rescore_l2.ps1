$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
$j='[{"FIN_BOOM_BASE":2.0},{"FIN_BOOM_BASE":2.1},{"FIN_BOOM_BASE":2.15},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30},{"FIN_BOOM_BASE":2.0,"LEV_PANIC_SPAN":30},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":25},{"FIN_BOOM_BASE":2.1,"CONF_CRASH_MAX":25},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30,"CONF_CRASH_MAX":25},{"FIN_BOOM_BASE":2.1,"EXP_PER_MONTH":0.05},{"FIN_BOOM_BASE":2.1,"CONF_PER_CRASH_HYPE":6},{"FIN_BOOM_BASE":2.1,"BUST_PER_HYPE":2.0},{"FIN_BOOM_BASE":2.1,"LEV_PANIC_SPAN":30,"BUST_PER_HYPE":2.0}]'
[IO.File]::WriteAllText("$s\l2.json",$j)
py -3 -B $s\mania.py one 1000 1 $s\l2.json; '#### values now'; py -3 -B -c "import sys;sys.path[:0]=['tools','tools/tuner'];import lab;c=lab.current();print({k:c[k] for k in ('LEV_PANIC_SPAN','CONF_CRASH_MAX','EXP_PER_MONTH','CONF_PER_CRASH_HYPE','BUST_PER_HYPE')})"
