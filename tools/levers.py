"""Speculation levers: per good, a country can Restrain Speculation (what the market makes of its interest pushed down
by PUSH over a few months, never below Calm, so its boom cannot crash while restrained but winds down as a Correction paid month by month (generate.py spec_c_restrain), the good's producers lose throughput and pay a levy) or Encourage Investment (interest
pushed up by PUSH over a few months, its producers gain throughput, paid for by the state), paid in Authority every month like a vanilla
consumption tax on the good. Throughput moves profits, which vanilla investors chase. A good has at most one lever;
Authority is the only limit on how many.

The money is a share of the country's weekly output of the good at base price, through vanilla's Additional Income
and Additional Expenses budget lines (country_tax_income_add, country_expenses_add, as vanilla's paid decisions do).
Vanilla subsidies are not used: set_subsidized has effect loc but no vanilla script calls it, it would overwrite the
player's own choices, and a subsidy only covers losses, so its cost would not follow the industry's size.

generate.py writes the script from script(), clamps hype with hype_clamp(), runs ai_block() and
then spec_update_levers in the monthly pulse (the costs move with the market) and adds loc(). The tab places strip() in a goods row (datacontext Goods)."""
import companies
import ig_stances
import leverage
import icons
import tuning

# Authority a month per lever, like a vanilla consumption tax on the good (its consumption_tax_cost, else
# NPolitics DEFAULT_GOODS_TAX_COST): LEVER_TAX_SHARE of it, from LEVER_FLOOR of that for a good with no share of the
# market's trade up to all of it at generate.EXPOSURE_FULL (spec_weight_<g>). A staple's high consumption-tax
# price measures the political cost of taxing households. Intervening in its producers uses the ordinary base instead.
DEFAULT_TAX_COST = 100
LEVER_TAX_SHARE = tuning.get("LEVER_TAX_SHARE", 0.5)
LEVER_FLOOR = 0.5
COST_STEP = 10          # the cost rounds to this, reading 30 or 120 rather than 37 or 123; the cheapest is 25, so never 0
LEVER_THROUGHPUT = tuning.get("LEVER_THROUGHPUT", 0.1)  # throughput of the good's producers: Encourage adds it, Restrain takes it away
# money a week, as a share of the country's weekly output of the good at base price: Encourage's subsidy, and
# Restrain's levy, lower so that restraining is not a money machine
SUBSIDY_SHARE = tuning.get("SUBSIDY_SHARE", 0.20)
LEVY_SHARE = tuning.get("LEVY_SHARE", 0.10)
AI_FUNDS = tuning.get("AI_FUNDS", 2)            # AI encourages only with a weekly surplus this many times the subsidy, and lifts it in deficit
AI_CONF = tuning.get("AI_CONF", 60)          # AI restrains its riskiest boom at this Market Confidence or above
AI_RISK = tuning.get("AI_RISK", 5)            # and only when its end would cost this much confidence (in practice a Collapse or a large Bust)
CALM_WORD = 3          # generate's interest word for Calm; the AI encourages only a Calm good
LEVER_EASE = tuning.get("LEVER_EASE", 0.35)  # a lever's push closes this share of the gap to its full size each month
RESTRAIN_TO = 1        # restrained interest never falls below this (Calm, above every unwind's end, so no boom ends while restrained)
# 1.2: each lever multiplies what the market makes of the good's interest, rather than setting it. PUSH is its size at
# Market Confidence PUSH_CONF (a flat market, 1, lands at Keen as the old target did); with m = confidence / PUSH_CONF
# (push_full), a confident market runs with Encourage, x(1 + 1.2m): 2.2 at 55, 2.9 at 85, 1.3 at 15, and shrugs off
# Restrain, /(1 + 1.2/m): 2.2 at 55, 1.8 at 85, 5.4 at 15, never below Calm. Restraining early works best; encouraging a
# scared market barely moves it. Was a flat x2.2 and /2.2, and before that a target (Calm, Keen) whatever the market did
PUSH = {"encourage": tuning.get("ENCOURAGE_PUSH", 2.2), "restrain": 1 / tuning.get("RESTRAIN_PUSH", 2.2)}
PUSH_CONF = tuning.get("CONF_START", 55)  # generate.CONF_START (asserted there), read from tuning: generate imports this module
RESTRAIN_RISK = 2      # Restrain needs Eager interest or more, or a boom whose end costs this much (a Correction never does)
ENCOURAGE_BELOW = 4    # Encourage needs interest below this word, Keen
# Float a Great Issue (plan_levers.md Phase 3): spec_issue_<g> and spec_issue for ISSUE_DAYS, spec_issue_cool from floating to a year past its end
# ponytail: centres.ON read from tuning, not imported: centres imports market_tab, which imports this module
ISSUE_ON = tuning.get("EXCHANGE_ON", 1) and tuning.get("EXCH_ISSUE_ON", 1)
# Exchange score while an issue runs, for a good with a full share of the market (spec_weight_<g> 1): x(1 + 0.25 x its
# weight), so an issue on a small good is a small bet. Was a flat x1.25 whatever the good, until 1.2: a good under
# generate.TOAST_SHARE risked no trust at its boom's end, so an issue on it was free score
ISSUE_SCORE = tuning.get("EXCH_ISSUE_SCORE", 1.25)
ISSUE_EXPO = tuning.get("EXCH_ISSUE_EXPO", 1.5)     # weight of the banks' loans into the good when its boom ends (exposure.py)
ISSUE_TRUST = tuning.get("EXCH_ISSUE_TRUST", 2)     # times the boom end's trust result (centres.TRUST_END)
# months on plain counters, not `days =` timers: after a save reload the engine sometimes kept spec_issue and
# spec_issue_cool past their timers while spec_issue_<g>, set with them, lapsed (runs/release_gate/pool_perf_106b7_r1)
ISSUE_MONTHS, COOL_MONTHS = 24, 12
# the Great Issue's paragraph in the Intervention concept (loc)
ISSUE_CONCEPT = (f"\\n\\n#b Float a Great Issue#! sells shares in a hot $concept_good$ on our [concept_spec_exchange] for #v {ISSUE_MONTHS // 12}#! years. "
                 f"Our [concept_spec_exchange] score rises by up to #P {ISSUE_SCORE - 1:.0%}#! for a $concept_good$ that makes up much of our trade, "
                 f"and the trust won or lost when its boom ends counts #v x{ISSUE_TRUST:g}#!. Only one runs at a time, at least #v {COOL_MONTHS // 12}#! year apart.") if ISSUE_ON else ""
# as vanilla's tariff levels (NDefines TARIFF_LEVEL_COOLDOWN_MONTHS, TARIFF_LEVEL_COOLDOWN_GRACE_PERIOD_DAYS): once the
# player switches a good's lever on or off, its levers wait WAIT_MONTHS monthly pulses (counters, as the issue's) to
# change again, save for GRACE_DAYS to change their mind. ponytail: players only, the AI's monthly rules already pace it
WAIT_MONTHS, GRACE_DAYS = 3, 7
# generate.monthly, for every country, after the AI floats
MONTHLY = ("\t\t\tspec_issue_clock = yes\n" if ISSUE_ON else "") + "\t\t\tspec_lever_clock = yes\n"
ISSUE_WORD = 5         # Eager or hotter, as cycle._hot
ISSUE_AI_CONF = 40
MODIFIERS = [  # name, script value giving its multiplier, icon, effects at a multiplier of 1
    ("spec_lever_restrain", "spec_lever_levy", "lever_restrain", {"country_tax_income_add": 1}),
    ("spec_lever_encourage", "spec_lever_spend", "lever_encourage", {"country_expenses_add": 1}),
    ("spec_levers", "spec_lever_authority", "lever_restrain", {"country_authority_add": -1}),
]
# country variables spec_update_levers stores for the tab's header, and the script value each holds
UI_CACHE = {"spec_c_lev_n": "spec_levers_used", "spec_c_lev_aut": "spec_lever_authority", "spec_c_xs_next": "spec_xs_next",
            "spec_c_panic_at": "spec_panic_at"}  # the last for the confidence bar's hover (market_tab.panic_hover)
