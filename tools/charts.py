"""The charts (design_exposure.md, Charts): vanilla's own chart types inside sections the mod already has.

Banking tab: lent() is "Where the Banks Have Lent", vanilla's pie chart and legend (the `chart` type of
politics_panel_types.gui, as World Market's importers), one slice a good from the monthly list spec_bank_goods;
credit_history() is the last HISTORY months of leverage as columns, coloured by the Leverage bar's zones.
Investor Interest section: interest_chart() is the market's trade as one bar split by interest level.
Charts show; the actions stay on their buttons."""
from market_tab import (P, W, FLAT, CLEAR, GOLD, RED, HISTORY, CHART_H, COL_W, COL_GAP, fx, v, sv, ind, header,
                        block)
from sectors import CHART_NAMED_SECTORS, GROUPS
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
TOP_N = 4  # Largest individual loans, followed by Other goods if a balance remains.


def sorted_list(name, goods, value, t, cond=""):
    """name: a variable list of the goods whose value is above 0, largest first, for the chart rows' tooltips (the
    loc can't sort): each round lists the largest not yet listed, until none is left."""
    pick = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{\n{t}\t\t\t{cond.format(g=g)}\n{t}\t\t\t{value(g)} > var:spec_rank_v\n"
                   f"{t}\t\t\tNOT = {{ is_target_in_variable_list = {{ name = {name} target = g:{g} }} }}\n{t}\t\t}}\n"
                   f"{t}\t\tset_variable = {{ name = spec_rank_v value = {value(g)} }}\n"
                   f"{t}\t\tset_variable = {{ name = spec_rank_g value = g:{g} }}\n{t}\t}}\n" for g in goods)
    return (f"{t}clear_variable_list = {name}\n{t}set_variable = spec_sort_more\n"
            f"{t}while = {{\n{t}\tlimit = {{ has_variable = spec_sort_more }}\n"
            f"{t}\tset_variable = {{ name = spec_rank_v value = 0 }}\n{t}\tremove_variable = spec_rank_g\n{pick}"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = spec_rank_g }}\n"
            f"{t}\t\tadd_to_variable_list = {{ name = {name} target = var:spec_rank_g }}\n{t}\t}}\n"
            f"{t}\telse = {{\n{t}\t\tremove_variable = spec_sort_more\n{t}\t}}\n{t}}}\n"
            f"{t}remove_variable = spec_rank_v\n{t}remove_variable = spec_rank_g\n")


BANK_SORTED, IW_SORTED = "spec_bank_sorted", "spec_iw_sorted"


def script(goods, t="\t\t\t"):
    """The tab block: the chart's goods, the TOP_N largest boom loans (over CHART_MIN of credit), largest first as
    vanilla sorts its charts; spec_bank_top is their sum, so the rest can show as Other goods. spec_bank_in_<g> marks
    the TOP_N, so Other goods' tooltip can list the rest."""
    pick = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tspec_exp_share_{g} > var:spec_rank_v\n"
                   f"{t}\t\tNOT = {{ is_target_in_variable_list = {{ name = {LIST} target = g:{g} }} }}\n{t}\t}}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_v value = spec_exp_share_{g} }}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_g value = g:{g} }}\n{t}}}\n" for g in goods)
    top = "".join(f"{t}if = {{ limit = {{ is_target_in_variable_list = {{ name = {LIST} target = g:{g} }} }} "
                  f"set_variable = spec_bank_in_{g} }}\n" for g in goods)
    rank = (f"{t}set_variable = {{ name = spec_rank_v value = {CHART_MIN} }}\n{t}remove_variable = spec_rank_g\n" + pick
            + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_rank_g }}\n"
            f"{t}\tadd_to_variable_list = {{ name = {LIST} target = var:spec_rank_g }}\n"
            f"{t}\tchange_variable = {{ name = spec_bank_top add = var:spec_rank_v }}\n{t}}}\n")
    # Any positive remainder needs a representative, even below the named-slice cutoff: its slice and row show Other goods (spec_bank_oth_<g>)
    other = (f"{t}set_variable = {{ name = spec_rank_v value = 0 }}\n{t}remove_variable = spec_rank_g\n" + pick
             + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_rank_g }}\n"
             f"{t}\tadd_to_variable_list = {{ name = {LIST} target = var:spec_rank_g }}\n"
             + "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_rank_g = {{ this = g:{g} }} }}\n"
                       f"{t}\t\tset_variable = {{ name = spec_bank_oth_{g} value = 1 }}\n{t}\t}}\n" for g in goods)
             + f"{t}}}\n")
    # the passes over every good only while some credit is in boom loans: with none, the chart is empty anyway
    passes = ind(rank * TOP_N + top + other + f"{t}remove_variable = spec_rank_v\n{t}remove_variable = spec_rank_g\n"
                 + sorted_list(BANK_SORTED, goods, lambda g: f"spec_exp_share_{g}", t, "always = yes"), 1)
    return (f"{t}clear_variable_list = {LIST}\n{t}clear_variable_list = {BANK_SORTED}\n{t}set_variable = {{ name = spec_bank_top value = 0 }}\n"
            + "".join(f"{t}remove_variable = spec_bank_oth_{g}\n{t}remove_variable = spec_bank_in_{g}\n" for g in goods)
            + f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_debt var:spec_debt >= 1 spec_exp_booms > 0 }}\n" + passes + f"{t}}}\n")


