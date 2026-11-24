"""The Finance window (Exchange, Speculation, Banking and Rankings tabs) and its loc.

generate.information_panel_bar hosts the window and its side bar button (tab_type). Everything here is built from vanilla pieces: entry backgrounds, headers, collapsible section
headers, the round progress pie, progress bars with markers, the budget panel's tax level control and
investment pool row, graph frames and the market panel's goods filters, goods tile, price and sparkline.

Order: where confidence stands, what the player can do about it (credit, rescue), which goods are exposed,
then the detail (what moved it, history, capital) in sections that fold away.
"""

import calc
import companies
import credit_ai
import cycle
import diplomacy
import economy
import icons
import levers
import leverage
import market_visual
from sectors import GROUPS
CATEGORIES = tuple(GROUPS)
import vanilla_ties

P = "Country.MakeScope"  # the player, or the owner of a market that isn't theirs (generate.market_panel)
W = 540  # vanilla's @panel_width: rows and blocks; headers keep vanilla's own size (554), tax_exp_frame rows 530
BAR_W = W - 40  # every full-width bar and scale in the window, 20 in from each side

# confidence tiers: key, from, to
TIERS = [("panic", 0, 20), ("wary", 20, 40), ("steady", 40, 60), ("buoyant", 60, 80), ("mania", 80, 100)]
BARS = "gfx/interface/progressbar"
BAR_H, RISK_TAG_W, RISK_TAG_H = 22, 60, 16  # the confidence bar, and the Risk tag's row under it
SCALE_H = 22 + BAR_H + RISK_TAG_H  # tier names, the bar, the Risk tag's row (was 44, before the tag moved under the bar)
BAR_TONE = 0.6 / 171  # a map colour (0-255) to a tint of progressbar_white (mean grey 171) as deep as vanilla's coloured fills
WHITE = "gfx/interface/progressbar/progressbar_white.dds"
FLAT = "gfx/interface/graph/white.dds"
CLEAR = "gfx/interface/icons/generic_icons/transparent.dds"
# a bar's fill slides to a new value rather than snapping, as vanilla's bars do (progressbar_properties,
# progressbars.gui:35, with progressbar_changed_animation), slower than vanilla's half second: these values change
# once a month; 6 seconds (was 1.5) keeps the bar gliding for most of a month at normal speed
SLIDE = """skip_initial_animation = yes
animate_negative_changes = yes
state = {
	name = progress_changed
	using = Animation_Curve_Default
	duration = 6
}
"""
# and the monthly figures behind the bars that slide reach each month's figure in GLIDE weekly steps (journal's
# Market Confidence, interest_board's Investor Interest, rivals' contests), so a bar creeps through the month
GLIDE = 4
ICONS = "gfx/interface/icons/generic_icons"


def fx(n):
    return f"'(CFixedPoint){n}'"


def v(name, default=0):
    return f"{P}.Var('{name}').GetValueWithDefault({fx(default)})"


def sv(name):
    return f"{P}.ScriptValue('{name}')"


def share_sq(name, weight):  # War Risk's part from a share: weight x share squared (economy.MONTHLY)
    return f"Multiply_CFixedPoint(Multiply_CFixedPoint({v(name)}, {v(name)}), {fx(weight)})"


def rounded(value, digits):
    """value rounded to digits decimals (of a percent, digits + 2), half away from zero. Victoria's number formats
    truncate the rest; generate.write rounds every loc number this way, GUI text calls it itself."""
    scale = fx(10 ** digits)
    half = f"Select_CFixedPoint(LessThan_CFixedPoint({value}, {fx(0)}), {fx(-0.5)}, {fx(0.5)})"
    return f"Divide_CFixedPoint(IntToFixedPoint(FixedPointToInt(Add_CFixedPoint(Multiply_CFixedPoint({value}, {scale}), {half}))), {scale})"


def rounded_tenth(value):
    return rounded(value, 1)


MONTHS = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "SPEC_DATE_MAY", "JUNE",  # vanilla has no May key: MAY is the Maya tag
          "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")
MONTH_START = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def long_date(day):
    """day, counted as game_date counts (year x 365 + day of the year, no leap years), written as vanilla's
    DATE_FORMATTING_LONG with vanilla's month names. TimeKeeper.GetCurrentDateWithDiff only gives the short 1851.2.1.
    The year is printed as century and rest, so no number format can add a thousands separator."""
    year = f"FixedPointToInt(Divide_CFixedPoint(Add_CFixedPoint({day}, {fx(0.01)}), {fx(365)}))"
    doy = f"Subtract_CFixedPoint({day}, Multiply_CFixedPoint(IntToFixedPoint({year}), {fx(365)}))"
    month, start = f"'{MONTHS[-1]}'", fx(MONTH_START[-1])
    for name, first, nxt in reversed(list(zip(MONTHS, MONTH_START, MONTH_START[1:]))):
        before = f"LessThan_CFixedPoint({doy}, {fx(nxt)})"
        month, start = f"SelectLocalization({before}, '{name}', {month})", f"Select_CFixedPoint({before}, {fx(first)}, {start})"
    dom = f"FixedPointToInt(Add_CFixedPoint(Subtract_CFixedPoint({doy}, {start}), {fx(1.01)}))"
    century = f"FixedPointToInt(Divide_CFixedPoint(Add_CFixedPoint(IntToFixedPoint({year}), {fx(0.01)}), {fx(100)}))"
    rest = f"Subtract_CFixedPoint(IntToFixedPoint({year}), Multiply_CFixedPoint(IntToFixedPoint({century}), {fx(100)}))"
    pad = f"[AddLocalizationIf(LessThan_CFixedPoint({rest}, {fx(10)}), 'SPEC_DATE_ZERO')]"
    return f"[{dom}] [{month}], [{century}]{pad}[FixedPointToInt(Add_CFixedPoint({rest}, {fx(0.01)}))]"  # callers add #v


def expiry_date(day, scope=P):
    return long_date(day)


def gt(a, b=0):
    return f"GreaterThan_CFixedPoint({a}, {fx(b)})"


CONF = v("spec_conf", 55)
# what the bar, ring, stage icon and figure show: spec_conf_shown glides weekly to each month's figure (journal.GLIDE);
# tooltips keep the real one
SHOWN = f"{P}.Var('spec_conf_shown').GetValueWithDefault({CONF})"
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