LEGACY = ["spec_lever_encourage_industry", "spec_lever_encourage_land"]  # older saves' modifiers: kept empty, removed on update
KINDS = (("restrain", -LEVER_THROUGHPUT, "lever_restrain"), ("encourage", LEVER_THROUGHPUT, "lever_encourage"))
# building types whose own throughput modifier logs as unknown, and the group holding only them; banana plantations
# share theirs with every plantation, so fruit gets no throughput
GROUPS = {"logging_camp": "building_group_bg_logging", "oil_rig": "building_group_bg_oil_extraction"}
P = "Country.MakeScope"  # market_tab.P
_MADE = {}  # script()'s industry(), for loc()


def industry(sells, upgrades):
    """good -> the throughput modifier types of the buildings making it."""
    made = [(b, g) for m in sells.values() for b, g in m.items()] + [(b, g) for b, ups in upgrades.items() for g, _ in ups]
    out = {}
    for b, g in made:
        if b in GROUPS or b not in companies.NO_THROUGHPUT:
            out.setdefault(g, []).append(f"{GROUPS.get(b, 'building_' + b)}_throughput_add")
    return out


# -- script ------------------------------------------------------------------------------------------------

def push_full():
    """spec_push_full_<kind>: a lever's full push at our Market Confidence (country scope), m = confidence / PUSH_CONF.
    In generate's spec_values.txt before the goods' spec_push_next_<g>, which read them."""
    up, down = PUSH["encourage"] - 1, 1 / PUSH["restrain"] - 1
    return [f"spec_push_m = {{\n\tvalue = var:spec_conf\n\tdivide = {PUSH_CONF:g}\n}}",
            f"spec_push_full_encourage = {{\n\tvalue = spec_push_m\n\tmultiply = {up:.4g}\n\tadd = 1\n}}",
            f"spec_push_full_restrain = {{\n\tvalue = spec_push_m\n\tdivide = {{\n\t\tvalue = spec_push_m\n\t\tadd = {down:.4g}\n\t}}\n}}"]


def push_values(g):
    """spec_push_sv_<g>: the lever's push on the good's interest, a multiplier (1 without a lever; spec_push_<g> is
    kept only while one is on). spec_push_next_<g>: next month's, LEVER_EASE of the way to the lever's full push
    (push_full), so it builds over a few months. Lifting a lever ends its push at once, as lifting the old target did."""
    on = f"OR = {{ has_variable = spec_encourage_{g} has_variable = spec_restrain_{g} }}"
    return [f"spec_push_sv_{g} = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_push_{g}\n\t\t\t{on}\n\t\t}}\n"
            f"\t\tvalue = var:spec_push_{g}\n\t}}\n}}",
            f"spec_push_next_{g} = {{\n\tvalue = 1\n"
            + "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ has_variable = spec_{k}_{g} }}\n\t\tvalue = spec_push_full_{k}\n\t}}\n"
                      for i, k in enumerate(PUSH))
            + f"\tsubtract = spec_push_sv_{g}\n\tmultiply = {LEVER_EASE:g}\n\tadd = spec_push_sv_{g}\n}}"]


def hype_push(g, lo, hi):
    """Lines for the end of spec_hype_next_<g>: what the market makes of it times the lever's push, within the market's
    own bounds (lo, hi); restrained, never below RESTRAIN_TO."""
    return (f"\tmultiply = spec_push_next_{g}\n\tmin = {lo:g}\n\tmax = {hi:g}\n"
            f"\tif = {{\n\t\tlimit = {{ has_variable = spec_restrain_{g} }}\n\t\tmin = {RESTRAIN_TO}\n\t}}\n")


# the monthly pulse, after the good's interest is set from spec_hype_next_<g> (which read this month's push)
def push_update(g, t="\t\t\t"):
    return (f"{t}if = {{\n{t}\tlimit = {{ OR = {{ has_variable = spec_encourage_{g} has_variable = spec_restrain_{g} }} }}\n"
            f"{t}\tset_variable = {{ name = spec_push_{g} value = spec_push_next_{g} }}\n{t}}}\n"
            f"{t}else_if = {{\n{t}\tlimit = {{ has_variable = spec_push_{g} }}\n{t}\tremove_variable = spec_push_{g}\n{t}}}\n")



def state_vars(goods):
    return ([f"spec_{k}_{g}" for g in goods for k in ("restrain", "encourage", "push", "ui_r", "ui_e", "ui_co", "lever_wait", "lever_grace", "lever_pending")
             + (("issue",) if ISSUE_ON else ())]
            + (["spec_issue", "spec_issue_cool", "spec_issue_w"] if ISSUE_ON else []))


def ui_effect():
    """spec_lever_ui = { G = <good> }: the tab's per-good figures, so the GUI reads one variable instead of running
    the scripted GUIs' triggers every frame. spec_ui_r_<g>, spec_ui_e_<g>: 2 the lever is on, 1 it can be switched on
    (players only: authority moves within the month, so this lags until the next month or toggle, and the scripted
    GUIs' effects check again), 0 neither. spec_ui_co_<g>: the throughput % interest and lever give its producers,
    for the Companies section (companies.INTEREST_THROUGHPUT)."""
    state = "".join(f"""	if = {{
		limit = {{ has_variable = spec_{k}_$G$ }}
		set_variable = {{ name = spec_ui_{k[0]}_$G$ value = 2 }}
	}}
	else_if = {{
		limit = {{
			is_player = yes
			spec_lever_free = {{ KIND = {k} OTHER = {o} G = $G$ }}
		}}
		set_variable = {{ name = spec_ui_{k[0]}_$G$ value = 1 }}
	}}
	else = {{
		set_variable = {{ name = spec_ui_{k[0]}_$G$ value = 0 }}
	}}
""" for k, o in (("restrain", "encourage"), ("encourage", "restrain")))
    tiers = [(w, p) for w, p in companies.INTEREST_THROUGHPUT.items() if p]
    co = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ var:spec_word_$G$ ?= {w} }}\n"
                 f"\t\tset_variable = {{ name = spec_ui_co_$G$ value = {p} }}\n\t}}\n" for i, (w, p) in enumerate(tiers))
    lever = round(LEVER_THROUGHPUT * 100)
    return f"""spec_lever_ui = {{
{state}	set_variable = {{ name = spec_ui_co_$G$ value = 0 }}
{co}	if = {{
		limit = {{ has_variable = spec_restrain_$G$ }}
		change_variable = {{ name = spec_ui_co_$G$ add = -{lever} }}
	}}
	else_if = {{
		limit = {{ has_variable = spec_encourage_$G$ }}
		change_variable = {{ name = spec_ui_co_$G$ add = {lever} }}
	}}
}}
"""


def _count(name, kind, goods):
    return (f"{name} = {{\n\tvalue = 0\n"
            + "".join(f"\tif = {{\n\t\tlimit = {{ has_variable = spec_{kind}_{g} }}\n\t\tadd = 1\n\t}}\n" for g in goods) + "}")


def _chain(goods, body, trigger=False):
    """One branch per good, picked by scope:spec_good; body(g) is the branch's content."""
    pre = "trigger_" if trigger else ""
    return "".join(f"\t{pre}{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ scope:spec_good = {{ this = g:{g} }} }}\n"
                   f"\t\t{body(g)}\n\t}}\n" for i, g in enumerate(goods))


