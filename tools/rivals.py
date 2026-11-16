"""Rival Exchanges (design_rivals.md): an Exchange names its rivals (var list spec_rv_chosen), apart from vanilla's
rivalries: one, or two from International Standing, among Exchanges within one Standing of its own, each kept at least a
year. A pair counts whichever named the other, both needing an Exchange. Once a year the pair's higher Financial Centre score wins a small amount of trust from the other. Between
contests either side may act against the other: Bear Raid, Lure Their Capital, Press Campaign, and Shore Up in defence.
The AI acts both ways, and a player who is targeted gets an event.

centres.py calls this module: pass_() in its monthly ranking pass, block() and marker() in the World tab, loc() in its
localization. build(write) writes the rest. An old save's single named rival (spec_rival) becomes a named rival; its
spec_rival_lock and spec_rival_last go. The AI names the nearest-scoring Exchange above it within reach."""
import icons
import tuning
from market_tab import W, fx, ind, heads, section, SLIDE, CLEAR

STAKE = tuning.get("RIVAL_STAKE", 3)          # contest trust at an equal standing (out of CALM)
BITTER = tuning.get("EXCH_RIVAL_BITTER", 1.5)  # the loser's loss times this on poor relations or worse
RAID_GDP = tuning.get("RIVAL_RAID_GDP", 0.005)  # Bear Raid and Shore Up: share of our GDP from the treasury
RAID_HIT, RAID_MONTHS = tuning.get("RIVAL_RAID_HIT", 6), 6  # confidence lost over the months
RAID_FAIL, RAID_FAIL_MORE = 20, 60            # % failure, plus up to this much more as their score exceeds ours
LURE_DEBT, LURE_SHARE, LURE_MONTHS = 2, tuning.get("RIVAL_LURE_SHARE", 0.1), 12  # months of our pool income owed
PRESS_INFL, PRESS_TRUST, PRESS_EXPOSE, PRESS_REL, PRESS_MONTHS = 25, 6, 30, 20, 12
VS_LO, VS_HI = 0.75, 1.33                         # their Exchange's score over ours, as costs and effects scale by it
SHORE_MONTHS, SHORE_CD = 12, 2                 # months one rival's moves are halved; years before shoring up against it again
CD_DAYS = 365                                 # each action's cooldown, per target
AI_CHANCE, AI_TEMPER = tuning.get("RIVAL_AI_CHANCE", 25), 15  # % a year per rivalry; Bold +, Cautious -
CALM_GAIN = 2                                 # the event's Ignore
MANIA = tuning.get("MANIA", 80)
CALM = tuning.get("CENTRE_CALM", 120)
ACTIONS = ("raid", "lure", "press")           # spec_rv_hit codes 1, 2, 3
SLOTS = 3                                     # Press Campaigns running at once, one modifier each
NAMED, NAMED_HIGH, NAMED_FROM = 1, 2, 2       # rivals an Exchange may name; NAMED_HIGH from this Standing (International)
REACH = 1                                     # a named rival's Standing within this many of ours
KEEP_DAYS = 365                               # a newly named rival cannot be dropped for this long
REL_HIT, REL_DRIFT = 10, 1                    # relations lost on rivalling, and each month after down to Poor (vanilla rivalry: to -20)
AI_CAP = 3                                    # the AI rivals no Exchange that this many already rival
AI_URGENCY = 15                               # % more a year to act, per year of the round gone
AI_REACH = -0.3                               # the AI names only rivals it starts no further behind than this
AI_CUT = -0.65                                # early in a round, it drops a rival it is this far behind
# the contest is a tug of war settled every ROUND years: the bar starts from the two scores (the lead as a share of the
# higher), each successful action pushes it PUSH toward its side (at most PUSHES each way, spec_rv_push_1..N lists on
# the pusher), and where it ends picks one of five results: a draw inside DRAW, past DECISIVE a decisive win or loss
ROUND = 5
PUSH, PUSHES = 0.1, 5
DRAW, DECISIVE = 0.1, 0.4
WIN_X, BIG_X = 2, 4                           # trust at stake: STAKE times these for a win and a decisive win
UPKEEP = (25, 50, 100, 150)                   # influence maintenance of a rival, by its Standing (vanilla pacts: 25 to 150)
OLD_VARS = ["spec_rival", "spec_rival_lock", "spec_rival_last", "spec_rv_shored", "spec_rv_shore_cd"]  # the last two: Shore Up before it was per rival
STATE_VARS = OLD_VARS + ["spec_c_rival", "spec_rv_raid", "spec_rv_raid_pm", "spec_rv_raider", "spec_rv_lure", "spec_rv_lurer", "spec_rv_lure_share",
                         "spec_rv_hit", "spec_rv_hit_by", "spec_rv_hit_ok", "spec_rv_hit_recent",
                         "spec_rv_n_out", "spec_rv_n_in", "spec_rv_n_chosen", "spec_rv_ui_p", "spec_rv_ui_us", "spec_rv_ui_them"]
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
    out = f"""# rival Exchanges (rivals.py): one named the other, both with an Exchange; scope:target = the other
spec_rv_chose = {{
	is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:target }}
}}

spec_rv_chosen_by = {{
	scope:target = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }}
}}

spec_rv_pair = {{
	{exch}
	scope:target = {{ {exch} }}
	OR = {{
		spec_rv_chose = yes
		spec_rv_chosen_by = yes
	}}
}}

spec_can_rv_choose = {{
	custom_tooltip = {{
		text = spec_rv_exch_tt
		{exch}
	}}
	custom_tooltip = {{
		text = spec_rv_their_exch_tt
		scope:target = {{ {exch} }}
	}}
}}

spec_can_rv_end = {{
	custom_tooltip = {{
		text = spec_rv_keep_tt
		NOT = {{ is_target_in_variable_list = {{ name = spec_rv_keep target = scope:target }} }}
	}}
}}

spec_can_rv_toggle = {{
	trigger_if = {{
		limit = {{ spec_rv_chose = yes }}
		spec_can_rv_end = yes
	}}
	trigger_else = {{
		spec_can_rv_choose = yes
	}}
}}

spec_can_rv_shore = {{
{pair}	custom_tooltip = {{
		text = spec_rv_shore_cd_tt
		NOT = {{ is_target_in_variable_list = {{ name = spec_rv_cd_shore target = scope:target }} }}
	}}
	custom_tooltip = {{
		text = spec_rv_shield_tt
		NOT = {{ is_target_in_variable_list = {{ name = spec_rv_shield target = scope:target }} }}
	}}
{gold}}}
"""
    for a in ACTIONS:
        out += f"\nspec_rv_pay_{a} = {{\n{pay[a]}}}\n\nspec_can_rv_{a} = {{\n{pair}{cd(a)}\tspec_rv_pay_{a} = yes\n}}\n"
    # Hold the Line: undo one of their pushes against us
    pushed = ("\tcustom_tooltip = {\n\t\ttext = spec_rv_pushed_tt\n"
              "\t\tscope:target = { is_target_in_variable_list = { name = spec_rv_push_1 target = prev } }\n\t}\n")
    out += f"\nspec_can_rv_hold = {{\n{pair}{cd('hold')}{pushed}{gold}}}\n"
    return out


