"""Investor Interest: a goods list in a fixed order. One row per traded good, in vanilla's goods
category order (CATEGORIES, as the market panel's filters) and then by key, so a good keeps its place month to
month. A row reads: the good; a six step scale, Fleeing to Feverish, bright up to the marker and dimmed beyond it,
the marker being the good's tier icon; a small arrow when interest rose or fell this month; the interest groups
favoring it, then those opposing it (ig_stances.slot); the Restrain and Encourage buttons. The marker also shows the good's state (interest_board.ui_effect's spec_ui_state_<g>): pulsing while a boom
large enough to Collapse is turning, with a tick at the crash line; a crash icon that pops in the month a boom ends;
the same icon, without the pop, on a muted bar while the good is in a glut. The Interest column's sort button switches
to the monthly word lists (spec_goods_w<w>, hottest first, larger trade first within a word).
market_tab.goods_board shows this.

The fixed rows are static, one per good (datacontext GetGoods('<good>')), so each test reads its variable by name
with no Concatenate; a row shows while the good is traded here (spec_word_<g> > 0). The category filters hide a
whole category's rows at once."""
import re

import icons
import ig_stances
import interest_board
import levers
from interest_board import HEAT, eq
from market_tab import P, W, fx, gt, v, ind, good_var, sv, rounded, rounded_tenth, expiry_date, level_effects, FLAT, BARS, CLEAR, SLIDE, RISK, TREND, WORD, WORDS, LEANING, CATEGORIES, CAT, cat_shown, any_of, goods_filters, FIN

ROW_H = 52
# the groups favoring and opposing the good (ig_stances.slot) after Risk; the scale gave up the width (segments 32 to 21), the
# lever column is its strip's width (3 x 32 + set_level_bar_background's 2 x 5)
# Risk has its own column (it shared the tier name's line, which ran into it); goods (156 to 141) and the tier icon,
# moved before the name, gave the width
COLS = [("goods", 141), ("scale", 177), ("risk", 40), ("fav", ig_stances.SLOT_W), ("dis", ig_stances.SLOT_W), ("lever", 106)]
COL = dict(COLS)
# the interest column: the tier icon and name over a bar of six tier segments. The icon sits before the name, so the
# bar has the column's width (it stood left of both, as tall as the two, until 1.2; sized() keeps that for the goods panel)
NAME_H, BAR_H = 18, 14   # the tier's name over the bar
NAME_GAP = 6             # between the name and the bar (2 read as cramped)
TOP = (ROW_H - NAME_H - NAME_GAP - BAR_H) // 2  # the name line's top
MARK = 22                # the tier icon, a little taller than the name it leads
ICON_X = 6
ICON_Y = TOP - (MARK - NAME_H) // 2
NAME_X, NAME_DY = MARK + 4, (MARK - NAME_H) // 2  # the name line, from the icon's corner
BAR_X, BAR_Y = ICON_X, TOP + NAME_H + NAME_GAP
NAME_FONT = ""           # the tier name's font: the default (sized() can set one)
SEG, GAP = 24, 3         # one tier's segment, and the divider between two
BAR_W = 6 * SEG + 5 * GAP
CRASH_ICON = icons.path("crash_risk")
CRASH_SIZE = 26          # the cracked coin, over the tier icon in the crash month and the glut
SORT = "spec_il_sort"    # GetVariableSystem flag: set, the list is ordered by interest
SORTED = f"GetVariableSystem.Exists('{SORT}')"
RISK_SORT = f"GetVariableSystem.HasValue('{SORT}', 'risk')"
ACTIVE = "spec_il_active"  # GetVariableSystem flag: set, the list shows only goods with an intervention on
FAV_F, DIS_F = "spec_il_fav", "spec_il_dis"  # flags: set, only goods a group favors / opposes (ig_stances.mark)
ANY_FILTER = f"Or(GetVariableSystem.Exists('{ACTIVE}'), Or(GetVariableSystem.Exists('{FAV_F}'), GetVariableSystem.Exists('{DIS_F}')))"
assert sum(COL.values()) == W
assert BAR_X + BAR_W <= COL["scale"] - 8


def var(g):
    """A row's figure reader: by name for a fixed row's good g, through Goods.GetKey for a list row (g None)."""
    return (lambda n: f"{P}.Var('{n}_{g}').GetValueWithDefault({fx(0)})") if g else good_var


def intervention_on(rd):
    """Every active control in the Intervention column, including a Great Issue."""
    active = [eq(rd(f"spec_ui_{kind}"), 2) for kind in ("r", "e")]
    if levers.ISSUE_ON:
        active.append(gt(rd("spec_issue")))
    return any_of(active)


def matches_filters(rd):
    """The same predicate for rows, category groups and the empty-list message."""
    active = f"Or(Not(GetVariableSystem.Exists('{ACTIVE}')), {intervention_on(rd)})"
    stances = (f"And(Or(Not(GetVariableSystem.Exists('{FAV_F}')), {gt(rd('spec_igs_fv'))}), "
               f"Or(Not(GetVariableSystem.Exists('{DIS_F}')), {gt(rd('spec_igs_op'))}))")
    return f"And({gt(rd('spec_word'))}, And({tier_shown(rd)}, And({active}, {stances})))"


