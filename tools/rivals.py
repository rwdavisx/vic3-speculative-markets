"""Rival Exchanges (design_rivals.md): every vanilla rivalry, in either direction, between two countries that both have
an Exchange. Once a year the pair's higher Financial Centre score wins a small amount of trust from the other. Between
contests either side may act against the other: Bear Raid, Lure Their Capital, Press Campaign, and Shore Up in defence.
The AI acts both ways, and a player who is targeted gets an event.

centres.py calls this module: pass_() in its monthly ranking pass, block() and marker() in the World tab, loc() in its
localization. build(write) writes the rest. The old one-rival state (spec_rival, spec_rival_lock, spec_rival_last) is
removed on load and no vanilla rivalry is made from it."""
import tuning
from market_tab import W, fx, ind

STAKE = tuning.get("RIVAL_STAKE", 3)          # contest trust at an equal standing (out of CALM)
BITTER = tuning.get("EXCH_RIVAL_BITTER", 1.5)  # the loser's loss times this on poor relations or worse
RAID_GDP = tuning.get("RIVAL_RAID_GDP", 0.005)  # Bear Raid and Shore Up: share of our GDP from the treasury
RAID_HIT, RAID_MONTHS = tuning.get("RIVAL_RAID_HIT", 6), 6  # confidence lost over the months
RAID_FAIL, RAID_FAIL_MORE = 20, 60            # % failure, plus up to this much more as their score exceeds ours
LURE_DEBT, LURE_SHARE, LURE_MONTHS = 2, tuning.get("RIVAL_LURE_SHARE", 0.1), 12  # months of our pool income owed
PRESS_INFL, PRESS_TRUST, PRESS_EXPOSE, PRESS_REL, PRESS_MONTHS = 25, 6, 30, 20, 12
SHORE_MONTHS, SHORE_CD = 12, 2                 # months halved; years before the next
CD_DAYS = 365                                 # each action's cooldown, per target
AI_CHANCE, AI_TEMPER = tuning.get("RIVAL_AI_CHANCE", 25), 15  # % a year per rivalry; Bold +, Cautious -
CALM_GAIN = 2                                 # the event's Ignore
MANIA = tuning.get("MANIA", 80)
CALM = tuning.get("CENTRE_CALM", 120)
ACTIONS = ("raid", "lure", "press")           # spec_rv_hit codes 1, 2, 3
SLOTS = 3                                     # Press Campaigns running at once, one modifier each
OLD_VARS = ["spec_rival", "spec_rival_lock", "spec_rival_last"]
STATE_VARS = OLD_VARS + ["spec_c_rival", "spec_rv_raid", "spec_rv_raid_pm", "spec_rv_lure", "spec_rv_lurer", "spec_rv_lure_share",
                         "spec_rv_shored", "spec_rv_shore_cd", "spec_rv_hit", "spec_rv_hit_by", "spec_rv_hit_ok", "spec_rv_hit_recent",
                         "spec_rv_n_out", "spec_rv_n_in"]
# scripted GUIs with root = the player and scope:target = the row's country
CALL = "GetScriptedGui('spec_sgui_{}').{}(GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('target', Country.MakeScope).End)"
US, THEM = "GetPlayer.MakeScope", "Country.MakeScope"
pc = lambda x: f"{round(x * 100, 1):g}%"


def shown(key):
    return CALL.format(key, "IsShown")


# -- script -----------------------------------------------------------------------------------------------------------

def triggers():
    gold = "\tcustom_tooltip = {\n\t\ttext = spec_rv_gold_tt\n\t\tgold_reserves >= spec_rv_cost\n\t}\n"
    cd = lambda a: (f"\tcustom_tooltip = {{\n\t\ttext = spec_rv_cd_tt\n"
                    f"\t\tNOT = {{ is_target_in_variable_list = {{ name = spec_rv_cd_{a} target = scope:target }} }}\n\t}}\n")
    pair = "\tcustom_tooltip = {\n\t\ttext = spec_rv_pair_tt\n\t\tspec_rv_pair = yes\n\t}\n"
    free = " ".join(f"has_modifier = spec_rv_press_{n}" for n in range(1, SLOTS + 1))
    pay = {
        "raid": gold,
        "lure": ("\tcustom_tooltip = {\n\t\ttext = spec_rv_panic_tt\n\t\tNOT = { has_variable = spec_panic }\n\t}\n"
                 "\tcustom_tooltip = {\n\t\ttext = spec_rv_lured_tt\n\t\tscope:target = { NOT = { has_variable = spec_rv_lure } }\n\t}\n"),
        "press": (f"\tcustom_tooltip = {{\n\t\ttext = spec_rv_infl_tt\n\t\tinfluence >= {PRESS_INFL}\n\t}}\n"
                  f"\tcustom_tooltip = {{\n\t\ttext = spec_rv_slots_tt\n\t\tNOT = {{ AND = {{ {free} }} }}\n\t}}\n"),
    }
    exch = ("has_variable = spec_exch_stand has_variable = spec_centre_score has_variable = spec_centre_trust")
    out = f"""# rival Exchanges (rivals.py): a vanilla rivalry either way, both with an Exchange; scope:target = the other
spec_rv_pair = {{
	{exch}
	scope:target = {{ {exch} }}
	OR = {{
		any_rival_country = {{ this = scope:target }}
		any_rivaling_country = {{ this = scope:target }}
	}}
}}

spec_can_rv_shore = {{
	custom_tooltip = {{
		text = spec_rv_exch_tt
		has_variable = spec_exch_stand
	}}
	custom_tooltip = {{
		text = spec_rv_shore_cd_tt
		NOT = {{ has_variable = spec_rv_shore_cd }}
	}}
{gold}}}
"""
    for a in ACTIONS:
        out += f"\nspec_rv_pay_{a} = {{\n{pay[a]}}}\n\nspec_can_rv_{a} = {{\n{pair}{cd(a)}\tspec_rv_pay_{a} = yes\n}}\n"
    return out