def heads(cols, w=W, visibility=None):
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
    visibility = visibility or {}
    def visible_line(key):
        return f'	visible = "[{visibility[key]}]"\n' if key in visibility else ""

    cells = "".join(f"""sort_button = {{
{visible_line(key)}	position = {{ {x} 0 }}
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
CHART_H, COL_W, COL_GAP = 100, 9, 1  # a pixel a point; COL_W for charts.py and the journal's charts
CHART_W = BAR_W - 110  # the confidence history, from the card rows' 110 to their end
GOLD, BLUE, RED = "0.80 0.62 0.28", "0.30 0.52 0.66", "0.74 0.24 0.20"  # as the bar's gold, default and bad fills
HIST_MID = 50  # the chart's middle line: gold above, blue below (SPEC_HISTORY_TT)


def history_chart(width=CHART_W):
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
    # the columns share the width, so the chart ends where the rows above it do (CHART_W: 10 or 11 pixels each)
    x = lambda i: round(i * (width + COL_GAP) / HISTORY)
    cols = "".join(f"""widget = {{
	position = {{ {x(HISTORY - n)} 0 }}
	size = {{ {x(HISTORY - n + 1) - x(HISTORY - n) - COL_GAP} {CHART_H} }}
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
	size = {{ {width} {CHART_H} }}
{ind(lines + cols, 1)}}}
"""




PANIC_SLICES = 100  # the panic zone's hover in 1% slices


def panic_hover(width):
    """The confidence bar's hover split at the panic line: the panic zone shows the Panic Threshold's breakdown, the
    rest the bar's own tooltip. Last in the bar, over the markers' full-width progressbars, which would otherwise take
    the hover. The zone is slices of the bar, each shown while wholly left of the line: a stretch factor split (hbox)
    kept its first sizes and put the edge far right of the line, and a widget hung off the line's marker would reach
    past the bar's left edge over the window beside it. Reads the threshold stored each month (levers.UI_CACHE)."""
    at = f"Add_CFixedPoint({v('spec_c_panic_at', 25)}, '(CFixedPoint)0.5')"  # and the line itself, half a point past it
    x = lambda i: round(i * width / PANIC_SLICES)
    slices = "".join(f"\twidget = {{\n\t\tposition = {{ {x(i)} 0 }}\n\t\tsize = {{ {x(i + 1) - x(i)} 100% }}\n"
                     f"\t\tvisible = \"[GreaterThanOrEqualTo_CFixedPoint({at}, {fx(100 * (i + 1) / PANIC_SLICES)})]\"\n"
                     f"\t\ttooltip = \"SPEC_PANIC_LINE_TT\"\n\t}}\n" for i in range(PANIC_SLICES))
    return ("### hover: the rest, then the panic zone over it\nwidget = {\n\tsize = { 100% 100% }\n"
            "\ttooltip = \"SPEC_CARD_BAR_TT\"\n" + slices + "}\n")


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
    """Confidence filling from the left, as the mod's other bars do (the user found a fill growing out of the middle
    read as a needle), in the map mode's colour for our stage as the ring is (icons.bars). Both ends are dangers, so
    the Panic and Mania segments are tinted red. The fill end has vanilla's glow and, while confidence moves, the
    changed value chevrons."""
    import interest_list as il  # imports this module
    seg = width / 5
    # the tier confidence sits in is bold; during a panic only the lowest one can be
    labels = "".join(f"""textbox = {{
	size = {{ {int(seg)} 20 }}
	position = {{ {int(i * seg)} 0 }}
	align = center|nobaseline
	using = fontsize_small
	fontsize_min = 10
	text = "[SelectLocalization({tier_test(SHOWN, lo, hi) if i == 0 else f'And(Not({IN_PANIC}), {tier_test(SHOWN, lo, hi)})'}, 'SPEC_TIER_{key.upper()}_ON', 'SPEC_TIER_{key.upper()}')]"
	tooltip = "SPEC_TIER_{key.upper()}_TT"
}}
""" for i, (key, lo, hi, *_) in enumerate(TIERS))

    import journal  # imports this module
    # the end's glow in the stage's own colour at full strength, a lighter shade of the fill (white, it read as a
    # separate pale strip)
    lit = lambda stage: " ".join(f"{int(ch) / 255:.3f}" for ch in journal.MAP_COLORS[stage].strip("rgb{} ").split())
    glow = lambda stage: f"""icon = {{
	size = {{ 30 100% }}
	widgetanchor = right
	alpha = 0.7
	color = {{ {lit(stage)} 1 }}
	texture = "{BARS}/progressbar_white_glow.dds"
	icon = {{
		size = {{ 3 100% }}
		parentanchor = right
		color = {{ {lit(stage)} 1 }}
		texture = "{BARS}/progressbar_white_glow_line.dds"
	}}
}}
"""
    # one fill a stage, only ours shown (the ring's test): vanilla's white fill in the stage's map mode colour, as
    # vanilla tints it ("should always have a scripted color"), as deep as vanilla's own coloured fills (BAR_TONE)
    rgb = stage_rgb
    fills = "".join(f"""progressbar = {{
	size = {{ 100% 100% }}
	visible = "[EqualTo_CFixedPoint({P}.ScriptValue('spec_stage'), {fx(n)})]"
	progresstexture = "{BARS}/progressbar_white.dds"
	noprogresstexture = "{CLEAR}"
	color = {{ {rgb(stage)} 1 }}
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	using = progressbar_texture_properties
{ind(SLIDE, 1)}	min = 0
	max = 100
	value = "[FixedPointToFloat({SHOWN})]"
	marker = {{
		widget = {{
			size = {{ 100% 100% }}
{ind(glow(stage), 3)}		}}
	}}
}}
""" for n, stage in journal.STAGES)
    # clipped to the bar: the end's glow reaches left of the fill's end, past the bar at low confidence
    fills = f"widget = {{\n\tsize = {{ 100% 100% }}\n\tscissor = yes\n{ind(fills, 1)}}}\n"
    # while confidence moves, the changed value chevrons run only through the lit part of the tier it sits in, as
    # the Investor Interest bars run theirs (interest_list.tier_overlay): a clear bar per tier, clipped to its segment
    fills += "".join(f"""widget = {{
	position = {{ {int(i * seg)} 0 }}
	size = {{ {int(seg)} 100% }}
	visible = "[{tier_test(SHOWN, lo, hi)}]"
	scissor = yes
	progressbar = {{
		size = {{ 100% 100% }}
		progresstexture = "{CLEAR}"
		noprogresstexture = "{CLEAR}"
{ind(SLIDE, 2)}		min = {lo}
		max = {hi}
		value = "[FixedPointToFloat({SHOWN})]"
		marker = {{
			widget = {{
				size = {{ 100% 100% }}
{ind(il.chevrons(CONF_UP, CONF_DOWN, 0.25, "right"), 4)}			}}
		}}
	}}
}}
""" for i, (key, lo, hi, *_) in enumerate(TIERS))
    zones ="".join(f"""icon = {{
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
	visible = "[{tier_test(SHOWN, lo, hi) if i == 0 else f'And(Not({IN_PANIC}), {tier_test(SHOWN, lo, hi)})'}]"
	texture = "{BARS}/progressbar_active_level.dds"
	spriteType = Corneredstretched
	spriteborder = {{ 6 6 }}
	texture_density = 2
}}
""" for i, (key, lo, hi, *_) in enumerate(TIERS))
    return f"""widget = {{
	size = {{ {width} {SCALE_H} }}
{ind(labels, 1)}	widget = {{
		size = {{ {width} {BAR_H} }}
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
		### where confidence would fall if every risk struck now: vanilla's white glow line (Panic's is solid red; a
		### dark edge round it read as a black stripe on the fill); its tag in a row under the bar, centred on the
		### line, so it never meets Panic's tag inside the bar whichever side of the Panic line it falls
		progressbar = {{
			size = {{ 100% 100% }}
			visible = "[{RISKS_SHOWN}]"
			progresstexture = "{CLEAR}"
			noprogresstexture = "{CLEAR}"
			min = 0
			max = 100
			value = "[FixedPointToFloat({RISK_FLOOR})]"
			marker = {{
				widget = {{
					size = {{ 100% 100% }}
					icon = {{
						position = {{ -1 0 }}
						size = {{ 2 100% }}
						texture = "{BARS}/progressbar_white_glow_line.dds"
					}}
					textbox = {{  # no tooltip: panic_hover lies over the bar, its tooltip says where risks would leave it
						position = {{ -{RISK_TAG_W // 2} {BAR_H} }}
						size = {{ {RISK_TAG_W} {RISK_TAG_H} }}
						align = center|nobaseline
						using = fontsize_small
						text = "SPEC_RISK_TAG"
					}}
				}}
			}}
		}}
{ind(panic_hover(width), 2)}	}}
}}
"""


FRESH = f"LessThan_CFixedPoint({v('spec_conf', -1)}, {fx(0)})"  # before the first monthly update
PANIC_LEFT, PANIC_LEN = v("spec_panic", 0), v("spec_panic_len", 1)
CARD_X = (W - BAR_W) // 2  # the card's inner margin: the scale and the risk rows start here
LABEL_W = 104  # the card rows' labels, short of the chips at 110 (German "Pressures" ran under them)
TEXT_X = 160  # the card's text column, right of the ring


XS_MAX, XS_ALERT = 300, 10  # journal.EXCESS_MAX, BUBBLE_ALERT (journal imports this module)
XS = v("spec_heat")
XS_HOT = f"GreaterThanOrEqualTo_CFixedPoint({sv('spec_burst_now')}, {fx(XS_ALERT)})"
XS_RISK = gt(sv("spec_burst_now"), 0.05)  # was spec_heat set: at exactly the threshold heat is 0 and the chip read -0.0
XS_NUM_W = 70  # the icon and figure left of the bar, where the chip rows above put theirs

# the Risks row's chips, each counted only while its chip shows; war and default count one month
RISK_PARTS = [("BOOMS", BAR_RISK, BAR_GAP), ("SRC", SRC_RISK, SRC_HIT), ("WAR", WAR_RISK, v("spec_war_risk")),
              ("DEFAULT", DEFAULT_RISK, fx(economy.DEFAULT_COST)), ("BUBBLE", XS_RISK, sv("spec_burst_now"))]
RISK_SUM = fx(0)
for _, shows, cost in RISK_PARTS:
    RISK_SUM = f"Add_CFixedPoint({RISK_SUM}, Select_CFixedPoint({shows}, {cost}, {fx(0)}))"
RISK_FLOOR = f"Max_CFixedPoint(Subtract_CFixedPoint({CONF}, {RISK_SUM}), {fx(0)})"  # where all of them striking leaves it
RISKS_SHOWN = f"GreaterThanOrEqualTo_CFixedPoint({RISK_SUM}, {fx(0.5)})"


def excess_row():
    """Speculative Excess, the bubble a long boom builds: gold while it builds, red once a fall would cost
    XS_ALERT or more confidence, its figure beside it as vanilla's involvement bar. As vanilla's will_increase and
    will_decrease bars, a paler strip shows next month's change: red where it grows, green where it shrinks."""
    nxt = v("spec_c_xs_next")  # stored by spec_update_levers (levers.UI_CACHE): the bar read the script value every frame
    to = f"Add_CFixedPoint({XS}, {nxt})"
    grows, shrinks = (f"And({XS_RISK}, {op}_CFixedPoint({nxt}, '(CFixedPoint)0'))" for op in ("GreaterThan", "LessThan"))
    now = f"Min_CFixedPoint({XS}, {to})"  # the bar itself stops where a shrink leaves it
    bw = W - 2 * CARD_X - 110 - XS_NUM_W
    bar = framed_bar(bw, 22, fill("progressbar_bad", XS_MAX, to, grows, alpha=0.45) + fill("progressbar_green", XS_MAX, XS, shrinks, alpha=0.6)
                     + fill("progressbar_gold", XS_MAX, now, f"Not({XS_HOT})") + fill("progressbar_bad", XS_MAX, now, XS_HOT))
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
	textbox = {{
		position = {{ 110 0 }}
		size = {{ {XS_NUM_W} 30 }}
		parentanchor = vcenter
		align = left|nobaseline
		raw_text = "@spec_speculative_excess! #v [{XS}|0]#!"
		tooltip = "SPEC_XS_TT"
	}}
	widget = {{
		position = {{ {110 + XS_NUM_W} 0 }}
		size = {{ {bw} 22 }}
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


PRESSURE_STEP = 0.01  # the smallest change visible in the driver breakdown


def chip_rows():
    """The card's Pressures and Risks rows, also shown in the journal entry (journal.widgets)."""
    return (card_row("SPEC_PRESSURES", "SPEC_PRESSURES_TT", "".join(card_chip(f"SPEC_CHIP_{n}", nonzero(v(f"spec_p{n}"), PRESSURE_STEP), icon)
                                                                  for n, (_, icon, _) in enumerate(PRESSURES, 1)))
            + card_row("SPEC_RISKS", "SPEC_RISKS_TT", card_chip("SPEC_RISK_1", BAR_RISK, "crash") + card_chip("SPEC_RISK_2", SRC_RISK, "panic_risk")
                       + card_chip("SPEC_RISK_3", WAR_RISK, "war_risk") + card_chip("SPEC_RISK_4", DEFAULT_RISK, "default_risk")
                       + card_chip("SPEC_RISK_5", XS_RISK, "bubble_risk")))


def stage_icons(size):
    """The state's icon, centred: below the wary line without a panic it stays wary."""
    return "".join(f"""icon = {{
	size = {{ {size} {size} }}
	parentanchor = center
	visible = "[{vis}]"
	texture = "{icons.path(f'state_{key}')}"
}}
""" for key, vis in [("panic", IN_PANIC), ("wary", f"And(Not({IN_PANIC}), {tier_test(SHOWN, 0, TIERS[1][2])})")]
        + [(key, f"And(Not({IN_PANIC}), {tier_test(SHOWN, lo, hi)})") for key, lo, hi in TIERS[2:]])


def stage_rgb(stage):
    """A stage's map mode colour as a tint of progressbar_white, as deep as vanilla's coloured fills (BAR_TONE)."""
    import journal  # imports this module
    return " ".join(f"{min(1, int(ch) * BAR_TONE):.3f}" for ch in journal.MAP_COLORS[stage].strip("rgb{} ").split())


# the icon and up to "100", as tight as vanilla's items. The state icons draw at 30 in vanilla's 26 slot: their art
# leaves more empty edge than vanilla's icons, and at 26 looked smaller and further from the figure
TOPBAR_W = 52
TOPBAR_ICON = 22  # the row's icons, vanilla's 26 smaller so the row with our item in it is less cramped


def topbar_item():
    """The topbar's Market Confidence, last in its second row and built as vanilla's GDP there: the state's icon and
    the figure. Its tooltip is the confidence card's monthly change, with the confidence and leverage histories under
    it as GDP's has its graph. The first row has no room: the alerts sit at a fixed place right of the topbar.
    A click opens Finance on Speculation."""
    import charts  # imports this module
    shown =f"And({ACTIVE}, Not({FRESH}))"
    plot_w = HISTORY * (COL_W + COL_GAP) - COL_GAP  # as Leverage History's columns, so the two charts line up
    ends = lambda y: f"""textbox = {{
	position = {{ {charts.AXIS_W} {y} }}
	autoresize = yes
	fontsize = 12
	text = "SPEC_LHIST_OLDEST"
}}
textbox = {{
	position = {{ {charts.AXIS_W + plot_w - 60} {y} }}
	size = {{ 60 16 }}
	align = right|nobaseline
	fontsize = 12
	text = "SPEC_LHIST_NOW"
}}
"""
    # each chart as vanilla's graphs in these tooltips (v3_plotline): on paper, under its name centred in #title
    paper = lambda key, body: f"""flowcontainer = {{
	direction = vertical
	margin = {{ 10 0 }}
	margin_bottom = 8
	background = {{
		using = paper_bg
	}}
	textbox = {{
		parentanchor = hcenter
		autoresize = yes
		align = hcenter|nobaseline
		margin_top = 10
		margin_bottom = 10
		default_format = "#title"
		text = "{key}"
	}}
{ind(body, 1)}}}
"""
    conf_chart = paper("SPEC_TOP_CONF_HIST", f"""widget = {{
	size = {{ {charts.AXIS_W + plot_w + charts.PANIC_W} {CHART_H + 18} }}
	widget = {{
		position = {{ {charts.AXIS_W} 0 }}
		size = {{ {plot_w} {CHART_H} }}
{ind(history_chart(plot_w), 2)}	}}
{ind(ends(CHART_H + 2), 1)}}}
""")
    lev_chart = paper("SPEC_TOP_LEV_HIST", f"""widget = {{
	size = {{ {charts.AXIS_W + plot_w + charts.PANIC_W} {charts.LEV_H + charts.LEV_PAD + 18} }}
{ind(charts.lev_scale(leverage.RUIN, sv('spec_credit_limit')), 1)}{ind(ends(charts.LEV_H + charts.LEV_PAD + 2), 1)}}}
""") if leverage.ON else ""
    tt = f"[SelectLocalization(Not({ACTIVE}), 'SPEC_TOP_OFF_TT', SelectLocalization({FRESH}, 'SPEC_TOP_FRESH_TT', 'SPEC_TOP_TT'))]"
    # the button twice, as the side bar's Finance button: once the journal entry has saved itself, the click also opens
    # its panel under the window for its map mode (JE_OK, JE_PANEL); both share the template
    click = lambda je: (f'visible = "[{JE_OK if je else f"Not({JE_OK})"}]"\n' + (JE_CONTEXT + "\n" if je else "")
                        + open_clicks("booms", journal_map=je) + (f'onclick = "{JE_PANEL}"\n' if je else ""))
    item = f"""### MARKET CONFIDENCE (Speculative Markets)
widget = {{
	size = {{ {TOPBAR_W} 30 }}
	button = {{
		using = spec_topbar_confidence
{ind(click(True), 2)}	}}
	button = {{
		using = spec_topbar_confidence
{ind(click(False), 2)}	}}
}}
"""
    return f"""# the topbar's Market Confidence (market_tab.topbar_item): all of its button but the click
template spec_topbar_confidence {{
	size = {{ {TOPBAR_W} 30 }}
	tooltip = "{tt}"
	tooltipwidget = {{
		TooltipWidgetType = {{
			blockoverride "tooltip_content_after" {{
				flowcontainer = {{
					direction = vertical
					visible = "[{shown}]"
					spacing = 10
					margin_top = 10
{ind(conf_chart + lev_chart, 5)}				}}
			}}
		}}
	}}
	using = tooltip_below
	enabled = "[GetMetaPlayer.GetPlayedOrObservedCountry.IsValid]"

	flowcontainer = {{
		parentanchor = vcenter
		spacing = 2
		widget = {{
			size = {{ {TOPBAR_ICON} {TOPBAR_ICON} }}  # not @secondary_icon_size: the template sits above its definition
			parentanchor = vcenter
{ind(stage_icons(round(TOPBAR_ICON * 30 / 26)), 3)}		}}
		textbox = {{
			parentanchor = vcenter
			visible = "[{shown}]"
			raw_text = "#variable [{SHOWN}|0]#!"
			autoresize = yes
			align = left|nobaseline
			fontsize_min = 12
		}}
	}}
}}
""", item


def mood_card():
    # the ring fills with confidence in the map mode's colour for our stage (icons.rings)
    import journal  # imports this module
    gauge = "".join(f"""		round_progress_default = {{
			size = {{ 112 112 }}
			parentanchor = center
			visible = "[EqualTo_CFixedPoint({P}.ScriptValue('spec_stage'), {fx(n)})]"
			texture = "{icons.DIR}/ring_{stage}.dds"
			value = "[{share(SHOWN)}]"
		}}
""" for n, stage in journal.STAGES)
    state_icons = ind(stage_icons(90), 2)
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
		size = {{ {CHART_W} {CHART_H} }}
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
		size = {{ {W} {150 + SCALE_H + 6} }}

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
			size = {{ {W - 2 * CARD_X} {SCALE_H} }}
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
                 + fill("progressbar_default", 100, SHOWN, f"Not({IN_PANIC})") + f"widget = {{\n\tsize = {{ 100% 100% }}\n\tvisible = \"[Not({IN_PANIC})]\"\n\talwaystransparent = yes\n{ind(PANIC_ZONE_BAR, 1)}}}\n"
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
    # 2026-11-22: the bar moves as confidence's does, vanilla's end glow and, while standards move, the changed value
    # chevrons through the lit part of the level it sits in (cycle.lax_terms' total, a month's change as things stand)
    import interest_list as il  # imports this module
    total = cycle.lax_terms()[-1]
    up, down = f"GreaterThanOrEqualTo_CFixedPoint({total}, {fx(0.05)})", f"LessThanOrEqualTo_CFixedPoint({total}, {fx(-0.05)})"
    moving = "".join(f"""widget = {{
	position = {{ {seg * i} 0 }}
	size = {{ {seg} 100% }}
	visible = "[{inside(i)}]"
	scissor = yes
	progressbar = {{
		size = {{ 100% 100% }}
		progresstexture = "{CLEAR}"
		noprogresstexture = "{CLEAR}"
{ind(SLIDE, 2)}		min = {cuts[i]:g}
		max = {cuts[i + 1]:g}
		value = "[FixedPointToFloat({lax})]"
		marker = {{
			widget = {{
				size = {{ 100% 100% }}
				icon = {{
					size = {{ 30 100% }}
					widgetanchor = right
					alpha = 0.5
					texture = "{BARS}/progressbar_white_glow.dds"
				}}
{ind(il.chevrons(up, down, 0.25, "right"), 4)}			}}
		}}
	}}
}}
""" for i in range(len(cycle.LAX_WORDS)))
    # each level's tooltip on its name; the bar keeps its own (the value and its month's change)
    hover = "".join(f"""widget = {{
	position = {{ {seg * i} 24 }}
	size = {{ {seg} 22 }}
	tooltip = "SPEC_LAXL_{i}_TT"
}}
""" for i in range(len(cycle.LAX_WORDS)))
    return f"""widget = {{
	size = {{ {BAR_W} 46 }}
	parentanchor = hcenter
	tooltip = "SPEC_EFFECT_LAX_TT"
{ind(framed_bar(BAR_W, 22, fills + dividers + active + moving), 1)}{ind(names + hover, 1)}}}
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


def fill(texture, top, value, visible="", alpha=None):
    """A framed bar's fill, sliding to each new value; alpha for a paler one, as a forecast strip."""
    shown = (f'	visible = "[{visible}]"\n' if visible else "") + (f"\talpha = {alpha:g}\n" if alpha else "")
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


def trend_next(fast, slow):
    """Next month's two price averages if the price holds (generate.spec_fast_next_<g>, spec_slow_next_<g>)."""
    step = lambda avg, rate: f"Add_CFixedPoint({avg}, Multiply_CFixedPoint(Subtract_CFixedPoint({good_sv('spec_dev')}, {avg}), {fx(rate)}))"
    return step(good_var("spec_fast"), fast), step(good_var("spec_slow"), slow)
NEAR_PEAK = 0.85                # interest this close to its boom's peak is still at the top
MOVE = good_var("spec_ui_move")  # interest_board.ui_effect's monthly move: 1 rose, -1 fell, 0 neither
LEANING = [6, 5, 4, 3, 2, 1]    # spec_word lists shown as rows, hottest first, Calm (3) in the middle
WORDS = {6: "feverish", 5: "eager", 4: "keen", 3: "calm", 2: "doubtful", 1: "fleeing"}
CAT = "spec_il_sector"  # the category picked in the Speculation list (none: all)


def cat_shown(c):
    return f"Or(Not(GetVariableSystem.Exists('{CAT}')), GetVariableSystem.HasValue('{CAT}', '{c}'))"


def cat_filters():
    """One icon per sector. Selecting the active sector again restores all goods."""
    buttons = []
    for sector in CATEGORIES:
        selected = f"GetVariableSystem.HasValue('{CAT}', '{sector}')"
        no_filter = f"Not(GetVariableSystem.Exists('{CAT}'))"
        ring = f"Or({no_filter}, {selected})"
        states = []
        for active, visible, click in ((False, f"Not({selected})", f"GetVariableSystem.Set('{CAT}', '{sector}')"),
                                       (True, selected, f"GetVariableSystem.Clear('{CAT}')")):
            fade = "" if active else f'alpha = "[TransparentIfFalse({no_filter})]"'
            states.append(f"""button_icon_round_big = {{ using = tooltip_above
                size = {{ {FILTER_BTN} {FILTER_BTN} }}
                parentanchor = center
                visible = "[{visible}]"
                {fade}
                onclick = "[{click}]"
                tooltip = "SPEC_SECTOR_{sector.upper()}_TT"
                blockoverride "wood_texture" {{ texture = "gfx/interface/buttons/round_button_big_wood_map_interaction.dds" }}
                blockoverride "icon" {{ texture = "{icons.path('sector_' + sector)}" }}
                blockoverride "icon_size" {{ size = {{ {FILTER_ICON} {FILTER_ICON} }} }}
            }}""")
        buttons.append(f"""widget = {{
            size = {{ {FILTER_RING} {FILTER_RING} }}
            icon = {{ size = {{ {FILTER_RING} {FILTER_RING} }} parentanchor = center texture = "gfx/interface/backgrounds/round_frame_dec.dds"
                visible = "[{ring}]" using = default_fade_in_out }}
            {' '.join(states)}
        }}""")
    # one row: nine 44px rings fit the row's 425px
    return "flowcontainer = { parentanchor = center spacing = 3\n" + "\n".join(buttons) + "\n}\n"


# the goods filters' round buttons (cat_filters, interest_list's tier filters): vanilla's 64px ring with a 52px button
# and 40px icon, scaled down so the nine sectors fit one row
# goods_filter_button forces a 48px icon over any icon_size, so these use its parent button_icon_round_big
FILTER_RING, FILTER_BTN, FILTER_ICON, FILTER_ROW = 44, 36, 40, 50


def any_of(tests):
    out = tests[0]
    for t in tests[1:]:
        out = f"Or({out}, {t})"
    return out


def goods_filters(label, row, more=()):
    """Vanilla's filter block (market_panel.gui ~391-446) under a collapsible Filters header: one dark area, the labels
    in a column, one divider, the filter rows in a column. label and row are the second row, 64 high, under the goods
    categories; more: further (label, row, height) rows."""
    width = W - 95 - 2 * 10  # the rest of the row: the label, two spacings and the divider
    # 2026-11-21 polish: smaller rings, the sectors on one row (they took two at 64), labels centred on their rows
    sector_height = FILTER_ROW
    labels = "".join(f"""	textbox = {{
		text = "{text}"
		multiline = yes
		size = {{ 95 {height} }}
		align = right|vcenter|nobaseline
		margin_right = 10
		margin_left = 10
		fontsize = 14
	}}
""" for text, height in (("SPEC_SECTOR_FILTER_LINK", sector_height), (label, FILTER_ROW), *((l, h) for l, _, h in more)))
    rows = "".join(f"""		widget = {{
			size = {{ {width} {h} }}
{ind(r, 3)}		}}
""" for r, h in ((row, FILTER_ROW), *((r, h) for _, r, h in more)))
    body = f"""flowcontainer = {{
	minimumsize = {{ {W} -1 }}
	parentanchor = hcenter
	margin_top = 6
	margin_bottom = 6
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
			size = {{ {width} {sector_height} }}
{ind(cat_filters(), 3)}		}}
{rows}	}}
}}
"""
    # Finance has no MarketPanel context; its filters use our own selection.
    return section("FILTERS", "spec_hide_filters", body, right="SPEC_CURRENT_GOODS_FILTERS")


def goods_board(k):
    import interest_list  # imports this module
    return section("CHARTS", "spec_hide_charts_interest", __import__("charts").interest_chart() + 'widget = { size = { 1 10 } }\n' + __import__("charts").sector_chart()) + interest_list.board(k)


def level_effects():
    """Each interest level's effects, one line each as vanilla modifier tooltips list them, by level name."""
    pct = {WORDS[w]: p for w, p in companies.INTEREST_THROUGHPUT.items()}
    tp = lambda w: f"Producers' [concept_throughput]: {'#P +' if pct[w] > 0 else '#N '}{pct[w]}%#!"
    lift = ("\\nRaises [concept_spec_market_confidence] every month, more if it is a big part of our trade, but not during a "
            "[concept_spec_financial_panic]")
    end = lambda name: f"\\nIts boom ends in a [concept_spec_{name.lower()}]"
    effects = {
        "feverish": tp("feverish") + lift + end("Collapse"),
        "eager": tp("eager") + lift + end("Bust"),
        "keen": tp("keen") + end("Correction"),
        "calm": "Producers' [concept_throughput] is unchanged, and it does not lift [concept_spec_market_confidence]",
        "doubtful": tp("doubtful") + "\\nAfter a boom ends, the good stays here or lower for a while to recover",
        "fleeing": tp("fleeing") + "\\nIf a #v Feverish#! boom drops this low, it ends in a [concept_spec_collapse]",
    }
    return effects


def band_loc(k):
    """The lever column's label, and each interest word's tooltip."""
    effects = level_effects()
    # the Filters header's summary (2026-11-22): the sector, then the interest level and the sentiment when picked,
    # comma separated; the sector's short chart name when it shares the line, "All Goods" only when nothing is picked
    from interest_list import TIER, SENT_F
    has = lambda flag: f"GetVariableSystem.Exists('{flag}')"
    def by_sector(suffix):
        out = "'SPEC_IB_EMPTY'"
        for category in reversed(CATEGORIES):
            out = (f"SelectLocalization(GetVariableSystem.HasValue('{CAT}', '{category}'), "
                   f"'SPEC_SECTOR_{category.upper()}{suffix}', {out})")
        return out
    extra = f"Or({has(TIER)}, {has(SENT_F)})"
    selected = (f"SelectLocalization({has(CAT)}, SelectLocalization({extra}, {by_sector('_SHORT')}, {by_sector('')}), "
                f"SelectLocalization({extra}, 'SPEC_IB_EMPTY', 'ALL_GOODS'))")
    tier = "'SPEC_IB_EMPTY'"
    for w in range(6, 0, -1):
        tier = f"SelectLocalization(GetVariableSystem.HasValue('{TIER}', '{w}'), 'SPEC_FILTER_TIER_{w}', {tier})"
    sep = lambda before: f"SelectLocalization({before}, 'SPEC_FILTER_SEP', 'SPEC_IB_EMPTY')"
    tier_words = "".join(f' SPEC_FILTER_TIER_{w}: "{WORDS[w].capitalize()}"\n' for w in range(1, 7))
    out = (f' SPEC_CURRENT_GOODS_FILTERS: "[{selected}][AddLocalizationIf({has(TIER)}, \'SPEC_FILTER_TIER_PART\')]'
           f'[AddLocalizationIf({has(SENT_F)}, \'SPEC_FILTER_SENT_PART\')]"\n'
           f' SPEC_FILTER_TIER_PART: "[{sep(has(CAT))}][{tier}]"\n'
           f" SPEC_FILTER_SENT_PART: \"[{sep(f'Or({has(CAT)}, {has(TIER)})')}][SelectLocalization(GetVariableSystem.HasValue('{SENT_F}', 'fav'), 'SPEC_JE_FAVOURED', 'SPEC_JE_SHUNNED')]\"\n"
           ' SPEC_FILTER_SEP: ", "\n'
           f'{tier_words}'
           " SPEC_COL_LEVER: \"[concept_spec_intervention]\"\n"  # a concept link, as the Investor Interest header
           " SPEC_COL_LEVER_TT: \"#header Market Interventions#!\\n$TOOLTIP_DELIMITER$\\n"
           "#v Restrain Speculation#! pushes [concept_spec_investor_interest] down, never below #v Calm#!. "
           f"Its makers lose #N {levers.LEVER_THROUGHPUT:.0%}#! [concept_throughput] and pay a levy of #v {levers.LEVY_SHARE:.0%}#! of their output.\\n"
           "#v Encourage Investment#! pushes it up until it reaches #v Eager#!. "
           f"Its makers gain #P {levers.LEVER_THROUGHPUT:.0%}#! $concept_throughput$ and are paid a subsidy of #v {levers.SUBSIDY_SHARE:.0%}#! of their output.\\n"
           + ("#v Float a Great Issue#! raises our [concept_spec_exchange] score, and the stakes when its boom ends.\\n" if levers.ISSUE_ON else "")
           + "A confident market follows Encourage further and listens to Restrain less.\\n"
           "$TOOLTIP_DELIMITER$\\n#weak Restraining or encouraging ties up [concept_authority] while in effect, more for staples and widely traded goods.#!\"\n")
    word_of = {n: w for w, n in WORDS.items()}
    for name, desc in effects.items():
        key = f"SPEC_SEP_{name.upper()}"
        share = f"#v [{market_visual.share(word_of[name])}|%0]#! of our trade is in goods with {name.capitalize()} interest"
        out += f" {key}_TT: \"#header @spec_interest_{name}! {name.capitalize()} [concept_spec_investor_interest]#!\\n$TOOLTIP_DELIMITER$\\n{share}\\n\\n{desc}\"\n"
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
    return f"#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WHY_COND #v x[{mult}|2]#!#!#! from [concept_spec_market_conditions]"


def why_lines(var, val, k):
    """A boom's cost if it ended now, in vanilla's calculator form (BASE_VALUE_FOR_CALCULATOR): peak interest above 1,
    then each multiplier "from" its cause, as generate.spec_risk_next_<g> makes it: its ending's rate (UNWINDS), its
    trade weight, bank exposure, overbuilding and market conditions, capped at CONF_CRASH_MAX. var(n) and val(n) read spec_<n>_<good> as a variable and a
    script value."""
    sev = var("spec_sev")
    tier = (f"SelectLocalization(EqualTo_CFixedPoint({sev}, {fx(3)}), 'SPEC_WHY_END_3', "
            f"SelectLocalization(EqualTo_CFixedPoint({sev}, {fx(2)}), 'SPEC_WHY_END_2', 'SPEC_WHY_END_1'))")
    share = f"Divide_CFixedPoint({val('spec_mv')}, Max_CFixedPoint({v('spec_mv_total', 1)}, {fx(1)}))"
    capped = f"GreaterThan_CFixedPoint(Multiply_CFixedPoint({val('spec_risk_raw')}, {sv('spec_crash_scale')}), {fx(k['CONF_CRASH_MAX'])})"
    falling = f"LessThan_CFixedPoint({var('spec_hype')}, {var('spec_hprev')})"
    peak = var("spec_peak")
    bank = f"#v x[{val('spec_exp_mult')}|2]#! $SPEC_CALC_BANK_EXPOSURE$\\n"
    supply = f"#v x[{val('spec_over_mult')}|2]#! $SPEC_CALC_OVERBUILDING$\\n" if cycle.ON else ""
    return ("$SPEC_RISK_LEAD$\\n\\n"
            f"#v [Subtract_CFixedPoint({peak}, {fx(1)})|1]#! base, from how high [concept_spec_investor_interest] got\\n"
            f"[{tier}]\\n"
            f"#v x[{val('spec_weight')}|2]#! from its #v [{share}|%1]#! share of our trade, counted in full from #v {k['EXPOSURE_FULL']:.0%}#!\\n"
            + bank + supply + cond_row(sv('spec_crash_scale')) +
            f"[AddLocalizationIf({capped}, 'SPEC_WHY_CAP')][AddLocalizationIf({falling}, 'SPEC_WHY_FALLING')]")


def risk_why(g, k):
    """A Booms at Risk good's nested tooltip, which has only the country in context, so one per good."""
    return (f' SPEC_RISK_WHY_{g.upper()}: "#header [GetGoods(\'{g}\').GetName] Boom at Risk: #N -[{rounded_tenth(v(f"spec_risk_{g}"))}|1]#!#!\\n$TOOLTIP_DELIMITER$\\n'
            + why_lines(lambda n: v(f"{n}_{g}"), lambda n: sv(f"{n}_{g}"), k) + '"\n')


def why_cond(k):
    """Market Conditions, generate.spec_crash_scale's factors; the last three only when they change it, as vanilla
    leaves out what adds nothing."""
    conf =f"Divide_CFixedPoint({CONF}, {fx(k['CONF_START'])})"
    rows = [("DEPTH", "spec_depth", "Financial Districts"), ("STEADY", "spec_steady", "Manor Houses"),
            ("FIN", "spec_fin_risk", "finance technologies")]
    out = (f' SPEC_WHY_COND: "#header [concept_spec_market_conditions]: x[{sv("spec_crash_scale")}|2]#!\\n$TOOLTIP_DELIMITER$\\n'
           f"The hotter the market, the more a [concept_spec_boom_end] costs.\\n\\n"
           f"#v x[{conf}|2]#! from our [concept_spec_market_confidence] of #v [{CONF}|0]#!"
           + "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({sv(n)}, {fx(1)})), 'SPEC_WHY_COND_{key}')]" for key, n, _ in rows)
           + f"\\n$TOOLTIP_DELIMITER$\\n#weak At #v {k['CONF_START']:g}#! $concept_spec_market_confidence$ this has no effect.#!\"\n")
    out += "".join(f' SPEC_WHY_COND_{key}: "\\n#v x[{sv(n)}|2]#! from {name}"\n' for key, n, name in rows)
    # how hard interest follows the price trend, generate.spec_hype_mult and spec_hype_mult_down; Loose credit (a
    # Credit Policy above 1) speeds rising prices only
    rows = [("TECH", "spec_tech_hype", "Joint-Stock Companies"), ("DEPTH", "spec_depth", "Financial Districts"),
            ("BAND", "spec_band_gain", "[concept_spec_market_confidence] (rising prices only)")]
    if __import__("centres").ON:  # centres.HYPE_REF: the Exchange multiplies spec_hype_mult, not spec_hype_mult_down
        rows.append(("EXCH", "spec_exch_hype", "[concept_spec_exchange] (rising prices only)"))
    loose = f"GreaterThan_CFixedPoint({sv('spec_stance_hype')}, {fx(1)})"
    out += (f' SPEC_WHY_SPEED: "#header Investor Reaction#!\\n$TOOLTIP_DELIMITER$\\n'
            f'Investors react #v [{sv("spec_hype_mult")}|2]#! times as strongly as usual to rising prices, '
            f'and #v [{sv("spec_hype_mult_down")}|2]#! times to falling prices.\\n\\n'
            f"#v x[{sv('spec_law_mult')}|2]#! from Economic System\\n"
            f"#v x[{sv('spec_stance_hype')}|2]#! from [concept_spec_credit_policy][AddLocalizationIf({loose}, 'SPEC_WHY_SPEED_LOOSE')]"
            + "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({sv(n)}, {fx(1)})), 'SPEC_WHY_SPEED_{key}')]" for key, n, _ in rows)
            + "\\n$TOOLTIP_DELIMITER$\\n#weak The stronger the reaction, the faster [concept_spec_investor_interest] follows prices.#!\"\n"
            ' SPEC_WHY_SPEED_LOOSE: " (rising prices only)"\n')
    return out + "".join(f' SPEC_WHY_SPEED_{key}: "\\n#v x[{sv(n)}|2]#! from {name}"\n' for key, n, name in rows)


def not1(name):
    """A script value that changes something: rows that multiply by 1 are left out, as vanilla leaves them."""
    return f"Not(EqualTo_CFixedPoint({sv(name)}, {fx(1)}))"


SHELTERS = (("WORLD", "our World Centre [concept_spec_exchange]"), ("BC", "our [concept_spec_blue_chip] companies"),
            ("PB", "our [concept_power_bloc]"))  # what spec_catch_panic multiplies a foreign panic's hit by


def shelter_rows(prefix, *values):
    return "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({val}, {fx(1)})), '{prefix}_{key}')]" for (key, _), val in zip(SHELTERS, values))