def history_shift(t="\t\t\t\t"):
    """Beside the confidence history (generate.monthly): this month's leverage into spec_lhist1, the rest one back."""
    return "".join(f"{t}if = {{ limit = {{ has_variable = spec_lhist{n - 1} }} set_variable = {{ name = spec_lhist{n} value = var:spec_lhist{n - 1} }} }}\n"
                   for n in range(HISTORY, 1, -1)) + f"{t}set_variable = {{ name = spec_lhist1 value = spec_lev }}\n"


STATE_VARS = [f"spec_lhist{n}" for n in range(1, HISTORY + 1)]
LEVELS = "spec_iw_levels"
# The native chart takes a list of scopes. Each of these goods identifies one tier,
# independently of that good's actual interest level in the player's market.
INTEREST_KEYS = ("grain", "fish", "wood", "coal", "iron", "tools")
SECTOR_LIST = "spec_sector_chart"
LISTS = [LIST, LEVELS, BANK_SORTED, IW_SORTED, SECTOR_LIST, "spec_sector_ranked"]


def state_vars(goods):
    return (STATE_VARS + ["spec_sector_share_other"] + [f"spec_sector_rank_{s}" for s in GROUPS] + [f"spec_ui_mv_{g}" for g in goods] + [f"spec_bank_oth_{g}" for g in goods] + [f"spec_bank_in_{g}" for g in goods] + ["spec_bank_top"]
            + [f"spec_iw_lvl{w}" for w in range(1, 7)] + [f"spec_iw_key_{g}" for g in INTEREST_KEYS])


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


def breakdown(shown, model, item_shown, text):
    """A row tooltip's goods, under its text as GDP's graph is under its own: the model's goods that item_shown passes,
    in the model's order (charts.sorted_list: largest first). Shown while shown holds for the row."""
    return f"""flowcontainer = {{
	direction = vertical
	visible = "[{shown}]"
	ignoreinvisible = yes
	margin = {{ 15 0 }}
	margin_bottom = 10
	datamodel = "[{model}]"
	item = {{
		textbox = {{
			visible = "[{item_shown}]"
			autoresize = yes
			align = left|nobaseline
			text = "{text}"
		}}
	}}
}}
"""