def cost_value(g, tax):
    """spec_lever_cost_<g>: the good's Authority a month (LEVER_TAX_SHARE); tax is its vanilla consumption_tax_cost."""
    # spec_lever_base_<g>: the cost before the share of trade, for the tooltip's breakdown
    base = min(tax or DEFAULT_TAX_COST, DEFAULT_TAX_COST) * LEVER_TAX_SHARE
    return (f"spec_lever_base_{g} = {base:g}\n"
            f"spec_lever_cost_{g} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_mv_total }}\n"
            f"\t\tvalue = spec_weight_{g}\n\t}}\n\tmultiply = {1 - LEVER_FLOOR:g}\n\tadd = {LEVER_FLOOR:g}\n"
            f"\tmultiply = {base / COST_STEP:g}\n\tround = yes\n\tmultiply = {COST_STEP}\n}}")


def money_values(g, cost):
    """spec_lever_output_<g>: the country's weekly output of g at its base price (cost); spec_lever_subsidy_<g> and
    spec_lever_levy_<g>: SUBSIDY_SHARE and LEVY_SHARE of it."""
    return [f"spec_lever_output_{g} = {{\n\tvalue = 0\n\tevery_scope_state = {{\n\t\tsg:{g} ?= {{\n\t\t\tadd = state_goods_production\n"
            f"\t\t}}\n\t}}\n\tmultiply = {cost:g}\n}}"] + [
        f"spec_lever_{name}_{g} = {{\n\tvalue = spec_lever_output_{g}\n\tmultiply = {share:g}\n\tround = yes\n}}"
        for name, share in (("subsidy", SUBSIDY_SHARE), ("levy", LEVY_SHARE))]


def _sum(name, kind, money, goods):
    return (f"{name} = {{\n\tvalue = 0\n" + "".join(
        f"\tif = {{\n\t\tlimit = {{ has_variable = spec_{kind}_{g} }}\n\t\tadd = spec_lever_{money}_{g}\n\t}}\n" for g in goods) + "}")