def values():
    them = "scope:target.var:spec_centre_score"
    return f"""# rival actions (actor scope, scope:target): their Exchange's size against ours, VS_LO to VS_HI. A larger rival
# costs more to act against or to shore up against; a larger Exchange's moves hit harder (spec_rv_heft, the inverse)
spec_rv_vs = {{
	value = 1
	if = {{
		limit = {{
			has_variable = spec_centre_score
			scope:target ?= {{ has_variable = spec_centre_score }}
		}}
		value = scope:target.var:spec_centre_score
		divide = {{
			value = var:spec_centre_score
			min = 1
		}}
	}}
	min = {VS_LO:g}
	max = {VS_HI:g}
}}

spec_rv_heft = {{
	value = 1
	divide = spec_rv_vs
}}

spec_rv_cost_base = {{
	value = gdp
	multiply = {RAID_GDP:g}
	min = 0
}}

spec_rv_cost = {{
	value = spec_rv_cost_base
	multiply = spec_rv_vs
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

spec_rv_lure_debt_base = {{
	value = spec_pool_month
	multiply = {LURE_DEBT}
}}

spec_rv_lure_debt = {{
	value = spec_rv_lure_debt_base
	multiply = spec_rv_vs
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

# the contest's bar from scope:spec_rival_me's side against this: the score lead as a share of the higher score, then
# the pushes each way, from -1 (theirs) to 1 (ours)
spec_rv_rope = {{
	value = scope:spec_rival_me.var:spec_centre_score
	subtract = var:spec_centre_score
	divide = {{
		value = var:spec_centre_score
		min = scope:spec_rival_me.var:spec_centre_score
		min = 1
	}}
{"".join(f'''	if = {{
		limit = {{ scope:spec_rival_me = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = prev }} }} }}
		add = {PUSH:g}
	}}
	if = {{
		limit = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = scope:spec_rival_me }} }}
		subtract = {PUSH:g}
	}}
''' for k in range(1, PUSHES + 1))}	min = -1
	max = 1
}}

# pushes on the contest between this and scope:spec_rival_me, by each side
spec_rv_n_push_me = {{
	value = 0
{"".join(f"	if = {{{chr(10)}		limit = {{ scope:spec_rival_me = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = prev }} }} }}{chr(10)}		add = 1{chr(10)}	}}{chr(10)}" for k in range(1, PUSHES + 1))}}}

spec_rv_n_push_it = {{
	value = 0
{"".join(f"	if = {{{chr(10)}		limit = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = scope:spec_rival_me }} }}{chr(10)}		add = 1{chr(10)}	}}{chr(10)}" for k in range(1, PUSHES + 1))}}}

# rivals an Exchange may name, and the Standings it may name them from
spec_rv_slots = {{
	value = {NAMED}
	if = {{
		limit = {{ has_variable = spec_exch_stand var:spec_exch_stand >= {NAMED_FROM} }}
		value = {NAMED_HIGH}
	}}
}}

spec_rv_reach_lo = {{
	value = var:spec_exch_stand
	subtract = {REACH}
}}

spec_rv_reach_hi = {{
	value = var:spec_exch_stand
	add = {REACH}
}}

# influence maintenance of rivalling this country, by its Standing (none counts as the lowest)
spec_rv_tier_cost = {{
	value = {UPKEEP[0]}
{"".join(f"	if = {{\n		limit = {{ has_variable = spec_exch_stand var:spec_exch_stand = {t} }}\n		value = {c}\n	}}\n" for t, c in enumerate(UPKEEP) if t)}}}

# our rivals' maintenance in all (spec_rv_count sums it)
spec_rv_upkeep_total = {{
	value = 0
	if = {{
		limit = {{ has_variable = spec_rv_upkeep_sum }}
		value = var:spec_rv_upkeep_sum
	}}
	if = {{  # a World Centre keeps its dearest rival free (centres.WORLD_FX)
		limit = {{ has_variable = spec_rv_upkeep_max has_variable = spec_exch_stand var:spec_exch_stand = 3 }}
		subtract = var:spec_rv_upkeep_max
	}}
}}

# the AI's pick, in a candidate against scope:spec_rival_me (the AI): its side of the bar, plus the bigger prize of
# beating a higher Standing (rivals' spec_rv_stake)
spec_rv_ai_pick_v = {{
	value = spec_rv_rope
	add = {{
		value = var:spec_exch_stand
		subtract = scope:spec_rival_me.var:spec_exch_stand
		multiply = 0.15
	}}
}}

spec_rv_ai_chance = {{
	value = {AI_CHANCE}
	if = {{  # keener as the contest nears its settling (spec_rv_ai runs after the round's count moves on)
		limit = {{ has_global_variable = spec_rv_round }}
		add = {{
			value = global_var:spec_rv_round
			multiply = {AI_URGENCY}
		}}
	}}
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
    """Halved if the side taking the hit has shored up against the other: the target, or the actor of a failed raid."""
    other = ("OR = { AND = { this = scope:spec_rv_actor is_target_in_variable_list = { name = spec_rv_shield target = scope:target } } "
             "AND = { NOT = { this = scope:spec_rv_actor } is_target_in_variable_list = { name = spec_rv_shield target = scope:spec_rv_actor } } }")
    return f"{t}if = {{\n{t}\tlimit = {{ {other} }}\n{t}\tchange_local_variable = {{ name = {var} multiply = 0.5 }}\n{t}}}\n"


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
    # a decisive result: the winner's stake BIG_X over WIN_X, and the loser's pool income lured to the winner for a year
    big = lambda t: f"""{t}if = {{
{t}	limit = {{ local_var:spec_rv_big = 1 }}
{t}	$DO$
{t}}}
"""
    body = f"""scope:spec_rv_w = {{
	set_local_variable = {{ name = spec_rv_stake value = spec_rv_stake }}
	change_local_variable = {{ name = spec_rv_stake multiply = {WIN_X} }}
{big(chr(9)).replace("$DO$", f"change_local_variable = {{ name = spec_rv_stake multiply = {BIG_X / WIN_X:g} }}")}{_gain("local_var:spec_rv_stake", chr(9))}	add_to_variable_list = {{ name = spec_rv_won target = scope:spec_rv_l }}
{big(chr(9)).replace("$DO$", "add_to_variable_list = { name = spec_rv_big target = scope:spec_rv_l }")}{note("won")}}}
scope:spec_rv_l = {{
{_lose("local_var:spec_rv_stake", chr(9))}	if = {{
		limit = {{ "relations(scope:spec_rv_w)" <= relations_threshold:poor }}
{_lose(f"{{ value = local_var:spec_rv_stake multiply = {BITTER - 1:g} }}", chr(9) * 2)}	}}
	add_to_variable_list = {{ name = spec_rv_lost target = scope:spec_rv_w }}
	if = {{
		limit = {{ local_var:spec_rv_big = 1 }}
		add_to_variable_list = {{ name = spec_rv_big target = scope:spec_rv_w }}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_rv_lure }} }}
			set_variable = {{ name = spec_rv_lure value = {LURE_MONTHS} }}
			set_variable = {{ name = spec_rv_lurer value = scope:spec_rv_w }}
			set_variable = {{ name = spec_rv_lure_share value = {LURE_SHARE:g} }}
		}}
	}}
{note("lost")}}}
"""
    return f"""# rival Exchanges (rivals.py): every {ROUND} years each pair's bar (spec_rv_rope) settles, in five bands
spec_rival_contest = {{
	every_country = {{
		limit = {{ has_variable = spec_exch_stand }}
		clear_variable_list = spec_rv_won
		clear_variable_list = spec_rv_lost
		clear_variable_list = spec_rv_tied
		clear_variable_list = spec_rv_big
	}}
	every_country = {{
		limit = {{ {exch} }}
		save_scope_as = spec_rival_me
		every_in_list = {{
			variable = spec_rv_chosen
			limit = {{
				{exch}
				NOT = {{ OR = {{ {done} }} }}
			}}
			set_local_variable = {{ name = spec_rv_p value = spec_rv_rope }}
			set_local_variable = {{ name = spec_rv_big value = 0 }}
			if = {{
				limit = {{ local_var:spec_rv_p >= {DECISIVE} }}
				set_local_variable = {{ name = spec_rv_big value = 1 }}
			}}
			if = {{
				limit = {{ local_var:spec_rv_p <= -{DECISIVE} }}
				set_local_variable = {{ name = spec_rv_big value = 1 }}
			}}
			if = {{
				limit = {{ local_var:spec_rv_p >= {DRAW} }}
				scope:spec_rival_me = {{ save_scope_as = spec_rv_w }}
				save_scope_as = spec_rv_l
			}}
			else_if = {{
				limit = {{ local_var:spec_rv_p <= -{DRAW} }}
				save_scope_as = spec_rv_w
				scope:spec_rival_me = {{ save_scope_as = spec_rv_l }}
			}}
			if = {{
				limit = {{ local_var:spec_rv_p > -{DRAW} local_var:spec_rv_p < {DRAW} }}
				add_to_variable_list = {{ name = spec_rv_tied target = scope:spec_rival_me }}
				save_temporary_scope_as = spec_rv_x
				scope:spec_rival_me = {{ add_to_variable_list = {{ name = spec_rv_tied target = scope:spec_rv_x }} }}
			}}
			else = {{
{ind(body, 4)}			}}
		}}
	}}
	# a new round: every push is spent
	every_country = {{
		limit = {{ has_variable_list = spec_rv_push_1 }}
{"".join(f"		clear_variable_list = spec_rv_push_{k}{chr(10)}" for k in range(1, PUSHES + 1))}	}}
	every_country = {{
		limit = {{ OR = {{ has_variable = spec_rival_note_won has_variable = spec_rival_note_lost }} }}
{flush}	}}
}}
# end spec_rival_contest

# a player's rows: rivals we named (spec_rv_outs), and Exchanges that named us (spec_rv_ins); a mutual one is in both
spec_rv_list = {{
	clear_variable_list = spec_rv_pairs
	clear_variable_list = spec_rv_outs
	clear_variable_list = spec_rv_ins
	set_variable = {{ name = spec_rv_n_out value = 0 }}
	set_variable = {{ name = spec_rv_n_in value = 0 }}
	save_scope_as = spec_rv_me
	every_in_list = {{
		variable = spec_rv_chosen
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_me = {{
			add_to_variable_list = {{ name = spec_rv_outs target = scope:spec_rv_x }}
			change_variable = {{ name = spec_rv_n_out add = 1 }}
		}}
	}}
	every_country = {{
		limit = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_me }} }}
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_me = {{
			change_variable = {{ name = spec_rv_n_in add = 1 }}
			add_to_variable_list = {{ name = spec_rv_ins target = scope:spec_rv_x }}
		}}
	}}
	spec_rv_ui = yes
}}

# a player's rows each carry its contest from the player's side (spec_rv_ui_p, the bar; spec_rv_ui_us and _them, the
# pushes), so the screen reads three numbers instead of working the bar out every frame. Monthly, and on each push.
# ponytail: one set per row country, so two players rivalling the same Exchange share it in multiplayer; per-player
# copies if that matters
spec_rv_ui = {{
	save_scope_as = spec_rival_me
	every_in_list = {{
		variable = spec_rv_outs
		spec_rv_ui_row = yes
	}}
	every_in_list = {{
		variable = spec_rv_ins
		spec_rv_ui_row = yes
	}}
}}

spec_rv_ui_row = {{
	if = {{
		limit = {{
			{exch}
			scope:spec_rival_me = {{ {exch} }}
		}}
		set_variable = {{ name = spec_rv_ui_p value = spec_rv_rope }}
		set_variable = {{ name = spec_rv_ui_us value = spec_rv_n_push_me }}
		set_variable = {{ name = spec_rv_ui_them value = spec_rv_n_push_it }}
	}}
	else_if = {{
		limit = {{ has_variable = spec_rv_ui_p }}
		remove_variable = spec_rv_ui_p
	}}
}}

# the named rivals: the dead go, the rest are counted (spec_rv_n_chosen) and their maintenance summed (spec_rv_upkeep_sum)
spec_rv_count = {{
	save_scope_as = spec_rv_cnt
	every_in_list = {{
		variable = spec_rv_chosen
		limit = {{ is_country_alive = no }}
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_cnt = {{ remove_list_variable = {{ name = spec_rv_chosen target = scope:spec_rv_x }} }}
	}}
	set_variable = {{ name = spec_rv_n_chosen value = 0 }}
	set_variable = {{ name = spec_rv_upkeep_sum value = 0 }}
	set_variable = {{ name = spec_rv_upkeep_max value = 0 }}
	every_in_list = {{
		variable = spec_rv_chosen
		set_local_variable = {{ name = spec_rv_c value = spec_rv_tier_cost }}
		scope:spec_rv_cnt = {{
			change_variable = {{ name = spec_rv_n_chosen add = 1 }}
			change_variable = {{ name = spec_rv_upkeep_sum add = local_var:spec_rv_c }}
			if = {{
				limit = {{ var:spec_rv_upkeep_max < local_var:spec_rv_c }}
				set_variable = {{ name = spec_rv_upkeep_max value = local_var:spec_rv_c }}
			}}
		}}
	}}
	if = {{
		limit = {{ has_modifier = spec_rv_upkeep }}
		remove_modifier = spec_rv_upkeep
	}}
	if = {{
		limit = {{ var:spec_rv_n_chosen > 0 }}
		add_modifier = {{ name = spec_rv_upkeep multiplier = spec_rv_upkeep_total }}
	}}
}}

# name scope:target a rival, or drop it; a player's rows follow at once
spec_rv_choose = {{
	add_to_variable_list = {{ name = spec_rv_chosen target = scope:target }}
	change_relations = {{ country = scope:target value = -{REL_HIT} }}
	add_to_variable_list = {{ name = spec_rv_keep target = scope:target days = {KEEP_DAYS} }}
	spec_rv_count = yes
	if = {{
		limit = {{ is_player = yes }}
		spec_rv_list = yes
	}}
}}