def marker(rd):
    """The tier icon left of the bar and everything on the bar that depends on the tier, one widget per tier shown
    only for the good's tier (spec_word), so a frame tests one tier's widgets: the name over the bar and the overlay
    (tier_overlay). The crash icon replaces the tier icon in the crash month and the glut, the overlay staying. One
    state test per widget (spec_ui_state: 0 normal, 1 turning, 2 crash month, 3 glut); a hidden widget's icons are
    not tested."""
    st = lambda n: eq(rd("spec_ui_state"), n)
    word = rd("spec_word")
    name = lambda key, with_trend=False: f"""flowcontainer = {{
	position = {{ {NAME_X} {NAME_DY} }}
	spacing = 8
	textbox = {{
		size = {{ -1 {NAME_H} }}
		autoresize = yes
		align = left|nobaseline
{NAME_FONT}		text = "{key}"
	}}
}}
{trend(rd) if with_trend else ''}"""
    # turning: vanilla's silent two state alpha loop (country_panel.gui:3260-3281) on the icon alone, not the
    # shimmer template, which plays a sound every cycle (shared/animations.gui:548-556). It loops from creation, so
    # it needs no test of its own
    pulse = """state = {
	name = 1
	next = 2
	alpha = 0.4
	duration = 1.4
	using = Animation_Curve_Default
	trigger_on_create = yes
}
state = {
	name = 2
	next = 1
	alpha = 1
	duration = 1.4
	using = Animation_Curve_Default
}
"""
    tiers = lambda turning: "".join(f"""widget = {{
	size = {{ 100% 100% }}
	visible = "[{eq(word, w)}]"
	icon = {{
		size = {{ 100% 100% }}
		texture = "{icons.path('interest_' + WORDS[w])}"
{ind(pulse, 2) if turning else ''}	}}
}}
""" for w in range(1, 7))
    # the tier's name and price trend over the bar, shared by the normal and turning states
    names = "".join(f"""widget = {{
	size = {{ 100% 100% }}
	visible = "[{eq(word, w)}]"
{ind(name(f'SPEC_IL_TIER_{w}', True), 1)}}}
""" for w in range(1, 7))
    overlays = "".join(f"""widget = {{
	size = {{ 100% 100% }}
	visible = "[{eq(word, w)}]"
{ind(overlay(rd, w), 1)}}}
""" for w in range(1, 7))
    # crash month: a one shot pop as the icon appears, vanilla's _show state (add_wargoal_panel.gui:150-167,
    # culture_panel.gui:1641-1646), no sound, then a short shake (budget_panel.gui:559-588's position states)
    pop = """state = {
	name = _show
	next = settle
	alpha = 0
	duration = 0
}
state = {
	name = settle
	next = shake_1
	alpha = 1
	duration = 0.25
	using = Animation_Curve_EaseOut
}
""" + "".join(f"""state = {{
	name = shake_{i}
{f'	next = shake_{i + 1}{chr(10)}' if i < 4 else ''}	position = {{ {dx} 0 }}
	duration = 0.06
}}
""" for i, dx in enumerate((-3, 3, -2, 0), 1))
    return f"""widget = {{
	size = {{ {MARK} {MARK} }}
	position = {{ {ICON_X} {ICON_Y} }}
	### the bar's overlay for the good's tier, once for every state; in a glut the fills drop to half alpha, so a
	### recovering good reads as muted
	widget = {{
		size = {{ 100% 100% }}
		alpha = "[Select_float({st(3)}, '(float)0.5', '(float)1.0')]"
{ind(overlays, 2)}	}}
	### turning: the Fleeing step pulses red, where the boom would end
	widget = {{
		position = {{ {BAR_X - ICON_X + seg_x(1)} {BAR_Y - ICON_Y} }}
		size = {{ {SEG} {BAR_H} }}
		visible = "[And({st(1)}, {gt(word, 1)})]"
{ind(danger_zone(), 2)}	}}
	widget = {{
		size = {{ 100% 100% }}
		visible = "[{st(0)}]"
		tooltip = "SPEC_IB_HEAT_TT"
{ind(tiers(False), 2)}	}}
	widget = {{
		size = {{ 100% 100% }}
		visible = "[{st(1)}]"
		tooltip = "SPEC_IB_TURNING_TT"
{ind(tiers(True), 2)}	}}
	widget = {{
		size = {{ 100% 100% }}
		visible = "[Or({st(0)}, {st(1)})]"
		alwaystransparent = yes
{ind(names, 2)}	}}
	widget = {{
		size = {{ 100% 100% }}
		visible = "[{gt(rd('spec_ui_state'), 1)}]"
		icon = {{
			size = {{ {CRASH_SIZE} {CRASH_SIZE} }}
			parentanchor = center
			visible = "[{st(2)}]"
			texture = "{CRASH_ICON}"
			tooltip = "SPEC_IL_CRASHED_TT"
{ind(pop, 3)}		}}
		icon = {{
			size = {{ {CRASH_SIZE} {CRASH_SIZE} }}
			parentanchor = center
			visible = "[{st(3)}]"
			texture = "{CRASH_ICON}"
			tooltip = "SPEC_IL_GLUT_TT"
		}}
		### the name stays put while the crash icon pops and shakes
		widget = {{
			size = {{ 100% 100% }}
			visible = "[{st(2)}]"
{ind(name('SPEC_IL_WORD_CRASHED'), 3)}		}}
		widget = {{
			size = {{ 100% 100% }}
			visible = "[{st(3)}]"
			tooltip = "SPEC_IL_GLUT_TT"
{ind(name('SPEC_IL_WORD_GLUT'), 3)}		}}
	}}
}}
"""


TYPED = True  # the list's overlays come from overlay_types(); sized() draws its own at another size


def overlay(rd, w):
    """The tier overlay as an instance of its type (overlay_types): a list row reads the good in context, so it takes
    the type as it is; a fixed row overrides the three figures it reads by name."""
    if not TYPED:
        return tier_overlay(rd, w)
    if rd is good_var:
        return f"spec_il_ov{w} = {{}}\n"
    return f"""spec_il_ov{w} = {{
	blockoverride "pos" {{
		value = "[FixedPointToFloat({rd('spec_ui_pos')})]"
	}}
	blockoverride "up" {{
		visible = "[{eq(rd('spec_ui_move'), 1)}]"
	}}
	blockoverride "down" {{
		visible = "[{eq(rd('spec_ui_move'), -1)}]"
	}}
}}
"""


def overlay_types():
    """One type per tier for the bar's overlay, so the 48 fixed rows and the list rows share one copy each: the
    figures it reads sit in blocks a fixed row overrides (overlay)."""
    out = ""
    for w in range(1, 7):
        body = tier_overlay(good_var, w)
        pos = f'value = "[FixedPointToFloat({good_var("spec_ui_pos")})]"'
        up = f'visible = "[{eq(good_var("spec_ui_move"), 1)}]"'
        down = f'visible = "[{eq(good_var("spec_ui_move"), -1)}]"'
        for line, name in ((pos, "pos"), (up, "up"), (down, "down")):
            assert body.count(line) == 1, (w, name)
            body = body.replace(line, f'block "{name}" {{\n\t{line}\n}}')
        assert body.startswith("widget = {")
        out += f"type spec_il_ov{w} = widget " + body[len("widget = "):]
    # the sorted view's row (board's word lists), once here rather than once in each list
    r = row()
    assert r.startswith("button = {")
    return out + "type spec_il_row = button " + r[len("button = "):]


def seg_x(w):
    return (w - 1) * (SEG + GAP)


GREY = "0.55 0.55 0.55"  # the Calm tier, which HEAT leaves uncoloured


def fill(colour):
    """vanilla's progressbar fill (shared/progressbars.gui:35-105, white_progressbar_horizontal): the white rounded
    texture tinted, with progressbar_texture_properties' cloth, velvet and gradient."""
    return f"""spriteType = Corneredtiled
spriteborder = {{ 4 4 }}
texture_density = 2
color = {{ {colour} 1 }}
using = progressbar_texture_properties
"""