def script(goods, made, tax, cost):
    """{mod path: text} for the levers' script values, effects, triggers, scripted GUIs and modifiers.
    made: industry(); tax: {good: vanilla consumption_tax_cost}, without the goods that have none; cost: {good: base price}."""
    _MADE.clear()
    _MADE.update(made)  # for loc()
    on =lambda g: f"OR = {{ has_variable = spec_restrain_{g} has_variable = spec_encourage_{g} }}"
    # a script value must be defined before one that reads it: the costs first, and the file sorts after spec_values.txt
    values = [cost_value(g, tax.get(g)) for g in goods] + [s for g in goods for s in money_values(g, cost[g])]
    values += [_count("spec_n_restrain", "restrain", goods), _count("spec_n_encourage", "encourage", goods),
               "spec_levers_used = {\n\tvalue = spec_n_restrain\n\tadd = spec_n_encourage\n}",
               _sum("spec_lever_levy", "restrain", "levy", goods), _sum("spec_lever_spend", "encourage", "subsidy", goods),
               "spec_lever_authority = {\n\tvalue = 0\n" + "".join(
                   f"\tif = {{\n\t\tlimit = {{ {on(g)} }}\n\t\tadd = spec_lever_cost_{g}\n\t}}\n" for g in goods) + "}"]
    # each sum worked out once, into a local variable, not once for the test and again for the multiplier
    update = "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n"
                     f"\tset_local_variable = {{ name = spec_lever_n value = {n} }}\n"
                     f"\tif = {{\n\t\tlimit = {{ local_var:spec_lever_n > 0 }}\n\t\tadd_modifier = {{\n\t\t\tname = {m}\n\t\t\tmultiplier = local_var:spec_lever_n\n\t\t}}\n\t}}\n"
                     for m, n, *_ in MODIFIERS)
    update += "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m in LEGACY)
    update += "".join(f"\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_{k}_{g}\n\t\t\tNOT = {{ has_modifier = spec_lever_{k}_{g} }}\n\t\t}}\n"
                      f"\t\tadd_modifier = {{ name = spec_lever_{k}_{g} }}\n\t}}\n"
                      f"\telse_if = {{\n\t\tlimit = {{\n\t\t\tNOT = {{ has_variable = spec_{k}_{g} }}\n\t\t\thas_modifier = spec_lever_{k}_{g}\n\t\t}}\n"
                      f"\t\tremove_modifier = spec_lever_{k}_{g}\n\t}}\n" for g in sorted(made) for k, *_ in KINDS)
    # the tab's lever and company figures, only where the tab can show them (generate.monthly's gate)
    update += ("\tif = {\n\t\tlimit = {\n\t\t\tOR = {\n\t\t\t\tis_player = yes\n\t\t\t\tmarket ?= { owner ?= root }\n\t\t\t}\n\t\t}\n"
               + "".join(f"\t\tspec_lever_ui = {{ G = {g} }}\n" for g in goods)
               # the tab's header figures, stored: as script values the header read them every frame (a chain over
               # every good each); the monthly pulse reaches here after the month's Excess is in
               + "".join(f"\t\tset_variable = {{ name = {c} value = {n} }}\n" for c, n in UI_CACHE.items()) + "\t}\n")
    effects = f"""{ui_effect()}
# the levers' modifiers: the money and Authority ones with their amount as the multiplier, and each lever's
# throughput on its good's producers; then the tab's figures
spec_update_levers = {{
{update}}}

spec_lever_flip = {{
	if = {{
		limit = {{ has_variable = spec_$KIND$_$G$ }}
		remove_variable = spec_$KIND$_$G$
		remove_variable = spec_lever_pending_$G$
		remove_variable = spec_lever_grace_$G$
	}}
	else = {{
		set_variable = {{ name = spec_$KIND$_$G$ value = 1 }}
		set_variable = spec_lever_pending_$G$
		set_variable = {{ name = spec_lever_grace_$G$ days = {GRACE_DAYS} }}
	}}
	# either way the good's levers wait (WAIT_MONTHS), after a few days to change our mind
	set_variable = {{ name = spec_lever_wait_$G$ value = {WAIT_MONTHS} }}
}}

# from the scripted GUIs: switch lever KIND on or off for scope:spec_good
spec_lever_toggle = {{
{_chain(goods, lambda g: f"spec_lever_flip = {{ KIND = $KIND$ G = {g} }}")}	spec_update_levers = yes
}}

# monthly: the waits count down; a good whose wait ends gets its tab figures again, so its buttons light up now
spec_lever_clock = {{
	if = {{
		limit = {{ is_player = yes }}
{"".join(f'''		if = {{
			limit = {{ has_variable = spec_lever_wait_{g} }}
            if = {{
                limit = {{ has_variable = spec_lever_pending_{g} NOT = {{ has_variable = spec_lever_grace_{g} }} }}
                remove_variable = spec_lever_pending_{g}
                if = {{ limit = {{ has_variable = spec_encourage_{g} }} spec_igs_lever_encourage = {{ G = {g} }} }}
                else_if = {{ limit = {{ has_variable = spec_restrain_{g} }} spec_igs_lever_restrain = {{ G = {g} }} }}
            }}
			change_variable = {{ name = spec_lever_wait_{g} add = -1 }}
			if = {{
				limit = {{ var:spec_lever_wait_{g} <= 0 }}
				remove_variable = spec_lever_wait_{g}
				spec_lever_ui = {{ G = {g} }}
			}}
		}}
''' for g in goods)}	}}
}}
"""
    if ISSUE_ON:  # Float a Great Issue on good G: centres.boom_end ends it with the boom, else it lapses.
        # The cooldown starts now, to run a year past the lapse; a boom end resets it to a year from then
        # spec_issue and spec_issue_cool hold the monthly pulses left; spec_issue_clock counts them down
        # spec_issue_w: the good's weight (spec_weight_<g>) for the score (centres._issue_score), kept monthly: a script
        # value there cannot read spec_values.txt's, defined after it
        effects += (f"\nspec_issue_float = {{\n\tset_variable = {{ name = spec_issue_$G$ value = 1 }}\n"
                    "\tspec_igs_lever_issue = { G = $G$ }  # interest groups' approval (ig_stances.py)\n"
                    f"\tset_variable = {{ name = spec_issue value = {ISSUE_MONTHS} }}\n"
                    "\tset_variable = { name = spec_issue_w value = spec_weight_$G$ }\n"
                    f"\tset_variable = {{ name = spec_issue_cool value = {ISSUE_MONTHS + COOL_MONTHS} }}\n}}\n"
                    "\nspec_issue_clock = {\n" + "".join(
                        f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ has_variable = spec_issue_{g} }}\n"
                        f"\t\tset_variable = {{ name = spec_issue_w value = spec_weight_{g} }}\n\t}}\n" for i, g in enumerate(goods))
                    + "\tif = {\n\t\tlimit = { has_variable = spec_issue }\n"
                    "\t\tchange_variable = { name = spec_issue add = -1 }\n\t\tif = {\n\t\t\tlimit = { var:spec_issue <= 0 }\n"
                    "\t\t\tremove_variable = spec_issue\n" + "".join(f"\t\t\tremove_variable = spec_issue_{g}\n" for g in goods)
                    + "\t\t\tspec_update_levers = yes\n\t\t}\n\t}\n\tif = {\n\t\tlimit = { has_variable = spec_issue_cool }\n"
                    "\t\tchange_variable = { name = spec_issue_cool add = -1 }\n\t\tif = {\n\t\t\tlimit = { var:spec_issue_cool <= 0 }\n"
                    "\t\t\tremove_variable = spec_issue_cool\n\t\t}\n\t}\n}\n")
    # an issue and a lever never share a good: Restrain or Encourage could hold off the boom end that resolves the issue
    no_issue = ("""		custom_tooltip = {
			text = spec_lever_no_issue_tt
			NOT = { has_variable = spec_issue_$G$ }
		}
""" if ISSUE_ON else "")
    triggers = f"""# switching lever KIND on or off for good G: off needs only the wait over (WAIT_MONTHS) or its grace days left
spec_lever_free = {{
	custom_tooltip = {{
		text = spec_lever_wait_tt
		OR = {{
			NOT = {{ has_variable = spec_lever_wait_$G$ }}
			AND = {{ has_variable = spec_lever_grace_$G$ has_variable = spec_$KIND$_$G$ }}
		}}
	}}
	trigger_if = {{
		limit = {{ NOT = {{ has_variable = spec_$KIND$_$G$ }} }}
		custom_tooltip = {{
			text = spec_lever_market_tt
			spec_law_mult > 0
		}}
		custom_tooltip = {{
			text = spec_lever_not_$OTHER$_tt
			NOT = {{ has_variable = spec_$OTHER$_$G$ }}
		}}
		custom_tooltip = {{
			text = spec_lever_fits_$KIND$_tt
			spec_lever_fits_$KIND$ = {{ G = $G$ }}
		}}
{no_issue}		custom_tooltip = {{
			text = spec_lever_authority_tt
			authority >= spec_lever_cost_$G$
		}}
	}}
}}

spec_lever_fits_restrain = {{
	OR = {{
		var:spec_word_$G$ >= 5
		var:spec_risk_$G$ >= {RESTRAIN_RISK}
	}}
}}

spec_lever_fits_encourage = {{
	var:spec_word_$G$ < {ENCOURAGE_BELOW}
	NOT = {{ has_variable = spec_glut_$G$ }}
	# not to hold up a boom that could end in a Bust or Collapse (generate.py lifts it once one starts)
	OR = {{
		NOT = {{ has_variable = spec_sev_$G$ }}
		var:spec_sev_$G$ < 2
	}}
}}

spec_can_lever = {{
{_chain(goods, lambda g: f"spec_lever_free = {{ KIND = $KIND$ OTHER = $OTHER$ G = {g} }}", trigger=True)}}}

# goods scope: a lever on it changes its producers' throughput
spec_lever_producers = {{
	OR = {{
{"".join(f"		this = g:{g}{chr(10)}" for g in sorted(made))}	}}
}}
"""
    if ISSUE_ON:
        triggers += f"""
# Float a Great Issue on good G
spec_issue_free = {{
	custom_tooltip = {{
		text = spec_issue_stand_tt
		AND = {{
			has_variable = spec_exch_stand
			var:spec_exch_stand >= 1
		}}
	}}
	custom_tooltip = {{
		text = spec_issue_hot_tt
		var:spec_word_$G$ >= {ISSUE_WORD}
	}}
	custom_tooltip = {{
		text = spec_issue_one_tt
		NOT = {{ has_variable = spec_issue }}
	}}
	custom_tooltip = {{
		text = spec_issue_cool_tt
		NOT = {{ has_variable = spec_issue_cool }}
	}}
	custom_tooltip = {{
		text = spec_issue_no_lever_tt
		NOT = {{ has_variable = spec_restrain_$G$ }}
		NOT = {{ has_variable = spec_encourage_$G$ }}
	}}
}}

spec_can_issue = {{
{_chain(goods, lambda g: f"spec_issue_free = {{ G = {g} }}", trigger=True)}}}
"""
    sguis = "".join(f"""spec_sgui_{k} = {{
	scope = country
	saved_scopes = {{ spec_good }}
	is_valid = {{ spec_can_lever = {{ KIND = {k} OTHER = {o} }} }}
	# the button's enabled state is spec_ui_{k[0]}_<g>, which can lag a month behind Authority: check again
	effect = {{
		if = {{
			limit = {{ spec_can_lever = {{ KIND = {k} OTHER = {o} }} }}
			hidden_effect = {{ spec_lever_toggle = {{ KIND = {k} }} }}
		}}
	}}
}}

""" for k, o in (("restrain", "encourage"), ("encourage", "restrain")))
    sguis += """# for the tab: a lever on scope:spec_good changes its producers' throughput
spec_sgui_lever_producers = {
	scope = country
	saved_scopes = { spec_good }
	is_valid = { scope:spec_good = { spec_lever_producers = yes } }
}
"""
    if ISSUE_ON:
        sguis += f"""
spec_sgui_issue = {{
	scope = country
	saved_scopes = {{ spec_good }}
	is_valid = {{ spec_can_issue = yes }}
	effect = {{
		if = {{
			limit = {{ spec_can_issue = yes }}
{_chain(goods, lambda g: f"spec_issue_float = {{ G = {g} }}")}			spec_update_levers = yes
		}}
	}}
}}
"""
    mods = "".join(f"{m} = {{\n\ticon = {icons.path(icon)}\n" + "".join(f"\t{k} = {v:g}\n" for k, v in fx.items())
                   + "}\n\n" for m, _, icon, fx in MODIFIERS)
    mods += "".join(f"spec_lever_{k}_{g} = {{\n\ticon = {icons.path(icon)}\n" + "".join(f"\t{t} = {v:g}\n" for t in made[g])
                    + "}\n\n" for g in sorted(made) for k, v, icon in KINDS)
    mods += "".join(f"{m} = {{\n\ticon = {icons.path('lever_encourage')}\n}}\n\n" for m in LEGACY)
    return {"common/script_values/spec_values_levers.txt": "\n\n".join(values) + "\n",
            "common/scripted_effects/spec_lever_effects.txt": effects,
            "common/scripted_triggers/spec_lever_triggers.txt": triggers,
            "common/scripted_guis/spec_lever_sguis.txt": sguis,
            "common/static_modifiers/spec_lever_modifiers.txt": "# applied by spec_update_levers: the money and Authority ones multiplied by their amount, then each lever's throughput\n" + mods}