def values():
    them = "scope:target.var:spec_centre_score"
    return f"""spec_rv_cost = {{
	value = gdp
	multiply = {RAID_GDP:g}
	min = 0
}}

spec_rv_cost_neg = {{
	value = spec_rv_cost
	multiply = -1
}}

# Bear Raid: the % chance it fails, more as their score exceeds ours (actor scope)
spec_rv_raid_fail = {{
	value = {RAID_FAIL}
	if = {{
		limit = {{ {them} > var:spec_centre_score }}
		add = {{
			value = {them}
			subtract = var:spec_centre_score
			divide = {them}
			multiply = {RAID_FAIL_MORE}
		}}
	}}
	max = {RAID_FAIL + RAID_FAIL_MORE}
}}

spec_rv_lure_debt = {{
	value = spec_pool_month
	multiply = {LURE_DEBT}
}}

# the yearly contest's stake, in the winner's scope against scope:spec_rv_l: an upset pays more, the expected less
spec_rv_stake = {{
	value = {STAKE}
	if = {{
		limit = {{ var:spec_exch_stand > scope:spec_rv_l.var:spec_exch_stand }}
		divide = {{
			value = var:spec_exch_stand
			subtract = scope:spec_rv_l.var:spec_exch_stand
			add = 1
		}}
	}}
	else_if = {{
		limit = {{ var:spec_exch_stand < scope:spec_rv_l.var:spec_exch_stand }}
		multiply = {{
			value = scope:spec_rv_l.var:spec_exch_stand
			subtract = var:spec_exch_stand
			add = 1
		}}
	}}
}}

spec_rv_ai_chance = {{
	value = {AI_CHANCE}
	if = {{
		limit = {{ has_variable = spec_temper }}
		add = {{
			value = var:spec_temper
			multiply = {AI_TEMPER}
		}}
	}}
	if = {{
		limit = {{ has_global_variable = spec_rv_ai_force }}
		value = 100
	}}
}}
"""


def _gain(by, t):
    return f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust add = {by} max = {CALM} }} }}\n"


def _lose(by, t):
    """As centres._lose: times spec_exch_loss, never below 0."""
    return (f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
            f"subtract = {{ value = {by} multiply = spec_exch_loss }} min = 0 }} }}\n")


def _half(var, t):
    return f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_rv_shored }}\n{t}\tchange_local_variable = {{ name = {var} multiply = 0.5 }}\n{t}}}\n"


