"""Leverage: the risk and the reward of riding a boom, both measured by outstanding credit.

Leverage is credit owed in months of investment pool income (spec_lev). It only climbs while confidence stays high
for years, because credit runs off at CREDIT_RUNOFF a month. Income here is the better of this month's and a running
average of about a year (spec_lev_income): one month's income can fall 96% and half return within the year, and on one
month alone most severe crunches hit countries with safe debts (tests lev4 to lev7), not ones that rode too hot.
Reward: buildings run LEV_REWARD better per month of leverage, up to LEV_REWARD_MAX months. A cash loan alone can't
pay: most large countries' pools hold more than they can spend, and whatever is lent is repaid.
Risk: past LEV_SAFE months, stress climbs to 1 at LEV_RUIN. Stress lifts the confidence a panic starts at by up to
LEV_PANIC_SPAN, so a boom's ordinary fall sets one off, and a panic with stress leaves a credit crunch of stress
x LEV_CRUNCH_MAX points (8 months: about 22): each is LEV_CRUNCH_THROUGHPUT of throughput and LEV_CRUNCH_INVEST of investment, and they
fade at LEV_CRUNCH_FADE a month, so the worst crunch lasts under six years and a small one within two. Banks lend nothing until
it ends, a bank rescue does not clear it, and the panic takes half of what is owed, by clawback or by default.
A country that loses LEV_LAND_LOST or more of its people in a month has lost land, to a peace deal or a split: nothing
else moves population that fast. It keeps its debt, and real leverage still drives panics, lending and the AI's stance.
But the loans it had then (spec_lev_old) are measured against the income it had then (spec_lev_ref) for the crunch and
the reward, or it takes the worst crunch for land it lost, not for risk it took, and a bigger bonus for being poorer.
The crunch's relief fades to nothing over LEV_RELIEF_MONTHS. New loans get none, and the old balance only shrinks.

LEV_ON = 0 builds the system without any of this, for comparing against it."""
import cycle
import tuning

ON = tuning.get("LEV_ON", 1)
SAFE, RUIN = tuning.get("LEV_SAFE", 3), tuning.get("LEV_RUIN", 12)
DANGER = 8  # the Leverage row turns Dangerous here: a crash from about 6.4 months is Severe, 15 points or more (22 at 8)
PANIC_SPAN = tuning.get("LEV_PANIC_SPAN", 40)
REWARD, REWARD_MAX = tuning.get("LEV_REWARD", 0.02), tuning.get("LEV_REWARD_MAX", 12)
# how fast a crash lands: Bad Debts points that bite each month, and months of bonus lost each month. All at once, the USA lost a quarter
# of its GDP within two months in the full test game, which read as a bug. 40 and 12 bring that back
CRUNCH_RAMP, BONUS_FADE = tuning.get("LEV_CRUNCH_RAMP", 3), tuning.get("LEV_BONUS_FADE", 1)
BITE = f"""change_variable = {{ name = spec_crunch_bite add = {CRUNCH_RAMP} }}
if = {{
	limit = {{ var:spec_crunch_bite > var:spec_crunch }}
	set_variable = {{ name = spec_crunch_bite value = var:spec_crunch }}
}}
add_modifier = {{
	name = spec_credit_crunch
	multiplier = var:spec_crunch_bite
}}
"""
BONUS_END = "" if BONUS_FADE < REWARD_MAX else ("\t# the boom's bonus ends with the boom, not at the next month's update\n\tif = {\n\t\tlimit = { has_variable = spec_lev_held }\n"
                                                "\t\tremove_modifier = spec_lev_boom\n\t\tremove_variable = spec_lev_held\n\t}\n")
