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
    ("build", icons.path("so_build"), "+=%1"),
    ("trade", icons.path("so_trade"), "+=%0"),
]
ROW_H, ICON, PCT_W = 60, 52, 84  # a ledger row each: the icon, a sentence with the figure in it, the percent at the right
INVEST = ("capitalists", "aristocrats", "shopkeepers")


BUILD_FLOOR = 0.05  # vanilla's MIN_CONSTRUCTION_EFFICIENCY

def _if(cond, body):
    return f"\tif = {{\n\t\tlimit = {{ {cond} }}\n\t\t{body}\n\t}}\n"


def _sum(name, parts):
    return f"{name} = {{\n\tvalue = 0\n" + "".join(f"\tadd = {p}\n" for p in parts) + "}"


def values(band_invest, band_rate, band_trade, panic_invest, panic_tp, panic_build, rescue_cut):
    """Script values (fractions) for the tiles and their tooltip lines."""
    bands = {f"spec_conf_{t}": {"invest": m, "rate": band_rate.get(t, 0), "trade": band_trade.get(t, 0)} for t, m in band_invest.items()}
    bands["spec_conf_panic_held"] = {"invest": 0, "rate": band_rate["panic"], "trade": band_trade["panic"]}
    mood = lambda what: "".join(_if(f"has_modifier = {m}", f"add = {d[what]:g}") for m, d in bands.items() if d[what])
    ld = lambda key: "".join(_if(f"has_modifier = {m}", f"add = {{ value = spec_ld_strength multiply = {mods[key]:g} }}")
                             for m, (_, mods) in depression.MODS.items() if mods.get(key))
    rescued = f"\tif = {{\n\t\tlimit = {{ has_variable = spec_rescued }}\n\t\tmultiply = {rescue_cut:g}\n\t}}\n"
    panic = lambda n: f"\tvalue = 0\n{_if('has_modifier = spec_panic', f'value = {n:g}')}{rescued}\tmultiply = spec_impact\n"
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
    build = ["spec_so_build_panic", "spec_so_build_ld"]
    out.append(f"spec_so_build_panic = {{\n{panic(panic_build)}}}")
    if leverage.ON:  # the leverage values are in percent
        out += [f"spec_so_tp_lev = {{\n\tvalue = spec_lev_boom_pct\n\tdivide = 100\n}}",
                f"spec_so_tp_debts = {{\n\tvalue = 0\n{_if('has_modifier = spec_credit_crunch_v2', 'value = { value = spec_crunch_tp_pct divide = -100 }')}}}",
                f"spec_so_invest_debts = {{\n\tvalue = 0\n{_if('has_modifier = spec_credit_crunch_v2', 'value = { value = spec_crunch_invest_pct divide = -100 }')}}}"]
        invest.append("spec_so_invest_debts")
        out += [f"spec_so_build_debts = {{\n\tvalue = 0\n{_if('has_modifier = spec_credit_crunch_v2', 'value = { value = spec_crunch_build_pct divide = -100 }')}}}"]
        build.append("spec_so_build_debts")
        if leverage.RECORD:
            out.append("spec_so_build_record = {\n\tvalue = spec_lev_record_pct\n\tdivide = 100\n}")
            build.insert(0, "spec_so_build_record")
        tp = ["spec_so_tp_lev", "spec_so_tp_debts"] + tp
        if leverage.SMOOTH and leverage.INV_FULL:  # the smooth bonus's investment, beside what Bad Debts take
            out.append("spec_so_invest_lev = {\n\tvalue = spec_lev_boom_inv_pct\n\tdivide = 100\n}")
            invest.insert(0, "spec_so_invest_lev")
    groups = sorted(cycle._GROUPS) if cycle.ON else []
    assert groups or not cycle.ON
    out += [f"spec_so_build_n = {{\n\tvalue = 0\n" + "".join(_if(f"has_variable = spec_bbv_{g} var:spec_bbv_{g} > 0", "add = 1") for g in groups) + "}",
            # spec_bbv_* is in steps (cycle.BB_STEP each): the fastest group's gain
            f"spec_so_build_top = {{\n\tvalue = 0\n" + "".join(
                _if(f"has_variable = spec_bbv_{g}", f"min = var:spec_bbv_{g}") for g in groups) + f"\tmultiply = {cycle.BB_STEP:g}\n}}",
            # the tile: what Sound Credit, a panic, Bad Debts and the Long Depression do to all construction
            _sum("spec_so_build", build), _sum("spec_so_invest", invest)[:-1] + "\tmin = -1\n}",  # investors cannot put in less than nothing
             _sum("spec_so_tp", tp),
            _sum("spec_so_trade", ["spec_so_trade_mood", "spec_so_trade_ld"]), _sum("spec_so_rate", ["spec_so_rate_mood", "spec_so_rate_ld"])]
    # the tiles' real amounts: the market's part of a total that already carries its multiplier m is total * m / (1 + m)
    part = lambda name, total, m: f"{name} = {{\n\tvalue = {total}\n\tmultiply = {m}\n\tdivide = {{ value = {m} add = 1 min = 0.05 }}\n}}"
    out += [part("spec_so_invest_amt", "investment_pool_gross_income", "spec_so_invest"), part("spec_so_tp_amt", "gdp", "spec_so_tp")]
    return out


