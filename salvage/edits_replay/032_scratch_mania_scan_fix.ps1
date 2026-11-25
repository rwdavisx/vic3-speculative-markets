$p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\mania.py"; $t=[IO.File]::ReadAllText($p); $t=$t.Replace('g = lambda b, k: (M[b].get(k) if M[b].get(k) is not None else float("nan"))','g = lambda b, k: num(M[b].get(k))').Replace('def main(','def num(x):
    if isinstance(x, dict): x = x.get("mean", x.get("avg", next(iter(x.values()))))
    return float("nan") if x is None else x
def main(').Replace('G = {b: g(b, "growth_core") for b in M}','G = {b: g(b, "growth_core") for b in M}
        if c["id"] == 0: print({k: v for k, v in M["passive"].items() if k in ("mania_pct", "growth_core", "mania_to_panic_pct")})'); [IO.File]::WriteAllText($p,$t); py -3 -B $p one 500 9001