# at 1% a point and 0.25 a month the worst Bad Debts cut a country's output by about 37% for about 13 years, deeper and longer
# than the Great Depression; 0.4% and 0.6 leave the worst at -16% clearing in about five years, a mild one within two
CRUNCH_MAX, CRUNCH_FADE = tuning.get("LEV_CRUNCH_MAX", 40), tuning.get("LEV_CRUNCH_FADE", 0.6)
CRUNCH_THROUGHPUT = tuning.get("LEV_CRUNCH_THROUGHPUT", 0.004)  # throughput lost per point of Bad Debts
CRUNCH_INVEST = tuning.get("LEV_CRUNCH_INVEST", 0.0075)  # investment lost per point: the worst Bad Debts (40) -30%, was 0.02 (-80%)
LAND_LOST, RELIEF_MONTHS = tuning.get("LEV_LAND_LOST", 0.1), tuning.get("LEV_RELIEF_MONTHS", 60)
# what a new month counts for in the running average of income: 2/13 is the usual figure for a span of 12 months
INCOME_SMOOTH = tuning.get("LEV_INCOME_SMOOTH", 0.15)
# income counts as at least this share of GDP a month. Only countries under about 3k GDP ever sit below it: with next to no
# pool income their leverage froze at 18 months or more while the debt ran off, and every panic took the worst Bad Debts
INCOME_FLOOR = tuning.get("LEV_INCOME_FLOOR", 0.01)
# months of leverage at which the AI turns Tight, by temperament; it stays Tight until half that. A limit below this means only
# falling income can set it off
AI_LIMIT = tuning.get("AI_LEV_LIMIT", {"-1": 5, "0": 8, "1": 9.5})  # Cautious was 3: a third of the AI never passed the safe line (tune12); Bold was 12, the ruin line
# percent chance, by temperament, that a Mania carries an AI away: it won't tighten for debt or confidence until the Mania passes or a
# panic comes. Rolled once per Mania. Bold's confidence rule alone would otherwise stop it long before the top of the credit limit
FEVER = {int(k): v for k, v in tuning.get("AI_FEVER", {"0": 10, "1": 50}).items()}
# the credit limit at each tech, never past LEV_RUIN. Central Banking comes first, then the others in either order, so their steps match. A crash
# needs about 6.4 months to be Severe (8.5 when Bad Debts grew with stress squared), and at the old 6 it left under 5 Bad Debts: one Severe crash in 56 years of the early game, against history's 1837, 1857 and 1873
LADDER = tuple(tuning.get("LEV_LADDER", (SAFE, 8, 10, 12)))
LADDER_STEPS = tuple(b - a for a, b in zip(LADDER, LADDER[1:]))
LADDER_TECHS = ("central_banking", "investment_banks", "international_exchange_standards")
STATE_VARS = ["spec_bailed", "spec_ai_fever", "spec_crunch", "spec_crunch_bite", "spec_lev_held", "spec_lev_last", "spec_lev_ready", "spec_c_drop", "spec_lev_pop", "spec_lev_avg", "spec_lev_old", "spec_lev_ref", "spec_lev_fade"]