def shelter_keys(prefix, *values):
    return "".join(f' {prefix}_{key}: "\\n#v x[{val}|2]#! from {name}"\n' for (key, name), val in zip(SHELTERS, values))


def ratio(scaled, raw):
    """What a month's sum was multiplied by, read back from the two, since the multiplier moves with confidence after."""
    return f"Divide_CFixedPoint({v(scaled)}, Min_CFixedPoint({v(raw)}, {fx(-0.001)}))"


def business_lines():
    """economy.BUSINESS in words, so the tooltip cannot drift from what the game applies."""
    def say(up):
        rows = sorted((row for row in economy.BUSINESS if (row[2] > 0) == up), key=lambda row: abs(row[1]))
        return ", or ".join(f"#{'P' if up else 'N'} {abs(val):g}#! {'while their [concept_approval] is' if i == 0 else 'at'} "
                            f"#v {at}#! or {'more' if up else 'less'}" for i, (_, at, val) in enumerate(rows))
    return f"Each month, [concept_spec_market_confidence] rises by {say(True)}. It falls by {say(False)}."


def war_why(n, k):
    """A war's calculator, in vanilla's breakdown form: what each of diplomacy.WAR_ROWS adds this month, and the reading
    behind it. Rows that add nothing are left out."""
    out = (f' SPEC_WAR_WHY_{n}: "#header [concept_war] with [{P}.Var(\'spec_war{n}\').GetCountry.GetName]: [{v(f"spec_war{n}_c")}|+=2]#!\\n'
           f"$TOOLTIP_DELIMITER$\\n#N -{k['WAR_BASE']:.2f}#! from being at war"
           + "".join(f"[AddLocalizationIf({nonzero(v(f'spec_war{n}_{key}'), 0.01)}, 'SPEC_WAR_ROW_{n}_{key.upper()}')]" for key in diplomacy.WAR_ROWS)
           + f"\\n$TOOLTIP_DELIMITER$\\n#weak A single war moves [concept_spec_market_confidence] by #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! a month. The first #v {diplomacy.WAR_GRACE_MONTHS}#! months, and a [concept_gdp] fall of up to #v {diplomacy.WAR_GDP_FREE:.0%}#!, cost nothing extra.#!\"\n")
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
                   f'#v x[{sv(f"spec_weight_{g}")}|%0]#! from its share of our trade\\n'
                   f'#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_DRIVER_BOOM_TT #v x[{mult}|2]#!#!#! from the limit and multipliers on all booms this month"\n'
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
    # key, its tooltip's header, the row's "from ..." (calculator lines, not "Name: value")
    kinds = [("warcap", "Limit on All Wars", "the limit on all our wars"), ("play", "[concept_diplomatic_play]", "a [concept_diplomatic_play]"),
             ("broke", "Treasury Running Out", "our [concept_treasury] running out"), ("default", "[concept_default]", "[concept_default]"),
             ("revolution", "[concept_revolution]", "a [concept_revolution]")]
    out += (' SPEC_ITEMS_TURMOIL: "#indent_newline:3 ' + "".join(f"[AddLocalizationIf({war(n)}.IsSet, 'SPEC_ITEM_WAR_{n}')]" for n in (1, 2, 3))
            + f"[AddLocalizationIf({P}.Var('spec_war_more').IsSet, 'SPEC_ITEM_WAR_MORE')]"
            + "".join(f"[AddLocalizationIf({P}.Var('spec_tm_{t}').IsSet, 'SPEC_ITEM_TM_{t.upper()}')]" for t, *_ in kinds) + '#!"\n')
    out += "".join(f' SPEC_ITEM_WAR_{n}: "\\n#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WAR_WHY_{n} [{v(f"spec_war{n}_c")}|+=1]#!#! from the [concept_war] with #v [{war(n)}.GetCountry.GetName]#!"\n' for n in (1, 2, 3))
    out += "".join(war_why(n, k) for n in diplomacy.WAR_SLOTS)
    out += (f' SPEC_ITEM_WAR_MORE: "\\n#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WAR_MORE_TT [{v("spec_war_more")}|+=1]#!#! from our other wars"\n'
            ' SPEC_WAR_MORE_TT: "#header Other Wars#!\\n$TOOLTIP_DELIMITER$\\nEvery war beyond the first three, added together"\n')
    out += "".join(f' SPEC_ITEM_TM_{t.upper()}: "\\n#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_TM_{t.upper()}_TT [{v(f"spec_tm_{t}")}|+=1]#!#! from {phrase}"\n' for t, _, phrase in kinds)
    head = lambda t, name: f' SPEC_TM_{t.upper()}_TT: "#header {name}: [{v(f"spec_tm_{t}")}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n'
    names = {t: name for t, name, _ in kinds}
    out += (head("warcap", names["warcap"]) + f'[{v("spec_war_sum")}|+=1] from all our wars\\n\\nTogether, our wars can move [concept_spec_market_confidence] by #N {k["WAR_ALL_MIN"]:g}#! to #P +{k["WAR_ALL_MAX"]:g}#! a month at most."\n'
            + head("play", names["play"]) + f'#N -{k["PLAY_TURMOIL"]:g}#! from being in a [concept_diplomatic_play]\\n$TOOLTIP_DELIMITER$\\n#weak This counts once, however many plays we are in, and stops when a [concept_war] begins.#!"\n'
            + head("broke", names["broke"]) + f'At our current losses, we face [concept_bankruptcy] in #v [{sv("spec_broke_weeks")}|0]#! weeks.\\n$TOOLTIP_DELIMITER$\\n#weak This starts #v {k["BROKE_WEEKS"]}#! weeks before $concept_bankruptcy$ and grows to #N -{k["BROKE_COST"]:g}#! a month as the [concept_treasury] runs dry.#!"\n'
            + head("default", names["default"]) + f'#N -{k["DEFAULT_COST"]:g}#! from being in [concept_default]"\n'
            + head("revolution", names["revolution"]) + f'#N -{k["REVOLUTION_COST"]:g}#! from a [concept_revolution]"\n')
    return out


def driver_rows():
    """Loc for a vanilla breakdown tooltip on the confidence line: the monthly drivers, the one-off jumps (bank
    support, the reset when a panic ends) and the 0 to 100 limit, so the rows add up to the change shown. No
    driver icons: custom textures cannot go inline in text."""
    # the gauge tooltip's rows, in vanilla's breakdown form "+1 from Literacy" (CULTURAL_FERVOR_FROM_*)
    out = ' SPEC_GAUGE_ROWS: "' + "".join(f"[AddLocalizationIf({nonzero(v(var))}, 'SPEC_GAUGE_ROW_{key.upper()}')]" for key, var in DRIVERS) + '"\n'
    for key, var in DRIVERS:
        name = f"$SPEC_DRIVER_{key.upper()}$"
        # the calculator sits on the number, as the Booms at Risk rows do
        num = lambda digits: f"#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_DRIVER_{key.upper()}_TT [{v(var)}|+={digits}]#!#!"
        out += f' SPEC_GAUGE_ROW_{key.upper()}: "\\n{num(1)} from {name}"\n'
        out += f' SPEC_CHIP_ROW_{key.upper()}: "\\n{num(2)} from {name}"\n'
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
    mode = 'journal_map' if je else 'open'
    steps += [f"GetVariableSystem.Clear('{nxt}')", f"GetVariableSystem.Set('{FIN}', '{mode}')"]
    if je:
        steps.append(JE_PANEL[1:-1])
    return "".join(f'onclick = "[{s}]"\n' for s in steps)
