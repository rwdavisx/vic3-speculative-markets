"""Companies, the last section of the Speculation tab: the market owner's companies and what speculation does to them.

One row per company, built from vanilla's own pieces: the company type's background art faint behind it, right
anchored as the building browser sets a building type's (building_browser_panel.gui:3498-3506); the company's icon,
name and vanilla's prosperity line under it (companies_panel.gui:1194-1265: the value, its target and the bar with the
changed value animations), prosperity being what speculation's throughput moves; then a chip for each good its
buildings make, the good in the round tinted frame of the goods rows with its investor interest icon on the corner and
a recovering warning, over the throughput the speculation gives those buildings, the interest tier's percent plus an
intervention's.
A glut's loss is not added: its modifier can outlast the glut variable, so the tooltip gives it on its own line. Clicking a row
opens the company panel, as the companies panel's name button does (companies_panel.gui:659). The tooltip is vanilla's
company tooltip with each good's interest, intervention and glut on top.

The GUI has no way from a building type to its goods, so companies.py stores them once in global variables
(companies.BT_SLOT) by building type key. Building types making no good with a throughput modifier show no chip.
ponytail: a company with several grain farms shows grain once for each.
"""
import companies
import icons
import levers
from market_tab import P, W, fx, gt, sv, ind, good_var, block, header, WORDS, WARNING, FIN

WORD = good_var("spec_word")  # 0 not traded here, 1 Fleeing to 6 Feverish
GLUT = good_var("spec_glut")
ENCOURAGE, RESTRAIN = good_var("spec_encourage"), good_var("spec_restrain")
LEVER = round(levers.LEVER_THROUGHPUT * 100)
CHIP_W, CHIP_ICON, GAP = 40, 34, 4
ROW_H = 72  # the name, the prosperity line and its bar, one under another
CO_ICON = 44
PROSPERITY_W = 220  # the name, prosperity text and bar column, the same width in every row


def select(cases, default):
    """Nested Select_CFixedPoint: the first true test picks its value."""
    out = default
    for test, value in reversed(cases):
        out = f"Select_CFixedPoint({test}, {value}, {out})"
    return out


# the throughput % interest and intervention give the good's producers, stored by levers.ui_effect() so the chip reads
# one variable each frame instead of a select over the interest words
EFFECT = good_var("spec_ui_co")
PCT = f"Multiply_CFixedPoint({EFFECT}, {fx(0.01)})"
# the glut's loss and length by how the boom ended (the glut variable holds the severity): companies.crash()'s modifier.
# ponytail: a milder end leaves an older, stronger glut modifier running, so these can understate it
_by_sev = lambda f: select([(f"EqualTo_CFixedPoint({GLUT}, {fx(s)})", fx(f(s))) for s in sorted(companies.UNWIND)], fx(0))
GLUT_LOSS = f"Multiply_CFixedPoint({sv('spec_company_tie')}, {_by_sev(lambda s: round(companies.COMPANY_BUST * companies.UNWIND[s][0], 4))})"
GLUT_MONTHS = _by_sev(lambda s: round(companies.UNWIND[s][1] / 30))


def slot(n, body):
    """body once for the n-th good of the BuildingType in context, with that Goods as the datacontext."""
    var = f"GetGlobalVariable(Concatenate('{companies.BT_SLOT.format(n)}', BuildingType.GetKey))"
    return f"""flowcontainer = {{
	visible = "[{var}.IsSet]"
	flowcontainer = {{
		datacontext = "[{var}.GetGoods]"
		direction = vertical
		ignoreinvisible = yes
{ind(body, 2)}	}}
}}
"""


def per_good(body, direction="horizontal"):
    """body for each good the company's building types make."""
    slots = "".join(slot(n, body) for n in range(1, companies.BT_SLOTS + 1))
    return f"""flowcontainer = {{
	direction = {direction}
	ignoreinvisible = yes
	spacing = {GAP}
	datamodel = "[Company.GetBuildingTypes]"
	item = {{
		flowcontainer = {{
			direction = {direction}
			ignoreinvisible = yes
			spacing = {GAP}
{ind(slots, 3)}		}}
	}}
}}
"""