def values(panic, near):
    if not ON:
        return []
    limit = "".join(f"\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_temper\n\t\t\tvar:spec_temper = {t}\n\t\t}}\n\t\tvalue = {v}\n\t}}\n"
                    for t, v in AI_LIMIT.items() if t != "0")
    return [
        f"spec_lev_floor = {{\n\tvalue = gdp\n\tmultiply = {INCOME_FLOOR:g}\n}}",
        "spec_lev_income = {\n\tvalue = spec_pool_month\n\tif = {\n\t\tlimit = { has_variable = spec_lev_avg }\n\t\tmin = var:spec_lev_avg\n\t}\n\tmin = spec_lev_floor\n}",
        f"spec_lev_avg_next = {{\n\tvalue = spec_pool_month\n\tif = {{\n\t\tlimit = {{ has_variable = spec_lev_avg }}\n\t\tsubtract = var:spec_lev_avg\n"
        f"\t\tmultiply = {INCOME_SMOOTH}\n\t\tadd = var:spec_lev_avg\n\t}}\n}}",
        # no income to measure against keeps the last month's figure, so a broke country isn't suddenly safe
        "spec_lev = {\n\tvalue = 0\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_debt\n\t\t\tspec_lev_income > 1\n\t\t}\n\t\tvalue = var:spec_debt\n"
        "\t\tdivide = spec_lev_income\n\t\tmin = 0\n\t}\n\telse_if = {\n\t\tlimit = {\n\t\t\thas_variable = spec_debt\n\t\t\tvar:spec_debt > 0\n"
        "\t\t\thas_variable = spec_lev_last\n\t\t}\n\t\tvalue = var:spec_lev_last\n\t}\n}",
        "spec_pop_kept = {\n\tvalue = 1\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_lev_pop\n\t\t\tvar:spec_lev_pop > 0\n\t\t}\n"
        "\t\tvalue = total_population\n\t\tdivide = var:spec_lev_pop\n\t\tmax = 1\n\t}\n}",
        # leverage with the loans from before a land loss measured against the income from before it
        "spec_lev_adj = {\n\tvalue = spec_lev\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_lev_old\n\t\t\tspec_lev_income > 1\n\t\t}\n"
        "\t\tvalue = var:spec_debt\n\t\tsubtract = var:spec_lev_old\n\t\tdivide = spec_lev_income\n"
        "\t\tadd = {\n\t\t\tvalue = var:spec_lev_old\n\t\t\tdivide = var:spec_lev_ref\n\t\t}\n\t\tmax = spec_lev\n\t\tmin = 0\n\t}\n}",
        # what a crunch is sized from: that figure at first, real leverage by the end of the relief
        "spec_lev_bad = {\n\tvalue = spec_lev\n\tif = {\n\t\tlimit = { has_variable = spec_lev_fade }\n\t\tvalue = spec_lev_adj\n\t\tsubtract = spec_lev\n"
        f"\t\tmultiply = var:spec_lev_fade\n\t\tdivide = {RELIEF_MONTHS}\n\t\tadd = spec_lev\n\t}}\n}}",
        f"spec_lev_stress = {{\n\tvalue = spec_lev\n\tsubtract = {SAFE}\n\tdivide = {RUIN - SAFE}\n\tmin = 0\n\tmax = 1\n}}",
        f"spec_panic_at = {{\n\tvalue = spec_lev_stress\n\tmultiply = {PANIC_SPAN}\n\tadd = {panic}\n\tsubtract = spec_shallow_panic\n}}",
        f"spec_near_at = {{\n\tvalue = spec_panic_at\n\tadd = {near - panic}\n}}",
        # whole months, so the modifier changes rarely; nothing during a panic or a crunch
        f"spec_lev_reward = {{\n\tvalue = spec_lev_adj\n\tmax = {REWARD_MAX}\n\tfloor = yes\n\tif = {{\n\t\tlimit = {{\n\t\t\tOR = {{\n"
        "\t\t\t\thas_variable = spec_panic\n\t\t\t\thas_variable = spec_crunch\n\t\t\t}\n\t\t}\n\t\tvalue = 0\n\t}\n}",
        f"spec_lev_bonus_min = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_lev_held }}\n\t\tvalue = var:spec_lev_held\n\t\tsubtract = {BONUS_FADE}\n\t}}\n}}",
        "spec_crunch_bite_sv = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_crunch_bite }\n\t\tvalue = var:spec_crunch_bite\n\t}\n}",
        f"spec_ai_lev_limit = {{\n\tvalue = {AI_LIMIT['0']}\n{limit}}}",
        "spec_ai_lev_back = {\n\tvalue = spec_ai_lev_limit\n\tmultiply = 0.5\n}",
        f"spec_lev_boom_pct = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_lev_held }}\n\t\tvalue = var:spec_lev_held\n\t\tmultiply = {REWARD * 100:g}\n\t}}\n}}",
        f"spec_crunch_invest_pct = {{\n\tvalue = spec_crunch_bite_sv\n\tmultiply = {CRUNCH_INVEST * 100:g}\n}}",
        "spec_crunch_left = {\n\tvalue = spec_crunch_sv\n\tsubtract = spec_crunch_bite_sv\n}",
        "spec_crunch_sv = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_crunch }\n\t\tvalue = var:spec_crunch\n\t}\n}",
        "spec_lev_fade_sv = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_lev_fade }\n\t\tvalue = var:spec_lev_fade\n\t}\n}",
        f"spec_crunch_stress = {{\n\tvalue = spec_lev_bad\n\tsubtract = {SAFE}\n\tdivide = {RUIN - SAFE}\n\tmin = 0\n\tmax = 1\n}}",
        # what a panic would leave today, for the panic and the tab's warning: a new panic never eases bad debts already there
        f"spec_crunch_if = {{\n\tvalue = spec_crunch_stress\n\tmultiply = {CRUNCH_MAX}\n\tmultiply = spec_nx_bad\n\tmin = spec_crunch_sv\n}}",
        f"spec_crunch_months = {{\n\tvalue = spec_crunch_sv\n\tdivide = {CRUNCH_FADE}\n\tceiling = yes\n}}",
        # throughput lost in percent, for the texts: now, once fully bitten in, and if a panic began now
        *(f"{name} = {{\n\tvalue = {src}\n\tmultiply = {CRUNCH_THROUGHPUT * 100:g}\n}}" for name, src in
          (("spec_crunch_tp_pct", "spec_crunch_bite_sv"), ("spec_crunch_tp_full_pct", "spec_crunch_sv"), ("spec_crunch_tp_if_pct", "spec_crunch_if"))),
    ]