def _active(key):
    """GUI test: the market is doing something to this part of the economy right now."""
    some = lambda n: f"GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({sv(n)}), {fx('0.0005')})"
    if key == "build":
        return f"Or(GreaterThanOrEqualTo_CFixedPoint({sv('spec_so_build_n')}, {fx(1)}), Or(LessThan_CFixedPoint({sv('spec_so_private')}, {fx(0)}), {some('spec_so_build')}))"
    return some(f"spec_so_{key}")


def _tile(key, icon, _fmt):
    # a row of the ledger; an effect the market isn't having right now fades back
    return f"""widget = {{
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_SO_{key.upper()}_TT"
	alpha = "[TransparentIfFalse({_active(key)})]"
	icon = {{
		size = {{ {ICON} {ICON} }}
		position = {{ 6 0 }}
		parentanchor = vcenter
		texture = "{icon}"
	}}
	textbox = {{
		size = {{ {W - ICON - 22 - PCT_W} {ROW_H} }}
		position = {{ {ICON + 16} 0 }}
		align = left|vcenter
		multiline = yes
		elide = right
		text = "SPEC_SO_{key.upper()}_SAY"
	}}
	textbox = {{
		size = {{ {PCT_W} {ROW_H} }}
		parentanchor = right
		position = {{ -8 0 }}
		align = right|vcenter
		using = fontsize_large
		text = "SPEC_SO_{key.upper()}_PCT"
	}}
}}
"""


def section():
    rule = f"divider_clean = {{ size = {{ {W - 20} 2 }} parentanchor = hcenter }}\n"
    row = f"""flowcontainer = {{
	parentanchor = hcenter
	direction = vertical
	margin_top = 2
	margin_bottom = 8
{ind(rule.join(_tile(*t) for t in TILES), 1)}}}
"""
    return block(header("SPEC_H_SOWHAT"), row)


