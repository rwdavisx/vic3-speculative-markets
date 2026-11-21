"""Investor Interest in the vanilla goods panel (the window a good opens on click), under the taxes and tariffs.

generate.py copies the vanilla goods_panel.gui and inserts two spec_goods_interest rows before the price graph:
one for the player's own market, one for the owner's data in another market, as market_panel() does for the tab.
The block reads the good's spec_word, spec_sev, spec_risk and spec_glut from Country.MakeScope and hides while the
good has no word yet (the system has not run, or the good is not traded there).
"""
import sys

import icons

import interest_list
import levers
from market_tab import W, fx, ind, good_var, RISK

WORD = good_var("spec_word")  # 0 none, 1 Fleeing to 6 Feverish
SEV = good_var("spec_sev")    # 0 none, 1 Correction, 2 Bust, 3 Collapse
GLUT = good_var("spec_glut")


def ge(a, n):
    return f"GreaterThanOrEqualTo_CFixedPoint({a}, {fx(n)})"


def is_word(w):
    return f"EqualTo_CFixedPoint({WORD}, {fx(w)})"


HAS_DATA = f"GreaterThan_CFixedPoint({WORD}, {fx(0)})"


OWN = "ObjectsEqual(GetPlayer.GetCapital.GetMarket, Goods.GetMarket)"

# a boom that would end (spec_sev), or the one that just ended while the good recovers (spec_glut holds its severity)
ENDING = f"Or({ge(SEV, 1)}, GreaterThan_CFixedPoint({GLUT}, {fx(0)}))"
SHOWN_SEV = f"Max_CFixedPoint({SEV}, {GLUT})"
NAME_H = 28  # the interest bar's name line
COL_H = 100  # each column: its title, then its content
RISK_W, MEDAL = 80, 50  # the Crash Risk column and its medallion
SEG, GAP = 30, 8  # the interest bar's segments; the space either side of each column divider
MARGIN = 16  # the row's side margin
LEVERS_W = 35 * (3 if levers.ISSUE_ON else 2) + 10  # vanilla's set_level_bar_item width, and its background's margins


def risk_icons():
    """The Crash Risk column's medallion (icons ending_<n>): no risk, or the ending this boom would reach, faded while
    the good recovers from one that has happened."""
    out = f"""icon = {{
	visible = "[Not({ENDING})]"
	size = {{ {MEDAL} {MEDAL} }}
	parentanchor = hcenter
	texture = "{icons.path('ending_0')}"
}}
"""
    for s in (1, 2, 3):
        out += f"""icon = {{
	visible = "[And({ENDING}, EqualTo_CFixedPoint({SHOWN_SEV}, {fx(s)}))]"
	size = {{ {MEDAL} {MEDAL} }}
	parentanchor = hcenter
	texture = "{icons.path(f'ending_{s}')}"
	alpha = "[Select_float({ge(SEV, 1)}, '(float)1.0', '(float)0.6')]"
}}
"""
    return out


def block_type():
    """One row as vanilla's Consumption Taxes and Tariffs above it (goods_panel.gui:185-285), in titled columns with
    dividers: Investor Interest with the Speculation tab's goods list scale, larger (interest_list.sized: tier icon,
    name, bar and animations), Crash Risk (the ending this boom would reach and its Market Confidence cost), and in the
    player's own market the tab's Restrain and Encourage control."""
    bar, (bw, bh) = interest_list.sized(good_var, seg=SEG, bar_h=22, name_h=NAME_H, crash=40, font="fontsize_large")
    bar_x = interest_list.ICON_X + 28 + interest_list.NAME_GAP + 22 + 10
    bar_w = bw - bar_x - interest_list.ICON_X  # the title and the throughput line centre on the bar
    assert 2 * MARGIN + bw + 4 * GAP + RISK_W + LEVERS_W <= W, (bw, W)
    return f"""types spec_goods_panel {{
	type spec_goods_interest = widget {{
		size = {{ {W} {COL_H + 28} }}
		parentanchor = hcenter
		hbox = {{
			layoutpolicy_horizontal = expanding
			layoutpolicy_vertical = expanding
			margin = {{ {MARGIN} 14 }}
			background = {{
				using = entry_bg_simple
			}}
			vbox = {{
				layoutpolicy_horizontal = expanding
				spacing = 8
				widget = {{
					size = {{ {bw} 24 }}
					textbox = {{
						position = {{ {bar_x} 0 }}
						size = {{ {bar_w} 24 }}
						text = "SPEC_GP_TITLE"
						align = center|nobaseline
					}}
				}}
				widget = {{
					size = {{ {bw} {bh} }}
{ind(bar, 5)}				}}
			}}
			widget = {{
				size = {{ {GAP} 5 }}
			}}
			vertical_divider_full = {{
				blockoverride "size" {{
					size = {{ 0 {COL_H} }}
				}}
			}}
			widget = {{
				size = {{ {GAP} 5 }}
			}}
			vbox = {{
				minimumsize = {{ {RISK_W} -1 }}
				spacing = 2
				tooltip = "[SelectLocalization({ge(RISK, 0.5)}, 'SPEC_RISK_TT', 'SPEC_RISK_NONE_TT')]"
				using = tooltip_ws
				textbox = {{
					text = "SPEC_GP_RISK_TITLE"
					autoresize = yes
					align = center|nobaseline
				}}
				widget = {{
					size = {{ {RISK_W} {MEDAL} }}
{ind(risk_icons(), 5)}				}}
				textbox = {{
					size = {{ {RISK_W} 22 }}
					text = "SPEC_GP_RISK_TEXT"
					align = center|nobaseline
					using = elide_fontsize_min
				}}
				expand = {{}}
			}}
			widget = {{
				visible = "[{OWN}]"
				size = {{ {GAP} 5 }}
			}}
			vertical_divider_full = {{
				visible = "[{OWN}]"
				blockoverride "size" {{
					size = {{ 0 {COL_H} }}
				}}
			}}
			widget = {{
				visible = "[{OWN}]"
				size = {{ {GAP} 5 }}
			}}
			vbox = {{
				visible = "[{OWN}]"
				layoutpolicy_horizontal = expanding
				layoutpolicy_vertical = expanding
				spacing = 8
				textbox = {{
					text = "SPEC_GP_LEVERS"
					autoresize = yes
					align = center|nobaseline
				}}
{ind(levers.strip(), 4)}				expand = {{}}
			}}
		}}
	}}
}}
"""