def tier_overlay(rd, w, danger=False):
    """What the bar shows for a good in tier w, laid over the bar from the tier icon, as vanilla's levels bar fills
    its segments (shared/progressbars.gui:107-226): the tiers below full, the current one lit to spec_ui_pos
    (word - 1 + bar) by its own progressbar with vanilla's glow, the tiers above left empty, vanilla's active level
    frame round the current one. While interest moves (spec_ui_move) the changed value chevrons run through the lit
    part (progressbars.gui:457-583): rightward when it rose, leftward when it fell. danger: a boom large enough to
    Collapse is turning, and the Fleeing step pulses red, where it would end."""
    colour = HEAT[w] or GREY
    below = "".join(f"""icon = {{
	position = {{ {seg_x(u)} 0 }}
	size = {{ {SEG} 100% }}
	texture = "{BARS}/progressbar_white.dds"
{ind(fill(HEAT[u] or GREY), 1)}}}
""" for u in range(1, w))
    lit = glow(colour) + chevrons(eq(rd("spec_ui_move"), 1), eq(rd("spec_ui_move"), -1))
    return _tier_overlay(rd, w, danger, colour, below, lit)


def chevrons(up, down, alpha=0.45, anchor="right", duration=1):
    """vanilla's changed value chevrons (progressbars.gui:457-583) through a lit bar: rightward while up,
    leftward while down. anchor: the side of the marker the lit part is on."""
    return "".join(f"""icon = {{
	size = {{ 100% 100% }}
	widgetanchor = {anchor}
	visible = "[{vis}]"
	texture = "{FLAT}"
	color = {{ 1 1 1 {alpha} }}
	shaderfile = "gfx/FX/pdxgui_repeat_texture.shader"
	modify_texture = {{
		name = arrow_animation
		texture = "{BARS}/progressbar_arrow.dds"
		spriteType = Corneredtiled
		spriteborder = {{ 0 0 }}
		texture_density = 10
		translate_uv = {{ 0 0 }}
		blend_mode = alphamultiply
{mirror}	}}
	state = {{
		trigger_on_create = yes
		name = arrow_animation_1
		next = arrow_animation_2
		duration = {duration}
		modify_texture = {{
			name = arrow_animation
			translate_uv = {{ -1 0 }}
		}}
	}}
	state = {{
		name = arrow_animation_2
		next = arrow_animation_1
		duration = 0
		modify_texture = {{
			name = arrow_animation
			translate_uv = {{ 0 0 }}
		}}
	}}
}}
""" for vis, mirror in ((up, ""), (down, "\t\tmirror = horizontal\n")))


def glow(colour):
    """vanilla's marker indicator (progressbar_marker_indicator): the glow and line where a bar is lit to."""
    return f"""icon = {{
	size = {{ 30 100% }}
	widgetanchor = right
	alpha = 0.7
	texture = "{BARS}/progressbar_white_glow.dds"
	shaderfile = "gfx/FX/pdxgui_repeat_texture.shader"
	color = {{ {colour} 1 }}
	icon = {{
		size = {{ 3 100% }}
		parentanchor = right
		texture = "{BARS}/progressbar_white_glow_line.dds"
		spriteType = Corneredtiled
		spriteborder = {{ 0 0 }}
	}}
}}
"""


def danger_zone(x=0):
    """The collapse zone: the Fleeing step, red and pulsing, where a turning boom would end."""
    return f"""### the collapse zone
icon = {{
	position = {{ {x} 0 }}
	size = {{ {SEG} 100% }}
	texture = "{BARS}/progressbar_bad.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	tooltip = "SPEC_IL_DANGER_TT"
	state = {{
		name = 1
		next = 2
		alpha = 0.1
		duration = 1.4
		using = Animation_Curve_Default
		trigger_on_create = yes
	}}
	state = {{
		name = 2
		next = 1
		alpha = 0.35
		duration = 1.4
		using = Animation_Curve_Default
	}}
}}
"""


def _tier_overlay(rd, w, danger, colour, below, lit):
    zone = danger_zone(seg_x(1)) if danger and w > 1 else ""
    return f"""widget = {{
	position = {{ {BAR_X - ICON_X} {BAR_Y - ICON_Y} }}
	size = {{ {BAR_W} {BAR_H} }}
{ind(below, 1)}	widget = {{
		position = {{ {seg_x(w)} 0 }}
		size = {{ {SEG} 100% }}
		scissor = yes
		progressbar = {{
			size = {{ 100% 100% }}
			progresstexture = "{BARS}/progressbar_white.dds"
			noprogresstexture = "{CLEAR}"
{ind(fill(colour) + SLIDE, 3)}			min = {w - 1}
			max = {w}
			value = "[FixedPointToFloat({rd('spec_ui_pos')})]"
			marker = {{
				widget = {{
					size = {{ 100% 100% }}
{ind(lit, 5)}				}}
			}}
		}}
	}}
	icon = {{
		position = {{ {seg_x(w)} 0 }}
		size = {{ {SEG} 100% }}
		texture = "{BARS}/progressbar_active_level.dds"
		spriteType = Corneredstretched
		spriteborder = {{ 6 6 }}
		texture_density = 2
	}}
{ind(zone, 1)}}}
"""


def scale(rd):
    """vanilla's levels bar (shared/progressbars.gui:107-226) as the Interests list shows it: the empty background,
    the frame and a divider between the six tiers. What fills it is the tier's own (tier_overlay)."""
    dividers = "".join(f"""icon = {{
	position = {{ {seg_x(w) + SEG} 1 }}
	size = {{ {GAP} {BAR_H - 2} }}
	texture = "{BARS}/progressbar_center_divider.dds"
	texture_density = 2
}}
""" for w in range(1, 6))
    return f"""widget = {{
	size = {{ {BAR_W} {BAR_H} }}
	position = {{ {BAR_X} {BAR_Y} }}
	tooltip = "SPEC_IB_HEAT_TT"
	background = {{
		texture = "{BARS}/progressbar_empty.dds"
		spriteType = Corneredtiled
		spriteborder = {{ 4 4 }}
		texture_density = 2
		alpha = 0.8
		using = progressbar_texture_properties
	}}
	background = {{
		texture = "{BARS}/progressbar_frame.dds"
		spriteType = Corneredstretched
		spriteborder = {{ 6 6 }}
		texture_density = 2
		margin = {{ 3 3 }}
	}}
{ind(dividers, 1)}}}
"""


def levels():
    """One hover area per tier segment, over everything else on the bar, each with that level's tooltip, as vanilla's
    involvement bar gives each tier segment its own (strategic_region_panel.gui:786, item_properties)."""
    return "".join(f"""widget = {{
	position = {{ {BAR_X + seg_x(w)} {BAR_Y - 3} }}
	size = {{ {SEG} {BAR_H + 6} }}
	tooltip = "SPEC_IL_LEVEL_{w}_TT"
	using = tooltip_ws
}}
""" for w in range(1, 7))


