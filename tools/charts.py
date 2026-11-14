"""The charts (design_exposure.md, Charts): vanilla's own chart types inside sections the mod already has.

Banking tab: lent() is "Where the Banks Have Lent", vanilla's pie chart and legend (the `chart` type of
politics_panel_types.gui, as World Market's importers), one slice a good from the monthly list spec_bank_goods;
credit_history() is the last HISTORY months of leverage as columns, coloured by the Leverage bar's zones.
Investor Interest section: interest_chart() is the market's trade as one bar split by interest level.
Charts show; the actions stay on their buttons."""
from market_tab import (P, W, FLAT, CLEAR, GOLD, RED, HISTORY, CHART_H, COL_W, COL_GAP, fx, v, sv, ind, header,
                        block)
import exposure
import leverage

LIST = "spec_bank_goods"
LEV_PAD = 8  # room above the chart for its top figure, which sits half above its line
LEV_H = 130  # Leverage History is taller than the other charts: its scale runs to 13 months
GREEN = "0.24 0.58 0.32"  # as the Leverage bar's safe fill (progressbar_green), brightened as market_tab's GOLD, BLUE, RED are
LIMIT = "1 1 1"  # the credit limit line, apart from Risky's gold
# vanilla colour defines (NGUI), cold to hot: blue, teal, grey, peach, orange, red
INTEREST_DEFINES = {1: "BUILDING_OWNERSHIP_COLOR_PLAYER_GOVERNMENT", 2: "BUILDING_OWNERSHIP_COLOR_PLAYER_POPS", 3: "NO_STARVATION_COLOR",
                    4: "BUILDING_OWNERSHIP_COLOR_LOCAL_NON_PLAYER_POPS", 5: "MILD_STARVATION_COLOR", 6: "SEVERE_STARVATION_COLOR"}


# -- script (generate.monthly) --------------------------------------------------------------------------------

# boom lending spreads thinly: 4% of loans in booms can be under 1% in every good, so the pie keeps slices of 0.1%
CHART_MIN = 0.001
TOP_N = 5  # vanilla's charts list their largest few; the rest is one "Other goods" line


def script(goods, t="\t\t\t"):
    """The tab block: the chart's goods, the TOP_N largest boom loans (over CHART_MIN of credit), largest first as
    vanilla sorts its charts; spec_bank_top is their sum, so the rest can show as Other goods."""
    pick = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tspec_exp_share_{g} > var:spec_rank_v\n"
                   f"{t}\t\tNOT = {{ is_target_in_variable_list = {{ name = {LIST} target = g:{g} }} }}\n{t}\t}}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_v value = spec_exp_share_{g} }}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_g value = g:{g} }}\n{t}}}\n" for g in goods)
    rank = (f"{t}set_variable = {{ name = spec_rank_v value = {CHART_MIN} }}\n{t}remove_variable = spec_rank_g\n" + pick
            + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_rank_g }}\n"
            f"{t}\tadd_to_variable_list = {{ name = {LIST} target = var:spec_rank_g }}\n"
            f"{t}\tchange_variable = {{ name = spec_bank_top add = var:spec_rank_v }}\n{t}}}\n")
    # the next largest stands in for every good past the TOP_N: its slice and row show Other goods (spec_bank_oth_<g>)
    other = (f"{t}set_variable = {{ name = spec_rank_v value = {CHART_MIN} }}\n{t}remove_variable = spec_rank_g\n" + pick
             + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_rank_g }}\n"
             f"{t}\tadd_to_variable_list = {{ name = {LIST} target = var:spec_rank_g }}\n"
             + "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_rank_g = {{ this = g:{g} }} }}\n"
                       f"{t}\t\tset_variable = {{ name = spec_bank_oth_{g} value = 1 }}\n{t}\t}}\n" for g in goods)
             + f"{t}}}\n")
    # the passes over every good only while some credit is in boom loans: with none, the chart is empty anyway
    passes = ind(rank * TOP_N + other + f"{t}remove_variable = spec_rank_v\n{t}remove_variable = spec_rank_g\n", 1)
    return (f"{t}clear_variable_list = {LIST}\n{t}set_variable = {{ name = spec_bank_top value = 0 }}\n"
            + "".join(f"{t}remove_variable = spec_bank_oth_{g}\n" for g in goods)
            + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_debt var:spec_debt >= 1 spec_exp_booms > {CHART_MIN} }}\n" + passes + f"{t}}}\n")