def effects():
    slots = "".join(f"\t{'if' if n == 1 else 'else_if'} = {{\n\t\tlimit = {{ NOT = {{ has_modifier = spec_rv_press_{n} }} }}\n"
                    f"\t\tadd_modifier = {{ name = spec_rv_press_{n} months = {PRESS_MONTHS} }}\n\t}}\n" for n in range(1, SLOTS + 1))
    # the yearly contest: once per pair, whichever named the other. Results are lists on both sides, emptied first
    lists = ("spec_rv_won", "spec_rv_lost", "spec_rv_tied")
    done = " ".join(f"is_target_in_variable_list = {{ name = {l} target = scope:spec_rival_me }}" for l in lists)
    note = lambda key: f"\tif = {{\n\t\tlimit = {{ is_player = yes }}\n\t\tset_variable = spec_rival_note_{key}\n\t}}\n"
    flush = "".join(f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = spec_rival_note_{k} }}\n\t\t\tpost_notification = spec_rival_{k}\n"
                    f"\t\t\tremove_variable = spec_rival_note_{k}\n\t\t}}\n" for k in ("won", "lost"))
    exch = "has_variable = spec_exch_stand has_variable = spec_centre_score has_variable = spec_centre_trust"
    body = f"""scope:spec_rv_w = {{
	set_local_variable = {{ name = spec_rv_stake value = spec_rv_stake }}
{_gain("local_var:spec_rv_stake", chr(9))}	add_to_variable_list = {{ name = spec_rv_won target = scope:spec_rv_l }}
{note("won")}}}
scope:spec_rv_l = {{
{_lose("local_var:spec_rv_stake", chr(9))}	if = {{
		limit = {{ "relations(scope:spec_rv_w)" <= relations_threshold:poor }}
{_lose(f"{{ value = local_var:spec_rv_stake multiply = {BITTER - 1:g} }}", chr(9) * 2)}	}}
	add_to_variable_list = {{ name = spec_rv_lost target = scope:spec_rv_w }}
{note("lost")}}}
"""
    save = lambda who, name: f"\t\t\t\tsave_scope_as = {name}\n" if who == "this" else f"\t\t\t\t{who} = {{ save_scope_as = {name} }}\n"
    settle = lambda w, l: save(w, "spec_rv_w") + save(l, "spec_rv_l") + ind(body, 4)
    return f"""# rival Exchanges (rivals.py)
spec_rival_contest = {{
	every_country = {{
		limit = {{ has_variable = spec_exch_stand }}
		clear_variable_list = spec_rv_won
		clear_variable_list = spec_rv_lost
		clear_variable_list = spec_rv_tied
	}}
	every_country = {{
		limit = {{ {exch} }}
		save_scope_as = spec_rival_me
		every_rival_country = {{
			limit = {{
				{exch}
				NOT = {{ OR = {{ {done} }} }}
			}}
			if = {{
				limit = {{ scope:spec_rival_me.var:spec_centre_score > var:spec_centre_score }}
{settle("scope:spec_rival_me", "this")}			}}
			else_if = {{
				limit = {{ scope:spec_rival_me.var:spec_centre_score < var:spec_centre_score }}
{settle("this", "scope:spec_rival_me")}			}}
			else = {{
				add_to_variable_list = {{ name = spec_rv_tied target = scope:spec_rival_me }}
				save_temporary_scope_as = spec_rv_x
				scope:spec_rival_me = {{ add_to_variable_list = {{ name = spec_rv_tied target = scope:spec_rv_x }} }}
			}}
		}}
	}}
	every_country = {{
		limit = {{ OR = {{ has_variable = spec_rival_note_won has_variable = spec_rival_note_lost }} }}
{flush}	}}
}}
# end spec_rival_contest

# a player's rows: every vanilla rivalry either way, with or without an Exchange
spec_rv_list = {{
	clear_variable_list = spec_rv_pairs
	set_variable = {{ name = spec_rv_n_out value = 0 }}
	set_variable = {{ name = spec_rv_n_in value = 0 }}
	save_scope_as = spec_rv_me
	every_rival_country = {{
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_me = {{
			add_to_variable_list = {{ name = spec_rv_pairs target = scope:spec_rv_x }}
			change_variable = {{ name = spec_rv_n_out add = 1 }}
		}}
	}}
	every_rivaling_country = {{
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_me = {{
			change_variable = {{ name = spec_rv_n_in add = 1 }}
			if = {{
				limit = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_pairs target = scope:spec_rv_x }} }} }}
				add_to_variable_list = {{ name = spec_rv_pairs target = scope:spec_rv_x }}
			}}
		}}
	}}
}}

# the last action against scope:target, for both rows and the targeted player's event (spec_rv_ok: 1 worked, 0 failed, -1 exposed)
spec_rv_log = {{
	scope:target = {{
		set_variable = {{ name = spec_rv_hit value = $CODE$ }}
		set_variable = {{ name = spec_rv_hit_by value = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_hit_ok value = local_var:spec_rv_ok }}
		set_variable = {{ name = spec_rv_hit_recent days = 365 }}
		if = {{
			limit = {{ is_player = yes }}
			trigger_event = {{ id = spec_rival.1 popup = yes }}
		}}
	}}
}}

# Bear Raid's confidence hit, in the scope that takes it
spec_rv_raided = {{
	set_local_variable = {{ name = spec_rv_pm value = {RAID_HIT / RAID_MONTHS:g} }}
	if = {{
		limit = {{ has_variable = spec_conf var:spec_conf >= {MANIA} }}
		change_local_variable = {{ name = spec_rv_pm multiply = 2 }}
	}}
{_half("spec_rv_pm", chr(9))}	if = {{
		limit = {{ NOT = {{ has_variable = spec_rv_raid_pm }} }}
		set_variable = {{ name = spec_rv_raid_pm value = 0 }}
	}}
	change_variable = {{ name = spec_rv_raid_pm add = local_var:spec_rv_pm }}
	set_variable = {{ name = spec_rv_raid value = {RAID_MONTHS} }}
}}

spec_rv_raid = {{
	custom_tooltip = spec_rv_raid_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
	add_treasury = spec_rv_cost_neg
	add_to_variable_list = {{ name = spec_rv_cd_raid target = scope:target days = {CD_DAYS} }}
	set_local_variable = {{ name = spec_rv_roll value = {{ fixed_range = {{ min = 0 max = 100 }} }} }}
	if = {{
		limit = {{ local_var:spec_rv_roll >= spec_rv_raid_fail }}
		set_local_variable = {{ name = spec_rv_ok value = 1 }}
		scope:target = {{ spec_rv_raided = yes }}
	}}
	else = {{
		set_local_variable = {{ name = spec_rv_ok value = 0 }}
		spec_rv_raided = yes
	}}
	spec_rv_log = {{ CODE = 1 }}
	}}
}}

spec_rv_lure = {{
	custom_tooltip = spec_rv_lure_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
	if = {{
		limit = {{ NOT = {{ has_variable = spec_debt }} }}
		set_variable = {{ name = spec_debt value = 0 }}
	}}
	change_variable = {{ name = spec_debt add = spec_rv_lure_debt }}
	add_to_variable_list = {{ name = spec_rv_cd_lure target = scope:target days = {CD_DAYS} }}
	set_local_variable = {{ name = spec_rv_ok value = 1 }}
	scope:target = {{
		set_local_variable = {{ name = spec_rv_share value = {LURE_SHARE:g} }}
{_half("spec_rv_share", chr(9) * 2)}		set_variable = {{ name = spec_rv_lure value = {LURE_MONTHS} }}
		set_variable = {{ name = spec_rv_lurer value = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_lure_share value = local_var:spec_rv_share }}
	}}
	spec_rv_log = {{ CODE = 2 }}
	}}
}}

spec_rv_press = {{
	custom_tooltip = spec_rv_press_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
{slots}	add_to_variable_list = {{ name = spec_rv_cd_press target = scope:target days = {CD_DAYS} }}
	set_local_variable = {{ name = spec_rv_ok value = 1 }}
	scope:target = {{
		set_local_variable = {{ name = spec_rv_t value = {PRESS_TRUST} }}
{_half("spec_rv_t", chr(9) * 2)}{_lose("local_var:spec_rv_t", chr(9) * 2)}	}}
	random = {{
		chance = {PRESS_EXPOSE}
		set_local_variable = {{ name = spec_rv_ok value = -1 }}
		change_relations = {{ country = scope:target value = -{PRESS_REL} }}
{_lose(PRESS_TRUST, chr(9) * 2)}	}}
	spec_rv_log = {{ CODE = 3 }}
	}}
}}

spec_rv_shore = {{
	custom_tooltip = spec_rv_shore_fx
	hidden_effect = {{
	add_treasury = spec_rv_cost_neg
	set_variable = {{ name = spec_rv_shored value = {SHORE_MONTHS} }}
	set_variable = {{ name = spec_rv_shore_cd days = {SHORE_CD * 365} }}
	}}
}}

# the AI against scope:target, at most once a year per rivalry: Shore Up first after being hit, else any action it may
spec_rv_ai_act = {{
	random = {{
		chance = spec_rv_ai_chance
		if = {{
			limit = {{
				has_variable = spec_rv_hit_recent
				spec_can_rv_shore = yes
			}}
			spec_rv_shore = yes
		}}
		else_if = {{
			limit = {{ OR = {{ {" ".join(f"spec_can_rv_{a} = yes" for a in ACTIONS)} }} }}
			random_list = {{
{"".join(f"				1 = {{{chr(10)}					trigger = {{ spec_can_rv_{a} = yes }}{chr(10)}					spec_rv_{a} = yes{chr(10)}				}}{chr(10)}" for a in ACTIONS)}			}}
		}}
	}}
}}

spec_rv_ai = {{
	every_country = {{
		limit = {{
			is_player = no
			{exch}
		}}
		save_scope_as = spec_rv_ai_me
		every_rival_country = {{
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
		every_rivaling_country = {{
			limit = {{ NOT = {{ any_rivaling_country = {{ this = scope:spec_rv_ai_me }} }} }}
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
	}}
}}

"""