# Shared Finance destination for the journal shortcut.
# ponytail: four onclicks through the one onclick = "{OPEN_TAB}" its users write
# Keep the Financial Markets entry underneath Finance for its map mode.
OPEN_TAB = ("[GetVariableSystem.Clear('spec_pick_slot')]\"\n"
            "\t\tonclick = \"[GetVariableSystem.Set('spec_finance_tab', 'booms')]\"\n"
            "\t\tonclick = \"[GetVariableSystem.Set('spec_finance', 'journal_map')]\"\n"
            "\t\tonclick = \"[GetVariableSystem.Clear('spec_finance_next')]")


def patch(gui):
    """One row before the price graph: the player's own data in their market, the owner's in others."""
    anchor = "\t\t\t\t\t### GRAPH LINE\n"
    if gui.count(anchor) != 1:
        sys.exit(f"goods_panel.gui changed, can't find: {anchor!r}")
    blocks = f"""					spec_goods_interest = {{
						datacontext = "[GetPlayer]"
						visible = "[And({OWN}, {HAS_DATA})]"
					}}
					spec_goods_interest = {{
						datacontext = "[Goods.GetMarket.GetOwner]"
						visible = "[And(Not({OWN}), {HAS_DATA})]"
					}}
"""
    return gui.replace(anchor, blocks + anchor)


def loc():
    at = lambda n: ge(SEV, n)
    return f""" SPEC_OPEN_TAB: "Open $SPEC_FINANCE$"
 SPEC_OPEN_TAB_TT: "#header $SPEC_FINANCE$#!\\nOpens the $SPEC_FIN_TAB_BOOMS$ tab, which shows [concept_spec_market_confidence] and the [concept_spec_investor_interest] in each good"
 SPEC_GP_LEVERS: "[concept_spec_intervention]"
 SPEC_GP_TITLE: "[concept_spec_investor_interest]"
 SPEC_GP_RISK_TITLE: "[concept_spec_boom_end]"
 SPEC_GP_RISK_TEXT: "[SelectLocalization({ENDING}, 'SPEC_GP_SEV_NAME', 'SPEC_GP_RISK_NONE')]"
 SPEC_GP_RISK_NONE: "#v None#!"
 SPEC_GP_SEV_NAME: "[SelectLocalization({at(1)}, 'SPEC_GP_SEV_NOW', 'SPEC_GP_SEV_PAST')]"
 SPEC_GP_SEV_NOW: "#v $SPEC_UNWIND$#![SelectLocalization({ge(RISK, 0.5)}, 'SPEC_GP_COST', 'SPEC_GOODS_NONE')]"
 SPEC_GP_SEV_PAST: "#n [SelectLocalization({ge(GLUT, 3)}, 'SPEC_UNWIND_3', SelectLocalization({ge(GLUT, 2)}, 'SPEC_UNWIND_2', 'SPEC_UNWIND_1'))]#!"
 SPEC_GP_COST: " #N -[{RISK}|0]#!"
"""