def _say():
    """Each row's sentence, worded by the figure's sign, and its percent."""
    a = lambda n: f"Abs_CFixedPoint({sv(n)})"
    pos, neg = (lambda n: f"GreaterThanOrEqualTo_CFixedPoint({sv(n)}, {fx('0.0005')})"), (lambda n: f"LessThanOrEqualTo_CFixedPoint({sv(n)}, {fx('-0.0005')})")
    pick = lambda k, n: f"[SelectLocalization({pos(n)}, 'SPEC_SO_{k}_UP', SelectLocalization({neg(n)}, 'SPEC_SO_{k}_DOWN', 'SPEC_SO_{k}_FLAT'))]"
    pct = lambda n, fmt: f"[SelectLocalization(Or({pos(n)}, {neg(n)}), 'SPEC_SO_PCT_{n.upper()}', 'SPEC_SO_DASH')]"
    booming = f"GreaterThanOrEqualTo_CFixedPoint({sv('spec_so_build_n')}, {fx(1)})"
    out = [f' SPEC_SO_INVEST_SAY: "{pick("INVEST", "spec_so_invest")}"',
           f' SPEC_SO_INVEST_UP: "Investors put in #P @money![{a("spec_so_invest_amt")}|D]#! more each week"',
           # past half, the money lost is too rough a guess (part() divides by what is left): the share instead
           f' SPEC_SO_INVEST_DOWN: "[SelectLocalization(LessThan_CFixedPoint({sv("spec_so_invest")}, {fx("-0.5")}), \'SPEC_SO_INVEST_CUT\', \'SPEC_SO_INVEST_LESS\')]"',
           f' SPEC_SO_INVEST_LESS: "Investors put in #N @money![{a("spec_so_invest_amt")}|D]#! less each week"',
           f' SPEC_SO_INVEST_CUT: "[SelectLocalization(LessThan_CFixedPoint({sv("spec_so_invest")}, {fx("-0.995")}), \'SPEC_SO_INVEST_STOP\', \'SPEC_SO_INVEST_SHARE\')]"',
           f' SPEC_SO_INVEST_SHARE: "Investors put in #N [{a("spec_so_invest")}|%0]#! less each week"',
           ' SPEC_SO_INVEST_STOP: "Investors have #N stopped#! putting money in"',
           ' SPEC_SO_INVEST_FLAT: "Investment runs at its normal pace"',
           f' SPEC_SO_TP_SAY: "{pick("TP", "spec_so_tp")}"',
           f' SPEC_SO_TP_UP: "Our economy makes #P @money![{a("spec_so_tp_amt")}|D]#! more a year"',
           f' SPEC_SO_TP_DOWN: "Our economy makes #N @money![{a("spec_so_tp_amt")}|D]#! less a year"',
           ' SPEC_SO_TP_FLAT: "Output runs at its normal level"',
           f' SPEC_SO_BUILD_SAY: "[SelectLocalization({pos("spec_so_build")}, \'SPEC_SO_BUILD_UP\', SelectLocalization({neg("spec_so_build")}, \'SPEC_SO_BUILD_DOWN\', SelectLocalization({booming}, \'SPEC_SO_BUILD_BOOMS\', \'SPEC_SO_BUILD_FLAT\')))]"',
           f' SPEC_SO_BUILD_UP: "We build #P [{a("spec_so_build")}|%1]#! more efficiently"',
           f' SPEC_SO_BUILD_DOWN: "We build #N [{a("spec_so_build")}|%1]#! less efficiently"',
              f' SPEC_SO_BUILD_BOOMS: "#P [{sv("spec_so_build_n")}|0]#! booming [SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({sv("spec_so_build_n")}, {fx(2)}), \'SPEC_SO_INDUSTRIES\', \'SPEC_SO_INDUSTRY\')] faster"',
           ' SPEC_SO_INDUSTRY: "industry builds"', ' SPEC_SO_INDUSTRIES: "industries build"',
           ' SPEC_SO_BUILD_FLAT: "No major good is booming"',
           f' SPEC_SO_TRADE_SAY: "{pick("TRADE", "spec_so_trade")}"',
           f' SPEC_SO_TRADE_UP: "Our merchants trade #P [{a("spec_so_trade")}|%0]#! more goods"',
           f' SPEC_SO_TRADE_DOWN: "Our merchants trade #N [{a("spec_so_trade")}|%0]#! fewer goods"',
           ' SPEC_SO_TRADE_FLAT: "Our merchants trade as normal"',
           ' SPEC_SO_DASH: "#weak –#!"',
           f' SPEC_SO_INVEST_PCT: "{pct("spec_so_invest", "+=%0")}"', f' SPEC_SO_PCT_SPEC_SO_INVEST: "[{sv("spec_so_invest")}|+=%0]"',
           f' SPEC_SO_TP_PCT: "{pct("spec_so_tp", "+=%1")}"', f' SPEC_SO_PCT_SPEC_SO_TP: "[{sv("spec_so_tp")}|+=%1]"',
           f' SPEC_SO_BUILD_PCT: "{pct("spec_so_build", "+=%1")}"', f' SPEC_SO_PCT_SPEC_SO_BUILD: "[{sv("spec_so_build")}|+=%1]"',
           f' SPEC_SO_TRADE_PCT: "{pct("spec_so_trade", "+=%0")}"', f' SPEC_SO_PCT_SPEC_SO_TRADE: "[{sv("spec_so_trade")}|+=%0]"']
    return out