def ai_block(goods, hot, rising, cooling):
    """For the AI section of the monthly pulse (4 tabs deep): restrain the riskiest boom while confidence is high,
    lift the restraint once its peak has faded below Keen (rising), or once the good's interest, unrestrained, is no
    longer booming (below hot) and not falling (cooling or more), so lifting cannot end the boom at once; then encourage()."""
    t = "\t\t\t\t"
    lift = "".join(f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_restrain_{g}\n{t}\t\tOR = {{\n"
                   f"{t}\t\t\tvar:spec_peak_{g} < {rising}\n"
                   f"{t}\t\t\tAND = {{\n{t}\t\t\t\tspec_hype_raw_{g} < {hot}\n{t}\t\t\t\tspec_hype_raw_{g} >= {cooling}\n{t}\t\t\t}}\n"
                   f"{t}\t\t}}\n{t}\t}}\n"
                   f"{t}\tremove_variable = spec_restrain_{g}\n{t}}}\n" for g in goods)
    free = lambda g: (f"NOT = {{ has_variable = spec_restrain_{g} }} NOT = {{ has_variable = spec_encourage_{g} }} "
                      + (f"NOT = {{ has_variable = spec_issue_{g} }} " if ISSUE_ON else "") + afford(g))
    best = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ {free(g)} var:spec_risk_{g} > var:spec_ai_risk }}\n"
                   f"{t}\t\tset_variable = {{ name = spec_ai_risk value = var:spec_risk_{g} }}\n{t}\t}}\n" for g in goods)
    pick = "".join(f"{t}\t\t{'if' if i == 0 else 'else_if'} = {{\n{t}\t\t\tlimit = {{ {free(g)} var:spec_risk_{g} = var:spec_ai_risk }}\n"
                   f"{t}\t\t\tset_variable = {{ name = spec_restrain_{g} value = 1 }}\n"
                   f"{t}\t\t\tspec_igs_lever_restrain = {{ G = {g} }}\n{t}\t\t}}\n" for i, g in enumerate(goods))
    return (f"{t}# speculation levers: restrain the riskiest boom, lift it once the boom has passed\n{lift}"
            # or, with the banks lent past the safe line, at any confidence: the booms they financed end harder (exposure.py)
            f"{t}if = {{\n{t}\tlimit = {{ OR = {{ var:spec_conf >= {AI_CONF} spec_lev >= {leverage.SAFE} }} }}\n"
            f"{t}\tset_variable = {{ name = spec_ai_risk value = 0 }}\n{best}"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_ai_risk >= {AI_RISK} }}\n{pick}{t}\t}}\n"
            f"{t}\tremove_variable = spec_ai_risk\n{t}}}\n"
            + TR("issue_ai", t) + encourage(goods) + issue_ai(goods) + TR("aidone", t))


def TR(name, t=""):
    """ponytail: crash hunt only (SPEC_TRACE=1): a log line naming the lever block about to run"""
    import os
    return f'{t}debug_log = "TRACE {name} [THIS.GetCountry.GetTagName]"\n' if os.environ.get("SPEC_TRACE") else ""


def issue_ai(goods):
    """For ai_block: a National Exchange or higher, confident, floats an issue on its biggest good at Eager or hotter.
    ponytail: deterministic, no roll; the cooldown paces it."""
    if not ISSUE_ON:
        return ""
    t = "\t\t\t\t"
    hot = lambda g: (f"var:spec_word_{g} >= {ISSUE_WORD} NOT = {{ has_variable = spec_restrain_{g} }} "
                     f"NOT = {{ has_variable = spec_encourage_{g} }}")
    best = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ {hot(g)} spec_weight_{g} > var:spec_ai_risk }}\n"
                   f"{t}\t\tset_variable = {{ name = spec_ai_risk value = spec_weight_{g} }}\n{t}\t}}\n" for g in goods)
    pick = "".join(f"{t}\t\t{'if' if i == 0 else 'else_if'} = {{\n{t}\t\t\tlimit = {{ {hot(g)} spec_weight_{g} = var:spec_ai_risk }}\n"
                   f"{t}\t\t\tspec_issue_float = {{ G = {g} }}\n{t}\t\t}}\n" for i, g in enumerate(goods))
    return (f"{t}# and float a Great Issue on its biggest hot good (Exchange)\n"
            f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_exch_stand\n{t}\t\tvar:spec_exch_stand >= 1\n"
            f"{t}\t\tvar:spec_conf >= {ISSUE_AI_CONF}\n{t}\t\thas_variable = spec_mv_total\n"
            f"{t}\t\tNOT = {{ has_variable = spec_issue }}\n{t}\t\tNOT = {{ has_variable = spec_issue_cool }}\n{t}\t}}\n"
            f"{t}\tset_variable = {{ name = spec_ai_risk value = 0 }}\n{best}"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_ai_risk > 0 }}\n{pick}{t}\t}}\n"
            f"{t}\tremove_variable = spec_ai_risk\n{t}}}\n")


def afford(g):
    """AI trigger: Authority to spare for a lever on g, twice its cost."""
    return f"authority >= {{ value = spec_lever_cost_{g} multiply = 2 }}"


def encourage(goods):
    """For ai_block: while Wary, encourage the most favored Calm good, one at a time, if the budget's surplus covers
    the subsidy AI_FUNDS times; lift it once confidence is back, a panic starts or the budget is in deficit.
    The confidence thresholds are the AI's credit ones (credit_ai.py), so temperament moves both."""
    t = "\t\t\t\t"
    free = lambda g: (f"NOT = {{ has_variable = spec_restrain_{g} }} {afford(g)} in_default = no "
                      + (f"NOT = {{ has_variable = spec_issue_{g} }} " if ISSUE_ON else "") +
                      f"net_total_income > {{ value = spec_lever_subsidy_{g} multiply = {AI_FUNDS} }}")
    lift = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = spec_encourage_{g} }}\n"
                   f"{t}\t\tremove_variable = spec_encourage_{g}\n{t}\t}}\n" for g in goods)
    # the cheap word test first: free() sums the good's output over every state
    best = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_word_{g} = {CALM_WORD} var:spec_hype_{g} > var:spec_ai_risk {free(g)} }}\n"
                   f"{t}\t\tset_variable = {{ name = spec_ai_risk value = var:spec_hype_{g} }}\n{t}\t}}\n" for g in goods)
    pick = "".join(f"{t}\t\t{'if' if i == 0 else 'else_if'} = {{\n{t}\t\t\tlimit = {{ var:spec_word_{g} = {CALM_WORD} "
                   f"var:spec_hype_{g} = var:spec_ai_risk {free(g)} }}\n"
                   f"{t}\t\t\tset_variable = {{ name = spec_encourage_{g} value = 1 }}\n"
                   f"{t}\t\t\tspec_igs_lever_encourage = {{ G = {g} }}\n{t}\t\t}}\n" for i, g in enumerate(goods))
    return (f"{t}# and encourage the most favored Calm good while Wary, lifting it once confidence is back\n"
            f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tOR = {{\n{t}\t\t\tvar:spec_conf >= spec_ai_unloose_at\n"
            f"{t}\t\t\thas_variable = spec_panic\n{t}\t\t\tnet_total_income < 0\n{t}\t\t\tin_default = yes\n"
            f"{t}\t\t}}\n{t}\t}}\n{lift}{t}}}\n"
            f"{t}else_if = {{\n{t}\tlimit = {{\n{t}\t\tvar:spec_conf < spec_ai_loose_at\n"
            f"{t}\t\tspec_n_encourage = 0\n{t}\t}}\n"
            f"{t}\tset_variable = {{ name = spec_ai_risk value = 0 }}\n{best}"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_ai_risk > 0 }}\n{pick}{t}\t}}\n"
            f"{t}\tremove_variable = spec_ai_risk\n{t}}}\n")