def limit(extra=""):
    """New credit stops at LEV_SAFE months until Central Banking, which is also what unlocks Tight, then rises a step with
    each finance tech, never past LEV_RUIN. Falling income can still carry a country past its limit: that is the risk of owing money."""
    steps = "".join(f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n\t\tadd = {n}\n\t}}\n" for t, n in zip(LADDER_TECHS, LADDER_STEPS))
    return f"spec_credit_limit = {{\n\tvalue = {SAFE}\n{steps}{extra}\tmax = {RUIN}\n}}"


def cap(months):
    return "\tmultiply = spec_credit_limit\n" if ON else f"\tmultiply = {months}\n"


def modifiers(icon_good, icon_bad):
    if not ON:
        return ""
    invest = "".join(f"\tstate_{c}_investment_pool_efficiency_mult = {-CRUNCH_INVEST:g}\n" for c in ("capitalists", "aristocrats", "shopkeepers"))
    return (f"# applied with the months of leverage as its multiplier\nspec_lev_boom = {{\n\ticon = {icon_good}\n\tbuilding_throughput_add = {REWARD:g}\n}}\n\n"
            f"# applied with the crunch's points as its multiplier\nspec_credit_crunch = {{\n\ticon = {icon_bad}\n\tbuilding_throughput_add = {-CRUNCH_THROUGHPUT:g}\n{invest}}}\n\n")


# after the month's credit, in the country's monthly pulse
MONTHLY = "" if not ON else f"""			# land lost: the average income is the income these loans were taken on. A repeat loss during the relief adds nothing
			if = {{
				limit = {{ has_variable = spec_lev_fade }}
				change_variable = {{ name = spec_lev_fade add = -1 }}
				if = {{
					limit = {{ var:spec_lev_fade <= 0 }}
					remove_variable = spec_lev_fade
				}}
			}}
			if = {{
				limit = {{
					NOT = {{ has_variable = spec_lev_fade }}
					var:spec_debt > 0
					has_variable = spec_lev_avg
					var:spec_lev_avg > 1
					spec_pop_kept <= {1 - LAND_LOST:g}
				}}
				set_variable = {{ name = spec_lev_old value = var:spec_debt }}
				set_variable = {{ name = spec_lev_ref value = var:spec_lev_avg }}
				set_variable = {{ name = spec_lev_fade value = {RELIEF_MONTHS} }}
			}}
			if = {{
				limit = {{ has_variable = spec_lev_old }}
				if = {{
					limit = {{ var:spec_lev_old > var:spec_debt }}
					set_variable = {{ name = spec_lev_old value = var:spec_debt }}
				}}
				# the reward's reference outlasts the relief, until the income is back or the old loans are gone
				if = {{
					limit = {{
						NOT = {{ has_variable = spec_lev_fade }}
						OR = {{
							var:spec_lev_old < 1
							spec_pool_month >= var:spec_lev_ref
						}}
					}}
					remove_variable = spec_lev_old
					remove_variable = spec_lev_ref
				}}
			}}
			set_variable = {{ name = spec_lev_pop value = total_population }}
			# frozen through a panic and Bad Debts, so leverage can only fall in a crash and one crash sets off no second panic
			if = {{
				limit = {{
					NOT = {{ has_variable = spec_panic }}
					NOT = {{ has_variable = spec_crunch }}
				}}
				set_variable = {{ name = spec_lev_avg value = spec_lev_avg_next }}
			}}
			# once, for a game from before leverage: old debt past the safe line is written down, not punished
			if = {{
				limit = {{
					NOT = {{ has_variable = spec_lev_ready }}
					spec_pool_month > 1
				}}
				set_variable = spec_lev_ready
				if = {{
					limit = {{ spec_lev > {SAFE} }}
					set_variable = {{ name = spec_debt value = {{ value = spec_pool_month multiply = {SAFE} }} }}
				}}
			}}
			if = {{
				limit = {{ spec_lev_income > 1 }}
				# the toast, the month Leverage first passes the safe line
				if = {{
					limit = {{
						is_player = yes
						has_variable = spec_lev_last
						var:spec_lev_last <= {SAFE}
						spec_lev > {SAFE}
					}}
					post_notification = spec_lev_unsafe
				}}
				set_variable = {{ name = spec_lev_last value = spec_lev }}
			}}
			if = {{
				limit = {{ has_variable = spec_crunch }}
				remove_modifier = spec_credit_crunch
				change_variable = {{ name = spec_crunch add = -{CRUNCH_FADE} }}
				if = {{
					limit = {{ var:spec_crunch <= 0 }}
					remove_variable = spec_crunch
					remove_variable = spec_crunch_bite
					remove_variable = spec_bailed
				}}
				else = {{
					# Bad Debts from a save without the build-up bite in full
					if = {{
						limit = {{ NOT = {{ has_variable = spec_crunch_bite }} }}
						set_variable = {{ name = spec_crunch_bite value = var:spec_crunch }}
					}}
					{BITE}
				}}
			}}
			set_local_variable = {{ name = spec_lev_now value = {{ value = spec_lev_reward min = spec_lev_bonus_min }} }}
			# no new loans this month: falling income alone can't raise the bonus
			if = {{
				limit = {{ local_var:spec_lent <= 0 }}
				if = {{
					limit = {{
						has_variable = spec_lev_held
						local_var:spec_lev_now > var:spec_lev_held
					}}
					set_local_variable = {{ name = spec_lev_now value = var:spec_lev_held }}
				}}
				else_if = {{
					limit = {{ NOT = {{ has_variable = spec_lev_held }} }}
					set_local_variable = {{ name = spec_lev_now value = 0 }}
				}}
			}}
			if = {{
				limit = {{
					OR = {{
						has_variable = spec_lev_held
						local_var:spec_lev_now > 0
					}}
				}}
				if = {{
					limit = {{ has_variable = spec_lev_held }}
					if = {{
						limit = {{ NOT = {{ var:spec_lev_held = local_var:spec_lev_now }} }}
						remove_modifier = spec_lev_boom
						remove_variable = spec_lev_held
					}}
				}}
				if = {{
					limit = {{
						NOT = {{ has_variable = spec_lev_held }}
						local_var:spec_lev_now > 0
					}}
					set_variable = {{ name = spec_lev_held value = local_var:spec_lev_now }}
					add_modifier = {{
						name = spec_lev_boom
						multiplier = var:spec_lev_held
					}}
				}}
			}}
"""