def trend(rd):
    """The price trend against its long run average (interest_board's SPEC_IB_HEAT_TT line), on the tier name's line
    flush with the bar's right end, to a tenth of a percent; hidden where that rounds to 0.0%. The box spanning the bar
    lets the mouse through, so only the figure takes its tooltip."""
    t = f"Subtract_CFixedPoint({rd('spec_fast')}, {rd('spec_slow')})"
    return f"""widget = {{
	position = {{ {BAR_X - ICON_X} {NAME_DY} }}
	size = {{ {BAR_W} {NAME_H} }}
	alwaystransparent = yes
	textbox = {{
		parentanchor = right
		size = {{ -1 {NAME_H} }}
		autoresize = yes
		align = right|nobaseline
		visible = "[Or(GreaterThanOrEqualTo_CFixedPoint({t}, {fx(0.0005)}), LessThanOrEqualTo_CFixedPoint({t}, {fx(-0.0005)}))]"
		raw_text = "[{rounded(t, 3)}|=+%1]"
		tooltip = "SPEC_IB_HEAT_TT"
	}}
}}
"""


def crash_flash(rd):
    """The crash month: one short flash of vanilla's red bar fill over the bar as it appears, fading out."""
    return f"""icon = {{
	position = {{ {BAR_X} {BAR_Y} }}
	size = {{ {BAR_W} {BAR_H} }}
	visible = "[{eq(rd('spec_ui_state'), 2)}]"
	texture = "{BARS}/progressbar_bad.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alwaystransparent = yes
	state = {{
		name = _show
		next = fade
		alpha = 0.5
		duration = 0
	}}
	state = {{
		name = fade
		alpha = 0
		duration = 1
		using = Animation_Curve_EaseOut
	}}
}}
"""


def sized(rd, seg, bar_h, name_h, crash, font=""):
    """The scale, marker, crash flash and hover areas at another size (the goods panel's), and the box they fill.
    ponytail: the pieces read this module's geometry, so a sized copy is swapped in for the call; pass the geometry
    through the functions if a third size appears."""
    g = globals()
    mark = name_h + NAME_GAP + bar_h
    geo = dict(TYPED=False, SEG=seg, BAR_H=bar_h, NAME_H=name_h, MARK=mark, BAR_W=6 * seg + 5 * GAP, ICON_Y=2,
               BAR_X=ICON_X + mark + 10, BAR_Y=2 + name_h + NAME_GAP, CRASH_SIZE=crash, NAME_X=mark + 10, NAME_DY=0,
               NAME_FONT=f"\t\tusing = {font}\n" if font else "")
    saved = {k: g[k] for k in geo}
    g.update(geo)
    try:
        return scale(rd) + marker(rd) + crash_flash(rd) + levels(), (geo["BAR_X"] + geo["BAR_W"] + ICON_X, mark + 4)
    finally:
        g.update(saved)


def column(name, body):
    return f"""widget = {{
	size = {{ {COL[name]} {ROW_H} }}
{ind(body, 1)}}}
"""


def row(g=None):
    """One good's row: fixed for good g, else a list row (datacontext Scope.GetGoods, hidden by the filters)."""
    rd = var(g)
    # Keep the native good icon at its original center on the neutral row.
    goods = f"""icon = {{
	position = {{ 7 0 }}
	size = {{ 30 30 }}
	parentanchor = vcenter
	texture = "[Goods.GetTexture]"
}}
textbox = {{
	position = {{ 48 0 }}
	size = {{ {COL['goods'] - 54} {ROW_H} }}
	parentanchor = vcenter
	align = left|nobaseline
	fontsize_min = 12
	elide = right
	text = "[Goods.GetNameNoFormatting]"
}}
"""
    # an interest group's button closes Finance before its panel opens, as the row does for the goods panel
    fav, dis = ig_stances.slot(rd, g, f"\t\tonclick = \"[GetVariableSystem.Clear('{FIN}')]\"\n")
    lever = interest_board.small_strip().replace("parentanchor = hcenter", "parentanchor = center", 1)
    if g:  # the lever flags (and the Great Issue's) by name too
        named = lambda x: re.sub(r"Concatenate\('(\w+_)', Goods\.GetKey\)", rf"'\g<1>{g}'", x)
        lever = named(lever)
    # on every row with a loss to show, whatever the sort. The tooltip is a plain key, built on hover: as a
    # [SelectLocalization(...)] binding its calculator (several script values a good) was rebuilt every frame for every row
    risk_number = f"""textbox = {{
	visible = "[{gt(rd('spec_risk'), 0.05)}]"
	size = {{ {COL['risk']} {NAME_H} }}
	parentanchor = center
	align = hcenter|nobaseline
	fontsize_min = 12
	text = "SPEC_IL_RISK_VALUE"
	tooltip = "SPEC_IL_RISK_DETAILS"
}}
"""
    cols = [column("goods", goods), column("scale", scale(rd) + marker(rd) + crash_flash(rd) + levels()), column("risk", risk_number),
            column("fav", fav), column("dis", dis), column("lever", lever)]
    context, shown = (f"GetGoods('{g}')" if g else "Scope.GetGoods"), matches_filters(rd)
    return f"""button = {{
	datacontext = "[{context}]"
	visible = "[{shown}]"
	size = {{ {W} {ROW_H} }}
	background = {{ using = dark_area }}
	using = select_button_sound
	onclick = "[GetVariableSystem.Clear('{FIN}')]"
	onclick = "[InformationPanelBar.OpenGoodsPanel(GetPlayer.GetMarket.Self, Goods.Self)]"
	onrightclick = "[RightClickMenuManager.ShowForGoods(Goods.AccessSelf)]"
	tooltip = "SPEC_TILE_TT"
	using = tooltip_se
	flowcontainer = {{
		parentanchor = vcenter
{ind("vertical_divider = {}\n".join(cols), 2)}	}}
}}
"""


TIER = "spec_il_tier"  # GetVariableSystem value: the one interest word the list shows, "1" to "6"; unset, all
HAS = lambda w: f"GetVariableSystem.HasValue('{TIER}', '{w}')"


def tier_shown(rd):
    """GUI test: no tier filter picked, or the good's word is the one picked."""
    # Read the country variable once, rather than once for each possible tier.
    # An unknown selection matches no traded good, as the old six-way test did.
    picked = fx(0)
    for w in range(6, 0, -1):
        picked = f"Select_CFixedPoint({HAS(w)}, {fx(w)}, {picked})"
    return f"Or(Not(GetVariableSystem.Exists('{TIER}')), EqualTo_CFixedPoint({rd('spec_word')}, {picked}))"


