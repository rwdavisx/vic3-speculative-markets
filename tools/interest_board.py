"""Investor Interest's per-good figures and shared pieces for the goods list in interest_list.py: ui_effect() and
monthly() store each good's figures, small_strip() goes into its rows, HEAT colours the
interest words, and loc() holds the tooltips its rows use.

The GUI re-evaluates every visible expression every frame, so the rows read figures ui_effect() stores monthly
(spec_ui_*_<good>, one variable read per test) instead of working them out from interest, peak and risk; tooltips,
which run on hover only, keep their own expressions."""
import levers
from market_tab import fx, good_var, RISK, WORD, TREND, LEANING, CATEGORIES, NEAR_PEAK, any_of

# the interest words' colours, warm to cold; Calm has none
HEAT = {6: "0.80 0.32 0.22", 5: "0.78 0.52 0.24", 4: "0.70 0.64 0.36", 3: None, 2: "0.34 0.48 0.64", 1: "0.28 0.34 0.68"}
MOVE_MIN = 0.06  # interest must move this much in a month to count as rising or falling (0.02 flagged nearly every good)

# ui_effect()'s figures for the row's good
BAR = good_var("spec_ui_bar")      # the bar, 0 to 1
# spec_ui_pos_<g>: word - 1 + bar, 0 to 6, the marker on interest_list's scale
# spec_ui_move_<g> (market_tab.MOVE, read by its tile tooltip): 1 interest rose by more than MOVE_MIN since last month, -1 fell
# spec_ui_badge_<g>: 1 a boom large enough to Collapse has turned
CAT = good_var("spec_ui_cat")      # the good's category, 1 + its index in CATEGORIES


def eq(a, n):
    return f"EqualTo_CFixedPoint({a}, {fx(n)})"


def cuts(k):
    """Where each band starts, Fleeing to Feverish, then the cap on interest."""
    return [k["HYPE_MIN"], k["CRASH_BELOW"], k["COOLING_HYPE"], k["RISING_HYPE"], k["HOT_HYPE"], k["PEAK_FOR_CRASH"], k["HYPE_MAX"]]


# -- script ------------------------------------------------------------------------------------------------

def ui_effect(k):
    """spec_ui_good = { G = <good> CAT = <1 + category index> }: the tile's figures, for a good traded here, from the
    month's interest (spec_hype), word, peak, severity and risk. Run where the tab can show them (generate.monthly).
    Bar: how far interest is from its band's start to the next band's start; Feverish has no band above, so its bar
    runs on to the cap: how deep into collapse danger the boom is. Move: which way interest went since last month.
    Badge: a boom that peaked high enough to Collapse and has fallen from its peak.
    ponytail: no sev = 3 clause; sev is 3 for every boom peaked that high (turning or not) and is reset in the month
    it collapses, so it would only bring back the badge on peaking booms."""
    c = cuts(k)
    g = "$G$"
    h, word, peak = f"var:spec_hype_{g}", f"var:spec_word_{g}", f"var:spec_peak_{g}"
    put = lambda name, val: f"set_variable = {{ name = spec_ui_{name}_{g} value = {val} }}"
    bar = "".join(f"\t\t{'if' if w == 1 else 'else_if'} = {{\n\t\t\tlimit = {{ {word} = {w} }}\n"
                  f"\t\t\t{put('bar', f'{{ value = {h} subtract = {lo:.4g} divide = {hi - lo:.4g} min = 0 max = 1 }}')}\n\t\t}}\n"
                  for w, (lo, hi) in enumerate(zip(c, c[1:]), 1))
    big = f"{peak} >= {k['PEAK_FOR_CRASH']}"
    near = f"{h} >= {{ value = {peak} multiply = {NEAR_PEAK} }}"
    return f"""# the Speculation tab's per-good figures (interest_board.py), so its tiles read one variable each frame
spec_ui_good = {{
	if = {{
		limit = {{ {word} > 0 }}
		{put('cat', '$CAT$')}
{bar}		{put('pos', f'{{ value = {word} subtract = 1 add = var:spec_ui_bar_{g} }}')}
		{put('move', 0)}
		if = {{
			limit = {{ has_variable = spec_hprev_{g} }}
			if = {{
				limit = {{ {h} > {{ value = var:spec_hprev_{g} add = {MOVE_MIN} }} }}
				{put('move', 1)}
			}}
			else_if = {{
				limit = {{ {h} < {{ value = var:spec_hprev_{g} subtract = {MOVE_MIN} }} }}
				{put('move', -1)}
			}}
		}}
		{put('badge', 0)}
		if = {{
			limit = {{
				{big}
				NOT = {{ {near} }}
				# a restrained boom eases down to Calm and cannot end there
				NOT = {{ has_variable = spec_restrain_{g} }}
			}}
			{put('badge', 1)}
		}}
		# interest_list's row state, one variable for its marker: 2 the boom ended this month (generate.monthly's
		# crash branch, which runs first), 3 in a glut after it, 1 turning as the badge, 0 none
		{put('state', 0)}
		if = {{
			limit = {{ has_variable = spec_ui_crash_{g} }}
			{put('state', 2)}
		}}
		else_if = {{
			limit = {{ has_variable = spec_glut_{g} }}
			{put('state', 3)}
		}}
		else_if = {{
			limit = {{ var:spec_ui_badge_{g} = 1 }}
			{put('state', 1)}
		}}
	}}
}}
"""


