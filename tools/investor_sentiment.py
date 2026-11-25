"""Rolling, price-led investor preferences. The old interest rankings still supply the story events."""

MONTHS = 12
QUALIFY = 6
MATURE = 9
PREMIUM = 0.10
SHARE = 0.01
BONUS = 0.10  # the base Investor Interest effect of a term (was a flat 0.12); the factors below scale it
# the effect's factors (2026-11-21), each a line in the good's tooltip, none capped:
GAP_FULL = 0.20      # price this far past base price gives the base effect; 10% half, 40% double
FADE_FROM = 6        # full strength until this many months are left, then it tapers to the term's end
EFFECT_TILT = 0.25   # Market Confidence: at 100 a Favored effect is x1.25 and a Shunned one x0.75, at 0 the reverse
SHARE_REF = 0.02     # a good with this share of market supply by value gets x1; each further 2% adds SHARE_WEIGHT
SHARE_WEIGHT = 0.25
TP_SHARE = 0.5       # the good's producers get this share of the effect as throughput
PASS_WEIGHT = 4
# ponytail: no cap on terms; each running term, Favored or Shunned, adds this many no-pick tickets to both draws
PASS_PER_TERM = 4
# Market Confidence tilts the draws: at 100 the Favored no-pick weight is x(1 - TILT) and the Shunned x(1 + TILT); at 0 the reverse
TILT = 0.5
CONF_MID = 50
SIDES = (("fav", 1), ("shun", -1))
LISTS = [f"spec_{kind}_goods" for kind, _ in SIDES]  # the running terms, rebuilt monthly, for the journal and Finance


def slots():
    return [f"spec_{kind}_n" for kind, _ in SIDES]


def state_vars(goods):
    return slots() + [f"spec_{v}_{g}" for g in goods for v in ("term", "case")]


def effects(goods):
    # Signed remaining months and consecutive observations. A running term earns no new evidence.
    term, case = "spec_term_$G$", "spec_case_$G$"
    side_blocks = []
    for kind, sign in SIDES:
        op = ">" if sign == 1 else "<"
        below_limit = "<" if sign == 1 else ">"
        variable = f"var:{case}"
        side_blocks.append(f"""spec_watch_{kind} = {{
    if = {{ limit = {{ NOT = {{ AND = {{ has_variable = {case} {variable} {op} 0 }} }} }} set_variable = {{ name = {case} value = 0 }} }}
    if = {{ limit = {{ {variable} {below_limit} {sign * MATURE} }} change_variable = {{ name = {case} add = {sign} }} }}
    if = {{ limit = {{ {variable} {op}= {sign * QUALIFY} }} set_local_variable = {{ name = spec_offer_{kind} value = yes }} }}
}}
""")
        side_blocks.append(f"""spec_list_{kind} = {{
    add_to_variable_list = {{ name = spec_{kind}_goods target = g:$G$ }}
    change_variable = {{ name = spec_{kind}_n add = 1 }}
    change_local_variable = {{ name = spec_sentiment_active add = 1 }}
}}
""")
    clock = f"""spec_sentiment_observe = {{
    if = {{ limit = {{ has_variable = {term} }}
        if = {{ limit = {{ var:{term} > 0 }} change_variable = {{ name = {term} subtract = 1 }} }}
        else = {{ change_variable = {{ name = {term} add = 1 }} }}
        if = {{ limit = {{ var:{term} = 0 }} remove_variable = {term} }}
    }}
    if = {{ limit = {{ has_variable = {term} var:{term} > 0 }} spec_list_fav = {{ G = $G$ }} }}
    else_if = {{ limit = {{ has_variable = {term} var:{term} < 0 }} spec_list_shun = {{ G = $G$ }} }}
    else_if = {{ limit = {{ $TURNOVER$ > 0 $PRICE$ >= {PREMIUM} }}
        spec_watch_fav = {{ G = $G$ }}
    }}
    else_if = {{ limit = {{ $TURNOVER$ > 0 $PRICE$ <= -{PREMIUM} }}
        spec_watch_shun = {{ G = $G$ }}
    }}
    else_if = {{ limit = {{ has_variable = {case} }} remove_variable = {case} }}
}}
"""
    pulse = ["spec_sentiment_monthly = {",
             f"    set_local_variable = {{ name = spec_sentiment_min value = {{ value = var:spec_mv_total multiply = {SHARE} min = 0.001 }} }}"]
    pulse += ["    set_local_variable = { name = spec_sentiment_active value = 0 }"]
    pulse += [f"    set_variable = {{ name = {slot} value = 0 }}" for slot in slots()] + [f"    clear_variable_list = {l}" for l in LISTS]
    pulse += [f"    spec_sentiment_observe = {{ G = {g} TURNOVER = spec_mv_{g} PRICE = spec_dev_{g} }}" for g in goods]
    for kind, sign in SIDES:
        op = ">=" if sign == 1 else "<="
        pulse += [f"    if = {{ limit = {{ has_local_variable = spec_offer_{kind} }}",
                  f"        set_local_variable = {{ name = spec_sentiment_pass value = {{ value = local_var:spec_sentiment_active multiply = {PASS_PER_TERM} add = {PASS_WEIGHT}",
                  f"            if = {{ limit = {{ has_variable = spec_conf }} multiply = {{ value = var:spec_conf subtract = {CONF_MID} divide = {CONF_MID} multiply = {-sign * TILT:g} add = 1 }} }} }} }}",
                  "        random_list = {",
                  "            0 = { modifier = { add = local_var:spec_sentiment_pass } }"]
        for g in goods:
            # A longer case and an established share of supply each add one ticket.
            for months, extra in ((QUALIFY, ""), (MATURE, ""), (QUALIFY, f" spec_mv_{g} >= local_var:spec_sentiment_min")):
                pulse.append(f"            1 = {{ trigger = {{ has_variable = spec_case_{g} var:spec_case_{g} {op} {sign * months}{extra} }} "
                             f"spec_grant_{kind} = {{ G = {g} }} }}")
        pulse += ["        }", "    }"]
        side_blocks.append(f"""spec_grant_{kind} = {{
    set_variable = {{ name = {term} value = {sign * MONTHS} }}
    remove_variable = {case}
    spec_list_{kind} = {{ G = $G$ }}
}}
""")
    return "\n".join(side_blocks) + clock + "\n".join(pulse + ["}", ""])