# -- interface ---------------------------------------------------------------------------------------------

SCOPE = f"GuiScope.SetRoot({P}).AddScope('spec_good', Goods.MakeScope).End"


def _sg(key, call):
    s = f"GetScriptedGui('spec_sgui_{key}').{call}({SCOPE})"
    return f"And(Country.IsLocalPlayer, {s})" if call == "IsValid" else s


def active(kind):
    """GUI expression, inside [...]: lever kind is on for the row's good."""
    return f"GreaterThan_CFixedPoint({P}.Var(Concatenate('spec_{kind}_', Goods.GetKey)).GetValueWithDefault('(CFixedPoint)0'), '(CFixedPoint)0')"


def _item(tooltip, texture, enabled, onclick, selected, sound, visible=None, lift=True):
    """One set_level_bar_item, as in the market panel's tariff control. lift: clicking the selected icon lifts it;
    without, the selected icon is a passive marker, as vanilla's."""
    click = f'\n\t\tonclick = "[{onclick}]"\n\t\tusing = {sound}' if lift else ""
    return f"""set_level_bar_item = {{
{f'	visible = "[{visible}]"' + chr(10) if visible else ''}	tooltip = "{tooltip}"
	blockoverride "button_texture" {{
		texture = "{texture}"
	}}
	blockoverride "click" {{
		enabled = "[{enabled}]"
		onclick = "[{onclick}]"
		using = {sound}
	}}
	blockoverride "is_selected_visibility" {{
		visible = {f'"[{selected}]"' if selected else "no"}
	}}
	# vanilla draws the selected icon as a button on top with no click, which would swallow the click that lifts it
	blockoverride "selected_texture_size" {{
		size = {{ 28 28 }}{click}
	}}
	blockoverride "is_clickable_alpha" {{
		alpha = "[TransparentIfFalse({enabled})]"
	}}
}}
"""


def locked():
    """GUI test: the row's good was switched lately (spec_flip's wait) and its days to change our mind are over."""
    has = lambda name: f"{P}.Var(Concatenate('{name}_', Goods.GetKey)).IsSet"
    return f"And({has('spec_lever_wait')}, Not({has('spec_lever_grace')}))"


def ui_state(kind):
    """GUI value: spec_ui_<r|e>_<good> (ui_effect()), 2 on, 1 can be switched on, 0 neither."""
    return f"{P}.Var(Concatenate('spec_ui_{kind[0]}_', Goods.GetKey)).GetValueWithDefault('(CFixedPoint)0')"


def strip():
    """The intervention control for a goods row, in the style of vanilla's tariff level bar: Restrain and Encourage,
    the one in effect framed, either greyed out where it can't be used. The scripted GUIs toggle, so clicking the one
    in effect lifts it. Needs datacontext Goods. The state is read from ui_state(), not the scripted GUIs' IsValid,
    which would run their triggers every frame for every tile; IsValidTooltip stays, as tooltips run on hover only."""
    def enabled(kind):  # on, or (for the local player only, as IsValid was) can be switched on; not while it waits
        return (f"And(GreaterThan_CFixedPoint({ui_state(kind)}, Select_CFixedPoint(Country.IsLocalPlayer, '(CFixedPoint)0', "
                f"'(CFixedPoint)1')), Not({locked()}))")
    on = lambda kind: f"EqualTo_CFixedPoint({ui_state(kind)}, '(CFixedPoint)2')"
    items = (_item("SPEC_LEVER_RESTRAIN_TT", icons.path("lever_restrain"), enabled("restrain"),
                   _sg("restrain", "Execute"), on("restrain"), "decrease_button_sound")
             + _item("SPEC_LEVER_ENCOURAGE_TT", icons.path("lever_encourage"), enabled("encourage"),
                     _sg("encourage", "Execute"), on("encourage"), "increase_button_sound"))
    if ISSUE_ON:  # the gate from variables, not IsValid (as above); the scripted GUI checks again on click
        at_least = lambda var, n: f"GreaterThanOrEqualTo_CFixedPoint({P}.Var({var}).GetValueWithDefault('(CFixedPoint)0'), '(CFixedPoint){n}')"
        unset = lambda name: f"Not({P}.Var('{name}').IsSet)"
        stand, word = at_least("'spec_exch_stand'", 1), at_least("Concatenate('spec_word_', Goods.GetKey)", ISSUE_WORD)
        no_lever = f"And(Not({on('restrain')}), Not({on('encourage')}))"
        can = (f"And(Country.IsLocalPlayer, And({unset('spec_issue')}, And({unset('spec_issue_cool')}, "
               f"And({stand}, And({word}, {no_lever})))))")
        # an issue can't be lifted, so its selected icon is a passive marker
        items += _item("SPEC_LEVER_ISSUE_TT", icons.path("lever_issue"), can,
                       _sg("issue", "Execute"), active("issue"), "increase_button_sound", lift=False)
    return "flowcontainer = {\n\tusing = set_level_bar_background\n\tignoreinvisible = yes\n" + "\n".join(
        "\t" + line if line.strip() else line for line in items.splitlines()) + "\n}\n"