def history_shift(t="\t\t\t\t"):
    """Beside the confidence history (generate.monthly): this month's leverage into spec_lhist1, the rest one back."""
    return "".join(f"{t}if = {{ limit = {{ has_variable = spec_lhist{n - 1} }} set_variable = {{ name = spec_lhist{n} value = var:spec_lhist{n - 1} }} }}\n"
                   for n in range(HISTORY, 1, -1)) + f"{t}set_variable = {{ name = spec_lhist1 value = spec_lev }}\n"


STATE_VARS = [f"spec_lhist{n}" for n in range(1, HISTORY + 1)]
LEVELS = "spec_iw_levels"  # Investor Interest chart: one good per level with trade, hottest first
LISTS = [LIST, LEVELS]


def state_vars(goods):
    return (STATE_VARS + [f"spec_ui_mv_{g}" for g in goods] + [f"spec_bank_oth_{g}" for g in goods] + ["spec_bank_top"]
            + [f"spec_iw_lvl{w}" for w in range(1, 7)])


# -- GUI ------------------------------------------------------------------------------------------------------

SHARE = f"{P}.Var(Concatenate('spec_exp_', Scope.GetGoods.GetKey)).GetValueWithDefault({fx(0)})"
OTHER = f"{P}.Var(Concatenate('spec_bank_oth_', Scope.GetGoods.GetKey)).IsSet"  # the slice standing in for Other goods
OTHER_SHARE = f"Subtract_CFixedPoint({sv('spec_exp_booms')}, {v('spec_bank_top')})"  # credit in boom loans past the TOP_N
MULT = f"{P}.Var(Concatenate('spec_ui_expx_', Scope.GetGoods.GetKey)).GetValueWithDefault({fx(1)})"  # set from 1% of credit up

IW_WORD = f"{P}.Var(Concatenate('spec_word_', Scope.GetGoods.GetKey)).GetValueWithDefault({fx(0)})"
CUTS = [1.5, 2.5, 3.5, 4.5, 5.5]  # as market_tab's SPEC_INTEREST
IW_WORD_TEXT = "[" + "".join(f"SelectLocalization(LessThan_CFixedPoint({IW_WORD}, {fx(c)}), 'SPEC_INTEREST_{i}', " for i, c in enumerate(CUTS)) + "'SPEC_INTEREST_5'" + ")" * len(CUTS) + "]"
SIZE = f"GetDataModelSize({P}.GetList('{LIST}'))"
SWATCH = "gfx/interface/piechart/piechart_legend.dds"
PIE, LIST_W, ROW_H = 150, 300, 24  # the chart on the left, its list (TOP_N rows and Other goods) on the right
PANIC_W = 56  # Leverage History's panic thresholds, right of the columns
AXIS_W = 26  # Leverage History's month figures, left of the columns


def side_chart(model, title, tooltip, value, colour, cells, visible, name="SPEC_BANK_SLICE_NAME"):
    """Vanilla's chart (a pie, or a treemap by the player's own toggle) laid out across: the chart on the left and,
    in place of vanilla's three-row legend, its slices listed on the right: colour, good, cells."""
    row = f"""widget = {{
	size = {{ {LIST_W - 14} {ROW_H} }}
	tooltip = "{tooltip}"
	hbox = {{
		margin = {{ 4 0 }}
		spacing = 4
		icon = {{
			size = {{ 14 14 }}
			texture = "{SWATCH}"
			color = "[{colour}]"
		}}
		textbox = {{
			layoutpolicy_horizontal = expanding
			size = {{ 0 {ROW_H} }}
			align = nobaseline
			elide = right
			fontsize_min = 12
			text = "{name}"
		}}
{ind(cells, 2)}	}}
}}
"""
    return f"""chart = {{
	parentanchor = hcenter
	visible = "[{visible}]"
	blockoverride "direction" {{
		direction = horizontal
	}}
	blockoverride "margin" {{
		margin = {{ 12 8 }}
	}}
	blockoverride "title" {{}}
	blockoverride "piechartsize" {{
		size = {{ {PIE} {PIE} }}
	}}
	blockoverride "datamodel" {{
		datamodel = "[{model}]"
	}}
	blockoverride "tooltip" {{
		tooltip = "{tooltip}"
	}}
	blockoverride "pieslice" {{
		value = "[{value}]"
	}}
	blockoverride "color" {{
		color = "[{colour}]"
	}}
	blockoverride "labels" {{
		flowcontainer = {{
			direction = vertical
			margin_left = 22
			spacing = 2
			textbox = {{
				size = {{ {LIST_W} 22 }}
				align = left|nobaseline
				default_format = "#title"
				text = "{title}"
			}}
			flowcontainer = {{
				direction = vertical
				datamodel = "[{model}]"
				item = {{
{ind(row, 5)}				}}
			}}
		}}
	}}
}}
"""


