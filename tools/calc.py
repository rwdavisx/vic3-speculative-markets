"""A bar's tooltip as vanilla's Liberty Desire: the change expected next month, then a line for each cause,
"+x from y", the lines adding up to it. Each cause is a script value, read by the monthly update (through the
total) and by the tooltip, so the forecast is the update's own figure. 1.2: Speculative Excess first (journal.py)."""

SHOWN_FROM = 0.05  # a line shows from this size either way (it reads 0.1 at one decimal)


def chain(name, base, parts):
    """Script values for base times each (condition, multiplier) part while its condition holds: {name}_0 the base
    (a script value body), {name}_<i> what part i adds to what came before it, {name} the total. Returns the script
    text and the script values of the lines, in order."""
    out, run, lines = [f"{name}_0 = {{\n{base}}}\n"], f"{name}_0", [f"{name}_0"]
    for i, (cond, n) in enumerate(parts, 1):
        out.append(f"{name}_{i} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {cond} }}\n\t\tvalue = {run}\n"
                   f"\t\tmultiply = {n - 1:g}\n\t}}\n}}\n{name}_r{i} = {{\n\tvalue = {run}\n\tadd = {name}_{i}\n}}\n")
        run = f"{name}_r{i}"
        lines.append(f"{name}_{i}")
    return "".join(out) + f"{name} = {{\n\tvalue = {run}\n}}\n", lines


def shows(value):
    """GUI test: a line of this GUI value shows."""
    return f"GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({value}), '(CFixedPoint){SHOWN_FROM}')"


def lines(rows, sv):
    """Loc: a line for each (script value, line key) that shows; sv makes a script value a GUI value. The line keys'
    texts are the caller's: "\\n[value|fmt] from $LABEL$" (line())."""
    return "".join(f"[AddLocalizationIf({shows(sv(n))}, '{key}')]" for n, key in rows)


def line(value, fmt, label):
    """A line's text: vanilla's PROGRESS_BAR_VALUE_FORMAT_MONTHLY, fmt +=1 when more is good, -=1 when more is bad."""
    return f"\\n[{value}|{fmt}] from {label}"


def progress(rows, t="\t\t"):
    """A scripted progress bar's monthly_progress lines for (script value, desc key), each while it shows: the
    journal's own breakdown ("+x from <desc>")."""
    return "".join(f"{t}if = {{\n{t}\tlimit = {{ OR = {{ {n} >= {SHOWN_FROM} {n} <= -{SHOWN_FROM} }} }}\n"
                   f"{t}\tadd = {{\n{t}\t\tdesc = \"{key}\"\n{t}\t\tvalue = {n}\n{t}\t}}\n{t}}}\n" for n, key in rows)


if __name__ == "__main__":
    text, names = chain("x", "\tvalue = 10\n", [("a = yes", 0.75), ("b = yes", 1.5)])
    assert names == ["x_0", "x_1", "x_2"] and "multiply = -0.25" in text and "multiply = 0.5" in text
    assert "x_2 = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { b = yes }\n\t\tvalue = x_r1\n" in text and "x = {\n\tvalue = x_r2\n}" in text
    print("ok")