FACTORS = ("gap", "fade", "conf", "share")


def values(good):
    """The term's effect on a good: side (+1 Favored, -1 Shunned, 0 none) x BONUS x the four factors, and its throughput."""
    g, term = good, f"var:spec_term_{good}"
    on = f"has_variable = spec_term_{g} spec_mv_{g} > 0"
    return [
        f"spec_term_side_{g} = {{ value = 0 if = {{ limit = {{ {on} {term} > 0 }} value = 1 }} else_if = {{ limit = {{ {on} {term} < 0 }} value = -1 }} }}",
        # how far the price has run its way, past base price; a price back on the wrong side gives nothing
        f"spec_term_gap_{g} = {{ value = spec_dev_{g} multiply = spec_term_side_{g} divide = {GAP_FULL} min = 0 }}",
        f"spec_term_fade_{g} = {{ value = 0 if = {{ limit = {{ has_variable = spec_term_{g} }} value = {term} multiply = spec_term_side_{g} divide = {FADE_FROM} max = 1 }} }}",
        f"spec_term_conf_{g} = {{ value = 1 if = {{ limit = {{ has_variable = spec_conf }} value = var:spec_conf subtract = 50 divide = 50 "
        f"multiply = {EFFECT_TILT} multiply = spec_term_side_{g} add = 1 }} }}",
        f"spec_term_supply_{g} = {{ value = 0 if = {{ limit = {{ var:spec_mv_total > 0 }} value = spec_mv_{g} divide = var:spec_mv_total }} }}",
        f"spec_term_share_{g} = {{ value = spec_term_supply_{g} "
        f"divide = {SHARE_REF} subtract = 1 multiply = {SHARE_WEIGHT} add = 1 }}",
        f"spec_term_effect_{g} = {{ value = spec_term_side_{g} multiply = {BONUS} "
        + " ".join(f"multiply = spec_term_{f}_{g}" for f in FACTORS) + " }",
        f"spec_term_tp_{g} = {{ value = spec_term_effect_{g} multiply = {TP_SHARE} }}",
        # Investor Interest is multiplied by 1 + the effect; a huge Shunned effect empties it, no lower
        f"spec_sentiment_factor_{g} = {{ value = spec_term_effect_{g} add = 1 min = 0 }}",
    ]


def effect_np(np, side, months, dev, conf, share):
    """The same effect for the tuner (tools/tuner/engine.py): arrays of side, signed months, price premium,
    confidence (per country, broadcast) and share of supply."""
    gap = np.maximum(dev * side / GAP_FULL, 0)
    fade = np.minimum(np.abs(months) / FADE_FROM, 1)
    tilt = 1 + (conf - 50) / 50 * EFFECT_TILT * side
    weight = 1 + (share / SHARE_REF - 1) * SHARE_WEIGHT
    return side * BONUS * gap * fade * tilt * weight


def modifiers(made, icon_up, icon_down):
    """Older saves' country modifiers, now empty: the term's throughput (spec_term_tp_<g>) is in the good's building
    modifier (companies.bp_script, 2026-11-24)."""
    return "".join(f"spec_term_{k}_{g} = {{\n\ticon = {icon}\n}}\n\n"
                   for g in sorted(made) for k, icon in (("up", icon_up), ("down", icon_down)))