# each month, relations with every rival we named fall, down to Poor (as vanilla's rivalry, to -20)
spec_rv_sour = {{
	save_scope_as = spec_rv_me
	every_in_list = {{
		variable = spec_rv_chosen
		save_temporary_scope_as = spec_rv_x
		scope:spec_rv_me = {{
			if = {{
				limit = {{ "relations(scope:spec_rv_x)" > relations_threshold:poor }}
				change_relations = {{ country = scope:spec_rv_x value = -{REL_DRIFT} }}
			}}
		}}
	}}
}}

spec_rv_end = {{
	remove_list_variable = {{ name = spec_rv_chosen target = scope:target }}
	spec_rv_count = yes
	if = {{
		limit = {{ is_player = yes }}
		spec_rv_list = yes
	}}
}}

# $BY$ pushes its contest bar against $ON$ one step, up to PUSHES (one list per step, so the count is the step reached)
spec_rv_push = {{
	$BY$ = {{
{"".join(f'''		{"if" if k == 1 else "else_if"} = {{
			limit = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = $ON$ }} }} }}
			add_to_variable_list = {{ name = spec_rv_push_{k} target = $ON$ }}
		}}
''' for k in range(1, PUSHES + 1))}	}}
	$BY$ = {{
		if = {{
			limit = {{ is_player = yes }}
			spec_rv_ui = yes
		}}
	}}
	$ON$ = {{
		if = {{
			limit = {{ is_player = yes }}
			spec_rv_ui = yes
		}}
	}}
}}

# $BY$'s last push against $ON$ is undone
spec_rv_unpush = {{
	$BY$ = {{
{"".join(f'''		{"if" if k == PUSHES else "else_if"} = {{
			limit = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = $ON$ }} }}
			remove_list_variable = {{ name = spec_rv_push_{k} target = $ON$ }}
		}}
''' for k in range(PUSHES, 0, -1))}	}}
	$BY$ = {{
		if = {{
			limit = {{ is_player = yes }}
			spec_rv_ui = yes
		}}
	}}
	$ON$ = {{
		if = {{
			limit = {{ is_player = yes }}
			spec_rv_ui = yes
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
		limit = {{ has_local_variable = spec_rv_amp }}
		change_local_variable = {{ name = spec_rv_pm multiply = local_var:spec_rv_amp }}
	}}
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
	if = {{
		limit = {{ this = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_raider value = scope:target }}
	}}
	else = {{
		set_variable = {{ name = spec_rv_raider value = scope:spec_rv_actor }}
	}}
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
		set_local_variable = {{ name = spec_rv_amp value = spec_nx_raid }}
		change_local_variable = {{ name = spec_rv_amp multiply = spec_rv_heft }}
		scope:target = {{ spec_rv_raided = yes }}
		spec_rv_push = {{ BY = scope:spec_rv_actor ON = scope:target }}
	}}
	else = {{
		set_local_variable = {{ name = spec_rv_ok value = 0 }}
		set_local_variable = {{ name = spec_rv_amp value = 1 }}
		spec_rv_raided = yes
		spec_rv_push = {{ BY = scope:target ON = scope:spec_rv_actor }}
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
	set_local_variable = {{ name = spec_rv_amp value = spec_nx_lure }}
	change_local_variable = {{ name = spec_rv_amp multiply = spec_rv_heft }}
	scope:target = {{
		set_local_variable = {{ name = spec_rv_share value = {LURE_SHARE:g} }}
		change_local_variable = {{ name = spec_rv_share multiply = local_var:spec_rv_amp }}
{_half("spec_rv_share", chr(9) * 2)}		set_variable = {{ name = spec_rv_lure value = {LURE_MONTHS} }}
		set_variable = {{ name = spec_rv_lurer value = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_lure_share value = local_var:spec_rv_share }}
	}}
	spec_rv_push = {{ BY = scope:spec_rv_actor ON = scope:target }}
	spec_rv_log = {{ CODE = 2 }}
	}}
}}

spec_rv_press = {{
	custom_tooltip = spec_rv_press_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
{slots}	add_to_variable_list = {{ name = spec_rv_cd_press target = scope:target days = {CD_DAYS} }}
	set_local_variable = {{ name = spec_rv_ok value = 1 }}
	set_local_variable = {{ name = spec_rv_amp value = spec_nx_press }}
	change_local_variable = {{ name = spec_rv_amp multiply = spec_rv_heft }}
	scope:target = {{
		set_local_variable = {{ name = spec_rv_t value = {PRESS_TRUST} }}
		change_local_variable = {{ name = spec_rv_t multiply = local_var:spec_rv_amp }}
{_half("spec_rv_t", chr(9) * 2)}{_lose("local_var:spec_rv_t", chr(9) * 2)}	}}
	random = {{
		chance = {PRESS_EXPOSE}
		set_local_variable = {{ name = spec_rv_ok value = -1 }}
		change_relations = {{ country = scope:target value = -{PRESS_REL} }}
{_lose(PRESS_TRUST, chr(9) * 2)}	}}
	if = {{
		limit = {{ local_var:spec_rv_ok = 1 }}
		spec_rv_push = {{ BY = scope:spec_rv_actor ON = scope:target }}
	}}
	else = {{
		spec_rv_push = {{ BY = scope:target ON = scope:spec_rv_actor }}
	}}
	spec_rv_log = {{ CODE = 3 }}
	}}
}}

spec_rv_hold = {{
	custom_tooltip = spec_rv_hold_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
	add_treasury = spec_rv_cost_neg
	add_to_variable_list = {{ name = spec_rv_cd_hold target = scope:target days = {CD_DAYS} }}
	spec_rv_unpush = {{ BY = scope:target ON = scope:spec_rv_actor }}
	}}
}}

spec_rv_shore = {{
	custom_tooltip = spec_rv_shore_fx
	hidden_effect = {{
	add_treasury = spec_rv_cost_neg
	# ponytail: a list's days take no script value, so two lengths: the Safe Harbour's (centres.NX, shore 1.4) or the
	# plain one; more steps here if more specialities lengthen it
	if = {{
		limit = {{ spec_nx_shore > 1.05 }}
		add_to_variable_list = {{ name = spec_rv_shield target = scope:target days = {round(SHORE_MONTHS * 30 * 1.4)} }}
	}}
	else = {{
		add_to_variable_list = {{ name = spec_rv_shield target = scope:target days = {SHORE_MONTHS * 30} }}
	}}
	add_to_variable_list = {{ name = spec_rv_cd_shore target = scope:target days = {SHORE_CD * 365} }}
	}}
}}

# the AI against scope:target, at most once a year per rivalry, from where its contest stands (spec_rv_ai_p, its
# side): Shore Up against whoever just hit it; nothing while already safely decisive; else undo their push (sure), else
# push: Lure most (it cannot fail), Press next, a Bear Raid mostly when our score is the higher (it fails less)
spec_rv_ai_act = {{
	save_scope_as = spec_rival_me
	scope:target = {{ set_local_variable = {{ name = spec_rv_ai_p value = spec_rv_rope }} }}
	random = {{
		chance = spec_rv_ai_chance
		if = {{
			limit = {{
				has_variable = spec_rv_hit_recent
				exists = var:spec_rv_hit_by
				var:spec_rv_hit_by = scope:target
				spec_can_rv_shore = yes
			}}
			spec_rv_shore = yes
		}}
		else_if = {{
			limit = {{ local_var:spec_rv_ai_p >= {DECISIVE + PUSH:g} }}
		}}
		else_if = {{
			limit = {{ spec_can_rv_hold = yes }}
			spec_rv_hold = yes
		}}
		else_if = {{
			limit = {{ OR = {{ {" ".join(f"spec_can_rv_{a} = yes" for a in ACTIONS)} }} }}
			random_list = {{
				3 = {{
					trigger = {{ spec_can_rv_lure = yes }}
					spec_rv_lure = yes
				}}
				2 = {{
					trigger = {{ spec_can_rv_press = yes }}
					spec_rv_press = yes
				}}
				1 = {{
					trigger = {{ spec_can_rv_raid = yes }}
					spec_rv_raid = yes
				}}
				2 = {{
					trigger = {{ spec_can_rv_raid = yes var:spec_centre_score >= scope:target.var:spec_centre_score }}
					spec_rv_raid = yes
				}}
			}}
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
		every_in_list = {{
			variable = spec_rv_chosen
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
		every_country = {{
			limit = {{
				is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_ai_me }}
				NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }}
			}}
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
	}}
}}

# once a year, before the contest: an AI drops rivals out of reach, without an Exchange, rivalled by more than AI_CAP,
# or, early in a round, too far ahead to catch; then fills its free slots among Exchanges fewer than AI_CAP rival (else
# everyone tied below one Exchange piles onto it) that it starts no further behind than AI_REACH, the best prize first
spec_rv_ai_pick = {{
	every_country = {{
		limit = {{
			is_player = no
			{exch}
		}}
		save_scope_as = spec_rv_ai_me
		save_scope_as = spec_rival_me
		set_local_variable = {{ name = spec_rv_lo value = spec_rv_reach_lo }}
		set_local_variable = {{ name = spec_rv_hi value = spec_rv_reach_hi }}
		every_in_list = {{
			variable = spec_rv_chosen
			limit = {{
				OR = {{
					is_country_alive = no
					NOT = {{ has_variable = spec_exch_stand }}
					NOT = {{ has_variable = spec_centre_score }}
					var:spec_exch_stand < local_var:spec_rv_lo
					var:spec_exch_stand > local_var:spec_rv_hi
					any_country = {{ count = {AI_CAP + 1} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }}
					AND = {{
						has_global_variable = spec_rv_round
						global_var:spec_rv_round <= 1
						spec_rv_rope <= {AI_CUT}
						scope:spec_rv_ai_me = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_keep target = prev }} }} }}
					}}
				}}
			}}
			save_temporary_scope_as = spec_rv_x
			scope:spec_rv_ai_me = {{ remove_list_variable = {{ name = spec_rv_chosen target = scope:spec_rv_x }} }}
		}}
		spec_rv_count = yes
		while = {{
			count = {NAMED_HIGH}
			if = {{
				limit = {{
					var:spec_rv_n_chosen < spec_rv_slots
					any_country = {{ is_country_alive = yes {exch} NOT = {{ this = scope:spec_rv_ai_me }} NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} var:spec_exch_stand >= local_var:spec_rv_lo var:spec_exch_stand <= local_var:spec_rv_hi spec_rv_rope >= {AI_REACH} NOT = {{ any_country = {{ count = {AI_CAP} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }}
				}}
				ordered_country = {{
					limit = {{ is_country_alive = yes {exch} NOT = {{ this = scope:spec_rv_ai_me }} NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} var:spec_exch_stand >= local_var:spec_rv_lo var:spec_exch_stand <= local_var:spec_rv_hi spec_rv_rope >= {AI_REACH} NOT = {{ any_country = {{ count = {AI_CAP} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }}
					order_by = spec_rv_ai_pick_v
					save_scope_as = target
				}}
				spec_rv_choose = yes
			}}
		}}
	}}
}}

"""


def pass_(t="\t"):
    """In centres' monthly ranking pass: old saves' one-rival state goes; players' rows are rebuilt; once a year the
    contest, then the AI's actions."""
    old = "".join(f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = {n} }}\n{t}\t\tremove_variable = {n}\n{t}\t}}\n" for n in OLD_VARS)
    return f"""{t}# rival Exchanges (rivals.py): an old save's single named rival becomes a named rival; the rest of its state goes
{t}every_country = {{
{t}	limit = {{ OR = {{ {" ".join(f"has_variable = {n}" for n in OLD_VARS)} }} }}
{t}	if = {{
{t}		limit = {{
{t}			exists = var:spec_rival
{t}			var:spec_rival = {{ is_country_alive = yes }}
{t}			NOT = {{ this = var:spec_rival }}
{t}		}}
{t}		var:spec_rival = {{ save_scope_as = target }}
{t}		if = {{
{t}			limit = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:target }} }} }}
{t}			add_to_variable_list = {{ name = spec_rv_chosen target = scope:target }}
{t}		}}
{t}	}}
{old}{t}}}
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_rv_round }} }}
{t}	set_global_variable = {{ name = spec_rv_round value = 0 }}
{t}}}
{t}every_country = {{
{t}	limit = {{ has_variable_list = spec_rv_chosen }}
{t}	spec_rv_count = yes
{t}	spec_rv_sour = yes
{t}}}
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_rival_year }} }}
{t}	set_global_variable = {{ name = spec_rival_year days = 365 }}
{t}	spec_rv_ai_pick = yes
{t}	if = {{
{t}		limit = {{ has_global_variable = spec_rival_started }}
{t}		change_global_variable = {{ name = spec_rv_round add = 1 }}
{t}		if = {{
{t}			limit = {{ global_var:spec_rv_round >= {ROUND} }}
{t}			spec_rival_contest = yes
{t}			set_global_variable = {{ name = spec_rv_round value = 0 }}
{t}		}}
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
					remove_variable = spec_rv_raider
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
"""