def cell(text, width=None, align="right"):
    size = f"size = {{ {width} {ROW_H} }}" if width else "autoresize = yes"
    return f"textbox = {{\n\t{size}\n\talign = {align}|nobaseline\n\ttext = \"{text}\"\n}}\n"


def lent():
    """The boom loans good by good, a slice each, the largest TOP_N and Other goods, beside a list of each one's
    interest and share of the boom loans; a line when there are none."""
    word = cell("SPEC_IW_SLICE_WORD", 78, "left").replace("textbox = {\n", f"textbox = {{\n\tvisible = \"[Not({OTHER})]\"\n", 1)
    chart = side_chart(f"{P}.GetList('{LIST}')", "SPEC_BANK_PIE", "SPEC_BANK_SLICE_TT",
                       f"Select_float({OTHER}, FixedPointToFloat({OTHER_SHARE}), FixedPointToFloat({SHARE}))",
                       f"Select_CVector4f({OTHER}, GetDefine('NGUI', '{INTEREST_DEFINES[3]}'), Scope.GetGoods.GetColor)",
                       word + cell("SPEC_BANK_SLICE_SHARE", 40), f"GreaterThan_int32({SIZE}, '(int32)0')")
    none = f"""textbox = {{
	parentanchor = hcenter
	visible = "[Not(GreaterThan_int32({SIZE}, '(int32)0'))]"
	size = {{ {W - 20} 40 }}
	align = center|nobaseline
	multiline = yes
	text = "SPEC_BANK_NONE_S"
	tooltip = "SPEC_BANK_NONE"
}}
"""
    return block(header("SPEC_H_BANK_LENT"), chart + none)