# the panic's limit in the monthly pulse
def panic_limit(panic):
    return "spec_panic_at" if ON else f"{panic}"


def near_limit(near):
    return "spec_near_at" if ON else f"{near}"


NO_CREDIT = "" if not ON else "\t\t\t\t\tNOT = { has_variable = spec_crunch }\n\t\t\t\t\tvar:spec_conf >= spec_panic_at\n"


# in spec_start_panic, before the debt is touched
def on_panic(panic):
    return "" if not ON else f"""	# a panic that starts high up still falls to the bottom, and the tab shows the fall. Just under the line: on it is the Wary band
	if = {{
		limit = {{ var:spec_conf >= {panic} }}
		set_variable = {{ name = spec_c_drop value = {{ value = {panic - 0.1} subtract = var:spec_conf }} }}
		change_variable = {{ name = spec_c_total add = var:spec_c_drop }}
		set_variable = {{ name = spec_conf value = {panic - 0.1} }}
		if = {{
			limit = {{ has_variable = spec_hist1 }}
			set_variable = {{ name = spec_hist1 value = var:spec_conf }}
		}}
	}}
{BONUS_END}	if = {{
		limit = {{ spec_crunch_if > 0 }}
		if = {{
			limit = {{ has_variable = spec_crunch }}
			remove_modifier = spec_credit_crunch
		}}
		# the bailout's button comes back only for Bad Debts larger than the ones it bought up
		if = {{
			limit = {{ spec_crunch_if > spec_crunch_sv }}
			remove_variable = spec_bailed
		}}
		set_variable = {{ name = spec_crunch value = spec_crunch_if }}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_crunch_bite }} }}
			set_variable = {{ name = spec_crunch_bite value = 0 }}
		}}
		{BITE}
	}}
"""


