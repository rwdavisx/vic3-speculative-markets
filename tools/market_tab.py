"""The Finance window (Exchange, Speculation, Banking and Rankings tabs) and its loc.

generate.information_panel_bar hosts the window and its side bar button (tab_type). Everything here is built from vanilla pieces: entry backgrounds, headers, collapsible section
headers, the round progress pie, progress bars with markers, the budget panel's tax level control and
investment pool row, graph frames and the market panel's goods filters, goods tile, price and sparkline.

Order: where confidence stands, what the player can do about it (credit, rescue), which goods are exposed,
then the detail (what moved it, history, capital) in sections that fold away.
"""

import companies
import credit_ai
import cycle
import diplomacy
import economy
import icons
import levers
import leverage
import market_visual
import vanilla_ties

P = "Country.MakeScope"  # the player, or the owner of a market that isn't theirs (generate.market_panel)
W = 540  # vanilla's @panel_width: rows and blocks; headers keep vanilla's own size (554), tax_exp_frame rows 530
BAR_W = W - 40  # every full-width bar and scale in the window, 20 in from each side

# confidence tiers: key, from, to
TIERS = [("panic", 0, 20), ("wary", 20, 40), ("steady", 40, 60), ("buoyant", 60, 80), ("mania", 80, 100)]
BARS = "gfx/interface/progressbar"
WHITE = "gfx/interface/progressbar/progressbar_white.dds"
FLAT = "gfx/interface/graph/white.dds"
CLEAR = "gfx/interface/icons/generic_icons/transparent.dds"
# a bar's fill slides to a new value rather than snapping, as vanilla's bars do (progressbar_properties,
# progressbars.gui:35, with progressbar_changed_animation), slower than vanilla's half second: these values change
# once a month, so the slide stands in for the weekly steps vanilla's interests take
SLIDE = """skip_initial_animation = yes
animate_negative_changes = yes
state = {
	name = progress_changed
	using = Animation_Curve_Default
	duration = 1.5
}
"""
ICONS = "gfx/interface/icons/generic_icons"


def fx(n):
    return f"'(CFixedPoint){n}'"


def v(name, default=0):
    return f"{P}.Var('{name}').GetValueWithDefault({fx(default)})"


def sv(name):
    return f"{P}.ScriptValue('{name}')"


def gt(a, b=0):
    return f"GreaterThan_CFixedPoint({a}, {fx(b)})"


CONF = v("spec_conf", 55)
# variable reads, not the script values spec_stance_value and spec_in_panic: the tab evaluates these every frame
STANCE = v("spec_stance", 0)
IN_PANIC = f"{P}.Var('spec_panic').IsSet"  # spec_panic counts the months left, from 1 up, while a panic runs
ACTIVE = gt(sv("spec_law_mult"))


def sg(key, call):
    s = f"GetScriptedGui('spec_sgui_{key}').{call}(GuiScope.SetRoot({P}).End)"
    return f"[And(Country.IsLocalPlayer, {s})]" if call == "IsValid" else f"[{s}]"


def tier_test(value, lo, hi):
    tests = []
    if lo > 0:
        tests.append(f"GreaterThanOrEqualTo_CFixedPoint({value}, {fx(lo)})")
    if hi < 100:
        tests.append(f"LessThan_CFixedPoint({value}, {fx(hi)})")
    return tests[0] if len(tests) == 1 else f"And({tests[0]}, {tests[1]})"


def ind(text, n):
    return "".join(("\t" * n + line) if line.strip() else line for line in text.splitlines(True))


def header(key, right=None, right_tooltip=None, right_visible=None):
    """A vanilla section header at its default size, title on the left, with an optional key figure on the right, shown while
    right_visible holds. The title's tooltip is key_TT."""
    return f"""default_header_2texts = {{
	parentanchor = hcenter
	blockoverride "text1" {{
		text = "{key}"
		tooltip = "{key}_TT"
	}}
	blockoverride "text2" {{
		text = "{right or ''}"
		{f'tooltip = "{right_tooltip}"' if right_tooltip else ""}
		{f'visible = "[{right_visible}]"' if right_visible else ""}
	}}
}}
"""


# one spacing for every tab: a header's body starts GAP_TOP below it and ends GAP_END above the next header, and
# separate components inside a body (cards, a chart and its key) stand GAP apart
GAP_TOP, GAP_END, GAP = 6, 12, 6


def block(head, body, gap=0):
    """A section as the budget panel lays one out: the header, then its body. gap spaces the body's components."""
    spacing = f"\t\tspacing = {gap}\n" if gap else ""
    return f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
{ind(head, 1)}	flowcontainer = {{
		direction = vertical
		parentanchor = hcenter
		margin_top = {GAP_TOP}
		margin_bottom = {GAP_END}
{spacing}{ind(body, 2)}	}}
}}
"""


def heads(cols, w=W):
    """A table's row of column heads, drawn as vanilla's sort buttons are. cols: (x, width, key, align, has a tooltip);
    the tooltip is key_TT, or tip itself when it is a key. A key ending .dds draws that icon, as vanilla's rank head.
    ponytail: they sort nothing, since no table here has enough rows to sort."""
    icon = lambda key: (f"""	button = {{
		texture = "{key}"
		size = {{ 25 25 }}
		parentanchor = center
		alwaystransparent = yes
	}}
""")
    cells = "".join(f"""sort_button = {{
	position = {{ {x} 0 }}
	size = {{ {cw} 30 }}
	{f'tooltip = "{tip if isinstance(tip, str) else key + "_TT"}"' if tip else ""}
{icon(key) if key.endswith(".dds") else f"""	textbox = {{
		size = {{ 100% 100% }}
		margin = {{ {4 if cw < 80 else 10} 0 }}
		align = {align}|nobaseline
		elide = right
		{"fontsize_min = 11" if cw < 80 else ""}
		alwaystransparent = yes
		text = "{key}"
	}}
"""}}}
""" for x, cw, key, align, tip in cols)
    return f"widget = {{\n\tsize = {{ {w} 30 }}\n{ind(cells, 1)}}}\n"


def section(key, toggle, body, open_by_default=True, right=None, tooltip=None, right_tooltip=None, right_visible=None):
    """A vanilla collapsible section header, as the Market panel uses, and its body. The toggle flips the default.
    tooltip goes on the whole header; right_tooltip makes the right text hoverable (so a click on it does not fold)."""
    shown = f"Not(GetVariableSystem.Exists('{toggle}'))" if open_by_default else f"GetVariableSystem.Exists('{toggle}')"
    hidden = f"GetVariableSystem.Exists('{toggle}')" if open_by_default else f"Not(GetVariableSystem.Exists('{toggle}'))"
    right_extra = (f'\n\t\t\talwaystransparent = no\n\t\t\ttooltip = "{right_tooltip}"' if right_tooltip else "") + (
        f'\n\t\t\tvisible = "[{right_visible}]"' if right_visible else "")
    right_text = f"""	blockoverride "right_text" {{
		section_header_right_text = {{
			text = "{right}"{right_extra}
		}}
	}}
""" if right else ""
    tip = f'\n\t\ttooltip = "{tooltip}"' if tooltip else ""
    margin = f"\tmargin_top = {GAP_TOP}\n\tmargin_bottom = {GAP_END}\n"
    return f"""section_header_button = {{
	parentanchor = hcenter
	blockoverride "left_text" {{
		text = "{key}"
		fontsize_min = 12
		elide = right
	}}
{right_text}	blockoverride "onclick" {{
		onclick = "[GetVariableSystem.Toggle('{toggle}')]"{tip}
	}}
	blockoverride "onclick_showmore" {{
		visible = "[{hidden}]"
	}}
	blockoverride "onclick_showless" {{
		visible = "[{shown}]"
	}}
}}
flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	visible = "[{shown}]"
{margin}{ind(body, 1)}}}
"""


def bar(size, value, colour, direction="horizontal", extra="", texture=FLAT):
    """A bare progress bar: one colour, no frame, so several can sit side by side as a chart."""
    return f"""progressbar = {{
	size = {{ {size[0]} {size[1]} }}
	{extra}
	direction = {direction}
	progresstexture = "{texture}"
	noprogresstexture = "{CLEAR}"
	min = 0
	max = 1
	value = "[{value}]"
	color = {{ {colour} 0.9 }}
}}
"""


def clamp01(expr):
    return f"FixedPointToFloat(Max_CFixedPoint(Min_CFixedPoint({expr}, {fx(1)}), {fx(0)}))"


def share(value, scale=100):
    return clamp01(f"Divide_CFixedPoint({value}, {fx(scale)})")


# -- mood card with the tier scale -------------------------------------------------------------------------

BAR_EXPOSURE = v("spec_exposure")  # confidence collapsing booms could cost this month
BAR_TOP = v("spec_risk_top")  # what the costliest single boom ending would take; booms rarely end together
BAR_RISK = f"GreaterThanOrEqualTo_CFixedPoint({BAR_TOP}, {fx(1)})"  # the Booms at Risk row shows from here
BAR_FLOOR = f"Max_CFixedPoint(Subtract_CFixedPoint({CONF}, {BAR_EXPOSURE}), {fx(0)})"  # where all of them ending leaves it
BAR_GAP = f"Min_CFixedPoint({BAR_TOP}, {CONF})"  # what the largest ending takes, down to 0
# the tied country whose panic would hit hardest, found monthly by spec_find_risk_src
SRC = f"{P}.Var('spec_risk_src').GetCountry"
SRC_HIT = v("spec_risk_src_hit")
SRC_CONF = f"{SRC}.MakeScope.Var('spec_conf').GetValueWithDefault({fx(55)})"
SRC_RISK = f"GreaterThanOrEqualTo_CFixedPoint({SRC_HIT}, {fx(2)})"
WAR_RISK = f"GreaterThan_CFixedPoint({v('spec_war_risk')}, {fx(0)})"  # plays short of war that could become one
DEFAULT_RISK = f"{P}.Var('spec_default_risk').IsSet"  # debt near the credit limit
BAND_NAMES = ["Shaken", "Wary", "Steady", "Buoyant", "Mania"]  # the TIERS


CONF_UP = f"GreaterThanOrEqualTo_CFixedPoint({v('spec_c_total')}, {fx(0.1)})"  # as SPEC_CONF_LINE shows a change
CONF_DOWN = f"LessThanOrEqualTo_CFixedPoint({v('spec_c_total')}, {fx(-0.1)})"
PANIC_ZONE, MANIA_ZONE = tier_test(CONF, *TIERS[0][1:3]), tier_test(CONF, *TIERS[-1][1:3])
HISTORY = 36  # months the history chart shows: spec_hist1 (this month) to spec_hist36, kept by generate.monthly
CHART_H, COL_W, COL_GAP = 100, 9, 1  # a pixel a point
GOLD, BLUE, RED = "0.80 0.62 0.28", "0.30 0.52 0.66", "0.74 0.24 0.20"  # as the bar's gold, default and bad fills
HIST_MID = 50  # the chart's middle line: gold above, blue below (SPEC_HISTORY_TT)


def history_chart():
    """The last HISTORY months of confidence as columns from a middle line at 50, the bar's fear and greed turned
    upright: gold up for greed, blue down for fear, the part in Panic or Mania red. Newest on the right. Each column
    is four bars reading one variable, the lower two with vanilla's reverse hack so they hang down from their top."""
    px = CHART_H / 100  # pixels a point
    y = lambda val: round((100 - val) * px)  # top of a value's band in the chart
    col = lambda n: v(f"spec_hist{n}", HIST_MID)

    def bar(n, lo, hi, colour, down):
        return f"""progressbar = {{
	position = {{ 0 {y(hi)} }}
	size = {{ 100% {y(lo) - y(hi)} }}
	direction = vertical
	progresstexture = "{CLEAR if down else FLAT}"
	noprogresstexture = "{FLAT if down else CLEAR}"
	color = {{ {colour} 0.9 }}
	min = {lo}
	max = {hi}
	value = "[FixedPointToFloat({col(n)})]"
}}
"""
    cols = "".join(f"""widget = {{
	position = {{ {(HISTORY - n) * (COL_W + COL_GAP)} 0 }}
	size = {{ {COL_W} {CHART_H} }}
	tooltip = "SPEC_HIST_{n}_TT"
{ind(bar(n, HIST_MID, 100, GOLD, False) + bar(n, TIERS[-1][1], 100, RED, False) + bar(n, 0, HIST_MID, BLUE, True) + bar(n, 0, TIERS[0][2], RED, True), 1)}}}
""" for n in range(HISTORY, 0, -1))
    lines = "".join(f"""icon = {{
	position = {{ 0 {y(val)} }}
	size = {{ 100% 1 }}
	texture = "{FLAT}"
	color = {{ 1 1 1 {alpha} }}
}}
""" for val, alpha in ((TIERS[-1][1], 0.12), (HIST_MID, 0.35), (TIERS[0][2], 0.12)))
    return f"""widget = {{
	size = {{ {HISTORY * (COL_W + COL_GAP) - COL_GAP} {CHART_H} }}
{ind(lines + cols, 1)}}}
"""




PANIC_ZONE_BAR = f"""### the panic zone: below the line a panic begins, red and pulsing as the goods list's Collapse Zone
progressbar = {{
	size = {{ 100% 100% }}
	progresstexture = "{BARS}/progressbar_bad.dds"
	noprogresstexture = "{CLEAR}"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alwaystransparent = yes
	min = 0
	max = 100
	value = "[FixedPointToFloat({sv('spec_panic_at')})]"
	state = {{
		name = 1
		next = 2
		alpha = 0.15
		duration = 1.4
		using = Animation_Curve_Default
		trigger_on_create = yes
	}}
	state = {{
		name = 2
		next = 1
		alpha = 0.45
		duration = 1.4
		using = Animation_Curve_Default
	}}
}}
"""


def tier_scale(width):
    """Confidence as fear against greed, on vanilla's double direction bar (shared/progressbars.gui:344-456, the
    market panel's price bar): from the middle of Steady it fills left in vanilla's blue as investors grow afraid
    and right in gold as they grow greedy. Both ends are dangers, so Panic and Mania are tinted red and the fill
    turns red in either. The fill end has vanilla's glow and, while confidence moves, the changed value chevrons."""
    import interest_list as il  # imports this module
    seg = width / 5
    # the tier confidence sits in is bold; during a panic only the lowest one can be
    labels = "".join(f"""textbox = {{
	size = {{ {int(seg)} 20 }}
	position = {{ {int(i * seg)} 0 }}
	align = center|nobaseline
	using = fontsize_small
	fontsize_min = 10
	text = "[SelectLocalization({tier_test(CONF, lo, hi) if i == 0 else f'And(Not({IN_PANIC}), {tier_test(CONF, lo, hi)})'}, 'SPEC_TIER_{key.upper()}_ON', 'SPEC_TIER_{key.upper()}')]"
	tooltip = "SPEC_TIER_{key.upper()}_TT"
}}
""" for i, (key, lo, hi, *_) in enumerate(TIERS))

    def half(left, texture, vis):
        """One side's fill: the left one with vanilla's reverse hack (lit past the value, not up to it), so both
        grow out from the middle."""
        side = "left" if left else "right"
        glow = f"""icon = {{
	size = {{ 30 100% }}
	widgetanchor = {side}
	alpha = 0.7
{'	mirror = horizontal' + chr(10) if left else ''}	texture = "{BARS}/{texture}_glow.dds"
	icon = {{
		size = {{ 3 100% }}
		parentanchor = {side}
		texture = "{BARS}/{texture}_glow_line.dds"
	}}
}}
"""
        fill = f'{BARS}/{texture}.dds'
        return f"""widget = {{
	size = {{ 50% 100% }}
{'' if left else '	parentanchor = right' + chr(10)}	visible = "[{vis}]"
	scissor = yes
	progressbar = {{
		size = {{ 100% 100% }}
		progresstexture = "{CLEAR if left else fill}"
		noprogresstexture = "{fill if left else CLEAR}"
		spriteType = Corneredtiled
		spriteborder = {{ 4 4 }}
		texture_density = 2
		using = progressbar_texture_properties
{ind(SLIDE, 2)}		min = {0 if left else 50}
		max = {50 if left else 100}
		value = "[FixedPointToFloat({CONF})]"
		marker = {{
			widget = {{
				size = {{ 100% 100% }}
{ind(glow + il.chevrons(CONF_UP, CONF_DOWN, 0.25, "left" if left else "right"), 4)}			}}
		}}
	}}
}}
"""
    below, above = f"LessThan_CFixedPoint({CONF}, {fx(50)})", f"GreaterThan_CFixedPoint({CONF}, {fx(50)})"
    fills = (half(True, "progressbar_default", f"And({below}, Not({PANIC_ZONE}))") + half(True, "progressbar_bad", PANIC_ZONE)
             + half(False, "progressbar_gold", f"And({above}, Not({MANIA_ZONE}))") + half(False, "progressbar_bad", MANIA_ZONE))
    zones = "".join(f"""icon = {{
	position = {{ {x} 0 }}
	size = {{ {int(seg)} 100% }}
	texture = "{BARS}/progressbar_bad.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alpha = 0.2
}}
""" for x in (width - int(seg),))  # Mania's; the left red is the panic zone, below
    dividers = "".join(f"""icon = {{
	position = {{ {int(i * seg) - 1} 1 }}
	size = {{ 3 20 }}
	texture = "{BARS}/progressbar_center_divider.dds"
	texture_density = 2
	alpha = 0.5
}}
""" for i in (1, 2, 3, 4))
    # vanilla's active level frame round the tier confidence sits in, as the Investor Interest bars mark theirs
    active = "".join(f"""icon = {{
	position = {{ {int(i * seg)} 0 }}
	size = {{ {int(seg)} 100% }}
	visible = "[{tier_test(CONF, lo, hi) if i == 0 else f'And(Not({IN_PANIC}), {tier_test(CONF, lo, hi)})'}]"
	texture = "{BARS}/progressbar_active_level.dds"
	spriteType = Corneredstretched
	spriteborder = {{ 6 6 }}
	texture_density = 2
}}
""" for i, (key, lo, hi, *_) in enumerate(TIERS))
    return f"""widget = {{
	size = {{ {width} 44 }}
{ind(labels, 1)}	widget = {{
		size = {{ {width} 22 }}
		position = {{ 0 22 }}
		tooltip = "SPEC_CARD_BAR_TT"
		background = {{
			texture = "{BARS}/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
			using = progressbar_texture_properties
		}}
		background = {{
			texture = "{BARS}/progressbar_frame.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
			margin = {{ 3 3 }}
		}}
{ind(zones + fills + dividers + active + PANIC_ZONE_BAR, 2)}		### where a panic would begin now: the line rises with Leverage
		progressbar = {{
			size = {{ 100% 100% }}
			progresstexture = "{CLEAR}"
			noprogresstexture = "{CLEAR}"
			min = 0
			max = 100
			value = "[FixedPointToFloat({sv('spec_panic_at')})]"
			marker = {{
				widget = {{
					size = {{ 100% 100% }}
					icon = {{
						position = {{ -1 0 }}
						size = {{ 3 100% }}
						texture = "{FLAT}"
						color = {{ 0.8 0.2 0.15 1 }}
						tooltip = "SPEC_PANIC_LINE_TT"
					}}
					textbox = {{
						position = {{ -5 0 }}
						size = {{ 60 100% }}
						widgetanchor = right
						align = right|nobaseline
						using = fontsize_small
						text = "SPEC_PANIC_TAG"
						tooltip = "SPEC_PANIC_LINE_TT"
					}}
				}}
			}}
		}}
		### the middle, as vanilla's double direction bar marks it
		widget = {{
			size = {{ 3 100% }}
			parentanchor = center
			background = {{
				texture = "{BARS}/progressbar_center_divider.dds"
				spriteType = Corneredstretched
				spriteborder = {{ 0 0 }}
				texture_density = 2
				margin = {{ 0 1 }}
			}}
		}}
	}}
}}
"""


FRESH = f"LessThan_CFixedPoint({v('spec_conf', -1)}, {fx(0)})"  # before the first monthly update
PANIC_LEFT, PANIC_LEN = v("spec_panic", 0), v("spec_panic_len", 1)
CARD_X = (W - BAR_W) // 2  # the card's inner margin: the scale and the risk rows start here
LABEL_W = 104  # the card rows' labels, short of the chips at 110 (German "Pressures" ran under them)
TEXT_X = 160  # the card's text column, right of the ring


