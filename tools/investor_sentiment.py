"""Rolling, price-led investor preferences. The old interest rankings still supply the story events."""

MONTHS = 12
QUALIFY = 6
MATURE = 9
PREMIUM = 0.10
SHARE = 0.01
BONUS = 0.12
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


def factor(good):
    return f"""spec_sentiment_factor_{good} = {{
    value = 1
    if = {{ limit = {{ has_variable = spec_term_{good} spec_mv_{good} > 0 }}
        if = {{ limit = {{ var:spec_term_{good} > 0 }} value = {1 + BONUS:g} }}
        else = {{ value = {1 - BONUS:g} }}
    }}
}}"""