def loc():
    f = lambda n, fmt: f"[{sv(n)}|{fmt}]"
    line = lambda n, fmt, label: f"[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({sv(n)}), {fx('0.0005')}), 'SPEC_SO_L_{n.upper()}')]"
    rows = {
        "invest": [("spec_so_invest_mood", "+=%0", "the market's mood"), ("spec_so_invest_panic", "+=%0", "the [concept_spec_financial_panic]"),
                   ("spec_so_invest_debts", "+=%0", "[concept_spec_bad_debts]"), ("spec_so_invest_ld", "+=%0", "the [concept_spec_long_depression]")],
        "tp": [("spec_so_tp_lev", "+=%1", "borrowed money, our [concept_spec_leverage]"), ("spec_so_tp_panic", "+=%1", "the [concept_spec_financial_panic]"),
               ("spec_so_tp_debts", "+=%1", "[concept_spec_bad_debts]")],
        "build": [("spec_so_build_record", "+=%1", "our sound credit"), ("spec_so_build_panic", "+=%1", "the [concept_spec_financial_panic]"),
                  ("spec_so_build_debts", "+=%1", "[concept_spec_bad_debts]"), ("spec_so_build_ld", "+=%1", "the [concept_spec_long_depression]")],
        "trade": [("spec_so_trade_mood", "+=%0", "the market's mood"), ("spec_so_trade_ld", "+=%0", "the [concept_spec_long_depression]")],
        "rate": [("spec_so_rate_mood", "-=%0", "the market's mood"), ("spec_so_rate_ld", "-=%0", "the [concept_spec_long_depression]")],
    }
    if leverage.SMOOTH and leverage.INV_FULL:
        rows["invest"].insert(0, ("spec_so_invest_lev", "+=%0", "borrowed money, our [concept_spec_leverage]"))
    if not leverage.ON:
        rows["invest"] = [r for r in rows["invest"] if "debts" not in r[0]]
        rows["tp"] = [r for r in rows["tp"] if r[0] == "spec_so_tp_panic"]
        rows["build"] = [r for r in rows["build"] if r[0] in ("spec_so_build_panic", "spec_so_build_ld")]
    elif not leverage.RECORD:
        rows["build"] = rows["build"][1:]
    lines, out = {}, []
    for k, rs in rows.items():
        lines[k] = ""
        for n, fmt, label in rs:
            lines[k] += line(n, fmt, label)
            out.append(f' SPEC_SO_L_{n.upper()}: "\\n{f(n, fmt)} from {label}"')
    none = "[AddLocalizationIf(LessThan_CFixedPoint(Abs_CFixedPoint({}), {}), 'SPEC_SO_NONE')]"
    build_none = f"[AddLocalizationIf(And(LessThan_CFixedPoint({sv('spec_so_build_n')}, {fx(1)}), Not(LessThan_CFixedPoint({sv('spec_so_private')}, {fx(0)}))), 'SPEC_SO_BUILD_NONE')]"
    # each booming industry on one line; hovering it lists the goods that make it boom, adding up to its gain
    booms = ""
    for grp, gs in sorted(cycle._GROUPS.items()) if cycle.ON else []:
        now = f"Multiply_CFixedPoint({P}.Var('spec_bbv_{grp}').GetValueWithDefault({fx(0)}), {fx(cycle.BB_STEP)})"
        booms += f"[AddLocalizationIf(GreaterThan_CFixedPoint({now}, {fx(0)}), 'SPEC_SO_BB_{grp.upper()}')]"
        parts = "".join(f"[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint({P}.Var('spec_ui_bb_{k}').GetValueWithDefault({fx(0)}), {fx('0.0005')}), 'SPEC_SO_BBG_{k.upper()}')]" for p, _, k in cycle.parts() if p == grp)
        out.append(f' SPEC_SO_BB_{grp.upper()}: "\\n[{now}|+=%1] for #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_SO_BBT_{grp.upper()} $bg_{grp}$#!#!"')
        out.append(f' SPEC_SO_BBT_{grp.upper()}: "#header $bg_{grp}$#!\\n$TOOLTIP_DELIMITER$\\nIts booming goods speed up its construction by [{now}|+=%1].\\n{parts}'
                   f'\\n\\n$SPEC_SO_BUILD_NONE$"')
    for _, g, k in cycle.parts() if cycle.ON else []:
        out.append(f" SPEC_SO_BBG_{k.upper()}: \"\\n[{P}.Var('spec_ui_bb_{k}').GetValueWithDefault({fx(0)})|+=%1] from [GetGoods('{g}').GetName], "
                   f"[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({P}.Var('spec_word_{g}').GetValueWithDefault({fx(0)}), {fx(6)}), 'SPEC_INTEREST_5', 'SPEC_INTEREST_4')]\"")
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
        *_say(),
        f' SPEC_SO_INVEST_TT: "{head("Investment")}The market changes how efficiently Capitalists, Aristocrats and Shopkeepers invest through the '
        f'[concept_investment_pool] by #v {f("spec_so_invest", "+=%0")}#!.\\n{lines["invest"]}'
        f'{none.format(sv("spec_so_invest"), fx("0.0005"))}[AddLocalizationIf(LessThan_CFixedPoint({sv("spec_so_invest")}, {fx("-0.995")}), \'SPEC_SO_INVEST_FLOOR\')]"',
        ' SPEC_SO_INVEST_FLOOR: "\\n#weak It cannot fall below -100%.#!"',
        f' SPEC_SO_TP_TT: "{head("Throughput")}The market changes the [concept_throughput] of every building by #v {f("spec_so_tp", "+=%1")}#!.\\n'
        f'{lines["tp"]}{none.format(sv("spec_so_tp"), fx("0.0005"))}"',
        f' SPEC_SO_BUILD_TT: "{head("Construction")}The market changes how efficiently every state builds by #v {f("spec_so_build", "+=%1")}#!.\\n{lines["build"]}{none.format(sv("spec_so_build"), fx("0.0005"))}[AddLocalizationIf(LessThan_CFixedPoint({sv("spec_so_build")}, {fx(BUILD_FLOOR - 1)}), \'SPEC_SO_BUILD_FLOOR\')]\\n\\n'
        f'[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint({sv("spec_so_build_n")}, {fx(1)}), \'SPEC_SO_BUILD_BOOM\')]'
        f'[AddLocalizationIf(LessThan_CFixedPoint({sv("spec_so_private")}, {fx(0)}), \'SPEC_SO_BUILD_PANIC\')]{build_none}"',
        f' SPEC_SO_BUILD_BOOM: "Booming industries build faster on top of that.\\n{booms}[AddLocalizationIf({panicking}, \'SPEC_SO_GAP\')]"',
        ' SPEC_SO_GAP: "\\n\\n"',
        # not part of the figure above: that is how fast buildings go up, this is how many our investors start
        f' SPEC_SO_BUILD_PANIC: "The [concept_spec_financial_panic] has also stopped #N [Abs_CFixedPoint({sv("spec_so_private")})|%0]#! of [concept_private_construction], the buildings our investors pay for."',
        f' SPEC_SO_BUILD_FLOOR: "\\n#weak However low this goes, buildings still go up at {BUILD_FLOOR:.0%} of their usual speed.#!"',
        f' SPEC_SO_BUILD_NONE: "An industry builds #P {cycle.BB_STEP:.0%}#! faster with every good it makes #v Eager#!, and #P {2 * cycle.BB_STEP:.0%}#! with every one #v Feverish#!. '
        f'The bigger a good\'s share of its industry\'s trade, the more of that it brings. An industry under #v {cycle.BB_FULL:.0%}#! of our trade gains less."',
        f' SPEC_SO_TRADE_TT: "{head("Trade")}The market changes how much our merchants trade by #v {f("spec_so_trade", "+=%0")}#!.\\n'
        f'{lines["trade"]}{none.format(sv("spec_so_trade"), fx("0.0005"))}'
        f'[AddLocalizationIf(GreaterThanOrEqualTo_CFixedPoint(Abs_CFixedPoint({sv("spec_so_rate")}), {fx("0.0005")}), \'SPEC_SO_RATE\')]"',
        f' SPEC_SO_RATE: "\\n\\nIt also changes the interest on our [concept_loans] by #v {f("spec_so_rate", "-=%0")}#!.{lines["rate"]}"',
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    cycle._GROUPS["light_industry"] = ["tools"]  # generate fills it through cycle.setup
    v = values({"panic": -0.2, "wary": -0.1, "steady": 0, "buoyant": 0.1, "mania": 0.2}, {"panic": 0.2, "wary": 0.1},
               {"panic": -0.1, "wary": -0.05, "buoyant": 0.05, "mania": 0.1}, -0.4, -0.1, -0.3, 0.5)
    text = "\n".join(v) + section() + loc()
    assert text.count("{") == text.count("}")
    assert "spec_so_invest = {" in "\n".join(v) and "add = 0.1" in v[0] and "\tmin = -1\n}" in "\n".join(v)
    print("hero ok")