def open_clicks(tab, when=None, *, journal_map=False):
    """onclicks opening the Finance window on a tab from outside any panel (the topbar, the alert row): any vanilla
    panel closes first, as the side bar's button does. when: the tab only if this holds (GetVariableSystem.SetIf)."""
    steps = ["InformationPanelBar.ClosePanel", f"GetVariableSystem.Clear('{PICK}')"]
    steps += ([f"GetVariableSystem.SetIf('{FIN_TAB}', '{t}', {w})" for t, w in when] if when else
              [f"GetVariableSystem.Set('{FIN_TAB}', '{tab}')"])
    mode = 'journal_map' if journal_map else 'open'
    steps += ["GetVariableSystem.Clear('spec_finance_next')", f"GetVariableSystem.Set('{FIN}', '{mode}')"]
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
JE_PANEL_OPEN = "InformationPanelBar.IsPanelOpen('journal_entry')"
JOURNAL_MAP = f"GetVariableSystem.HasValue('{FIN}', 'journal_map')"
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
		trigger_when = "[And3(GetVariableSystem.Exists('{FIN}'), InformationPanelBar.IsAnyPanelOpen, Not(And({JOURNAL_MAP}, {JE_PANEL_OPEN})))]"
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
                       block(header("SPEC_H_KNOWN", "SPEC_H_KNOWN_RIGHT"), exch.known_block()) if exch.EARN else "")
                       + __import__("company_section").section()))
    return out + [
        ("booms", block(header("SPEC_H_MOOD"), card) + __import__("hero").section() + block(header("SPEC_H_GOODS", "SPEC_LEVERS_RIGHT", "SPEC_LEVERS_TT"), goods_board(k))),
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
    # the Panic Threshold as vanilla's Liberty Desire: the base, then a line a part (leverage.values' spec_pl_*)
    pl_rows = [("spec_pl_lev", "SPEC_PL_LEV"), ("spec_pl_shallow", "SPEC_PL_SHALLOW")] if leverage.ON else []
    panic_tt = (f' SPEC_PANIC_LINE_TT: "#header Panic Threshold: [{sv("spec_panic_at")}|1]#!\\n$TOOLTIP_DELIMITER$\\n'
                f'A [concept_spec_financial_panic] will begin if [concept_spec_market_confidence] falls below this.\\n\\n'
                f'#v {panic:.1f}#! base{calc.lines(pl_rows, sv)}"\n'
                + (f' SPEC_PL_LEV: "{calc.line(sv("spec_pl_lev"), "-=1", f"[concept_spec_leverage] (#v [{sv("spec_lev")}|1]#! months)")}"\n'
                   f' SPEC_PL_SHALLOW: "{calc.line(sv("spec_pl_shallow"), "-=1", "few $building_financial_district$")}"\n'
                   if leverage.ON else ""))
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
    rad = [f"#N {x:.0%}#! of ${p}_no_icon$" for p, x in k["PANIC_RADICALS"].items()]  # generate's spec_start_panic
    radicals = ", ".join(rad[:-1]) + " and " + rad[-1]
    # the World Crash that opens the Long Depression stops lending (depression.NO_CREDIT: the spec_ld_crash modifier)
    ld_crash = f"{P}.Var('spec_world_crash').IsSet"  # depression.CRASH_FLAG: set exactly while the World Crash blocks lending

    def invest_line(t):
        """What a confidence band does to investment, for the card's description."""
        m = k["BAND_INVEST"].get(t, 0)
        return f"{pops} invest #{'P' if m > 0 else 'N'} {abs(m):.0%}#! {'more' if m > 0 else 'less'}."

    def pc(h):
        return f"{round((h - 1) * 100):+d}%"
    no_credit, no_credit_end, no_credit_tt, lev_loc, no_rescue, panic_bad, owed_lev, owed_lim = "", "", "", "", "", "", "", ""
    if leverage.ON:
        crunch = f"{P}.Var('spec_crunch').IsSet"
        no_rescue = "\\nIt does not clear [concept_spec_bad_debts]. #v Buy Up Bad Loans#! can halve them once while they last."
        panic_bad = f"[AddLocalizationIf({crunch}, 'SPEC_PANIC_BAD_DEBTS')]"
        # Bad Debts cut lending gradually (spec_crunch_lend, a row of the rate); only past their stop do banks lend nothing
        no_credit, no_credit_end, no_credit_tt = f"SelectLocalization(Not({gt(sv('spec_crunch_lend'))}), 'SPEC_CREDIT_NO_CRUNCH', ", ")", ""
        relief = f"{P}.Var('spec_lev_fade').IsSet"
        lev, limit = sv("spec_lev"), sv("spec_credit_limit")
        inv_if = f"Multiply_CFixedPoint({sv('spec_crunch_if')}, {fx(f'{leverage.CRUNCH_INVEST * 100:g}')})"  # investment lost if a panic began now
        months_tt = f"#v #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_LEV_MONTHS_TT [{lev}|1] months#!#!#!"
        owed_lev = f" It comes to {months_tt} of the pool's income."
        owed_lim = f", up to our Lending Limit of #v [{limit}|0]#! months of pool income"
        # Bad Debts a panic would leave now, with none yet (leverage.spec_crunch_if): leverage's part in throughput
        # points, then the specialities' multiplier
        bad_lev = f"Multiply_CFixedPoint({sv('spec_crunch_stress')}, {fx(f'{leverage.CRUNCH_MAX * leverage.CRUNCH_THROUGHPUT * 100:g}')})"
        # the Lending Limit as leverage.limit adds it up: the base, a step a finance technology, the Exchange's place,
        # the power bloc's share, then the ceiling at leverage.RUIN
        tech_rows = [(f"spec_lim_{t}", f"SPEC_LEV_LIM_{t.upper()}") for t in leverage.LADDER_TECHS]
        parts = fx(leverage.SAFE)
        for n in [n for n, _ in tech_rows] + ["spec_pb_limit"] + (["spec_exch_limit"] if exch.BRAKE else []):
            parts = f"Add_CFixedPoint({parts}, {sv(n)})"
        lim_cap = f"Subtract_CFixedPoint({limit}, {parts})"
        lim_loc = "".join(f' {key}: "' + calc.line(sv(n), "+=0", f"[GetTechnology('{t}').GetName]") + '"\n'
                          for t, (n, key) in zip(leverage.LADDER_TECHS, tech_rows))
        reward_decimals = 1 if leverage.SMOOTH else len(f"{leverage.REWARD * 100:g}".partition(".")[2])
        boom_now = f"#P +[{sv('spec_lev_boom_pct')}|{reward_decimals}]%#! [concept_throughput]" + (
            f" and #P +[{sv('spec_lev_boom_inv_pct')}|1]%#! investment" if leverage.SMOOTH and leverage.INV_FULL else "")
        # one month's bonus; ponytail: assumes CURVE 1 (straight), a front-loaded curve would need the text per section
        step_bonus = (f"#P +{round(leverage.boom_pct(1), 2):g}%#! [concept_throughput]" + (f" and #P +{round(leverage.boom_pct(1, leverage.INV_FULL), 2):g}%#! investment" if leverage.INV_FULL else "")
                      + f" up to #v {leverage.RUIN:g}#! months") if leverage.SMOOTH else f"#P +{leverage.REWARD * 100:g}%#! [concept_throughput] up to #v {leverage.REWARD_MAX:g}#! months"
        # with an investment bonus, each month's added risk names the investment Bad Debts take too
        step_bad_inv = (f" and #N -[Multiply_CFixedPoint({fx(round(leverage.CRUNCH_MAX / (leverage.RUIN - leverage.SAFE) * leverage.CRUNCH_INVEST * 100, 3))}, {sv('spec_nx_bad')})|1]%#! investment"
                        if leverage.SMOOTH and leverage.INV_FULL else "")
        lev_loc = f""" SPEC_CREDIT_NO_CRUNCH: "Not lending while [concept_spec_bad_debts] are past what our [concept_spec_lending_standards] allow"
 SPEC_LEV_BAD_NOW: "\\n[concept_spec_bad_debts] cost #N -[{sv('spec_crunch_tp_pct')}|1]%#! [concept_throughput] now and clear in #v [{sv('spec_crunch_months')}|0]#! months."
 SPEC_LEV_RELIEF: "\\nWe lost land, so [concept_spec_bad_debts] count only #v [{sv('spec_lev_bad')}|1]#! months of [concept_spec_leverage]. They go back to full over #v [{sv('spec_lev_fade_sv')}|0]#! more months."
 SPEC_LEV_NOTES: "[AddLocalizationIf({crunch}, 'SPEC_LEV_BAD_NOW')][AddLocalizationIf({relief}, 'SPEC_LEV_RELIEF')]"
 SPEC_PANIC_BAD_DEBTS: "[concept_spec_bad_debts] cost #N -[{sv('spec_crunch_tp_pct')}|1]%#! [concept_throughput] now and clear in #v [{sv('spec_crunch_months')}|0]#! months. They may outlast the panic.\\n\\n"
 SPEC_DRIVER_DROP: "Panic Begins"
 SPEC_DRIVER_DROP_TT: "#header Panic Begins: [{v('spec_c_drop')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nA [concept_spec_financial_panic] that begins while [concept_spec_leverage] is high drops [concept_spec_market_confidence] straight to below #v {k['PANIC']}#!."
 SPEC_EFFECT_LEV: "[concept_spec_leverage]"
 SPEC_EFFECT_LEV_VALUE: "[SelectLocalization({gt(lev, leverage.SAFE)}, 'SPEC_LEV_HOT', 'SPEC_LEV_SAFE')]"
 SPEC_EFFECT_BAD: "[concept_spec_bad_debts]"
 SPEC_EFFECT_BAD_VALUE: "[SelectLocalization({crunch}, 'SPEC_EFFECT_BAD_ON', SelectLocalization({gt(sv('spec_crunch_if'))}, 'SPEC_EFFECT_BAD_IF', 'SPEC_GP_RISK_NONE'))]"
 SPEC_EFFECT_BAD_IF: "#v None#! (#N -[{sv('spec_crunch_tp_if_pct')}|1]%#! if a panic began now)"
 SPEC_EFFECT_BAD_ON: "#N -[{sv('spec_crunch_tp_pct')}|1]%#! for #v [{sv('spec_crunch_months')}|0]#! months"
 SPEC_LEV_SAFE: "#v [{lev}|1]#! months"
 SPEC_LEV_HOT: "#N [{lev}|1]#! months"
 SPEC_LEV_ADVICE_SAFE: "Up to #v {leverage.SAFE}#! months this is #P Safe#!, and a [concept_spec_financial_panic] leaves no [concept_spec_bad_debts]."
 SPEC_LEV_ADVICE_RISKY: "Past #v {leverage.SAFE}#! months this is #N Risky#!, as a [concept_spec_financial_panic] starts sooner and leaves [concept_spec_bad_debts]."
 SPEC_LEV_ADVICE_DANGER: "Past #v {leverage.DANGER}#! months this is #N Dangerous#!, as a [concept_spec_financial_panic] starts much sooner and leaves heavy [concept_spec_bad_debts]."
 SPEC_LEV_MONTHS_TT: "#header [concept_spec_leverage]: #v [{lev}|1]#! months#!\\n$TOOLTIP_DELIMITER$\\nOur banks have lent us #v @money![{v('spec_debt')}|D]#!. Our [concept_investment_pool] takes in #v @money![{sv('spec_lev_income')}|D]#! a month.\\n$TOOLTIP_DELIMITER$\\n#weak Pool income is the highest of this month's, its yearly average and #v {leverage.INCOME_FLOOR * 100:g}%#! of [concept_gdp].#!"
 SPEC_LEV_LIMIT: "#header Lending Limit: #v [{limit}|0]#! months#!\\n$TOOLTIP_DELIMITER$\\nBanks stop lending once [concept_spec_outstanding_credit] reaches this many months of [concept_investment_pool] income.\\n\\n#v {leverage.SAFE}#! base{calc.lines(tech_rows, sv)}{exch.LIMIT_LINE}{calc.lines([('spec_pb_limit', 'SPEC_LEV_LIM_BLOC')], sv)}[AddLocalizationIf({calc.shows(lim_cap)}, 'SPEC_LEV_LIM_CAP')]"
{lim_loc} SPEC_LEV_LIM_BLOC: "{calc.line(sv('spec_pb_limit'), '+=0', 'our [concept_power_bloc]')}"
 SPEC_LEV_LIM_CAP: "{calc.line(lim_cap, '+=0', f'the ceiling of #v {leverage.RUIN}#! months')}"
 SPEC_LEV_LIMIT_KEY: "Lending Limit: #v [{limit}|0] months#!"
 SPEC_LEV_MAIN_TT: "#header [concept_spec_leverage]: $SPEC_EFFECT_LEV_VALUE$#!\\n$TOOLTIP_DELIMITER$\\nOur banks have lent us {months_tt} of [concept_investment_pool] income. [SelectLocalization({gt(lev, leverage.DANGER)}, 'SPEC_LEV_ADVICE_DANGER', SelectLocalization({gt(lev, leverage.SAFE)}, 'SPEC_LEV_ADVICE_RISKY', 'SPEC_LEV_ADVICE_SAFE'))]\\n\\n{boom_now} from borrowed money[AddLocalizationIf({calc.shows(sv('spec_pl_lev'))}, 'SPEC_LEV_PL')][AddLocalizationIf({calc.shows(sv('spec_crunch_tp_if_pct'))}, 'SPEC_LEV_IF_PANIC_LINE')][AddLocalizationIf(Or({crunch}, {relief}), 'SPEC_LEV_NOTES')]\\n\\n$SPEC_LEV_STEP$\\n$TOOLTIP_DELIMITER$\\nBanks lend up to our Lending Limit of #v #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_LEV_LIMIT [{limit}|0] months#!#!#!."
 SPEC_LEV_STEP: "Each month of [concept_spec_leverage], part months included, adds {step_bonus}. Past #v {leverage.SAFE}#! months, each also brings a [concept_spec_financial_panic] #N [Divide_CFixedPoint(Subtract_CFixedPoint({sv(f'spec_panic_at_{leverage.RUIN}')}, {sv(f'spec_panic_at_{leverage.SAFE}')}), {fx(leverage.RUIN - leverage.SAFE)})|1]#! [concept_spec_market_confidence] sooner and adds #N -[Multiply_CFixedPoint({fx(round(leverage.CRUNCH_MAX / (leverage.RUIN - leverage.SAFE) * leverage.CRUNCH_THROUGHPUT * 100, 3))}, {sv('spec_nx_bad')})|1]%#! [concept_throughput]{step_bad_inv} to its [concept_spec_bad_debts]."
 SPEC_LEV_PL: "\\n#N +[{sv('spec_pl_lev')}|1]#! Panic Threshold, so a panic starts sooner"
 SPEC_LEV_IF_PANIC_LINE: "\\n#N -[{sv('spec_crunch_tp_if_pct')}|1]%#! [concept_throughput] and #N -[{inv_if}|1]%#! investment from [concept_spec_bad_debts], if a panic began now"
 SPEC_LEV_IF_PANIC: "A [concept_spec_financial_panic] now would leave [concept_spec_bad_debts] of #N -[{sv('spec_crunch_tp_if_pct')}|1]%#! [concept_throughput] and #N -[{inv_if}|1]%#! investment."
 SPEC_BAD_IF_NONE: "A [concept_spec_financial_panic] now would leave no [concept_spec_bad_debts]."
"""
        # each rung of the credit ladder: what it allows at its top, what unlocks it, and whether the country is on it
        edges = (0, *leverage.LADDER)
        rungs = list(zip(edges, edges[1:]))
        stress = lambda m: min(max((m - leverage.SAFE) / (leverage.RUIN - leverage.SAFE), 0), 1)
        # throughput %, or investment's, times the Exchange's specialities as leverage.spec_crunch_if multiplies them
        # (a bubble's burst adds its own, shown on the Bubble Risk chip)
        bad_at = lambda m, per=leverage.CRUNCH_THROUGHPUT: f"[Multiply_CFixedPoint({fx(round(leverage.CRUNCH_MAX * stress(m) * per * 100, 3))}, {sv('spec_nx_bad')})|1]"
        # each section of the bar: who lends that far, then what its top end gives and risks, against Safe's
        ib, ies = (f"[GetTechnology('{t}').GetName]" for t in leverage.LADDER_TECHS[1:])
        cb = f"[GetTechnology('{leverage.LADDER_TECHS[0]}').GetName]"
        unlock = ("Banks lend this far from the start.", f"{cb} lets banks lend this far.",
                  f"{ib} or {ies} lets banks lend this far.", f"{ib} and {ies} together let banks lend this far.")
        zone = lambda hi: ("#P Safe#!" if hi <= leverage.SAFE else "#N Risky#!" if hi <= leverage.DANGER else "#N Dangerous#!")
        safe_at = f"[{sv(f'spec_panic_at_{leverage.SAFE}')}|0]"
        for i, (lo, hi) in enumerate(rungs):
            # a range, not a step: the bonus and the risk both grow with every month inside the section
            # (tenths of a percent, and under SMOOTH the investment beside the throughput)
            rng = lambda full: (f"#P +{round(leverage.boom_pct(lo, full), 1):g}%#! to " if lo else "up to ") + f"#P +{round(leverage.boom_pct(hi, full), 1):g}%#!"
            boom = " and ".join(f"{rng(full)} {w}" for full, w in ((None, "[concept_throughput]"), (leverage.INV_FULL if leverage.SMOOTH else 0, "investment")) if full is None or full)
            risk = (" A [concept_spec_financial_panic] leaves no [concept_spec_bad_debts]." if hi <= leverage.SAFE else
                    f" By #v {hi}#! months, a [concept_spec_financial_panic] starts below #N [{sv(f'spec_panic_at_{hi}')}|0]#! [concept_spec_market_confidence] instead of #v {safe_at}#!, "
                    f"and leaves [concept_spec_bad_debts] costing up to #N -{bad_at(hi)}%#! [concept_throughput] and #N -{bad_at(hi, leverage.CRUNCH_INVEST)}%#! investment.")
            lev_loc += f""" SPEC_LEV_TIER_{i}_TT: "#header {lo} to {hi} Months, {zone(hi)}#!\\n$TOOLTIP_DELIMITER$\\n{unlock[i]}\\n\\nAcross these months, borrowed money adds {boom}.{risk}"
"""
        lev_loc += f""" SPEC_BAILOUT: "Buy Up Bad Loans"
 SPEC_BAILOUT_TT: "#header Buy Up Bad Loans#!\\n$TOOLTIP_DELIMITER$\\nThe state buys up the banks' bad loans and takes the loss itself.\\n\\n[GetScriptedGui('spec_sgui_bailout').BuildTooltip(GuiScope.SetRoot({P}).End)]"
 SPEC_BAD_SCALE: "[concept_spec_bad_debts] come from a [concept_spec_financial_panic] that starts with more than #v {leverage.SAFE}#! months of [concept_spec_leverage], worse the more months, or from a bubble of [concept_spec_speculative_excess] that bursts for more than our [concept_spec_market_confidence]. Banks lend less the more there are, and nothing past #v [{sv('spec_crunch_stop')}|0]#! at our [concept_spec_lending_standards]."
 SPEC_BAD_BUILDING: "\\nStill growing by #N {leverage.CRUNCH_RAMP * leverage.CRUNCH_THROUGHPUT * 100:g}%#! a month, to #N -[{sv('spec_crunch_tp_full_pct')}|1]%#!"
 SPEC_EFFECT_BAD_TT: "#header [concept_spec_bad_debts]: #N -[{sv('spec_crunch_tp_pct')}|1]%#!#!\\n$TOOLTIP_DELIMITER$\\nOur banks' bad loans clear in #v [{sv('spec_crunch_months')}|0]#! months. Until then, banks lend #N [{sv('spec_crunch_lend_cut')}|0]%#! less, and nothing past #v [{sv('spec_crunch_stop')}|0]#!.\\n\\n#N -[{sv('spec_crunch_tp_pct')}|1]%#! [concept_throughput]\\n#N -[{sv('spec_crunch_invest_pct')}|0]%#! investment[AddLocalizationIf({gt(sv('spec_crunch_left'))}, 'SPEC_BAD_BUILDING')]\\n$TOOLTIP_DELIMITER$\\nOnce felt in full, they shrink by #v {leverage.CRUNCH_FADE * leverage.CRUNCH_THROUGHPUT * 100:g}%#! [concept_throughput] a month, or #v {leverage.CRUNCH_FADE_TIGHT * leverage.CRUNCH_THROUGHPUT * 100:g}%#! under [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]. The [concept_throughput] borrowed money added fades while they last. #v Buy Up Bad Loans#! clears {leverage.BAILOUT_CUT:.0%} of them, once."
 SPEC_EFFECT_BAD_NONE_TT: "#header [concept_spec_bad_debts]: #P None#!#!\\n$TOOLTIP_DELIMITER$\\n[SelectLocalization({calc.shows(sv('spec_crunch_tp_if_pct'))}, 'SPEC_BAD_IF', 'SPEC_BAD_IF_NONE')]\\n$TOOLTIP_DELIMITER$\\n$SPEC_BAD_SCALE$"
 SPEC_BAD_IF: "$SPEC_LEV_IF_PANIC$\\n\\n#N -[{bad_lev}|1]%#! from [concept_spec_leverage] (#v [{sv('spec_lev_bad')}|1]#! months)#indent_newline:3 [AddLocalizationIf({not1('spec_nx_bad')}, 'SPEC_BAD_IF_NX')]#!"
 SPEC_BAD_IF_NX: "\\n#v x[{sv('spec_nx_bad')}|2]#! from our [concept_spec_exchange]'s specialities"
 SPEC_EFFECT_LEV_TT: "$SPEC_LEV_MAIN_TT$"
"""
    banking = gt(sv("spec_has_central_banking"))
    # generate.spec_credit multiplies spec_credit_mult by Lending Standards (cycle.CREDIT) and by the Exchange's
    # charter and specialities (centres.CREDIT): each gets a row, and the word reads generate's spec_credit_rate, their product
    credit_rate = sv("spec_credit_rate")
    def factor(script):  # the product of a CREDIT string's "multiply = x" lines, so it follows whatever that module multiplies
        names = [line.split("=")[1].strip() for line in script.splitlines()]
        out = sv(names[0])
        for n in names[1:]:
            out = f"Multiply_CFixedPoint({out}, {sv(n)})"
        return out
    extra = [(name, factor(script)) for name, script in (("[concept_spec_lending_standards]", cycle.CREDIT),
                                                         ("our [concept_spec_exchange]", exch.CREDIT),
                                                         ("[concept_spec_bad_debts]", leverage.CREDIT)) if script]
    # the rate's calculator: a line a factor, those at x1 left out as vanilla leaves them
    rate_parts = [("$ECONOMIC_SYSTEM_GC_LINK$", sv("spec_law_mult")), ("Finance Technologies", sv("spec_tech_credit")),
                  ("[concept_spec_credit_policy]", sv("spec_stance_credit")), ("[concept_spec_banking_reforms]", sv("spec_reform_credit"))] + extra
    rate_lines = "".join(f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({m}, {fx(1)})), 'SPEC_RATE_{i}')]" for i, (_, m) in enumerate(rate_parts))
    rate_loc = "".join(f' SPEC_RATE_{i}: "\\n#v x[{m}|2]#! from {name}"\n' for i, (name, m) in enumerate(rate_parts))
    # a panic's length as generate's spec_panic_months_trust works it out, a line a factor (x1 left out)
    len_parts = ([("spec_panic_mult", "$ECONOMIC_SYSTEM_GC_LINK$"), ("spec_nx_panic", "our [concept_spec_exchange]'s specialities"),
                  ("spec_trust_mult", "[concept_legitimacy]"), ("spec_reform_panic_len", "[concept_spec_banking_reforms]")]
                 + ([("spec_panic_lev_len", "[concept_spec_leverage]")] if leverage.ON else []))
    len_lines = "".join(f"[AddLocalizationIf({not1(n)}, 'SPEC_PANIC_LEN_{i}')]" for i, (n, _) in enumerate(len_parts))
    len_loc = "".join(f' SPEC_PANIC_LEN_{i}: "\\n#v x[{sv(n)}|2]#! from {label}"\n' for i, (n, label) in enumerate(len_parts))
    # Withdrawn in a Panic as generate's spec_clawback works it out: the share called back, cut to what the pool allows
    asked = f"Multiply_CFixedPoint({v('spec_debt')}, {fx(k['CLAWBACK'])})"
    if cycle.ON:  # Lending Standards scale the share (cycle.RECALL)
        asked = f"Multiply_CFixedPoint({asked}, {sv('spec_lax_recall')})"
    claw_cut = f"Subtract_CFixedPoint({asked}, {sv('spec_clawback')})"
    claw_lax = f"[AddLocalizationIf({not1('spec_lax_recall')}, 'SPEC_DEBT_LAX')]" if cycle.ON else ""
    recall_lax = (f"[AddLocalizationIf(Not(EqualTo_CFixedPoint({v('spec_recall_lax', 1)}, {fx(1)})), 'SPEC_RECALL_LAX')]"
                  if cycle.ON else "")
    claw_share = sv("spec_claw_share") if leverage.ON else fx(1)
    # confidence's recovery (generate's spec_conf_recover): our Exchange's trust scales it (centres.RECOVER_REF)
    drift_trust = f"[AddLocalizationIf({not1('spec_exch_recover')}, 'SPEC_DRIFT_TRUST')]" if exch.RECOVER_REF else ""
    claw_note = (f"The most a panic can take is #v {k['CLAW_FLOOR']:.0%}#! of the pool at low [concept_spec_leverage], "
                 f"rising to all of it at #v {leverage.DANGER}#! months. " if leverage.ON else "")
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

    # the gauge tooltip, laid out as vanilla's value tooltips: INFAMY_TOOLTIP's header (name: level (value)),
    # CULTURE_POPULATION_CHANGE's "Monthly Change", CULTURAL_FERVOR_FROM_*'s "+1 from X" rows and
    # LEGITIMACY_LEVEL_ACTIVE_TOOLTIP's indented "Effects:" block
    def band_fx(t):
        """A band's effects as stat lines, for the gauge and the band tooltips."""
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
    mood_company_delta = f"Subtract_CFixedPoint({v('spec_mood_shift')}, {v('spec_mood_random')})"
    mood_company = f"[AddLocalizationIf({gt(mood_company_delta)}, 'SPEC_MOOD_COMPANY')]"
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
        f' SPEC_CHIP_{n}: "[SelectLocalization({nonzero(v(f"spec_p{n}"), 0.05)}, \'SPEC_CHIP_{n}_V\', \'SPEC_CHIP_ZERO\')]"\n'
        f' SPEC_CHIP_{n}_V: "[{rounded_tenth(v(f"spec_p{n}"))}|+=1]"\n'
        f' SPEC_CHIP_{n}_TT: "#header $SPEC_PRESSURE_{name.upper()}$: [{v(f"spec_p{n}")}|+=2]#!\\n$TOOLTIP_DELIMITER$'
        + "".join(f"[AddLocalizationIf({nonzero(v(var[k]), PRESSURE_STEP)}, 'SPEC_CHIP_ROW_{k.upper()}')]"
                  + (f"[AddLocalizationIf({nonzero(v(var[k]))}, 'SPEC_ITEMS_{k.upper()}')]" if k in ITEMS else "") for k in keys)
        + f"[AddLocalizationIf(Not({any_of([nonzero(v(var[k]), PRESSURE_STEP) for k in keys])}), 'SPEC_CHIP_NONE')]" + '"\n'
        for n, (name, _, keys) in enumerate(PRESSURES, 1))
    chips += ' SPEC_CHIP_NONE: "\\nNo change this month."\n'
    # Speculative Excess as vanilla's Liberty Desire: next month's change, a cause a line (journal.excess_calc, calc.py)
    xs_rows = __import__("journal").excess_calc(k)[1]
    xs = (f' SPEC_XS_TT: "#header [concept_spec_speculative_excess]: [{XS}|0]#!\\n$TOOLTIP_DELIMITER$\\n'
          f"[SelectLocalization({gt(sv('spec_has_stock_exchange'))}, SelectLocalization({calc.shows(sv('spec_xs_next'))}, "
          f"'SPEC_XS_TT_NEXT', 'SPEC_XS_TT_IDLE'), 'SPEC_XS_BAR_OFF')]"
          f"[AddLocalizationIf({P}.Var('spec_heat').IsSet, 'SPEC_XS_TT_RISK')]\"\n"
          f' SPEC_XS_TT_NEXT: "Expected next month: [{sv("spec_xs_next")}|-=1]#indent_newline:3 {calc.lines([(n, key + "_LINE") for n, key, _ in xs_rows], sv)}#!"\n'
          # the whole life of a bubble, since none is building to show it (2026-11-20: the top end was only told once one was)
          f' SPEC_XS_TT_IDLE: "It grows each month [concept_spec_market_confidence] is #v [{sv("spec_heat_from")}|0]#! or more, faster the higher it is. '
          f'Below that it shrinks by #v {1 - k["HEAT_COOL"]:.0%}#! a month, or #v {1 - k["HEAT_COOL_TIGHT"]:.0%}#! under a '
          f"[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')] credit policy.\\n\\n"
          f'If [concept_spec_market_confidence] falls below #v {k["BURST_BELOW"]}#!, the bubble bursts and costs [concept_spec_market_confidence] '
          f'#N [{sv("spec_burst_per_heat")}|%0]#! of its size. The bar turns red once a burst would cost #v {XS_ALERT}#! or more, and is full '
          f'when it would take all of it.{" Past that, what a burst cannot take becomes [concept_spec_bad_debts]." if leverage.ON else ""}"\n'
          # spec_burst_now stops at BURST_BELOW: a burst then takes all the confidence there is when it comes
          f' SPEC_XS_TT_RISK: "\\n$TOOLTIP_DELIMITER$\\n[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({sv("spec_burst_now")}, {fx(k["BURST_BELOW"])}), '
          f"'SPEC_XS_TT_ALL', 'SPEC_RISK_5_COST')]\"\n"  # the burst's cost, worded as on the Bubble Risk chip
          ' SPEC_XS_TT_ALL: "$SPEC_RISK_5_ALL$\\nThe bar is full. '
          + ('Past this, what a burst cannot take from [concept_spec_market_confidence] becomes [concept_spec_bad_debts]."\n' if leverage.ON else
             'More $concept_spec_speculative_excess$ only makes it slower to cool off."\n')
          + "".join(f' {key}_LINE: "{calc.line(sv(n), "-=1", "$" + key + "$")}"\n' for n, key, _ in xs_rows))

    sector_name = "'SPEC_IB_EMPTY'"
    for index, sector in reversed(list(enumerate(GROUPS, 1))):
        sector_name = f"SelectLocalization(EqualTo_CFixedPoint({good_var('spec_ui_cat')}, {fx(index)}), 'SPEC_SECTOR_{sector.upper()}', {sector_name})"
    mean = good_sv("spec_review_mean")
    direction = f"SelectLocalization({gt(mean)}, 'SPEC_SECTOR_RISING', SelectLocalization(LessThan_CFixedPoint({mean}, {fx(0)}), 'SPEC_SECTOR_FALLING', 'SPEC_SECTOR_FLAT'))"
    fast_n, slow_n = trend_next(k["FAST"], k["SLOW"])  # the Investor Interest forecast (SPEC_II_TREND)
    # the Market Confidence forecast (SPEC_CONF_FORECAST), as spec_conf_pre and spec_conf_next work it out: this
    # month's steady drivers again, mood fading by MOOD_KEEP, the pull to baseline and Tight Credit afresh. One-off
    # jumps (ended booms, foreign panics, rescues, war ends, bursts, events) and mood's random part are left out
    import centres  # imports this module
    pre = CONF
    for part in [v(f"spec_c_{d}") for d in ("boom", "restrain", "world", "turmoil", "debt", "growth", "business", "rival")] \
            + [f"Multiply_CFixedPoint({v('spec_c_mood')}, {fx(k['MOOD_KEEP'])})", sv("spec_conf_recover")] \
            + ([sv("spec_exch_lean")] if centres.LEAN else []):
        pre = f"Add_CFixedPoint({pre}, {part})"
    pull = f"Min_CFixedPoint(Multiply_CFixedPoint(Subtract_CFixedPoint({fx(k['TIGHT_FROM'])}, {pre}), {fx(k['TIGHT_PULL'])}), {fx(0)})"
    conf_next = f"Max_CFixedPoint(Min_CFixedPoint(Add_CFixedPoint({pre}, Select_CFixedPoint({tight}, {pull}, {fx(0)})), {fx(100)}), {fx(0)})"
    conf_move = f"Subtract_CFixedPoint({conf_next}, {CONF})"
    return f""" SPEC_OFF: "Investors do not speculate under the current $ECONOMIC_SYSTEM_GC_LINK$."
 SPEC_CONF_LINE: "[concept_spec_market_confidence]: #v [{SHOWN}|0]#![SelectLocalization({nonzero(v('spec_c_total'))}, 'SPEC_CONF_CHANGE', 'SPEC_CONF_NO_CHANGE')]"
 SPEC_CONF_CHANGE: " ([{v('spec_c_total')}|+=1])"
 SPEC_CONF_NO_CHANGE: ""
 SPEC_CARD_CHANGE_TT: "$SPEC_GAUGE_HEAD$\\n$SPEC_GAUGE_CHANGE$\\n$SPEC_CONF_FORECAST${member}"
 SPEC_CONF_FORECAST: "Expected next month: [{conf_move}|+=1]\\n#weak One-off events and swings in mood are left out#!"
 SPEC_CARD_MEMBER: "\\n\\nThis is the [concept_spec_market_confidence] of #v [Country.GetName]#!. Each [concept_country] in the [concept_market] has its own."
 SPEC_CARD_RING_TT: "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_TT', 'SPEC_GAUGE_TT')]"
 SPEC_CARD_BAR_TT: "$SPEC_CARD_RING_TT$[AddLocalizationIf({RISKS_SHOWN}, 'SPEC_RISK_FALL_ADD')]"
 SPEC_RISK_FALL_ADD: "\\n$TOOLTIP_DELIMITER$\\n$SPEC_RISK_FALL$"
 SPEC_RISK_FALL: "If every risk struck at once, [concept_spec_market_confidence] would fall to #N [{RISK_FLOOR}|1]#! (#v [{by_tier('SPEC_TIER', value=RISK_FLOOR)}]#!)"
 SPEC_CARD_FRESH: "#grey First measured next month#!"
 SPEC_CARD_FRESH_TT: "#header [concept_spec_market_confidence]#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_spec_market_confidence] will be measured for the first time next month."
 SPEC_TOP_HEAD: "#header [concept_spec_market_confidence]#!"
 SPEC_TOP_TT: "$SPEC_TOP_HEAD$\\nConfidence stands at #v [{CONF}|0]#! ($SPEC_STATE_TITLE$), and should be about #v [{conf_next}|0]#! next month\\n$TOOLTIP_DELIMITER$\\nIt changed by #tooltippable #tooltip:[Country.GetTooltipTag],SPEC_TOP_CHANGE_TT [{v('spec_c_total')}|+=1]#!#! this month.\\n\\n$SPEC_STATE_DESC${member}"
 SPEC_TOP_CHANGE_TT: "#header Monthly Change#!\\n$TOOLTIP_DELIMITER$$SPEC_GAUGE_ROWS$"
 SPEC_TOP_FRESH_TT: "$SPEC_TOP_HEAD$\\n$TOOLTIP_DELIMITER$\\nIt will be measured for the first time next month."
 SPEC_TOP_OFF_TT: "$SPEC_TOP_HEAD$\\n$TOOLTIP_DELIMITER$\\n$SPEC_OFF$"
 SPEC_TOP_CONF_HIST: "$concept_spec_market_confidence$"
 SPEC_TOP_LEV_HIST: "$concept_spec_leverage$"
 SPEC_CARD_MONTH: "month"
 SPEC_CARD_MONTHS: "months"
{driver_rows()} SPEC_GAUGE_TT: "$SPEC_GAUGE_HEAD$\\n$SPEC_GAUGE_CHANGE$\\n$SPEC_CONF_FORECAST$\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!#indent_newline:3 \\n[{by_tier('SPEC_GAUGE_FX', state_names)}]\\n$SPEC_GAUGE_LEND$$SPEC_DEPTH_LINE$#!\\n\\n[{by_tier('SPEC_GAUGE_NEXT', state_names)}]{member}"
 SPEC_GAUGE_HEAD: "#header [concept_spec_market_confidence]: #bold $SPEC_STATE_TITLE$#! (#v [{CONF}|0]#!)#!"
 SPEC_GAUGE_CHANGE: "Monthly Change: [{v('spec_c_total')}|+=1]#indent_newline:3 $SPEC_GAUGE_ROWS$#!"
 SPEC_GAUGE_LEND: "[SelectLocalization({IN_PANIC}, 'SPEC_GAUGE_LEND_PANIC', {no_credit.replace('SPEC_CREDIT_NO_CRUNCH', 'SPEC_GAUGE_LEND_BAD')}SelectLocalization({ld_crash}, 'SPEC_GAUGE_LEND_CRASH', SelectLocalization({tight}, 'SPEC_GAUGE_LEND_TIGHT', SelectLocalization(Not({gt(CONF, credit_from)}), 'SPEC_GAUGE_LEND_ABOVE', SelectLocalization(LessThan_CFixedPoint({CONF}, {sv('spec_panic_at')}), 'SPEC_GAUGE_LEND_LINE', SelectLocalization(Not({gt(sv('spec_credit_room'))}), 'SPEC_GAUGE_LEND_LIMIT', 'SPEC_GAUGE_LENDING'))))){no_credit_end})]"
 SPEC_GAUGE_LEND_LINE: "Banks do not lend below the Panic Threshold."
 SPEC_GAUGE_LEND_LIMIT: "Banks do not lend past our Lending Limit."
 SPEC_GAUGE_LEND_PANIC: "Banks do not lend during a [concept_spec_financial_panic]."
 SPEC_GAUGE_LEND_BAD: "Banks do not lend while [concept_spec_bad_debts] are past what our [concept_spec_lending_standards] allow."
 SPEC_GAUGE_LEND_CRASH: "Banks do not lend in the World Crash that opens the [concept_spec_long_depression]."
 SPEC_GAUGE_LEND_TIGHT: "Banks do not lend under [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]."
 SPEC_GAUGE_LENDING: "Banks lend into the [concept_investment_pool]."
 SPEC_GAUGE_LEND_ABOVE: "Banks lend only while [concept_spec_market_confidence] is above #v {credit_from}#!."
 SPEC_DATE_ZERO: "0"
 SPEC_DATE_MAY: "May"
 SPEC_PRESSURES: "Pressures"
 SPEC_PRESSURES_TT: "#header Pressures: [SelectLocalization({nonzero(v('spec_c_total'))}, 'SPEC_PRESSURES_SUM', 'SPEC_CHIP_ZERO')]#!\\n$TOOLTIP_DELIMITER$\\nThe groups below show what moved our [concept_spec_market_confidence] this month.\\n\\n#instruction Hover over a group to see its causes#!"
 SPEC_PRESSURES_SUM: "[{v('spec_c_total')}|+=1]"
 SPEC_CHIP_ZERO: "#v 0.0#!"
 SPEC_PRESSURE_GOODS: "Economy"
 SPEC_PRESSURE_ABROAD: "Abroad"
 SPEC_PRESSURE_STATE: "War and Government"
 SPEC_PRESSURE_MOOD: "Investor Mood"
 SPEC_PRESSURE_CREDIT: "Credit"
{chips} SPEC_DOWNSIDE_TT: "#header Booms at Risk: #N -[{BAR_GAP}|1]#!#!\\n$TOOLTIP_DELIMITER$\\nIf our boom in #v [{P}.Var('spec_risk_top_good').GetGoods.GetName]#! ended now, [concept_spec_market_confidence] would fall by #N [{BAR_GAP}|1]#!.\\n\\n#v [{v('spec_n_risk')}|0]#! of our booms could end. If all of them ended at once, [concept_spec_market_confidence] would fall to #v [{BAR_FLOOR}|1]#! (#v [{by_tier('SPEC_TIER', value=BAR_FLOOR)}]#!).[AddLocalizationIf({gt(v('spec_n_held'))}, 'SPEC_RISK_HELD_LINE')]\\n$TOOLTIP_DELIMITER$\\n#title By Good:#!#indent_newline:3 $SPEC_ITEMS_RISK$#![AddLocalizationIf({market_visual.mt.gt(v('spec_heat_collapse'), market_visual.SHOWN)}, 'SPEC_RISK_SHARE')]"
 SPEC_RISKS: "Risks"
 SPEC_XS: "Excess"
 SPEC_XS_BAR_OFF: "Needs [GetTechnology('stock_exchange').GetName]"
{xs} SPEC_HISTORY: "History"
 SPEC_HISTORY_TT: "#header Market Confidence History#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_spec_market_confidence] over the last #v {HISTORY}#! months, with the newest on the right.\\n\\nBars are #v gold#! above #v {HIST_MID}#! and #v blue#! below it. They turn #N red#! when the market is #v {BAND_NAMES[0]}#!, below #v {TIERS[0][2]}#!, or in #v {BAND_NAMES[-1]}#!, above #v {TIERS[-1][1]}#!."
{"".join(f""" SPEC_HIST_{n}_TT: "[SelectLocalization({P}.Var('spec_hist{n}').IsSet, 'SPEC_HIST_{n}_ON', 'SPEC_HIST_NONE')]"
 SPEC_HIST_{n}_ON: "#header {'This Month' if n == 1 else 'Last Month' if n == 2 else f'{n - 1} Months Ago'}#!\\n[concept_spec_market_confidence]: #v [{v(f'spec_hist{n}')}|0]#! ([{by_tier('SPEC_TIER', value=v(f'spec_hist{n}'))}])"