XS_MAX, XS_ALERT = 200, 10  # journal.EXCESS_MAX, BUBBLE_ALERT (journal imports this module)
XS = v("spec_heat")
XS_HOT = f"GreaterThanOrEqualTo_CFixedPoint({sv('spec_burst_now')}, {fx(XS_ALERT)})"
XS_RISK = f"{P}.Var('spec_heat').IsSet"
XS_UP = f"GreaterThanOrEqualTo_CFixedPoint({CONF}, {sv('spec_heat_from')})"


def excess_row():
    """Speculative Excess, the bubble a long boom builds: gold while it builds, red once a fall would cost
    XS_ALERT or more confidence, its state written across it."""
    bar = framed_bar(W - 2 * CARD_X - 110, 22, fill("progressbar_gold", XS_MAX, XS, f"Not({XS_HOT})")
                     + fill("progressbar_bad", XS_MAX, XS, XS_HOT) + BAR_TEXT.format(key="SPEC_XS_BAR")[:-2] + '\ttooltip = "SPEC_XS_TT"\n}\n')
    return f"""widget = {{
	size = {{ {W - 2 * CARD_X} 36 }}
	parentanchor = hcenter
	tooltip = "SPEC_XS_TT"
	divider_clean = {{}}
	textbox = {{
		text = "SPEC_XS"
		tooltip = "SPEC_XS_TT"
		size = {{ {LABEL_W} 30 }}
		parentanchor = vcenter
		align = left|nobaseline
		elide = right
	}}
	widget = {{
		position = {{ 110 0 }}
		size = {{ {W - 2 * CARD_X - 110} 22 }}
		parentanchor = vcenter
		tooltip = "SPEC_XS_TT"
{ind(bar, 2)}	}}
}}
"""


# the lines under the scale, as budget rows of chips in fixed places: the pressures (spec_pick_driver's five
# groups), what moved confidence this month, and under its first two the risks, what it could lose at once
def card_chip(key, on, icon):
    return f"""	widget = {{
		size = {{ 64 30 }}
		tooltip = "{key}_TT"
		icon = {{
			size = {{ 26 26 }}
			parentanchor = vcenter
			alpha = "[TransparentIfFalse({on})]"
			texture = "{CHIP_ICONS[icon]}"
		}}
		textbox = {{
			position = {{ 30 0 }}
			autoresize = yes
			parentanchor = vcenter
			align = left|nobaseline
			text = "{key}"
		}}
	}}
"""


# Budget rows raise their labels with a bottom margin. These compact rows
# need the label, icons and values on the same vertical centre instead.
def card_row(label, tt, chips):
    return f"""widget = {{
	size = {{ {W - 2 * CARD_X} 36 }}
	parentanchor = hcenter
	tooltip = "{tt}"
	divider_clean = {{}}
	textbox = {{
		text = "{label}"
		size = {{ {LABEL_W} 30 }}
		parentanchor = vcenter
		align = left|nobaseline
		elide = right
	}}
	flowcontainer = {{
		position = {{ 110 0 }}
		parentanchor = vcenter
		spacing = 6
{ind(chips, 1)}	}}
}}
"""


def chip_rows():
    """The card's Pressures and Risks rows, also shown in the journal entry (journal.widgets)."""
    return (card_row("SPEC_PRESSURES", "SPEC_PRESSURES_TT", "".join(card_chip(f"SPEC_CHIP_{n}", nonzero(v(f"spec_p{n}")), icon)
                                                                  for n, (_, icon, _) in enumerate(PRESSURES, 1)))
            + card_row("SPEC_RISKS", "SPEC_RISKS_TT", card_chip("SPEC_RISK_1", BAR_RISK, "crash") + card_chip("SPEC_RISK_2", SRC_RISK, "panic_risk")
                       + card_chip("SPEC_RISK_3", WAR_RISK, "war_risk") + card_chip("SPEC_RISK_4", DEFAULT_RISK, "default_risk")
                       + card_chip("SPEC_RISK_5", XS_RISK, "bubble_risk")))


def mood_card():
    # the ring fills with confidence, red in a panic or either end band, as the bar's fill is
    low = f"Or({IN_PANIC}, Or({PANIC_ZONE}, {MANIA_ZONE}))"
    gauge = "".join(f"""		round_progress_{kind} = {{
			size = {{ 112 112 }}
			parentanchor = center
			visible = "[{vis}]"
			value = "[{share(CONF)}]"
		}}
""" for kind, vis in [("default", f"Not({low})"), ("bad", low)])
    # the icon in the ring changes with the state; below the wary line without a panic it stays wary
    state_icons = "".join(f"""		icon = {{
			size = {{ 90 90 }}
			parentanchor = center
			visible = "[{vis}]"
			texture = "{icons.path(f'state_{key}')}"
		}}
""" for key, vis in [("panic", IN_PANIC), ("wary", f"And(Not({IN_PANIC}), {tier_test(CONF, 0, TIERS[1][2])})")]
        + [(key, f"And(Not({IN_PANIC}), {tier_test(CONF, lo, hi)})") for key, lo, hi in TIERS[2:]])
    fresh = f"""widget = {{
	size = {{ {W} 90 }}
	visible = "[{FRESH}]"
	using = entry_bg_fancy
	textbox = {{
		size = {{ {W - 2 * CARD_X} 70 }}
		parentanchor = center
		multiline = yes
		align = center|nobaseline
		text = "SPEC_CARD_FRESH"
		tooltip = "SPEC_CARD_FRESH_TT"
	}}
}}
"""
    risk_rows = (chip_rows()
                 + excess_row()
                 + f"""tax_exp_frame = {{
	size = {{ {W - 2 * CARD_X} {CHART_H + 16} }}
	parentanchor = hcenter
	tooltip = "SPEC_HISTORY_TT"
	blockoverride "text" {{
		text = "SPEC_HISTORY"
		size = {{ {LABEL_W} 30 }}
	}}
	blockoverride "text_2" {{}}
	widget = {{
		position = {{ 110 0 }}
		size = {{ {HISTORY * (COL_W + COL_GAP) - COL_GAP} {CHART_H} }}
		parentanchor = vcenter
{ind(history_chart(), 2)}	}}
}}
""")
    text_w = W - TEXT_X - CARD_X
    return fresh + f"""flowcontainer = {{
	direction = vertical
	visible = "[Not({FRESH})]"
	margin_bottom = 8
	using = entry_bg_fancy
	widget = {{
		size = {{ {W} 204 }}

		### gauge: the ring around an icon, as the law enactment gauge does
		widget = {{
			size = {{ 128 128 }}
			position = {{ 14 12 }}
			tooltip = "SPEC_CARD_RING_TT"
			background = {{
				using = circle_bg_simple_dark
			}}
{gauge}{state_icons}		}}

		### state, the number, and what it means
		textbox = {{
			position = {{ {TEXT_X} 16 }}
			size = {{ {text_w} 36 }}
			using = fontsize_xl
			align = left|nobaseline
			elide = right
			text = "SPEC_STATE_TITLE"
			tooltip = "SPEC_CARD_RING_TT"
		}}
		textbox = {{
			position = {{ {TEXT_X} 52 }}
			size = {{ {text_w} 26 }}
			using = fontsize_large
			align = left|nobaseline
			text = "SPEC_CONF_LINE"
			tooltip = "SPEC_CARD_CHANGE_TT"
		}}
		### up to three lines at the small size: the longer band descriptions cut off at two lines of the default size
		textbox = {{
			position = {{ {TEXT_X} 82 }}
			size = {{ {text_w} 64 }}
			multiline = yes
			using = fontsize_small
			align = left|top
			text = "SPEC_STATE_DESC"
		}}

		widget = {{
			position = {{ {CARD_X} 150 }}
			size = {{ {W - 2 * CARD_X} 44 }}
{ind(tier_scale(W - 2 * CARD_X), 3)}		}}
	}}
{ind(risk_rows, 1)}}}
"""


# -- panic -------------------------------------------------------------------------------------------------

# a value written across a bar, as vanilla writes progress on its bars
BAR_TEXT = """textbox = {{
	size = {{ 100% 100% }}
	align = center|nobaseline
	using = fontsize_small
	text = "{key}"
}}
"""


def panic_block():
    """The Banking tab's Bank Rescue row: the loans called in, the months left (or, with no panic, confidence against the
    Panic Threshold, in the confidence scale's panic zone) and the rescue button. The Speculation
    tab's confidence card names the panic and when it ends."""
    return f"""widget = {{
	size = {{ {W} 84 }}
	tooltip = "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_TT', 'SPEC_PANIC_NONE_TT')]"
	background = {{
		using = entry_bg
	}}
	widget = {{
		size = {{ 100% 100% }}
		visible = "[{IN_PANIC}]"
		background = {{
			using = fade_right_colored_red
			alpha = 0.35
		}}
	}}
	icon = {{
		size = {{ 44 44 }}
		position = {{ 14 0 }}
		parentanchor = vcenter
		texture = "{icons.path('bank_rescue')}"
	}}
	textbox = {{
		position = {{ 70 16 }}
		size = {{ 270 24 }}
		align = left|nobaseline
		elide = right
		text = "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_SUB', 'SPEC_PANIC_NONE')]"
	}}
	widget = {{
		position = {{ 70 50 }}
		size = {{ {W - 20 - BTN_W - 10 - 70} 22 }}
{ind(framed_bar(W - 20 - BTN_W - 10 - 70, 22, fill("progressbar_bad", 1, f"Max_CFixedPoint(Min_CFixedPoint(Divide_CFixedPoint({PANIC_LEFT}, {PANIC_LEN}), {fx(1)}), {fx(0)})")
                 + fill("progressbar_default", 100, CONF, f"Not({IN_PANIC})") + f"widget = {{\n\tsize = {{ 100% 100% }}\n\tvisible = \"[Not({IN_PANIC})]\"\n\talwaystransparent = yes\n{ind(PANIC_ZONE_BAR, 1)}}}\n"
                 + BAR_TEXT.format(key="SPEC_PANIC_BAR")), 2)}	}}
	button = {{
		size = {{ {BTN_W} {BTN_H} }}
		position = {{ -20 {50 + 11 - BTN_H // 2} }}
		parentanchor = right
		using = default_button_primary
		align = center|nobaseline
		enabled = "{sg('rescue', 'IsValid')}"
		onclick = "{sg('rescue', 'Execute')}"
		text = "SPEC_RESCUE"
		tooltip = "SPEC_RESCUE_TT"
	}}
}}
"""


# -- credit policy -----------------------------------------------------------------------------------------

STANCE_ICONS = [("tight", -1, "budget_set_very_low", 1), ("normal", 0, "budget_set_medium", 3),
                ("loose", 1, "budget_set_very_high", 5)]
EFFECTS = (["owed"] if leverage.ON else []) + ["debt"] + (["lax"] if cycle.ON else []) + (["lev"] if leverage.ON else [])  # Leverage last: its bar follows  # credit lent this month, and the lending rate, are the section header figure and its tooltip


def level_items(icons, current, tt="SPEC_STANCE"):
    """The budget panel's lit level bar: one button per (key, value, icon, level), each run by spec_sgui_<key>."""
    return "".join(f"""set_level_bar_item = {{
	tooltip = "{tt}_{key.upper()}_TT"
	blockoverride "size" {{
		size = {{ 56 32 }}
	}}
	blockoverride "button_texture" {{
		texture = "gfx/interface/budget/{icon}.dds"
	}}
	blockoverride "click" {{
		enabled = "{sg(key, 'IsValid')}"
		onclick = "{sg(key, 'Execute')}"
		using = budget_coins_lvl_{level}_button_sound
	}}
	blockoverride "is_selected_visibility" {{
		visible = "[EqualTo_CFixedPoint({current}, {fx(value)})]"
	}}
	blockoverride "is_clickable_alpha" {{
		alpha = "[TransparentIfFalse(Or({sg(key, 'IsValid')[1:-1]}, EqualTo_CFixedPoint({current}, {fx(value)})))]"
	}}
}}
""" for key, value, icon, level in icons)


POOL = "Country.GetInvestmentPool"


def debt_bar():
    """The investment pool as a bar: green what a panic would leave, red what it would pull out (spec_clawback, part
    of Outstanding Credit, never more than the pool), the sums written across it."""
    has = f"GreaterThan_CFixedPoint({POOL}, {fx(0)})"
    left = f"Divide_CFixedPoint(Subtract_CFixedPoint({POOL}, {sv('spec_clawback')}), Max_CFixedPoint({POOL}, {fx(1)}))"
    bar = framed_bar(BAR_W, 22, fill("progressbar_bad", 1, fx(1), has) + fill("progressbar_green", 1, left, has)
                     + BAR_TEXT.format(key="SPEC_DEBT_BAR"))
    return f"""widget = {{
	size = {{ {BAR_W} 30 }}
	parentanchor = hcenter
	tooltip = "SPEC_EFFECT_DEBT_TT"
{ind(bar, 1)}}}
"""


def lax_scale():
    """Lending Standards as five levels, Strict to Reckless: the fill green while Sound or stricter, gold when Lax, red
    when Reckless, each level named under its fifth and the current one lit."""
    lax, cuts = v("spec_lax", cycle.LAX_START), (0, *cycle.LAX_CUTS, 1)
    seg = BAR_W // len(cycle.LAX_WORDS)
    inside = lambda i: (f"And(GreaterThanOrEqualTo_CFixedPoint({lax}, {fx(cuts[i])}), LessThan_CFixedPoint({lax}, {fx(cuts[i + 1])}))"
                        if i < len(cycle.LAX_WORDS) - 1 else f"GreaterThanOrEqualTo_CFixedPoint({lax}, {fx(cuts[i])})")
    fills = (fill("progressbar_green", 1, lax, f"LessThan_CFixedPoint({lax}, {fx(cuts[3])})")
             + fill("progressbar_gold", 1, lax, inside(3)) + fill("progressbar_bad", 1, lax, inside(4)))
    dividers = "".join(f"""icon = {{
	position = {{ {seg * i - 1} 1 }}
	size = {{ 3 20 }}
	texture = "{BARS}/progressbar_center_divider.dds"
	texture_density = 2
	alpha = 0.5
}}
""" for i in range(1, len(cycle.LAX_WORDS)))
    names = "".join(f"""textbox = {{
	position = {{ {seg * i} 26 }}
	size = {{ {seg} 18 }}
	align = center|nobaseline
	using = fontsize_small
	text = "SPEC_LAXW_{i}"
	visible = "[{inside(i)}]"
}}
textbox = {{
	position = {{ {seg * i} 26 }}
	size = {{ {seg} 18 }}
	align = center|nobaseline
	using = fontsize_small
	text = "SPEC_LAXW_{i}"
	alpha = 0.4
	visible = "[Not({inside(i)})]"
}}
""" for i in range(len(cycle.LAX_WORDS)))
    active = "".join(f"""icon = {{
	position = {{ {seg * i} 0 }}
	size = {{ {seg} 100% }}
	visible = "[{inside(i)}]"
	texture = "{BARS}/progressbar_active_level.dds"
	spriteType = Corneredstretched
	spriteborder = {{ 6 6 }}
	texture_density = 2
}}
""" for i in range(len(cycle.LAX_WORDS)))
    hover = "".join(f"""widget = {{
	position = {{ {seg * i} 0 }}
	size = {{ {seg} 46 }}
	tooltip = "SPEC_LAXL_{i}_TT"
}}
""" for i in range(len(cycle.LAX_WORDS)))
    return f"""widget = {{
	size = {{ {BAR_W} 46 }}
	parentanchor = hcenter
	tooltip = "SPEC_EFFECT_LAX_TT"
{ind(framed_bar(BAR_W, 22, fills + dividers + active), 1)}{ind(names + hover, 1)}}}
"""


def policy():
    """Laid out like the budget panel's tax level: the current level and its status with a lit level bar (each level
    named in its tooltip), then budget rows for the investment pool credit feeds and what a panic would recall."""
    items = level_items(STANCE_ICONS, STANCE)
    pool = """tax_exp_frame = {
	parentanchor = hcenter
	blockoverride "text" {
		raw_text = "[concept_investment_pool]"
	}
	blockoverride "text_2" {
		raw_text = "#v @money![Country.GetInvestmentPool|D+]#! ([Country.GetInvestmentPoolChange|=+D])"
		using = investment_pool_tooltip_with_graph
	}
}
"""
    merged = "owed" in EFFECTS  # the withdrawal is drawn under Outstanding Credit, not a row of its own
    rows = "".join(f"""tax_exp_frame = {{
	parentanchor = hcenter
	tooltip = "SPEC_EFFECT_{key.upper()}_TT"
	blockoverride "text" {{
		text = "SPEC_EFFECT_{key.upper()}"
	}}
	blockoverride "text_2" {{
		text = "SPEC_EFFECT_{key.upper()}_VALUE"
	}}
}}
""" + (lax_scale() if key == "lax" else "") + (debt_bar() if key == "owed" else "")
                   for key in EFFECTS if not (merged and key == "debt"))
    return f"""tax_exp_frame_coin = {{
	parentanchor = hcenter
	tooltip = "SPEC_POLICY_TT"
	blockoverride "text_upper" {{
		text = "SPEC_POLICY_UPPER"
	}}
	blockoverride "text_lower" {{
		text = "SPEC_POLICY_LOWER"
		max_width = 245
		fontsize_min = 11
	}}
	blockoverride "text_money" {{
	}}
	blockoverride "revenue_controls" {{
		flowcontainer = {{
			position = {{ -10 0 }}
			parentanchor = right|vcenter
			direction = vertical
			flowcontainer = {{
				using = set_level_bar_background
{ind(items, 4)}			}}
		}}
	}}
}}
{pool}{rows}{leverage_scale()}{bad_debts()}"""


def framed_bar(width, height, inner):
    """Vanilla's empty track and frame, so a bar at zero still shows as a bar."""
    return f"""widget = {{
	size = {{ {width} {height} }}
	parentanchor = hcenter
	background = {{
		texture = "{BARS}/progressbar_empty.dds"
		spriteType = Corneredtiled
		spriteborder = {{ 4 4 }}
		texture_density = 2
		using = progressbar_texture_properties
	}}
	background = {{
		texture = "{BARS}/progressbar_frame.dds"
		spriteType = Corneredstretched
		spriteborder = {{ 6 6 }}
		texture_density = 2
		margin = {{ 3 3 }}
	}}
{ind(inner, 1)}}}
"""


def fill(texture, top, value, visible=""):
    """A framed bar's fill, sliding to each new value."""
    shown = f'	visible = "[{visible}]"\n' if visible else ""
    return f"""progressbar = {{
	size = {{ 100% 100% }}
{shown}	progresstexture = "{BARS}/{texture}.dds"
	noprogresstexture = "{CLEAR}"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	using = progressbar_texture_properties
{ind(SLIDE, 1)}	min = 0
	max = {top}
	value = "[FixedPointToFloat({value})]"
}}
"""


