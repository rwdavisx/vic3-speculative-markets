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
from market_tab import P, W, fx, gt, sv, v, ind, good_var, block, header, expiry_date, WORDS, WARNING, FIN

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


# blue chips (companies.BLUE_UPDATE): the status, its run of low months, or the climb towards it; never two at once
_CV = lambda n: f"Company.MakeScope.Var('{n}')"
BC, BC_LOW, BC_CLIMB = (f"{_CV(n)}.IsSet" for n in ("spec_blue_chip", "spec_bc_low", "spec_bc_months"))
COTY, PROPPED, FRAGILE = (f"{_CV(n)}.IsSet" for n in ("spec_coty", "spec_bc_propped", "spec_bc_fragile"))  # bluechips.py


def badge():
    """The company's icon, with the blue chip badge on its corner: whole for a blue chip, faded while its low months
    run, faint while it climbs towards the status."""
    alpha = f"Select_float({BC}, Select_float({BC_LOW}, '(float)0.55', '(float)1.0'), '(float)0.3')"
    return f"""widget = {{
	size = {{ {CO_ICON} {CO_ICON} }}
	icon = {{
		size = {{ {CO_ICON} {CO_ICON} }}
		texture = "[Company.GetCompanyType.GetIcon]"
	}}
	icon = {{
		size = {{ 24 24 }}
		parentanchor = bottom|right
		position = {{ 6 6 }}
		visible = "[Or({BC}, {BC_CLIMB})]"
		alpha = "[{alpha}]"
		texture = "{icons.path('blue_chip')}"
	}}
}}
"""