def sguis():
    act = "".join(f"\nspec_sgui_rv_{a} = {{\n\tscope = country\n\tis_valid = {{ spec_can_rv_{a} = yes }}\n\teffect = {{ spec_rv_{a} = yes }}\n}}\n"
                  for a in ACTIONS + ("hold", "shore"))
    tests = {"pair": "spec_rv_pair = yes", "out": "spec_rv_chose = yes", "in": "spec_rv_chosen_by = yes",
             **{k: f"is_target_in_variable_list = {{ name = spec_rv_{k} target = scope:target }}" for k in ("won", "lost", "tied")},
             "locked": "is_target_in_variable_list = { name = spec_rv_keep target = scope:target }",
             "big": "is_target_in_variable_list = { name = spec_rv_big target = scope:target }",
             "shield": "is_target_in_variable_list = { name = spec_rv_shield target = scope:target }",
             "shielded": "scope:target = { is_target_in_variable_list = { name = spec_rv_shield target = root } }",
             "bitter": '"relations(scope:target)" <= relations_threshold:poor',  # a loser loses BITTER times more
             **{f"push_{k}": f"is_target_in_variable_list = {{ name = spec_rv_push_{k} target = scope:target }}" for k in range(1, PUSHES + 1)},
             **{f"pushed_{k}": f"scope:target = {{ is_target_in_variable_list = {{ name = spec_rv_push_{k} target = root }} }}"
                for k in range(1, PUSHES + 1)},
             **{f"cd_{a}": f"is_target_in_variable_list = {{ name = spec_rv_cd_{a} target = scope:target }}" for a in ACTIONS + ("hold", "shore")}}

    act += ("\nspec_sgui_rv_toggle = {\n\tscope = country\n\tis_shown = {\n\t\tNOT = { this = scope:target }\n"
            "\t\tOR = {\n\t\t\tspec_rv_chose = yes\n\t\t\tscope:target = { has_variable = spec_exch_stand }\n\t\t}\n\t}\n"
            "\tis_valid = { spec_can_rv_toggle = yes }\n"
            "\teffect = {\n\t\tif = {\n\t\t\tlimit = { spec_rv_chose = yes spec_can_rv_end = yes }\n\t\t\tspec_rv_end = yes\n\t\t}\n"
            "\t\telse_if = {\n\t\t\tlimit = { spec_rv_chose = no spec_can_rv_choose = yes }\n\t\t\tspec_rv_choose = yes\n\t\t}\n\t}\n}\n"
            "\nspec_sgui_rv_end = {\n\tscope = country\n\tis_shown = { spec_rv_chose = yes }\n"
            "\tis_valid = { spec_can_rv_end = yes }\n\teffect = { spec_rv_end = yes }\n}\n")
    return act + "".join(f"\nspec_sgui_rv_is_{k} = {{\n\tscope = country\n\tis_shown = {{ {t} }}\n}}\n" for k, t in tests.items())


def picture():
    """The rival event's picture: the mod's painting once it exists, else vanilla's videos by region."""
    if icons.has("picture_rival"):
        return f'\tevent_image = {{\n\t\ttexture = "{icons.path("picture_rival")}"\n\t}}\n'
    return __import__("stories").pictures({"west": "europenorthamerica_capitalists_meeting", "mideast": "middleeast_upperclass_party"})


def events():
    pick = lambda code, ok: f"var:spec_rv_hit ?= {code} var:spec_rv_hit_ok ?= {ok}"
    descs = [(1, 1), (1, 0), (2, 1), (3, 1), (3, -1)]
    desc = "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_rival.1.d{c}{'n' if o < 0 else o}\n"
                   f"\t\t\t\ttrigger = {{ {pick(c, o)} }}\n\t\t\t}}\n" for c, o in descs)
    back = " ".join(f"AND = {{ var:spec_rv_hit = {i} spec_rv_pay_{a} = yes }}" for i, a in enumerate(ACTIONS, 1))
    do = "".join(f"\t\tif = {{\n\t\t\tlimit = {{ var:spec_rv_hit = {i} }}\n\t\t\tcustom_tooltip = spec_rival.1.a_{i}\n"
                 f"\t\t\tspec_rv_{a} = yes\n\t\t}}\n" for i, a in enumerate(ACTIONS, 1))
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
{picture()}	icon = "gfx/interface/icons/event_icons/event_trade.dds"
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
{do}
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

""" for n in range(1, SLOTS + 1)) + """spec_rv_upkeep = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_newspaper_negative.dds
	country_influence_add = -1
}
"""


def build(write):
    write("common/scripted_triggers/spec_rival_triggers.txt", triggers())
    write("common/script_values/spec_rival_values.txt", values())
    write("common/scripted_effects/spec_rival_effects.txt", effects())
    write("common/scripted_guis/spec_rival_sguis.txt", sguis())
    write("events/spec_rival_events.txt", events())
    write("common/static_modifiers/spec_rival_modifiers.txt", MODIFIERS)


# -- interface --------------------------------------------------------------------------------------------------------

ROW_H = 44  # a row: the contest's result over its bar
# columns, (x, width): flag and name | the contest | actions (4 tariff items, then the toggle on our rivals' rows)
C_NAME, C_SCORE, C_ACT = (0, 150), (152, 184), (342, W - 342)
BANDS = ("BIGWIN", "WIN", "DRAW", "LOSS", "BIGLOSS")  # the five results, left (ours) to right
BAR = "gfx/interface/progressbar"
SCORE = lambda who: f"{who}.Var('spec_centre_score').GetValue"


def _item(tooltip, texture, call, selected="no", lift=False, badge=None, used=None):
    """One icon button as vanilla's tariff control draws them (levers._item): framed while selected, greyed out when
    it can't be used. The selected icon sits on top as a passive marker, so the click goes to the button under it.
    badge: a number shown on its corner while selected (the months the action has left on them). used: framed too,
    not greyed, while it waits out its cooldown, so a used action reads as done rather than unavailable."""
    running = selected
    if used:
        selected = used if selected == "no" else f"Or({selected}, {used})"
    lifted = (f'\n\t\tenabled = "[{call('IsValid')}]"\n\t\tonclick = "[{call('Execute')}]"\n\t\tusing = decrease_button_sound'
              if lift else "")
    mark = (f"""	textbox = {{
		visible = "[{running}]"
		position = {{ -2 -1 }}
		autoresize = yes
		parentanchor = bottom|right
		alwaystransparent = yes
		using = fontsize_small
		raw_text = "#v [{badge}|0]#!"
	}}
""" if badge else "")
    return f"""set_level_bar_item = {{
{mark}
	tooltip = "{tooltip}"
	blockoverride "button_texture" {{
		texture = "{texture}"
	}}
	blockoverride "click" {{
		enabled = "[{call('IsValid')}]"
		onclick = "[{call('Execute')}]"
		using = increase_button_sound
	}}
	blockoverride "is_selected_visibility" {{
		visible = {selected if selected == "no" else f'"[{selected}]"'}
	}}
	blockoverride "selected_texture_size" {{
		size = {{ 28 28 }}{lifted}
	}}
	blockoverride "is_clickable_alpha" {{
		alpha = "[TransparentIfFalse({call('IsValid') if not used else f"Or({call('IsValid')}, {used})"})]"
	}}
}}
"""


def _strip(items, x, visible=None):
    vis = f'\tvisible = "[{visible}]"\n' if visible else ""
    return (f"flowcontainer = {{\n\tusing = set_level_bar_background\n\tignoreinvisible = yes\n\tposition = {{ {x} 0 }}\n"
            f"\tparentanchor = vcenter\n{vis}{ind(items, 1)}}}\n")


def _toggle(x=None):
    """Rival them, or end it: as vanilla's subsidize toggle (building_subsidize_toggle), a round action button with a
    silhouette of our rival icon while off, and the icon in colour on vanilla's rotating glow while on. Always enabled,
    since the game greys a disabled button: the toggle's effect itself refuses a locked rivalry, its tooltip says why."""
    # ponytail: icon sizes matched by eye-maths: a 21px rival icon draws its object at ~18px, as the 22px Specialities
    # icons do; repaint-independent normalising in icons.build if more families need matching
    call = lambda what: CALL.format("rv_toggle", what)
    on = shown("rv_is_out")
    pos = f"\tposition = {{ {x} 0 }}\n" if x is not None else ""
    side = lambda vis, tex, sound: f"""	button_icon_round_action = {{
		visible = "[{vis}]"
		size = {{ 100% 100% }}
		onclick = "[{call('Execute')}]"
		tooltip = "SPEC_RV_TOGGLE_TT"
		using = tooltip_se
		using = {sound}
		blockoverride "icon" {{
			texture = "{tex}"
		}}
		blockoverride "icon_size" {{
			size = {{ 21 21 }}
		}}
	}}
"""
    return f"""widget = {{
{pos}	size = {{ 32 32 }}
	parentanchor = vcenter
	visible = "[{call('IsShown')}]"
	icon = {{
		visible = "[{on}]"
		using = rotate_glow_blue
		size = {{ 130% 130% }}
		alwaystransparent = yes
		parentanchor = center
		using = default_fade_in_out
	}}
{side(on, icons.RIVALRY, "icon_toggle_single_off_sound")}{side(f"Not({on})", icons.RIVALRY_OFF, "icon_toggle_single_on_sound")}}}
"""