def leverage_scale():
    """Leverage on the credit ladder, in the confidence scale's style: a tier for each step, sized to its months. Tiers the
    country has no tech for are dark, the one it sits in has vanilla's active level frame, and the fill goes green, gold, red as the risk grows.
    Falling income can carry a country past its limit, so the fill runs over dark tiers too, and past the end it stays full."""
    if not leverage.ON:
        return ""
    width, lev, limit = BAR_W, sv("spec_lev"), sv("spec_credit_limit")
    edges = (0, *leverage.LADDER)
    tiers = list(zip(edges, edges[1:]))
    x = lambda months: int(width * months / edges[-1])
    unlocked = lambda months: gt(limit, months - 0.5)
    fills = (fill("progressbar_green", edges[-1], lev, f"And({gt(lev)}, Not({gt(lev, leverage.SAFE)}))")
             + fill("progressbar_gold", edges[-1], lev, f"And({gt(lev, leverage.SAFE)}, Not({gt(lev, leverage.DANGER)}))")
             + fill("progressbar_bad", edges[-1], lev, gt(lev, leverage.DANGER)))
    danger = f"""icon = {{
	position = {{ {x(leverage.DANGER)} 0 }}
	size = {{ {width - x(leverage.DANGER)} 100% }}
	texture = "{BARS}/progressbar_bad.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alpha = 0.2
}}
"""
    dark = "".join(f"""icon = {{
	position = {{ {x(lo)} 0 }}
	size = {{ {x(hi) - x(lo)} 100% }}
	visible = "[Not({unlocked(hi)})]"
	texture = "{FLAT}"
	color = {{ 0 0 0 0.6 }}
}}
""" for lo, hi in tiers)
    dividers = "".join(f"""icon = {{
	position = {{ {x(m) - 1} 1 }}
	size = {{ 3 20 }}
	texture = "{BARS}/progressbar_center_divider.dds"
	texture_density = 2
	alpha = 0.5
}}
""" for m in leverage.LADDER[:-1])
    active = "".join(f"""icon = {{
	position = {{ {x(lo)} 0 }}
	size = {{ {x(hi) - x(lo)} 100% }}
	visible = "[{tier_test(lev, lo, hi if hi < edges[-1] else 9999)}]"
	texture = "{BARS}/progressbar_active_level.dds"
	spriteType = Corneredstretched
	spriteborder = {{ 6 6 }}
	texture_density = 2
}}
""" for lo, hi in tiers)
    hover = "".join(f"""widget = {{
	position = {{ {x(lo)} 0 }}
	size = {{ {x(hi) - x(lo)} 100% }}
	tooltip = "SPEC_LEV_TIER_{i}_TT"
}}
""" for i, (lo, hi) in enumerate(tiers))
    ticks = "".join(f"""textbox = {{
	position = {{ {min(x(m) - 20, width - 40)} 24 }}
	size = {{ 40 16 }}
	align = {'right' if m == edges[-1] else 'center'}|nobaseline
	using = fontsize_small
	raw_text = "{m}"
}}
""" for m in leverage.LADDER)
    return f"""widget = {{
	size = {{ {width} 42 }}
	parentanchor = hcenter
{ind(framed_bar(width, 22, danger + dark + fills + dividers + active + hover), 1)}{ind(ticks, 1)}}}
"""


BAD_W = 310  # the Bad Debts bar; the button takes the rest of the BAR_W the Leverage bar spans
BTN_W, BTN_H = 180, 30  # both bars' buttons, in one column
BAD_TICKS = [leverage.CRUNCH_MAX * i / 4 for i in (1, 2, 3, 4)]  # points; labelled as the throughput they cost