def loc():
    stored = lambda c: f"{P}.Var('{c}').GetValueWithDefault('(CFixedPoint)0')"  # UI_CACHE
    used = f"[{stored('spec_c_lev_n')}|0]"
    cost = f"[{stored('spec_c_lev_aut')}|0]"
    tp = lambda key: f"[SelectLocalization({_sg('lever_producers', 'IsValid')}, '{key}', 'SPEC_LEVER_NONE')]"
    on = lambda k, a, b: f"[SelectLocalization({active(k)}, '{a}', '{b}')]"
    head = "#header {}#!\\n$TOOLTIP_DELIMITER$\\n"
    gsv = lambda name: f"{P}.ScriptValue(Concatenate('{name}_', Goods.GetKey))"
    weight = f"Add_CFixedPoint(Multiply_CFixedPoint({gsv('spec_weight')}, '(CFixedPoint){1 - LEVER_FLOOR:g}'), '(CFixedPoint){LEVER_FLOOR:g}')"
    share = f"Divide_CFixedPoint({gsv('spec_mv')}, Max_CFixedPoint({P}.Var('spec_mv_total').GetValueWithDefault('(CFixedPoint)1'), '(CFixedPoint)1'))"
    # in vanilla's calculator form (BASE_VALUE_FOR_CALCULATOR), as cost_value() makes it
    cost_line = (f"Ties up #N [{gsv('spec_lever_cost')}|0]#! [concept_authority] while in effect, returned when lifted"
                 f"#indent_newline:3 \\n#v [{gsv('spec_lever_base')}|0]#! base cost, capped at #v {DEFAULT_TAX_COST * LEVER_TAX_SHARE:g}#!"
                 f"\\n#v x[{weight}|%0]#! from its #v [{share}|%1]#! share of our market's trade#!")
    money = lambda kind: f"[{P}.ScriptValue(Concatenate('spec_lever_{kind}_', Goods.GetKey))|D]"
    n = stored("spec_c_lev_n")
    gt_used = f"GreaterThan_CFixedPoint({n}, '(CFixedPoint)0')"
    one_used = f"EqualTo_CFixedPoint({n}, '(CFixedPoint)1')"
    names = "".join(f' spec_lever_restrain_{g}: "${g}$ Levy"\n spec_lever_encourage_{g}: "${g}$ Subsidy"\n' for g in sorted(_MADE))
    return names + f""" spec_lever_restrain: "Speculation Levies"
 spec_lever_encourage: "Investment Subsidies"
 spec_lever_market_tt: "Our $ECONOMIC_SYSTEM_GC_LINK$ lets investors chase prices"
 spec_lever_not_restrain_tt: "Speculation in this good is not restrained"
 spec_lever_not_encourage_tt: "Investment in this good is not encouraged"
 spec_levers: "Market Interventions"
 spec_lever_authority_tt: "Enough [concept_authority] is available"
 spec_lever_wait_tt: "Not switched on or off in the last #v {WAIT_MONTHS}#! months, or activated less than #v {GRACE_DAYS}#! days ago and can still be undone"
 SPEC_LEVER_WAIT: "\\n#N Switched lately.#! It can change again in #v [{P}.Var(Concatenate('spec_lever_wait_', Goods.GetKey)).GetValueWithDefault('(CFixedPoint)0')|0]#! months"
 spec_lever_fits_restrain_tt: "[concept_spec_investor_interest] #v Eager#! or higher, or a boom whose end costs #v {RESTRAIN_RISK}#! or more [concept_spec_market_confidence]"
 spec_lever_fits_encourage_tt: "[concept_spec_investor_interest] below #v Keen#!, not recovering from a [concept_spec_boom_end], and no boom that could end in a [concept_spec_bust] or [concept_spec_collapse]"
 SPEC_LEVER_RESTRAIN_TT: "{head.format('Restrain Speculation in [Goods.GetName]')}[concept_spec_investor_interest] is multiplied by #N [{P}.ScriptValue('spec_push_full_restrain')|2]#! over a few months, but never below #v Calm#!. The higher our [concept_spec_market_confidence], the less the market listens.\\n{tp('SPEC_LEVER_TP_DOWN')}Its makers pay a levy of #P @money!{money('levy')}#! a week, #v {LEVY_SHARE:.0%}#! of their output\\nIts boom cannot end all at once. It winds down over about a year, costing no more [concept_spec_market_confidence] than a [concept_spec_correction]{ig_stances.lever_lines('restrain')}\\n\\n{cost_line}{on('restrain', 'SPEC_LEVER_LIFT', 'SPEC_LEVER_NONE')}[AddLocalizationIf({locked()}, 'SPEC_LEVER_WAIT')]\\n\\n[{_sg('restrain', 'IsValidTooltip')}]"
 SPEC_LEVER_ENCOURAGE_TT: "{head.format('Encourage Investment in [Goods.GetName]')}[concept_spec_investor_interest] is multiplied by #P [{P}.ScriptValue('spec_push_full_encourage')|2]#! over a few months. The higher our [concept_spec_market_confidence], the more the market follows.\\n{tp('SPEC_LEVER_TP_UP')}Its makers are paid a subsidy of #N @money!{money('subsidy')}#! a week, #v {SUBSIDY_SHARE:.0%}#! of their output\\nIt ends by itself once [concept_spec_investor_interest] reaches #v Eager#!{ig_stances.lever_lines('encourage')}\\n\\n{cost_line}{on('encourage', 'SPEC_LEVER_LIFT', 'SPEC_LEVER_NONE')}[AddLocalizationIf({locked()}, 'SPEC_LEVER_WAIT')]\\n\\n[{_sg('encourage', 'IsValidTooltip')}]"
 SPEC_LEVER_TP_DOWN: "Its makers lose #N {LEVER_THROUGHPUT:.0%}#! [concept_throughput]\\n"
 SPEC_LEVER_TP_UP: "Its makers gain #P {LEVER_THROUGHPUT:.0%}#! [concept_throughput]\\n"
 SPEC_LEVER_LIFT: "\\n\\nIn effect, multiplying [concept_spec_investor_interest] by #v [{gsv('spec_push_sv')}|2]#! so far\\n#instruction Click to lift it#!"
 SPEC_LEVER_NONE: ""
 SPEC_LEVERS_RIGHT: "[SelectLocalization({gt_used}, SelectLocalization({one_used}, 'SPEC_LEVERS_ONE', 'SPEC_LEVERS_MANY'), 'SPEC_LEVER_NONE')]"
 SPEC_LEVERS_ONE: "1 Intervention: #N -{cost}#! @aut!"
 SPEC_LEVERS_MANY: "{used} Interventions: #N -{cost}#! @aut!"
 concept_spec_intervention: "Intervention"
 concept_spec_intervention_desc: "The government stepping into the market for one [concept_good]. A good can have only one at a time, and once one is switched on or off it cannot change again for #v {WAIT_MONTHS}#! months.\\n\\n#b Restrain Speculation#! pushes [concept_spec_investor_interest] down, never below #v Calm#!, so its boom winds down as a [concept_spec_correction] instead of crashing. Its makers lose #N {LEVER_THROUGHPUT:.0%}#! [concept_throughput] and pay a levy of #v {LEVY_SHARE:.0%}#! of their output a week.\\n\\n#b Encourage Investment#! pushes $concept_spec_investor_interest$ up until it reaches #v Eager#!, then ends by itself. Its makers gain #P {LEVER_THROUGHPUT:.0%}#! $concept_throughput$ and are paid a subsidy of #v {SUBSIDY_SHARE:.0%}#! of their output a week.\\n\\nBoth build up over a few months and tie up [concept_authority] while in effect, up to #v {LEVER_TAX_SHARE * DEFAULT_TAX_COST:g}#! per good. Widely traded $concept_goods$ cost more to manage. The higher our [concept_spec_market_confidence], the further the market follows Encourage and the less it listens to Restrain. At #v {PUSH_CONF}#! confidence, Restrain multiplies $concept_spec_investor_interest$ by #N {PUSH['restrain']:.2f}#! and Encourage by #P {PUSH['encourage']:g}#!.{ISSUE_CONCEPT}"
{issue_loc(head)} SPEC_LEVERS_TT: "#header Market Interventions#!\\n$TOOLTIP_DELIMITER$\\nWe restrain speculation in #v [{P}.ScriptValue('spec_n_restrain')|0]#! goods and encourage investment in #v [{P}.ScriptValue('spec_n_encourage')|0]#!.\\n\\nThey tie up #N {cost}#! [concept_authority]. Levies bring in #P @money![{P}.ScriptValue('spec_lever_levy')|D]#! a week as [concept_budget_additional_income], and subsidies cost #N @money![{P}.ScriptValue('spec_lever_spend')|D]#! a week as [concept_budget_additional_expenses]."
"""


