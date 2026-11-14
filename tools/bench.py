"""The history benchmarks (stats.MOD) for each finished run, with the target range.

Usage: py -3 tools/bench.py [--decade 1830] <runNN dir or session dir>...  (--decade: that decade only, to set a short
run beside longer ones)"""
import json
import sys
from pathlib import Path

import stats


def runs(paths):
    for p in map(Path, paths):
        yield from ([p] if (p / "meta.json").exists() else [m.parent for m in sorted(p.glob("run*/meta.json"))])


if __name__ == "__main__":
    args = sys.argv[1:]
    decade = args[args.index("--decade") + 1] if "--decade" in args else None
    paths = [a for a in args if a != "--decade" and a != decade]
    metas = [(r, json.loads((r / "meta.json").read_text(encoding="utf-8"))) for r in runs(paths)]
    block = lambda m: (m.get("mod") or {}).get("decades", {}).get(decade) if decade else (m.get("mod") or {}).get("total")
    metas = [(r, m) for r, m in metas if block(m)]
    print("reading".ljust(56) + "".join(f"{r.parent.name[-12:]}/{r.name}".rjust(24) for r, _ in metas) + "   target")
    for key, name, unit, target, _ in stats.MOD:
        vals = [stats.reading(block(m), key) for _, m in metas]
        f = (lambda x: f"{100 * x:.2f}%" if unit == "%" else f"{x:.2f}")
        tgt = "" if not target else (f"{f(target[0])} to {f(target[1])}" + (f" ({f(target[2])})" if len(target) > 2 else ""))
        print(name[:55].ljust(56) + "".join((f(v) if v is not None else "-").rjust(24) for v in vals) + "   " + tgt)