def tier_filters():
    """The second filter row, under the goods categories: one round button per interest word, vanilla's goods filter
    button and selection ring (market_panel.gui goods_filters, ~964-1012). One at a time, as the categories are:
    picking a word replaces the last, picking it again clears it. Each word is two overlapping buttons, one shown
    while it is not picked (sets it) and one while it is (clears it). Fleeing to Feverish, as the bar reads."""
    # vanilla dims the unpicked categories by their own darker textures; these icons have none, so the unpicked fade
    FADE = f"\t\talpha = \"[TransparentIfFalse(Not(GetVariableSystem.Exists('{TIER}')))]\"\n"
    buttons = "".join(f"""widget = {{
	size = {{ 64 64 }}
	icon = {{
		texture = "gfx/interface/backgrounds/round_frame_dec.dds"
		size = {{ 64 64 }}
		visible = "[Or(Not(GetVariableSystem.Exists('{TIER}')), {HAS(w)})]"
		using = default_fade_in_out
	}}
{"".join(f'''	goods_filter_button = {{
		size = {{ 52 52 }}
		visible = "[{shown}]"
{fade}		tooltip = "SPEC_SEP_{WORDS[w].upper()}_TT"
		onclick = "[{click}]"
		blockoverride "icon" {{
			texture = "{icons.path('interest_' + WORDS[w])}"
		}}
		blockoverride "icon_size" {{
			size = {{ 40 40 }}
		}}
	}}
''' for shown, click, fade in ((f"Not({HAS(w)})", f"GetVariableSystem.Set('{TIER}', '{w}')", FADE),
                              (HAS(w), f"GetVariableSystem.Clear('{TIER}')", "")))}}}
""" for w in sorted(LEANING))
    return f"""flowcontainer = {{
	parentanchor = center
	spacing = 3
{ind(buttons, 1)}}}
"""


def order(category):
    """The fixed order: vanilla's category order, then the good's key."""
    return sorted(category, key=lambda g: (CATEGORIES.index(category[g]), g))


def risk_order_value(goods):
    """Read the cached loss shown on the goods row from its country's scope."""
    ranks = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{ limit = {{ this = g:{g} }} value = scope:spec_sort_owner.var:spec_risk_{g} }}\n"
                    for i, g in enumerate(goods))
    return "spec_goods_risk_order = {\n\tvalue = 0\n" + ranks + "}\n"


def risk_list_effect(category):
    goods = order(category)
    name = "spec_goods_by_risk"
    append = lambda group, target: f"add_to_variable_list = {{ name = {name}{group} target = {target} }}"
    lines = ["spec_refresh_risk_list = {", "\tspec_refresh_ranked_interest = yes", "\tsave_temporary_scope_as = spec_sort_owner", "\tclear_variable_list = spec_risky_goods",
             f"\tclear_variable_list = {name}"]
    lines += [f"\tclear_variable_list = {name}_{c}" for c in CATEGORIES]
    for g in goods:
        lines.append(f"\tif = {{ limit = {{ has_variable = spec_word_{g} var:spec_word_{g} > 0 has_variable = spec_risk_{g} var:spec_risk_{g} > 0 }} add_to_variable_list = {{ name = spec_risky_goods target = g:{g} }} }}")
    lines += ["\tordered_in_list = {", "\t\tvariable = spec_risky_goods", "\t\torder_by = spec_goods_risk_order",
              "\t\tscope:spec_sort_owner = { " + append("", "prev") + " }"]
    for c in CATEGORIES:
        match = " ".join(f"this = g:{g}" for g in goods if category[g] == c)
        if match:
            lines.append(f"\t\tif = {{ limit = {{ OR = {{ {match} }} }} scope:spec_sort_owner = {{ {append('_' + c, 'prev')} }} }}")
    lines.append("\t}")
    # Most goods have zero risk. Keep these in normal goods order without sorting them.
    for g in goods:
        lines.append(f"\tif = {{ limit = {{ has_variable = spec_word_{g} var:spec_word_{g} > 0 NOT = {{ is_target_in_variable_list = {{ name = {name} target = g:{g} }} }} }} "
                     f"{append('', 'g:' + g)} {append('_' + category[g], 'g:' + g)} }}")
    return "\n".join(lines) + "\n\tclear_variable_list = spec_risky_goods\n}\n"


def header():
    """vanilla's sort buttons over the columns: Goods (fixed order) and Investor Interest (by interest) sort, each
    setting its order, as vanilla's do. Each row's tier icon names its tier in its tooltip, so the header needs no
    legend. HEAD_H: vanilla's sort_button is 30 tall whatever size it is given (shared/buttons.gui)."""
    HEAD_H = 30
    picked = lambda on: f"""	blockoverride "selected_visibility" {{
		visible = "[{on}]"
	}}
"""
    # Investor Interest and Risk switch their order on, and off again (back to the goods order, no header lit): two
    # overlapping buttons each, one shown while off (sets it) and one while on (clears it), as tier_filters' are;
    # vanilla's variable system has no conditional clear
    toggle = lambda col, face, tooltip, value, on: "".join(f"""	sort_button = {{
		size = {{ {COL[col]} {HEAD_H} }}
		visible = "[{shown}]"
{ind(face, 2)}		tooltip = "{tooltip}"
		onclick = "[{click}]"
{lit}	}}
""" for shown, click, lit in ((f"Not({on})", f"GetVariableSystem.Set('{SORT}', '{value}')", ""),
                              (on, f"GetVariableSystem.Clear('{SORT}')", picked(on))))
    # the crash month's cracked coin, as the group headers' icons: text elides in so narrow a button
    coin = f'icon = {{\n\tsize = {{ 24 24 }}\n\tparentanchor = center\n\ttexture = "{CRASH_ICON}"\n}}\n'
    return f"""flowcontainer = {{
	parentanchor = hcenter
	ignoreinvisible = yes
	sort_button = {{
		size = {{ {COL['goods']} {HEAD_H} }}
		text = "SPEC_IL_COL_GOODS"
		tooltip = "SPEC_IL_SORT_GOODS_TT"
		onclick = "[GetVariableSystem.Clear('{SORT}')]"
	}}
{toggle('scale', 'text = "SPEC_IL_COL_INTEREST"' + chr(10), "SPEC_IL_SORT_INTEREST_TT", "yes", f"And({SORTED}, Not({RISK_SORT}))")}{toggle('risk', coin, "SPEC_IL_SORT_RISK_TT", "risk", RISK_SORT)}
{"".join(f'''	sort_button = {{
		size = {{ {COL[c]} {HEAD_H} }}
		tooltip = "SPEC_IL_COL_{c.upper()}_TT"
		onclick = "[GetScriptedGui('spec_sgui_igs_mark').Execute(GuiScope.SetRoot({P}).End)]"
		onclick = "[GetVariableSystem.Toggle('{flag}')]"
		icon = {{  # vanilla's marker, as an icon: as text it elides in so narrow a button
			size = {{ 22 22 }}
			parentanchor = center
			texture = "gfx/interface/icons/generic_icons/{tex}.dds"
		}}
	{picked(f"GetVariableSystem.Exists('{flag}')")}	}}
''' for c, tex, flag in (("fav", "approval_icon", FAV_F), ("dis", "disapproval_icon", DIS_F)))}
	sort_button = {{
		size = {{ {COL['lever']} {HEAD_H} }}
		text = "SPEC_COL_LEVER"
		tooltip = "SPEC_IL_SORT_LEVER_TT"
		onclick = "[GetVariableSystem.Toggle('{ACTIVE}')]"
	blockoverride "selected_visibility" {{
		visible = "[GetVariableSystem.Exists('{ACTIVE}')]"
	}}
	}}
}}
"""