def pass_(t="\t"):
    """In centres' monthly ranking pass: old saves' one-rival state goes; players' rows are rebuilt; once a year the
    contest, then the AI's actions."""
    old = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = {n} }}\n{t}\t\tremove_variable = {n}\n{t}\t}}\n" for n in OLD_VARS)
    return f"""{t}# rival Exchanges (rivals.py): an old save's single rival is dropped, not made a vanilla rivalry
{t}every_country = {{
{t}	limit = {{ OR = {{ {" ".join(f"has_variable = {n}" for n in OLD_VARS)} }} }}
{old}{t}}}
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_rival_year }} }}
{t}	set_global_variable = {{ name = spec_rival_year days = 365 }}
{t}	if = {{
{t}		limit = {{ has_global_variable = spec_rival_started }}
{t}		spec_rival_contest = yes
{t}		spec_rv_ai = yes
{t}	}}
{t}	set_global_variable = spec_rival_started
{t}}}
{t}every_country = {{
{t}	limit = {{ is_player = yes }}
{t}	spec_rv_list = yes
{t}}}
"""


# in generate's spec_monthly, country scope, before the month's confidence is summed
MONTHLY = f"""			# rival actions running (rivals.py): a Bear Raid's monthly hit, a lure's pool money, Shore Up's months
			set_variable = {{ name = spec_c_rival value = 0 }}
			if = {{
				limit = {{ has_variable = spec_rv_raid }}
				set_variable = {{ name = spec_c_rival value = {{ value = var:spec_rv_raid_pm multiply = -1 }} }}
				change_variable = {{ name = spec_rv_raid add = -1 }}
				if = {{
					limit = {{ var:spec_rv_raid <= 0 }}
					remove_variable = spec_rv_raid
					remove_variable = spec_rv_raid_pm
				}}
			}}
			if = {{
				limit = {{ has_variable = spec_rv_lure }}
				if = {{
					limit = {{ exists = var:spec_rv_lurer var:spec_rv_lurer = {{ is_country_alive = yes }} }}
					set_local_variable = {{ name = spec_rv_amt value = {{ value = spec_pool_month multiply = var:spec_rv_lure_share }} }}
					var:spec_rv_lurer = {{ add_investment_pool = local_var:spec_rv_amt }}
					change_local_variable = {{ name = spec_rv_amt multiply = -1 }}
					add_investment_pool = local_var:spec_rv_amt
				}}
				change_variable = {{ name = spec_rv_lure add = -1 }}
				if = {{
					limit = {{ var:spec_rv_lure <= 0 }}
					remove_variable = spec_rv_lure
					remove_variable = spec_rv_lurer
					remove_variable = spec_rv_lure_share
				}}
			}}
			if = {{
				limit = {{ has_variable = spec_rv_shored }}
				change_variable = {{ name = spec_rv_shored add = -1 }}
				if = {{
					limit = {{ var:spec_rv_shored <= 0 }}
					remove_variable = spec_rv_shored
				}}
			}}
"""


def sguis():
    act = "".join(f"\nspec_sgui_rv_{a} = {{\n\tscope = country\n\tis_valid = {{ spec_can_rv_{a} = yes }}\n\teffect = {{ spec_rv_{a} = yes }}\n}}\n"
                  for a in ACTIONS + ("shore",))
    tests = {"pair": "spec_rv_pair = yes", "out": "any_rival_country = { this = scope:target }",
             "in": "any_rivaling_country = { this = scope:target }",
             **{k: f"is_target_in_variable_list = {{ name = spec_rv_{k} target = scope:target }}" for k in ("won", "lost", "tied")}}
    dbg = ("\nspec_sgui_rv_dbg_year = {\n\tscope = country\n\teffect = {\n\t\tspec_rival_contest = yes\n"
           "\t\tevery_country = { limit = { is_player = yes } spec_rv_list = yes }\n\t}\n}\n"
           "\nspec_sgui_rv_dbg_ai = {\n\tscope = country\n\teffect = {\n\t\tset_global_variable = spec_rv_ai_force\n"
           "\t\tspec_rv_ai = yes\n\t\tremove_global_variable = spec_rv_ai_force\n"
           "\t\tevery_country = { limit = { is_player = yes } spec_rv_list = yes }\n\t}\n}\n")
    return act + dbg + "".join(f"\nspec_sgui_rv_is_{k} = {{\n\tscope = country\n\tis_shown = {{ {t} }}\n}}\n" for k, t in tests.items())