""" for n in range(1, HISTORY + 1))} SPEC_HIST_NONE: "No record for this month yet."
 SPEC_RISKS_TT: "[SelectLocalization({RISKS_SHOWN}, 'SPEC_RISKS_ON', 'SPEC_RISKS_NONE')]"
 SPEC_RISKS_ON: "#header Risks: #N -[{RISK_SUM}|1]#!#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RISK_FALL$:#indent_newline:3 {''.join(f"[AddLocalizationIf({shows}, 'SPEC_RISKS_{name}')]" for name, shows, _ in RISK_PARTS)}#!\\n$TOOLTIP_DELIMITER$\\n#weak War and Default Risk count one month#!\\n#instruction Hover over each one to see what is behind it#!"
{''.join(f''' SPEC_RISKS_{name}: "\\n#N -[{cost}|1]#! from {label}"
''' for (name, _, cost), label in zip(RISK_PARTS, ("Booms at Risk", "Panic Risk", "War Risk", "Default Risk", "Bubble Risk")))} SPEC_RISKS_NONE: "#header Risks#!\\n$TOOLTIP_DELIMITER$\\nNothing threatens our [concept_spec_market_confidence] right now. Each risk shows here as it appears."
 SPEC_RISK_1: "[SelectLocalization({BAR_RISK}, 'SPEC_RISK_1_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_1_V: "#N -[{rounded_tenth(BAR_GAP)}|1]#!"
 SPEC_RISK_1_TT: "[SelectLocalization({BAR_RISK}, 'SPEC_DOWNSIDE_TT', 'SPEC_RISK_1_NONE')]"
 SPEC_RISK_HELD_LINE: " #v [{v('spec_n_held')}|0]#! more are held back and will wind down gently as a [concept_spec_correction]."
{"".join(f''' SPEC_WHY_END_{sev}: "#v x{rate:g}#! from ending in a [concept_spec_{name}]"
''' for (sev, _, _, rate, _), name in zip(k['UNWINDS'], ("collapse", "bust", "correction")))} SPEC_WHY_CAP: "\\nNo boom can take more than #N {k['CONF_CRASH_MAX']:g}#! in a month."
 SPEC_WHY_FALLING: "\\n\\n[concept_spec_investor_interest] fell this month. If it keeps falling, the boom will end."
 SPEC_RISK_1_NONE: "#header Booms at Risk#!\\nNothing to worry about. None of our booms would hurt our [concept_spec_market_confidence] if it ended."
 SPEC_RISK_2: "[SelectLocalization({SRC_RISK}, 'SPEC_RISK_2_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_2_V: "#N -[{rounded_tenth(SRC_HIT)}|1]#!"
 SPEC_RISK_2_TT: "[SelectLocalization({SRC_RISK}, 'SPEC_BAR_SRC_TT', 'SPEC_RISK_2_NONE')]"
 SPEC_RISK_2_NONE: "#header Panic Risk#!\\nNothing to worry about. No [concept_country] tied to ours is close to a [concept_spec_financial_panic] or in a #v {BAND_NAMES[-1]}#!."
 SPEC_RISK_3: "[SelectLocalization({WAR_RISK}, 'SPEC_RISK_3_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_3_V: "#N -[{rounded_tenth(v('spec_war_risk'))}|1]#!"
 SPEC_RISK_3_TT: "[SelectLocalization({WAR_RISK}, 'SPEC_RISK_3_ON', 'SPEC_RISK_3_NONE')]"
 SPEC_RISK_3_ON: "#header War Risk: #N -[{v('spec_war_risk')}|1]#!#!\\n$TOOLTIP_DELIMITER$\\nIf our [concept_diplomatic_play] became a war, [concept_spec_war_news] would take about this much more [concept_spec_market_confidence] each month than the play does now:{''.join(f"[AddLocalizationIf({P}.Var('spec_wr{n}').IsSet, 'SPEC_ITEM_WR_{n}')]" for n in range(1, 4))}[AddLocalizationIf({P}.Var('spec_wr_play').IsSet, 'SPEC_WR_PLAY')]\\n$TOOLTIP_DELIMITER$\\n#weak How the war goes decides its real cost, from #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! a month#!"
 SPEC_WR_PLAY: "\\n\\n#P +{k['PLAY_TURMOIL']:.2f}#! from the play's own cost, which stops once war begins"
{''.join(f""" SPEC_ITEM_WR_{n}: "\\n\\n#N -[{v(f'spec_wrc{n}')}|2]#! from a war against #v [{P}.Var('spec_wr{n}').GetCountry.GetName]#!#indent_newline:3 \\n#N -{k['WAR_BASE']:.2f}#! from any war\\n#N -[{share_sq(f'spec_wra{n}', k['WAR_RISK_ARMY'])}|2]#! from their side's #v [{v(f'spec_wra{n}')}|%0]#! of the armies\\n#N -[{share_sq(f'spec_wrs{n}', k['WAR_RISK_NAVY'])}|2]#! from their side's #v [{v(f'spec_wrs{n}')}|%0]#! of the navies#!"
""" for n in range(1, 4))} SPEC_RISK_3_NONE: "[SelectLocalization({gt(v('spec_wr_n'))}, 'SPEC_RISK_3_CHEAP', 'SPEC_RISK_3_CALM')]"
 SPEC_RISK_3_CALM: "#header War Risk#!\\nNothing to worry about. We are in no [concept_diplomatic_play] that could turn into war."
 SPEC_RISK_3_CHEAP: "#header War Risk#!\\nNothing to worry about. If our [concept_diplomatic_play] became a war, [concept_spec_war_news] would likely take no more [concept_spec_market_confidence] than the play does now."
 SPEC_RISK_5: "[SelectLocalization({XS_RISK}, 'SPEC_RISK_5_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_5_V: "#N -[{rounded_tenth(sv('spec_burst_now'))}|1]#!"
 SPEC_RISK_5_TT: "[SelectLocalization({XS_RISK}, 'SPEC_RISK_5_ON', 'SPEC_RISK_5_NONE')]"
 SPEC_RISK_5_ON: "#header Bubble Risk: #N -[{sv('spec_burst_now')}|1]#!#!\\n$TOOLTIP_DELIMITER$\\nA bubble of #v [{XS}|0]#! [concept_spec_speculative_excess] has formed. It grows while [concept_spec_market_confidence] stays at #v [{sv('spec_heat_from')}|0]#! or more, slowly shrinks below that, and bursts if [concept_spec_market_confidence] falls below #v {k['BURST_BELOW']}#!.\\n\\n[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({sv('spec_burst_now')}, {fx(k['BURST_BELOW'])}), 'SPEC_RISK_5_ALL', 'SPEC_RISK_5_COST')]"
 SPEC_RISK_5_COST: "If it burst now, [concept_spec_market_confidence] would fall by #N [{sv('spec_burst_now')}|1]#!."
 SPEC_RISK_5_ALL: "If it burst now, it would take all our [concept_spec_market_confidence]{f"[AddLocalizationIf({calc.shows(sv('spec_xs_bad_now'))}, 'SPEC_RISK_5_BAD')]" if leverage.ON else ""}."
 SPEC_RISK_5_BAD: " and leave at least #N [{sv('spec_xs_bad_now')}|0]#! [concept_spec_bad_debts]"
 SPEC_RISK_5_NONE: "#header Bubble Risk#!\\nNothing to worry about. There is no bubble right now. One starts to grow once [concept_spec_market_confidence] reaches #v [{sv('spec_heat_from')}|0]#!."
 SPEC_RISK_4: "[SelectLocalization({DEFAULT_RISK}, 'SPEC_RISK_4_V', 'SPEC_CHIP_ZERO')]"
 SPEC_RISK_4_V: "#N -{k['DEFAULT_COST']:.1f}#!"
 SPEC_RISK_4_TT: "[SelectLocalization({DEFAULT_RISK}, 'SPEC_RISK_4_ON', 'SPEC_RISK_4_NONE')]"
 SPEC_RISK_4_ON: "#header Default Risk: #N -{k['DEFAULT_COST']:.1f}#!#!\\n$TOOLTIP_DELIMITER$\\nWe have used #v [{v('spec_default_risk')}|%0]#! of our [concept_credit]. If we go past #v 100%#!, we fall into [concept_default], and [concept_spec_market_confidence] falls by #N {k['DEFAULT_COST']:g}#! every month until it ends.[AddLocalizationIf({P}.Var('spec_tm_broke').IsSet, 'SPEC_RISK_4_BROKE')]\\n$TOOLTIP_DELIMITER$\\n#weak This risk shows once we have used #v {k['DEFAULT_FROM']:.0%}#! of our $concept_credit$#!"
 SPEC_RISK_4_BROKE: "\\n\\nAt our current losses, we face [concept_bankruptcy] in #v [{sv('spec_broke_weeks')}|0]#! weeks. This already costs [{v('spec_tm_broke')}|+=1] [concept_spec_market_confidence] a month."
 SPEC_RISK_4_NONE: "#header Default Risk#!\\nNothing to worry about. Our debt is well within our [concept_credit] limit."
 SPEC_BAR_SRC_TT: "#header Panic Risk: #N -[{SRC_HIT}|1]#!#!\\n$TOOLTIP_DELIMITER$\\nIf #v [{SRC}.GetName]#! falls into a [concept_spec_financial_panic], it could spread to us and cost #N [{SRC_HIT}|1]#! [concept_spec_market_confidence]. Its market is #v [{by_tier('SPEC_TIER', value=SRC_CONF)}]#! right now.\\n\\n[SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(1)}), 'SPEC_BAR_TIE_1', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(2)}), 'SPEC_BAR_TIE_2', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(3)}), 'SPEC_BAR_TIE_3', SelectLocalization(EqualTo_CFixedPoint({v('spec_risk_src_tie')}, {fx(4)}), 'SPEC_BAR_TIE_4', 'SPEC_BAR_TIE_5'))))]\\n$TOOLTIP_DELIMITER$\\n#N -{k['CONTAGION']}#! from a [concept_spec_foreign_panic]#indent_newline:3 \\n#v x[{v('spec_risk_src_size')}|2]#! from the size of their economy next to ours\\n#v x[{v('spec_risk_src_w')}|2]#! from our [concept_spec_market_tie]\\n#v x[{v('spec_risk_src_reach')}|2]#! from their [concept_rank][AddLocalizationIf({not1('spec_foreign_loss_mult')}, 'SPEC_FOREIGN_UNSTD')]{shelter_rows('SPEC_SRC', sv('spec_world_shelter'), sv('spec_bc_shelter'), v('spec_risk_src_pb', 1))}#!\\n$TOOLTIP_DELIMITER$\\n#weak Only a market that is #v {BAND_NAMES[0]}#!, #v {BAND_NAMES[1]}#! or in #v {BAND_NAMES[-1]}#! can spread a panic#!"
 SPEC_BAR_TIE_1: "#v [{SRC}.GetName]#! shares our [concept_market]."
 SPEC_BAR_TIE_2: "#v [{SRC}.GetName]#! is our overlord or [concept_subject]."
 SPEC_BAR_TIE_3: "#v [{SRC}.GetName]#! has investment rights with us by treaty."
 SPEC_BAR_TIE_4: "Our [concept_market] relies on trade with #v [{SRC}.GetName]#!."
 SPEC_BAR_TIE_5: "#v [{SRC}.GetName]#! owns a large share of our economy."
 SPEC_DEPTH_LINE: "{word(sv('spec_depth'), 'SPEC_DEPTH', vanilla_ties.DEPTH_WORDS)}"
 SPEC_DEPTH_0: "\\nWe have few $building_financial_district$, so booms and their endings are milder here."
 SPEC_DEPTH_1: ""
 SPEC_DEPTH_2: "\\nOur $building_financial_district$ make booms and their endings stronger here."
 SPEC_STATE_TITLE: "[SelectLocalization({IN_PANIC}, 'SPEC_STATE_PANIC', {by_tier('SPEC_STATE', state_names)})][AddLocalizationIf(EqualTo_CFixedPoint({P}.ScriptValue('spec_stage'), {fx(6)}), 'SPEC_STATE_LD')]"
 SPEC_STATE_LD: " in the [concept_spec_long_depression]"
 SPEC_STATE_PANIC: "#n Financial Panic#!"
{''.join(f' SPEC_STATE_{s.upper()}: "{n}"{chr(10)}' for s, n in zip(state_names, BAND_NAMES))}
 SPEC_STATE_DESC: "[SelectLocalization({IN_PANIC}, 'SPEC_STATE_DESC_PANIC', {by_tier('SPEC_STATE_DESC', state_names)})]"
 SPEC_STATE_DESC_PANIC: "$SPEC_PANIC_LEFT$. [SelectLocalization({rescued}, 'SPEC_STATE_DESC_PANIC_RESCUED', 'SPEC_STATE_DESC_PANIC_FULL')]"
 SPEC_STATE_DESC_PANIC_FULL: "Until then, [concept_private_construction] is #N [{sv('spec_panic_cut_shown')}|%0]#! lower."
 SPEC_STATE_DESC_PANIC_RESCUED: "Until then, [concept_private_construction] is #N [{sv('spec_panic_cut_shown')}|%0]#! lower, eased by the Bank Rescue."
 SPEC_STATE_DESC_SHAKEN: "{invest_line('panic')} No new [concept_spec_financial_panic] can begin for #v [{cooldown}|0]#! {months.format(cooldown)}."
 SPEC_STATE_DESC_WARY: "[SelectLocalization({gt(cooldown)}, 'SPEC_STATE_DESC_WARY_SAFE', 'SPEC_STATE_DESC_WARY_RISK')]"
 SPEC_STATE_DESC_WARY_RISK: "{invest_line('wary')} A sharp fall in prices could set off a [concept_spec_financial_panic]."
 SPEC_STATE_DESC_WARY_SAFE: "{invest_line('wary')} No new [concept_spec_financial_panic] can begin for #v [{cooldown}|0]#! {months.format(cooldown)}."
 SPEC_STATE_DESC_STEADY: "Investment follows the market as normal."
 SPEC_STATE_DESC_BUOYANT: "{invest_line('buoyant')}"
 SPEC_STATE_DESC_MANIA: "{invest_line('mania')} A sharp fall in prices would hit [concept_spec_market_confidence] hard."
{tiers} SPEC_TIER_PANIC_TT: "#header {BAND_NAMES[0]}#!\\n[concept_spec_market_confidence] below #v {TIERS[0][2]}#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_GAUGE_FX_SHAKEN$\\n\\nA [concept_spec_financial_panic] starts below #v [{sv('spec_panic_at')}|0]#!. It cuts [concept_private_construction] by #N [{sv('spec_panic_cut_if')}|%0]#! for up to #v [{sv('spec_panic_months_trust')}|0]#! months.{' [concept_spec_leverage] makes it deeper and longer.' if leverage.ON else ''}\\n\\n#weak After a panic, no new one can start for #v {k['PANIC_COOLDOWN']}#! months.#!"
 SPEC_TIER_WARY_TT: "#header {BAND_NAMES[1]}#!\\n[concept_spec_market_confidence] from #v {TIERS[1][1]}#! to #v {TIERS[1][2]}#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_GAUGE_FX_WARY$\\n\\nBanks do not lend, and a [concept_spec_financial_panic] starts below #v [{sv('spec_panic_at')}|0]#!."
 SPEC_TIER_STEADY_TT: "#header {BAND_NAMES[2]}#!\\n[concept_spec_market_confidence] from #v {TIERS[2][1]}#! to #v {TIERS[2][2]}#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_GAUGE_FX_STEADY$\\n\\nBanks lend only while [concept_spec_market_confidence] is above #v {credit_from}#!. It drifts back toward its [concept_spec_baseline] of #v {k['CONF_START']}#!."
 SPEC_TIER_BUOYANT_TT: "#header {BAND_NAMES[3]}#!\\n[concept_spec_market_confidence] from #v {TIERS[3][1]}#! to #v {TIERS[3][2]}#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_GAUGE_FX_BUOYANT$\\n\\nBanks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is above #v {credit_from}#!, unless [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')] stops them."
 SPEC_TIER_MANIA_TT: "#header {BAND_NAMES[4]}#!\\n[concept_spec_market_confidence] above #v {mania}#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_GAUGE_FX_MANIA$\\n\\nBanks lend the most here, but a fall in prices also hurts the most."
 SPEC_PANIC_LEFT: "Ends in #v [{PANIC_LEFT}|0]#! {months.format(PANIC_LEFT)}"
 SPEC_PANIC_NONE: "No [concept_spec_financial_panic]"
 SPEC_PANIC_BAR: "[SelectLocalization({IN_PANIC}, 'SPEC_PANIC_BAR_ON', 'SPEC_PANIC_BAR_OFF')]"
 SPEC_PANIC_BAR_ON: "#N [{v('spec_panic', 0)}|0]#! of #v [{v('spec_panic_len', 1)}|0]#! months left"
 SPEC_PANIC_BAR_OFF: "Begins below #v [{sv('spec_panic_at')}|0]#! [concept_spec_market_confidence]"
 SPEC_PANIC_NONE_TT: "#header [concept_spec_financial_panic]: #P None#!#!\\n$TOOLTIP_DELIMITER$\\nNothing to worry about. There is no panic right now.\\n$TOOLTIP_DELIMITER$\\nA [concept_spec_financial_panic] will begin if [concept_spec_market_confidence] falls below #v [{sv('spec_panic_at')}|0]#!. It would last up to #v [{sv('spec_panic_months_trust')}|0]#! months.\\n\\n#v {k['PANIC_DAYS'] / 30:g}#! months base{len_lines}\\n$TOOLTIP_DELIMITER$\\n#weak Rounded up to whole months#!"
{len_loc} SPEC_PANIC_SUB: "[SelectLocalization({gt(v('spec_clawed'))}, 'SPEC_PANIC_LOANS', 'SPEC_PANIC_NO_LOANS')]"
 SPEC_RECALL_DETAIL: "#indent_newline:3 \\n#v @money![{v('spec_recall_balance')}|D]#! from [concept_spec_outstanding_credit] before the panic\\n#v x{k['CLAWBACK']:g}#! from the share banks call back{recall_lax}[AddLocalizationIf(LessThan_CFixedPoint({v('spec_clawed')}, {v('spec_recall_requested')}), 'SPEC_RECALL_LIMIT')]#!"
 SPEC_RECALL_LAX: "\\n#v x[{v('spec_recall_lax', 1)}|2]#! from [concept_spec_lending_standards]"
 SPEC_DEBT_LAX: "\\n#v x[{sv('spec_lax_recall')}|2]#! from [concept_spec_lending_standards]"
 SPEC_RECALL_LIMIT: "\\n#N -@money![Subtract_CFixedPoint({v('spec_recall_requested')}, {v('spec_clawed')})|D]#! from the most a panic can take, #v [{v('spec_recall_pool_share', 1)}|%1]#! of our [concept_investment_pool]"
 SPEC_PANIC_LOANS: "Banks called in #v @money![{v('spec_clawed')}|D]#! of loans"
 SPEC_PANIC_NO_LOANS: "No loans were called in"
 SPEC_PANIC_TT: "$SPEC_GAUGE_HEAD$\\n$SPEC_PANIC_LEFT$\\n$SPEC_GAUGE_CHANGE$\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!#indent_newline:3 \\n[SelectLocalization({rescued}, 'SPEC_PANIC_ALL_EFFECTS_RESCUED', 'SPEC_PANIC_ALL_EFFECTS')]\\n$SPEC_PANIC_SUB$.[AddLocalizationIf(And({P}.Var('spec_recall_balance').IsSet, {gt(v('spec_clawed'))}), 'SPEC_RECALL_DETAIL')]\\n$SPEC_GAUGE_LEND$#!\\n\\n[AddLocalizationIf({rescued}, 'SPEC_PANIC_RESCUED_NOTE')]{panic_bad}$SPEC_PANIC_TT_END$"
{"".join(f""" SPEC_PANIC_EFFECTS{key}: "[concept_private_construction] is #N [{sv('spec_panic_cut_shown')}|%0]#! lower.\\n{pops} invest #N {-k['PANIC_INVEST'] * 100 * h:g}%#! less.\\n[Concept('concept_company','$concept_companies$')] lose #N {-companies.PANIC_COMPANY * 100 * h:g}%#! [concept_throughput].\\n${companies.FD_SOL}$: #N {companies.FD_PANIC * h:g}#!\\n{igs}: #N {k['PANIC_APPROVAL'] * h:g}#! [concept_approval]\\nAs it began, {radicals} became [Concept('concept_radical','$concept_radicals$')]"
""" for key, h in (("", 1), ("_RESCUED", k['RESCUE_CUT'])))} SPEC_PANIC_RESCUED_NOTE: "The Bank Rescue halves these effects. "
 SPEC_PANIC_TT_END: "$SPEC_PANIC_RELIEF_NOTE$\\n\\n$SPEC_PANIC_RECOVERY$"
 SPEC_PANIC_ALL_EFFECTS: "$SPEC_PANIC_ECONOMY$\\n$SPEC_PANIC_EFFECTS$"
 SPEC_PANIC_ALL_EFFECTS_RESCUED: "$SPEC_PANIC_ECONOMY_RESCUED$\\n$SPEC_PANIC_EFFECTS_RESCUED$"
 SPEC_PANIC_ECONOMY: "$ALL_BUILDINGS$: [concept_throughput] #N {k['PANIC_THROUGHPUT']:+.0%}#!\\n$state_tax_collection_mult$: #N {k['PANIC_TAX']:+.0%}#!"
 SPEC_PANIC_ECONOMY_RESCUED: "$ALL_BUILDINGS$: [concept_throughput] #N {k['PANIC_THROUGHPUT'] * k['RESCUE_CUT']:+.0%}#!\\n$state_tax_collection_mult$: #N {k['PANIC_TAX'] * k['RESCUE_CUT']:+.1%}#!"
 spec_panic_relief: "Panic Relief"
 spec_panic_relief_desc: "The Treasury makes weekly payments to the unemployed until the [concept_spec_financial_panic] ends."
 SPEC_RESCUE_EXCEPTIONS: "#weak Does not cut $spec_panic_relief$ or win back the people radicalized when the panic began#!"
 SPEC_PANIC_RELIEF_NOTE: "#v $spec_panic_relief$#! pays the unemployed from the Treasury every week until the panic ends"
 SPEC_PANIC_RECOVERY: "Ends early once [concept_spec_market_confidence] is back to #v {k['PANIC_ENDS_AT']}#!\\nNo new panic for #v {k['PANIC_COOLDOWN']}#! months after it ends"
 SPEC_RESCUE: "[SelectLocalization({gt(sv('spec_rescued_value'))}, 'SPEC_RESCUED', 'SPEC_RESCUE_LABEL')]"
 SPEC_RESCUE_LABEL: "Lend to the Banks"
 SPEC_RESCUED: "Lent to the Banks"
 SPEC_RESCUE_TT: "$SPEC_RESCUE_ACTION_TT$\\n\\n$SPEC_RESCUE_EXCEPTIONS$"
 SPEC_RESCUE_ACTION_TT: "#header Lend to the Banks#!\\n$TOOLTIP_DELIMITER$\\nThe panic ends within #v [{sv('spec_rescue_months')}|0]#! months, and its ongoing penalties are cut by #P {1 - k['RESCUE_CUT']:.0%}#!\\nOur [concept_spec_market_confidence] rises by #P {k['RESCUE_CONF']}#!{no_rescue}\\n\\n{sg('rescue', 'BuildTooltip')}"
 SPEC_H_POLICY: "Credit Policy"
 SPEC_H_POLICY_TT: "#header $concept_spec_credit_policy$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_credit_policy_desc$"
 SPEC_POLICY_TT: "[SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(-1)}), 'SPEC_STANCE_TIGHT_TT', SelectLocalization(EqualTo_CFixedPoint({STANCE}, {fx(1)}), 'SPEC_STANCE_LOOSE_TT', 'SPEC_STANCE_NORMAL_TT'))]"
 SPEC_H_RESCUE: "Bank Rescue"
 SPEC_H_RESCUE_TT: "#header Bank Rescue#!\\n$TOOLTIP_DELIMITER$\\nDuring a [concept_spec_financial_panic], #v Lend to the Banks#! ends it within #v [{sv('spec_rescue_months')}|0]#! months, cuts its penalties for the months left by #P {1 - k['RESCUE_CUT']:.0%}#! and raises [concept_spec_market_confidence] by #P {k['RESCUE_CONF']}#!. It costs about #v [{sv('spec_rescue_share_now')}|%1]#! of [concept_gdp], more the longer the panic has left to run, and can be used once per panic."
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
 SPEC_CREDIT_NO_PANIC: "Not lending during a [concept_spec_financial_panic]"
 SPEC_CREDIT_NO_CRASH: "Not lending in the World Crash"
 SPEC_CREDIT_NO_TIGHT: "Not lending under [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]"
 SPEC_CREDIT_NO_CONF: "Not lending below #v {credit_from}#! [concept_spec_market_confidence]"
 SPEC_CREDIT_LENDING: "Lending while [concept_spec_market_confidence] is above #v {credit_from}#!"
 SPEC_POLICY_COOLDOWN: "[SelectLocalization(EqualTo_CFixedPoint({cd}, {fx(1)}), 'SPEC_POLICY_COOLDOWN_ONE', 'SPEC_POLICY_COOLDOWN_MANY')]"
 SPEC_POLICY_COOLDOWN_ONE: "Can be changed in #v 1#! month"
 SPEC_POLICY_COOLDOWN_MANY: "Can be changed in #v [{cd}|0]#! months"
 SPEC_STANCE_TIGHT_TT: "#header Tight Credit#!\\n$TOOLTIP_DELIMITER$\\nBanks stop lending. Each month, #N {tight_pull:.0%}#! of our [concept_spec_market_confidence] above #v {tight_from}#! drains away.\\n\\nInvestor Reaction: #N -{1 - k['STANCE_HYPE']['tight']:.0%}#!\\n{credit_ai.ig_lines('tight')}\\n\\n#weak Booms grow smaller, and their endings and panics are softer.#!{lock['tight']}"
 SPEC_STANCE_NORMAL_TT: "#header Normal Credit#!\\n$TOOLTIP_DELIMITER$\\nBanks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is above #v {credit_from}#!. This month they would lend #v @money![{sv('spec_credit_preview')}|D]#!.{lock['normal']}"
 SPEC_STANCE_LOOSE_TT: "#header Loose Credit#!\\n$TOOLTIP_DELIMITER$\\nBanks lend freely into the [concept_investment_pool]. This month they would lend #v @money![{sv('spec_credit_preview_loose')}|D]#!.\\n\\nLending Rate: #P +{k['STANCE_CREDIT']['loose'] - 1:.0%}#!\\nInvestor Reaction to rising prices: #P +{k['STANCE_HYPE']['loose'] - 1:.0%}#!\\n{credit_ai.ig_lines('loose')}\\n\\n#weak Booms grow bigger, and so do the losses when they end.#!{lock['loose']}"
 SPEC_CREDIT_CURRENT: ""
{why_loc} SPEC_CREDIT_LOCK: "\\n\\nLocks [concept_spec_credit_policy] for #v {k['STANCE_COOLDOWN']}#! months"
 SPEC_EFFECT_GIVEN_TT: "#header Credit Lent This Month: #v @money![{v('spec_credit_given')}|D]#!#!\\n$TOOLTIP_DELIMITER$\\nMoney our banks add to our [concept_investment_pool]. They lend every month while [concept_spec_market_confidence] is above #v {credit_from}#!, more the higher it goes, until they reach our Lending Limit.\\n\\nLending Rate: #v x[{credit_rate}|2]#! (#v {word(credit_rate, 'SPEC_CREDITW', [0.01, 0.5, 1.15, 1.8])}#!)#indent_newline:3 {rate_lines}#!\\n$TOOLTIP_DELIMITER$\\n#weak The rate is how freely our banks lend, not interest we pay. The [concept_investment_pool] shows the lending week by week.#!"
{rate_loc} SPEC_EFFECT_DEBT: "Withdrawn in a Panic"
 SPEC_DEBT_BAR: "[SelectLocalization(GreaterThan_CFixedPoint({POOL}, {fx(0)}), 'SPEC_DEBT_BAR_ON', 'SPEC_DEBT_BAR_NONE')]"
 SPEC_DEBT_BAR_ON: "A panic would take #N @money![{sv('spec_clawback')}|D]#! of our @money![{POOL}|D] [concept_investment_pool]"
 SPEC_DEBT_BAR_NONE: "Our [concept_investment_pool] is empty, so a panic has nothing to take"
 SPEC_EFFECT_OWED: "[concept_spec_outstanding_credit]"
 SPEC_EFFECT_OWED_VALUE: "#v @money![{v('spec_debt')}|D]#!"
 SPEC_EFFECT_OWED_TT: "#header [concept_spec_outstanding_credit]: #v @money![{v('spec_debt')}|D]#!#!\\n$TOOLTIP_DELIMITER$\\nMoney our banks have lent into our [concept_investment_pool].{owed_lev}\\n[AddLocalizationIf({gt(v('spec_credit_given'))}, 'SPEC_OWED_LENT')]\\n#N -@money![{sv('spec_credit_runoff')}|D]#! repaid each month (#v {k['CREDIT_RUNOFF']:.0%}#!)\\n$TOOLTIP_DELIMITER$\\nBanks lend each month while [concept_spec_market_confidence] is above #v {credit_from}#!{owed_lim}. A [concept_spec_financial_panic] calls part of it back."
 SPEC_OWED_LENT: "\\n#P +@money![{v('spec_credit_given')}|D]#! lent this month"
{panic_tt} SPEC_PANIC_TAG: "#b Panic#!"
 SPEC_RISK_TAG: "#b Risk#!"
 SPEC_EFFECT_DEBT_VALUE: "#v @money![{sv('spec_clawback')}|D]#!"
 SPEC_EFFECT_DEBT_TT: "#header Withdrawn in a Panic: #N @money![{sv('spec_clawback')}|D]#!#!\\n$TOOLTIP_DELIMITER$\\nThis money is still in our [concept_investment_pool]. If a [concept_spec_financial_panic] began today, banks would call back part of their loans and take it out.\\n\\n#v @money![{v('spec_debt')}|D]#! from [concept_spec_outstanding_credit]#indent_newline:3 \\n#v x{k['CLAWBACK']:g}#! from the share banks call back{claw_lax}[AddLocalizationIf({gt(claw_cut, 1)}, 'SPEC_DEBT_CAP')]#!\\n$TOOLTIP_DELIMITER$\\n#weak {claw_note}$concept_spec_outstanding_credit$ shrinks by #v {k['CREDIT_RUNOFF']:.0%}#! a month as loans are paid off.#!"
 SPEC_DEBT_CAP: "\\n#N -@money![{claw_cut}|D]#! from the most a panic can take, #v [{claw_share}|%0]#! of our [concept_investment_pool]"
{lev_loc} SPEC_CREDITW_0: "None"
 SPEC_CREDITW_1: "Low"
 SPEC_CREDITW_2: "Normal"
 SPEC_CREDITW_3: "High"
 SPEC_CREDITW_4: "Very High"
 SPEC_H_MOOD: "Market Confidence"
 SPEC_H_MOOD_TT: "#header $concept_spec_market_confidence$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_market_confidence_desc$"
 SPEC_H_GOODS: "Investor Interest"
 SPEC_H_GOODS_TT: "#header $concept_spec_investor_interest$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_investor_interest_desc$"
 SPEC_INTEREST: "{word(WORD, 'SPEC_INTEREST', [1.5, 2.5, 3.5, 4.5, 5.5])}"
{"".join(f' SPEC_INTEREST_{i}: "@spec_interest_{WORDS[i + 1]}! {WORDS[i + 1].capitalize()}"' + chr(10) for i in range(6))} SPEC_GOODS_NONE: ""
 SPEC_TILE_TT: "#header [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BODY$\\n\\n#instruction Click to open the [Goods.GetName] panel#!"
 SPEC_II_TREND: "Recent prices are #v [{TREND}|=+%1]#! from their long-run average, which sets its [concept_spec_investor_interest].\\nIf prices hold, the trend will be #v [Subtract_CFixedPoint({fast_n}, {slow_n})|=+%1]#! next month.#indent_newline:3 \\n#v [{fast_n}|=+%1]#! from recent prices over [concept_base_price]\\n#v [Multiply_CFixedPoint({slow_n}, {fx(-1)})|=+%1]#! from long-run prices over [concept_base_price]#![AddLocalizationIf({P}.Var(Concatenate('spec_push_', Goods.GetKey)).IsSet, 'SPEC_II_PUSH')][AddLocalizationIf({gt(good_var('spec_glut'))}, 'SPEC_II_GLUT')]"
 SPEC_II_PUSH: "\\n\\n[concept_spec_intervention] multiplies its interest by #v [{good_sv('spec_push_sv')}|2]#! so far."
 SPEC_II_GLUT: "\\n\\nWhile it recovers, its interest is held at #v Doubtful#! or lower."
 concept_spec_market_sector: "Market Sector"
 concept_spec_market_sector_desc: "Each tracked good belongs to one sector. The chart values all tracked goods offered for sale at their [concept_base_price]. Goods with a larger share of this supply count more toward their sector’s trend. If the sector moves less than the good or moves the other way, its price pressure on [concept_spec_investor_interest] can fall by up to half."
 SPEC_SECTOR_OTHER: "Other sectors"
 SPEC_SECTOR_TURNOVER_LINK: "[Concept('concept_spec_market_sector','$SPEC_SECTOR_TURNOVER$')]"
 SPEC_SECTOR_FILTER_LINK: "[Concept('concept_spec_market_sector','$SPEC_MARKET_SECTORS$')]"
 SPEC_MARKET_SECTORS: "Market Sectors"
 SPEC_SECTOR_PRICE_TREND: "Previous sector price trend"
 SPEC_SECTOR_TURNOVER: "Goods for sale by sector"
 SPEC_SECTOR_SHARE: "Share of goods for sale"
 SPEC_SECTOR_RISING: "rising"
 SPEC_SECTOR_FALLING: "falling"
 SPEC_SECTOR_FLAT: "flat"
 SPEC_SECTOR_WAIT: "Awaiting the first sector comparison."
 SPEC_SECTOR_NO_MOVE: "This good had no price pressure to dampen."
 SPEC_SECTOR_EFFECT: "That softened this good's pull on [concept_spec_investor_interest] by #v [{good_sv('spec_review_reduction')}|%0]#!."
 SPEC_SECTOR_REVIEW: "Last month its sector's prices were #v [{direction}]#! ([{mean}|=+%1]). [SelectLocalization(EqualTo_CFixedPoint({TREND}, {fx(0)}), 'SPEC_SECTOR_NO_MOVE', 'SPEC_SECTOR_EFFECT')]"
 SPEC_SECTOR_LINE: "It belongs to the #v [{sector_name}]#! [concept_spec_market_sector]. [SelectLocalization({gt(good_sv('spec_review_has'))}, 'SPEC_SECTOR_REVIEW', 'SPEC_SECTOR_WAIT')]"
 SPEC_TILE_REACT: "#tooltippable #tooltip:[Country.GetTooltipTag],SPEC_WHY_SPEED Investors here react #v [{sv('spec_hype_mult')}|2]#! times as strongly as usual.#!#!"
 SPEC_TILE_TREND: "\\nRecent prices are #v [{TREND}|=+%1]#! from their long-run average."
 SPEC_TILE_BODY: "Investors are #v $SPEC_INTEREST$#! about [Goods.GetName], $SPEC_TILE_MOVE$.$SPEC_TILE_TREND$$SPEC_TILE_NEXT$\\n$TOOLTIP_DELIMITER$\\nIts producers' [concept_throughput] changes by $SPEC_PULL$.$SPEC_TILE_LIFT$\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BOOM$$SPEC_TILE_BANKS$"
 SPEC_IL_TREND_TT: "#header Price Trend of [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_II_TREND$\\n\\n$SPEC_SECTOR_LINE$\\n\\n$SPEC_TILE_REACT$"
 SPEC_TILE_BOOM: "[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_sev')}, {fx(1)}), 'SPEC_TILE_BOOM_ON', SelectLocalization(GreaterThan_CFixedPoint({good_var('spec_glut')}, {fx(0)}), 'SPEC_TILE_BOOM_PAST', 'SPEC_TILE_BOOM_NONE'))]"
 SPEC_TILE_BOOM_ON: "If the boom ended now, it would be a $SPEC_UNWIND_LINK$[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({RISK}, {fx(0.05)}), 'SPEC_TILE_BOOM_COST', 'SPEC_TILE_BOOM_SLIGHT')]."
 SPEC_TILE_BOOM_COST: " costing #N [{RISK}|1]#! [concept_spec_market_confidence]"
 SPEC_TILE_BOOM_SLIGHT: " costing a little [concept_spec_market_confidence]"
 SPEC_TILE_BOOM_PAST: "It is recovering from a [SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_glut')}, {fx(3)}), 'SPEC_UNWIND_C_3', SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({good_var('spec_glut')}, {fx(2)}), 'SPEC_UNWIND_C_2', 'SPEC_UNWIND_C_1'))].[AddLocalizationIf({gt(good_var('spec_glut_until'))}, 'SPEC_IL_RECOVERY_LEFT')]"
 SPEC_TILE_BOOM_NONE: "It cannot boom until its interest reaches @spec_interest_keen! #v Keen#!."
 SPEC_PULL: "{word(WORD, 'SPEC_PULL', [1.5, 2.5, 3.5, 4.5, 5.5])}"
{"".join(f' SPEC_PULL_{w - 1}: "{"#P +" if p > 0 else "#N " if p < 0 else "#v "}{p}%#!"' + chr(10) for w, p in companies.INTEREST_THROUGHPUT.items())} SPEC_TILE_LIFT: "[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({HYPE}, {fx(k['HOT_HYPE'])}), 'SPEC_TILE_LIFTS', 'SPEC_GOODS_NONE')]"
 SPEC_TILE_LIFTS: "\\nIt is booming, so it lifts [concept_spec_market_confidence] each month."
 SPEC_TILE_MOVE: "[SelectLocalization(EqualTo_CFixedPoint({MOVE}, {fx(1)}), 'SPEC_TILE_RISING', SelectLocalization(EqualTo_CFixedPoint({MOVE}, {fx(-1)}), 'SPEC_TILE_FALLING', 'SPEC_TILE_STEADY'))]"
 SPEC_TILE_RISING: "#P up#! from last month"
 SPEC_TILE_FALLING: "#N down#! from last month"
 SPEC_TILE_STEADY: "the same as last month"
 SPEC_RISK_NONE_TT: "$SPEC_RISK_NONE$"
 SPEC_INTEREST_TT: "#header [concept_spec_investor_interest] in [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BODY$"
 SPEC_CALC_BANK_EXPOSURE: "from bank loans tied to this good"
 SPEC_CALC_OVERBUILDING: "from supply growth since the boom began"
 SPEC_RISK_LEAD: "If the boom ended now, [concept_spec_market_confidence] would fall by this much."
 SPEC_RISK_TT: "#header Risk of a $SPEC_UNWIND$: #N -[{rounded_tenth(RISK)}|1]#!#!\\n$TOOLTIP_DELIMITER$\\n{why_lines(good_var, good_sv, k)}\\n$TOOLTIP_DELIMITER$\\n$SPEC_UNWIND_DESC$"
{band_loc(k)}
 SPEC_DRIVER_RESTRAIN_TT: "#header Restrained Booms: [{v('spec_c_restrain')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_restrain_raw')}|+=1] from booms we are letting down gently#indent_newline:3 \\n{cond_row(ratio('spec_c_restrain', 'spec_restrain_raw'))}#!\\n$TOOLTIP_DELIMITER$\\n#weak A restrained boom winds down slowly as a [concept_spec_correction] instead of ending all at once.#!"
 SPEC_DRIVER_CAUTION_TT: "#header Government and Events: [{v('spec_c_caution')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nOur decisions and market events changed [concept_spec_market_confidence] once this month."
 SPEC_DRIVER_LIMIT_TT: "#header Floor and Ceiling: [{v('spec_c_limit')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[concept_spec_market_confidence] cannot fall below #v 0#! or rise above #v 100#!, so this much of the month's change was lost."
 SPEC_DRIVER_RESCUE_TT: "#header Bank Rescue: [{v('spec_c_rescue')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n#v $SPEC_RESCUE_LABEL$#! or #v Suspend the Bank Act#! raised our [concept_spec_market_confidence] once this month."
 SPEC_DRIVER_RESCUE: "Bank Rescue"
 SPEC_DRIVER_WAREND: "End of War"
 SPEC_DRIVER_WAREND_TT: "#header End of War: [{v('spec_c_warend')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nWe felt #v [{v('spec_war_stakes_now')}|%0]#! of the full effect, because of our [concept_casualties].\\n\\nWinning a war and enforcing a [concept_war_goal] raises [concept_spec_market_confidence] by #P {k['WAR_END']['won'][0]:g}#!, and winning without one by #P {k['WAR_END']['won'][1]:g}#!. Losing and giving up a war goal lowers it by #N {-k['WAR_END']['lost'][0]:g}#!, and losing without giving one up by #N {-k['WAR_END']['lost'][1]:g}#!. A war nobody wins lowers it by #N {-k['WAR_END']['drawn'][0]:g}#!.\\n\\n#weak We always feel at least #v {diplomacy.WAR_STAKES_MIN:.0%}#! of this, and all of it once the war has cost #v {diplomacy.WAR_STAKES_FULL:.0%}#! of our forces.#!"
 SPEC_DRIVER_BURST: "Bubble Bursts"
 SPEC_DRIVER_BURST_TT: "#header Bubble Bursts: [{v('spec_c_burst')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nOur bubble of #v [Divide_CFixedPoint({v('spec_c_burst')}, Multiply_CFixedPoint({sv('spec_burst_per_heat')}, {fx(-1)}))|0]#! [concept_spec_speculative_excess] burst. Each point cost #N [{sv('spec_burst_per_heat')}|2]#! [concept_spec_market_confidence].\\n\\n#weak A bubble grows while [concept_spec_market_confidence] stays at #v [{sv('spec_heat_from')}|0]#! or more, and bursts if it falls below #v {k['BURST_BELOW']}#!. It needs [GetTechnology('stock_exchange').GetName].#!"
 SPEC_DRIVER_CAUTION: "Government and Events"
 SPEC_DRIVER_RESTRAIN: "Restrained Booms"
 SPEC_DRIVER_LIMIT: "Floor and Ceiling"
 SPEC_DRIVER_BOOM: "Booming Goods"
 SPEC_DRIVER_BOOM_TT: "#header Booming Goods: [{v('spec_c_boom')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_boom_raw')}|+=1] from #v [{v('spec_n_boom')}|0]#! booming {goods}#indent_newline:3 [AddLocalizationIf({gt(v('spec_boom_raw'), k['CONF_BOOM_MAX'])}, 'SPEC_BOOM_CAP')][AddLocalizationIf({not1('spec_steady')}, 'SPEC_BOOM_STEADY')][AddLocalizationIf({not1('spec_fin_boom')}, 'SPEC_BOOM_FIN')][AddLocalizationIf({not1('spec_boom_rule')}, 'SPEC_BOOM_RULE')]#!\\n$TOOLTIP_DELIMITER$\\n#weak A good's boom adds more the bigger its share of our [concept_market]. [GetTechnology('stock_exchange').GetName], [GetTechnology('investment_banks').GetName] and [GetTechnology('modern_financial_instruments').GetName] make booms add more, and they add nothing during a [concept_spec_financial_panic].#!"
 SPEC_BOOM_CAP: "\\nCapped at #v +{k['CONF_BOOM_MAX']}#! before the multipliers below"
 SPEC_BOOM_STEADY: "\\n#v x[{sv('spec_steady')}|2]#! from Manor Houses"
 SPEC_BOOM_FIN: "\\n#v x[{sv('spec_fin_boom')}|2]#! from finance technologies"
 SPEC_BOOM_RULE: "\\n#v x[{sv('spec_boom_rule')}|2]#! from Market Volatility"
 SPEC_DRIVER_CRASH: "Ended Booms"
 SPEC_DRIVER_CRASH_TT: "#header Ended Booms: [{v('spec_c_crash')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[{v('spec_crash_raw')}|+=1] from how big the ended booms were#indent_newline:3 \\n{cond_row(ratio('spec_c_crash', 'spec_crash_raw'))}#![AddLocalizationIf(Not(GreaterThan_CFixedPoint({v('spec_c_crash')}, {fx(-k['CONF_CRASH_MAX'])})), 'SPEC_CRASH_CAP')]\\n\\nThe biggest loss came from the end of our #v [{P}.Var('spec_crashed').GetGoods.GetName]#! boom.\\n$TOOLTIP_DELIMITER$\\n#weak Bigger booms, and goods with more of our [concept_market], cost more. [GetTechnology('mutual_funds').GetName] softens the loss and [GetTechnology('modern_financial_instruments').GetName] deepens it.#!"
 SPEC_CRASH_CAP: "\\nEnded booms cannot take more than #N {k['CONF_CRASH_MAX']:g}#! in a month."
 SPEC_DRIVER_FOREIGN: "Foreign Panics"
 SPEC_FOREIGN_HIT: "\\n#N -{k['CONTAGION']}#! from a [concept_spec_foreign_panic]#indent_newline:3 \\n#v x[{v('spec_fh_size')}|2]#! from the size of their economy next to ours\\n#v x[{v('spec_fh_tie')}|2]#! from our [concept_spec_market_tie]\\n#v x[{v('spec_fh_reach')}|2]#! from their [concept_rank][AddLocalizationIf({not1('spec_foreign_loss_mult')}, 'SPEC_FOREIGN_UNSTD')]{shelter_rows('SPEC_FH', v('spec_fh_world', 1), v('spec_fh_bc', 1), v('spec_fh_pb', 1))}#!"
 SPEC_FOREIGN_UNSTD: "\\n#v x[{sv('spec_foreign_loss_mult')}|2]#! from not having [GetTechnology('currency_standards').GetName]"
{shelter_keys('SPEC_FH', v('spec_fh_world', 1), v('spec_fh_bc', 1), v('spec_fh_pb', 1))}{shelter_keys('SPEC_SRC', sv('spec_world_shelter'), sv('spec_bc_shelter'), v('spec_risk_src_pb', 1))}
 SPEC_FOREIGN_FLIGHT: "\\n[{v('spec_c_flight')}|+=2] from [concept_spec_capital_flight]"
 SPEC_DRIVER_FOREIGN_TT: "#header Foreign Panics: [{v('spec_c_foreign')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nThe latest panic to reach us came from #v [{P}.Var('spec_foreign_src').GetCountry.GetName]#!.\\n[AddLocalizationIf({nonzero(f"Subtract_CFixedPoint({v('spec_c_foreign')}, {v('spec_c_flight')})", 0.01)}, 'SPEC_FOREIGN_HIT')][AddLocalizationIf({nonzero(v('spec_c_flight'), 0.01)}, 'SPEC_FOREIGN_FLIGHT')]\\n$TOOLTIP_DELIMITER$\\nThrough a [concept_spec_market_tie], #v [{sv('spec_tie_market')}|%0]#! of a panic reaches us from a shared [concept_market], #v {k['LINKS']['subject']:.0%}#! from a subject or overlord, #v [{sv('spec_tie_investment')}|%0]#! through investment rights, #v [{sv('spec_tie_trade')}|%0]#! through heavy trade, and up to #v {k['LINKS']['owned']:.0%}#! through foreign ownership. Ties do not add up, and only the biggest panic in a month counts.\\n\\n#weak A [concept_great_power]'s panic reaches us at #v {k['REACH'][7]:.0%}#!, a major power's at #v {k['REACH'][6]:.0%}#! and a smaller country's at #v {k['REACH_MINOR']:.0%}#!. A panic we caught from abroad does not spread on.#!"
 SPEC_DRIVER_TURMOIL: "War and Unrest"
 SPEC_DRIVER_TURMOIL_TT: "#header War and Unrest: [{v('spec_c_turmoil')}|+=1]#!$SPEC_ITEMS_TURMOIL$\\n$TOOLTIP_DELIMITER$\\nThrough [concept_spec_war_news], each [concept_war] moves [concept_spec_market_confidence] by #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! a month, and all wars together by #N {k['WAR_ALL_MIN']:g}#! to #P +{k['WAR_ALL_MAX']:g}#!.\\n\\nIt also falls by #N {k['PLAY_TURMOIL']:g}#! a month in a [concept_diplomatic_play], by up to #N {k['BROKE_COST']:g}#! from #v {k['BROKE_WEEKS']}#! weeks before [concept_bankruptcy], by #N {k['DEFAULT_COST']:g}#! in [concept_default] and by #N {k['REVOLUTION_COST']:g}#! in a [concept_revolution].\\n\\n#instruction Hover over a figure to see its causes#!"
 SPEC_DRIVER_MOOD: "Market Mood"
 SPEC_DRIVER_MOOD_TT: "#header $SPEC_DRIVER_MOOD$: [{v('spec_c_mood')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[Subtract_CFixedPoint({v('spec_c_mood')}, {v('spec_mood_shift')})|+=1] from last month's mood\\n[SelectLocalization({P}.Var('spec_mood_random').IsSet, 'SPEC_MOOD_SOURCES', 'SPEC_MOOD_COMBINED')]\\n$TOOLTIP_DELIMITER$\\n#weak Each month, [concept_spec_market_mood] keeps #v {k['MOOD_KEEP']:.0%}#! of the last month's and adds a new random swing.#!"
 SPEC_MOOD_COMBINED: "[{v('spec_mood_shift')}|+=1] from this month's swing"
 SPEC_MOOD_SOURCES: "[{v('spec_mood_random')}|+=1] from this month's random swing{mood_company}"
 SPEC_MOOD_COMPANY: "\\n[Subtract_CFixedPoint({v('spec_mood_shift')}, {v('spec_mood_random')})|+=1] from how well our companies are doing"
 SPEC_DRIVER_DRIFT: "Return to Baseline"
 SPEC_DRIVER_DRIFT_TT: "#header Return to Baseline: [{v('spec_c_recover')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n[Divide_CFixedPoint({v('spec_c_recover')}, Divide_CFixedPoint({sv('spec_recover_pct')}, {fx(100)}))|+=1] from the gap to our [concept_spec_baseline] of #v {k['CONF_START']}#!#indent_newline:3 \\n#v x{k['CONF_RECOVER']:g}#! from the share of it that closes each month[AddLocalizationIf({not1('spec_macro')}, 'SPEC_DRIFT_MACRO')]{drift_trust}#!\\n$TOOLTIP_DELIMITER$\\n#weak [GetTechnology('macroeconomics').GetName] makes the gap close faster.#!"
 SPEC_DRIFT_MACRO: "\\n#v x[{sv('spec_macro')}|2]#! from [GetTechnology('macroeconomics').GetName]"
 SPEC_DRIFT_TRUST: "\\n#v x[{sv('spec_exch_recover')}|2]#! from our [concept_spec_exchange]'s [concept_spec_trust]"
 SPEC_DRIVER_TIGHT: "Tight Credit"
 SPEC_DRIVER_GROWTH: "Growth"
 SPEC_DRIVER_GROWTH_TT: "#header Growth: [{v('spec_c_growth')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_gdp] growth against its average of recent months is #v [{v('spec_growth')}|=+%1]#!, and #v {k['GROWTH_NORMAL']:.0%}#! counts as normal.\\n\\n#weak [concept_spec_market_confidence] moves #v {k['GROWTH_K'] / 100:g}#! a month for each point of growth above or below normal, by up to #v {k['GROWTH_MAX']:g}#! either way.#!"
 SPEC_DRIVER_BUSINESS: "Business Mood"
 SPEC_DRIVER_BUSINESS_TT: "#header Business Mood: [{v('spec_c_business')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nThe $ig_industrialists$ have #v [{sv('spec_ind_approval')}|0]#! [concept_approval].\\n\\n{business_lines()}"
 SPEC_DRIVER_TIGHT_TT: "#header Tight Credit: [{v('spec_c_tight')}|+=1]#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_spec_market_confidence] is #v [Divide_CFixedPoint({v('spec_c_tight')}, {fx(-tight_pull)})|1]#! above #v {tight_from}#!. Under [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')], #N {tight_pull:.0%}#! of that drains away each month.\\n\\n#weak This cools a boom slowly instead of all at once.#!"
 concept_spec_market_conditions: "Market Conditions"
 concept_spec_market_conditions_desc: "$concept_spec_market_conditions$ are how hot the market is when a [concept_spec_boom_end] comes. They decide how much [concept_spec_market_confidence] the ending costs. The higher $concept_spec_market_confidence$ is at the time, the bigger the loss. At #v {k['CONF_START']:g}#! they do nothing. Financial Districts, Manor Houses and finance technologies also change them."
 concept_spec_baseline: "Baseline Confidence"
 concept_spec_baseline_desc: "$concept_spec_baseline$ is the level, #v {k['CONF_START']}#!, to which [concept_spec_market_confidence] returns when left alone, from above or below. The further it has strayed, the faster it returns."
 concept_spec_market_mood: "Market Mood"
 concept_spec_market_mood_desc: "A random drift in [concept_spec_market_confidence]. Each month it keeps #v {k['MOOD_KEEP']:.0%}#! of last month's mood and adds a new random swing, whose size depends on the financial system."
 concept_spec_market_tie: "Market Tie"
 concept_spec_market_tie_desc: "A $concept_spec_market_tie$ is how closely one [concept_country] follows another's [concept_market]. It sets how much of a [concept_spec_financial_panic] passes between them.\\n\\nOwnership counts once a country owns #v {k['OWNED_FROM']:.0%}#! of the other's [concept_gdp], and is strongest at #v {k['OWNED_FULL']:.0%}#!. [GetLawType('law_free_trade').GetName] strengthens the trade tie and other trade policies weaken it. [GetTechnology('international_exchange_standards').GetName] strengthens market and investment ties. An [concept_embargo] cuts the trade tie."
 concept_spec_capital_flight: "Capital Flight"
 concept_spec_capital_flight_desc: "When a [concept_spec_financial_panic] begins, money flees to safety. {flight_who} gains up to #P +[GetPlayer.MakeScope.ScriptValue('spec_flight_gain_max')|0]#! [concept_spec_market_confidence] if it is at peace, at #v {BAND_NAMES[2]}#! or better, and not tied to the country in panic. [GetTechnology('international_trade').GetName] and [GetTechnology('international_exchange_standards').GetName] raise the gain.{flight_more}"
 concept_spec_war_news: "War News"
 concept_spec_war_news_desc: "Investors follow a [concept_war] month by month. $concept_spec_war_news$ moves [concept_spec_market_confidence] each month by how it is going. [concept_casualties], [concept_blockade], [concept_devastation], falling [concept_gdp] and a long war lower it, while winning [Concept('concept_battle','$concept_battles$')] and holding enemy land raise it. Each war moves it by #N {k['WAR_WORST']:g}#! to #P +{k['WAR_BEST']:g}#! per month, and all wars together by #N {k['WAR_ALL_MIN']:g}#! to #P +{k['WAR_ALL_MAX']:g}#!."
"""