def monthly(goods, category):
    """For generate.monthly's tab block (3 tabs deep), after the band counts: each good's figures. category: good ->
    its CATEGORIES name."""
    return "".join(f"\t\t\tspec_ui_good = {{ G = {g} CAT = {CATEGORIES.index(category[g]) + 1} }}\n" for g in goods)


def state_vars(goods):
    return [f"spec_ui_{n}_{g}" for g in goods for n in ("bar", "pos", "move", "badge", "cat", "state", "crash")]


# -- interface ---------------------------------------------------------------------------------------------

def small_strip():
    """levers.strip() at tile size."""
    sizes = ('\tblockoverride "size" { size = { 32 28 } }\n\tblockoverride "button_size" { size = { 32 28 } }\n'
             '\tblockoverride "texture_size" { size = { 22 22 } }\n\tblockoverride "selected_frame_size" { size = { 34 31 } }\n')
    return (levers.strip().replace("set_level_bar_item = {\n", "set_level_bar_item = {\n" + sizes)
            .replace("flowcontainer = {\n", "flowcontainer = {\n\tparentanchor = hcenter\n", 1))


def loc(k):
    conf = "[concept_spec_market_confidence]"
    out = (" SPEC_IB_TURNING_TT: \"#header Boom Turning#!\\n$TOOLTIP_DELIMITER$\\n#italic [Goods.GetName] had a big boom, and it is fading.#!\\n"
           "\\nIf [concept_spec_investor_interest] keeps falling, it ends in a [concept_spec_collapse]\\n"
           f"That would cost about #N [{RISK}|1]#! {conf}\"\n"
           " SPEC_IB_HEAT_TT: \"#header [concept_spec_investor_interest] in [Goods.GetName]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_TILE_BODY$\"\n")
    # only the top band reads its bar out, as collapse danger. Below it no next band is named: that read as if interest
    # only ever rose
    pct = f"[{BAR}|%0]"
    out += (f" SPEC_TILE_NEXT: \"[SelectLocalization({eq(WORD, 6)}, 'SPEC_TILE_DANGER', 'SPEC_IB_EMPTY')]\"\n"
            " SPEC_IB_EMPTY: \"\"\n"
            f" SPEC_TILE_DANGER: \"\\nCollapse Zone: #v {pct}#! of the way to the top\\nThe higher it climbs, the "
            f"more {conf} a [concept_spec_collapse] would cost\"\n")
    return out


if __name__ == "__main__":
    k = {"HYPE_MIN": 0.05, "CRASH_BELOW": 0.167, "COOLING_HYPE": 0.5, "RISING_HYPE": 2, "HOT_HYPE": 3,
         "PEAK_FOR_CRASH": 6, "HYPE_MAX": 20}
    e = ui_effect(k)
    assert e.count("{") == e.count("}")
    assert "spec_ui_stage" not in e
    assert "subtract = 6 divide = 14 min = 0 max = 1" in e and "subtract = 0.05 divide = 0.117" in e
    assert ("var:spec_peak_$G$ >= 6\n\t\t\t\tNOT = { var:spec_hype_$G$ >= { value = var:spec_peak_$G$ multiply = 0.85 } }"
            in e and "spec_sev_" not in e)
    # the row state: the crash month before the glut it starts, both before turning
    assert e.index("has_variable = spec_ui_crash_$G$") < e.index("has_variable = spec_glut_$G$") < e.index("var:spec_ui_badge_$G$ = 1")
    assert "spec_ui_state_grain" in state_vars(["grain"]) and "spec_ui_crash_grain" in state_vars(["grain"])
    lo = loc(k)
    assert "SPEC_IB_TURNING_TT:" in lo and "SPEC_IB_TREND_TT" not in lo
    m = monthly(["grain"], {"grain": "staple"})
    assert "spec_ui_good = { G = grain CAT = 1 }" in m and "spec_ui_rows_w" not in m
    print("interest_board ok")