def tooltip_lines():
    blue = "".join(f"""custom_tooltip_textbox = {{
	visible = "[{test}]"
	text = "{key}"
}}
""" for key, test in (("SPEC_CO_BC", BC), ("SPEC_CO_BC_LOW", BC_LOW), ("SPEC_CO_BC_CLIMB", BC_CLIMB),
                      ("SPEC_CO_COTY", COTY), ("SPEC_CO_PROPPED", f"And({BC}, {PROPPED})"), ("SPEC_CO_FRAGILE", f"And({BC}, {FRAGILE})")))
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
{ind(per_good(lines, "vertical"), 1)}{ind(blue, 1)}}}
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
	### the value and its target on the left, the blue chip status on the right of the same line
	widget = {{
		size = {{ {PROSPERITY_W} 18 }}
		textbox = {{
			autoresize = yes
			align = left|nobaseline
			using = fontsize_small
			text = "COMPANY_PROSPERITY_FORMATTED"
		}}
		flowcontainer = {{
			parentanchor = right
			ignoreinvisible = yes
{ind(tag(), 3)}		}}
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
{ind(badge(), 2)}		vbox = {{
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


def tag():
    """The row's blue chip status in a word, after its name: one at a time, the most pressing first."""
    urgent = f"Or({COTY}, {BC_LOW})"
    cases = (("SPEC_CO_TAG_COTY", f"And({BC}, {COTY})"),
             ("SPEC_CO_TAG_LOW", f"And(And({BC}, {BC_LOW}), Not({COTY}))"),
             ("SPEC_CO_TAG_PROPPED", f"And(And({BC}, {PROPPED}), Not({urgent}))"),
             ("SPEC_CO_TAG_FRAGILE", f"And(And({BC}, {FRAGILE}), Not(Or({urgent}, {PROPPED})))"),
             ("SPEC_CO_TAG_BC", f"And({BC}, Not(Or({urgent}, Or({FRAGILE}, {PROPPED}))))"),
             ("SPEC_CO_TAG_CLIMB", f"And({BC_CLIMB}, Not({BC}))"))
    return "".join(f"""textbox = {{
	visible = "[{test}]"
	autoresize = yes
	align = right|nobaseline
	using = fontsize_small
	text = "{key}"
}}
""" for key, test in cases)


def strip():
    """Our blue chips at a glance: the count, a slot for each that counts (up to bluechips.CAP), lit while held, and
    what they give now. Its tooltip is the header's: every effect and how a company becomes one."""
    import bluechips
    lit = lambda i: f"Select_float({gt(v('spec_bc_n'), i - 0.5)}, '(float)1.0', '(float)0.18')"
    slots = "".join(f"""	icon = {{
		size = {{ {26 if i <= bluechips.CAP else 18} {26 if i <= bluechips.CAP else 18} }}
		alpha = "[{lit(i)}]"
		texture = "{icons.path('blue_chip')}"
	}}
""" for i in range(1, bluechips.CAP2 + 1))
    return f"""widget = {{
	size = {{ {W} 56 }}
	parentanchor = hcenter
	datacontext = "[Country.MakeScope.GetCountry]"  # the tooltip's own context: without it the figures find no Country
	tooltip = "SPEC_BC_STRIP_TT"
	background = {{
		using = fade_right_colored
		color = {{ 0.35 0.55 0.9 1 }}
		alpha = 0.22
	}}
	icon = {{
		position = {{ 10 0 }}
		size = {{ 40 40 }}
		parentanchor = vcenter
		texture = "{icons.path('blue_chip')}"
	}}
	textbox = {{
		position = {{ 58 8 }}
		size = {{ 90 22 }}
		align = left|nobaseline
		using = fontsize_large
		default_format = "#header"
		text = "SPEC_BC_STRIP"
	}}
	textbox = {{
		position = {{ 58 30 }}
		size = {{ 90 18 }}
		align = left|nobaseline
		using = fontsize_small
		text = "SPEC_BC_STRIP_N"
	}}
	hbox = {{
		position = {{ 150 0 }}
		size = {{ 230 56 }}
		spacing = 3
{ind(slots, 1)}	}}
	textbox = {{
		position = {{ -12 0 }}
		size = {{ 150 54 }}
		parentanchor = right|vcenter
		align = right|nobaseline
		multiline = yes
		using = fontsize_small
		text = "SPEC_BC_STRIP_FX"
	}}
}}
"""


def section():
    body = f"""{strip()}flowcontainer = {{
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
    return block(header("SPEC_H_COMPANIES", "SPEC_H_COMPANIES_RIGHT", "SPEC_H_COMPANIES_RIGHT_TT"), body)


def bc_loc():
    import bluechips as b
    n = sv("spec_bc_counted")
    mul = lambda x: f"Multiply_CFixedPoint({n}, {fx(x)})"
    lo = companies.BLUE_LOSE
    return (" SPEC_BC_STRIP: \"Blue Chips\"\n"
            f" SPEC_BC_STRIP_N: \"#v [{v('spec_bc_n')}|0]#! held\"\n"
            f" SPEC_BC_STRIP_FX: \"Crash shield #P [{mul(b.SHELTER * 100)}|0]%#!\\n"
            f"Contest pull #P +[{mul(b.PULL * 100)}|0]%#!\\nTrust #P +[{mul(round(b.DIVIDEND / 1.2, 3))}|1]%#! a year\"\n"
            f" SPEC_BC_STRIP_TT: \"#header $concept_spec_blue_chips$: #v [{v('spec_bc_n')}|0]#!#!\\n$TOOLTIP_DELIMITER$\\n"
            f"A company becomes one after #v {companies.BLUE_MONTHS}#! months in a row at "
            f"#v {companies.BLUE_PROSPER:g}#! or more [concept_prosperity].\\n\\n"
            + b.effect_lines(lambda x, f: f"[{mul(round(x, 4))}|{f}]", each=True)
            + f"\\n#grey The first {b.CAP} count in full and the next {b.CAP2 - b.CAP} half. Each also adds #v {companies.BLUE_BONUS:g}#! to our "
            "[concept_spec_company_strength].#!"
            + "\\n$TOOLTIP_DELIMITER$\\n" + b.risk_text() + "\"\n"
            " SPEC_CO_TAG_COTY: \"#P Company of the Year#!\"\n"
            f" SPEC_CO_TAG_LOW: \"#N Slipping [{_CV('spec_bc_low')}.GetValue|0]/{lo}#!\"\n"
            " SPEC_CO_TAG_FRAGILE: \"#N Fragile#!\"\n"
            " SPEC_CO_TAG_PROPPED: \"#P Propped Up#!\"\n"
            " SPEC_CO_TAG_BC: \"#P Blue Chip#!\"\n"
            ' SPEC_CO_TAG_CLIMB: "#grey [Company.MakeScope.ScriptValue(\'spec_bc_updates_left\')|0] months left#!"\n')


def loc():
    status_date = lambda key: f"{_CV('spec_bc_' + key)}.GetValueWithDefault({fx(0)})"
    words = "".join(f' SPEC_CO_W{w}: "@spec_interest_{word}! #v {word.capitalize()}#!"\n' for w, word in sorted(WORDS.items()))
    pick = "".join(f"SelectLocalization(EqualTo_CFixedPoint({WORD}, {fx(w)}), 'SPEC_CO_W{w}', " for w in sorted(WORDS))
    pick = f"[{pick}'SPEC_CO_W0'{')' * len(WORDS)}]"
    kstr, kbc = f"{P}.ScriptValue('spec_log_kstr')", v('spec_bc_n')
    from_bc = f"Multiply_CFixedPoint({kbc}, {fx(companies.BLUE_BONUS)})"  # centres' spec_log_kstr: prosperity / CO_STRENGTH + this
    return (" SPEC_H_COMPANIES: \"Companies\"\n"
            f" SPEC_H_COMPANIES_TT: \"#header $concept_companies$#!\\n$TOOLTIP_DELIMITER$\\n"
            "High [concept_spec_investor_interest] in a [concept_good] gives the buildings that make it #P more#! [concept_throughput], "
            "and low interest gives them #N less#!. After its boom ends they get #N less still#! until it recovers.\\n\\n"
            "A [concept_company] making the good gains or loses [concept_prosperity] the same way.\"\n"
            f" SPEC_H_COMPANIES_RIGHT: \"[GetDataModelSize(Country.GetCompanies)]  @spec_blue_chip! #v [{v('spec_bc_n')}|0]#!\"\n"
            f" SPEC_H_COMPANIES_RIGHT_TT: \"#header [concept_spec_company_strength]: #v [{kstr}|1]#!#!\\n$TOOLTIP_DELIMITER$\\n"
            f"#v [Subtract_CFixedPoint({kstr}, {from_bc})|1]#! from the [concept_prosperity] of our $concept_companies$, "
            f"#v 1#! for every #v {__import__('centres').CO_STRENGTH:g}#!\\n"
            f"#v [{from_bc}|1]#! from our #v [{kbc}|0]#! @spec_blue_chip! [Concept('concept_spec_blue_chip','$concept_spec_blue_chips$')], "
            f"#v {companies.BLUE_BONUS:g}#! each\\n$TOOLTIP_DELIMITER$\\n"
            "The strongest [concept_country] can claim Home of Great Companies as a speciality of its [concept_spec_exchange]. "
            "More companies help only through their [concept_prosperity].\"\n"
            f" SPEC_CO_BC: \"#P [concept_spec_blue_chip]#!, adding #v {companies.BLUE_BONUS:g}#! to our [concept_spec_company_strength] "
            "and counting toward our $concept_spec_blue_chips$\"\n"
            f" SPEC_CO_BC_LOW: \"  #N Slipping#! below #v {companies.BLUE_PROSPER:g}#! [concept_prosperity] for #v [{_CV('spec_bc_low')}.GetValue|0]#! "
            f"of #v {companies.BLUE_LOSE}#! months. At #v {companies.BLUE_LOSE}#! it stops being one.\"\n"
            f" SPEC_CO_BC_CLIMB: \"Becomes a [concept_spec_blue_chip] after #v [Company.MakeScope.ScriptValue('spec_bc_updates_left')|0]#! more months at #v {companies.BLUE_PROSPER:g}#! or more [concept_prosperity]\"\n"
            " SPEC_CO_COTY: \"#P Company of the Year#!, the world's most prosperous [concept_spec_blue_chip]\"\n"
            f" SPEC_CO_PROPPED: \"  Propped up to keep its status, whatever its [concept_prosperity][AddLocalizationIf({gt(status_date('propped'), 1)}, 'SPEC_CO_PROPPED_END')]\"\n"
            f" SPEC_CO_FRAGILE: \"  #N Fragile#!, so a single month below #v {companies.BLUE_PROSPER:g}#! [concept_prosperity] loses the status[AddLocalizationIf({gt(status_date('fragile'), 1)}, 'SPEC_CO_FRAGILE_END')]\"\n"
            f" SPEC_CO_PROPPED_END: \" until #v {expiry_date(status_date('propped'), 'Company.MakeScope')}#!\"\n"
            f" SPEC_CO_FRAGILE_END: \" until #v {expiry_date(status_date('fragile'), 'Company.MakeScope')}#!\"\n"
            " SPEC_CO_NONE: \"#low We own no companies#!\"\n"
            + bc_loc() +
            f" SPEC_CO_PCT: \"[{EFFECT}|+=0]%\"\n"
            " SPEC_CO_TT_HEAD: \"#header [concept_spec_investor_interest]#!\"\n"
            f" SPEC_CO_LINE: \"[{PCT}|+=%0] [concept_throughput] from {pick} [Goods.GetName]\"\n"
            f" SPEC_CO_ENC: \"  #P +{LEVER}%#! [concept_throughput] from Encourage Investment\"\n"
            f" SPEC_CO_RES: \"  #N -{LEVER}%#! [concept_throughput] from Restrain Speculation\"\n"
            f" SPEC_CO_GLUT: \"  @warning! #N [{GLUT_LOSS}|%0]#! [concept_throughput] for #v [{GLUT_MONTHS}|0]#! months while [Goods.GetName] recovers\"\n"
            " SPEC_CO_W0: \"#low untraded#!\"\n" + words + __import__("bluechips").loc())


if __name__ == "__main__":
    gui, text = section(), loc()
    assert gui.count("{") == gui.count("}") and "SPEC_CO_PCT" in gui and "spec_bt_g3_" in gui
    assert gui.index(f"Clear('{FIN}')") < gui.index("OpenCompanyPanel"), "opening a company closes Finance"
    pct_line = text.split("SPEC_CO_PCT:")[1].split("\n")[0]
    assert "spec_ui_co_" in pct_line and "Select_CFixedPoint" not in pct_line
    assert "set_variable = { name = spec_ui_co_$G$ value = -10 }" in levers.ui_effect() and f"add = {LEVER}" in levers.ui_effect()
    assert "SPEC_CO_W6" in text and "'SPEC_CO_W0'" in text and text.count("SPEC_CO_PCT:") == 1
    assert "SPEC_CO_TT_NOTE" not in gui + text and "elide_fontsize_min" in gui and "max_width" not in gui
    for k in ("SPEC_CO_BC", "SPEC_CO_BC_LOW", "SPEC_CO_BC_CLIMB"):
        assert f'text = "{k}"' in gui and f" {k}:" in text
    assert BC_CLIMB in gui and "SPEC_CO_TAG_CLIMB" in gui and "spec_bc_n" in text and "@spec_blue_chip!" in text
    assert fx(round(companies.COMPANY_BUST, 4)) in GLUT_LOSS and fx(round(companies.UNWIND[3][1] / 30)) in GLUT_MONTHS
    print("ok")