def _cell(c, key, align="center", small=False, visible=None):
    vis = f'\tvisible = "[{visible}]"\n' if visible else ""
    return (f"textbox = {{\n{vis}\tposition = {{ {c[0]} 0 }}\n\tsize = {{ {c[1]} {ROW_H} }}\n\tparentanchor = vcenter\n"
            f"\tmargin = {{ 8 0 }}\n\talign = {align}|nobaseline\n\telide = right\n"
            + ("\tusing = fontsize_small\n" if small else "") + f"\ttext = \"{key}\"\n}}\n")


def _name(own=False):
    """Flag and name, which opens the country, as the Leading Exchanges rows."""
    return f"""tiny_flag = {{
	position = {{ 6 0 }}
	parentanchor = vcenter
}}
button = {{
	position = {{ 40 0 }}
	size = {{ {C_NAME[1] - 64} 30 }}
	parentanchor = vcenter
	using = clean_button
	onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
	tooltipwidget = {{
		FancyTooltip_Country = {{}}
	}}
	textbox = {{
		size = {{ 100% 100% }}
		margin_left = 8
		align = nobaseline
		parentanchor = vcenter
		elide = right
		alwaystransparent = yes
		text = "{'SPEC_RV_US_NAME' if own else '[Country.GetNameNoFormatting]'}"
	}}
}}
"""


# the contest bar from our side (rivals' spec_rv_rope): the score lead as a share of the higher, plus our pushes less theirs


def _sum(terms):
    out = terms[0]
    for x in terms[1:]:
        out = f"Add_CFixedPoint({out}, {x})"
    return out


def rope():
    """The contest from our side, -1 to 1 (rivals' spec_rv_rope), as spec_rv_ui stores it on the row's country."""
    return f"{THEM}.Var('spec_rv_ui_p').GetValue"


def pushes(key):
    return f"{THEM}.Var('spec_rv_ui_{'us' if key == 'push' else 'them'}').GetValue"


PAIR = f"{THEM}.Var('spec_rv_ui_p').IsSet"  # both have an Exchange, so there is a contest


def _score():
    """The contest as a tug of war, drawn as the mod's Market Confidence bar (market_tab.tier_scale) on vanilla's
    double direction bar: the result it would settle at now above it, then from the centre line the fill slides
    green toward us (left) or red toward them, with vanilla's glow and, while one side has pushed more, the changed
    value chevrons running its way. Dividers part the five results, the decisive ends are tinted, and vanilla's
    active level frame rings the one it sits in. Without their Exchange there is no contest."""
    import interest_list as il
    x, w = C_SCORE
    bw = w - 6
    at = f"Subtract_CFixedPoint({fx(50)}, Multiply_CFixedPoint({fx(50)}, {rope()}))"  # 0 all ours, 50 even, 100 theirs
    ours_more = f"GreaterThan_CFixedPoint({pushes('push')}, {pushes('pushed')})"
    theirs_more = f"GreaterThan_CFixedPoint({pushes('pushed')}, {pushes('push')})"
    edges = [0, 50 - 50 * DECISIVE, 50 - 50 * DRAW, 50 + 50 * DRAW, 50 + 50 * DECISIVE, 100]
    px = lambda e: round(bw * e / 100)

    def half(left, texture, vis):
        side = "left" if left else "right"
        fill = f"{BAR}/{texture}.dds"
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
		value = "[FixedPointToFloat({at})]"
		marker = {{
			widget = {{
				size = {{ 100% 100% }}
				icon = {{
					size = {{ 24 100% }}
					widgetanchor = {side}
					alpha = 0.7
{'					mirror = horizontal' + chr(10) if left else ''}					texture = "{BAR}/{texture}_glow.dds"
					icon = {{
						size = {{ 3 100% }}
						parentanchor = {side}
						texture = "{BAR}/{texture}_glow_line.dds"
					}}
				}}
{ind(il.chevrons(theirs_more, ours_more, 0.25, side, duration=3), 4)}			}}
		}}
	}}
}}
"""
    tint = lambda a, b, tex: f"""icon = {{
	position = {{ {px(a)} 0 }}
	size = {{ {px(b) - px(a)} 100% }}
	texture = "{BAR}/{tex}.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alpha = 0.18
}}
"""
    dividers = "".join(f"""icon = {{
	position = {{ {px(e) - 1} 1 }}
	size = {{ 3 12 }}
	texture = "{BAR}/progressbar_center_divider.dds"
	texture_density = 2
	alpha = 0.5
}}
""" for e in edges[1:-1] if e != 50)
    inside = lambda a, b: (f"And(GreaterThanOrEqualTo_CFixedPoint({at}, {fx(a)}), LessThan_CFixedPoint({at}, {fx(b)}))" if b < 100
                           else f"GreaterThanOrEqualTo_CFixedPoint({at}, {fx(a)})")
    active = "".join(f"""icon = {{
	visible = "[{inside(a, b)}]"
	position = {{ {px(a)} 0 }}
	size = {{ {px(b) - px(a)} 100% }}
	texture = "{BAR}/progressbar_active_level.dds"
	spriteType = Corneredstretched
	spriteborder = {{ 6 6 }}
	texture_density = 2
}}
""" for a, b in zip(edges, edges[1:]))
    # each result's own section answers to the mouse with what that result would do; on the row itself, as a
    # tooltip nested deeper in the cell lost the row's Country
    tiers = "".join(f"""widget = {{
	visible = "[{PAIR}]"
	position = {{ {x + 3 + px(a)} 0 }}
	size = {{ {px(b) - px(a)} {ROW_H} }}
	tooltip = "SPEC_RV_TIER_{k}_TT"
}}
""" for (a, b), k in zip(zip(edges, edges[1:]), BANDS))
    return f"""widget = {{
	visible = "[{PAIR}]"
	position = {{ {x} 0 }}
	size = {{ {w} {ROW_H} }}
	tooltip = "SPEC_RV_SCORE_TT"
	textbox = {{
		position = {{ 0 4 }}
		size = {{ 100% 16 }}
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_RV_NOW"
	}}
	widget = {{
		position = {{ 3 22 }}
		size = {{ {bw} 14 }}
		background = {{
			texture = "{BAR}/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
			using = progressbar_texture_properties
		}}
		background = {{
			texture = "{BAR}/progressbar_frame.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
			margin = {{ 3 3 }}
		}}
{ind(tint(0, edges[1], "progressbar_green") + tint(edges[4], 100, "progressbar_bad"), 2)}{ind(half(True, "progressbar_green", f"LessThan_CFixedPoint({at}, {fx(50)})"), 2)}{ind(half(False, "progressbar_bad", f"GreaterThan_CFixedPoint({at}, {fx(50)})"), 2)}{ind(dividers + active, 2)}		widget = {{
			size = {{ 3 100% }}
			parentanchor = center
			background = {{
				texture = "{BAR}/progressbar_center_divider.dds"
				spriteType = Corneredstretched
				spriteborder = {{ 0 0 }}
				texture_density = 2
				margin = {{ 0 1 }}
			}}
		}}
	}}
}}
{tiers}{_cell(C_SCORE, "SPEC_RV_SCORE_OFF", small=True, visible=f"Not({PAIR})")}"""


# a row lights up under the mouse, as vanilla's list entries do
HOVER = """state = {
	name = _mouse_hierarchy_enter
	on_start = "[PdxGuiWidget.AccessChild('spec_rv_hover').TriggerAnimation('in')]"
}
state = {
	name = _mouse_hierarchy_leave
	on_start = "[PdxGuiWidget.AccessChild('spec_rv_hover').TriggerAnimation('out')]"
}
icon = {
	name = "spec_rv_hover"
	size = { 100% 100% }
	alwaystransparent = yes
	using = entry_bg_simple
	alpha = 0
	state = {
		name = in
		alpha = 0.6
		duration = 0.1
		using = Animation_Curve_Default
	}
	state = {
		name = out
		alpha = 0
		duration = 0.15
		using = Animation_Curve_Default
	}
}
divider_clean = {
	parentanchor = bottom
	position = { 0 2 }
}
"""


def _list(model, row, empty):
    some = f"GreaterThan_int32(GetDataModelSize({model}), '(int32)0')"
    return f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	datamodel = "[{model}]"
	item = {{
		widget = {{
			size = {{ {W} {ROW_H} }}
			datacontext = "[Scope.GetCountry]"
			tooltip = "SPEC_RV_ROW_TT"
{ind(HOVER + row, 3)}		}}
	}}
}}
textbox = {{
	visible = "[Not({some})]"
	size = {{ {W} {ROW_H} }}
	parentanchor = hcenter
	margin = {{ 12 0 }}
	align = left|nobaseline
	text = "{empty}"
}}
"""


def _lock(x):
    """A small lock on the toggle's corner while the rivalry is in its first year and cannot be ended."""
    return f"""icon = {{
	visible = "[{shown('rv_is_locked')}]"
	position = {{ {x + 20} 4 }}
	size = {{ 14 14 }}
	alwaystransparent = yes
	texture = "gfx/interface/buttons/button_icons/lock.dds"
}}
"""


# what rival actions run on our market: (variable, icon, months it runs, who did it)
CHIPS = (("raid", "raid", RAID_MONTHS, "spec_rv_raider"), ("lure", "lure", LURE_MONTHS, "spec_rv_lurer"))


