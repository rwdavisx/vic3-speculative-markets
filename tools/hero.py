"""The Speculation tab's top row (2026-11-21): what the market is doing to our economy right now, in four tiles.
Each figure adds up the market's own modifiers on the country (mood bands, panic, leverage, Bad Debts, construction
booms, the Long Depression) by the same constants and multipliers they are applied with, so the tile shows the
market's part only, not the country's totals."""
import cycle
import icons
import depression
import leverage
from market_tab import P, W, fx, sv, ind, block, header

TILES = [  # key, vanilla icon, big-number format
    ("invest", icons.path("so_invest"), "+=%0"),
    ("tp", icons.path("so_tp"), "+=%1"),
    ("build", icons.path("so_build"), "+=%0"),
    ("trade", icons.path("so_trade"), "+=%0"),
]
GAP, TILE_H = 4, 118
TILE_W = (W - 3 * GAP) // 4
INVEST = ("capitalists", "aristocrats", "shopkeepers")


def _if(cond, body):
    return f"\tif = {{\n\t\tlimit = {{ {cond} }}\n\t\t{body}\n\t}}\n"


def _sum(name, parts):
    return f"{name} = {{\n\tvalue = 0\n" + "".join(f"\tadd = {p}\n" for p in parts) + "}"


def values(band_invest, band_rate, band_trade, panic_invest, panic_tp, rescue_cut):
    """Script values (fractions) for the tiles and their tooltip lines."""
    bands = {f"spec_conf_{t}": {"invest": m, "rate": band_rate.get(t, 0), "trade": band_trade.get(t, 0)} for t, m in band_invest.items()}
    bands["spec_conf_panic_held"] = {"invest": 0, "rate": band_rate["panic"], "trade": band_trade["panic"]}
    mood = lambda what: "".join(_if(f"has_modifier = {m}", f"add = {d[what]:g}") for m, d in bands.items() if d[what])
    ld = lambda key: "".join(_if(f"has_modifier = {m}", f"add = {{ value = spec_ld_strength multiply = {mods[key]:g} }}")
                             for m, (_, mods) in depression.MODS.items() if mods.get(key))
    rescued = f"\tif = {{\n\t\tlimit = {{ has_variable = spec_rescued }}\n\t\tmultiply = {rescue_cut:g}\n\t}}\n"
    panic = lambda n: f"\tvalue = 0\n{_if('has_modifier = spec_panic', f'value = {n:g}')}{rescued}"
    out = [f"spec_so_invest_mood = {{\n\tvalue = 0\n{mood('invest')}}}",
           f"spec_so_invest_panic = {{\n{panic(panic_invest)}}}",
           f"spec_so_invest_ld = {{\n\tvalue = 0\n{ld(f'state_{INVEST[0]}_investment_pool_efficiency_mult')}}}",
           f"spec_so_tp_panic = {{\n{panic(panic_tp)}}}",
           f"spec_so_trade_mood = {{\n\tvalue = 0\n{mood('trade')}}}",
           f"spec_so_trade_ld = {{\n\tvalue = 0\n{ld('state_trade_quantity_mult')}}}",
           f"spec_so_rate_mood = {{\n\tvalue = 0\n{mood('rate')}}}",
           f"spec_so_rate_ld = {{\n\tvalue = 0\n{ld('country_loan_interest_rate_mult')}}}",
           f"spec_so_build_ld = {{\n\tvalue = 0\n{ld('state_construction_mult')}}}",
           # the share of private construction a panic's credit crunch takes (generate: spec_panic_cut_shown)
           f"spec_so_private = {{\n\tvalue = 0\n{_if('has_modifier = spec_panic_crunch', 'value = { value = spec_panic_cut_shown multiply = -1 }')}}}"]
    invest, tp = ["spec_so_invest_mood", "spec_so_invest_panic", "spec_so_invest_ld"], ["spec_so_tp_panic"]
    if leverage.ON:  # the leverage values are in percent
        out += [f"spec_so_tp_lev = {{\n\tvalue = spec_lev_boom_pct\n\tdivide = 100\n}}",
                f"spec_so_tp_debts = {{\n\tvalue = 0\n{_if('has_modifier = spec_credit_crunch_v2', 'value = { value = spec_crunch_tp_pct divide = -100 }')}}}",
                f"spec_so_invest_debts = {{\n\tvalue = 0\n{_if('has_modifier = spec_credit_crunch_v2', 'value = { value = spec_crunch_invest_pct divide = -100 }')}}}"]
        invest.append("spec_so_invest_debts")
        tp = ["spec_so_tp_lev", "spec_so_tp_debts"] + tp
    groups = sorted(cycle._GROUPS) if cycle.ON else []
    assert groups or not cycle.ON
    out += [f"spec_so_build_n = {{\n\tvalue = 0\n" + "".join(_if(f"spec_bb_{g} > 0", "add = 1") for g in groups) + "}",
            # spec_bb_* is 1 at Eager and 2 at Feverish (cycle.BB_STEP each): the fastest group's gain
            f"spec_so_build_top = {{\n\tvalue = 0\n" + "".join(
                _if("OR = { " + " ".join(f"spec_bb_{g} >= {n}" for g in groups) + " }", f"value = {n * cycle.BB_STEP:g}")
                for n in (1, 2)) + "}",
            # the tile: what a panic takes from private construction, else the fastest booming industry's gain
            f"spec_so_build = {{\n\tvalue = spec_so_build_top\n{_if('has_modifier = spec_panic_crunch', 'value = spec_so_private')}}}",
            _sum("spec_so_invest", invest), _sum("spec_so_tp", tp),
            _sum("spec_so_trade", ["spec_so_trade_mood", "spec_so_trade_ld"]), _sum("spec_so_rate", ["spec_so_rate_mood", "spec_so_rate_ld"])]
    # the tiles' real amounts: the market's part of a total that already carries its multiplier m is total * m / (1 + m)
    part = lambda name, total, m: f"{name} = {{\n\tvalue = {total}\n\tmultiply = {m}\n\tdivide = {{ value = {m} add = 1 min = 0.05 }}\n}}"
    out += [part("spec_so_invest_amt", "investment_pool_gross_income", "spec_so_invest"), part("spec_so_tp_amt", "gdp", "spec_so_tp")]
    return out