def chip():
    tiers = "".join(f"""icon = {{
	size = {{ 18 18 }}
	position = {{ {CHIP_W // 2 + 4} {CHIP_ICON - 16} }}
	visible = "[EqualTo_CFixedPoint({WORD}, {fx(w)})]"
	texture = "{icons.path('interest_' + word)}"
}}
""" for w, word in sorted(WORDS.items()))
    return f"""widget = {{
	size = {{ {CHIP_W} {CHIP_ICON + 18} }}
	icon = {{
		size = {{ {CHIP_ICON} {CHIP_ICON} }}
		parentanchor = hcenter
		texture = "gfx/interface/market_view/trade_good_icon_bg.dds"
		color = "[Goods.GetCategoryColor]"
		icon = {{
			size = {{ 26 26 }}
			parentanchor = center
			texture = "[Goods.GetTexture]"
		}}
	}}
{ind(tiers, 1)}	icon = {{
		size = {{ 16 16 }}
		position = {{ {CHIP_W // 2 + 4} 0 }}
		visible = "[{gt(GLUT)}]"
		texture = "{WARNING}"
	}}
	textbox = {{
		position = {{ 0 {CHIP_ICON} }}
		size = {{ {CHIP_W} 18 }}
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_CO_PCT"
	}}
}}
"""


def tooltip_lines():
    lines = "".join(f"""custom_tooltip_textbox = {{
	{f'visible = "[{test}]"' if test else ""}
	text = "{key}"
}}
""" for key, test in (("SPEC_CO_LINE", None), ("SPEC_CO_ENC", gt(ENCOURAGE)), ("SPEC_CO_RES", gt(RESTRAIN)),
                      ("SPEC_CO_GLUT", gt(GLUT))))
    return f"""flowcontainer = {{
	direction = vertical
	ignoreinvisible = yes
	custom_tooltip_textbox = {{
		text = "SPEC_CO_TT_HEAD"
	}}
{ind(per_good(lines, "vertical"), 1)}}}
"""


def prosperity():
    """vanilla's prosperity line from the companies panel (companies_panel.gui:1194-1265), at row size: the bar, with
    the changed value animations while it moves and the target faint behind, then the value and its target."""
    pmax = "GetDefine('NEconomy','COMPANY_PROSPERITY_MAX')"
    values = f"""blockoverride "values" {{
	min = 0
	max = "[{pmax}]"
	value = "[Company.GetProsperity]"
}}
blockoverride "arrow_texture_density" {{
	texture_density = 4
}}
"""
    below_max = f"LessThan_CFixedPoint(Company.GetProsperity, {pmax})"
    return f"""vbox = {{
	spacing = 3
	tooltip = "COMPANY_PROSPERITY_TOOLTIP"
	### the value and its target over the bar, as vanilla lays them out, on a line of their own so they never reach the goods
	textbox = {{
		autoresize = yes
		align = left|nobaseline
		using = fontsize_small
		text = "COMPANY_PROSPERITY_FORMATTED"
	}}
	widget = {{
		size = {{ {PROSPERITY_W} 10 }}
		changed_value_increased_progressbar_horizontal = {{
			visible = "[And(GreaterThan_CFixedPoint(Company.GetProsperityChange, '(CFixedPoint)0'), {below_max})]"
			size = {{ 100% 100% }}
{ind(values, 3)}			blockoverride "animate_negative_change" {{
				animate_negative_changes = no
			}}
		}}
		changed_value_decreased_progressbar_horizontal = {{
			visible = "[And(LessThan_CFixedPoint(Company.GetProsperityChange, '(CFixedPoint)0'), {below_max})]"
			size = {{ 100% 100% }}
{ind(values, 3)}		}}
		default_progressbar_horizontal = {{
			visible = "[Or(EqualTo_CFixedPoint(Company.GetProsperityChange, '(CFixedPoint)0'), Not({below_max}))]"
			size = {{ 100% 100% }}
{ind(values, 3)}		}}
		default_progressbar_horizontal = {{
			visible = "[NotEqualTo_CFixedPoint(Company.GetProsperity, Company.GetTargetProsperity)]"
			size = {{ 100% 100% }}
			alpha = 0.2
			blockoverride "values" {{
				min = 0
				max = "[{pmax}]"
				value = "[Company.GetTargetProsperity]"
			}}
			blockoverride "background" {{}}
			blockoverride "frame" {{}}
		}}
	}}
}}
"""