def side_chart(model, title, tooltip, value, colour, cells, visible, name="SPEC_BANK_SLICE_NAME", after="", box_only=False):
    """Vanilla's chart (a pie, or a treemap by the player's own toggle) laid out across: the chart on the left and,
    in place of vanilla's three-row legend, its slices listed on the right: colour, good, cells. after: what each
    row's tooltip shows under its text (breakdown)."""
    tip = f"""tooltipwidget = {{
	TooltipWidgetType = {{
		blockoverride "tooltip_content_after" {{
{ind(after, 3)}		}}
	}}
}}
""" if after else ""
    row = f"""widget = {{
	size = {{ {LIST_W - 14} {ROW_H} }}
	tooltip = "{tooltip}"
{ind(tip, 1)}	hbox = {{
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
    # vanilla's v3_piechart and v3_treemapchart (politics_panel_types.gui:1014-1088) in a fixed size widget: theirs are
    # containers framed at 130% and 124% of their own size, so each show grew the box chart and pushed the list right
    # until the section was reopened (2026-11-20)
    # no slice tooltip: the engine opens it with only the slice's Goods context, so every Country.MakeScope in it failed
    # (SPEC_SECTOR_*_TT, 2026-11-21); the legend rows beside the chart carry the same tooltip
    slice_ = f'value = "[{value}]"\ncolor = "[{colour}]"\n'
    def drawn(shown, kind, body, frame, frame_w):
        visibility = "" if box_only else f'visible = "[{shown}]"'
        return f"""widget = {{
	size = {{ 100% 100% }}
	{visibility}
	{kind}chart = {{
		size = {{ 100% 100% }}
{ind(body, 2)}		datamodel = "[{model}]"
		item = {{
			{kind}slice = {{
{ind(slice_, 4)}			}}
		}}
	}}
	icon = {{
		texture = "gfx/interface/{kind}chart/{frame}"
		parentanchor = center
		size = {{ {frame_w}% 110% }}
	}}
}}
"""
    pie = drawn("GetVariableSystem.Exists('piecharts')", "pie", "startangle = 450\nendangle = 90\n", "piechart_frame.dds", 130)
    box = drawn("Not(GetVariableSystem.Exists('piecharts'))", "treemap", "", "treemapchart_frame.dds", 124).replace(
        "\t\t\ttreemapslice = {\n", '\t\t\ttreemapslice = {\n\t\t\t\ttexture = "gfx/interface/treemapchart/treemapchart.dds"\n', 1)
    # vanilla's chart type round it (politics_panel_types.gui:648-830): the background and the toggle that shows on hover
    hover = "" if box_only else """onmousehierarchyenter = "[PdxGuiWidget.FindChild('chart_button').InterruptThenTriggerAnimation('hide_chart_button','show_chart_button')]"
	onmousehierarchyleave = "[PdxGuiWidget.FindChild('chart_button').InterruptThenTriggerAnimation('show_chart_button','hide_chart_button')]"
"""
    toggle = "" if box_only else f"""
	widget = {{
		name = "chart_button"
		parentanchor = right|top
		position = {{ -5 5 }}
		size = {{ 30 30 }}
		state = {{
			name = hide_chart_button
			trigger_on_create = yes
			alpha = 0
			duration = 0.2
		}}
		state = {{
			name = show_chart_button
			alpha = 1
			duration = 0.15
		}}
		button_icon_round_toggle = {{
			size = {{ 29 29 }}
			parentanchor = right|vcenter
			position = {{ -10 0 }}
			blockoverride "on_click" {{
				onclick = "[GetVariableSystem.Toggle('piecharts')]"
			}}
			blockoverride "view_1" {{
				visible = "[Not(GetVariableSystem.Exists('piecharts'))]"
			}}
			blockoverride "view_2" {{
				visible = "[GetVariableSystem.Exists('piecharts')]"
			}}
			blockoverride "icon_1" {{
				texture = "gfx/interface/buttons/button_icons/piecharts.dds"
			}}
			blockoverride "icon_2" {{
				texture = "gfx/interface/buttons/button_icons/areacharts.dds"
			}}
			blockoverride "tooltip_1" {{
				tooltip = "TOOLTIP_PIE_CHART"
			}}
			blockoverride "tooltip_2" {{
				tooltip = "TOOLTIP_AREA_CHART"
			}}
		}}
	}}