def lev_scale(most, limit):
    """The Leverage History plot and its axis, topping out a month above `most`."""
    top = most + 1
    px = LEV_H / top
    y = lambda val: round((top - val) * px)
    zones = ((0, leverage.SAFE, GREEN), (leverage.SAFE, leverage.DANGER, GOLD), (leverage.DANGER, top, RED))

    def bar(n, lo, hi, colour):
        return f"""progressbar = {{
	position = {{ 0 {y(hi)} }}
	size = {{ 100% {y(lo) - y(hi)} }}
	direction = vertical
	progresstexture = "{FLAT}"
	noprogresstexture = "{CLEAR}"
	color = {{ {colour} 0.9 }}
	min = {lo}
	max = {hi}
	value = "[FixedPointToFloat({v(f'spec_lhist{n}')})]"
}}
"""
    cols = "".join(f"""widget = {{
	position = {{ {(HISTORY - n) * (COL_W + COL_GAP)} 0 }}
	size = {{ {COL_W} {LEV_H} }}
	tooltip = "SPEC_LHIST_{n}_TT"
{ind("".join(bar(n, lo, hi, c) for lo, hi, c in zones), 1)}}}
""" for n in range(HISTORY, 0, -1))
    marks = (0, leverage.SAFE, leverage.DANGER, leverage.LADDER[-1])
    lines = "".join(f"""icon = {{
	position = {{ 0 {y(val)} }}
	size = {{ 100% 1 }}
	texture = "{FLAT}"
	color = {{ 1 1 1 0.15 }}
}}
""" for val in marks[1:])
    # the credit limit: a white line, and its figure in white on the axis in place of the plain one
    at = lambda val: f"EqualTo_CFixedPoint({limit}, {fx(val)})"
    lines += "".join(f"""icon = {{
	visible = "[{at(val)}]"
	position = {{ 0 {y(val)} }}
	size = {{ 100% 2 }}
	texture = "{FLAT}"
	color = {{ {LIMIT} 0.9 }}
	tooltip = "SPEC_LEV_LIMIT"
}}
""" for val in range(leverage.SAFE, most + 1))
    axis = "".join(f"""textbox = {{
	visible = "[Not({at(val)})]"
	position = {{ 0 {y(val) - 8 + LEV_PAD} }}
	size = {{ {AXIS_W - 6} 16 }}
	align = right|nobaseline
	fontsize = 12
	raw_text = "#low {val}#!"
}}
""" for val in marks) + "".join(f"""textbox = {{
	visible = "[{at(val)}]"
	position = {{ 0 {y(val) - 8 + LEV_PAD} }}
	size = {{ {AXIS_W - 6} 16 }}
	align = right|nobaseline
	fontsize = 12
	color = {{ {LIMIT} 1 }}
	raw_text = "{val}"
	tooltip = "SPEC_LEV_LIMIT"
}}
""" for val in range(leverage.SAFE, most + 1))
    plot_w = HISTORY * (COL_W + COL_GAP) - COL_GAP
    # the panic threshold at each gridline, in a column right of the plot so it never sits on a column
    panic = "".join(f"""textbox = {{
	position = {{ {AXIS_W + plot_w + 4} {y(val) - 8 + LEV_PAD} }}
	size = {{ {PANIC_W - 4} 16 }}
	align = left|nobaseline
	fontsize = 12
	text = "SPEC_LHIST_PANIC_{val}"
	tooltip = "SPEC_LHIST_PANIC_{val}_TT"
}}
""" for val in marks[1:])
    return f"""widget = {{
	size = {{ {AXIS_W + plot_w + PANIC_W} {LEV_H + LEV_PAD} }}
{ind(axis + panic, 1)}	widget = {{
		position = {{ {AXIS_W} {LEV_PAD} }}
		size = {{ {plot_w} {LEV_H} }}
{ind(lines + cols, 2)}	}}
}}
"""


def credit_history():
    """Leverage month by month, newest on the right, each column in the Leverage bar's zones: safe, risky, dangerous."""
    # the credit limit stops at RUIN months, so one scale: a month of headroom keeps the limit line clear of the top, and
    # debt past it (only when income collapses) fills the column
    limit = sv("spec_credit_limit")
    plot_w = HISTORY * (COL_W + COL_GAP) - COL_GAP
    chart = f"""widget = {{
	parentanchor = hcenter
	size = {{ {AXIS_W + plot_w + PANIC_W} {LEV_H + 18 + LEV_PAD} }}
{ind(lev_scale(leverage.RUIN, limit), 1)}	textbox = {{
		position = {{ {AXIS_W} {LEV_H + 2 + LEV_PAD} }}
		autoresize = yes
		fontsize = 12
		text = "SPEC_LHIST_OLDEST"
	}}
	textbox = {{
		position = {{ {AXIS_W + plot_w - 60} {LEV_H + 2 + LEV_PAD} }}
		size = {{ 60 16 }}
		align = right|nobaseline
		fontsize = 12
		text = "SPEC_LHIST_NOW"
	}}
	textbox = {{
		position = {{ {AXIS_W} {LEV_PAD} }}
		size = {{ {plot_w} {LEV_H} }}
		align = center|nobaseline
		visible = "[Not({P}.Var('spec_lhist1').IsSet)]"
		text = "SPEC_LHIST_EMPTY"
	}}
}}
"""

    def key(colour, text, h=12):
        return f"""icon = {{
	size = {{ 12 {h} }}
	texture = "{FLAT}"
	color = {{ {colour} 0.9 }}
}}
textbox = {{
	autoresize = yes
	align = left|nobaseline
	margin_right = 10
	text = "{text}"
}}
"""
    # an hbox can't sit straight in the block's flowcontainer (the game logs it and crashes on load), so a widget holds it
    legend = f"""widget = {{
	parentanchor = hcenter
	size = {{ {W - 20} 24 }}
	hbox = {{
		spacing = 4
		expand = {{}}
{ind(key(GREEN, "SPEC_LHIST_KEY_SAFE") + key(GOLD, "SPEC_LHIST_KEY_RISKY") + key(RED, "SPEC_LHIST_KEY_DANGER") + key(LIMIT, "SPEC_LEV_LIMIT_KEY", 2), 2)}		expand = {{}}
	}}
}}
"""
    return block(header("SPEC_H_CREDIT_HISTORY", "SPEC_H_CREDIT_HISTORY_RIGHT"), chart + legend)