def _us_row(var, pic, months, by):
    """One action running on us, as a table row: its icon and who did it, what it does, and its months on a bar."""
    left = f"{US}.Var('spec_rv_{var}').GetValue"
    return f"""widget = {{
	visible = "[{US}.Var('spec_rv_{var}').IsSet]"
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_RV_US_{var.upper()}_TT"
{ind(HOVER, 1)}	icon = {{
		position = {{ 8 0 }}
		size = {{ 32 32 }}
		parentanchor = vcenter
		texture = "{icons.path('rival_' + pic)}"
	}}
	textbox = {{
		position = {{ 48 4 }}
		size = {{ 250 20 }}
		align = left|nobaseline
		elide = right
		text = "SPEC_RV_US_{var.upper()}"
	}}
	textbox = {{
		position = {{ 48 23 }}
		size = {{ 250 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_RV_US_{var.upper()}_FX"
	}}
	textbox = {{
		position = {{ 306 4 }}
		size = {{ {W - 318} 18 }}
		align = right|nobaseline
		using = fontsize_small
		text = "SPEC_RV_US_LEFT_{var.upper()}"
	}}
	widget = {{
		position = {{ 306 24 }}
		size = {{ {W - 318} 12 }}
		background = {{
			texture = "{BAR}/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
			using = progressbar_texture_properties
		}}
		progressbar = {{
			size = {{ 100% 100% }}
			progresstexture = "{BAR}/progressbar_bad.dds"
			noprogresstexture = "{CLEAR}"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
			using = progressbar_texture_properties
{ind(SLIDE, 3)}			min = 0
			max = {months}
			value = "[FixedPointToFloat({left})]"
		}}
		background = {{
			texture = "{BAR}/progressbar_frame.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
			margin = {{ 3 3 }}
		}}
	}}
}}
"""


# the last move against us (spec_rv_log, kept a year) when it left nothing running, so had no row of its own: a Press
# Campaign, or a Bear Raid that failed and hit them
_hit = lambda n: f"EqualTo_CFixedPoint({US}.Var('spec_rv_hit').GetValueWithDefault({fx(0)}), {fx(n)})"
_hit_ok = lambda n: f"EqualTo_CFixedPoint({US}.Var('spec_rv_hit_ok').GetValueWithDefault({fx(0)}), {fx(n)})"
LAST = f"And({US}.Var('spec_rv_hit_recent').IsSet, Or({_hit(3)}, And({_hit(1)}, Not({_hit_ok(1)}))))"


def _last_row():
    pics = "".join(f"""	icon = {{
		visible = "[{_hit(i)}]"
		position = {{ 8 0 }}
		size = {{ 32 32 }}
		parentanchor = vcenter
		texture = "{icons.path('rival_' + a)}"
	}}
""" for i, a in enumerate(ACTIONS, 1))
    return f"""widget = {{
	visible = "[{LAST}]"
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_RV_US_LAST_TT"
{ind(HOVER, 1)}{pics}	textbox = {{
		position = {{ 48 4 }}
		size = {{ 250 20 }}
		align = left|nobaseline
		elide = right
		text = "SPEC_RV_US_LAST"
	}}
	textbox = {{
		position = {{ 48 23 }}
		size = {{ {W - 60} 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_RV_US_LAST_FX"
	}}
	textbox = {{
		position = {{ 306 4 }}
		size = {{ {W - 318} 18 }}
		align = right|nobaseline
		using = fontsize_small
		text = "SPEC_RV_US_LAST_WHEN"
	}}
}}
"""


def _ours():
    """Our Market: a folding section as the two tables, one row per rival action running on us, then the last move
    against us that left nothing running, or a line saying there is none. Its header says when the contests next
    settle. Shore Up against a rival is in that rival's row."""
    some = LAST
    for v, *_ in CHIPS:  # the GUI's Or takes two
        some = f"Or({US}.Var('spec_rv_{v}').IsSet, {some})"
    rows = "".join(_us_row(*c) for c in CHIPS) + _last_row()
    body = f"""flowcontainer = {{
	direction = vertical
	parentanchor = hcenter
	ignoreinvisible = yes
{ind(rows, 1)}}}
textbox = {{
	visible = "[Not({some})]"
	size = {{ {W} {ROW_H} }}
	parentanchor = hcenter
	margin = {{ 12 0 }}
	align = left|nobaseline
	text = "SPEC_RV_CARD_NONE"
}}
"""
    return section("SPEC_RV_CARD_TITLE", "spec_hide_rv_us", body, right="SPEC_RV_ROUND", tooltip="SPEC_RV_US_TT")


def _shored_badge():
    """A small shield after their name while they are shored up against us."""
    return f"""icon = {{
	visible = "[{shown('rv_is_shielded')}]"
	position = {{ {C_NAME[1] - 22} 0 }}
	size = {{ 20 20 }}
	parentanchor = vcenter
	texture = "{icons.path('rival_shore')}"
	tooltip = "SPEC_RV_SHIELDED_TT"
}}
"""


def block():
    """The Rivalries section: our market (the rival actions running on us, when contests settle), then two
    tables with one layout, each under a folding header: Country | Contest | Actions. An action running on them lights
    its button with the months it has left. Rivalries are named and ended in the Leading Exchanges list. Rules live
    in the Rivalries header's tooltip, detail in each cell's."""
    running = {"raid": "raid", "lure": "lure"}  # actions that leave something running on the target
    acts = "".join(_item(f"SPEC_RV_{a.upper()}_TT", icons.path("rival_" + a), lambda what, a=a: CALL.format("rv_" + a, what),
                         f"{THEM}.Var('spec_rv_{running[a]}').IsSet" if a in running else "no",
                         badge=f"{THEM}.Var('spec_rv_{running[a]}').GetValue" if a in running else None,
                         used=shown(f"rv_is_cd_{a}"))
                   for a in ACTIONS + ("hold",))
    acts += _item("SPEC_RV_SHORE_TT", icons.path("rival_shore"), lambda what: CALL.format("rv_shore", what), shown("rv_is_shield"),
                  used=shown("rv_is_cd_shore"))
    in_row = _name() + _shored_badge() + _score() + _strip(acts, C_ACT[0])
    out_row = in_row  # the rivalry itself is named and ended from the Leading Exchanges list (marker)
    outs, ins = f"{US}.GetList('spec_rv_outs')", f"{US}.GetList('spec_rv_ins')"
    h = heads([(x, w, k, "center" if i else "left", bool(i)) for i, ((x, w), k) in
               enumerate([(C_NAME, "SPEC_RV_COL_EXCH"), (C_SCORE, "SPEC_RV_COL_SCORE"), (C_ACT, "SPEC_RV_COL_ACT")])])
    return (_ours()
            + section("SPEC_RV_SUB_OUT", "spec_hide_rv_out", h + _list(outs, out_row, "SPEC_RV_EMPTY_OUT"), right="SPEC_RV_SUB_OUT_RIGHT")
            + section("SPEC_RV_SUB_IN", "spec_hide_rv_in", h + _list(ins, in_row, "SPEC_RV_EMPTY_IN"), right="SPEC_RV_SUB_IN_RIGHT"))