def bad_debts():
    """Always there, so a player knows of them before the first crash: a bar of what remains of the worst crash on a
    scale to the largest possible, its value written on it (or what a panic would leave), and the bailout beside it."""
    if not leverage.ON:
        return ""
    x = lambda v: round(v / leverage.CRUNCH_MAX * BAD_W)
    ticks = "".join(f"""textbox = {{
	position = {{ {min(x(m) - 20, BAD_W - 40)} 28 }}
	size = {{ 40 16 }}
	align = {'right' if m == BAD_TICKS[-1] else 'center'}|nobaseline
	using = fontsize_small
	raw_text = "-{m * leverage.CRUNCH_THROUGHPUT * 100:g}%"
}}
""" for m in BAD_TICKS)
    dividers = "".join(f"""icon = {{
	position = {{ {x(m) - 1} 1 }}
	size = {{ 3 20 }}
	texture = "{BARS}/progressbar_center_divider.dds"
	texture_density = 2
	alpha = 0.5
}}
""" for m in BAD_TICKS[:-1])
    # behind the fill, faint: what a panic now would leave
    ghost = fill("progressbar_bad", leverage.CRUNCH_MAX, sv("spec_crunch_if"), gt(sv("spec_crunch_if")))[:-2] + "\tcolor = { 1 1 1 0.3 }\n}\n"
    bar = framed_bar(BAD_W, 22, ghost + fill("progressbar_bad", leverage.CRUNCH_MAX, sv("spec_crunch_bite_sv"), gt(sv("spec_crunch_bite_sv"))) + dividers)
    return f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	spacing = 6
	tooltip = "[SelectLocalization({P}.Var('spec_crunch').IsSet, 'SPEC_EFFECT_BAD_TT', 'SPEC_EFFECT_BAD_NONE_TT')]"
	tax_exp_frame = {{
		parentanchor = hcenter
		blockoverride "text" {{
			text = "SPEC_EFFECT_BAD"
		}}
		blockoverride "text_2" {{
		}}
		textbox = {{
			autoresize = yes
			position = {{ {(W - BAR_W) // 2 + BAD_W - (W - 530) // 2 - 530} 0 }}  # right edge over the bar's (bar row BAR_W, this frame 530)
			parentanchor = right|vcenter
			margin_bottom = 6
			text = "SPEC_EFFECT_BAD_VALUE"
		}}
	}}
	widget = {{
		size = {{ {BAR_W} 46 }}
		parentanchor = hcenter
		widget = {{
			size = {{ {BAD_W} 46 }}
{ind(bar + ticks, 3)}		}}
		button = {{
			size = {{ {BTN_W} {BTN_H} }}
			position = {{ 0 {11 - BTN_H // 2} }}
			parentanchor = right
			using = default_button_primary
			align = center|nobaseline
			enabled = "{sg('bailout', 'IsValid')}"
			onclick = "{sg('bailout', 'Execute')}"
			text = "SPEC_BAILOUT"
			tooltip = "SPEC_BAILOUT_TT"
		}}
	}}
}}
"""


# -- goods board -------------------------------------------------------------------------------------------

def good_var(name):
    return f"{P}.Var(Concatenate('{name}_', Goods.GetKey)).GetValueWithDefault({fx(0)})"


HYPE = good_var("spec_hype")
WORD = good_var("spec_word")    # the interest word, 1 Fleeing to 6 Feverish: words hold within generate.WORD_BUFFER of a cut
RISK = good_var("spec_risk")    # confidence a collapse of this boom would cost
RISK_SHOWN = levers.RESTRAIN_RISK  # smaller losses get no warning
WARNING = f"{ICONS}/warning.dds"
# the price trend interest follows: fast minus slow average of the price against base
TREND = f"Subtract_CFixedPoint({good_var('spec_fast')}, {good_var('spec_slow')})"
NEAR_PEAK = 0.85                # interest this close to its boom's peak is still at the top
MOVE = good_var("spec_ui_move")  # interest_board.ui_effect's monthly move: 1 rose, -1 fell, 0 neither
LEANING = [6, 5, 4, 3, 2, 1]    # spec_word lists shown as rows, hottest first, Calm (3) in the middle
WORDS = {6: "feverish", 5: "eager", 4: "keen", 3: "calm", 2: "doubtful", 1: "fleeing"}
CATEGORIES = ["staple", "industrial", "luxury", "military"]  # vanilla's goods filters
CAT = "spec_il_cat"  # the category picked in the Speculation list (none: all)
CAT_TT = {"staple": "STAPLE_FILTER", "industrial": "INDUSTRIAL_GOODS_FILTER", "luxury": "LUXURY_GOODS_FILTER",
          "military": "MILITARY_GOODS_FILTER"}


def cat_shown(c):
    return f"Or(Not(GetVariableSystem.Exists('{CAT}')), GetVariableSystem.HasValue('{CAT}', '{c}'))"


def cat_filters():
    """vanilla's four category buttons (goods_filters), but on our variable: the vanilla ones act on MarketPanel,
    which the Finance window has none of. As vanilla: all lit at first, a click keeps only that one, again shows all."""
    on = lambda c: f"GetVariableSystem.HasValue('{CAT}', '{c}')"
    out = ""
    for c in CATEGORIES:
        btn = lambda shown, click, tex: f"""	goods_filter_button = {{
		visible = "[{shown}]"
		onclick = "[{click}]"
		tooltip = "{CAT_TT[c]}"
		using = tooltip_ne
		using = market_filter_{c}_button_sound
		blockoverride "icon" {{
			texture = "gfx/interface/market_view/{tex}.dds"
		}}
	}}
"""
        out += f"""widget = {{
	size = {{ 75 75 }}
	icon = {{
		visible = "[{cat_shown(c)}]"
		size = {{ 100% 100% }}
		texture = "gfx/interface/backgrounds/round_frame_dec.dds"
		using = default_fade_in_out
	}}
{btn(f"Not({cat_shown(c)})", f"GetVariableSystem.Set('{CAT}', '{c}')", f"filter_{c}_goods")}{btn(f"Not(GetVariableSystem.Exists('{CAT}'))", f"GetVariableSystem.Set('{CAT}', '{c}')", f"filter_{c}_goods_selected")}{btn(on(c), f"GetVariableSystem.Clear('{CAT}')", f"filter_{c}_goods_selected")}}}
"""
    return f"""flowcontainer = {{
	parentanchor = center
{ind(out, 1)}}}
"""


def any_of(tests):
    out = tests[0]
    for t in tests[1:]:
        out = f"Or({out}, {t})"
    return out


def goods_filters(label, row):
    """Vanilla's filter block (market_panel.gui ~391-446) under a collapsible Filters header: one dark area, the labels
    in a column, one divider, the filter rows in a column. label and row are the second row, 64 high, under the goods
    categories."""
    width = W - 95 - 2 * 10  # the rest of the row: the label, two spacings and the divider
    labels = "".join(f"""	textbox = {{
		text = "{text}"
		multiline = yes
		size = {{ 95 {height} }}
		align = right|nobaseline
		margin_right = 10
		margin_left = 10
		using = elide_fontsize_min
	}}
""" for text, height in (("GOODS_CATEGORY", 75), (label, 64)))
    body = f"""flowcontainer = {{
	minimumsize = {{ {W} -1 }}
	parentanchor = hcenter
	margin_top = 5
	margin_bottom = 10
	spacing = 10
	background = {{
		using = dark_area
	}}
	flowcontainer = {{
		direction = vertical
{labels}	}}
	vertical_divider = {{}}
	flowcontainer = {{
		direction = vertical
		widget = {{
			size = {{ {width} 75 }}
{ind(cat_filters(), 3)}		}}
		widget = {{
			size = {{ {width} 64 }}
{ind(row, 3)}		}}
	}}
}}
"""
    # Finance has no MarketPanel context; its filters use our own selection.
    return section("FILTERS", "spec_hide_filters", body, right="SPEC_CURRENT_GOODS_FILTERS")


def goods_board(k):
    import interest_list  # imports this module
    return section("CHARTS", "spec_hide_charts_interest", __import__("charts").interest_chart()) + interest_list.board(k)


def level_effects():
    """Each interest level's effects, one line each as vanilla modifier tooltips list them, by level name."""
    pct = {WORDS[w]: p for w, p in companies.INTEREST_THROUGHPUT.items()}
    tp = lambda w: f"Producers' [concept_throughput]: {'#P +' if pct[w] > 0 else '#N '}{pct[w]}%#!"
    lift = ("\\n[concept_spec_market_confidence] #P goes up#! every month (more if it is a big part of our trade, "
            "none during a [concept_spec_financial_panic])")
    end = lambda name: f"\\nWhen it ends: [concept_spec_{name.lower()}]"
    effects = {
        "feverish": tp("feverish") + lift + end("Collapse"),
        "eager": tp("eager") + lift + end("Bust"),
        "keen": tp("keen") + end("Correction"),
        "calm": "Nothing happens at this level",
        "doubtful": tp("doubtful") + "\\nAfter a boom ends, the good stays here or lower for a while to recover",
        "fleeing": tp("fleeing") + "\\nIf a #v Feverish#! boom drops this low, it ends in a [concept_spec_collapse]",
    }
    return effects


def band_loc(k):
    """The lever column's label, and each interest word's tooltip."""
    effects = level_effects()
    selected = "'ALL_GOODS'"
    for category in reversed(CATEGORIES):
        selected = (f"SelectLocalization(GetVariableSystem.HasValue('{CAT}', '{category}'), "
                    f"'{category.upper()}_FILTER_NAME', {selected})")
    out = (f' SPEC_CURRENT_GOODS_FILTERS: "[{selected}]"\n'
           " SPEC_COL_LEVER: \"Intervention\"\n"
           " SPEC_COL_LEVER_TT: \"#header Market Interventions#!\\n$TOOLTIP_DELIMITER$\\n#italic Step in to cool a good down or heat it up.#!\\n\\n"
           "#v Restrain Speculation#! keeps interest #v Calm#!. Producers #N lose#! [concept_throughput] and pay a levy\\n"
           "#v Encourage Investment#! keeps interest at least #v Keen#!. Producers #P gain#! $concept_throughput$ and the state pays\\n"
           "$TOOLTIP_DELIMITER$\\n#weak Each one costs [concept_authority] every month until lifted, more for staples and widely traded goods#!\"\n")
    word_of = {n: w for w, n in WORDS.items()}
    for name, desc in effects.items():
        key = f"SPEC_SEP_{name.upper()}"
        share = f"\\nShare of Our Trade: #v [{market_visual.share(word_of[name])}|%0]#!"
        out += f" {key}_TT: \"#header @spec_interest_{name}! {name.capitalize()} [concept_spec_investor_interest]#!{share}\\n$TOOLTIP_DELIMITER$\\n#italic How keen investors are on this good.#!\\n\\n{desc}\"\n"
    import interest_board
    import interest_list
    return out + interest_board.loc(k) + interest_list.loc(k) + __import__('exposure').loc() + __import__('charts').loc(k)


# -- what moved confidence ---------------------------------------------------------------------------------

DRIVERS = [("boom", "spec_c_boom"), ("crash", "spec_c_crash"), ("restrain", "spec_c_restrain"), ("foreign", "spec_c_foreign"), ("world", "spec_c_world"),
           ("turmoil", "spec_c_turmoil"), ("debt", "spec_c_debt"), ("mood", "spec_c_mood"), ("drift", "spec_c_recover"), ("tight", "spec_c_tight"), ("rescue", "spec_c_rescue"), ("warend", "spec_c_warend"), ("burst", "spec_c_burst"),
           ("caution", "spec_c_caution"), ("limit", "spec_c_limit"), ("growth", "spec_c_growth"), ("business", "spec_c_business"), ("rival", "spec_c_rival")] + ([("drop", "spec_c_drop")] if leverage.ON else [])
# the card's pressure chips: the mod's driver icons, vanilla ones for the rest
_VANILLA = "gfx/interface/icons"
DRIVER_ICONS = {k: icons.path(f"driver_{k}") for k in ("boom", "crash", "foreign", "turmoil", "tight")} | {
    "world": f"{ICONS}/world_market.dds", "debt": f"{_VANILLA}/lens_toolbar_icons/take_on_debt.dds",
    "mood": f"{_VANILLA}/event_icons/event_newspaper.dds", "rescue": f"{ICONS}/government_building_icon.dds",
    "caution": f"{_VANILLA}/event_icons/event_scales.dds",
    "limit": f"{ICONS}/map_list_lock.dds", "restrain": icons.path("lever_restrain")}
# the card's chips: the pressures by their main driver's icon, the risks by icons of their own, no two alike
CHIP_ICONS = DRIVER_ICONS | {"panic_risk": f"{_VANILLA}/lens_toolbar_icons/unused/foreign_investment_rights_break.dds",
                             "war_risk": f"{_VANILLA}/notification_icons/diplomatic_play.dds",
                             "default_risk": f"{_VANILLA}/alert_icons/bankruptcy.dds", "bubble_risk": icons.path("excess_alert")}


# the card's fixed pressure chips: every driver in one of five groups, each chip the sum of its group, so the five add
# up to the month's change and never trade places
PRESSURES = [("goods", "boom", ("boom", "crash", "restrain", "burst", "growth")), ("abroad", "foreign", ("foreign", "world", "rival")),
             ("state", "turmoil", ("turmoil", "debt", "caution", "rescue", "warend")), ("mood", "mood", ("mood", "business", "drift")),
             ("credit", "tight", ("tight", "limit") + (("drop",) if leverage.ON else ()))]
assert sorted(k for *_, ks in PRESSURES for k in ks) == sorted(k for k, _ in DRIVERS)


def pick_driver():
    """Scripted effect: spec_p1 to spec_p5 = the month's change from each PRESSURES group. Run monthly for players
    and market owners, and after each one-off jump."""
    var = dict(DRIVERS)
    out = "spec_pick_driver = {\n"
    for n, (_, _, keys) in enumerate(PRESSURES, 1):
        out += f"\tset_variable = {{ name = spec_p{n} value = 0 }}\n" + "".join(
            f"\tif = {{\n\t\tlimit = {{ has_variable = {var[k]} }}\n\t\tchange_variable = {{ name = spec_p{n} add = var:{var[k]} }}\n\t}}\n"
            for k in keys)
    return out + "}\n"


def nonzero(val, at=0.1):
    """Shown to one decimal, which truncates, so changes under 0.1 are left out."""
    return f"Or(GreaterThanOrEqualTo_CFixedPoint({val}, {fx(at)}), Not(GreaterThan_CFixedPoint({val}, {fx(-at)})))"


ITEMS = {"boom", "crash", "foreign", "turmoil"}  # drivers whose chip tooltip lists what made them up


def good_sv(name):
    """A per-good script value for the good in context, as good_var reads a variable."""
    return f"{P}.ScriptValue(Concatenate('{name}_', Goods.GetKey))"


def cond_row(mult):
    """A multiplier from Market Conditions: its calculator on the number, the concept on the words."""
    return f"#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WHY_COND #v x[{mult}|2]#!#!#! how hot the market is ([concept_spec_market_conditions])"


def why_lines(var, val, k):
    """A boom's cost if it ended now, in vanilla's calculator form (BASE_VALUE_FOR_CALCULATOR): peak interest above 1,
    then each multiplier "from" its cause, as generate.spec_risk_next_<g> makes it: its ending's rate (UNWINDS), its
    weight, spec_crash_scale, capped at CONF_CRASH_MAX. var(n) and val(n) read spec_<n>_<good> as a variable and a
    script value."""
    sev = var("spec_sev")
    tier = (f"SelectLocalization(EqualTo_CFixedPoint({sev}, {fx(3)}), 'SPEC_WHY_END_3', "
            f"SelectLocalization(EqualTo_CFixedPoint({sev}, {fx(2)}), 'SPEC_WHY_END_2', 'SPEC_WHY_END_1'))")
    share = f"Divide_CFixedPoint({val('spec_mv')}, Max_CFixedPoint({v('spec_mv_total', 1)}, {fx(1)}))"
    capped = f"GreaterThan_CFixedPoint(Multiply_CFixedPoint({val('spec_risk_raw')}, {sv('spec_crash_scale')}), {fx(k['CONF_CRASH_MAX'])})"
    falling = f"LessThan_CFixedPoint({var('spec_hype')}, {var('spec_hprev')})"
    peak = var("spec_peak")
    return (f"#v [Subtract_CFixedPoint({peak}, {fx(1)})|1]#! base, from how high [concept_spec_investor_interest] got (#v [{peak}|1]#!)\\n"
            f"[{tier}]\\n"
            f"#v x[{val('spec_weight')}|%0]#! how much of our trade it is (#v [{share}|%1]#! of our [concept_market], full effect at #v {k['EXPOSURE_FULL']:.0%}#!)\\n"
            + cond_row(sv('spec_crash_scale')) +
            f"[AddLocalizationIf({capped}, 'SPEC_WHY_CAP')][AddLocalizationIf({falling}, 'SPEC_WHY_FALLING')]")


def risk_why(g, k):
    """A Booms at Risk good's nested tooltip, which has only the country in context, so one per good."""
    return (f' SPEC_RISK_WHY_{g.upper()}: "#header [GetGoods(\'{g}\').GetName] Boom#!\\n'
            f"If it ended now: #N -[{v(f'spec_risk_{g}')}|1]#! [concept_spec_market_confidence]\\n$TOOLTIP_DELIMITER$\\n#b Why so much#!\\n"
            + why_lines(lambda n: v(f"{n}_{g}"), lambda n: sv(f"{n}_{g}"), k) + '"\n')


def why_cond(k):
    """Market Conditions, generate.spec_crash_scale's factors; the last three only when they change it, as vanilla
    leaves out what adds nothing."""
    conf =f"Divide_CFixedPoint({CONF}, {fx(k['CONF_START'])})"
    rows = [("DEPTH", "spec_depth", "Financial Districts"), ("STEADY", "spec_steady", "Manor Houses"),
            ("FIN", "spec_fin_risk", "finance technologies")]
    out = (f' SPEC_WHY_COND: "#header [concept_spec_market_conditions]: x[{sv("spec_crash_scale")}|2]#!\\n$TOOLTIP_DELIMITER$\\n'
           f"#italic The hotter the market, the more it hurts when a boom ends.#!\\n\\n"
           f"#v x[{conf}|2]#! because [concept_spec_market_confidence] is #v [{CONF}|0]#!"
           + "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({sv(n)}, {fx(1)})), 'SPEC_WHY_COND_{key}')]" for key, n, _ in rows)
           + f"\\n$TOOLTIP_DELIMITER$\\n#weak No effect at #v {k['CONF_START']:g}#! $concept_spec_market_confidence$. The higher it goes, the bigger the hit from a [concept_spec_boom_end]#!\"\n")
    out += "".join(f' SPEC_WHY_COND_{key}: "\\n#v x[{sv(n)}|2]#! from {name}"\n' for key, n, name in rows)
    # how hard interest follows the price trend, generate.spec_hype_mult and spec_hype_mult_down; Loose credit (a
    # Credit Policy above 1) speeds rising prices only
    rows = [("TECH", "spec_tech_hype", "Joint-Stock Companies"), ("DEPTH", "spec_depth", "Financial Districts"),
            ("BAND", "spec_band_gain", "[concept_spec_market_confidence] (rising prices only)")]
    if __import__("centres").ON:  # centres.HYPE_REF: the Exchange multiplies spec_hype_mult, not spec_hype_mult_down
        rows.append(("EXCH", "spec_exch_hype", "[concept_spec_exchange] (rising prices only)"))
    loose = f"GreaterThan_CFixedPoint({sv('spec_stance_hype')}, {fx(1)})"
    out += (f' SPEC_WHY_SPEED: "#header Investor Reaction#!\\n$TOOLTIP_DELIMITER$\\n#italic How fast investors chase a change in price.#!\\n\\n'
            f'When prices rise: #v x[{sv("spec_hype_mult")}|2]#!\\n'
            f'When prices fall: #v x[{sv("spec_hype_mult_down")}|2]#!\\n$TOOLTIP_DELIMITER$\\n#b Why#!\\n'
            f"#v x[{sv('spec_law_mult')}|2]#! from Economic System\\n"
            f"#v x[{sv('spec_stance_hype')}|2]#! from [concept_spec_credit_policy][AddLocalizationIf({loose}, 'SPEC_WHY_SPEED_LOOSE')]"
            + "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({sv(n)}, {fx(1)})), 'SPEC_WHY_SPEED_{key}')]" for key, n, _ in rows)
            + "\\n$TOOLTIP_DELIMITER$\\n#weak The higher it is, the faster [concept_spec_investor_interest] follows prices up or down#!\"\n"
            ' SPEC_WHY_SPEED_LOOSE: " (rising prices only)"\n')
    return out + "".join(f' SPEC_WHY_SPEED_{key}: "\\n#v x[{sv(n)}|2]#! from {name}"\n' for key, n, name in rows)


def not1(name):
    """A script value that changes something: rows that multiply by 1 are left out, as vanilla leaves them."""
    return f"Not(EqualTo_CFixedPoint({sv(name)}, {fx(1)}))"


def ratio(scaled, raw):
    """What a month's sum was multiplied by, read back from the two, since the multiplier moves with confidence after."""
    return f"Divide_CFixedPoint({v(scaled)}, Min_CFixedPoint({v(raw)}, {fx(-0.001)}))"


def business_lines():
    """economy.BUSINESS in words, so the tooltip cannot drift from what the game applies."""
    names = {10: "Loyal", 5: "Happy", -5: "Unhappy", -10: "Angry"}
    return "\\n".join(f"{names[at]} (#v {at}#! or {'more' if at > 0 else 'less'}): {'#P +' if val > 0 else '#N '}{val:g}#! per month"
                       for _, at, val in sorted(economy.BUSINESS, key=lambda row: -row[1]))


def war_why(n, k):
    """A war's calculator, in vanilla's breakdown form: what each of diplomacy.WAR_ROWS adds this month, and the reading
    behind it. Rows that add nothing are left out."""
    out = (f' SPEC_WAR_WHY_{n}: "#header [concept_war] with [{P}.Var(\'spec_war{n}\').GetCountry.GetName]#!\\n'
           f"[concept_spec_market_confidence] a month: [{v(f'spec_war{n}_c')}|+=2]\\n$TOOLTIP_DELIMITER$\\n#N -{k['WAR_BASE']:.2f}#! just for being at war"
           + "".join(f"[AddLocalizationIf({nonzero(v(f'spec_war{n}_{key}'), 0.01)}, 'SPEC_WAR_ROW_{n}_{key.upper()}')]" for key in diplomacy.WAR_ROWS)
           + f"\\n$TOOLTIP_DELIMITER$\\n#weak One war can move it #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! a month. The first #v 12#! months, and a [concept_gdp] drop of up to #v 10%#!, cost nothing extra#!\"\n")
    return out + "".join(f' SPEC_WAR_ROW_{n}_{key.upper()}: "\\n[{v(f"spec_war{n}_{key}")}|+=2] from {row[0].format(r=v(f"spec_war{n}_{key}_r"), t=v(f"spec_war{n}_total"))}"\n'
                         for key, row in diplomacy.WAR_ROWS.items())


def item_loc(goods, k):
    """The lists under the chip tooltips' rows, indented as vanilla's breakdowns are, and the Booms at Risk tooltip's
    goods. A good's part of the month's boom or collapse is its share of the unscaled sum (spec_cb_, spec_cc_ against
    spec_boom_raw, spec_crash_raw) times the scaled one, so the list adds up to the row. The divisors are kept off 0:
    a save from before these were stored reads them as 0."""
    gv = lambda g: f"GetGoods('{g}').GetName"
    boom = lambda g: f"Multiply_CFixedPoint({v(f'spec_cb_{g}')}, Divide_CFixedPoint({v('spec_c_boom')}, Max_CFixedPoint({v('spec_boom_raw')}, {fx(0.001)})))"
    crash = lambda g: f"Multiply_CFixedPoint({fx(-1)}, Multiply_CFixedPoint({v(f'spec_cc_{g}')}, Divide_CFixedPoint({v('spec_c_crash')}, Min_CFixedPoint({v('spec_crash_raw')}, {fx(-0.001)}))))"
    hot = lambda g: f"And(GreaterThanOrEqualTo_CFixedPoint({v(f'spec_hype_{g}')}, {fx(k['HOT_HYPE'])}), GreaterThanOrEqualTo_CFixedPoint({boom(g)}, {fx(0.01)}))"
    lists = {
        "BOOM": [(hot(g), f"[{gv(g)}]: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_BOOM_WHY_{g.upper()} [{boom(g)}|+=2]#!#!") for g in goods],
        "CRASH": [(f"{P}.Var('spec_cc_{g}').IsSet", f"[{gv(g)}]: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_CRASH_WHY_{g.upper()} [{crash(g)}|+=2]#!#!") for g in goods],
        # a restrained boom cannot end, so it is left out (SPEC_RISK_HELD_LINE counts it); each name explains its number
        "RISK": [(f"And(Not({P}.Var('spec_restrain_{g}').IsSet), GreaterThanOrEqualTo_CFixedPoint({v(f'spec_risk_{g}')}, {fx(0.5)}))",
                  f"[{gv(g)}]: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_RISK_WHY_{g.upper()} #N -[{v(f'spec_risk_{g}')}|1]#!#!#!")
                 for g in goods],
    }
    out = ""
    for key, items in lists.items():
        out += f' SPEC_ITEMS_{key}: "' + "".join(f"[AddLocalizationIf({c}, 'SPEC_ITEM_{key}_{g.upper()}')]"
                                                 for g, (c, _) in zip(goods, items)) + '"\n'
        out += "".join(f' SPEC_ITEM_{key}_{g.upper()}: "\\n{t}"\n' for g, (_, t) in zip(goods, items))
    out += "".join(risk_why(g, k) for g in goods) + why_cond(k)
    # the same goods' parts of this month's booms and collapses, each by its own calculator
    mult = f"Divide_CFixedPoint({v('spec_c_boom')}, Max_CFixedPoint({v('spec_boom_raw')}, {fx(0.001)}))"
    out += "".join(f' SPEC_BOOM_WHY_{g.upper()}: "#header [{gv(g)}] Boom: [{boom(g)}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n#P +{k["CONF_PER_HOT"]:g}#! for a boom\\n'
                   f'#v x[{sv(f"spec_weight_{g}")}|%0]#! how much of our trade it is\\n'
                   f'#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_DRIVER_BOOM_TT #v x[{mult}|2]#!#!#! adjusted for all booms this month"\n'
                   f' SPEC_CRASH_WHY_{g.upper()}: "#header [{gv(g)}] Boom Ending: [{crash(g)}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n'
                   f'[Multiply_CFixedPoint({fx(-1)}, {v(f"spec_cc_{g}")})|+=2] from how big the boom was\\n'
                   f'{cond_row(ratio("spec_c_crash", "spec_crash_raw"))}"\n' for g in goods)
    for key in ("BOOM", "CRASH"):
        out = out.replace(f' SPEC_ITEMS_{key}: "', f' SPEC_ITEMS_{key}: "#indent_newline:3 ', 1).replace(
            f"'SPEC_ITEM_{key}_{goods[-1].upper()}')]\"\n", f"'SPEC_ITEM_{key}_{goods[-1].upper()}')]#!\"\n", 1)
    # every country whose panic reached us this month (the largest hit is the one that counts)
    src = lambda n: f"{P}.Var('spec_fs{n}')"
    out += (' SPEC_ITEMS_FOREIGN: "#indent_newline:3 ' + "".join(f"[AddLocalizationIf({src(n)}.IsSet, 'SPEC_ITEM_FS_{n}')]"
                                                             for n in range(1, k['SOURCES'] + 1)) + '#!"\n')
    out += "".join(f' SPEC_ITEM_FS_{n}: "\\nPanic in #v [{src(n)}.GetCountry.GetName]#!"\n' for n in range(1, k['SOURCES'] + 1))
    # each war by the enemy's war leader, then plays, default and revolution
    war = lambda n: f"{P}.Var('spec_war{n}')"
    kinds = [("warcap", "Limit on All Wars"), ("play", "[concept_diplomatic_play]"), ("broke", "Treasury Running Out"), ("default", "[concept_default]"), ("revolution", "[concept_revolution]")]
    out += (' SPEC_ITEMS_TURMOIL: "#indent_newline:3 ' + "".join(f"[AddLocalizationIf({war(n)}.IsSet, 'SPEC_ITEM_WAR_{n}')]" for n in (1, 2, 3))
            + f"[AddLocalizationIf({P}.Var('spec_war_more').IsSet, 'SPEC_ITEM_WAR_MORE')]"
            + "".join(f"[AddLocalizationIf({P}.Var('spec_tm_{t}').IsSet, 'SPEC_ITEM_TM_{t.upper()}')]" for t, _ in kinds) + '#!"\n')
    out += "".join(f' SPEC_ITEM_WAR_{n}: "\\n[concept_war] with #v [{war(n)}.GetCountry.GetName]#!: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WAR_WHY_{n} [{v(f"spec_war{n}_c")}|+=1]#!#!"\n' for n in (1, 2, 3))
    out += "".join(war_why(n, k) for n in diplomacy.WAR_SLOTS)
    out += (f' SPEC_ITEM_WAR_MORE: "\\nOther Wars: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WAR_MORE_TT [{v("spec_war_more")}|+=1]#!#!"\n'
            ' SPEC_WAR_MORE_TT: "#header Other Wars#!\\n$TOOLTIP_DELIMITER$\\nEvery war beyond the first three, added together"\n')
    out += "".join(f' SPEC_ITEM_TM_{t.upper()}: "\\n{name}: #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_TM_{t.upper()}_TT [{v(f"spec_tm_{t}")}|+=1]#!#!"\n' for t, name in kinds)
    head = lambda t, name: f' SPEC_TM_{t.upper()}_TT: "#header {name}: [{v(f"spec_tm_{t}")}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n'
    names = dict(kinds)
    out += (head("warcap", names["warcap"]) + f'[{v("spec_war_sum")}|+=2] from all our wars together\\nCapped at #N {k["WAR_ALL_MIN"]:g}#! to #P +{k["WAR_ALL_MAX"]:g}#! a month"\n'
            + head("play", names["play"]) + f'#N -{k["PLAY_TURMOIL"]:g}#! for being in a [concept_diplomatic_play]\\n$TOOLTIP_DELIMITER$\\n#weak Counts once, however many plays, until a [concept_war] starts#!"\n'
            + head("broke", names["broke"]) + f'#v [{sv("spec_broke_weeks")}|0]#! weeks until [concept_bankruptcy] if we keep losing money like this\\n$TOOLTIP_DELIMITER$\\n#weak Starts #v {k["BROKE_WEEKS"]}#! weeks before $concept_bankruptcy$ and grows to #N -{k["BROKE_COST"]:g}#! as the [concept_treasury] runs dry#!"\n'
            + head("default", names["default"]) + f'#N -{k["DEFAULT_COST"]}#! for being in [concept_default]"\n'
            + head("revolution", names["revolution"]) + '#N -2#! for a [concept_revolution]"\n')
    return out


def driver_rows():
    """Loc for a vanilla breakdown tooltip on the confidence line: the monthly drivers, the one-off jumps (bank
    support, the reset when a panic ends) and the 0 to 100 limit, so the rows add up to the change shown. No
    driver icons: custom textures cannot go inline in text."""
    any_row = nonzero(v(DRIVERS[-1][1]))
    for _, var in reversed(DRIVERS[:-1]):
        any_row = f"Or({nonzero(v(var))}, {any_row})"
    rows = "".join(f"[AddLocalizationIf({nonzero(v(var))}, 'SPEC_CARD_ROW_{key.upper()}')]" for key, var in DRIVERS)
    out = f' SPEC_CARD_ROWS: "[AddLocalizationIf({any_row}, \'SPEC_CARD_ROWS_LIST\')]"\n'
    out += f' SPEC_CARD_ROWS_LIST: "\\n$TOOLTIP_DELIMITER${rows}"\n'
    # the gauge tooltip's rows, in vanilla's breakdown form "+1 from Literacy" (CULTURAL_FERVOR_FROM_*)
    out += ' SPEC_GAUGE_ROWS: "' + "".join(f"[AddLocalizationIf({nonzero(v(var))}, 'SPEC_GAUGE_ROW_{key.upper()}')]" for key, var in DRIVERS) + '"\n'
    for key, var in DRIVERS:
        name = f"$SPEC_DRIVER_{key.upper()}$"
        # the calculator sits on the number, as the Booms at Risk rows do
        num = lambda digits: f"#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_DRIVER_{key.upper()}_TT [{v(var)}|+={digits}]#!#!"
        out += f' SPEC_CARD_ROW_{key.upper()}: "\\n{name}: {num(1)}"\n'
        out += f' SPEC_GAUGE_ROW_{key.upper()}: "\\n{num(1)} from {name}"\n'
        out += f' SPEC_CHIP_ROW_{key.upper()}: "\\n{name}: {num(2)}"\n'
    return out


# -- the tab -----------------------------------------------------------------------------------------------

def off_notice():
    return f"""widget = {{
	size = {{ {W} 90 }}
	visible = "[Not({ACTIVE})]"
	background = {{
		using = entry_bg_simple
	}}
	textbox = {{
		size = {{ {W - 40} 70 }}
		parentanchor = center
		multiline = yes
		align = center|nobaseline
		text = "SPEC_OFF"
	}}
}}
"""



FIN, FIN_TAB = "spec_finance", "spec_finance_tab"  # GetVariableSystem: the window is open; its tab (unset: the first)


def cycle_clicks(k, je=True):
    """The side bar button's onclicks, as vanilla's: open on the first tab, then each click the next, wrapping.
    The next tab goes into a scratch variable first, so setting the tab cannot satisfy the following test."""
    names = [n for n, _ in tabs(k)]
    nxt = "spec_finance_next"
    first = f"Or(Not(GetVariableSystem.Exists('{FIN_TAB}')), GetVariableSystem.HasValue('{FIN_TAB}', '{names[0]}'))"
    steps = [f"GetVariableSystem.Clear('{nxt}')"]
    for i, n in enumerate(names[1:], 1):
        cond = first if i == 1 else f"GetVariableSystem.HasValue('{FIN_TAB}', '{names[i - 1]}')"
        # from a closed window the first tab, not the second
        cond = f"And(GetVariableSystem.Exists('{FIN}'), {cond})"
        steps.append(f"GetVariableSystem.SetIf('{nxt}', '{n}', {cond})")
    steps.append(f"GetVariableSystem.SetIf('{nxt}', '{names[0]}', Not(GetVariableSystem.Exists('{nxt}')))")
    steps += [f"GetVariableSystem.SetIf('{FIN_TAB}', '{n}', GetVariableSystem.HasValue('{nxt}', '{n}'))" for n in names]
    steps += [f"GetVariableSystem.Clear('{nxt}')", f"GetVariableSystem.Set('{FIN}', 'open')"] + ([JE_PANEL[1:-1]] if je else [])
    return "".join(f'onclick = "[{s}]"\n' for s in steps)
PICK = "spec_pick_slot"  # centres.py's "choose a speciality" mode: it ends whenever the window opens or closes
# closing, as the back and close buttons do; ponytail: two onclicks through the one onclick = "..." its users write
# Financial Markets' panel, opened under the window: the journal map mode follows the open entry's panel, and nothing
# else selects it (SetTempMapModeByKey painted the map grey, 2026-11-16). Last in any onclick list: it replaces the
# panel the click came from
JE_PANEL = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"
JE_CONTEXT = "datacontext = \"[GetPlayer.MakeScope.Var('spec_je').GetJournalEntry]\""  # on the widget whose onclick has JE_PANEL
# only then: an empty panel, opened before the entry first saved itself, checked its triggers on no country every
# frame (error.log, 2026-11-16)
JE_OK = "GetPlayer.MakeScope.Var('spec_je').GetJournalEntry.IsValid"
JE_PANEL_OPEN = "Or(InformationPanelBar.IsPanelOpen('journal_entry'), InformationPanelBar.IsPanelOpen('journal_entry_panel'))"
CLOSE = (f"[GetVariableSystem.Clear('{FIN}')]\"\n\t\t\t\tonclick = \"[GetVariableSystem.Clear('{PICK}')]\"\n"
         "\t\t\t\tonclick = \"[InformationPanelBar.ClosePanel]")


def navigation_guard():
    """A sibling of Finance, so it keeps updating while Finance is hidden.

    Top-bar figures, map clicks and other mods can open vanilla panels without
    running our sidebar handlers. Yield to that navigation and disarm any slot.
    """
    return f"""type spec_finance_navigation_guard = widget {{
	name = "spec_finance_navigation_guard"
	size = {{ 1 1 }}
	alwaystransparent = yes
	state = {{
		name = spec_finance_yield_to_panel
		trigger_when = "[And3(GetVariableSystem.Exists('{FIN}'), InformationPanelBar.IsAnyPanelOpen, Not({JE_PANEL_OPEN}))]"
		on_start = "[GetVariableSystem.Clear('{FIN}')]"
		on_start = "[GetVariableSystem.Clear('{PICK}')]"
		duration = 0
	}}
}}
"""


def tabs(k):
    """The Finance window's tabs, in order: (name, body). The first is the one it opens on."""
    exch, charts = __import__("centres"), __import__("charts")  # these import this module
    card = f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	margin_bottom = {GAP_END}
	spacing = 5
	ignoreinvisible = yes
{ind(mood_card(), 1)}}}
"""
    out = []
    if exch.ON:
        out.append(("exchange", block(header("SPEC_H_EXCH", "SPEC_CENTRE_STAND", "SPEC_EFFECT_EXCH_TT"), exch.standing_block())                    + ((block(header("SPEC_H_CHARTER", "SPEC_H_KNOWN_RIGHT"), exch.known_block())
                        + block(header("SPEC_H_KNOWN", "SPEC_H_NAMES_RIGHT"), exch.names_block())
                        + block(header("SPEC_H_CONTEST"), exch.contest_block())
                        ) if exch.NAMES_ON else
                       block(header("SPEC_H_KNOWN", "SPEC_H_KNOWN_RIGHT"), exch.known_block()) if exch.EARN else "")))
    return out + [
        ("booms", card + block(header("SPEC_H_GOODS", "SPEC_LEVERS_RIGHT", "SPEC_LEVERS_TT"), goods_board(k))
         + __import__("company_section").section()),
        # every tab the same way: large headers for its sections, folding ones only inside a section
        ("banking", section("CHARTS", "spec_hide_charts_bank", charts.lent() + charts.credit_history())
         + block(header("SPEC_H_POLICY", "SPEC_H_POLICY_RIGHT", "SPEC_EFFECT_GIVEN_TT", gt(v("spec_credit_given"))), policy())
         + block(header("SPEC_H_RESCUE"), panic_block() + (exch.pledge_row() if exch.ON else ""), gap=GAP)),
        ("world", exch.section() + (block(header("SPEC_H_RIVAL", "SPEC_H_RIVAL_RIGHT"), exch.rival_block())
                                     if exch.ON and exch.RIVAL_ON else "")),
    ]


def tab_type(k):
    """The Finance window (generate.information_panel_bar hosts it and its side bar button): vanilla's panel frame
    and tab bar, shown while GetVariableSystem has spec_finance, the player's own country always."""
    import interest_list  # imports this module
    ts = tabs(k)
    on = lambda i: (f"Or(Not(GetVariableSystem.Exists('{FIN_TAB}')), GetVariableSystem.HasValue('{FIN_TAB}', '{ts[i][0]}'))" if i == 0
                    else f"GetVariableSystem.HasValue('{FIN_TAB}', '{ts[i][0]}')")
    buttons = "".join(f"""blockoverride "{n}_button" {{
	text = "SPEC_FIN_TAB_{name.upper()}"
}}
blockoverride "{n}_button_tooltip" {{
	tooltip = "SPEC_FIN_TAB_{name.upper()}_TT"
}}
blockoverride "{n}_button_click" {{
	onclick = "[GetVariableSystem.Set('{FIN_TAB}', '{name}')]"
}}
blockoverride "{n}_button_visibility" {{
	visible = "[{on(i)}]"
}}
blockoverride "{n}_button_visibility_checked" {{
	visible = "[Not({on(i)})]"
}}
blockoverride "{n}_button_selected" {{
	text = "SPEC_FIN_TAB_{name.upper()}"
}}
""" for i, (n, (name, _)) in enumerate(zip(("first", "second", "third", "fourth", "fifth"), ts)))
    bodies = "".join(f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	visible = "[And({ACTIVE}, {on(i)})]"

{ind(body, 1)}}}
""" for i, (_, body) in enumerate(ts))
    return f"""types spec_market_types {{
{ind(interest_list.overlay_types(), 1)}
{ind(navigation_guard(), 1)}
	type spec_finance_window = default_block_window {{
		visible = "[GetVariableSystem.Exists('{FIN}')]"
		datacontext = "[GetPlayer]"

		blockoverride "window_header_name" {{
			text = "SPEC_FINANCE"
		}}
		blockoverride "entire_back_button" {{
			back_button_large = {{
				position = {{ 8 30 }}
				onclick = "{CLOSE}"
				input_action = "back"
			}}
		}}
		blockoverride "header_close_button" {{
			onclick = "{CLOSE}"
		}}
		blockoverride "fixed_top" {{
			tab_buttons = {{
{ind(buttons, 4)}			}}
		}}
		blockoverride "scrollarea_content" {{
			flowcontainer = {{
				direction = vertical
				parentanchor = hcenter
				margin_top = 12
				margin_bottom = 24
				ignoreinvisible = yes

{ind(off_notice(), 4)}
{ind(bodies, 4)}			}}
		}}
	}}
}}
"""


def loc(k):
    panic, mania, credit_from, tight_pull, tight_from = k["PANIC"], k["MANIA"], k["CREDIT_FROM"], k["TIGHT_PULL"], k["TIGHT_FROM"]
    panic_rise = (f"Borrowing raises it. Once [concept_spec_leverage] passes #v {leverage.SAFE}#! months it climbs, up to #v {panic + leverage.PANIC_SPAN:g}#! at #v {leverage.RUIN}#! months."
                  if leverage.ON else "")
    panic_months = -(-k["PANIC_DAYS"] // 30)  # rounded up, as spec_panic_months is
    exch = __import__("centres")  # imports this module
    flight_who = ("Each [concept_great_power], and each [concept_country] whose [concept_spec_exchange] is #v International#! or higher,"
                  if exch.ON else "Each [concept_great_power]")
    # no multiplier here: the gain shown before it already counts our own Standing
    flight_more = " The higher an [concept_spec_exchange] stands, the more it receives." if exch.ON else ""

    def by_tier(prefix, names=None, value=CONF):
        names = names or [t[0] for t in TIERS]
        return "".join(f"SelectLocalization({tier_test(value, lo, hi)},'{prefix}_{n.upper()}', " for n, (_, lo, hi, *_) in zip(names, TIERS[:-1])) \
            + f"'{prefix}_{names[-1].upper()}'" + ")" * (len(TIERS) - 1)

    def by_stance(prefix):
        return (f"[SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(-1)}), '{prefix}_TIGHT', "
                f"SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(1)}), '{prefix}_LOOSE', '{prefix}_NORMAL'))]")
    cd = v("spec_stance_cooldown", 0)

    def pct(expr):
        """A multiplier shown the vanilla way, as a signed, coloured percentage."""
        return f"[Subtract_CFixedPoint({expr}, {fx(1)})|=+%0]"

    def pct_neutral(expr):
        """The same for a trade-off, where higher is neither good nor bad: signed, but not coloured green or red."""
        return f"#v [Subtract_CFixedPoint({expr}, {fx(1)})|+%0]#!"

    def word(expr, prefix, cuts):
        """A level in words: the first cut the value sits below picks the word, past the last cut the last word."""
        picks = "".join(f"SelectLocalization(LessThan_CFixedPoint({expr}, {fx(c)}), '{prefix}_{i}', " for i, c in enumerate(cuts))
        return f"[{picks}'{prefix}_{len(cuts)}'{')' * len(cuts)}]"

    pops = "$capitalists_no_icon$, $aristocrats_no_icon$ and $shopkeepers_no_icon$"
    igs = "$ig_industrialists$ and $ig_petty_bourgeoisie$"
    # the World Crash that opens the Long Depression stops lending (depression.NO_CREDIT: the spec_ld_crash modifier)
    ld_crash = f"{P}.Var('spec_world_crash').IsSet"  # depression.CRASH_FLAG: set exactly while the World Crash blocks lending

    def invest_line(t):
        """What a confidence band does to investment, for the card's description."""
        m = k["BAND_INVEST"].get(t, 0)
        return f"{pops} invest #{'P' if m > 0 else 'N'} {abs(m):.0%}#! {'more' if m > 0 else 'less'}."

    def pc(h):
        return f"{round((h - 1) * 100):+d}%"
    no_credit, no_credit_end, no_credit_tt, lev_loc, no_rescue, panic_bad = "", "", "", "", "", ""
    if leverage.ON:
        crunch = f"{P}.Var('spec_crunch').IsSet"
        no_rescue = "\\n[concept_spec_bad_debts]: #N Not cleared#!\\n#v Buy Up Bad Loans#! can halve them once while they last."
        panic_bad = f"[AddLocalizationIf({crunch}, 'SPEC_PANIC_BAD_DEBTS')]"
        no_credit, no_credit_end, no_credit_tt = f"SelectLocalization({P}.Var('spec_crunch').IsSet, 'SPEC_CREDIT_NO_CRUNCH', ", ")", ", while [concept_spec_bad_debts] last"
        relief = f"{P}.Var('spec_lev_fade').IsSet"
        lev = sv("spec_lev")
        inv_if = f"Multiply_CFixedPoint({sv('spec_crunch_if')}, {fx(f'{leverage.CRUNCH_INVEST * 100:g}')})"  # investment lost if a panic began now
        lev_loc = f""" SPEC_CREDIT_NO_CRUNCH: "Not Lending: [concept_spec_bad_debts]"
 SPEC_LEV_BAD_NOW: "[concept_spec_bad_debts]: #N -[{sv('spec_crunch_tp_pct')}|1]%#! [concept_throughput] now, fading over #v [{sv('spec_crunch_months')}|0]#! more months\\n"
 SPEC_LEV_RELIEF: "We lost land, so [concept_spec_bad_debts] count only #v [{sv('spec_lev_bad')}|1]#! months of [concept_spec_leverage]. They go back to full over #v [{sv('spec_lev_fade_sv')}|0]#! more months\\n"
 SPEC_LEV_NOTES: "[AddLocalizationIf({crunch}, 'SPEC_LEV_BAD_NOW')][AddLocalizationIf({relief}, 'SPEC_LEV_RELIEF')]"
 SPEC_PANIC_BAD_DEBTS: "[concept_spec_bad_debts]: #N -[{sv('spec_crunch_tp_pct')}|1]%#! [concept_throughput] now, fading over #v [{sv('spec_crunch_months')}|0]#! more months. They may outlast the panic.\\n\\n"
 SPEC_DRIVER_DROP: "Panic Begins"
 SPEC_DRIVER_DROP_TT: "#header Panic Begins: [{v('spec_c_drop')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n#italic Borrowing too much makes a panic hit harder.#!\\n\\nWhen a [concept_spec_financial_panic] starts while [concept_spec_leverage] is high, [concept_spec_market_confidence] drops straight to below #v {k['PANIC']}#!."
 SPEC_EFFECT_LEV: "Credit Leverage"
 SPEC_EFFECT_LEV_VALUE: "[SelectLocalization({gt(lev, leverage.SAFE)}, 'SPEC_LEV_HOT', 'SPEC_LEV_SAFE')]"
 SPEC_EFFECT_BAD: "[concept_spec_bad_debts]"
 SPEC_EFFECT_BAD_VALUE: "[SelectLocalization({crunch}, 'SPEC_EFFECT_BAD_ON', SelectLocalization({gt(sv('spec_crunch_if'))}, 'SPEC_EFFECT_BAD_IF', 'SPEC_GP_RISK_NONE'))]"
 SPEC_EFFECT_BAD_IF: "#v None#! (#N -[{sv('spec_crunch_tp_if_pct')}|1]%#! if a panic began now)"
 SPEC_EFFECT_BAD_ON: "#N -[{sv('spec_crunch_tp_pct')}|1]%#! for #v [{sv('spec_crunch_months')}|0]#! months"
 SPEC_LEV_SAFE: "#v [{lev}|1]#! months"
 SPEC_LEV_HOT: "#N [{lev}|1]#! months"
 SPEC_LEV_WORD_SAFE: "#P Safe#!"
 SPEC_LEV_WORD_RISKY: "#N Risky#!"
 SPEC_LEV_WORD_DANGER: "#N Dangerous#!"
 SPEC_LEV_ADVICE_SAFE: "Safe up to #v {leverage.SAFE}#! months"
 SPEC_LEV_ADVICE_RISKY: "Risky past #v {leverage.SAFE}#! months"
 SPEC_LEV_ADVICE_DANGER: "Heavy [concept_spec_bad_debts] past #v {leverage.DANGER}#! months"
 SPEC_LEV_MONTHS_TT: "[concept_spec_outstanding_credit]: #v @money![{v('spec_debt')}|D]#!\\nMonthly Pool Income: #v @money![{sv('spec_lev_income')}|D]#!\\n$TOOLTIP_DELIMITER$\\n#weak Pool income is this month's [concept_investment_pool] income or its yearly average, whichever is higher#!"
 SPEC_LEV_LIMIT: "Lending Limit: #v [{sv('spec_credit_limit')}|0] months#!{exch.LIMIT_LINE}"
 SPEC_LEV_LIMIT_KEY: "Lending Limit: #v [{sv('spec_credit_limit')}|0] months#!"
 SPEC_LEV_MAIN_TT: "#header [concept_spec_leverage]#!\\n$TOOLTIP_DELIMITER$\\n#italic How much our banks have lent out, counted in months of income.#!\\n\\nBanks have lent us #v #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_LEV_MONTHS_TT [{lev}|1] months#!#!#! of pool income\\nStatus: [SelectLocalization({gt(lev, leverage.DANGER)}, 'SPEC_LEV_WORD_DANGER', SelectLocalization({gt(lev, leverage.SAFE)}, 'SPEC_LEV_WORD_RISKY', 'SPEC_LEV_WORD_SAFE'))]\\n$SPEC_LEV_LIMIT$\\n$TOOLTIP_DELIMITER$\\n[concept_throughput] from borrowed money: #P +[{sv('spec_lev_boom_pct')}|0]%#!\\nA panic starts below #v [{sv('spec_panic_at')}|0]#! [concept_spec_market_confidence]\\nIf a panic started now, [concept_spec_bad_debts] would cost #N -[{sv('spec_crunch_tp_if_pct')}|1]%#! [concept_throughput] and #N -[{inv_if}|1]%#! investment\\n[AddLocalizationIf(Or({crunch}, {relief}), 'SPEC_LEV_NOTES')]\\n[SelectLocalization({gt(lev, leverage.DANGER)}, 'SPEC_LEV_ADVICE_DANGER', SelectLocalization({gt(lev, leverage.SAFE)}, 'SPEC_LEV_ADVICE_RISKY', 'SPEC_LEV_ADVICE_SAFE'))]"
"""
        # each rung of the credit ladder: what it allows at its top, what unlocks it, and whether the country is on it
        edges = (0, *leverage.LADDER)
        rungs = list(zip(edges, edges[1:]))
        stress = lambda m: min(max((m - leverage.SAFE) / (leverage.RUIN - leverage.SAFE), 0), 1)
        bad_at = lambda m, per=leverage.CRUNCH_THROUGHPUT: f"{leverage.CRUNCH_MAX * stress(m) * per * 100:.1f}".rstrip("0").rstrip(".")  # throughput %, or investment's
        ib, ies = (f"[GetTechnology('{t}').GetName]" for t in leverage.LADDER_TECHS[1:])
        unlock = ("Available from the start.", f"Unlocked by [GetTechnology('{leverage.LADDER_TECHS[0]}').GetName].",
                  f"Unlocked by {ib} or {ies}.", f"Unlocked by {ib} and {ies} together.")
        for i, (lo, hi) in enumerate(rungs):
            boom = round(leverage.REWARD * 100 * min(hi, leverage.REWARD_MAX))
            debts = "no [concept_spec_bad_debts]" if i == 0 else f"[concept_spec_bad_debts] up to #N -{bad_at(hi)}%#! [concept_throughput] and #N -{bad_at(hi, leverage.CRUNCH_INVEST)}%#! investment"
            lev_loc += f""" SPEC_LEV_LVL_{i}: "#bold {lo} to {hi} months#!: [concept_throughput] from Credit up to #P +{boom}%#!, Panic Threshold up to #v {round(k['PANIC'] + leverage.PANIC_SPAN * stress(hi))}#!, {debts}"
 SPEC_LEV_UNLOCK_{i}: "{unlock[i]}"
 SPEC_LEV_TIER_{i}_TT: "$SPEC_LEV_LVL_{i}$\\n$SPEC_LEV_UNLOCK_{i}$\\n$TOOLTIP_DELIMITER$\\n$SPEC_LEV_YOURS$"
"""
        lev_loc += f""" SPEC_BAILOUT: "Buy Up Bad Loans"
 SPEC_BAILOUT_TT: "#header Buy Up Bad Loans#!\\n$TOOLTIP_DELIMITER$\\n#italic The state buys up the banks' bad loans and takes the loss itself.#!\\n\\n[GetScriptedGui('spec_sgui_bailout').BuildTooltip(GuiScope.SetRoot({P}).End)]"
 SPEC_BAD_SCALE: "The more [concept_spec_leverage] past #v {leverage.SAFE}#! months when a [concept_spec_financial_panic] starts, the worse they are, up to #N -{leverage.CRUNCH_MAX * leverage.CRUNCH_THROUGHPUT * 100:g}%#! [concept_throughput] and #N -{leverage.CRUNCH_MAX * leverage.CRUNCH_INVEST * 100:g}%#! investment at #v {leverage.RUIN}#! months"
 SPEC_BAD_BUILDING: "\\nStill growing, to #N -[{sv('spec_crunch_tp_full_pct')}|1]%#! (#v {leverage.CRUNCH_RAMP * leverage.CRUNCH_THROUGHPUT * 100:g}%#! per month)"
 SPEC_EFFECT_BAD_TT: "#header [concept_spec_bad_debts]#!\\n$TOOLTIP_DELIMITER$\\n#italic Loans that went bad in the panic. Until they clear, banks will not lend.#!\\n\\n[concept_throughput]: #N -[{sv('spec_crunch_tp_pct')}|1]%#!\\nInvestment: #N -[{sv('spec_crunch_invest_pct')}|0]%#!\\nClears in: #v [{sv('spec_crunch_months')}|0] months#![AddLocalizationIf({gt(sv('spec_crunch_left'))}, 'SPEC_BAD_BUILDING')]\\n$TOOLTIP_DELIMITER$\\nThe $concept_throughput$ we got from borrowed money fades away\\n#v Buy Up Bad Loans#! halves them, once\\n\\n$SPEC_BAD_SCALE$"
 SPEC_EFFECT_BAD_NONE_TT: "#header [concept_spec_bad_debts]#!\\nNothing to worry about. Our banks have no bad loans right now.\\n$TOOLTIP_DELIMITER$\\nIf a [concept_spec_financial_panic] started now: #N -[{sv('spec_crunch_tp_if_pct')}|1]%#! [concept_throughput], #N -[{inv_if}|1]%#! Investment\\n$SPEC_LEV_YOURS$\\n\\n$SPEC_BAD_SCALE$"
 SPEC_LEV_YOURS: "Our [concept_spec_leverage]: #v [{lev}|1]#! months"
 SPEC_LEV_LEVELS: "#bold Levels#!{''.join(f'\\n$SPEC_LEV_LVL_{i}$' for i in range(len(rungs)))}"
 SPEC_EFFECT_LEV_TT: "$SPEC_LEV_MAIN_TT$\\n$TOOLTIP_DELIMITER$\\n$SPEC_LEV_LEVELS$"
"""
    banking = gt(sv("spec_has_central_banking"))
    # generate.spec_credit multiplies spec_credit_mult by Lending Standards (cycle.CREDIT) and by the Exchange's
    # charter and specialities (centres.CREDIT): each gets a row, and the word reads generate's spec_credit_rate, their product
    credit_rate, credit_rows = sv("spec_credit_rate"), f"\\n[concept_spec_banking_reforms]: {pct_neutral(sv('spec_reform_credit'))}"
    def factor(script):  # the product of a CREDIT string's "multiply = x" lines, so it follows whatever that module multiplies
        names = [line.split("=")[1].strip() for line in script.splitlines()]
        out = sv(names[0])
        for n in names[1:]:
            out = f"Multiply_CFixedPoint({out}, {sv(n)})"
        return out
    extra = [(name, factor(script)) for name, script in (("[concept_spec_lending_standards]", cycle.CREDIT),
                                                         ("[concept_spec_exchange]", exch.CREDIT)) if script]
    for name, m in extra:
        credit_rows += f"\\n{name}: {pct_neutral(m)}"
    tight = f"EqualTo_CFixedPoint({STANCE}, {fx(-1)})"
    state_names = ["shaken", "wary", "steady", "buoyant", "mania"]
    # the lowest band's title is Shaken: a Financial Panic, when one runs, has its own title
    tiers = "".join(f""" SPEC_TIER_{t.upper()}: "{n}"
 SPEC_TIER_{t.upper()}_ON: "#bold {n}#!"
""" for (t, *_), n in zip(TIERS, BAND_NAMES))
    # each band's effect (BAND_INVEST, BAND_RATE), for the tier tooltips and the gauge tooltip
    def invest(m, r, tr):
        out = f"\\nInvestment by {pops}: #{'P +' if m > 0 else 'N -'}{abs(m):.0%}#!" if m else ""
        out += f"\\n[concept_loans] interest rate: #{'N +' if r > 0 else 'P -'}{abs(r):.0%}#!" if r else ""
        return out + (f"\\nTraded Quantity: #{'P +' if tr > 0 else 'N -'}{abs(tr):.0%}#!" if tr else "")
    tiers += "".join(f' SPEC_INVEST_{t.upper()}: "{invest(*(k[b].get(t, 0) for b in ("BAND_INVEST", "BAND_RATE", "BAND_TRADE")))}{companies.band_tip(t)}"\n' for t, *_ in TIERS)

    # the gauge tooltip, laid out as vanilla's value tooltips: INFAMY_TOOLTIP's header (name: level (value)),
    # CULTURE_POPULATION_CHANGE's "Monthly Change", CULTURAL_FERVOR_FROM_*'s "+1 from X" rows and
    # LEGITIMACY_LEVEL_ACTIVE_TOOLTIP's indented "Effects:" block
    def band_fx(t):
        """A band's effects as stat lines, as SPEC_INVEST_ shows them."""
        m = k["BAND_INVEST"].get(t, 0)
        out = invest(m, k["BAND_RATE"].get(t, 0), k["BAND_TRADE"].get(t, 0))
        out = out.removeprefix("\\n") if m else "Investment follows the market as normal" + out
        return out + companies.band_tip(t)

    def band_next(i):
        """The thresholds either side of band i."""
        _, lo, hi = TIERS[i]
        parts = []
        if lo > 0:
            below = "a [concept_spec_financial_panic] can begin" if i == 1 else f"the market turns #v {BAND_NAMES[i - 1]}#!"
            parts.append(f"Below #v {'$SPEC_PANIC_AT$' if i == 1 else lo}#! {below}")
        if hi < 100:
            parts.append(f"{'at' if parts else 'At'} #v {hi}#! it turns #v {BAND_NAMES[i + 1]}#!")
        return ", ".join(parts) + "."
    tiers += "".join(f' SPEC_GAUGE_FX_{s.upper()}: "{band_fx(t)}"\n SPEC_GAUGE_NEXT_{s.upper()}: "{band_next(i)}"\n'
                     for i, ((t, *_), s) in enumerate(zip(TIERS, state_names)))
    months = "[SelectLocalization(EqualTo_CFixedPoint({}, " + fx(1) + "), 'SPEC_CARD_MONTH', 'SPEC_CARD_MONTHS')]"
    cooldown = v("spec_panic_cooldown")
    rescued = gt(sv("spec_rescued_value"))
    member = "[AddLocalizationIf(Not(ObjectsEqual(Country.Self, Country.GetCapital.GetMarket.GetOwner)), 'SPEC_CARD_MEMBER')]"
    # the stance tooltips: on the current level nothing, on the others the 6-month lock
    # an option that cannot be chosen says why (the button's BuildTooltip: a missing technology or the cooldown); only
    # then, since its hidden effect otherwise leaves BuildTooltip blank lines
    why = lambda t, n: (f"[AddLocalizationIf(And(Not(EqualTo_CFixedPoint({STANCE}, {fx(n)})), "
                        f"Not(GetScriptedGui('spec_sgui_{t}').IsValid(GuiScope.SetRoot({P}).End))), 'SPEC_STANCE_{t.upper()}_WHY')]")
    lock = {t: f"[SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(n)}), 'SPEC_CREDIT_CURRENT', 'SPEC_CREDIT_LOCK')]{why(t, n)}"
            for t, n, *_ in STANCE_ICONS}
    why_loc = "".join(f' SPEC_STANCE_{t.upper()}_WHY: "\\n\\n{sg(t, "BuildTooltip")}"\n' for t, *_ in STANCE_ICONS)
    goods ="[Concept('concept_good','$concept_goods$')]"
    buildings = "[Concept('concept_building','$concept_buildings$')]"
    # each pressure chip: its group's change, a grey 0 when it is still; the tooltip lists the group's drivers
    var = dict(DRIVERS)
    chips = "".join(
        f' SPEC_CHIP_{n}: "[SelectLocalization({nonzero(v(f"spec_p{n}"))}, \'SPEC_CHIP_{n}_V\', \'SPEC_CHIP_ZERO\')]"\n'
        f' SPEC_CHIP_{n}_V: "[{v(f"spec_p{n}")}|+=1]"\n'
        f' SPEC_CHIP_{n}_TT: "#header $SPEC_PRESSURE_{name.upper()}$: $SPEC_CHIP_{n}$#!\\n$TOOLTIP_DELIMITER$'
        + "".join(f"[AddLocalizationIf({nonzero(v(var[k]))}, 'SPEC_CHIP_ROW_{k.upper()}')]"
                  + (f"[AddLocalizationIf({nonzero(v(var[k]))}, 'SPEC_ITEMS_{k.upper()}')]" if k in ITEMS else "") for k in keys)
        + f"[AddLocalizationIf(Not({any_of([nonzero(v(var[k])) for k in keys])}), 'SPEC_CHIP_NONE')]" + '"\n'
        for n, (name, _, keys) in enumerate(PRESSURES, 1))
    chips += ' SPEC_CHIP_NONE: "\\nNo change this month."\n'

    return f""" SPEC_OFF: "Investors do not speculate under the current $ECONOMIC_SYSTEM_GC_LINK$."
 SPEC_CONF_LINE: "[concept_spec_market_confidence]: #v [{CONF}|0]#![SelectLocalization({nonzero(v('spec_c_total'))}, 'SPEC_CONF_CHANGE', 'SPEC_CONF_NO_CHANGE')]"
 SPEC_CONF_CHANGE: " ([{v('spec_c_total')}|+=1])"
 SPEC_CONF_NO_CHANGE: ""
 SPEC_CARD_CHANGE_TT: "#header Market Confidence#!\\nMonthly Change: [{v('spec_c_total')}|+=1]$SPEC_CARD_ROWS${member}"
 SPEC_CARD_MEMBER: "\\n\\nThis is the [concept_spec_market_confidence] of #v [Country.GetName]#!. Each [concept_country] in the [concept_market] has its own."
 SPEC_CARD_RING_TT: "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_TT', 'SPEC_GAUGE_TT')]"
 SPEC_CARD_BAR_TT: "$SPEC_CARD_RING_TT$[AddLocalizationIf(Not({IN_PANIC}), 'SPEC_PANIC_LINE_ADD')]"
 SPEC_PANIC_LINE_ADD: "\\n$TOOLTIP_DELIMITER$\\n$SPEC_PANIC_LINE_TT$"
 SPEC_CARD_FRESH: "#grey First measured next month#!"
 SPEC_CARD_FRESH_TT: "Investors are watching prices. [concept_spec_market_confidence] is first measured next month."
 SPEC_CARD_MONTH: "month"
 SPEC_CARD_MONTHS: "months"
{driver_rows()} SPEC_GAUGE_TT: "$SPEC_GAUGE_HEAD$\\n$SPEC_GAUGE_CHANGE$\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!#indent_newline:3 \\n[{by_tier('SPEC_GAUGE_FX', state_names)}]\\n$SPEC_GAUGE_LEND$$SPEC_DEPTH_LINE$#!\\n\\n[{by_tier('SPEC_GAUGE_NEXT', state_names)}]{member}"
 SPEC_GAUGE_HEAD: "#header [concept_spec_market_confidence]: #bold $SPEC_STATE_TITLE$#! (#v [{CONF}|0]#!)#!"
 SPEC_GAUGE_CHANGE: "Monthly Change: [{v('spec_c_total')}|+=1]#indent_newline:3 $SPEC_GAUGE_ROWS$#!"
 SPEC_GAUGE_LEND: "[SelectLocalization({IN_PANIC}, 'SPEC_GAUGE_LEND_PANIC', {no_credit.replace('SPEC_CREDIT_NO_CRUNCH', 'SPEC_GAUGE_LEND_BAD')}SelectLocalization({ld_crash}, 'SPEC_GAUGE_LEND_CRASH', SelectLocalization({tight}, 'SPEC_GAUGE_LEND_TIGHT', SelectLocalization(Not({gt(CONF, credit_from)}), 'SPEC_GAUGE_LEND_ABOVE', SelectLocalization(LessThan_CFixedPoint({CONF}, {sv('spec_panic_at')}), 'SPEC_GAUGE_LEND_LINE', SelectLocalization(Not({gt(sv('spec_credit_room'))}), 'SPEC_GAUGE_LEND_LIMIT', 'SPEC_GAUGE_LENDING'))))){no_credit_end})]"
 SPEC_GAUGE_LEND_LINE: "Banks do not lend below the Panic Threshold."
 SPEC_GAUGE_LEND_LIMIT: "Banks do not lend past our Lending Limit."
 SPEC_GAUGE_LEND_PANIC: "Banks do not lend during a [concept_spec_financial_panic]."
 SPEC_GAUGE_LEND_BAD: "Banks do not lend while [concept_spec_bad_debts] last."
 SPEC_GAUGE_LEND_CRASH: "Banks do not lend in the World Crash that opens the [concept_spec_long_depression]."
 SPEC_GAUGE_LEND_TIGHT: "Banks do not lend under [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]."
 SPEC_GAUGE_LENDING: "Banks lend into the [concept_investment_pool]."
 SPEC_GAUGE_LEND_ABOVE: "Banks lend only above #v {credit_from}#!."
 SPEC_PRESSURES: "Pressures"
 SPEC_PRESSURES_TT: "#header Pressures: [SelectLocalization({nonzero(v('spec_c_total'))}, 'SPEC_PRESSURES_SUM', 'SPEC_CHIP_ZERO')]#!\\n$TOOLTIP_DELIMITER$\\n#italic What pushed our [concept_spec_market_confidence] up or down this month.#!\\n\\n#instruction Hover over a group to see its causes#!"
 SPEC_PRESSURES_SUM: "[{v('spec_c_total')}|+=1]"
 SPEC_CHIP_ZERO: "#v 0#!"
 SPEC_PRESSURE_GOODS: "Economy"
 SPEC_PRESSURE_ABROAD: "Abroad"
 SPEC_PRESSURE_STATE: "War and Government"
 SPEC_PRESSURE_MOOD: "Investor Mood"
 SPEC_PRESSURE_CREDIT: "Credit"
{chips} SPEC_DOWNSIDE_TT: "#header Booms at Risk#!\\n$TOOLTIP_DELIMITER$\\n#italic Booms do not last forever. When one ends, our [concept_spec_market_confidence] takes a hit.#!\\n\\nBiggest danger: #v [{P}.Var('spec_risk_top_good').GetGoods.GetName]#!, #N -[{BAR_GAP}|0]#! if it ended now\\nBooms that could end: #v [{v('spec_n_risk')}|0]#!\\nIf all end at once, confidence falls to #v [{BAR_FLOOR}|0]#! (#v [{by_tier('SPEC_TIER', value=BAR_FLOOR)}]#!)[AddLocalizationIf({gt(v('spec_n_held'))}, 'SPEC_RISK_HELD_LINE')]\\n$TOOLTIP_DELIMITER$\\n#title By Good:#!#indent_newline:3 $SPEC_ITEMS_RISK$#![AddLocalizationIf({market_visual.mt.gt(v('spec_heat_collapse'), market_visual.SHOWN)}, 'SPEC_RISK_SHARE')]"
 SPEC_RISKS: "Risks"
 SPEC_XS: "Excess"
 SPEC_XS_BAR: "[SelectLocalization({gt(sv('spec_has_stock_exchange'))}, SelectLocalization({P}.Var('spec_heat').IsSet, SelectLocalization({XS_UP}, 'SPEC_XS_BAR_UP', 'SPEC_XS_BAR_COOL'), 'SPEC_XS_BAR_NONE'), 'SPEC_XS_BAR_OFF')]"
 SPEC_XS_BAR_UP: "[{XS}|0] and building. A fall costs #N -[{sv('spec_burst_now')}|0]#!"
 SPEC_XS_BAR_COOL: "[{XS}|0] and cooling. A fall costs #N -[{sv('spec_burst_now')}|0]#!"
 SPEC_XS_BAR_NONE: "None. It builds at #v [{sv('spec_heat_from')}|0]#! confidence"
 SPEC_XS_BAR_OFF: "None without a [GetTechnology('stock_exchange').GetName]"
 SPEC_XS_TT: "#header $concept_spec_speculative_excess$: [{XS}|0] / {XS_MAX}#!\\n$TOOLTIP_DELIMITER$\\n#italic This is the bubble. The longer a boom runs hot, the bigger it gets.#!\\n\\n#P Grows#! while [concept_spec_market_confidence] is #v [{sv('spec_heat_from')}|0]#! or more\\n#v Shrinks#! slowly while it is between #v 60#! and #v [{sv('spec_heat_from')}|0]#!\\n#N Pops#! if it drops below #v 60#!\\n\\nIf it popped now: #N -[{sv('spec_burst_now')}|0]#! [concept_spec_market_confidence] at once (never more than #N [{sv('spec_burst_max')}|0]#!)\\n$TOOLTIP_DELIMITER$\\n#instruction To let it down gently, hold confidence between 60 and [{sv('spec_heat_from')}|0]. The bar turns red when a pop would hurt.#!"
 SPEC_HISTORY: "History"
 SPEC_HISTORY_TT: "#header Market Confidence History#!\\n$TOOLTIP_DELIMITER$\\n#italic Our [concept_spec_market_confidence] over the last #v {HISTORY}#! months. Newest is on the right.#!\\n\\n#v Gold#!: above #v {HIST_MID}#!\\n#v Blue#!: below #v {HIST_MID}#!\\n#N Red#!: #v {BAND_NAMES[0]}#! (below #v {TIERS[0][2]}#!) or #v {BAND_NAMES[-1]}#! (above #v {TIERS[-1][1]}#!)"
{"".join(f""" SPEC_HIST_{n}_TT: "[SelectLocalization({P}.Var('spec_hist{n}').IsSet, 'SPEC_HIST_{n}_ON', 'SPEC_HIST_NONE')]"
 SPEC_HIST_{n}_ON: "#header {'This Month' if n == 1 else 'Last Month' if n == 2 else f'{n - 1} Months Ago'}#!\\n[concept_spec_market_confidence]: #v [{v(f'spec_hist{n}')}|0]#! ([{by_tier('SPEC_TIER', value=v(f'spec_hist{n}'))}])"