def row():
    return f"""button = {{
	size = {{ {W} {ROW_H} }}
	using = alternating_dark_bg
	onclick = "[GetVariableSystem.Clear('{FIN}')]"
	onclick = "[InformationPanelBar.OpenCompanyPanel(Company.Self)]"
	tooltipwidget = {{
		FancyTooltip_Company = {{
			blockoverride "tooltip_content_before" {{
{ind(tooltip_lines(), 4)}			}}
		}}
	}}
	### the company type's art, faint and fading to the left, behind the goods; a background, as vanilla draws it
	### (companies_panel.gui:754), since only backgrounds take fittype
	widget = {{
		size = {{ 300 100% }}
		parentanchor = right
		alpha = 0.3
		background = {{
			texture = "[Company.GetCompanyType.GetBackground]"
			fittype = centercrop
			modify_texture = {{
				texture = "gfx/interface/masks/fade_horizontal_left.dds"
				spriteType = Corneredstretched
				spriteborder = {{ 0 0 }}
				blend_mode = alphamultiply
			}}
		}}
	}}
	### as vanilla's list rows: the name and prosperity take what the goods leave and elide, never running under them
	hbox = {{
		size = {{ 100% 100% }}
		margin_left = 10
		margin_right = 10
		spacing = 10
		icon = {{
			size = {{ {CO_ICON} {CO_ICON} }}
			texture = "[Company.GetCompanyType.GetIcon]"
		}}
		vbox = {{
			spacing = 4
			textbox = {{
				size = {{ {PROSPERITY_W} 24 }}
				align = left|nobaseline
				using = elide_fontsize_min
				default_format = "#header"
				text = "[Company.GetNameNoFormatting]"
			}}
{ind(prosperity(), 3)}		}}
		expand = {{}}
{ind(per_good(chip()), 2)}	}}
}}
"""


def section():
    body = f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	visible = "[Not(IsDataModelEmpty(Country.GetCompanies))]"
	datamodel = "[Country.GetCompanies]"
	item = {{
{ind(row(), 2)}	}}
}}
textbox = {{
	size = {{ {W} 30 }}
	parentanchor = hcenter
	visible = "[IsDataModelEmpty(Country.GetCompanies)]"
	align = center|nobaseline
	text = "SPEC_CO_NONE"
}}
"""
    return block(header("SPEC_H_COMPANIES", "SPEC_H_COMPANIES_RIGHT"), body)


def loc():
    words = "".join(f' SPEC_CO_W{w}: "@spec_interest_{word}! #v {word.capitalize()}#!"\n' for w, word in sorted(WORDS.items()))
    pick = "".join(f"SelectLocalization(EqualTo_CFixedPoint({WORD}, {fx(w)}), 'SPEC_CO_W{w}', " for w in sorted(WORDS))
    pick = f"[{pick}'SPEC_CO_W0'{')' * len(WORDS)}]"
    company = "[concept_company]"
    return (" SPEC_H_COMPANIES: \"Companies\"\n"
            f" SPEC_H_COMPANIES_TT: \"#header $concept_companies$#!\\n$TOOLTIP_DELIMITER$\\n[concept_spec_investor_interest] in a good raises or "
            f"lowers the [concept_throughput] of the buildings making it, and lowers it further while the good recovers after its boom. A "
            f"{company} earns more while its goods are in favor and less once they fall.\"\n"
            " SPEC_H_COMPANIES_RIGHT: \"[GetDataModelSize(Country.GetCompanies)]\"\n"
            " SPEC_CO_NONE: \"#low We have no Companies#!\"\n"
            f" SPEC_CO_PCT: \"[{EFFECT}|+=0]%\"\n"
            " SPEC_CO_TT_HEAD: \"#header [concept_spec_investor_interest]#!\"\n"
            f" SPEC_CO_LINE: \"[Goods.GetName]: {pick}, [concept_throughput] [{PCT}|+=%0]\"\n"
            f" SPEC_CO_ENC: \"  Encourage Investment: [concept_throughput] #P +{LEVER}%#!\"\n"
            f" SPEC_CO_RES: \"  Restrain Speculation: [concept_throughput] #N -{LEVER}%#!\"\n"
            f" SPEC_CO_GLUT: \"  @warning! #N [Goods.GetName] Recovering#!: [concept_throughput] #N [{GLUT_LOSS}|%0]#! for #v [{GLUT_MONTHS}|0]#! months\"\n"
            " SPEC_CO_W0: \"#low not traded here#!\"\n" + words)


if __name__ == "__main__":
    gui, text = section(), loc()
    assert gui.count("{") == gui.count("}") and "SPEC_CO_PCT" in gui and "spec_bt_g3_" in gui
    assert gui.index(f"Clear('{FIN}')") < gui.index("OpenCompanyPanel"), "opening a company closes Finance"
    pct_line = text.split("SPEC_CO_PCT:")[1].split("\n")[0]
    assert "spec_ui_co_" in pct_line and "Select_CFixedPoint" not in pct_line
    assert "set_variable = { name = spec_ui_co_$G$ value = -10 }" in levers.ui_effect() and f"add = {LEVER}" in levers.ui_effect()
    assert "SPEC_CO_W6" in text and "'SPEC_CO_W0'" in text and text.count("SPEC_CO_PCT:") == 1
    assert "SPEC_CO_TT_NOTE" not in gui + text and "elide_fontsize_min" in gui and "max_width" not in gui
    assert fx(round(companies.COMPANY_BUST, 4)) in GLUT_LOSS and fx(round(companies.UNWIND[3][1] / 30)) in GLUT_MONTHS
    print("ok")