def issue_loc(head):
    if not ISSUE_ON:
        return ""
    years = ISSUE_MONTHS // 12
    # the ranking concept, shown as plain "Exchange score" whatever the concept is called
    SCORE = "[concept_spec_exchange] score"
    on = f"[SelectLocalization({active('issue')}, 'SPEC_ISSUE_ON', 'SPEC_LEVER_NONE')]"
    return f""" SPEC_LEVER_ISSUE_TT: "{head.format('Float a Great Issue in [Goods.GetName]')}For #v {years}#! years, our {SCORE} rises by #P [Multiply_CFixedPoint({P}.ScriptValue(Concatenate('spec_weight_', Goods.GetKey)), '(CFixedPoint){ISSUE_SCORE - 1:g}')|%0]#!, up to #P {ISSUE_SCORE - 1:.0%}#! for a [concept_good] that makes up much of our market's trade\\nWhen its boom ends, bank loans in it hurt #N x{ISSUE_EXPO:g}#! as much, and the trust won or lost is #v x{ISSUE_TRUST:g}#! as big\\nIf it ends in a [concept_spec_bust] or [concept_spec_collapse], the groups favoring it lose twice the usual [concept_approval]{ig_stances.lever_lines('issue')}\\n$TOOLTIP_DELIMITER$\\nOnly one at a time, at least #v {COOL_MONTHS // 12}#! year apart{on}\\n\\n[{_sg('issue', 'IsValidTooltip')}]"
 SPEC_ISSUE_ON: "\\n\\nThe issue ends in #v [{P}.Var('spec_issue').GetValue|0]#! months, and the next can float in #v [{P}.Var('spec_issue_cool').GetValueWithDefault('(CFixedPoint)0')|0]#!."
 spec_issue_stand_tt: "Our [concept_spec_exchange] stands #v National#! or higher"
 spec_issue_hot_tt: "[concept_spec_investor_interest] is #v Eager#! or higher"
 spec_issue_one_tt: "No other issue is running"
 spec_issue_cool_tt: "The market has had a year's rest since the last issue"
 spec_issue_no_lever_tt: "No [concept_spec_intervention] is in effect on this [concept_good]"
 spec_lever_no_issue_tt: "No Great Issue is running on this [concept_good]"
"""


if __name__ == "__main__":
    made = industry({"02_agro": {"wheat_farm": "grain"}, "x": {"steel_mill": "steel", "logging_camp": "wood", "banana_plantation": "fruit"}},
                    {"steel_mill": [("tools", "t")]})
    assert made["wood"] == ["building_group_bg_logging_throughput_add"] and "fruit" not in made
    assert made["steel"] == ["building_steel_mill_throughput_add"] and made["tools"] == made["steel"]
    out = script(["fruit", "grain", "steel", "wine"], made, {"grain": 500}, {"fruit": 30, "grain": 20, "steel": 50, "wine": 50})
    v, m = out["common/script_values/spec_values_levers.txt"], out["common/static_modifiers/spec_lever_modifiers.txt"]
    # costs in tens: the share of the tax in steps, rounded, then back up
    assert "multiply = 25\n\tround = yes\n\tmultiply = 10\n" in v and "multiply = 5\n\tround = yes\n\tmultiply = 10\n" in v
    assert "add = spec_lever_cost_wine" in v
    assert "sg:steel ?= {\n\t\t\tadd = state_goods_production" in v and "multiply = 50\n}" in v
    assert SUBSIDY_SHARE > LEVY_SHARE, "Restrain must not pay more than Encourage costs"
    assert f"spec_lever_subsidy_steel = {{\n\tvalue = spec_lever_output_steel\n\tmultiply = {SUBSIDY_SHARE:g}\n\tround = yes\n}}" in v
    assert f"spec_lever_levy_steel = {{\n\tvalue = spec_lever_output_steel\n\tmultiply = {LEVY_SHARE:g}\n\tround = yes\n}}" in v
    assert v.index("spec_lever_output_wine = ") < v.index("spec_lever_subsidy_wine = ") < v.index("spec_lever_spend = ")
    assert "add = spec_lever_levy_wine" in v.split("spec_lever_levy = ")[1].split("spec_lever_spend")[0]
    assert "add = spec_lever_subsidy_wine" in v.split("spec_lever_spend = ")[1] and "spec_lever_money" not in v + loc()
    assert f"{LEVY_SHARE:.0%}" in loc() and f"{SUBSIDY_SHARE:.0%}" in loc()
    # approval is the interest groups' (ig_stances.py), not the levers' own modifiers
    assert "approval" not in m and "country_authority_add = -1\n" in m
    assert "spec_lever_encourage_steel = {" in m and "building_steel_mill_throughput_add = -0.1" in m and "spec_lever_restrain_fruit" not in m
    assert "country_expenses_add = 1\n" in m and "country_tax_income_add = 1\n" in m
    assert "interest_rate" not in m and "investment_pool" not in m
    e = out["common/scripted_effects/spec_lever_effects.txt"]
    assert "value = spec_lever_spend }" in e and "add_modifier = { name = spec_lever_restrain_grain }" in e
    assert "authority >= spec_lever_cost_$G$" in out["common/scripted_triggers/spec_lever_triggers.txt"]
    ai = ai_block(["grain", "steel"], 3, 2, 0.5)
    assert ai.count("authority >= { value = spec_lever_cost_steel multiply = 2 }") == 4 and "spec_update_levers" not in ai
    assert ai.count(f"net_total_income > {{ value = spec_lever_subsidy_steel multiply = {AI_FUNDS} }}") == 2
    # the tab's figures: refreshed on every update, the GUI reads them instead of running the scripted GUIs' triggers
    assert e.index("spec_lever_ui = {") < e.index("spec_update_levers = {") and "\t\tspec_lever_ui = { G = wine }\n" in e
    assert "spec_lever_free = { KIND = restrain OTHER = encourage G = $G$ }" in e and "set_variable = { name = spec_ui_co_$G$ value = -10 }" in e
    s, gui = out["common/scripted_guis/spec_lever_sguis.txt"], strip()
    assert s.count("limit = { spec_can_lever = { KIND = ") == 2, "the toggle must check again: the GUI's state can lag"
    assert "IsValid(" not in gui and "spec_ui_r_" in gui and "spec_ui_e_" in gui and gui.count(".Execute(") == 4 + bool(ISSUE_ON)  # each button and its selected icon; the issue's is a passive marker
    assert "local_var:spec_lever_n > 0" in e and e.count("value = spec_lever_levy }") == 1 and "limit = { spec_lever_levy > 0 }" not in e
    if ISSUE_ON:  # an issue and a lever never share a good, for the player and the AI; the cooldown starts on floating
        t = out["common/scripted_triggers/spec_lever_triggers.txt"]
        assert "text = spec_lever_no_issue_tt" in t.split("spec_lever_free = {")[1].split("spec_lever_fits_restrain")[0]
        assert "NOT = { has_variable = spec_restrain_$G$ }" in t.split("spec_issue_free = {")[1]
        assert f"name = spec_issue_cool value = {ISSUE_MONTHS + COOL_MONTHS}" in e.split("spec_issue_float = {")[1]
        clock = e.split("spec_issue_clock = {")[1]
        assert "days =" not in e.split("spec_issue_float = {")[1].split("spec_issue_clock")[0] and "remove_variable = spec_issue_wine" in clock
        assert "spec_issue_clock = yes" in MONTHLY
        assert "NOT = { has_variable = spec_issue_steel }" in ai and "NOT = { has_variable = spec_restrain_steel }" in issue_ai(["steel"])
        assert "spec_issue_no_lever_tt:" in loc() and "spec_lever_no_issue_tt:" in loc() and "Financial Centres" not in loc()
        assert "spec_update_levers = yes" in s.split("spec_sgui_issue = {")[1]
    assert "spec_ui_r_wine" in state_vars(["wine"])
    assert "var:spec_peak_steel < 2" in ai and "spec_hype_raw_steel >= 0.5" in ai and "spec_hype_raw_steel < 3" in ai
    w, m = ai.index(f"var:spec_word_steel = {CALM_WORD}"), ai.index("spec_lever_subsidy_steel")
    assert w < m, "the word test must come before the every_scope_state money check"
    assert "has_variable = spec_glut_$G$" in out["common/scripted_triggers/spec_lever_triggers.txt"]
    assert "net_total_income < 0" in ai
    print("levers ok")