def board(k):
    # a group with no row shown is hidden too: an empty flowcontainer still takes its place and spacing, so picking a
    # category (which hides the other groups) moved everything below. Read from the monthly counts (spec_n_w<word>_<c>)
    filled = lambda c: any_of([f"And(Or(Not(GetVariableSystem.Exists('{TIER}')), {HAS(w)}), {gt(v(f'spec_n_w{w}_{c}'))})"
                               for w in LEANING])
    goods = order(k["CATEGORY"])
    in_cat = {c: [g for g in goods if k["CATEGORY"][g] == c] for c in CATEGORIES}
    # Counts handle ordinary tier filters; with interventions selected, test the
    # same rows so an active good hidden by another filter leaves no empty group.
    matches = lambda gs: any_of([matches_filters(var(g)) for g in gs]) if gs else 'no'
    present = lambda c: f"And({cat_shown(c)}, And({filled(c)}, {matches(in_cat[c])}))"
    # each row brings its own 2px gap (a 0-high lead, then the group's spacing; the parent has none), so a group whose
    # rows a filter hides takes no room and needs no test of every good's filters each frame (Jomini's And/Or do not
    # short-circuit: the test cost every good's filters every frame, filter or not)
    lead = "widget = {\n\tsize = { 1 0 }\n}\n"
    ordinary = any_of([f"And({cat_shown(c)}, {filled(c)})" for c in CATEGORIES])
    active_rows = any_of([present(c) for c in CATEGORIES])
    empty = "".join(f"""flowcontainer = {{
	direction = vertical
	visible = "[{mode}]"
	textbox = {{
		visible = "[Not({rows})]"
		size = {{ {W} {ROW_H} }}
		align = center|nobaseline
		using = empty_state_text_properties
		text = "SPEC_IL_EMPTY_FILTERS"
	}}
}}
""" for mode, rows in ((f"Not({ANY_FILTER})", ordinary), (ANY_FILTER, active_rows)))
    # the word lists' rows, one type (overlay_types) rather than a copy in each of the lists
    lists_of = lambda suffix, item: "".join(f"""flowcontainer = {{
	datamodel = "[{P}.GetList('spec_goods_w{w}{suffix}')]"
	direction = vertical
	spacing = 2
	ignoreinvisible = yes
	item = {{
{ind(item, 2)}	}}
}}
""" for w in LEANING)
    # beside the lists, one empty row-high slot for each row shown, never hidden by a sort: a view a sort shows reads
    # its rows' filters a frame late, and the tab's scroll area, that frame short of rows, sprang back to the top.
    # Fixed slots read by name: as items of the word lists (one datamodel each, names concatenated) the tab lagged
    # Two copies, so with no tier or other filter picked a slot tests only its category and whether the good trades
    slot = lambda g, test: (f'widget = {{\n\tsize = {{ 1 {ROW_H} }}\n'
                            f'\tvisible = "[And({cat_shown(k["CATEGORY"][g])}, {test(var(g))})]"\n}}\n')
    narrowed = f"Or({ANY_FILTER}, GetVariableSystem.Exists('{TIER}'))"
    hold = "".join(f"""flowcontainer = {{
	direction = vertical
	spacing = 2
	ignoreinvisible = yes
	visible = "[{shown}]"
{ind(lead + "".join(slot(g, test) for g in goods), 1)}}}
""" for shown, test in ((f"Not({narrowed})", lambda rd: gt(rd('spec_word'))), (narrowed, matches_filters)))
    sections = []
    for sector, members in in_cat.items():
        if not members:
            continue
        # Tier counts suffice until the player enables an intervention or political filter.
        visible = f"And({cat_shown(sector)}, And({filled(sector)}, Or(Not({ANY_FILTER}), {matches(members)})))"
        fixed = "".join(row(g) for g in members)
        sorted_rows = lists_of("_" + sector, "spec_il_row = {}\n")
        sections.append(f"""flowcontainer = {{
            direction = vertical
            ignoreinvisible = yes
            spacing = 2
            visible = "[{visible}]"
            widget = {{
                size = {{ {W} 38 }}
                tooltip = "SPEC_SECTOR_{sector.upper()}_TT"
                background = {{
                    texture = "gfx/interface/buttons/expand_button_bg.dds"
                    spriteType = Corneredtiled
                    spriteborder = {{ 20 20 }}
                    texture_density = 2
                }}
                icon = {{ parentanchor = left|vcenter position = {{ 9 0 }} size = {{ 30 30 }} texture = "{icons.path('sector_' + sector)}" alwaystransparent = yes }}
                textbox = {{ parentanchor = left|vcenter position = {{ 48 0 }} size = {{ {W - 150} 36 }} using = fontsize_large default_format = "#title" align = left|nobaseline elide = right fontsize_min = 12 text = "SPEC_SECTOR_{sector.upper()}" alwaystransparent = yes }}
                textbox = {{ parentanchor = right|vcenter margin_right = 12 size = {{ 82 36 }} align = right|nobaseline text = "[{v('spec_sector_share_' + sector)}|%1]" alwaystransparent = yes }}
            }}
            flowcontainer = {{ direction = vertical spacing = 2 ignoreinvisible = yes visible = "[Not({SORTED})]"
                {fixed}
            }}
            flowcontainer = {{ direction = vertical spacing = 2 ignoreinvisible = yes visible = "[And({SORTED}, Not({RISK_SORT}))]"
                {sorted_rows}
            }}
            flowcontainer = {{ direction = vertical spacing = 2 ignoreinvisible = yes visible = "[{RISK_SORT}]"
                datamodel = "[{P}.GetList('spec_goods_by_risk_{sector}')]"
                item = {{ spec_il_row = {{}} }}
            }}
        }}""")
    views = "\n".join(sections)
    lists = f"""flowcontainer = {{
	ignoreinvisible = yes
{ind(hold, 1)}	flowcontainer = {{
		direction = vertical
		ignoreinvisible = yes
{ind(views, 2)}	}}
}}
{empty}"""
    import journal
    rows = "".join(journal.goods_row(label, keys) for label, keys in journal.RANKED_GOODS)
    summary = f"""flowcontainer = {{
        direction = vertical
        parentanchor = hcenter
        visible = "[{P}.Var('spec_conf').IsSet]"
        {rows}
    }}
"""
    return goods_filters("SPEC_IL_FILTER_TIERS", tier_filters()) + summary + f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	margin_top = 12
	ignoreinvisible = yes
	spacing = 3
{ind(header() + lists, 1)}}}
"""


def loc(k):
    ge = lambda a, n: f"GreaterThanOrEqualTo_CFixedPoint({a}, {fx(n)})"
    # Correction, Bust or Collapse (generate.unwind_loc's SPEC_UNWIND_<sev>) and its glut months, by a severity variable
    pick = lambda a, key: f"[SelectLocalization({ge(a, 3)}, '{key}_3', SelectLocalization({ge(a, 2)}, '{key}_2', '{key}_1'))]"
    crash, glut = good_var("spec_ui_crash"), good_var("spec_glut")
    until = good_var("spec_glut_until")
    months = "".join(f' SPEC_IL_MONTHS_{s}: "#v {m}#! months"\n' for s, m in sorted(k["GLUT_MONTHS"].items()))
    loses = "\\n[Concept('concept_company','$concept_companies$')] making it #N lose#! [concept_throughput]"
    # the tier names over the bar, plain: the tier icon is beside them
    tiers = "".join(f' SPEC_IL_TIER_{w}: "{WORDS[w].capitalize()}"\n' for w in range(1, 7))
    # each tier segment's tooltip, laid out as vanilla's interest tier tooltip (INTEREST_TIER_ACTIVE_TOOLTIP): the
    # level, whether the good is at it, where it applies, the good's figure now, then its effects
    cut = lambda w: f"#v [{sv(f'spec_level_from_{w}')}|=+%1]#!"
    where = {1: f"below {cut(2)}", 6: f"above {cut(6)}"} | {w: f"between {cut(w)} and {cut(w + 1)}" for w in range(2, 6)}
    effects = level_effects()
    allows = {w: ("\\nWe can Restrain Speculation here" if w >= 5 else "\\nWe can Encourage Investment here, unless the good is recovering" if w <= 3 else "")
              for w in range(1, 7)}
    levels = "".join(
        f' SPEC_IL_LEVEL_{w}_TT: "#header @spec_interest_{WORDS[w]}! {WORDS[w].capitalize()}#!'
        f"[AddLocalizationIf(EqualTo_CFixedPoint({WORD}, {fx(w)}), 'SPEC_IL_LEVEL_CURRENT')]"
        f"\\n$TOOLTIP_DELIMITER$\\nA good is at this level while its price trend is {where[w]}.\\n\\n$SPEC_II_TREND$"
        f'\\n$TOOLTIP_DELIMITER$\\n#title Effects:#!\\n{effects[WORDS[w]]}{allows[w]}"\n'
        for w in range(1, 7))
    levels += ' SPEC_IL_LEVEL_CURRENT: "\\n#P [Goods.GetName] is at this level#!"\n'
    return months + tiers + levels + (
        ' SPEC_IL_COL_GOODS: "Goods"\n'
        f' SPEC_IL_RISK_VALUE: "[Multiply_CFixedPoint({rounded_tenth(RISK)}, {fx(-1)})|=+1]"\n'
        ' SPEC_IL_RISK_DETAILS: "#title [Goods.GetName]#!\\n$SPEC_RISK_TT$"\n'
        ' SPEC_IL_SORT_RISK_TT: "#header Sort by Collapse Risk#!\\n$TOOLTIP_DELIMITER$\\nRanks goods by the [concept_spec_market_confidence] their boom would cost if it ended this month.\\n\\n#instruction Hover over a number to see its calculation.#!$SPEC_IL_SORT_OFF$"\n'
        ' SPEC_IL_EMPTY_FILTERS: "No goods match the current filters"\n'
        ' SPEC_IL_WORD_CRASHED: "#N Boom Ended#!"\n'
        ' SPEC_IL_WORD_GLUT: "#n Recovering#!"\n'
        ' SPEC_IL_COL_INTEREST: "[concept_spec_investor_interest]"\n'
        ' SPEC_IL_FILTER_TIERS: "[concept_spec_investor_interest]"\n'
        " SPEC_IL_SORT_GOODS_TT: \"#header Sort by Goods#!\\n$TOOLTIP_DELIMITER$\\nThe [Concept('concept_good','$concept_goods$')] traded in our "
        '[concept_market] in a fixed order, by category and then by name."\n'
        ' SPEC_IL_SORT_INTEREST_TT: "#header Sort by [concept_spec_investor_interest]#!\\n$TOOLTIP_DELIMITER$\\nHottest goods '
        'first, then the most traded\\n\\nThe marker shows the level, from @spec_interest_fleeing! '
        '#v Fleeing#! to @spec_interest_feverish! #v Feverish#!\\nThe arrow shows this month\'s change$SPEC_IL_SORT_OFF$"\n'
        ' SPEC_IL_SORT_OFF: "\\n\\n#instruction Click again to return to the goods order#!"\n'
        f' SPEC_IL_SORT_LEVER_TT: "$SPEC_IL_SORT_LEVER_BASE_TT${"$SPEC_IL_ISSUE_FILTER$" if levers.ISSUE_ON else ""}"\n'
        ' SPEC_IL_ISSUE_FILTER: "\\n\\nRunning Great Issues are also shown."\n'
        ' SPEC_IL_COL_FAV_TT: "$SPEC_IL_COL_IGS_TT$\\n\\n#instruction Click to show only goods a group favors, click again to show all#!"\n'
        ' SPEC_IL_COL_DIS_TT: "$SPEC_IL_COL_IGS_TT$\\n\\n#instruction Click to show only goods a group opposes, click again to show all#!"\n'
        ' SPEC_IL_SORT_LEVER_BASE_TT: "#header Show Interventions#!\\n$TOOLTIP_DELIMITER$\\nShows only goods with an '
        '[concept_spec_intervention]\\n\\n#instruction Click to show only these goods, click again to show all#!"\n'
        ' SPEC_IL_DANGER_TT: "#header Collapse Zone#!\\n$TOOLTIP_DELIMITER$\\n'
        'If [concept_spec_investor_interest] falls this far, the boom ends in a [concept_spec_collapse], '
        f'costing about #N [{RISK}|1]#! [concept_spec_market_confidence]"\n'
        f' SPEC_IL_CRASHED_TT: "#header [Goods.GetName]: Boom Ended#!\\n$TOOLTIP_DELIMITER$\\n'
        f'Its boom ended this month in a {pick(crash, "SPEC_UNWIND_C")}\\n'
        f'#N Investors stay away#! for {pick(crash, "SPEC_IL_MONTHS")}{loses}"\n'
        f' SPEC_IL_GLUT_TT: "#header [Goods.GetName] Recovering#!\\n$TOOLTIP_DELIMITER$\\n'
        f'Investors are still wary after its boom ended in a {pick(glut, "SPEC_UNWIND_C")}\\n'
        f'[concept_spec_investor_interest] #N stuck#! at #v Doubtful#! or lower{loses}'
        f"[AddLocalizationIf({gt(until)}, 'SPEC_IL_RECOVERY_LEFT')]\"\n"
        f' SPEC_IL_RECOVERY_LEFT: "\\nIt recovers on #v {expiry_date(until)}#!, in #v [Subtract_CFixedPoint({until}, {sv("spec_calendar_day")})|0]#! days"\n')


def bindings(t):
    """Rough per frame cost: data bound properties, not counting click handlers (run on click) or tooltips (hover)."""
    return [p for p in re.findall(r'^\s*(\w+) = "\[', t, re.M) if p not in ("onclick", "onrightclick", "tooltip")]


if __name__ == "__main__":
    cat = {"grain": "food", "wine": "plantation", "tools": "industry", "fish": "food", "small_arms": "defence"}
    assert order(cat) == ["fish", "grain", "wine", "tools", "small_arms"]
    r, d = row("grain"), row()
    for t in (r, d):
        assert t.count("{") == t.count("}")
    # a fixed row reads each figure by name: no Concatenate, no interest maths, no scripted GUI triggers, no filters
    assert "Concatenate" not in r and "Goods.GetKey" not in r and "IsValid(" not in r and "MarketPanel" not in r
    assert "GetGoods('grain')" in r and "'spec_word_grain'" in r and "'spec_ui_r_grain'" in r and "'spec_ui_e_grain'" in r
    assert "spec_hype_" not in r + d  # Divide_CFixedPoint is allowed: the risk figure's 1-decimal rounding
    # no sound on any row animation, no badge column
    # one pos read and two move tests per tier, in the one overlay set every state shares
    assert r.count("'spec_ui_pos_grain'") == 6 and r.count("'spec_ui_move_grain'") == 12
    # the row's visible and tier filter, the overlays, the normal and turning icons, the names, the danger zone
    assert r.count("'spec_word_grain'") == 1 + 1 + 6 + 12 + 6 + 1 + 2 * bool(levers.ISSUE_ON)  # and the issue button's gate and alpha
    assert r.count("'spec_ui_state_grain'") == 12  # the names layer (2) and the danger zone, and before: normal, turning, crash and glut, its glut dimming, month (icon, name), glut (icon, name), flash
    assert r.count("name = _show") == 2 and "trigger_when" not in r and f'texture = "{CRASH_ICON}"' in r
    n = bindings(r)
    # 117 written, but a frame updates about 28 (with the price trend): the row, the state widgets, one set's six tier tests, then inside
    # the one tier shown its value and two chevron tests, the flash and the lever (the old one marker bar: 28)
    # the Interest Groups column: grain's groups on each side's line, and each line's test
    assert len(n) <= 122, len(n)
    # a list row is a word list's good: hidden, not dimmed, by the filters
    assert "Scope.GetGoods" in d and "MarketPanel" not in d
    b = board({"CATEGORY": cat})
    assert b.count("{") == b.count("}") and len(set(re.findall(r"datacontext = \"\[GetGoods\('(\w+)'\)\]\"", b))) == len(cat)
    assert b.index("GetGoods('fish')") < b.index("GetGoods('grain')") < b.index("GetGoods('tools')") < b.index("GetGoods('small_arms')")
    assert b.count("GetList('spec_goods_w") == 6 * len(set(cat.values())) and "MarketPanel" not in b
    # the Interest header sets the sort, so a second click keeps it; Goods clears it
    assert f"GetVariableSystem.Set('{SORT}', 'yes')" in b and f"Toggle('{SORT}')" not in b and f"Clear('{SORT}')" in b
    assert header().count(" 30 }") >= 6 and " 20 }" not in header()  # 30 high headers (sort buttons come in overlapping pairs)
    # the word lists share one row type
    assert b.count("spec_il_row = {}") == 7 * len(set(cat.values())) and "Scope.GetGoods" not in b
    assert "type spec_il_row = button {" in overlay_types() and "datacontext = \"[Scope.GetGoods]\"" in overlay_types()
    # a row opens the goods panel for our own market and closes Finance
    assert f"Clear('{FIN}')" in r and "OpenGoodsPanel(GetPlayer.GetMarket.Self, Goods.Self)" in r and "Market.Self" not in r.replace("GetMarket.Self", "")
    assert r.index(f"Clear('{FIN}')") < r.index("OpenGoodsPanel")
    # Show Interventions hides groups with no lever, and an empty list says so
    assert b.count(f"Not(GetVariableSystem.Exists('{ACTIVE}')), Or(") >= 1 and "'spec_ui_r_fish'" in b.split("GetGoods('fish')")[0]
    assert b.count("SPEC_IL_EMPTY_FILTERS") == 2
    assert all(icons.path("interest_" + WORDS[w]) in b for w in LEANING) and "SPEC_IL_N" not in b and all("SPEC_SECTOR_" + c.upper() in b for c in cat.values())
    lo = loc({"GLUT_MONTHS": {3: 12, 2: 6, 1: 3}})
    # no dashes in the text; a minus before a number is a figure, a hyphen inside a word ("long-run") is spelling
    assert "SPEC_IL_N" not in lo and "SPEC_IL_COL_BADGE_TT" not in lo and not re.search(r"(?<!\w)-(?!\d)|-(?!\w)", lo.replace("_", ""))
    assert 'SPEC_IL_MONTHS_3: "#v 12#! months"' in lo and "'SPEC_UNWIND_C_3'" in lo and "spec_ui_crash_" in lo
    assert all(f"{key}:" in lo for key in ("SPEC_IL_DANGER_TT", "SPEC_IL_CRASHED_TT", "SPEC_IL_GLUT_TT"))
    print(f"interest_list ok, {len(n)} data bound properties per fixed row (all widgets; hidden ones are not updated)")