def panic_event_loc(root, keys):
    """The panic event's paragraph on Bad Debts, and each text with it: the texts themselves stay as translated."""
    if not ON:
        return ""
    line = (f"The boom's loans have gone bad. Over the coming months [concept_spec_bad_debts] will cut [concept_throughput] by #N [{root}.ScriptValue('spec_crunch_tp_full_pct')|1]%#!, then fade, clearing in "
            f"#v [{root}.ScriptValue('spec_crunch_months')|0]#! months. Banks will lend nothing until they clear, and #v Lend to the Banks#! will not clear them.")
    return f' spec_markets.2.bad_debts: "{line}"\n' + "".join(f' {k}_bad: "${k}$\\n\\n$spec_markets.2.bad_debts$"\n' for k in keys)


# in spec_start_panic, after the clawback: what the pool couldn't pay back, the banks lose
def after_clawback(clawback):
    return "" if not ON else (f"\tset_variable = {{ name = spec_debt value = {{ value = var:spec_debt add = var:spec_clawed multiply = {1 - clawback:g} }} }}\n"
                              f"\tif = {{\n\t\tlimit = {{ has_variable = spec_lev_old }}\n\t\tchange_variable = {{ name = spec_lev_old multiply = {1 - clawback:g} }}\n\t}}\n")


# the monthly pulse, before the runoff comes off the debt: the old loans shrink in step with it
ON_REPAY = "" if not ON else ("\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\thas_variable = spec_lev_old\n\t\t\t\t\tvar:spec_debt > 0\n\t\t\t\t}\n"
                              "\t\t\t\tset_variable = { name = spec_lev_old value = { value = var:spec_debt subtract = local_var:spec_runoff divide = var:spec_debt multiply = var:spec_lev_old } }\n\t\t\t}\n")


# the AI's stance rule: leverage over its limit tightens, and it stays tight and won't loosen until half that
def ai_tight(test):
    return test if not ON else f"OR = {{\n\t\t\t\t\t\t\t{test}\n\t\t\t\t\t\t\tspec_lev > spec_ai_lev_limit\n\t\t\t\t\t\t}}\n\t\t\t\t\t\tNOT = {{ has_variable = spec_ai_fever }}"


# when a Mania fires, and each month in the AI's rules
FEVER_ROLL = "" if not ON else "\t\t\t\tif = {\n\t\t\t\t\tlimit = { is_player = no }\n\t\t\t\t\tspec_ai_temper = yes\n" + "".join(
    f"\t\t\t\t\tif = {{\n\t\t\t\t\t\tlimit = {{ var:spec_temper = {t} }}\n\t\t\t\t\t\trandom = {{\n\t\t\t\t\t\t\tchance = {v}\n\t\t\t\t\t\t\tset_variable = spec_ai_fever\n\t\t\t\t\t\t}}\n\t\t\t\t\t}}\n"
    for t, v in FEVER.items()) + "\t\t\t\t}\n"
FEVER_END = "" if not ON else ("\t\t\t\tif = {\n\t\t\t\t\tlimit = {\n\t\t\t\t\t\thas_variable = spec_ai_fever\n\t\t\t\t\t\tOR = {\n"
                               "\t\t\t\t\t\t\tNOT = { has_variable = spec_mania }\n\t\t\t\t\t\t\thas_variable = spec_panic\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n"
                               "\t\t\t\t\tremove_variable = spec_ai_fever\n\t\t\t\t}\n")


# the monthly pulse, each after its neighbour in generate.py
CLEAR_DROP = "" if not ON else "\t\t\tremove_variable = spec_c_drop\n"
AFTER_PANIC = "" if not ON else "\t\t\t\tif = {\n\t\t\t\t\tlimit = { has_variable = spec_c_drop }\n\t\t\t\t\tspec_pick_driver = yes\n\t\t\t\t}\n"
# no credit, for the tab's previews
BLOCKED = ("OR = { has_variable = spec_panic has_variable = spec_crunch has_modifier = spec_ld_crash AND = { has_variable = spec_conf var:spec_conf < spec_panic_at } }"
           if ON else "OR = { has_variable = spec_panic has_modifier = spec_ld_crash }")