def lvl(w):
    return f"{P}.Var('spec_iw_lvl{w}').GetValueWithDefault({fx(0)})"


def by_word(level, select):
    """A GUI expression for the list item's interest level: level(w) for its word, w 1 (Fleeing) to 6 (Feverish)."""
    out = level(6)
    for w in range(5, 0, -1):
        out = f"{select}(LessThan_CFixedPoint({IW_WORD}, {fx(CUTS[w - 1])}), {level(w)}, {out})"
    return out


def interest_chart():
    """The market's trade by interest level as the bank chart: a slice a level, hottest first, in vanilla's own colour
    defines (blue Fleeing to red Feverish). The list holds one good per level; its word picks the level's figures.
    The goods themselves are in the Filters below."""
    size = f"GetDataModelSize({P}.GetList('{LEVELS}'))"
    chart = side_chart(f"{P}.GetList('{LEVELS}')", "SPEC_IW_PIE", "SPEC_IW_SLICE_TT",
                       by_word(lambda w: f"FixedPointToFloat({lvl(w)})", "Select_float"),
                       by_word(lambda w: f"GetDefine('NGUI', '{INTEREST_DEFINES[w]}')", "Select_CVector4f"),
                       cell("SPEC_IW_SLICE_SHARE", 40), f"GreaterThan_int32({size}, '(int32)0')", name="SPEC_IW_SLICE_WORD")
    # worked out in the monthly update, so a market just loaded or just formed has none yet
    none = f"""textbox = {{
	parentanchor = hcenter
	visible = "[Not(GreaterThan_int32({size}, '(int32)0'))]"
	size = {{ {W - 20} 30 }}
	align = center|nobaseline
	text = "SPEC_IW_NONE"
}}
"""
    return chart + none


def interest_script(goods, t="\t\t\t"):
    """The tab block, after the word lists (spec_goods_w<w>) are built: each traded good's share of trade, added up by
    its interest level (spec_word_<g>, 1 to 6), then one good of each level with at least 0.5% of trade (what shows as 1%)
    into the chart's list, the largest level first as vanilla sorts its charts."""
    shares = "".join(f"{t}if = {{\n{t}\tlimit = {{ spec_mv_{g} > 0 }}\n"
                     f"{t}\tset_variable = {{ name = spec_ui_mv_{g} value = {{ value = spec_mv_{g} divide = var:spec_mv_total }} }}\n"
                     + "".join(f"{t}\t{'if' if w == 1 else 'else_if'} = {{\n{t}\t\tlimit = {{ var:spec_word_{g} = {w} }}\n"
                               f"{t}\t\tchange_variable = {{ name = spec_iw_lvl{w} add = var:spec_ui_mv_{g} }}\n{t}\t}}\n"
                               for w in range(1, 7))
                     + f"{t}}}\n{t}else = {{\n{t}\tremove_variable = spec_ui_mv_{g}\n{t}}}\n" for g in goods)
    # each round finds the largest level not yet listed (spec_iw_used<w>) and lists one of its goods
    pick = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tvar:spec_iw_lvl{w} >= var:spec_rank_v\n{t}\t\tNOT = {{ has_variable = spec_iw_used{w} }}\n{t}\t}}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_v value = var:spec_iw_lvl{w} }}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_w value = {w} }}\n{t}}}\n" for w in range(1, 7))
    add = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_rank_w\n{t}\t\tvar:spec_rank_w = {w}\n{t}\t}}\n"
                  f"{t}\tset_variable = spec_iw_used{w}\n"
                  f"{t}\trandom_in_list = {{\n{t}\t\tvariable = spec_goods_w{w}\n{t}\t\tsave_temporary_scope_as = spec_iw\n"
                  f"{t}\t\troot = {{ add_to_variable_list = {{ name = {LEVELS} target = scope:spec_iw }} }}\n{t}\t}}\n{t}}}\n"
                  for w in range(1, 7))
    # ponytail: levels under 1% are left out; the game rounds % down, so they would read 0%
    rank = f"{t}set_variable = {{ name = spec_rank_v value = 0.01 }}\n{t}remove_variable = spec_rank_w\n" + pick + add
    return ("".join(f"{t}set_variable = {{ name = spec_iw_lvl{w} value = 0 }}\n" for w in range(1, 7))
            + shares + f"{t}clear_variable_list = {LEVELS}\n" + rank * 6
            + "".join(f"{t}remove_variable = spec_iw_used{w}\n" for w in range(1, 7))
            + f"{t}remove_variable = spec_rank_v\n{t}remove_variable = spec_rank_w\n")