def marker():
    """Leading Exchanges row, Rival column (the row's Country is the listed one): the rivalry icon button, framed
    while we rival them, and a small shield when they rival us."""
    return ind(_toggle(314) + _lock(314) + f"""icon = {{
	visible = "[And(Not(ObjectsEqual(Country.Self, GetPlayer.Self)), {shown('rv_is_in')})]"
	position = {{ 350 0 }}
	size = {{ 22 22 }}
	parentanchor = vcenter
	texture = "{icons.path('rival_in')}"
	tooltip = "SPEC_RV_MARK_TT"
}}
""", 2)


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
    rule = (f"An [concept_spec_exchange] rivals whichever Exchanges it likes, apart from diplomatic rivalries. Each rival has an influence "
            f"maintenance cost by its Standing, from #N {UPKEEP[0]}#! to #N {UPKEEP[-1]}#!, and a rivalry cannot be ended in its first year.\\n\\n"
            f"Every #v {ROUND}#! years each rivalry is settled like a tug of war. The bar starts from the two [Concept('concept_spec_financial_centre','$concept_spec_exchange$')] scores, "
            f"and each action that works pushes it #v {pc(PUSH)}#! toward its side, up to #v {PUSHES}#! pushes each. Near the middle it is a draw. "
            f"A win takes #P {pc(WIN_X * STAKE / CALM)}#! trust from the loser; past #v {pc(DECISIVE)}#! a decisive win takes #P {pc(BIG_X * STAKE / CALM)}#! "
            f"and #P {pc(LURE_SHARE)}#! of the loser's [concept_investment_pool] income for {LURE_MONTHS} months. "
            f"Across a gap in Standing, a win by the lower Exchange pays more and a win by the higher pays less. On poor relations or worse the loser loses #N x{BITTER:g}#!.\\n\\n"
            "Rival actions work both ways: against Exchanges we rival and Exchanges rivaling us. Each can be used once a year per rival. "
            f"Against a larger Exchange they cost more and do less, from #v x{VS_LO:g}#! to #v x{VS_HI:g}#!. "
            "In a [concept_spec_financial_panic], fleeing money goes to a rival first.")
    why = lambda sg: f"[AddLocalizationIf(Not({CALL.format(sg, 'IsValid')}), '{'SPEC_RV_WHY_' + sg.upper()}')]"
    head = lambda title: f"#header {title}#!\\n$TOOLTIP_DELIMITER$\\n"
    vs = lambda them: (f"Min_CFixedPoint({fx(VS_HI)}, Max_CFixedPoint({fx(VS_LO)}, Divide_CFixedPoint({num(them, 'spec_centre_score')}, "
                       f"Max_CFixedPoint({num(US, 'spec_centre_score')}, {fx(1)}))))")
    heft = lambda them: f"Divide_CFixedPoint({fx(1)}, {vs(them)})"
    EV = "SCOPE.sCountry('target').MakeScope"
    cost_of = lambda them: f"@money![Multiply_CFixedPoint({US}.ScriptValue('spec_rv_cost_base'), {vs(them)})|D]"
    debt_of = lambda them: f"#N @money![Multiply_CFixedPoint({US}.ScriptValue('spec_rv_lure_debt_base'), {vs(them)})|D]#!"
    cost, debt, cost_ev, debt_ev = cost_of(THEM), debt_of(THEM), cost_of(EV), debt_of(EV)
    hit = lambda them: f"[Multiply_CFixedPoint({fx(RAID_HIT)}, {heft(them)})|1]"
    share = lambda them: f"[Multiply_CFixedPoint({fx(LURE_SHARE)}, {heft(them)})|%0]"
    dent = lambda them: f"[Multiply_CFixedPoint({fx(round(PRESS_TRUST / CALM, 4))}, {heft(them)})|%0]"
    upk = f"{US}.ScriptValue('spec_rv_upkeep_total')"
    yr = lambda n: "1 year" if n == 1 else f"{n} years"
    stand_is = lambda t: f"EqualTo_CFixedPoint({num(THEM, 'spec_exch_stand')}, {fx(t)})"
    tier_cost = (f"[SelectLocalization({stand_is(3)}, 'SPEC_RV_COST_3', SelectLocalization({stand_is(2)}, 'SPEC_RV_COST_2', "
                 f"SelectLocalization({stand_is(1)}, 'SPEC_RV_COST_1', 'SPEC_RV_COST_0')))]")
    r = rope()
    past = lambda f: f"GreaterThanOrEqualTo_CFixedPoint({r}, {fx(f)})"
    bands = (f"SelectLocalization({past(DECISIVE)}, 'SPEC_RV_BAND_BIGWIN', SelectLocalization({past(DRAW)}, 'SPEC_RV_BAND_WIN', "
             f"SelectLocalization(GreaterThan_CFixedPoint({r}, {fx(-DRAW)}), 'SPEC_RV_BAND_DRAW', "
             f"SelectLocalization(GreaterThan_CFixedPoint({r}, {fx(-DECISIVE)}), 'SPEC_RV_BAND_LOSS', 'SPEC_RV_BAND_BIGLOSS'))))")
    left = f"Subtract_CFixedPoint({fx(ROUND)}, GetGlobalVariable('spec_rv_round').GetValue)"
    st = lambda who: num(who, 'spec_exch_stand')
    stake = lambda w, l: (f"Select_CFixedPoint(GreaterThan_CFixedPoint({st(w)}, {st(l)}), "
                          f"Divide_CFixedPoint({fx(STAKE)}, Add_CFixedPoint(Subtract_CFixedPoint({st(w)}, {st(l)}), {fx(1)})), "
                          f"Multiply_CFixedPoint({fx(STAKE)}, Add_CFixedPoint(Max_CFixedPoint(Subtract_CFixedPoint({st(l)}, {st(w)}), {fx(0)}), {fx(1)})))")
    # trust as a share of CALM, as the Leading Exchanges show it
    gain = lambda w, l, k: f"Divide_CFixedPoint(Multiply_CFixedPoint({stake(w, l)}, {fx(k)}), {fx(CALM)})"
    loss = lambda w, l, k: (f"Multiply_CFixedPoint(Multiply_CFixedPoint({gain(w, l, k)}, {l}.ScriptValue('spec_exch_loss')), "
                            f"Select_CFixedPoint({shown('rv_is_bitter')}, {fx(BITTER)}, {fx(1)}))")
    swing = lambda k, we_win: (f"Our Trust: #P +[{gain(US, THEM, k)}|%0]#!\\nTheir Trust: #N -[{loss(US, THEM, k)}|%0]#!" if we_win else
                               f"Our Trust: #N -[{loss(THEM, US, k)}|%0]#!\\nTheir Trust: #P +[{gain(THEM, US, k)}|%0]#!")
    lured = lambda text: f"\\n{text}, {LURE_MONTHS} months"
    effect = {"BIGWIN": swing(BIG_X, True) + lured(f"Their [concept_investment_pool] Income: #P {pc(LURE_SHARE)}#! to us"),
              "WIN": swing(WIN_X, True), "DRAW": "No change",
              "LOSS": swing(WIN_X, False), "BIGLOSS": swing(BIG_X, False) + lured(f"Our [concept_investment_pool] Income: #N {pc(LURE_SHARE)}#! to them")}
    tiers = [(f"SPEC_RV_TIER_{k}_TT", f"#header $SPEC_RV_BAND_{k}$#!\\n$TOOLTIP_DELIMITER$\\n{effect[k]}\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_SCORE_BODY$")
             for k in BANDS]
    lines = [
        (f"SPEC_H_RIVAL", "Rivalries"),
        ("SPEC_H_RIVAL_TT", "#header Rivalries#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RIVAL_RULE$"),
        ("SPEC_H_RIVAL_RIGHT", f"#N -[{upk}|0]#! @inf!"),
        ("SPEC_RIVAL_RULE", rule),
        ("SPEC_RV_SUB_OUT", "Exchanges We Rival"), ("SPEC_RV_SUB_OUT_RIGHT", f"#v [{num(US, 'spec_rv_n_out')}|0]#!"),
        ("SPEC_RV_SUB_IN", "Exchanges Rivaling Us"), ("SPEC_RV_SUB_IN_RIGHT", f"#v [{num(US, 'spec_rv_n_in')}|0]#!"),
        ("SPEC_RV_COL_EXCH", "$concept_country$"),
        ("SPEC_RV_COL_SCORE", "Contest"), ("SPEC_RV_COL_SCORE_TT", f"Where the contest stands: our score against theirs, then each side's pushes. It settles every #v {ROUND}#! years"),
        ("SPEC_RV_COL_ACT", "Actions"), ("SPEC_RV_COL_ACT_TT", "Our actions against them. Each that works pushes the contest our way"),
        ("SPEC_RV_COL_LAST", "Their Last Action"), ("SPEC_RV_COL_LAST_TT", "Their last action against us"),
        ("SPEC_RV_SCORE_TT", "#header [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_SCORE_BODY$"),
        ("SPEC_RV_SCORE_BODY", f"Now: [{bands}]\\nScores: #v {score(US)}#! to #v {score(THEM)}#!\\n"
                               f"Pushes: #P [{pushes('push')}|0]#! ours, #N [{pushes('pushed')}|0]#! theirs\\nSettles in #v [{left}|0]#! years"),
        ("SPEC_RV_ROUND", f"#weak Contests settle in#! #v [{left}|0]#! #weak years#!"),
        ("SPEC_RV_BAND_BIGWIN", "#P Decisive Win#!"), ("SPEC_RV_BAND_WIN", "#P Win#!"), ("SPEC_RV_BAND_DRAW", "Draw"),
        ("SPEC_RV_BAND_LOSS", "#N Loss#!"), ("SPEC_RV_BAND_BIGLOSS", "#N Decisive Loss#!"),
        ("SPEC_RV_SCORE_OFF", "#weak No Exchange#!"),
        ("SPEC_RV_NOW", f"[{bands}]"),
        *tiers,
        ("SPEC_RV_CARD_TITLE", "Rival Actions on Us"),
        ("SPEC_RV_US_RAID", f"#b Bear Raid#! by [{var(US, 'spec_rv_raider')}.GetCountry.GetNameNoFormatting]"),
        ("SPEC_RV_US_RAID_FX", f"[concept_spec_market_confidence] #N -[{num(US, 'spec_rv_raid_pm')}|1]#! a month"),
        ("SPEC_RV_US_RAID_TT", f"#header Bear Raid on Us#!\\n$TOOLTIP_DELIMITER$\\nBy: [{var(US, 'spec_rv_raider')}.GetCountry.GetName]\\n"
                               f"Effect: [concept_spec_market_confidence] #N -[{num(US, 'spec_rv_raid_pm')}|1]#! a month\\n"
                               f"Months Left: #v [{num(US, 'spec_rv_raid')}|0]#! of {RAID_MONTHS}\\n$TOOLTIP_DELIMITER$\\n"
                               "#weak Shore Up against them in their row to halve their next moves#!"),
        ("SPEC_RV_US_LURE", f"#b Capital Lured#! by [{var(US, 'spec_rv_lurer')}.GetCountry.GetNameNoFormatting]"),
        ("SPEC_RV_US_LURE_FX", f"#N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to them"),
        ("SPEC_RV_US_LURE_TT", f"#header Capital Lured from Us#!\\n$TOOLTIP_DELIMITER$\\nBy: [{var(US, 'spec_rv_lurer')}.GetCountry.GetName]\\n"
                               f"Effect: #N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to them\\n"
                               f"Months Left: #v [{num(US, 'spec_rv_lure')}|0]#! of {LURE_MONTHS}\\n$TOOLTIP_DELIMITER$\\n"
                               "#weak Shore Up against them in their row to halve their next moves#!"),
        ("SPEC_RV_US_LAST", f"#b {act(US)}#! by [{var(US, 'spec_rv_hit_by')}.GetCountry.GetNameNoFormatting]"),
        ("SPEC_RV_US_LAST_FX", f"[SelectLocalization({_hit(1)}, 'SPEC_RV_LAST_FAILED', SelectLocalization({_hit_ok(1)}, 'SPEC_RV_LAST_PRESS', 'SPEC_RV_LAST_EXPOSED'))]"),
        ("SPEC_RV_LAST_FAILED", "#P It failed:#! their own market took the hit"),
        ("SPEC_RV_LAST_PRESS", "Our [concept_spec_exchange] lost trust"),
        ("SPEC_RV_LAST_EXPOSED", "#P Exposed:#! their own trust fell, and relations worsened"),
        ("SPEC_RV_US_LAST_WHEN", "#weak In the last year#!"),
        ("SPEC_RV_US_LAST_TT", "#header Last Move Against Us#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_US_LAST$\\n$SPEC_RV_US_LAST_FX$\\n$TOOLTIP_DELIMITER$\\n"
                               "#weak Shore Up against them in their row to halve their next moves#!"),
        ("SPEC_RV_US_LEFT_RAID", f"#v [{num(US, 'spec_rv_raid')}|0]#! #weak months left#!"),
        ("SPEC_RV_US_LEFT_LURE", f"#v [{num(US, 'spec_rv_lure')}|0]#! #weak months left#!"),
        ("SPEC_RV_CARD_NONE", "#weak No rival actions are running on us#!"),
        ("SPEC_RV_YEAR", f"[SelectLocalization({shown('rv_is_won')}, 'SPEC_RV_YEAR_W', {sel(shown('rv_is_lost'), 'SPEC_RV_YEAR_L', 'SPEC_RV_YEAR_REST')})]"),
        ("SPEC_RV_YEAR_W", f"[{sel(shown('rv_is_big'), 'SPEC_RV_BAND_BIGWIN', 'SPEC_RV_BAND_WIN')}]"),
        ("SPEC_RV_YEAR_L", f"[{sel(shown('rv_is_big'), 'SPEC_RV_BAND_BIGLOSS', 'SPEC_RV_BAND_LOSS')}]"),
        ("SPEC_RV_YEAR_REST", f"[{sel(shown('rv_is_tied'), 'SPEC_RV_TIED', 'SPEC_RV_NONE')}]"),
        ("SPEC_RV_TIED", "Draw"), ("SPEC_RV_NONE", "#weak –#!"),
        ("SPEC_RV_THEIR_LAST", f"[SelectLocalization({by(US, 'Country.Self')}, 'SPEC_RV_THEIRS_IS', 'SPEC_RV_NONE')]"),
        ("SPEC_RV_THEIRS_IS", f"#v {act(US)}#!, {res(US)}"),
        ("SPEC_RV_US_TT", f"#header Rival Actions on Us#!\\n$TOOLTIP_DELIMITER$\\nWhat rival Exchanges are doing to our market now, and for how long. "
                          f"To halve a rival's next moves, Shore Up against them in their row.\\n\\nEvery #v {ROUND}#! years each rivalry's contest settles."),
        ("SPEC_RV_SHIELDED_TT", "#header Shored Up Against Us#!\\n$TOOLTIP_DELIMITER$\\nFor now, our actions against them have half their effect"),
        ("spec_rv_shield_tt", "We are not already shored up against them"),
        ("SPEC_RV_TOGGLE_TT", f"[SelectLocalization({shown('rv_is_out')}, 'SPEC_RV_TOGGLE_TT_ON', 'SPEC_RV_TOGGLE_TT_OFF')]{why('rv_toggle')}"),
        ("SPEC_RV_TOGGLE_TT_OFF", head("Rival [Country.GetNameNoFormatting]") + f"Maintenance: @inf! {tier_cost}\\n"
                                  f"Relations: #N -{REL_HIT}#! now, then #N -{REL_DRIFT}#! a month down to Poor"),
        ("SPEC_RV_TOGGLE_TT_ON", head("Rival of [Country.GetNameNoFormatting]") + f"Maintenance: @inf! {tier_cost}\\n"
                                 f"Relations: #N -{REL_DRIFT}#! a month down to Poor"),
        ("SPEC_RV_WHY_RV_TOGGLE", f"\\n\\n[{CALL.format('rv_toggle', 'BuildTooltip')}]"),
        *((f"SPEC_RV_COST_{t}", f"#N {c}#!") for t, c in enumerate(UPKEEP)),
        ("spec_rv_their_exch_tt", "They have an [concept_spec_exchange]"),
        ("spec_rv_keep_tt", "The rivalry is more than a year old"),
        ("SPEC_RV_EMPTY_OUT", "#weak None. Use the rivalry button in the Leading Exchanges list.#!"),
        ("SPEC_RV_EMPTY_IN", "#weak None#!"),
        ("spec_rv_upkeep", "Rival Exchanges"),
        ("spec_rv_upkeep_desc", "Our [concept_spec_exchange] spends influence keeping up its rivalries."),
        
        ("spec_rv_raid_fx", f"We pay {cost_ev}. Their [concept_spec_market_confidence] falls by #N {hit(EV)}#! over {RAID_MONTHS} months, or ours if it fails."),
        ("spec_rv_lure_fx", f"Our [concept_spec_outstanding_credit] grows by {debt_ev}. For {LURE_MONTHS} months #P {share(EV)}#! of their [concept_investment_pool] income comes to ours."),
        ("spec_rv_press_fx", f"We pay #N {PRESS_INFL}#! influence for {PRESS_MONTHS} months. Their [concept_spec_exchange] loses #N {dent(EV)}#! trust. "
                             f"#N {PRESS_EXPOSE}%#! chance it is exposed: relations #N -{PRESS_REL}#!, our trust #N -{pc(PRESS_TRUST / CALM)}#!."),
        ("spec_rv_hold_fx", f"We pay {cost_ev}. One of their pushes in our contest is undone."),
        ("spec_rv_pushed_tt", "They have pushed our contest their way"),
        ("SPEC_RV_HOLD", "Hold the Line"),
        ("spec_rv_shore_fx", f"We pay {cost_ev}. For {SHORE_MONTHS} months their actions against us have half their effect."),
        ("SPEC_RV_LAST", f"[SelectLocalization({by(THEM, 'GetPlayer.Self')}, 'SPEC_RV_LAST_OURS', "
                         f"{sel(by(US, 'Country.Self'), 'SPEC_RV_LAST_THEIRS', 'SPEC_RV_LAST_NONE')})]"),
        ("SPEC_RV_LAST_OURS", f"Our last action: #v {act(THEM)}#!, {res(THEM)}"),
        ("SPEC_RV_LAST_THEIRS", f"Their last action: #v {act(US)}#!, {res(US)}"),
        ("SPEC_RV_LAST_NONE", "No actions between us yet"),
        ("SPEC_RV_OK", "#P it worked#!"), ("SPEC_RV_FAILED", "#N it failed#!"), ("SPEC_RV_EXPOSED", "#N it was exposed#!"),
        ("SPEC_RV_RAID", "Bear Raid"), ("SPEC_RV_LURE", "Lure Capital"), ("SPEC_RV_PRESS", "Press Campaign"), ("SPEC_RV_SHORE", "Shore Up"),
        ("SPEC_RV_ROW_TT", "#header [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_LAST$"),
        ("SPEC_RV_MARK_TT", "#header They Rival Us#!\\n$TOOLTIP_DELIMITER$\\nTheir [concept_spec_exchange] has made ours its rival."),
        ("spec_rv_pair_tt", "Both countries have an [concept_spec_exchange]"),
        ("spec_rv_exch_tt", "Our country has an [concept_spec_exchange]"),
        ("spec_rv_cd_tt", "We have not used this against them in the last year"),
        ("spec_rv_shore_cd_tt", f"We have not shored up against them in the last #v {SHORE_CD}#! years"),
        ("spec_rv_gold_tt", "Our treasury can pay the cost"),
        ("spec_rv_panic_tt", "Our market is not in a [concept_spec_financial_panic]"),
        ("spec_rv_lured_tt", "No one is luring their capital already"),
        ("spec_rv_infl_tt", f"We have #v {PRESS_INFL}#! influence to spare"),
        ("spec_rv_slots_tt", f"We run fewer than #v {SLOTS}#! press campaigns"),
        ("spec_rv_press_1", "Press Campaign"), ("spec_rv_press_2", "Second Press Campaign"), ("spec_rv_press_3", "Third Press Campaign"),
        *((f"spec_rv_press_{n}_desc", "Newspapers abroad are paid to doubt a rival Exchange.") for n in range(1, SLOTS + 1)),
        ("spec_rival.1.t", "A Rival Moves Against Us"),
        ("spec_rival.1.d11", f"Brokers in [SCOPE.sCountry('target').GetName] sold our securities short all at once. "
                             f"Our [concept_spec_market_confidence] will fall by #N [Multiply_CFixedPoint({num(US, 'spec_rv_raid_pm')}, {fx(RAID_MONTHS)})|1]#! over {RAID_MONTHS} months."),
        ("spec_rival.1.d10", "Brokers in [SCOPE.sCountry('target').GetName] tried to break our market by selling short, and misjudged it. "
                             f"Their own [concept_spec_market_confidence] falls by #P {RAID_HIT:g}#! over {RAID_MONTHS} months."),
        ("spec_rival.1.d21", "Bankers from [SCOPE.sCountry('target').GetName] are courting our investors with better terms. "
                             f"For {LURE_MONTHS} months, #N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to them."),
        ("spec_rival.1.d31", "Newspapers in [SCOPE.sCountry('target').GetName] are full of doubts about our [concept_spec_exchange]. "
                             f"It loses #N [Multiply_CFixedPoint({fx(round(PRESS_TRUST / CALM, 4))}, {vs(EV)})|%0]#! trust."),
        ("spec_rival.1.d3n", "Newspapers in [SCOPE.sCountry('target').GetName] are full of doubts about our [concept_spec_exchange], "
                             "and it is now known who paid them. We lose trust, but so do they, and their name suffers abroad."),
        ("spec_rival.1.f", '\\"A run on the market may begin with a single rumor.\\"'),
        ("spec_rival.1.a", "Answer in kind."), ("spec_rival.1.a_tt", "We do the same to them, even if we did so this year."),
        ("spec_rival.1.a_1", "#v Bear Raid#! against them:"), ("spec_rival.1.a_2", "#v Lure Their Capital#!:"),
        ("spec_rival.1.a_3", "#v Press Campaign#! against them:"),
        ("spec_rival.1.b", "Shore up against them."), ("spec_rival.1.b_tt", f"For {SHORE_MONTHS} months their actions against us have half their effect. Costs {cost_ev}."),
        ("spec_rival.1.c", "Keep calm."), ("spec_rival.1.c_tt", f"Our [concept_spec_exchange] gains #P {pc(CALM_GAIN / CALM)}#! trust for keeping its head."),
    ]
    lines += [
        ("SPEC_DRIVER_RIVAL", "Rival Actions"),
        ("SPEC_DRIVER_RIVAL_TT", "#header Rival Actions: [Country.MakeScope.Var('spec_c_rival').GetValueWithDefault('(CFixedPoint)0')|+=2]#!\\n"
                                 "A rival's Bear Raid on our market, spread over six months."),
    ]
    out = "".join(f' {k}: "{t}"\n' for k, t in lines)
    tip = lambda a, title, body: (f' SPEC_RV_{a.upper()}_TT: "{head(title)}{body}{why("rv_" + a)}"\n'
                                  f' SPEC_RV_WHY_RV_{a.upper()}: "\\n\\n[{CALL.format("rv_" + a, "BuildTooltip")}]"\n')
    out += tip("raid", "Bear Raid",
               f"Cost: {cost}\\nEffect: their [concept_spec_market_confidence] #N -{hit(THEM)}#! over {RAID_MONTHS} months\\n"
               f"Risk: #N [{fail}|0]%#! it fails and hits us")
    out += tip("lure", "Lure Capital",
               f"Cost: our [concept_spec_outstanding_credit] {debt}\\nEffect: #P {share(THEM)}#! of their [concept_investment_pool] income, {LURE_MONTHS} months")
    out += tip("press", "Press Campaign",
               f"Cost: #N {PRESS_INFL}#! @inf! for {PRESS_MONTHS} months\\nEffect: their trust #N -{dent(THEM)}#!\\n"
               f"Risk: #N {PRESS_EXPOSE}%#! exposed: relations #N -{PRESS_REL}#!, our trust #N -{pc(PRESS_TRUST / CALM)}#!")
    out += tip("hold", "Hold the Line", f"Cost: {cost}\\nEffect: undoes one of their pushes")
    out += tip("shore", "Shore Up",
               f"Cost: {cost}\\nEffect: their actions on us halved, {SHORE_MONTHS} months\\nCooldown: {yr(SHORE_CD)}")
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
    assert contest.count("is_player = yes") == 2 and contest.count("post_notification") == 2  # the notification testbed swaps these
    assert contest.count("spec_rv_rope") == 1 and "spec_rv_push = { BY = scope:target ON = scope:spec_rv_actor }" in effects()
    assert "spec_rv_reach" not in triggers() and "spec_can_rv_end = yes" in triggers()
    assert "multiplier = spec_rv_upkeep_total" in effects() and "spec_rv_upkeep = {" in MODIFIERS
    assert "rv_toggle" in marker() and "set_level_bar_item" in gui and "spec_rv_pairs" not in gui
    assert effects().count("count = %d is_target" % AI_CAP) == 2 and "count = %d is_target" % (AI_CAP + 1) in effects()
    print("ok")