"""
    return f"""container = {{
	parentanchor = hcenter
	visible = "[{visible}]"
	alwaystransparent = no
	{hover}
	flowcontainer = {{
		spacing = 5
		margin = {{ 12 8 }}
		background = {{
			using = entry_bg
		}}
		widget = {{
			size = {{ {PIE} {PIE} }}
{ind(box if box_only else pie + box, 3)}		}}
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
{toggle}

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
                       word + cell("SPEC_BANK_SLICE_SHARE", 40) + cell("SPEC_BANK_SLICE_AMOUNT"), f"GreaterThan_int32({SIZE}, '(int32)0')",
                       after=breakdown(OTHER, f"{P}.GetList('{BANK_SORTED}')",
                                       f"Not({P}.Var(Concatenate('spec_bank_in_', Scope.GetGoods.GetKey)).IsSet)", "SPEC_BANK_ITEM"))
    none = f"""textbox = {{
	parentanchor = hcenter
	visible = "[Not(GreaterThan_int32({SIZE}, '(int32)0'))]"
	size = {{ {W - 20} 74 }}
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


# the level an interest chart row stands for, by its representative good
ROW_TIER = f"{P}.Var(Concatenate('spec_iw_key_', Scope.GetGoods.GetKey)).GetValueWithDefault({IW_WORD})"


def by_word(level, select):
    """Old saves keep their representative goods until the first monthly rebuild."""
    out = level(6)
    for w in range(5, 0, -1):
        out = f"{select}(LessThan_CFixedPoint({ROW_TIER}, {fx(CUTS[w - 1])}), {level(w)}, {out})"
    return out


def sector_chart():
    model = f"{P}.GetList('spec_sector_ranked')"
    share = fx(0)
    representatives = [(members.split()[0], sector) for sector, (_, members) in GROUPS.items()]
    for good, sector in [*representatives, ("fish", "other")]:
        share = f"Select_CFixedPoint(EqualTo_string(Scope.GetGoods.GetKey, '{good}'), {v('spec_sector_share_' + sector)}, {share})"
    return side_chart(model, "SPEC_SECTOR_TURNOVER_LINK", "SPEC_SECTOR_CHART_TT", f"FixedPointToFloat({share})",
                      "Scope.GetGoods.GetColor", cell(f"[{share}|%1]", 62),
                      f"GreaterThan_int32(GetDataModelSize({model}), '(int32)0')", name="SPEC_SECTOR_CHART_NAME", box_only=True)


def sector_tooltips(k):
    def label(suffix):
        result = "'SPEC_IB_EMPTY'"
        for sector, (_, members) in reversed(GROUPS.items()):
            result = f"SelectLocalization(EqualTo_string(Scope.GetGoods.GetKey, '{members.split()[0]}'), 'SPEC_SECTOR_{sector.upper()}{suffix}', {result})"
        return f"[SelectLocalization(EqualTo_string(Scope.GetGoods.GetKey, 'fish'), 'SPEC_SECTOR_OTHER{suffix}', {result})]"
    lines = [f' SPEC_SECTOR_CHART_NAME: "{label("")}"', f' SPEC_SECTOR_CHART_TT: "{label("_TT")}"']
    tail = "".join(f"[AddLocalizationIf(EqualTo_CFixedPoint({v('spec_sector_rank_' + sec)}, {fx(rank)}), 'SPEC_SECTOR_{sec.upper()}_ITEM')]" for rank in range(CHART_NAMED_SECTORS + 1, len(GROUPS) + 1) for sec in GROUPS)
    lines.append(f' SPEC_SECTOR_OTHER_TT: "#header $SPEC_SECTOR_OTHER$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_SECTOR_TURNOVER$  #v [{v("spec_sector_share_other")}|%1]#!{tail}"')
    for sector in GROUPS:
        name = "SPEC_SECTOR_" + sector.upper()
        share = v("spec_sector_share_" + sector)
        trend = v("spec_review_" + sector)
        lines.append(f' {name}_ITEM: "\\n#tooltippable #tooltip:[Country.GetTooltipTag],{name}_TT '
                     f'@spec_sector_{sector}! ${name}$  #v [{share}|%1]#!#!#!"')
        names = ", ".join(f"[GetGoods('{g}').GetName]" for g in sorted(k["CATEGORY"]) if k["CATEGORY"][g] == sector)
        lines.append(f' {name}_SHARE_TT: "${name}$ goods make up #v [{share}|%1]#! of the goods for sale in our market, valued at their [concept_base_price]."')
        lines.append(f' {name}_TREND: "$SPEC_SECTOR_PRICE_TREND$  #v [{trend}|=+%1]#!"')
        review = f"[SelectLocalization({P}.Var('spec_review_{sector}').IsSet, '{name}_TREND', 'SPEC_SECTOR_WAIT')]"
        lines.append(f' {name}_TT: "#header [Concept(\'concept_spec_market_sector\',\'${name}$\')]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_SECTOR_TURNOVER$  #v [{share}|%1]#!\\n{review}\\n\\n{names}"')
    # these open from chart rows, filter buttons, headers and each other, and some of those tooltips arrive without the
    # window's Country (log, 2026-11-21); the Finance window always shows the played or observed country, so name it
    return ("\n".join(lines) + "\n").replace("Country.", "GetMetaPlayer.GetPlayedOrObservedCountry.")


def interest_chart():
    """The market's trade by interest level as the bank chart: a slice a level, hottest first, in vanilla's own colour
    defines (blue Fleeing to red Feverish). The list holds one good per level; its word picks the level's figures.
    The goods themselves are in the Filters below."""
    size = f"GetDataModelSize({P}.GetList('{LEVELS}'))"
    chart = side_chart(f"{P}.GetList('{LEVELS}')", "SPEC_IW_PIE", "SPEC_IW_SLICE_TT",
                       by_word(lambda w: f"FixedPointToFloat({lvl(w)})", "Select_float"),
                       by_word(lambda w: f"GetDefine('NGUI', '{INTEREST_DEFINES[w]}')", "Select_CVector4f"),
                       cell("SPEC_IW_SLICE_SHARE", 56) + cell("SPEC_IW_SLICE_AMOUNT"), f"GreaterThan_int32({size}, '(int32)0')", name="SPEC_IW_CHART_WORD",
                       after="".join(breakdown(f"EqualTo_CFixedPoint({ROW_TIER}, {fx(w)})", f"{P}.GetList('{IW_SORTED}')",
                                               f"EqualTo_CFixedPoint({IW_WORD}, {fx(w)})", "SPEC_IW_ITEM") for w in range(1, 7)))
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
    """Group trade value by interest and allocate exactly 1,000 tenths of a percent across nonempty tiers."""
    shares = "".join(f"{t}if = {{\n{t}\tlimit = {{ spec_mv_{g} > 0 }}\n"
                     f"{t}\tset_variable = {{ name = spec_ui_mv_{g} value = {{ value = spec_mv_{g} divide = var:spec_mv_total }} }}\n"
                     + "".join(f"{t}\t{'if' if w == 1 else 'else_if'} = {{\n{t}\t\tlimit = {{ var:spec_word_{g} = {w} }}\n"
                               f"{t}\t\tchange_variable = {{ name = spec_iw_lvl{w} add = spec_mv_{g} }}\n{t}\t}}\n"
                               for w in range(1, 7))
                     + f"{t}}}\n{t}else = {{\n{t}\tremove_variable = spec_ui_mv_{g}\n{t}}}\n" for g in goods)
    # Round cumulative boundaries once and subtract adjacent boundaries. The last is exactly
    # 1,000, even when rounding each tier independently would make the legend sum to 99.9.
    total = " ".join(f"add = var:spec_iw_lvl{w}" for w in range(1, 7))
    normalize = (f"{t}set_local_variable = {{ name = spec_iw_total value = {{ value = 0 {total} }} }}\n"
                 f"{t}set_local_variable = {{ name = spec_iw_sum value = 0 }}\n"
                 f"{t}set_local_variable = {{ name = spec_iw_prior value = 0 }}\n"
                 f"{t}if = {{\n{t}\tlimit = {{ local_var:spec_iw_total > 0 }}\n")
    for w in range(1, 7):
        normalize += (f"{t}\tchange_local_variable = {{ name = spec_iw_sum add = var:spec_iw_lvl{w} }}\n"
                      f"{t}\tset_local_variable = {{ name = spec_iw_edge value = {{ value = local_var:spec_iw_sum "
                      "divide = local_var:spec_iw_total multiply = 1000 round = yes } }\n"
                      f"{t}\tset_variable = {{ name = spec_iw_lvl{w} value = {{ value = local_var:spec_iw_edge "
                      "subtract = local_var:spec_iw_prior divide = 1000 } }\n"
                      f"{t}\tset_local_variable = {{ name = spec_iw_prior value = local_var:spec_iw_edge }}\n")
    normalize += f"{t}}}\n"
    pick = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tvar:spec_iw_lvl{w} >= var:spec_rank_v\n{t}\t\tNOT = {{ has_variable = spec_iw_used{w} }}\n{t}\t}}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_v value = var:spec_iw_lvl{w} }}\n"
                   f"{t}\tset_variable = {{ name = spec_rank_w value = {w} }}\n{t}}}\n" for w in range(1, 7))
    add = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_rank_w\n{t}\t\tvar:spec_rank_w = {w}\n{t}\t}}\n"
                  f"{t}\tset_variable = spec_iw_used{w}\n"
                  f"{t}\tset_variable = {{ name = spec_iw_key_{good} value = {w} }}\n"
                  f"{t}\tadd_to_variable_list = {{ name = {LEVELS} target = g:{good} }}\n{t}}}\n"
                  for w, good in enumerate(INTEREST_KEYS, 1))
    rank = f"{t}set_variable = {{ name = spec_rank_v value = 0.001 }}\n{t}remove_variable = spec_rank_w\n" + pick + add
    return ("".join(f"{t}set_variable = {{ name = spec_iw_lvl{w} value = 0 }}\n" for w in range(1, 7))
            + shares + normalize + f"{t}clear_variable_list = {LEVELS}\n" + rank * 6
            + "".join(f"{t}remove_variable = spec_iw_used{w}\n" for w in range(1, 7))
            + f"{t}remove_variable = spec_rank_v\n{t}remove_variable = spec_rank_w\n"
            + sorted_list(IW_SORTED, goods, lambda g: f"var:spec_ui_mv_{g}", t, "has_variable = spec_ui_mv_{g}"))


def loc(k):
    when = lambda n: "This Month" if n == 1 else "Last Month" if n == 2 else f"{n - 1} Months Ago"
    lev = lambda n: v(f"spec_lhist{n}")
    at = lambda m: f"[{sv(f'spec_panic_at_{m}')}|1]"
    # the chart lists' amounts after their shares, and a line for each good in a row's tooltip (breakdown)
    money = lambda x: f"@money![{x}|D]"
    debt, booms = v("spec_debt"), f"Max_CFixedPoint({sv('spec_exp_booms')}, {fx('0.00001')})"
    trade = lambda share: f"Multiply_CFixedPoint({share}, {v('spec_mv_total')})"
    mv = f"{P}.Var(Concatenate('spec_ui_mv_', Scope.GetGoods.GetKey)).GetValueWithDefault({fx(0)})"
    return sector_tooltips(k) + (
        f' SPEC_BANK_SLICE_AMOUNT: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER_AMOUNT\', \'SPEC_BANK_GOOD_AMOUNT\')]"\n'
        f' SPEC_BANK_GOOD_AMOUNT: "({money(f"Multiply_CFixedPoint({SHARE}, {debt})")})"\n'
        f' SPEC_BANK_OTHER_AMOUNT: "({money(f"Multiply_CFixedPoint({OTHER_SHARE}, {debt})")})"\n'
        f' SPEC_BANK_ITEM: "[Scope.GetGoods.GetName]  #v [Divide_CFixedPoint({SHARE}, {booms})|%1]#! ({money(f"Multiply_CFixedPoint({SHARE}, {debt})")})"\n'
        f' SPEC_IW_ITEM: "[Scope.GetGoods.GetName]  #v [{mv}|%1]#! ({money(trade(mv))})"\n'
        + f' SPEC_IW_SLICE_AMOUNT: "[{by_word(lambda w: f"\'SPEC_IW_AMOUNT_{w}\'", "SelectLocalization")}]"\n'
        + "".join(f' SPEC_IW_AMOUNT_{w}: "({money(trade(lvl(w)))})"\n' for w in range(1, 7)) +
        ' SPEC_H_BANK_LENT: "Where the Banks Have Lent"\n'
        ' SPEC_H_BANK_LENT_TT: "#header Where the Banks Have Lent#!\\n$TOOLTIP_DELIMITER$\\n'
        'Banks lend new money into booming goods, more into bigger goods with more [concept_spec_investor_interest]. '
        'A loan stays in its good until it is paid back.'
        '\\n\\n#N When a boom with loans in it ends, [concept_spec_market_confidence] falls further.#!\\n'
        '$TOOLTIP_DELIMITER$\\n#instruction Restraining Speculation in a good halves its share of new boom loans.#!"\n'
        ' SPEC_BANK_PIE: "Boom Loans by Good"\n'
        f' SPEC_BANK_SLICE_NAME: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER\', \'SPEC_BANK_GOOD_NAME\')]"\n'
        ' SPEC_BANK_GOOD_NAME: "[Scope.GetGoods.GetName]"\n'
        f' SPEC_BANK_SLICE_SHARE: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER_SHARE\', \'SPEC_BANK_GOOD_SHARE\')]"\n'
        f' SPEC_BANK_OTHER_SHARE: "#v [Divide_CFixedPoint({OTHER_SHARE}, Max_CFixedPoint({sv("spec_exp_booms")}, {fx("0.00001")}))|%0]#!"\n'
        f' SPEC_BANK_GOOD_SHARE: "#v [Divide_CFixedPoint({SHARE}, Max_CFixedPoint({sv("spec_exp_booms")}, {fx("0.00001")}))|%0]#!"\n'
        f' SPEC_BANK_SLICE_TT: "[SelectLocalization({OTHER}, \'SPEC_BANK_OTHER_TT\', \'SPEC_BANK_GOOD_TT\')]"\n'
        f' SPEC_BANK_GOOD_TT: "#header [Scope.GetGoods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n'
        f'#v {money(f"Multiply_CFixedPoint({SHARE}, {debt})")}#! is lent into its boom, $SPEC_BANK_GOOD_SHARE$ of boom loans and #v [{SHARE}|%1]#! of all [concept_spec_outstanding_credit].\\n\\nIf its boom ended, these loans would make '
        f'[concept_spec_market_confidence] fall #N x[{MULT}|2]#! as far"\n'
        ' SPEC_BANK_NONE_S: "#grey No credit lent into booms#!\\n$SPEC_GAUGE_LEND$"\n'
        ' SPEC_BANK_NONE: "None of our [concept_spec_outstanding_credit] is lent into booming goods.\\n$SPEC_GAUGE_LEND$"\n'
        ' SPEC_LHIST_EMPTY: "#grey Recorded each month from now on#!"\n'
        ' SPEC_H_CREDIT_HISTORY: "Credit Leverage History"\n'
        f' SPEC_H_CREDIT_HISTORY_TT: "#header Credit Leverage History#!\\n$TOOLTIP_DELIMITER$\\n'
        f'Our [concept_spec_leverage] over the last #v {HISTORY}#! months, newest on the right. It is #P Safe#! up to #v {leverage.SAFE}#! months, '
        f'#v Risky#! up to #v {leverage.DANGER}#! and #N Dangerous#! past that.\\n'
        '\\nThe white line is our Lending Limit. Each mark on the right edge shows the [concept_spec_market_confidence] below which a '
        '[concept_spec_financial_panic] would start at that much leverage."\n'
        f' SPEC_H_CREDIT_HISTORY_RIGHT: "Now #v [{sv("spec_lev")}|1]#! months"\n'
        f' SPEC_LHIST_OLDEST: "#grey {HISTORY - 1} Months Ago#!"\n'
        ' SPEC_LHIST_NOW: "#grey This Month#!"\n'
        ' SPEC_LHIST_KEY_SAFE: "Safe"\n'
        ' SPEC_LHIST_KEY_RISKY: "Risky"\n'
        ' SPEC_LHIST_KEY_DANGER: "Dangerous"\n'
        + "".join(f' SPEC_LHIST_PANIC_{m}: "#low Panic {at(m)}#!"\n'
                  f' SPEC_LHIST_PANIC_{m}_TT: "#header Panic Threshold: {at(m)}#!\\n$TOOLTIP_DELIMITER$\\n'
                  f'At #v {m}#! months of [concept_spec_leverage], a [concept_spec_financial_panic] '
                  f'starts if [concept_spec_market_confidence] drops below #v {at(m)}#!"\n' for m in (leverage.SAFE, leverage.DANGER, leverage.LADDER[-1]))
        + "".join(f' SPEC_LHIST_{n}_TT: "[SelectLocalization({P}.Var(\'spec_lhist{n}\').IsSet, \'SPEC_LHIST_{n}_ON\', \'SPEC_HIST_NONE\')]"\n'
                  f' SPEC_LHIST_{n}_ON: "#header {when(n)}#!\\n#v [{lev(n)}|1]#! months of [concept_spec_leverage]"\n' for n in range(1, HISTORY + 1))
        + ' SPEC_BANK_OTHER: "Other Goods"\n'
        f' SPEC_BANK_OTHER_TT: "#header $SPEC_BANK_OTHER$#!\\n$TOOLTIP_DELIMITER$\\n#v {money(f"Multiply_CFixedPoint({OTHER_SHARE}, {debt})")}#! is lent into these booms, '
        f'$SPEC_BANK_OTHER_SHARE$ of boom loans and #v [{OTHER_SHARE}|%1]#! of all [concept_spec_outstanding_credit]."\n'
        + ' SPEC_IW_PIE: "Trade by [concept_spec_investor_interest]"\n'
        ' SPEC_IW_NONE: "#grey Shown from the start of next month#!"\n'
        f' SPEC_IW_SLICE_WORD: "{IW_WORD_TEXT}"\n'
        + f' SPEC_IW_CHART_WORD: "[{by_word(lambda w: repr(f"SPEC_INTEREST_{w - 1}"), "SelectLocalization")}]"\n'
        + f' SPEC_IW_SLICE_TT: "[{by_word(lambda w: f"\'SPEC_IW_LVL_{w}_TT\'", "SelectLocalization")}]"\n'
        f' SPEC_IW_SLICE_SHARE: "[{by_word(lambda w: f"\'SPEC_IW_SHARE_{w}\'", "SelectLocalization")}]"\n'
        + "".join(f' SPEC_IW_SHARE_{w}: "#v [{lvl(w)}|%1]#!"\n'
                  f' SPEC_IW_LVL_{w}_TT: "#header $SPEC_INTEREST_{w - 1}$#!\\n$TOOLTIP_DELIMITER$\\n#v [{lvl(w)}|%1]#! of the market\'s trade, '
                  f'#v {money(trade(lvl(w)))}#!, is in #v [{v(f"spec_n_w{w}")}|0]#! $SPEC_INTEREST_{w - 1}$ goods."\n'
                  for w in range(1, 7)))


if __name__ == "__main__":
    for part in (lent(), credit_history(), interest_chart(), interest_script(["coal"]), script(["coal"]), history_shift(), loc({"CREDIT_FROM": 1, "PANIC": 25, "CATEGORY": {"coal": "energy"}})):
        assert part.count("{") == part.count("}"), part[:80]
    assert script(["coal", "iron"]).count(f"add_to_variable_list = {{ name = {LIST} ") == TOP_N + 1  # one pick per rank, then Other goods
    assert sorted_list("x", ["coal"], lambda g: g, "").count("while = {") == 1
    assert script(["coal"]).index("var:spec_debt >= 1") < script(["coal"]).index("spec_rank_v")  # no debt, no passes
    assert interest_script(["coal"]).count(f"add_to_variable_list = {{ name = {LEVELS} ") == 36  # six rounds, each able to list any level
    print("charts ok")