# the panic event's texts: (key suffix, extra trigger), the first that fits wins
PANIC_DESCS = [("_bad", "has_variable = spec_crunch"), ("", "")] if ON else [("", "")]
# in spec_shut_down
SHUT_DOWN = "" if not ON else "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m in ("spec_lev_boom", "spec_credit_crunch"))
# the bank bailout: Bad Debts cut by BAILOUT_CUT at a treasury cost of BAILOUT_COST x points squared of GDP. Worst case, 40 points
# halved, about 5% of GDP: more than a rescue (2%), as the state takes over losses rather than lending through a panic. Squared, as
# small Bad Debts were dear for what they cut (10 points cost 1.25%, now 0.3%)
BAILOUT_CUT, BAILOUT_COST = 0.5, 0.00003
BAILOUT_VALUES = [] if not ON else [
    # in two steps: the engine reads no 3e-05, and too many decimals lose precision
    f"spec_bailout_share = {{\n\tvalue = spec_crunch_sv\n\tmultiply = spec_crunch_sv\n\tmultiply = {BAILOUT_COST * 100:g}\n\tdivide = 100\n}}",
    "spec_bailout_cost = {\n\tvalue = gdp\n\tmultiply = spec_bailout_share\n\tdivide = 1000\n\tround = yes\n\tmultiply = 1000\n\tmin = 1000\n}",
    f"spec_bailout_months = {{\n\tvalue = spec_crunch_sv\n\tmultiply = {1 - BAILOUT_CUT:g}\n\tdivide = {CRUNCH_FADE}\n\tceiling = yes\n}}",
]


def bailout_effect(igs):
    """The effect, its cost and the interest groups' anger shown as plain lines, the cut itself as one line."""
    return "" if not ON else f"""# the bank bailout, once per spell of Bad Debts, from the market tab
spec_bailout = {{
	custom_tooltip = spec_bailout_fx_tt
	custom_tooltip = {{
		text = spec_bailout_cost_tt
		add_treasury = {{ value = spec_bailout_cost multiply = -1 }}
	}}
{igs}	hidden_effect = {{
		# the button's tooltip previews this effect even with no Bad Debts: read nothing that is unset
		if = {{
			limit = {{ has_variable = spec_crunch has_variable = spec_crunch_bite }}
			remove_modifier = spec_credit_crunch
			set_variable = {{ name = spec_crunch value = {{ value = var:spec_crunch multiply = {1 - BAILOUT_CUT:g} }} }}
			if = {{
				limit = {{ var:spec_crunch_bite > var:spec_crunch }}
				set_variable = {{ name = spec_crunch_bite value = var:spec_crunch }}
			}}
			add_modifier = {{
				name = spec_credit_crunch
				multiplier = var:spec_crunch_bite
			}}
		}}
		set_variable = spec_bailed
{cycle.rescued(2)}	}}
}}

"""


BAILOUT_SGUI = "" if not ON else """spec_sgui_bailout = {
	scope = country
	is_valid = { spec_can_bailout = yes }
	effect = { spec_bailout = yes }
}
"""
BAILOUT_TRIGGER = "" if not ON else """spec_can_bailout = {
	custom_tooltip = {
		text = spec_bailout_debts_tt
		has_variable = spec_crunch
	}
	has_technology_researched = banking
	in_default = no
	custom_tooltip = {
		text = spec_bailed_tt
		NOT = { has_variable = spec_bailed }
	}
}
"""
ROOT = "ROOT.GetCountry.MakeScope"
LOC = "" if not ON else f""" spec_lev_boom: "Credit Boom"
 spec_bailout_fx_tt: "[concept_spec_bad_debts] are #P halved#!, clearing in #v [{ROOT}.ScriptValue('spec_bailout_months')|0]#! months instead of #v [{ROOT}.ScriptValue('spec_crunch_months')|0]#!"
 spec_bailout_cost_tt: "[concept_treasury]: #N -@money![{ROOT}.ScriptValue('spec_bailout_cost')|D]#!, about #v [{ROOT}.ScriptValue('spec_bailout_share')|%0]#! of [concept_gdp]"
 spec_bailout_debts_tt: "There are [concept_spec_bad_debts] to clear"
 spec_bailed_tt: "The state has not bought up bad loans since these [concept_spec_bad_debts] began"
 spec_lev_boom_desc: "Borrowed money keeps the works busy, adding #P {REWARD:+.0%}#! [concept_throughput] for each whole month of [concept_spec_leverage], up to #P {REWARD * REWARD_MAX:+.0%}#!"
 spec_credit_crunch: "Bad Debts"
 spec_credit_crunch_desc: "The banks are still counting their losses from the last boom. #N They lend nothing#! until this fades.\\n#v Lend to the Banks#! does not clear it\\n#v Buy Up Bad Loans#! halves it, once while it lasts"
"""
# the AI buys up bad loans too, from money it has; about one month in seven while it can
AI_BAILOUT = "" if not ON else """				if = {
					limit = {
						spec_can_bailout = yes
						scaled_debt < 0.6
						gold_reserves >= spec_bailout_cost
						NOT = { spec_nearly_broke = yes }
						}
					random = {
						chance = 15
						spec_bailout = yes
					}
				}
"""
AI_BACK = "" if not ON else "\t\t\t\t\t\tspec_lev < spec_ai_lev_back\n"
# the LOG line's own values, for generate.log_values: a log build only
LOG_VALUES = [] if not ON else ["spec_log_fever = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_ai_fever }\n\t\tvalue = 1\n\t}\n}",
                                "spec_log_pop = {\n\tvalue = total_population\n}"]