def events():
    pick = lambda code, ok: f"var:spec_rv_hit ?= {code} var:spec_rv_hit_ok ?= {ok}"
    descs = [(1, 1), (1, 0), (2, 1), (3, 1), (3, -1)]
    desc = "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_rival.1.d{c}{'n' if o < 0 else o}\n"
                   f"\t\t\t\ttrigger = {{ {pick(c, o)} }}\n\t\t\t}}\n" for c, o in descs)
    back = " ".join(f"AND = {{ var:spec_rv_hit = {i} spec_rv_pay_{a} = yes }}" for i, a in enumerate(ACTIONS, 1))
    do = "".join(f"\t\t\tif = {{\n\t\t\t\tlimit = {{ var:spec_rv_hit = {i} }}\n\t\t\t\tspec_rv_{a} = yes\n\t\t\t}}\n"
                 for i, a in enumerate(ACTIONS, 1))
    return f"""namespace = spec_rival

# a rival has acted against us (rivals.py): answer in kind, shore up, or keep calm
spec_rival.1 = {{
	type = country_event
	placement = root
	title = spec_rival.1.t
	desc = {{
		first_valid = {{
{desc}		}}
	}}
	flavor = spec_rival.1.f
	duration = 3
{__import__("stories").pictures({"west": "europenorthamerica_capitalists_meeting", "mideast": "middleeast_upperclass_party"})}	icon = "gfx/interface/icons/event_icons/event_trade.dds"
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	immediate = {{
		var:spec_rv_hit_by = {{ save_scope_as = target }}
	}}

	option = {{
		name = spec_rival.1.a
		trigger = {{
			exists = scope:target
			spec_rv_pair = yes
			OR = {{ {back} }}
		}}
		custom_tooltip = spec_rival.1.a_tt
		hidden_effect = {{
{do}		}}
		ai_chance = {{
			base = 1
		}}
	}}
	option = {{
		name = spec_rival.1.b
		trigger = {{ spec_can_rv_shore = yes }}
		custom_tooltip = spec_rival.1.b_tt
		hidden_effect = {{
			spec_rv_shore = yes
		}}
		ai_chance = {{
			base = 1
		}}
	}}
	option = {{
		name = spec_rival.1.c
		default_option = yes
		custom_tooltip = spec_rival.1.c_tt
		hidden_effect = {{
			if = {{
				limit = {{ has_variable = spec_centre_trust }}
{_gain(CALM_GAIN, chr(9) * 4)}			}}
		}}
		ai_chance = {{
			base = 1
		}}
	}}
}}
"""


MODIFIERS = "".join(f"""spec_rv_press_{n} = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_newspaper_negative.dds
	country_influence_add = -{PRESS_INFL}
}}

""" for n in range(1, SLOTS + 1))


def build(write):
    write("common/scripted_triggers/spec_rival_triggers.txt", triggers())
    write("common/script_values/spec_rival_values.txt", values())
    write("common/scripted_effects/spec_rival_effects.txt", effects())
    write("common/scripted_guis/spec_rival_sguis.txt", sguis())
    write("events/spec_rival_events.txt", events())
    write("common/static_modifiers/spec_rival_modifiers.txt", MODIFIERS)


# -- interface --------------------------------------------------------------------------------------------------------

def _button(a):
    return f"""button = {{
	size = {{ 122 26 }}
	using = default_button
	align = center|nobaseline
	enabled = "[{CALL.format('rv_' + a, 'IsValid')}]"
	alpha = "[TransparentIfFalse({CALL.format('rv_' + a, 'IsValid')})]"
	onclick = "[{CALL.format('rv_' + a, 'Execute')}]"
	text = "SPEC_RV_{a.upper()}"
	tooltip = "SPEC_RV_{a.upper()}_TT"
}}
"""


ROW_H = 128


def _dbg(k, key):
    """A debug-mode button: the year's contest now, or every AI acting now."""
    return (f"\tbutton = {{\n\t\tsize = {{ 200 26 }}\n\t\tusing = default_button\n"
            f"\t\tonclick = \"[GetScriptedGui('spec_sgui_rv_dbg_{k}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]\"\n\t\ttext = \"{key}\"\n\t}}\n")


def block():
    """The Rivalries section's body: one row per country in a vanilla rivalry with us, either way."""
    line = lambda y, key, small=False: (f"\ttextbox = {{\n\t\tposition = {{ 20 {y} }}\n\t\tsize = {{ {W - 40} 22 }}\n"
                                        f"\t\talign = left|nobaseline\n\t\telide = right\n"
                                        + ("\t\tusing = fontsize_small\n" if small else "") + f"\t\ttext = \"{key}\"\n\t}}\n")
    row = f"""widget = {{
	size = {{ {W} {ROW_H} }}
	datacontext = "[Scope.GetCountry]"
	tooltip = "SPEC_RV_ROW_TT"
	background = {{
		using = entry_bg_simple
	}}
	tiny_flag = {{
		position = {{ 14 6 }}
	}}
	button = {{
		position = {{ 48 4 }}
		size = {{ 220 28 }}
		using = clean_button
		onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
		tooltipwidget = {{
			FancyTooltip_Country = {{}}
		}}
		textbox = {{
			size = {{ 100% 100% }}
			margin_left = 12
			align = nobaseline
			elide = right
			alwaystransparent = yes
			text = "SPEC_RV_NAME"
		}}
	}}
	textbox = {{
		position = {{ -16 4 }}
		size = {{ 250 28 }}
		parentanchor = right
		align = right|nobaseline
		text = "SPEC_RV_DIR"
	}}
{line(34, "SPEC_RV_LINE")}{line(54, "SPEC_RV_FX", True)}{line(72, "SPEC_RV_LAST", True)}	flowcontainer = {{
		position = {{ 14 96 }}
		spacing = 4
		visible = "[{shown('rv_is_pair')}]"
{ind(''.join(_button(a) for a in ACTIONS + ('shore',)), 2)}	}}
}}
"""
    model = f"{US}.GetList('spec_rv_pairs')"
    dbg = "".join(_dbg(k, key) for k, key in (("year", "SPEC_RV_DBG_YEAR"), ("ai", "SPEC_RV_DBG_AI")))
    return f"""flowcontainer = {{
	visible = "[InDebugMode]"
	parentanchor = hcenter
	spacing = 4
{dbg}}}
flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	spacing = 3
	datamodel = "[{model}]"
	item = {{
{ind(row, 2)}	}}
}}
textbox = {{
	visible = "[Not(GreaterThan_int32(GetDataModelSize({model}), '(int32)0'))]"
	size = {{ {W - 40} 60 }}
	parentanchor = hcenter
	multiline = yes
	align = left|nobaseline
	using = fontsize_small
	text = "SPEC_RV_EMPTY"
}}
"""