def _tile(key, icon, _fmt):
    return f"""widget = {{
	size = {{ {TILE_W} {TILE_H} }}
	background = {{
		using = entry_bg
	}}
	tooltip = "SPEC_SO_{key.upper()}_TT"
	icon = {{
		size = {{ 38 38 }}
		position = {{ 0 8 }}
		parentanchor = hcenter
		texture = "{icon}"
	}}
	textbox = {{
		size = {{ {TILE_W} 30 }}
		position = {{ 0 46 }}
		align = center|nobaseline
		using = fontsize_xl
		text = "SPEC_SO_{key.upper()}_BIG"
	}}
	textbox = {{
		size = {{ {TILE_W - 10} 40 }}
		position = {{ 5 74 }}
		align = hcenter|top
		multiline = yes
		elide = right
		using = fontsize_small
		default_format = "#weak"
		text = "SPEC_SO_{key.upper()}_LABEL"
	}}
}}
"""


def section():
    row = f"""flowcontainer = {{
	parentanchor = hcenter
	spacing = {GAP}
	margin_top = 4
	margin_bottom = 8
{ind("".join(_tile(*t) for t in TILES), 1)}}}
"""
    return block(header("SPEC_H_SOWHAT"), row)


def loc():
    f = lambda n, fmt: f"[{sv(n)}|{fmt}]"
    line = lambda n, fmt, label: f"[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({sv(n)}), {fx('0.0005')}), 'SPEC_SO_L_{n.upper()}')]"
    rows = {
        "invest": [("spec_so_invest_mood", "+=%0", "the market's mood"), ("spec_so_invest_panic", "+=%0", "the [concept_spec_financial_panic]"),
                   ("spec_so_invest_debts", "+=%0", "[concept_spec_bad_debts]"), ("spec_so_invest_ld", "+=%0", "the [concept_spec_long_depression]")],
        "tp": [("spec_so_tp_lev", "+=%1", "borrowed money, our [concept_spec_leverage]"), ("spec_so_tp_panic", "+=%1", "the [concept_spec_financial_panic]"),
               ("spec_so_tp_debts", "+=%1", "[concept_spec_bad_debts]")],
        "trade": [("spec_so_trade_mood", "+=%0", "the market's mood"), ("spec_so_trade_ld", "+=%0", "the [concept_spec_long_depression]")],
        "rate": [("spec_so_rate_mood", "-=%0", "the market's mood"), ("spec_so_rate_ld", "-=%0", "the [concept_spec_long_depression]")],
    }
    if not leverage.ON:
        rows["invest"] = [r for r in rows["invest"] if "debts" not in r[0]]
        rows["tp"] = [r for r in rows["tp"] if r[0] == "spec_so_tp_panic"]
    lines, out = {}, []
    for k, rs in rows.items():
        lines[k] = ""
        for n, fmt, label in rs:
            lines[k] += line(n, fmt, label)
            out.append(f' SPEC_SO_L_{n.upper()}: "\\n{f(n, fmt)} from {label}"')
    none = "[AddLocalizationIf(LessThan_CFixedPoint(Abs_CFixedPoint({}), {}), 'SPEC_SO_NONE')]"
    build_none = f"[AddLocalizationIf(And(LessThan_CFixedPoint({sv('spec_so_build_n')}, {fx(1)}), Not(LessThan_CFixedPoint({sv('spec_so_private')}, {fx(0)}))), 'SPEC_SO_BUILD_NONE')]"
    panicking = f"LessThan_CFixedPoint({sv('spec_so_private')}, {fx(0)})"
    head = lambda t: f"#header {t}#!\\n$TOOLTIP_DELIMITER$\\n"
    out += [
        ' SPEC_H_SOWHAT: "Effects on Our Economy"',
        ' SPEC_H_SOWHAT_TT: "What the market is doing to our economy this month, from its mood, booms, panics and debts. '
        'Hover over each figure to see where it comes from."',
        ' SPEC_SO_NONE: "\\nThe market has no effect on it right now."',
        *(f' SPEC_SO_{k.upper()}: "{f("spec_so_" + k, fmt)}"' for k, _, fmt in TILES),
        f' SPEC_SO_INVEST_BIG: "@money![{sv("spec_so_invest_amt")}|=+D]"',
        f' SPEC_SO_TP_BIG: "@money![{sv("spec_so_tp_amt")}|=+D]"',
        f' SPEC_SO_BUILD_BIG: "[SelectLocalization({panicking}, \'SPEC_SO_BUILD\', \'SPEC_SO_BUILD_N\')]"',
        f' SPEC_SO_BUILD_N: "[{sv("spec_so_build_n")}|0]"',
        ' SPEC_SO_TRADE_BIG: "$SPEC_SO_TRADE$"',
        f' SPEC_SO_INVEST_LABEL: "invested a week ({f("spec_so_invest", "+=%0")})"',
        f' SPEC_SO_TP_LABEL: "GDP a year ({f("spec_so_tp", "+=%1")} output)"',
        f' SPEC_SO_BUILD_LABEL: "[SelectLocalization({panicking}, \'SPEC_SO_PRIVATE_LABEL\', \'SPEC_SO_BOOM_LABEL\')]"',
        ' SPEC_SO_PRIVATE_LABEL: "private construction lost to the panic"',
        f' SPEC_SO_BOOM_LABEL: "booming industries ({f("spec_so_build_top", "+=%0")} speed)"',
        ' SPEC_SO_TRADE_LABEL: "goods traded by our merchants"',
        f' SPEC_SO_INVEST_TT: "{head("Investment")}The market changes how efficiently Capitalists, Aristocrats and Shopkeepers invest through the '
        f'[concept_investment_pool] by #v {f("spec_so_invest", "+=%0")}#!.\\n{lines["invest"]}'
        f'{none.format(sv("spec_so_invest"), fx("0.0005"))}"',
        f' SPEC_SO_TP_TT: "{head("Throughput")}The market changes the [concept_throughput] of every building by #v {f("spec_so_tp", "+=%1")}#!.\\n'
        f'{lines["tp"]}{none.format(sv("spec_so_tp"), fx("0.0005"))}"',
        f' SPEC_SO_BUILD_TT: "{head("Construction")}'
        f'[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint({sv("spec_so_build_n")}, {fx(1)}), \'SPEC_SO_BUILD_BOOM\')]'
        f'[AddLocalizationIf(LessThan_CFixedPoint({sv("spec_so_private")}, {fx(0)}), \'SPEC_SO_BUILD_PANIC\')]'
        f'[AddLocalizationIf(LessThan_CFixedPoint({sv("spec_so_build_ld")}, {fx(0)}), \'SPEC_SO_BUILD_LD\')]{build_none}"',
        f' SPEC_SO_BUILD_BOOM: "Booms speed up construction in their industries. #v [{sv("spec_so_build_n")}|0]#! of our industries build up to '
        f'#P {f("spec_so_build_top", "%0")}#! more efficiently.\\n"',
        f' SPEC_SO_BUILD_PANIC: "The [concept_spec_financial_panic] has stopped the banks lending, cutting [concept_private_construction] by '
        f'#N {f("spec_so_private", "%0")}#!.\\n"',
        f' SPEC_SO_BUILD_LD: "The [concept_spec_long_depression] changes construction speed by {f("spec_so_build_ld", "+=%0")}.\\n"',
        ' SPEC_SO_BUILD_NONE: "No industry is booming, so the market adds nothing to construction right now."',
        f' SPEC_SO_TRADE_TT: "{head("Trade")}The market changes how much our merchants trade by #v {f("spec_so_trade", "+=%0")}#!.\\n'
        f'{lines["trade"]}{none.format(sv("spec_so_trade"), fx("0.0005"))}'
        f'[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({sv("spec_so_rate")}), {fx("0.0005")}), \'SPEC_SO_RATE\')]"',
        f' SPEC_SO_RATE: "\\n\\nIt also changes the interest on our [concept_loans] by #v {f("spec_so_rate", "-=%0")}#!.{lines["rate"]}"',
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    cycle._GROUPS["light_industry"] = ["tools"]  # generate fills it through cycle.setup
    v = values({"panic": -0.2, "wary": -0.1, "steady": 0, "buoyant": 0.1, "mania": 0.2}, {"panic": 0.2, "wary": 0.1},
               {"panic": -0.1, "wary": -0.05, "buoyant": 0.05, "mania": 0.1}, -0.4, -0.1, 0.5)
    text = "\n".join(v) + section() + loc()
    assert text.count("{") == text.count("}")
    assert "spec_so_invest = {" in "\n".join(v) and "add = 0.1" in v[0]
    print("hero ok")