LOG = "" if not ON else " fever=[THIS.ScriptValue('spec_log_fever')] lev=[THIS.ScriptValue('spec_lev')] crunch=[THIS.ScriptValue('spec_crunch_sv')] bite=[THIS.ScriptValue('spec_crunch_bite_sv')] adj=[THIS.ScriptValue('spec_lev_adj')] fade=[THIS.ScriptValue('spec_lev_fade_sv')] pop=[THIS.ScriptValue('spec_log_pop')]"


if __name__ == "__main__":
    import generate
    got = {}
    generate.write = lambda rel, text: got.setdefault(rel, text)  # values() writes its file: keep it here instead
    generate.values()
    sv = got["common/script_values/spec_values.txt"]
    assert not __import__("re").search(r"\de-\d", sv), "the engine reads no scientific notation"
    for s in (MONTHLY, on_panic(30), limit(), BLOCKED, *values(30, 40)):
        assert s.count("{") == s.count("}"), s
    if ON:
        assert limit().rstrip().endswith(f"max = {RUIN}\n}}"), "the credit limit stops at the ruin line"
        crunch_if = next(v for v in values(30, 40) if v.startswith("spec_crunch_if"))
        assert crunch_if.count("spec_crunch_stress") == 1, "Bad Debts grow with stress, not stress squared"
        assert "spec_panic_at" in NO_CREDIT and "spec_ld_crash" in BLOCKED and "spec_panic_at" in BLOCKED
        # the income average holds through a panic or Bad Debts; no lending this month, no bigger bonus
        assert MONTHLY.index("NOT = {{ has_variable = spec_crunch }}".replace("{{", "{").replace("}}", "}")) < MONTHLY.index("spec_lev_avg value = spec_lev_avg_next")
        assert "local_var:spec_lent <= 0" in MONTHLY and "name = spec_lent value = var:spec_credit_given" in generate.monthly(False)
        # the bailout re-arms only for bigger Bad Debts, and costs points squared: 40 points 4.8% of GDP, 10 points 0.3%
        assert "limit = { spec_crunch_if > spec_crunch_sv }\n\t\t\tremove_variable = spec_bailed" in on_panic(30)
        assert abs(40 ** 2 * BAILOUT_COST - 0.048) < 1e-9 and abs(10 ** 2 * BAILOUT_COST - 0.003) < 1e-9
    # credit: confidence's share capped at CREDIT_FLOW_MAX, then the rate, then the ceiling and the room against leverage's income
    credit = sv[sv.index("spec_credit = {"):]
    credit = credit[:credit.index("\n}") + 2]
    order = [f"max = {generate.CREDIT_FLOW_MAX}", "multiply = spec_pool_month", "multiply = spec_credit_rate", "max = spec_credit_ceiling", "max = spec_credit_room"]
    assert [credit.index(o) for o in order] == sorted(credit.index(o) for o in order), credit
    assert ("value = spec_lev_income" if ON else "value = spec_pool_month") in sv[sv.index("spec_credit_room = {"):][:60]
    # the runoff comes off in full, the pool pays what it holds
    assert "subtract = local_var:spec_runoff" in generate.monthly(False) and "spec_credit_repay = {\n\tvalue = spec_credit_runoff\n\tmax = investment_pool" in sv
    print("leverage ok")