def loc(k):
    when = lambda n: "This Month" if n == 1 else "Last Month" if n == 2 else f"{n - 1} Months Ago"
    lev = lambda n: v(f"spec_lhist{n}")
    at = lambda m: round(k["PANIC"] + leverage.PANIC_SPAN * min(max((m - leverage.SAFE) / (leverage.RUIN - leverage.SAFE), 0), 1))  # the Panic Threshold there
    return (
        ' SPEC_H_BANK_LENT: "Where the Banks Have Lent"\n'
        ' SPEC_H_BANK_LENT_TT: "#header Where the Banks Have Lent#!\\n$TOOLTIP_DELIMITER$\\nBanks lend most new credit into '
        'booming goods: the larger a good\'s share of our trade and the higher its [concept_spec_investor_interest], '
        'the more it gets. A loan stays in its good until repaid.\\n\\nWhen a boom the banks lent into ends, '
        '[concept_spec_market_confidence] falls further. Restraining speculation in a good halves the new lending it attracts."\n'
        ' SPEC_BANK_PIE: "Boom Loans by Good"\n'
        f' SPEC_BANK_SLICE_NAME: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER\', \'SPEC_BANK_GOOD_NAME\')]"\n'
        ' SPEC_BANK_GOOD_NAME: "[Scope.GetGoods.GetName]"\n'
        f' SPEC_BANK_SLICE_SHARE: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER_SHARE\', \'SPEC_BANK_GOOD_SHARE\')]"\n'
        f' SPEC_BANK_OTHER_SHARE: "#v [Divide_CFixedPoint({OTHER_SHARE}, Max_CFixedPoint({sv("spec_exp_booms")}, {fx(0.001)}))|%0]#!"\n'
        f' SPEC_BANK_GOOD_SHARE: "#v [Divide_CFixedPoint({SHARE}, Max_CFixedPoint({sv("spec_exp_booms")}, {fx(0.001)}))|%0]#!"\n'
        f' SPEC_BANK_SLICE_TT: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER_TT\', \'SPEC_BANK_GOOD_TT\')]"\n'
        f' SPEC_BANK_GOOD_TT: "#header [Scope.GetGoods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n#v [{SHARE}|%1]#! of [concept_spec_outstanding_credit] '
        f'is lent into it.\\nIf its boom ended, [concept_spec_market_confidence] would fall #v x[{MULT}|2]#! as far.\\n\\n'
        '#grey A loan stays in its good until it is repaid, even after the boom cools.#!"\n'
        ' SPEC_BANK_NONE_S: "#grey No credit lent into booms#!"\n'
        f' SPEC_BANK_NONE: "The banks have lent nothing into booms. Banks lend while [concept_spec_market_confidence] is above '
        f'#v {k["CREDIT_FROM"]}#! (now #v [{v("spec_conf")}|0]#!), most of it into goods #v Keen#! or hotter."\n'
        ' SPEC_LHIST_EMPTY: "#grey Recorded each month from now on#!"\n'
        ' SPEC_H_CREDIT_HISTORY: "Credit Leverage History"\n'
        f' SPEC_H_CREDIT_HISTORY_TT: "#header Credit Leverage History#!\\n$TOOLTIP_DELIMITER$\\n[concept_spec_leverage] over the last #v {HISTORY}#! '
        f'months, newest on the right\\nSafe up to #v {leverage.SAFE}#! months, Risky to #v {leverage.DANGER}#!, Dangerous past #v {leverage.DANGER}#!\\n'
        'White line: our Lending Limit\\nRight edge: the Panic Threshold at each level"\n'
        f' SPEC_H_CREDIT_HISTORY_RIGHT: "Now #v [{sv("spec_lev")}|1]#! months"\n'
        f' SPEC_LHIST_OLDEST: "#grey {HISTORY - 1} Months Ago#!"\n'
        ' SPEC_LHIST_NOW: "#grey This Month#!"\n'
        ' SPEC_LHIST_KEY_SAFE: "Safe"\n'
        ' SPEC_LHIST_KEY_RISKY: "Risky"\n'
        ' SPEC_LHIST_KEY_DANGER: "Dangerous"\n'
        + "".join(f' SPEC_LHIST_PANIC_{m}: "#low Panic {at(m)}#!"\n'
                  f' SPEC_LHIST_PANIC_{m}_TT: "#header Panic Threshold#!\\nAt #v {m}#! months of [concept_spec_leverage], a [concept_spec_financial_panic] '
                  f'begins below #v {at(m)}#! [concept_spec_market_confidence]."\n' for m in (leverage.SAFE, leverage.DANGER, leverage.LADDER[-1]))
        + "".join(f' SPEC_LHIST_{n}_TT: "[SelectLocalization({P}.Var(\'spec_lhist{n}\').IsSet, \'SPEC_LHIST_{n}_ON\', \'SPEC_HIST_NONE\')]"\n'
                  f' SPEC_LHIST_{n}_ON: "#header {when(n)}#!\\n[concept_spec_leverage]: #v [{lev(n)}|1]#! months"\n' for n in range(1, HISTORY + 1))
        + ' SPEC_BANK_OTHER: "Other goods"\n'
        f' SPEC_BANK_OTHER_TT: "#header $SPEC_BANK_OTHER$#!\\n$TOOLTIP_DELIMITER$\\n#v [{OTHER_SHARE}|%1]#! of [concept_spec_outstanding_credit] is lent into the booms of every other good."\n'
        + ' SPEC_IW_PIE: "Trade by [concept_spec_investor_interest]"\n'
        ' SPEC_IW_NONE: "#grey Shown from the start of next month#!"\n'
        f' SPEC_IW_SLICE_WORD: "{IW_WORD_TEXT}"\n'
        + f' SPEC_IW_SLICE_TT: "[{by_word(lambda w: f"\'SPEC_IW_LVL_{w}_TT\'", "SelectLocalization")}]"\n'
        f' SPEC_IW_SLICE_SHARE: "[{by_word(lambda w: f"\'SPEC_IW_SHARE_{w}\'", "SelectLocalization")}]"\n'
        + "".join(f' SPEC_IW_SHARE_{w}: "#v [{lvl(w)}|%0]#!"\n'
                  f' SPEC_IW_LVL_{w}_TT: "$SPEC_INTEREST_{w - 1}$: #v [{lvl(w)}|%0]#! of the market\'s trade, in #v [{v(f"spec_n_w{w}")}|0]#! goods"\n'
                  for w in range(1, 7)))


if __name__ == "__main__":
    for part in (lent(), credit_history(), interest_chart(), interest_script(["coal"]), script(["coal"]), history_shift(), loc({"CREDIT_FROM": 1, "PANIC": 25})):
        assert part.count("{") == part.count("}"), part[:80]
    assert script(["coal", "iron"]).count("add_to_variable_list") == TOP_N + 1  # one pick per rank, then Other goods
    assert script(["coal"]).index("var:spec_debt >= 1") < script(["coal"]).index("spec_rank_v")  # no debt, no passes
    assert interest_script(["coal"]).count("add_to_variable_list") == 36  # six rounds, each able to list any level
    print("charts ok")