""" for n in range(1, HISTORY + 1))} SPEC_HIST_NONE: "No record for this month yet."
 SPEC_RISKS_TT: "#header Risks#!\\n$TOOLTIP_DELIMITER$\\n#italic Things that could knock our [concept_spec_market_confidence] down. The bigger the red number, the harder the hit.#!\\n\\n#b Booms at Risk#! shows the hit if one of our booms ends\\n#b Panic Risk#! shows the hit if a panic in a market tied to ours spreads to us\\n#b War Risk#! shows the hit if a [concept_diplomatic_play] turns into war\\n#b Default Risk#! shows the hit if we borrow past our [Concept('concept_credit','$concept_credit_limit$')]\\n#b Bubble#! shows the hit if our $concept_spec_speculative_excess$ pops\\n$TOOLTIP_DELIMITER$\\n#instruction Hover over each one to see what is behind it#!"
 SPEC_RISK_1: "[SelectLocalization({BAR_RISK}, 'SPEC_RISK_1_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_1_V: "#N -[{BAR_GAP}|0]#!"
 SPEC_RISK_1_TT: "[SelectLocalization({BAR_RISK}, 'SPEC_DOWNSIDE_TT', 'SPEC_RISK_1_NONE')]"
 SPEC_RISK_HELD_LINE: "\\nHeld back, winding down gently as a [concept_spec_correction]: #v [{v('spec_n_held')}|0]#!"
{"".join(f''' SPEC_WHY_END_{sev}: "#v x{rate:g}#! from [concept_spec_{name}]"
''' for (sev, _, _, rate, _), name in zip(k['UNWINDS'], ("collapse", "bust", "correction")))} SPEC_WHY_CAP: "\\nNo boom can take more than #N {k['CONF_CRASH_MAX']:g}#! in a month."
 SPEC_WHY_FALLING: "\\n\\nInterest fell this month. If it keeps falling, the boom ends."
 SPEC_RISK_1_NONE: "#header Booms at Risk#!\\nNothing to worry about. None of our booms would hurt our [concept_spec_market_confidence] if it ended."
 SPEC_RISK_2: "[SelectLocalization({SRC_RISK}, 'SPEC_RISK_2_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_2_V: "#N -[{SRC_HIT}|0]#!"
 SPEC_RISK_2_TT: "[SelectLocalization({SRC_RISK}, 'SPEC_BAR_SRC_TT', 'SPEC_RISK_2_NONE')]"
 SPEC_RISK_2_NONE: "#header Panic Risk#!\\nNothing to worry about. No [concept_country] tied to ours is close to a [concept_spec_financial_panic] or in a #v {BAND_NAMES[-1]}#!."
 SPEC_RISK_3: "[SelectLocalization({WAR_RISK}, 'SPEC_RISK_3_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_3_V: "#N -[{v('spec_war_risk')}|1]#!"
 SPEC_RISK_3_TT: "[SelectLocalization({WAR_RISK}, 'SPEC_RISK_3_ON', 'SPEC_RISK_3_NONE')]"
 SPEC_RISK_3_ON: "#header War Risk#!\\n$TOOLTIP_DELIMITER$\\n#italic A [concept_diplomatic_play] that turns into war shakes the markets.#!\\n\\nIf war breaks out, up to #N -[{v('spec_war_risk')}|1]#! [concept_spec_market_confidence] a month\\nPlays that could become wars: #v [{v('spec_wr_n')}|0]#!\\n#N -{k['WAR_COST']:g}#! for each, from an average war#indent_newline:3 {''.join(f"[AddLocalizationIf({P}.Var('spec_wr{n}').IsSet, 'SPEC_ITEM_WR_{n}')]" for n in range(1, 4))}#!\\n$TOOLTIP_DELIMITER$\\n#weak A war that goes badly costs even more through [concept_spec_war_news].#!"
{''.join(f""" SPEC_ITEM_WR_{n}: "\\nAgainst #v [{P}.Var('spec_wr{n}').GetCountry.GetName]#!: #N -{k['WAR_COST']:g}#!"
""" for n in range(1, 4))} SPEC_RISK_3_NONE: "#header War Risk#!\\nNothing to worry about. We are in no [concept_diplomatic_play] that could turn into war."
 SPEC_RISK_5: "[SelectLocalization({XS_RISK}, 'SPEC_RISK_5_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_5_V: "#N -[{sv('spec_burst_now')}|0]#!"
 SPEC_RISK_5_TT: "[SelectLocalization({XS_RISK}, 'SPEC_XS_TT', 'SPEC_RISK_5_NONE')]"
 SPEC_RISK_5_NONE: "#header $concept_spec_speculative_excess$#!\\nNothing to worry about. There is no bubble right now. One starts to grow once [concept_spec_market_confidence] reaches #v [{sv('spec_heat_from')}|0]#!."
 SPEC_RISK_4: "[SelectLocalization({DEFAULT_RISK}, 'SPEC_RISK_4_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_4_V: "#N -{k['DEFAULT_COST']}#!"
 SPEC_RISK_4_TT: "[SelectLocalization({DEFAULT_RISK}, 'SPEC_RISK_4_ON', 'SPEC_RISK_4_NONE')]"
 SPEC_RISK_4_ON: "#header Default Risk#!\\n$TOOLTIP_DELIMITER$\\n#italic We are borrowing close to our limit. Go over it and we default.#!\\n\\n[concept_credit] used: #v [{v('spec_default_risk')}|%0]#![AddLocalizationIf({P}.Var('spec_tm_broke').IsSet, 'SPEC_RISK_4_BROKE')]\\nIf it passes #v 100%#!: [concept_default], #N -{k['DEFAULT_COST']}#! [concept_spec_market_confidence] every month until it ends\\n$TOOLTIP_DELIMITER$\\n#weak Shows up once we have used #v {k['DEFAULT_FROM']:.0%}#! of our $concept_credit$#!"
 SPEC_RISK_4_BROKE: "\\n#v [{sv('spec_broke_weeks')}|0]#! weeks until [concept_bankruptcy] if we keep losing money like this. Already costing [{v('spec_tm_broke')}|+=2] a month"
 SPEC_RISK_4_NONE: "#header Default Risk#!\\nNothing to worry about. Our debt is well within our [concept_credit] limit."
 SPEC_BAR_SRC_TT: "#header Panic Risk#!\\n$TOOLTIP_DELIMITER$\\n#italic Markets are connected. If #v [{SRC}.GetName]#!'s market panics, the panic can spread to ours.#!\\n\\nIf it spreads: #N -[{SRC_HIT}|0]#! [concept_spec_market_confidence]\\n[SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(1)}), 'SPEC_BAR_TIE_1', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(2)}), 'SPEC_BAR_TIE_2', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(3)}), 'SPEC_BAR_TIE_3', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(4)}), 'SPEC_BAR_TIE_4', 'SPEC_BAR_TIE_5'))))]\\nTheir market right now: #v [{by_tier('SPEC_TIER', value=SRC_CONF)}]#!\\n$TOOLTIP_DELIMITER$\\n#b Why so much#!\\n#N -{k['CONTAGION']}#! base hit from a [concept_spec_foreign_panic]\\n#v x[{v('spec_risk_src_size')}|2]#! how big their economy is next to ours\\n#v x[{v('spec_risk_src_w')}|2]#! how closely we are tied ([concept_spec_market_tie])\\n#v x[{v('spec_risk_src_reach')}|2]#! how important they are ([concept_rank])\\n$TOOLTIP_DELIMITER$\\n#weak Only markets that are #v {BAND_NAMES[0]}#!, #v {BAND_NAMES[1]}#! or in #v {BAND_NAMES[-1]}#! can spread a panic#!"
 SPEC_BAR_TIE_1: "#v [{SRC}.GetName]#! shares our [concept_market]."
 SPEC_BAR_TIE_2: "#v [{SRC}.GetName]#! is our overlord or [concept_subject]."
 SPEC_BAR_TIE_3: "#v [{SRC}.GetName]#! has investment rights with us by treaty."
 SPEC_BAR_TIE_4: "Our [concept_market] relies on trade with #v [{SRC}.GetName]#!."
 SPEC_BAR_TIE_5: "#v [{SRC}.GetName]#! owns a large share of our economy."
 SPEC_DEPTH_LINE: "{word(sv('spec_depth'), 'SPEC_DEPTH', vanilla_ties.DEPTH_WORDS)}"
 SPEC_DEPTH_0: "\\nWe have few $building_financial_district$, so booms and their endings are milder here."
 SPEC_DEPTH_1: ""
 SPEC_DEPTH_2: "\\nOur $building_financial_district$ make booms and their endings stronger here."
 SPEC_STATE_TITLE: "[SelectLocalization({IN_PANIC}, 'SPEC_STATE_PANIC', {by_tier('SPEC_STATE', state_names)})]"
 SPEC_STATE_PANIC: "#n Financial Panic#!"
{''.join(f' SPEC_STATE_{s.upper()}: "{n}"{chr(10)}' for s, n in zip(state_names, BAND_NAMES))}
 SPEC_STATE_DESC: "[SelectLocalization({IN_PANIC}, 'SPEC_STATE_DESC_PANIC', {by_tier('SPEC_STATE_DESC', state_names)})]"
 SPEC_STATE_DESC_PANIC: "$SPEC_PANIC_LEFT$. [SelectLocalization({rescued}, 'SPEC_STATE_DESC_PANIC_RESCUED', 'SPEC_STATE_DESC_PANIC_FULL')]"
 SPEC_STATE_DESC_PANIC_FULL: "Until then [concept_private_construction] is halved."
 SPEC_STATE_DESC_PANIC_RESCUED: "After the Bank Rescue, [concept_private_construction] is #N {50 * 0.5:g}%#! lower until then."
 SPEC_STATE_DESC_SHAKEN: "{invest_line('panic')} No new [concept_spec_financial_panic] can begin for #v [{cooldown}|0]#! {months.format(cooldown)}."
 SPEC_STATE_DESC_WARY: "[SelectLocalization({gt(cooldown)}, 'SPEC_STATE_DESC_WARY_SAFE', 'SPEC_STATE_DESC_WARY_RISK')]"
 SPEC_STATE_DESC_WARY_RISK: "{invest_line('wary')} Another sharp fall in prices could cause a [concept_spec_financial_panic]."
 SPEC_STATE_DESC_WARY_SAFE: "{invest_line('wary')} No new [concept_spec_financial_panic] can begin for #v [{cooldown}|0]#! {months.format(cooldown)}."
 SPEC_STATE_DESC_STEADY: "Investment follows the market as normal."
 SPEC_STATE_DESC_BUOYANT: "{invest_line('buoyant')}"
 SPEC_STATE_DESC_MANIA: "{invest_line('mania')} A sharp fall in prices would hit [concept_spec_market_confidence] hard."
{tiers} SPEC_TIER_PANIC_TT: "#header {BAND_NAMES[0]}#!\\nBelow #v {TIERS[0][2]}#!\\n$TOOLTIP_DELIMITER$\\n#italic Investors are scared.#!\\n$SPEC_INVEST_PANIC$\\n\\nA [concept_spec_financial_panic] starts below #v [{sv('spec_panic_at')}|0]#! and halves [concept_private_construction] for up to #v [{sv('spec_panic_months_trust')}|0]#! months\\n#weak After a panic, no new one can start for #v {k['PANIC_COOLDOWN']}#! months#!"
 SPEC_TIER_WARY_TT: "#header {BAND_NAMES[1]}#!\\n#v {TIERS[1][1]}#! to #v {TIERS[1][2]}#!\\n$TOOLTIP_DELIMITER$\\n#italic Investors are nervous.#!\\n$SPEC_INVEST_WARY$\\n\\nBanks will not lend. A [concept_spec_financial_panic] starts below #v [{sv('spec_panic_at')}|0]#!."
 SPEC_TIER_STEADY_TT: "#header {BAND_NAMES[2]}#!\\n#v {TIERS[2][1]}#! to #v {TIERS[2][2]}#!\\n$TOOLTIP_DELIMITER$\\n#italic Investors act normally.#!\\n$SPEC_INVEST_STEADY$\\n\\nBanks lend only while [concept_spec_market_confidence] is above #v {credit_from}#!. $concept_spec_market_confidence$ slowly drifts back toward its [concept_spec_baseline] of #v {k['CONF_START']}#!."
 SPEC_TIER_BUOYANT_TT: "#header {BAND_NAMES[3]}#!\\n#v {TIERS[3][1]}#! to #v {TIERS[3][2]}#!\\n$TOOLTIP_DELIMITER$\\n#italic Investors are in a good mood.#!\\n$SPEC_INVEST_BUOYANT$\\n\\nBanks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is above #v {credit_from}#!. Only the [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')] credit policy stops them."
 SPEC_TIER_MANIA_TT: "#header {BAND_NAMES[4]}#!\\nAbove #v {mania}#!\\n$TOOLTIP_DELIMITER$\\n#italic Investors are wild with excitement.#!\\n$SPEC_INVEST_MANIA$\\n\\nBanks lend the most here, but a fall in prices hurts the most too."
 SPEC_PANIC_LEFT: "Ends in #v [{PANIC_LEFT}|0]#! {months.format(PANIC_LEFT)}"
 SPEC_PANIC_NONE: "No [concept_spec_financial_panic]"
 SPEC_PANIC_BAR: "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_BAR_ON', 'SPEC_PANIC_BAR_OFF')]"
 SPEC_PANIC_BAR_ON: "#N [{v('spec_panic', 0)}|0]#! of #v [{v('spec_panic_len', 1)}|0]#! months left"
 SPEC_PANIC_BAR_OFF: "Begins below #v [{sv('spec_panic_at')}|0]#! [concept_spec_market_confidence]"
 SPEC_PANIC_NONE_TT: "#header [concept_spec_financial_panic]#!\\nNothing to worry about. There is no panic right now.\\n$TOOLTIP_DELIMITER$\\nA panic starts if [concept_spec_market_confidence] drops below #v [{sv('spec_panic_at')}|0]#!"
 SPEC_PANIC_SUB: "[SelectLocalization({gt(v('spec_clawed'))}, 'SPEC_PANIC_LOANS', 'SPEC_PANIC_NO_LOANS')]"
 SPEC_PANIC_LOANS: "Banks called in #v @money![{v('spec_clawed')}|D]#! of loans"
 SPEC_PANIC_NO_LOANS: "No loans were called in"
 SPEC_PANIC_TT: "$SPEC_GAUGE_HEAD$\\n$SPEC_PANIC_LEFT$\\n$SPEC_GAUGE_CHANGE$\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!#indent_newline:3 \\n[SelectLocalization({rescued}, 'SPEC_PANIC_ALL_EFFECTS_RESCUED', 'SPEC_PANIC_ALL_EFFECTS')]\\n$SPEC_PANIC_SUB$.\\n$SPEC_GAUGE_LEND$#!\\n\\n[AddLocalizationIf({rescued}, 'SPEC_PANIC_RESCUED_NOTE')]{panic_bad}$SPEC_PANIC_TT_END$"
{"".join(f""" SPEC_PANIC_EFFECTS{key}: "[concept_private_construction] is #N {50 * h:g}%#! lower.\\n{pops} invest #N {40 * h:g}%#! less.\\n[Concept('concept_company','$concept_companies$')] lose #N {-companies.PANIC_COMPANY * 100 * h:g}%#! [concept_throughput].\\n${companies.FD_SOL}$: #N {companies.FD_PANIC * h:g}#!\\n{igs}: #N {-2 * h:g}#! [concept_approval]\\nAs it began, #N 10%#! of $capitalists_no_icon$ and #N 5%#! of $aristocrats_no_icon$ and $shopkeepers_no_icon$ became [Concept('concept_radical','$concept_radicals$')]"
""" for key, h in (("", 1), ("_RESCUED", 0.5)))} SPEC_PANIC_RESCUED_NOTE: "The Bank Rescue halves these effects. "
 SPEC_PANIC_TT_END: "$SPEC_PANIC_RELIEF_NOTE$\\n\\n$SPEC_PANIC_RECOVERY$"
 SPEC_PANIC_ALL_EFFECTS: "$SPEC_PANIC_ECONOMY$\\n$SPEC_PANIC_EFFECTS$"
 SPEC_PANIC_ALL_EFFECTS_RESCUED: "$SPEC_PANIC_ECONOMY_RESCUED$\\n$SPEC_PANIC_EFFECTS_RESCUED$"
 SPEC_PANIC_ECONOMY: "$ALL_BUILDINGS$: [concept_throughput] #N {k['PANIC_THROUGHPUT']:+.0%}#!\\n$state_tax_collection_mult$: #N {k['PANIC_TAX']:+.0%}#!"
 SPEC_PANIC_ECONOMY_RESCUED: "$ALL_BUILDINGS$: [concept_throughput] #N {k['PANIC_THROUGHPUT'] * 0.5:+.0%}#!\\n$state_tax_collection_mult$: #N {k['PANIC_TAX'] * 0.5:+.1%}#!"
 spec_panic_relief: "Panic Relief"
 spec_panic_relief_desc: "The Treasury makes weekly payments to the unemployed until the [concept_spec_financial_panic] ends."
 SPEC_RESCUE_EXCEPTIONS: "#weak Does not cut $spec_panic_relief$ or win back the people radicalized when the panic began#!"
 SPEC_PANIC_RELIEF_NOTE: "#v $spec_panic_relief$#! pays the unemployed from the Treasury every week until the panic ends"
 SPEC_PANIC_RECOVERY: "Ends early once [concept_spec_market_confidence] is back to #v {k['PANIC_ENDS_AT']}#!\\nNo new panic for #v {k['PANIC_COOLDOWN']}#! months after it ends"
 SPEC_RESCUE: "[SelectLocalization({gt(sv('spec_rescued_value'))}, 'SPEC_RESCUED', 'SPEC_RESCUE_LABEL')]"
 SPEC_RESCUE_LABEL: "Lend to the Banks"
 SPEC_RESCUED: "Lent to the Banks"
 SPEC_RESCUE_TT: "$SPEC_RESCUE_ACTION_TT$\\n\\n$SPEC_RESCUE_EXCEPTIONS$"
 SPEC_RESCUE_ACTION_TT: "#header Lend to the Banks#!\\n$TOOLTIP_DELIMITER$\\n#italic Prop up the banks with state money to stop the panic.#!\\n\\nThe panic ends within #v [{sv('spec_rescue_months')}|0]#! months\\nThe panic's ongoing penalties: #P -50%#!\\n[concept_spec_market_confidence]: #P +{k['RESCUE_CONF']}#!{no_rescue}\\n\\n#lore The Bank of England lent freely in the crises of 1847, 1857 and 1866.#!\\n\\n{sg('rescue', 'BuildTooltip')}"
 SPEC_H_POLICY: "Credit Policy"
 SPEC_H_POLICY_TT: "#header $concept_spec_credit_policy$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_credit_policy_desc$\\n\\n#lore Central banks steered lending through their discount rate, as the Bank of England did with Bank Rate.#!"
 SPEC_POLICY_TT: "[SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(-1)}), 'SPEC_STANCE_TIGHT_TT', SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(1)}), 'SPEC_STANCE_LOOSE_TT', 'SPEC_STANCE_NORMAL_TT'))]"
 SPEC_H_RESCUE: "Bank Rescue"
 SPEC_H_RESCUE_TT: "#header Bank Rescue#!\\n$TOOLTIP_DELIMITER$\\nDuring a [concept_spec_financial_panic], #v Lend to the Banks#! ends it sooner."
 SPEC_FINANCE: "Finance"
 SPEC_FINANCE_BUTTON_TT: "#header $SPEC_FINANCE$#!\\nBooms and panics, the banks{', our [concept_spec_exchange] and the world rankings' if exch.ON else ''}"
 SPEC_FINANCE_BTN: "Finance"
 SPEC_FIN_TAB_EXCHANGE: "Trading Floor"
 SPEC_FIN_TAB_EXCHANGE_TT: "Our [concept_spec_exchange], with its Standing, its Exchange Charter and its specialities"
 SPEC_FIN_TAB_BOOMS: "Speculation"
 SPEC_FIN_TAB_BOOMS_TT: "[concept_spec_market_confidence] and [concept_spec_investor_interest] in each good"
 SPEC_FIN_TAB_BANKING: "Banking"
 SPEC_FIN_TAB_BANKING_TT: "[concept_spec_credit_policy], [concept_spec_leverage], [concept_spec_bad_debts] and Bank Rescues"
 SPEC_FIN_TAB_WORLD: "Exchanges"
 SPEC_FIN_TAB_WORLD_TT: "Where our [concept_spec_exchange] ranks among the world's Exchanges, and our competitors"
 SPEC_H_POLICY_RIGHT: "#v @money![{v('spec_credit_given')}|+D]#! this month"
 SPEC_POLICY_UPPER: "{by_stance('SPEC_POLICY_UPPER')}"
 SPEC_POLICY_UPPER_TIGHT: "[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]"
 SPEC_POLICY_UPPER_NORMAL: "[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_normal$')]"
 SPEC_POLICY_UPPER_LOOSE: "[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_loose$')]"
 SPEC_POLICY_LOWER: "[SelectLocalization({IN_PANIC}, 'SPEC_CREDIT_NO_PANIC', {no_credit}SelectLocalization({ld_crash}, 'SPEC_CREDIT_NO_CRASH', SelectLocalization({tight}, 'SPEC_CREDIT_NO_TIGHT', SelectLocalization(Not({gt(CONF, credit_from)}), 'SPEC_CREDIT_NO_CONF', SelectLocalization(LessThan_CFixedPoint({CONF}, {sv('spec_panic_at')}), 'SPEC_CREDIT_NO_LINE', SelectLocalization(Not({gt(sv('spec_credit_room'))}), 'SPEC_CREDIT_NO_ROOM', SelectLocalization(Not({banking}), 'SPEC_CREDIT_LENDING_LOCKED', SelectLocalization({gt(cd)}, 'SPEC_POLICY_COOLDOWN', 'SPEC_CREDIT_LENDING')))))))){no_credit_end}]"
 SPEC_CREDIT_NO_LINE: "Not lending while below the Panic Threshold"
 SPEC_CREDIT_NO_ROOM: "Not lending while at the Lending Limit"
 SPEC_CREDIT_LENDING_LOCKED: "Lending up to #v [{sv('spec_credit_limit')}|0]#! months. Policy requires [GetTechnology('central_banking').GetName]"
 SPEC_CREDIT_NO_PANIC: "Not Lending: [concept_spec_financial_panic]"
 SPEC_CREDIT_NO_CRASH: "Not Lending: World Crash"
 SPEC_CREDIT_NO_TIGHT: "Not Lending: [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]"
 SPEC_CREDIT_NO_CONF: "Not Lending: below #v {credit_from}#! [concept_spec_market_confidence]"
 SPEC_CREDIT_LENDING: "Lending while [concept_spec_market_confidence] is above #v {credit_from}#!"
 SPEC_POLICY_COOLDOWN: "[SelectLocalization(EqualTo_CFixedPoint({cd}, {fx(1)}), 'SPEC_POLICY_COOLDOWN_ONE', 'SPEC_POLICY_COOLDOWN_MANY')]"
 SPEC_POLICY_COOLDOWN_ONE: "Can be changed in #v 1#! month"
 SPEC_POLICY_COOLDOWN_MANY: "Can be changed in #v [{cd}|0]#! months"
 SPEC_STANCE_TIGHT_TT: "#header Tight Credit#!\\nCredit Lent This Month: #v None#!\\n$TOOLTIP_DELIMITER$\\n#italic Banks stop lending to cool the market down.#!\\n\\nEach month, #N {tight_pull:.0%}#! of our [concept_spec_market_confidence] above #v {tight_from}#! drains away\\nInvestor Reaction: #N -50%#!\\n{credit_ai.ig_lines('tight')}\\n\\n#P Smaller#! booms, and #P softer#! crashes and panics{lock['tight']}"
 SPEC_STANCE_NORMAL_TT: "#header Normal Credit#!\\nCredit Lent This Month: #v @money![{sv('spec_credit_preview')}|D]#!\\n$TOOLTIP_DELIMITER$\\n#italic Banks lend as usual.#!\\n\\nBanks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is above #v {credit_from}#!.{lock['normal']}"
 SPEC_STANCE_LOOSE_TT: "#header Loose Credit#!\\nCredit Lent This Month: #v @money![{sv('spec_credit_preview_loose')}|D]#!\\n$TOOLTIP_DELIMITER$\\n#italic Banks lend freely to heat the market up.#!\\n\\nInvestor Reaction to Rising Prices: #v +30%#!\\n{credit_ai.ig_lines('loose')}\\n\\n#P Bigger#! booms, but #N bigger#! losses when they end{lock['loose']}"
 SPEC_CREDIT_CURRENT: ""
{why_loc} SPEC_CREDIT_LOCK: "\\n\\nLocks [concept_spec_credit_policy] for #v {k['STANCE_COOLDOWN']}#! months"
 SPEC_EFFECT_GIVEN_TT: "#header Credit Lent This Month#!\\n#v @money![{v('spec_credit_given')}|D]#! this month\\n$TOOLTIP_DELIMITER$\\n#italic Money our banks add to our [concept_investment_pool].#!\\n\\nLending Rate: #v {word(credit_rate, 'SPEC_CREDITW', [0.01, 0.5, 1.15, 1.8])}#!\\n#italic How freely our banks lend, not interest we pay.#!\\n\\n#b Compared with normal lending#!\\n$ECONOMIC_SYSTEM_GC_LINK$: {pct_neutral(sv('spec_law_mult'))}\\nFinance Technologies: {pct_neutral(sv('spec_tech_credit'))}\\n[concept_spec_credit_policy]: {pct_neutral(sv('spec_stance_credit'))}{credit_rows}\\n$TOOLTIP_DELIMITER$\\n#weak Banks lend every month while [concept_spec_market_confidence] is above #v {credit_from}#!, more the higher it goes, until they reach their lending limit. The [concept_investment_pool] shows it week by week.#!"
 SPEC_EFFECT_DEBT: "Withdrawn in a Panic"
 SPEC_DEBT_BAR: "[SelectLocalization(GreaterThan_CFixedPoint({POOL}, {fx(0)}), 'SPEC_DEBT_BAR_ON', 'SPEC_DEBT_BAR_NONE')]"
 SPEC_DEBT_BAR_ON: "A panic would take #N @money![{sv('spec_clawback')}|D]#! of our @money![{POOL}|D] [concept_investment_pool]"
 SPEC_DEBT_BAR_NONE: "Our [concept_investment_pool] is empty, so a panic has nothing to take"
 SPEC_EFFECT_OWED: "[concept_spec_outstanding_credit]"
 SPEC_EFFECT_OWED_VALUE: "#v @money![{v('spec_debt')}|D]#!"
 SPEC_EFFECT_OWED_TT: "#header [concept_spec_outstanding_credit]#!\\n$SPEC_LEV_MONTHS_TT$"
 SPEC_PANIC_LINE_TT: "#header Panic Threshold#!\\nIf [concept_spec_market_confidence] drops below #v [{sv('spec_panic_at')}|0]#!, a [concept_spec_financial_panic] starts. {panic_rise}"\n SPEC_PANIC_TAG: "#b Panic#!"
 SPEC_EFFECT_DEBT_VALUE: "#v @money![{sv('spec_clawback')}|D]#!"
 SPEC_EFFECT_DEBT_TT: "#header Withdrawn in a Panic#!\\n#v @money![{sv('spec_clawback')}|D]#! if a panic began today\\n$TOOLTIP_DELIMITER$\\n#italic Money still in our [concept_investment_pool] for now. If a [concept_spec_financial_panic] hits, banks call back part of their loans and take it out.#!\\n\\n[concept_spec_outstanding_credit]: #v @money![{v('spec_debt')}|D]#!\\nShare called back: #v {k['CLAWBACK']:.0%}#!\\nMost it can take of our pool: #v [{sv('spec_claw_share')}|%0]#! at our [concept_spec_leverage]\\n$TOOLTIP_DELIMITER$\\n#instruction The higher our [concept_spec_leverage], the more of the pool a panic can take: #v {k['CLAW_FLOOR']:.0%}#! at low leverage, all of it once leverage turns dangerous.#!\\n\\n#weak $concept_spec_outstanding_credit$ shrinks by #v {k['CREDIT_RUNOFF']:.0%}#! a month as loans are paid off#!"
{lev_loc} SPEC_CREDITW_0: "None"
 SPEC_CREDITW_1: "Low"
 SPEC_CREDITW_2: "Normal"
 SPEC_CREDITW_3: "High"
 SPEC_CREDITW_4: "Very High"
 SPEC_H_GOODS: "Investor Interest"
 SPEC_H_GOODS_TT: "#header $concept_spec_investor_interest$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_investor_interest_desc$"
 SPEC_INTEREST: "{word(WORD, 'SPEC_INTEREST', [1.5, 2.5, 3.5, 4.5, 5.5])}"
{"".join(f' SPEC_INTEREST_{i}: "@spec_interest_{WORDS[i + 1]}! {WORDS[i + 1].capitalize()}"' + chr(10) for i in range(6))} SPEC_GOODS_NONE: ""
 SPEC_TILE_TT: "#header [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BODY$\\n\\n#instruction Click to open the [Goods.GetName] panel#!"
 SPEC_TILE_BODY: "[concept_spec_investor_interest]: #v $SPEC_INTEREST$#!\\nSince Last Month: $SPEC_TILE_MOVE$\\nPrice Trend: #v [{TREND}|=+%0]#! compared with its usual price\\n#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WHY_SPEED Investor Reaction: #v x[{sv('spec_hype_mult')}|2]#!#!#!$SPEC_TILE_NEXT$\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!\\nProducers' [concept_throughput]: $SPEC_PULL$$SPEC_TILE_LIFT$\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BOOM$$SPEC_TILE_BANKS$"
 SPEC_TILE_BOOM: "[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_sev')}, {fx(1)}), 'SPEC_TILE_BOOM_ON', SelectLocalization(GreaterThan_CFixedPoint({good_var('spec_glut')}, {fx(0)}), 'SPEC_TILE_BOOM_PAST', 'SPEC_TILE_BOOM_NONE'))]"
 SPEC_TILE_BOOM_ON: "If the boom ends: $SPEC_UNWIND_LINK$[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({RISK}, {fx(0.5)}), 'SPEC_TILE_BOOM_COST', 'SPEC_TILE_BOOM_SLIGHT')]"
 SPEC_TILE_BOOM_COST: ", #N -[{RISK}|0]#! [concept_spec_market_confidence]"
 SPEC_TILE_BOOM_SLIGHT: ", a slight loss of [concept_spec_market_confidence]"
 SPEC_TILE_BOOM_PAST: "Recovering from a [SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_glut')}, {fx(3)}), 'SPEC_UNWIND_C_3', SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_glut')}, {fx(2)}), 'SPEC_UNWIND_C_2', 'SPEC_UNWIND_C_1'))], interest held at #v Doubtful#! or lower"
 SPEC_TILE_BOOM_NONE: "No boom until interest reaches @spec_interest_keen! #v Keen#!"
 SPEC_PULL: "{word(WORD, 'SPEC_PULL', [1.5, 2.5, 3.5, 4.5, 5.5])}"
{"".join(f' SPEC_PULL_{w - 1}: "{"#P +" if p > 0 else "#N " if p < 0 else "#v "}{p}%#!"' + chr(10) for w, p in companies.INTEREST_THROUGHPUT.items())} SPEC_TILE_LIFT: "[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({HYPE}, {fx(k['HOT_HYPE'])}), 'SPEC_TILE_LIFTS', 'SPEC_GOODS_NONE')]"
 SPEC_TILE_LIFTS: "\\nBooming, so it lifts [concept_spec_market_confidence] each month"
 SPEC_TILE_MOVE: "[SelectLocalization(EqualTo_CFixedPoint({MOVE}, {fx(1)}), 'SPEC_TILE_RISING', SelectLocalization(EqualTo_CFixedPoint({MOVE}, {fx(-1)}), 'SPEC_TILE_FALLING', 'SPEC_TILE_STEADY'))]"
 SPEC_TILE_RISING: "#P Rising#!"
 SPEC_TILE_FALLING: "#N Falling#!"
 SPEC_TILE_STEADY: "#v Unchanged#!"
 SPEC_RISK_NONE_TT: "$SPEC_RISK_NONE$"
 SPEC_INTEREST_TT: "#header [concept_spec_investor_interest] in [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BODY$"
 SPEC_RISK_TT: "#header Risk of a $SPEC_UNWIND$#!\\nIf the boom ends now: #N -[{RISK}|1]#! [concept_spec_market_confidence]\\n$TOOLTIP_DELIMITER$\\n#b Why so much#!\\n{why_lines(good_var, good_sv, k)}\\n$TOOLTIP_DELIMITER$\\n$SPEC_UNWIND_DESC$"
{band_loc(k)}
 SPEC_DRIVER_RESTRAIN_TT: "#header Restrained Booms: [{v('spec_c_restrain')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_restrain_raw')}|+=2] from booms we let down gently this month\\n{cond_row(ratio('spec_c_restrain', 'spec_restrain_raw'))}\\n$TOOLTIP_DELIMITER$\\n#weak Held-back booms wind down slowly as a [concept_spec_correction] instead of crashing all at once#!"
 SPEC_DRIVER_CAUTION_TT: "#header Government and Events: [{v('spec_c_caution')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nA one-off change from our decisions and market events"
 SPEC_DRIVER_LIMIT_TT: "#header Floor and Ceiling: [{v('spec_c_limit')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[concept_spec_market_confidence] cannot go below #v 0#! or above #v 100#!. This is the part that did not fit."
 SPEC_DRIVER_RESCUE_TT: "#header Bank Rescue: [{v('spec_c_rescue')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nA one-off boost from #v Lend to the Banks#! or #v Suspend the Bank Act#! (never above #v 100#!)"
 SPEC_DRIVER_RESCUE: "Bank Rescue"
 SPEC_DRIVER_WAREND: "End of War"
 SPEC_DRIVER_WAREND_TT: "#header End of War: [{v('spec_c_warend')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n#v x[{v('spec_war_stakes_now')}|%0]#! of the full effect, based on our [concept_casualties]\\n$TOOLTIP_DELIMITER$\\n#title Full Effect#!\\nWon and got a [concept_war_goal]: #P +{k['WAR_END']['won'][0]}#!\\nWon, but got nothing: #P +{k['WAR_END']['won'][1]}#!\\nLost and gave up a [concept_war_goal]: #N {k['WAR_END']['lost'][0]}#!\\nLost, but gave up nothing: #N {k['WAR_END']['lost'][1]}#!\\nNobody won: #N {k['WAR_END']['drawn'][0]}#!\\n\\n#weak We always feel at least #v {diplomacy.WAR_STAKES_MIN:.0%}#! of it, and all of it once the war cost #v 25%#! of our forces#!"
 SPEC_DRIVER_BURST: "Bubble Bursts"
 SPEC_DRIVER_BURST_TT: "#header Bubble Bursts: [{v('spec_c_burst')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n#italic The bubble popped.#!\\n\\n#v [Divide_CFixedPoint({v('spec_c_burst')}, Multiply_CFixedPoint({sv('spec_burst_per_heat')}, {fx(-1)}))|0]#! points of [concept_spec_speculative_excess]\\n#N -[{sv('spec_burst_per_heat')}|2]#! for each point\\nNever more than #N -[{sv('spec_burst_max')}|0]#!\\n$TOOLTIP_DELIMITER$\\nIt pops when [concept_spec_market_confidence] drops below #v {k['BURST_BELOW']}#! after a boom above #v [{sv('spec_heat_from')}|0]#!\\nThe longer and higher the boom, the bigger the pop\\n#weak Needs [GetTechnology('stock_exchange').GetName]#!"
 SPEC_DRIVER_CAUTION: "Government and Events"
 SPEC_DRIVER_RESTRAIN: "Restrained Booms"
 SPEC_DRIVER_LIMIT: "Floor and Ceiling"
 SPEC_DRIVER_BOOM: "Booming Goods"
 SPEC_DRIVER_BOOM_TT: "#header Booming Goods: [{v('spec_c_boom')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_boom_raw')}|+=2] from #v [{v('spec_n_boom')}|0]#! booming {goods}[AddLocalizationIf({gt(v('spec_boom_raw'), k['CONF_BOOM_MAX'])}, 'SPEC_BOOM_CAP')][AddLocalizationIf({not1('spec_steady')}, 'SPEC_BOOM_STEADY')][AddLocalizationIf({not1('spec_fin_boom')}, 'SPEC_BOOM_FIN')][AddLocalizationIf({not1('spec_boom_rule')}, 'SPEC_BOOM_RULE')]\\n$TOOLTIP_DELIMITER$\\nThe bigger a good's share of our [concept_market], the more its boom adds. Nothing during a [concept_spec_financial_panic]\\n#weak [GetTechnology('stock_exchange').GetName], [GetTechnology('investment_banks').GetName] and [GetTechnology('modern_financial_instruments').GetName] make it bigger#!"
 SPEC_BOOM_CAP: "\\nCapped at #v +{k['CONF_BOOM_MAX']}#! before anything below"
 SPEC_BOOM_STEADY: "\\n#v x[{sv('spec_steady')}|2]#! from Manor Houses"
 SPEC_BOOM_FIN: "\\n#v x[{sv('spec_fin_boom')}|2]#! from finance technologies"
 SPEC_BOOM_RULE: "\\n#v x[{sv('spec_boom_rule')}|2]#! from Market Volatility"
 SPEC_DRIVER_CRASH: "Ended Booms"
 SPEC_DRIVER_CRASH_TT: "#header Ended Booms: [{v('spec_c_crash')}|+=2]#!\\nBiggest one last month: #v [{P}.Var('spec_crashed').GetGoods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_crash_raw')}|+=2] from how big the ended booms were\\n{cond_row(ratio('spec_c_crash', 'spec_crash_raw'))}[AddLocalizationIf(Not(GreaterThan_CFixedPoint({v('spec_c_crash')}, {fx(-k['CONF_CRASH_MAX'])})), 'SPEC_CRASH_CAP')]\\n$TOOLTIP_DELIMITER$\\nBigger booms, and goods with more of our [concept_market], hurt more\\n#weak [GetTechnology('mutual_funds').GetName] softens it, [GetTechnology('modern_financial_instruments').GetName] makes it worse#!"
 SPEC_CRASH_CAP: "\\nCapped at #N -{k['CONF_CRASH_MAX']}#! a month"
 SPEC_DRIVER_FOREIGN: "Foreign Panics"
 SPEC_FOREIGN_HIT: "\\n#N -{k['CONTAGION']}#! base hit from a [concept_spec_foreign_panic]\\n#v x[{v('spec_fh_size')}|2]#! how big their economy is next to ours\\n#v x[{v('spec_fh_tie')}|2]#! how closely we are tied ([concept_spec_market_tie])\\n#v x[{v('spec_fh_reach')}|2]#! how important they are ([concept_rank])[AddLocalizationIf({not1('spec_foreign_loss_mult')}, 'SPEC_FOREIGN_UNSTD')]"
 SPEC_FOREIGN_UNSTD: "\\n#v x[{sv('spec_foreign_loss_mult')}|2]#! because we have no [GetTechnology('currency_standards').GetName]"
 SPEC_FOREIGN_FLIGHT: "\\n[{v('spec_c_flight')}|+=2] from [concept_spec_capital_flight]"
 SPEC_DRIVER_FOREIGN_TT: "#header Foreign Panics: [{v('spec_c_foreign')}|+=2]#!\\nLatest: #v [{P}.Var('spec_foreign_src').GetCountry.GetName]#!\\n$TOOLTIP_DELIMITER$[AddLocalizationIf({nonzero(f"Subtract_CFixedPoint({v('spec_c_foreign')}, {v('spec_c_flight')})", 0.01)}, 'SPEC_FOREIGN_HIT')][AddLocalizationIf({nonzero(v('spec_c_flight'), 0.01)}, 'SPEC_FOREIGN_FLIGHT')]\\n$TOOLTIP_DELIMITER$\\n#title [concept_spec_market_tie]#!\\n#italic How much of a tied country's panic reaches us through each kind of tie. They do not add up. When several panics reach us in a month, only the biggest hit counts.#!\\nSame [concept_market]: #v [{sv('spec_tie_market')}|%0]#!\\nSubject or Overlord: #v {k['LINKS']['subject']:.0%}#!\\nForeign Investment Rights: #v [{sv('spec_tie_investment')}|%0]#!\\nHeavy Trade Between Markets: #v [{sv('spec_tie_trade')}|%0]#!\\nForeign Ownership of Our Economy: up to #v {k['LINKS']['owned']:.0%}#!\\n$TOOLTIP_DELIMITER$\\n#weak A [concept_great_power]'s panic hits us in full, a major power's by half, a small country's barely. A panic we caught from abroad does not spread on.#!"
 SPEC_DRIVER_TURMOIL: "War and Unrest"
 SPEC_DRIVER_TURMOIL_TT: "#header War and Unrest: [{v('spec_c_turmoil')}|+=2]#!$SPEC_ITEMS_TURMOIL$\\n$TOOLTIP_DELIMITER$\\nEach [concept_war] ([concept_spec_war_news]): #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! a month\\nAll wars together: #N {k['WAR_ALL_MIN']:g}#! to #P +{k['WAR_ALL_MAX']:g}#! a month\\nA [concept_diplomatic_play] that is not war yet: #N -{k['PLAY_TURMOIL']:g}#! a month\\nTreasury running dry: up to #N -{k['BROKE_COST']:g}#! a month, starting #v {k['BROKE_WEEKS']}#! weeks before [concept_bankruptcy]\\n[concept_default]: #N -5#! a month\\n[concept_revolution]: #N -2#! a month\\n\\n#instruction Hover over a figure to see its causes#!"
 SPEC_DRIVER_MOOD: "Market Mood"
 SPEC_DRIVER_MOOD_TT: "#header Market Mood: [{v('spec_c_mood')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_mood_shift')}|+=2] from this month's random swing\\n[Subtract_CFixedPoint({v('spec_c_mood')}, {v('spec_mood_shift')})|+=2] left over from last month\\n$TOOLTIP_DELIMITER$\\n#weak Swings at random each month, up to #v {k['MOOD_SHOCK']:g}#! either way. #v {k['MOOD_KEEP']:.0%}#! of it carries into next month.{' Companies with high [concept_prosperity] lift it once our [concept_spec_exchange] is #v National#!.' if __import__('centres').LEAN else ''}#!"
 SPEC_DRIVER_DRIFT: "Return to Baseline"
 SPEC_DRIVER_DRIFT_TT: "#header Return to Baseline: [{v('spec_c_recover')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n[Divide_CFixedPoint({v('spec_c_recover')}, Divide_CFixedPoint({sv('spec_recover_pct')}, {fx(100)}))|+=1] how far we are from [concept_spec_baseline] (#v {k['CONF_START']}#!)\\n#v x[Divide_CFixedPoint({sv('spec_recover_pct')}, {fx(100)})|%1]#! of the gap closes each month\\n$TOOLTIP_DELIMITER$\\n#weak [GetTechnology('macroeconomics').GetName] makes this half again as fast#!"
 SPEC_DRIVER_TIGHT: "Tight Credit"
 SPEC_DRIVER_GROWTH: "Growth"
 SPEC_DRIVER_GROWTH_TT: "#header Growth: [{v('spec_c_growth')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n#v [{v('spec_growth')}|=+%1]#! [concept_gdp] growth compared with recent months\\n#v {k['GROWTH_NORMAL']:.0%}#! growth counts as normal and changes nothing\\n$TOOLTIP_DELIMITER$\\n#weak [concept_spec_market_confidence] moves #v {k['GROWTH_K'] / 100:g}#! a month for each #v 1%#! faster or slower than normal, up to #v {k['GROWTH_MAX']:g}#! either way#!"
 SPEC_DRIVER_BUSINESS: "Business Mood"
 SPEC_DRIVER_BUSINESS_TT: "#header Business Mood: [{v('spec_c_business')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\nIndustrialists' [concept_approval]: #v [{sv('spec_ind_approval')}|0]#!\\n\\n{business_lines()}"
 SPEC_DRIVER_TIGHT_TT: "#header Tight Credit: [{v('spec_c_tight')}|+=2]#!\\n$TOOLTIP_DELIMITER$\\n#v [Divide_CFixedPoint({v('spec_c_tight')}, {fx(-tight_pull)})|1]#! of [concept_spec_market_confidence] above #v {tight_from}#!\\n#N -{tight_pull:.0%}#! of that a month, from [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]\\n$TOOLTIP_DELIMITER$\\n#weak Cools a boom slowly over months instead of all at once#!"
 concept_spec_market_conditions: "Market Conditions"
 concept_spec_market_conditions_desc: "$concept_spec_market_conditions$ are how hot the market is when a [concept_spec_boom_end] comes. They decide how much [concept_spec_market_confidence] the ending costs. The higher $concept_spec_market_confidence$ is at the time, the bigger the loss. At #v {k['CONF_START']:g}#! they do nothing. Financial Districts, Manor Houses and finance technologies also change them."
 concept_spec_baseline: "Baseline Confidence"
 concept_spec_baseline_desc: "$concept_spec_baseline$ is the level, #v {k['CONF_START']}#!, to which [concept_spec_market_confidence] returns when left alone, from above or below. The further it has strayed, the faster it returns."
 concept_spec_market_mood: "Market Mood"
 concept_spec_market_mood_desc: "$concept_spec_market_mood$ is the swing in investors' feelings with no single cause. Each month it shifts by chance, by up to #v {k['MOOD_SHOCK']:g}#! either way, and #v {k['MOOD_KEEP']:.0%}#! of it carries over, so good and bad spells last a while before they fade."
 concept_spec_market_tie: "Market Tie"
 concept_spec_market_tie_desc: "A $concept_spec_market_tie$ is how closely one [concept_country] follows another's [concept_market]. It sets how much of a [concept_spec_financial_panic] passes between them.\\n\\nOwnership counts once a country owns #v {k['OWNED_FROM']:.0%}#! of the other's [concept_gdp], and is strongest at #v {k['OWNED_FULL']:.0%}#!. [GetLawType('law_free_trade').GetName] strengthens the trade tie and other trade policies weaken it. [GetTechnology('international_exchange_standards').GetName] strengthens market and investment ties. An [concept_embargo] cuts the trade tie."
 concept_spec_capital_flight: "Capital Flight"
 concept_spec_capital_flight_desc: "When a [concept_spec_financial_panic] begins, money flees to safety. {flight_who} gains up to #P +[GetPlayer.MakeScope.ScriptValue('spec_flight_gain_max')|0]#! [concept_spec_market_confidence] if it is at peace, at #v {BAND_NAMES[2]}#! or better, and not tied to the country in panic. [GetTechnology('international_trade').GetName] and [GetTechnology('international_exchange_standards').GetName] raise the gain.{flight_more}"
 concept_spec_war_news: "War News"
 concept_spec_war_news_desc: "Investors follow a [concept_war] month by month. $concept_spec_war_news$ moves [concept_spec_market_confidence] each month by how it is going. [concept_casualties], [concept_blockade], [concept_devastation], falling [concept_gdp] and a long war lower it, while winning [Concept('concept_battle','$concept_battles$')] and holding enemy land raise it. Each war moves it by #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! per month, and all wars together by #N {k['WAR_ALL_MIN']:g}#! to #P +{k['WAR_ALL_MAX']:g}#!."
"""