def marker():
    """World tab row, Rival column (the row's Country is the listed one): the rivalry icon on a rival's row."""
    return f"""		icon = {{
			visible = "[And(Not(ObjectsEqual(Country.Self, GetPlayer.Self)), Or({shown('rv_is_out')}, {shown('rv_is_in')}))]"
			position = {{ 322 0 }}
			size = {{ 28 28 }}
			parentanchor = vcenter
			texture = "gfx/interface/icons/lens_toolbar_icons/rivalry.dds"
			tooltip = "SPEC_RV_MARK_TT"
		}}
"""


def loc():
    sel = lambda cond, a, b: f"SelectLocalization({cond}, '{a}', '{b}')"
    var = lambda who, n: f"{who}.Var('{n}')"
    num = lambda who, n: f"{var(who, n)}.GetValue"
    eq = lambda x, n: f"EqualTo_CFixedPoint({x}, {fx(n)})"
    months = lambda who, n, key: f"[AddLocalizationIf({var(who, n)}.IsSet, '{key}')]"
    act = lambda who: (f"[SelectLocalization({eq(num(who, 'spec_rv_hit'), 1)}, 'SPEC_RV_RAID', "
                       f"{sel(eq(num(who, 'spec_rv_hit'), 2), 'SPEC_RV_LURE', 'SPEC_RV_PRESS')})]")
    res = lambda who: (f"[SelectLocalization({eq(num(who, 'spec_rv_hit_ok'), 1)}, 'SPEC_RV_OK', "
                       f"{sel(eq(num(who, 'spec_rv_hit_ok'), 0), 'SPEC_RV_FAILED', 'SPEC_RV_EXPOSED')})]")
    by = lambda who, other: f"And({var(who, 'spec_rv_hit_by')}.GetCountry.IsValid, ObjectsEqual({var(who, 'spec_rv_hit_by')}.GetCountry.Self, {other}))"
    score = lambda who: f"[{num(who, 'spec_centre_score')}|0]"
    their, ours = THEM, US
    fail = (f"Min_CFixedPoint({fx(RAID_FAIL + RAID_FAIL_MORE)}, Add_CFixedPoint({fx(RAID_FAIL)}, Multiply_CFixedPoint({fx(RAID_FAIL_MORE)}, "
            f"Max_CFixedPoint({fx(0)}, Divide_CFixedPoint(Subtract_CFixedPoint({num(their, 'spec_centre_score')}, {num(ours, 'spec_centre_score')}), "
            f"Max_CFixedPoint({num(their, 'spec_centre_score')}, {fx(1)}))))))")
    stake = pc(STAKE / CALM)
    rule = (f"When two countries with an [concept_spec_exchange] are rivals, whichever declared it, their Exchanges are rivals too. "
            f"Each year the one with the higher [Concept('concept_spec_financial_centre','$concept_spec_exchange$')] score wins #P {stake}#! "
            f"trust from the other when both hold the same Standing. Across a gap in Standing, a win by the lower Exchange pays more and a "
            f"win by the higher pays less: times or divided by one plus the gap. On poor relations or worse the loser loses #N x{BITTER:g}#!.\\n"
            "In a [concept_spec_financial_panic], fleeing money goes to a rival first.\\n"
            "Rivalries are declared and ended through diplomacy, with Declare Rivalry.")
    tip = lambda a, head, body: f' SPEC_RV_{a.upper()}_TT: "#header {head}#!\\n{body}\\n\\n[{CALL.format("rv_" + a, "BuildTooltip")}]"\n'
    cost = f"@money![{US}.ScriptValue('spec_rv_cost')|D]"
    debt = f"#N @money![{US}.ScriptValue('spec_rv_lure_debt')|D]#!"
    anyfx = lambda who: f"Or({var(who, 'spec_rv_raid')}.IsSet, Or({var(who, 'spec_rv_lure')}.IsSet, {var(who, 'spec_rv_shored')}.IsSet))"
    lines = [
        (f"SPEC_H_RIVAL", "Rivalries"),
        ("SPEC_H_RIVAL_TT", "#header Rivalries#!\\n$SPEC_RIVAL_RULE$"),
        ("SPEC_H_RIVAL_RIGHT", f"We rival #v [{num(US, 'spec_rv_n_out')}|0]#!, rivalled by #v [{num(US, 'spec_rv_n_in')}|0]#!"),
        ("SPEC_RIVAL_RULE", rule),
        ("SPEC_RV_NAME", "[Country.GetNameNoFormatting]"),
        ("SPEC_RV_DIR", f"[SelectLocalization(And({shown('rv_is_out')}, {shown('rv_is_in')}), 'SPEC_RV_DIR_BOTH', "
                        f"{sel(shown('rv_is_out'), 'SPEC_RV_DIR_OUT', 'SPEC_RV_DIR_IN')})]"),
        ("SPEC_RV_DIR_BOTH", "#v Mutual rivals#!"), ("SPEC_RV_DIR_OUT", "#v We rival them#!"), ("SPEC_RV_DIR_IN", "#v They rival us#!"),
        ("SPEC_RV_LINE", f"[{sel(shown('rv_is_pair'), 'SPEC_RV_LINE_ON', 'SPEC_RV_LINE_OFF')}]"),
        ("SPEC_RV_LINE_ON", f"Score: ours #v {score(US)}#!, theirs #v {score(THEM)}#!. $SPEC_RV_LAST_YEAR$"),
        ("SPEC_RV_LINE_OFF", "#N Not a rivalry of Exchanges:#! both countries need an [concept_spec_exchange]."),
        ("SPEC_RV_LAST_YEAR", f"[SelectLocalization({shown('rv_is_won')}, 'SPEC_RV_WON', {sel(shown('rv_is_lost'), 'SPEC_RV_LOST', 'SPEC_RV_NONE')})]"),
        ("SPEC_RV_WON", "#P Won last year#!"), ("SPEC_RV_LOST", "#N Lost last year#!"), ("SPEC_RV_NONE", "No result last year"),
        ("SPEC_RV_FX", f"[AddLocalizationIf({anyfx(THEM)}, 'SPEC_RV_FX_THEM')][AddLocalizationIf({anyfx(US)}, 'SPEC_RV_FX_US')]"
                       f"[AddLocalizationIf(Not(Or({anyfx(THEM)}, {anyfx(US)})), 'SPEC_RV_FX_NONE')]"),
        ("SPEC_RV_FX_THEM", f"Them: {months(THEM, 'spec_rv_raid', 'SPEC_RV_FX_RAID')}{months(THEM, 'spec_rv_lure', 'SPEC_RV_FX_LURE')}"
                            f"{months(THEM, 'spec_rv_shored', 'SPEC_RV_FX_SHORE')} "),
        ("SPEC_RV_FX_US", f"Us: {months(US, 'spec_rv_raid', 'SPEC_RV_FX_RAID_US')}"
                          f"{months(US, 'spec_rv_lure', 'SPEC_RV_FX_LURE_US')}{months(US, 'spec_rv_shored', 'SPEC_RV_FX_SHORE_US')}"),
        ("SPEC_RV_FX_NONE", "No actions running on either side."),
        ("SPEC_RV_DBG_YEAR", "Debug: yearly contest"), ("SPEC_RV_DBG_AI", "Debug: every AI acts"),
        ("spec_rv_raid_fx", f"We pay {cost}. Their [concept_spec_market_confidence] falls by #N {RAID_HIT:g}#! over {RAID_MONTHS} months, or ours if it fails."),
        ("spec_rv_lure_fx", f"Our [concept_spec_outstanding_credit] grows by {debt}. For {LURE_MONTHS} months #P {pc(LURE_SHARE)}#! of their [concept_investment_pool] income comes to ours."),
        ("spec_rv_press_fx", f"We pay #N {PRESS_INFL}#! influence for {PRESS_MONTHS} months. Their [concept_spec_exchange] loses #N {pc(PRESS_TRUST / CALM)}#! trust. "
                             f"#N {PRESS_EXPOSE}%#! chance it is exposed: relations #N -{PRESS_REL}#!, our trust #N -{pc(PRESS_TRUST / CALM)}#!."),
        ("spec_rv_shore_fx", f"We pay {cost}. For {SHORE_MONTHS} months every rival action against us has half its effect."),
        ("SPEC_RV_FX_RAID", f"#N Raided#! #v [{num(THEM, 'spec_rv_raid')}|0]#! mo. "),
        ("SPEC_RV_FX_LURE", f"#N Lured#! #v [{num(THEM, 'spec_rv_lure')}|0]#! mo. "),
        ("SPEC_RV_FX_SHORE", f"#P Shored up#! #v [{num(THEM, 'spec_rv_shored')}|0]#! mo. "),
        ("SPEC_RV_FX_RAID_US", f"#N Raided#! #v [{num(US, 'spec_rv_raid')}|0]#! mo. "),
        ("SPEC_RV_FX_LURE_US", f"#N Lured#! #v [{num(US, 'spec_rv_lure')}|0]#! mo. "),
        ("SPEC_RV_FX_SHORE_US", f"#P Shored up#! #v [{num(US, 'spec_rv_shored')}|0]#! mo. "),
        ("SPEC_RV_LAST", f"[SelectLocalization({by(THEM, 'GetPlayer.Self')}, 'SPEC_RV_LAST_OURS', "
                         f"{sel(by(US, 'Country.Self'), 'SPEC_RV_LAST_THEIRS', 'SPEC_RV_LAST_NONE')})]"),
        ("SPEC_RV_LAST_OURS", f"Our last move: #v {act(THEM)}#!, {res(THEM)}"),
        ("SPEC_RV_LAST_THEIRS", f"Their last move: #v {act(US)}#!, {res(US)}"),
        ("SPEC_RV_LAST_NONE", "No moves between us yet."),
        ("SPEC_RV_OK", "#P it worked#!"), ("SPEC_RV_FAILED", "#N it failed#!"), ("SPEC_RV_EXPOSED", "#N it was exposed#!"),
        ("SPEC_RV_RAID", "Bear Raid"), ("SPEC_RV_LURE", "Lure Capital"), ("SPEC_RV_PRESS", "Press Campaign"), ("SPEC_RV_SHORE", "Shore Up"),
        ("SPEC_RV_ROW_TT", "#header Rivalry with [Country.GetNameNoFormatting]#!\\n$SPEC_RIVAL_RULE$"),
        ("SPEC_RV_EMPTY", "No rivalries. Declare one through diplomacy with Declare Rivalry. A country that rivals us is listed here too."),
        ("SPEC_RV_MARK_TT", "#header Rival#!\\n$SPEC_RIVAL_RULE$"),
        ("spec_rv_pair_tt", "We rival each other through diplomacy, and both countries have an [concept_spec_exchange]"),
        ("spec_rv_exch_tt", "Our country has an [concept_spec_exchange]"),
        ("spec_rv_cd_tt", "We have not used this against them in the last year"),
        ("spec_rv_shore_cd_tt", f"We have not shored up in the last #v {SHORE_CD}#! years"),
        ("spec_rv_gold_tt", f"Our treasury holds {cost}"),
        ("spec_rv_panic_tt", "Our market is not in a [concept_spec_financial_panic]"),
        ("spec_rv_lured_tt", "No one is luring their capital already"),
        ("spec_rv_infl_tt", f"We have #v {PRESS_INFL}#! influence to spare"),
        ("spec_rv_slots_tt", f"We run fewer than #v {SLOTS}#! press campaigns"),
        ("spec_rv_press_1", "Press Campaign"), ("spec_rv_press_2", "Second Press Campaign"), ("spec_rv_press_3", "Third Press Campaign"),
        *((f"spec_rv_press_{n}_desc", "Newspapers abroad are paid to doubt a rival Exchange.") for n in range(1, SLOTS + 1)),
        ("spec_rival.1.t", "A Rival Moves Against Us"),
        ("spec_rival.1.d11", f"Brokers in [SCOPE.sCountry('target').GetName] sold our securities short all at once. "
                             f"Our [concept_spec_market_confidence] will fall by #N {RAID_HIT:g}#! over {RAID_MONTHS} months, twice that in a [concept_spec_speculative_mania]."),
        ("spec_rival.1.d10", "Brokers in [SCOPE.sCountry('target').GetName] tried to break our market by selling short, and misjudged it. "
                             f"Their own [concept_spec_market_confidence] falls by #P {RAID_HIT:g}#! over {RAID_MONTHS} months."),
        ("spec_rival.1.d21", "Bankers from [SCOPE.sCountry('target').GetName] are courting our investors with better terms. "
                             f"For {LURE_MONTHS} months, #N {pc(LURE_SHARE)}#! of our [concept_investment_pool] income goes to them."),
        ("spec_rival.1.d31", "Newspapers in [SCOPE.sCountry('target').GetName] are full of doubts about our [concept_spec_exchange]. "
                             f"It loses #N {pc(PRESS_TRUST / CALM)}#! trust."),
        ("spec_rival.1.d3n", "Newspapers in [SCOPE.sCountry('target').GetName] are full of doubts about our [concept_spec_exchange], "
                             "and it is now known who paid them. We lose trust, but so do they, and their name suffers abroad."),
        ("spec_rival.1.f", '\\"A run on the market may begin with a single rumour.\\"'),
        ("spec_rival.1.a", "Answer in kind."), ("spec_rival.1.a_tt", "We do the same to them, paying its cost, even if we did so this year."),
        ("spec_rival.1.b", "Shore up our market."), ("spec_rival.1.b_tt", f"For {SHORE_MONTHS} months every rival action against us has half its effect. Costs {cost}."),
        ("spec_rival.1.c", "Keep calm."), ("spec_rival.1.c_tt", f"Our [concept_spec_exchange] gains #P {pc(CALM_GAIN / CALM)}#! trust for keeping its head."),
    ]
    lines += [
        ("SPEC_DRIVER_RIVAL", "Rival Actions"),
        ("SPEC_DRIVER_RIVAL_TT", "#header Rival Actions: [Country.MakeScope.Var('spec_c_rival').GetValueWithDefault('(CFixedPoint)0')|+=2]#!\\n"
                                 "A rival's Bear Raid on our market, spread over six months."),
    ]
    out = "".join(f' {k}: "{t}"\n' for k, t in lines)
    out += tip("raid", "Bear Raid",
               f"Sell their securities short: their [concept_spec_market_confidence] falls by #N {RAID_HIT:g}#! over {RAID_MONTHS} months, "
               f"twice that in a [concept_spec_speculative_mania]. Costs {cost}.\\nIt fails #N [{fail}|0]%#! of the time, more as their score "
               "exceeds ours, and then we take the fall instead.")
    out += tip("lure", "Lure Their Capital",
               f"For {LURE_MONTHS} months, #P {pc(LURE_SHARE)}#! of their [concept_investment_pool] income comes to ours. "
               f"Our [concept_spec_outstanding_credit] grows by #N {LURE_DEBT}#! months of our own pool income, and our leverage with it.")
    out += tip("press", "Press Campaign",
               f"Their [concept_spec_exchange] loses #N {pc(PRESS_TRUST / CALM)}#! trust. Costs #N {PRESS_INFL}#! influence for {PRESS_MONTHS} months.\\n"
               f"#N {PRESS_EXPOSE}%#! of the time it is exposed: relations #N -{PRESS_REL}#! and our own trust #N -{pc(PRESS_TRUST / CALM)}#!.")
    out += tip("shore", "Shore Up",
               f"For {SHORE_MONTHS} months every rival action against us, from any rival, has half its effect. Costs {cost}. "
               f"Once every {SHORE_CD} years.")
    return out


if __name__ == "__main__":
    import re
    gui = block() + marker()
    words = loc()
    for s in (triggers(), values(), effects(), sguis(), events(), MODIFIERS, pass_(), MONTHLY, gui):
        assert s.count("{") == s.count("}"), s[:200]
        assert not re.search(r"\d\.\d{4,}", s)
    keys = {line.split(":")[0].strip() for line in words.splitlines()}
    used = set(re.findall(r'"(SPEC_[A-Z0-9_]+)"', gui)) | set(re.findall(r"'(SPEC_[A-Z0-9_]+)'", words))
    assert used <= keys, used - keys
    script = triggers() + effects() + events()
    tts = set(re.findall(r"text = (spec_rv_\w+_tt)", script))
    assert tts <= keys, tts - keys
    contest = effects().split("spec_rival_contest = {")[1].split("# end spec_rival_contest")[0]
    assert contest.count("is_player = yes") == 4 and contest.count("post_notification") == 2  # the notification testbed swaps these
    print("ok")
