"""Rival Exchanges (design_rivals.md): an Exchange names its rivals (var list spec_rv_chosen), apart from vanilla's
rivalries: one, or two from International Standing, among Exchanges within one Standing of its own, each kept at least a
year. A pair counts whichever named the other, both needing an Exchange. Once a year the pair's higher Financial Centre score wins a small amount of trust from the other. Between
contests either side may act against the other: Bear Raid, Lure Their Capital, Press Campaign, and Shore Up in defence.
The AI acts both ways, and a player who is targeted gets an event.

centres.py calls this module: pass_() in its monthly ranking pass, block() and marker() in the World tab, loc() in its
localization. build(write) writes the rest. An old save's single named rival (spec_rival) becomes a named rival; its
spec_rival_lock and spec_rival_last go. The AI names the nearest-scoring Exchange above it within reach."""
import icons
from pathlib import Path
import re
import tuning
import bluechips as BC
from market_tab import W, fx, ind, heads, section, SLIDE, GLIDE, CLEAR, long_date, rounded

STAKE = tuning.get("RIVAL_STAKE", 3)          # contest trust at an equal standing (out of CALM)
BITTER = tuning.get("EXCH_RIVAL_BITTER", 1.5)  # the loser's loss times this on poor relations or worse
RAID_GDP = tuning.get("RIVAL_RAID_GDP", 0.04)  # Bear Raid and Shore Up: share of our GDP from the treasury
RAID_HIT, RAID_MONTHS = tuning.get("RIVAL_RAID_HIT", 3), 6  # confidence lost over the months (beta.12: 3, the AI plays as often as a player)
RAID_FAIL, RAID_FAIL_MORE = 20, 60            # % failure, plus up to this much more as their score exceeds ours
LURE_DEBT, LURE_SHARE, LURE_MONTHS = 6, tuning.get("RIVAL_LURE_SHARE", 0.05), 12  # months of our pool income owed
PRESS_INFL, PRESS_TRUST, PRESS_EXPOSE, PRESS_REL, PRESS_MONTHS = 75, 2, 30, 20, 12  # beta.12: trust 6 to 2, trust sets mood swings and recovery and the AI presses often
# Press Campaign's exposure % by the target's speech law: a free press answers back, a censored one cannot
PRESS_EXPOSE_BY = (('law_outlawed_dissent', 10), ('law_censorship', 20), ('law_right_of_assembly', 35), ('law_protected_speech', 50))
VS_LO, VS_HI = 0.75, 1.33                         # their Exchange's score over ours, as costs and effects scale by it
SHORE_MONTHS, SHORE_CD = 12, 2                 # months one rival's moves are halved; years before shoring up against it again
CD_DAYS = 365                                 # each action's cooldown, per target
CALM_GAIN = 1.2                                 # the event's Keep Calm, x(1 + CALM_STAND x their Standing)
CALM_STAND = 1  # keep calm: 1%, 2%, 3%, 4% by their Standing
EV_GAP = 180                                  # days between two competitor events for one player
COUNTER_GDP = 0.01                           # the event's fitted counter: share of our GDP from the treasury
MANIA = tuning.get("MANIA", 80)
CALM = tuning.get("CENTRE_CALM", 120)
ACTIONS = ("raid", "lure", "press")           # spec_rv_hit codes 1, 2, 3
SLOTS = 3                                     # Press Campaigns running at once, one modifier each
CONTESTS = (1, 2, 4, 6)  # contests an Exchange may run by Standing, Provincial to World Centre (2026-11-19: 1, 2, 3, 4)
NAMED, NAMED_HIGH, NAMED_FROM = CONTESTS[0], CONTESTS[-1], 2  # (beta.12: the user won every one of many)
THIN = 0.25                                   # spread thin: a side's score counts 1 / (1 + THIN x its contests past the first)
REACH = 1                                     # a named rival's Standing within this many of ours
KEEP_DAYS = 365                               # a newly named rival cannot be dropped for this long
REL_HIT, REL_DRIFT = 10, 1                    # relations lost on rivalling, and each month after down to Poor (vanilla rivalry: to -20)
AI_CAP = 3                                    # the AI rivals no Exchange that this many already rival
AI_LATE, AI_NEAR, AI_RESERVE = 2, 0.15, 3  # endgame years, nearness to a result's edge, money kept in reserve
AI_LEV = 2                                    # the AI lures only below this leverage: a lure's debt is its own (190 lures a year took AIs to 4)
AI_PICK_CHANCE = 16                           # % chance a look (AI_EVERY days) an AI with a free slot names one new competitor without an opening: about half a year (2026-11-19: 50 a year, on one day)
AI_EVERY = 90                                 # days between the AI's looks at its contests (beta.12: was a yearly dice roll)
RAID_CAP = tuning.get("RIVAL_RAID_CAP", 4)   # most confidence a country loses to Bear Raids in a year, all raiders together
AI_REACH = -0.3                               # the AI names only rivals it starts no further behind than this
AI_CUT = -0.65                                # it drops a rival it is this far behind, short of a Decisive Loss (-DECISIVE)
# the contest is a tug of war settled every ROUND years: the bar starts from the two scores (the lead as a share of the
# higher), each successful action pushes it PUSH toward its side (at most PUSHES each way, spec_rv_push_1..N lists on
# the pusher), and where it ends picks one of five results: a draw inside DRAW, past DECISIVE a decisive win or loss
ROUND = 5
MONTHS = ROUND * 12  # a contest's clock counts months (spec_rv_age_<0..MONTHS-1>): it settles ROUND years after it
# starts, not at the shared yearly round (2026-11-19: one begun mid-year settled in 4.2 years)
PUSH, PUSHES = 0.1, 5
DRAW, DECISIVE = 0.2, 0.75                    # beta.12: widened from 0.1/0.4, then decisive 0.6 to 0.75 (the user: wins too easy)
INTEREST_TIER = 2                             # contests need our Interest at least Engaged (vanilla rank 2) in the rival capital's strategic region (2026-11-16)
INVOLVE_START, INVOLVE_MONTH = 1000, 90       # involvement in a contested capital's region: on naming it (vanilla's rivalry pact gives 1000), then monthly against the decay (20 a week)
WIN_X, BIG_X = 2, 4                           # trust at stake: STAKE times these for a win and a decisive win
UPKEEP = (25, 50, 100, 150)                   # influence maintenance of a rival, by its Standing (vanilla pacts: 25 to 150)
OLD_VARS = ["spec_rival", "spec_rival_lock", "spec_rival_last", "spec_rv_shored", "spec_rv_shore_cd"]  # the last two: Shore Up before it was per rival
STATE_VARS = OLD_VARS + ["spec_c_rival", "spec_rv_ai_wait", "spec_rv_ai_seen", "spec_rv_raid_year", "spec_rv_raid", "spec_rv_raid_pm", "spec_rv_raider", "spec_rv_lure", "spec_rv_lurer", "spec_rv_lure_share",
                         "spec_rv_hit", "spec_rv_hit_by", "spec_rv_hit_ok", "spec_rv_hit_recent",
                         "spec_rv_did", "spec_rv_did_on", "spec_rv_did_ok", "spec_rv_did_recent", "spec_rv_did_amt", "spec_rv_did_cost",
                         "spec_rv_n_out", "spec_rv_n_in", "spec_rv_n_chosen", "spec_rv_ui_left", "spec_rv_n_all", "spec_rv_focus", "spec_rv_ui_p", "spec_rv_ui_shown", "spec_rv_ui_step", "spec_rv_ui_us", "spec_rv_ui_them", "spec_rv_ui_forfeit"]
# scripted GUIs with root = the player and scope:target = the row's country
CALL = "GetScriptedGui('spec_sgui_{}').{}(GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('target', Country.MakeScope).End)"
US, THEM = "GetMetaPlayer.GetPlayedOrObservedCountry.MakeScope", "Country.MakeScope"
CAN_MANAGE = "Not(GetMetaPlayer.IsObserver)"
OUTGOING = f"{US}.GetList(Select_CString(GetMetaPlayer.IsObserver, 'spec_rv_observed_out', 'spec_rv_outs'))"
INCOMING = f"{US}.GetList(Select_CString(GetMetaPlayer.IsObserver, 'spec_rv_observed_in', 'spec_rv_ins'))"
PICK = "spec_rv_pick"  # GetVariableSystem flag: set, the contest picker under the slots is open (_picker)
pc = lambda x: f"{round(x * 100, 1):g}%"
RAID_TERMS = range(1, RAID_MONTHS + 1)
STATE_VARS += [f"spec_rv_due_{n}" for n in RAID_TERMS] + ["spec_rv_next", "spec_rv_next_year"]


LOG = "--log" in __import__("sys").argv  # generate.py --log: SPECRV debug lines for tools/observe.py runs


def _log(what, t):
    """In the actor's scope with scope:target saved: one SPECRV line in a --log build, else nothing."""
    if not LOG:
        return ""
    return (f"{t}set_variable = {{ name = spec_rv_log_vs value = spec_rv_vs }}\n"
            f"{t}debug_log = \"SPECRV {what} by=[THIS.GetCountry.GetTagName] on=[SCOPE.sCountry('target').GetTagName]"
            " date=[TimeKeeper.GetCurrentDate.GetString] vs=[THIS.Var('spec_rv_log_vs').GetValue]"
            " ok=[THIS.Var('spec_rv_log_ok').GetValue] score=[THIS.Var('spec_centre_score').GetValue]"
            " tscore=[SCOPE.sCountry('target').MakeScope.Var('spec_centre_score').GetValue]"
            # last, as an unset Var ends the line: the act's size (spec_rv_did sets both before raid and lure log)
            " amt=[THIS.Var('spec_rv_did_amt').GetValue] cost=[THIS.Var('spec_rv_did_cost').GetValue]\"\n")


# --log only: one SPECRVA line per AI look (spec_rv_ai): contests looked at (n), those that called for a move before one
# was made (e), the branch each took (shore, wait while decisive, hold, push), pushes where a Lure was allowed (lure_ok)
_LG = ("n", "e", "shore", "wait", "hold", "push", "lure_ok")
_lg_add = lambda k, t: f"{t}change_local_variable = {{ name = spec_rv_lg_{k} add = 1 }}\n" if LOG else ""
LG_INIT = "".join(f"\t\tset_local_variable = {{ name = spec_rv_lg_{k} value = 0 }}\n" for k in _LG) if LOG else ""
LG_OUT = ("".join(f"\t\tset_variable = {{ name = spec_rv_lg_{k} value = local_var:spec_rv_lg_{k} }}\n" for k in _LG)
          + "\t\tset_variable = { name = spec_rv_lg_nch value = 0 }\n"
          "\t\tevery_in_list = { variable = spec_rv_chosen prev = { change_variable = { name = spec_rv_lg_nch add = 1 } } }\n"
          "\t\tdebug_log = \"SPECRVA tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] lev=[THIS.ScriptValue('spec_lev')]"
          " panic=[THIS.ScriptValue('spec_in_panic')] chosen=[THIS.Var('spec_rv_lg_nch').GetValue]"
          + "".join(f" {k}=[THIS.Var('spec_rv_lg_{k}').GetValue]" for k in _LG) + "\"\n") if LOG else ""
LG_N, LG_E = _lg_add("n", "\t"), _lg_add("e", "\t\t")
LG_SHORE, LG_WAIT, LG_HOLD, LG_PUSH = (_lg_add(k, "\t\t") for k in ("shore", "wait", "hold", "push"))
LG_LURE = (f"\t\tif = {{\n\t\t\tlimit = {{ spec_can_rv_lure = yes spec_lev < {AI_LEV} }}\n" + _lg_add("lure_ok", "\t\t\t") + "\t\t}\n") if LOG else ""


def _ok(t):
    return f"{t}set_variable = {{ name = spec_rv_log_ok value = local_var:spec_rv_ok }}\n" if LOG else ""


def _settle_log(what, me, value, t):
    """In the rival's scope, with scope:<me> the country that named it: the bar from <me>'s side."""
    if not LOG:
        return ""
    return (f"{t}set_variable = {{ name = spec_rv_log_p value = {value} }}\n"
            f"{t}debug_log = \"SPECRV {what} by=[SCOPE.sCountry('{me}').GetTagName] on=[THIS.GetCountry.GetTagName]"
            " date=[TimeKeeper.GetCurrentDate.GetString] p=[THIS.Var('spec_rv_log_p').GetValue]"
            f" score=[SCOPE.sCountry('{me}').MakeScope.Var('spec_centre_score').GetValue] tscore=[THIS.Var('spec_centre_score').GetValue]"
            f" stand=[SCOPE.sCountry('{me}').MakeScope.Var('spec_exch_stand').GetValue] tstand=[THIS.Var('spec_exch_stand').GetValue]\"\n")


def _year_log(t):
    """Once a year, a line per Exchange: rivals named, upkeep, Standing, score, trust, influence."""
    if not LOG:
        return ""
    keys = [k for k, *_ in __import__("centres").NAMES]
    # each speciality's strength (spec_pw_<key>, 0 to 1) and our place on it (spec_lead_<key>, 1 to 3), 0 when unset
    pre = "".join(f"{t}\tset_variable = {{ name = spec_rv_log_{n}_{k} value = 0 }}\n"
                  f"{t}\tif = {{ limit = {{ has_variable = {v}_{k} }} set_variable = {{ name = spec_rv_log_{n}_{k} value = var:{v}_{k} }} }}\n"
                  for k in keys for n, v in (("pw", "spec_pw"), ("at", "spec_lead")))
    # our companies at 50+, 60+ and 70+ prosperity (blue chip calibration)
    bands = (50, 60, 70)
    pre += ("".join(f"{t}\tset_local_variable = {{ name = spec_rv_k{b} value = 0 }}\n" for b in bands)
            + f"{t}\tevery_company = {{\n"
            + "".join(f"{t}\t\tif = {{ limit = {{ prosperity >= {b} }} change_local_variable = {{ name = spec_rv_k{b} add = 1 }} }}\n" for b in bands)
            + f"{t}\t}}\n"
            + "".join(f"{t}\tset_variable = {{ name = spec_rv_log_k{b} value = local_var:spec_rv_k{b} }}\n" for b in bands))
    keys_k = "".join(f" k{b}=[THIS.Var('spec_rv_log_k{b}').GetValue]" for b in bands)
    return (f"{t}every_country = {{\n{t}\tlimit = {{ has_variable = spec_exch_stand has_variable = spec_centre_score }}\n"
            f"{t}\tdebug_log = \"SPECRVY tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString]"
            " named=[THIS.Var('spec_rv_n_chosen').GetValue] upkeep=[THIS.ScriptValue('spec_rv_upkeep_total')]"
            " stand=[THIS.Var('spec_exch_stand').GetValue] score=[THIS.Var('spec_centre_score').GetValue]"
            " trust=[THIS.Var('spec_centre_trust').GetValue] round=[GetGlobalVariable('spec_rv_round').GetValue]"
            " bc=[THIS.ScriptValue('spec_log_kbc')] kstr=[THIS.ScriptValue('spec_log_kstr')]" + keys_k
            + "".join(f" pw_{k}=[THIS.Var('spec_rv_log_pw_{k}').GetValue] at_{k}=[THIS.Var('spec_rv_log_at_{k}').GetValue]" for k in keys)
            + f"\"\n{t}}}\n").replace(f"{t}\tdebug_log", pre + f"{t}\tdebug_log", 1)


def shown(key):
    return CALL.format(key, "IsShown").replace("GetPlayer.MakeScope", US)


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
                 "\tcustom_tooltip = {\n\t\ttext = spec_rv_lured_tt\n\t\tscope:target = { spec_rv_active_lure = no }\n\t}\n"),
        "press": (f"\tcustom_tooltip = {{\n\t\ttext = spec_rv_infl_tt\n\t\tinfluence >= {PRESS_INFL}\n\t}}\n"
                  f"\tcustom_tooltip = {{\n\t\ttext = spec_rv_slots_tt\n\t\tNOT = {{ AND = {{ {free} }} }}\n\t}}\n"),
    }
    exch = ("has_variable = spec_exch_stand has_variable = spec_centre_score has_variable = spec_centre_trust")
    out = f"""# rival Exchanges (rivals.py): one named the other, both with an Exchange; scope:target = the other
spec_rv_active_lure = {{
	has_variable = spec_rv_lure
	exists = var:spec_rv_lurer
	var:spec_rv_lurer = {{ is_country_alive = yes }}
}}

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
		text = spec_rv_room_tt
		OR = {{
			NOT = {{ has_variable = spec_rv_n_chosen }}
			var:spec_rv_n_chosen < spec_rv_slots
		}}
	}}
	custom_tooltip = {{
		text = spec_rv_their_exch_tt
		scope:target = {{ {exch} }}
	}}
	custom_tooltip = {{
		text = spec_rv_mutual_tt
		scope:target = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }}
	}}
	custom_tooltip = {{
		text = spec_rv_interest_tt
		scope:target = {{ exists = capital }}
		has_strategic_region_interest_tier = {{
			strategic_region = scope:target.capital.region
			value >= {INTEREST_TIER}
		}}
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

spec_rv_today = {{ value = game_date }}
# the days Shore Up would end and be ready again if used now (spec_rv_shore), for the dates its tooltips show
spec_rv_shore_end_day = {{
	value = game_date
	add = {SHORE_MONTHS * 30}
	if = {{
		limit = {{ spec_nx_shore > 1.05 }}
		add = {round(SHORE_MONTHS * 30 * 0.4)}
	}}
}}
spec_rv_shore_again_day = {{ value = game_date add = {SHORE_CD * 365} }}

{"".join(f'''spec_rv_{key}_date = {{
	value = 0
	if = {{
		limit = {{ is_key_in_variable_map = {{ name = spec_rv_{key} target = scope:target }} }}
		value = "variable_map(spec_rv_{key}|scope:target)"
	}}
}}
''' for key in ('shore_until', 'protected_until'))}

spec_rv_raid_applied = {{
	value = 0
	if = {{
		limit = {{ has_variable = spec_rv_raid_pm }}
		value = var:spec_rv_raid_pm
		max = {{
			value = {RAID_CAP}
			if = {{ limit = {{ has_variable = spec_rv_raid_year }} subtract = var:spec_rv_raid_year }}
		}}
		min = 0
	}}
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

# the AI pays for a money action only with this much gold in reserve
spec_rv_ai_money = {{
	value = spec_rv_cost
	multiply = {AI_RESERVE:g}
}}

# the competitor event's fitted counter (rivals.COUNTER_GDP)
spec_rv_counter_cost = {{
	value = gdp
	multiply = {COUNTER_GDP:g}
}}

spec_rv_counter_cost_neg = {{
	value = spec_rv_counter_cost
	multiply = -1
}}

# Press Campaign: the % chance it is exposed, by the target's speech law (target scope)
spec_rv_press_expose = {{
	value = {PRESS_EXPOSE}
{''.join(f'	if = {{ limit = {{ has_law = law_type:{l} }} value = {v} }}\n' for l, v in PRESS_EXPOSE_BY)}}}

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
	value = spec_rv_me_eff
	subtract = spec_rv_it_eff
	divide = {{
		value = spec_rv_it_eff
		min = spec_rv_me_eff
		min = 1
	}}
	# blue chips (bluechips.PULL each as counted: each in full, up to CAP)
	if = {{
		limit = {{ scope:spec_rival_me = {{ has_variable = spec_bc_n }} }}
		add = {{
			value = 0
{BC.counted('scope:spec_rival_me.var:spec_bc_n', chr(9) * 3)}			multiply = {BC.PULL:g}
		}}
	}}
	if = {{
		limit = {{ has_variable = spec_bc_n }}
		subtract = {{ value = spec_bc_counted multiply = {BC.PULL:g} }}
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
	value = {CONTESTS[0]}
{"".join(f"	if = {{{chr(10)}		limit = {{ var:spec_exch_stand ?= {t} }}{chr(10)}		value = {CONTESTS[t]}{chr(10)}	}}{chr(10)}" for t in (1, 2, 3))}}}

# spread thin: what a side's score counts for, by the contests it is in (spec_rv_n_all, monthly)
spec_rv_focus_sv = {{
	value = 1
	divide = {{
		value = var:spec_rv_n_all
		subtract = 1
		min = 0
		multiply = {THIN:g}
		add = 1
	}}
}}

# the two sides' scores as they count (scope:spec_rival_me's, and this country's)
spec_rv_me_eff = {{
	value = scope:spec_rival_me.var:spec_centre_score
	if = {{
		limit = {{ scope:spec_rival_me = {{ has_variable = spec_rv_focus }} }}
		multiply = scope:spec_rival_me.var:spec_rv_focus
	}}
}}
spec_rv_it_eff = {{
	value = var:spec_centre_score
	if = {{
		limit = {{ has_variable = spec_rv_focus }}
		multiply = var:spec_rv_focus
	}}
}}

# years into a contest (its clock in months, spec_rv_age_<k> on the side that named the other): from this to scope:target
spec_rv_age_t = {{
	value = 0
	if = {{
		limit = {{ exists = scope:target }}
{"".join(f"		if = {{ limit = {{ OR = {{ is_target_in_variable_list = {{ name = spec_rv_age_{k} target = scope:target }} scope:target = {{ is_target_in_variable_list = {{ name = spec_rv_age_{k} target = prev }} }} }} }} value = {k} }}" + chr(10) for k in range(1, MONTHS))}	}}
	divide = 12
}}

# the same from scope:spec_rival_me to this (a player's rows)
spec_rv_age_m = {{
	value = 0
{"".join(f"	if = {{ limit = {{ OR = {{ is_target_in_variable_list = {{ name = spec_rv_age_{k} target = scope:spec_rival_me }} scope:spec_rival_me = {{ is_target_in_variable_list = {{ name = spec_rv_age_{k} target = prev }} }} }} }} value = {k} }}" + chr(10) for k in range(1, MONTHS))}	divide = 12
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
"""


def _gain(by, t, why="rivals"):
    return BC.record_trust(_raw_gain(by, t), "rivals", t, why)


def _lose(by, t, why="rivals"):
    return BC.record_trust(_raw_lose(by, t), "rivals", t, why)


def _raw_gain(by, t):
    return f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust add = {by} max = {CALM} }} }}\n"


def _raw_lose(by, t):
    """As centres._lose: times spec_exch_loss, never below 0."""
    return (f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
            f"subtract = {{ value = {by} multiply = spec_exch_loss }} min = 0 }} }}\n")


def _half(var, t):
    """Halved if the side taking the hit has shored up against the other: the target, or the actor of a failed raid."""
    other = ("OR = { AND = { this = scope:spec_rv_actor is_target_in_variable_list = { name = spec_rv_shield target = scope:target } } "
             "AND = { NOT = { this = scope:spec_rv_actor } is_target_in_variable_list = { name = spec_rv_shield target = scope:spec_rv_actor } } }")
    return f"{t}if = {{\n{t}\tlimit = {{ {other} }}\n{t}\tchange_local_variable = {{ name = {var} multiply = 0.5 }}\n{t}}}\n"


def raid_expiry_effects():
    # Raids starting in the same month expire together. Track their summed rate and
    # all sources, including raids which backfired, without imposing an attacker limit.
    def remember(n, source):
        return f"""add_to_variable_list = {{ name = spec_rv_from_{n} target = {source} }}
if = {{
	limit = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_attackers target = {source} }} }} }}
	add_to_variable_list = {{ name = spec_rv_attackers target = {source} }}
}}"""

    migrate = []
    shift = []
    for n in RAID_TERMS:
        migrate.append(f"""{'if' if n == 1 else 'else_if'} = {{
	limit = {{ var:spec_rv_raid = {n} }}
	set_variable = {{ name = spec_rv_due_{n} value = var:spec_rv_raid_pm }}
	if = {{
		limit = {{ exists = var:spec_rv_raider }}
{ind(remember(n, 'var:spec_rv_raider'), 2)}
	}}
}}""")
        if n > 1:
            shift.append(f"""if = {{
	limit = {{ has_variable = spec_rv_due_{n} }}
	set_variable = {{ name = spec_rv_due_{n - 1} value = var:spec_rv_due_{n} }}
	remove_variable = spec_rv_due_{n}
	every_in_list = {{
		variable = spec_rv_from_{n}
		save_temporary_scope_as = spec_rv_source
		prev = {{ add_to_variable_list = {{ name = spec_rv_from_{n - 1} target = scope:spec_rv_source }} }}
	}}
	clear_variable_list = spec_rv_from_{n}
}}""")
    remaining = " ".join(f"is_target_in_variable_list = {{ name = spec_rv_from_{n} target = prev }}" for n in RAID_TERMS if n > 1)
    return f"""
spec_rv_migrate_raid = {{
	if = {{
		limit = {{ has_variable = spec_rv_raid has_variable = spec_rv_raid_pm NOR = {{ {' '.join(f'has_variable = spec_rv_due_{n}' for n in RAID_TERMS)} }} }}
{ind(chr(10).join(migrate), 2)}
	}}
}}

spec_rv_register_raid = {{
	if = {{
		limit = {{ NOT = {{ has_variable = spec_rv_due_{RAID_MONTHS} }} }}
		set_variable = {{ name = spec_rv_due_{RAID_MONTHS} value = 0 }}
	}}
	change_variable = {{ name = spec_rv_due_{RAID_MONTHS} add = local_var:spec_rv_pm }}
{ind(remember(RAID_MONTHS, 'var:spec_rv_raider'), 1)}
}}

spec_rv_expire_raids = {{
	if = {{
		limit = {{ has_variable = spec_rv_due_1 }}
		change_variable = {{ name = spec_rv_raid_pm subtract = var:spec_rv_due_1 }}
		remove_variable = spec_rv_due_1
		every_in_list = {{
			variable = spec_rv_from_1
			limit = {{ prev = {{ NOR = {{ {remaining} }} }} }}
			save_temporary_scope_as = spec_rv_source
			prev = {{ remove_list_variable = {{ name = spec_rv_attackers target = scope:spec_rv_source }} }}
		}}
		clear_variable_list = spec_rv_from_1
	}}
{ind(chr(10).join(shift), 1)}
}}
"""


def effects():
    slots = "".join(f"\t{'if' if n == 1 else 'else_if'} = {{\n\t\tlimit = {{ NOT = {{ has_modifier = spec_rv_press_{n} }} }}\n"
                    f"\t\tadd_modifier = {{ name = spec_rv_press_{n} months = {PRESS_MONTHS} }}\n\t}}\n" for n in range(1, SLOTS + 1))
    # the yearly contest: once per pair, whichever named the other. Results are lists on both sides, emptied first
    lists = ("spec_rv_won", "spec_rv_lost", "spec_rv_tied")
    done = " ".join(f"is_target_in_variable_list = {{ name = {l} target = scope:spec_rival_me }}" for l in lists)
    # the player keeps each Exchange it beat or lost to this year, and gets one toast per contest that names it
    note = lambda key, other: f"\tif = {{\n\t\tlimit = {{ is_player = yes }}\n\t\tadd_to_variable_list = {{ name = spec_rival_vs_{key} target = scope:{other} }}\n\t}}\n"
    # named as the Exchange is (centres SPEC_EXCH_CITY): its seat, else its capital. Picked here, as SelectLocalization
    # in a toast cannot read SCOPE (notify.py)
    flush = "".join(f"""		every_in_list = {{
			variable = spec_rival_vs_{k}
			save_scope_as = spec_note_src
			if = {{
				limit = {{ has_variable = spec_exch_seat exists = var:spec_exch_seat }}
				var:spec_exch_seat = {{ save_scope_as = spec_note_state }}
			}}
			else = {{
				capital = {{ save_scope_as = spec_note_state }}
			}}
			prev = {{ post_notification = spec_rival_{k} }}
		}}
		clear_variable_list = spec_rival_vs_{k}
""" for k in ("won", "lost"))
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
{big(chr(9)).replace("$DO$", f"change_local_variable = {{ name = spec_rv_stake multiply = {BIG_X / WIN_X:g} }}")}{_gain("local_var:spec_rv_stake", chr(9), "contest_won")}	add_to_variable_list = {{ name = spec_rv_won target = scope:spec_rv_l }}
{big(chr(9)).replace("$DO$", "add_to_variable_list = { name = spec_rv_big target = scope:spec_rv_l }")}{note("won", "spec_rv_l")}}}
scope:spec_rv_l = {{
{_lose("local_var:spec_rv_stake", chr(9), "contest_lost")}	if = {{
		limit = {{ "relations(scope:spec_rv_w)" <= relations_threshold:poor }}
{_lose(f"{{ value = local_var:spec_rv_stake multiply = {BITTER - 1:g} }}", chr(9) * 2, "contest_bitter")}	}}
	add_to_variable_list = {{ name = spec_rv_lost target = scope:spec_rv_w }}
	if = {{
		limit = {{ local_var:spec_rv_big = 1 }}
		add_to_variable_list = {{ name = spec_rv_big target = scope:spec_rv_w }}
		if = {{
			limit = {{ spec_rv_active_lure = no }}
			set_variable = {{ name = spec_rv_lure value = {LURE_MONTHS} }}
			set_variable = {{ name = spec_rv_lurer value = scope:spec_rv_w }}
			set_variable = {{ name = spec_rv_lure_share value = {LURE_SHARE:g} }}
		}}
	}}
{note("lost", "spec_rv_w")}}}
"""
    return f"""# rival Exchanges (rivals.py): every {ROUND} years each pair's bar (spec_rv_rope) settles, in five bands
spec_rival_contest = {{
	every_country = {{
		limit = {{ has_variable_list = spec_rv_settled }}
		clear_variable_list = spec_rv_settled
	}}
	every_country = {{
		limit = {{ {exch} }}
		save_scope_as = spec_rival_me
		every_in_list = {{
			variable = spec_rv_chosen
			limit = {{
				{exch}
				scope:spec_rival_me = {{ is_target_in_variable_list = {{ name = spec_rv_age_{MONTHS - 1} target = prev }} }}
				NOT = {{ is_target_in_variable_list = {{ name = spec_rv_settled target = scope:spec_rival_me }} }}
			}}
			# Snapshot the final bar while both competitors still have their pushes.
			set_local_variable = {{ name = spec_rv_p value = spec_rv_rope }}
			# this pair's last result and pushes go; it settles once this year
			save_temporary_scope_as = spec_rv_x
			add_to_variable_list = {{ name = spec_rv_settled target = scope:spec_rival_me }}
			scope:spec_rival_me = {{ add_to_variable_list = {{ name = spec_rv_settled target = scope:spec_rv_x }} }}
{"".join(f"			remove_list_variable = {{ name = {l} target = scope:spec_rival_me }}{chr(10)}			scope:spec_rival_me = {{ remove_list_variable = {{ name = {l} target = scope:spec_rv_x }} }}{chr(10)}" for l in ("spec_rv_won", "spec_rv_lost", "spec_rv_tied", "spec_rv_big") + tuple(f"spec_rv_push_{k}" for k in range(1, PUSHES + 1)))}			set_local_variable = {{ name = spec_rv_big value = 0 }}
{_settle_log('settle', 'spec_rival_me', 'local_var:spec_rv_p', chr(9) * 3)}			if = {{
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
	# a year on every clock; a settled contest is over and frees its slot (2026-11-19: it used to start again)
	every_country = {{
		limit = {{ has_variable_list = spec_rv_chosen }}
		every_in_list = {{
			variable = spec_rv_age_{MONTHS - 1}
			save_temporary_scope_as = spec_rv_x
			prev = {{ remove_list_variable = {{ name = spec_rv_chosen target = scope:spec_rv_x }} }}
		}}
		clear_variable_list = spec_rv_age_{MONTHS - 1}
{"".join(f"""		every_in_list = {{
			variable = spec_rv_age_{k}
			save_temporary_scope_as = spec_rv_x
			prev = {{ add_to_variable_list = {{ name = spec_rv_age_{k + 1} target = scope:spec_rv_x }} }}
		}}
		clear_variable_list = spec_rv_age_{k}
""" for k in range(MONTHS - 2, -1, -1))}		spec_rv_count = yes
	}}
	every_country = {{
		limit = {{ OR = {{ has_variable_list = spec_rival_vs_won has_variable_list = spec_rival_vs_lost }} }}
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
	remove_variable = spec_rv_next
	remove_variable = spec_rv_next_year
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
		# the bar shows spec_rv_ui_shown, which spec_rv_glide steps to the new figure over GLIDE weeks
		if = {{
			limit = {{ NOT = {{ has_variable = spec_rv_ui_shown }} }}
			set_variable = {{ name = spec_rv_ui_shown value = var:spec_rv_ui_p }}
		}}
		set_variable = {{ name = spec_rv_ui_step value = {{ value = var:spec_rv_ui_p subtract = var:spec_rv_ui_shown divide = {GLIDE} }} }}
		set_variable = {{ name = spec_rv_ui_left value = {{ value = {ROUND} subtract = spec_rv_age_m }} }}
		save_temporary_scope_as = spec_rv_row
		scope:spec_rival_me = {{
			if = {{
				limit = {{ OR = {{ NOT = {{ has_variable = spec_rv_next_year }} scope:spec_rv_row.var:spec_rv_ui_left < var:spec_rv_next_year }} }}
				set_variable = {{ name = spec_rv_next value = scope:spec_rv_row }}
				set_variable = {{ name = spec_rv_next_year value = scope:spec_rv_row.var:spec_rv_ui_left }}
			}}
		}}
		set_variable = {{ name = spec_rv_ui_us value = spec_rv_n_push_me }}
		set_variable = {{ name = spec_rv_ui_them value = spec_rv_n_push_it }}
		set_variable = {{
			name = spec_rv_ui_forfeit
			value = {{
				value = {STAKE}
				if = {{
					limit = {{ var:spec_exch_stand > scope:spec_rival_me.var:spec_exch_stand }}
					divide = {{ value = var:spec_exch_stand subtract = scope:spec_rival_me.var:spec_exch_stand add = 1 }}
				}}
				else_if = {{
					limit = {{ var:spec_exch_stand < scope:spec_rival_me.var:spec_exch_stand }}
					multiply = {{ value = scope:spec_rival_me.var:spec_exch_stand subtract = var:spec_exch_stand add = 1 }}
				}}
				multiply = {WIN_X}
				if = {{
					limit = {{ spec_rv_rope <= -{DECISIVE} }}
					multiply = {BIG_X / WIN_X:g}
				}}
			}}
		}}
	}}
	else_if = {{
		limit = {{ has_variable = spec_rv_ui_p }}
		remove_variable = spec_rv_ui_p
		remove_variable = spec_rv_ui_shown
		remove_variable = spec_rv_ui_step
	}}
}}

# weekly for a player (journal's on_weekly_pulse): each contest bar a step to its month's figure
spec_rv_glide = {{
	every_in_list = {{
		variable = spec_rv_outs
		spec_rv_glide_row = yes
	}}
	every_in_list = {{
		variable = spec_rv_ins
		spec_rv_glide_row = yes
	}}
}}

spec_rv_glide_row = {{
	if = {{
		limit = {{ has_variable = spec_rv_ui_step NOT = {{ var:spec_rv_ui_step = 0 }} }}
		change_variable = {{ name = spec_rv_ui_shown add = var:spec_rv_ui_step }}
		if = {{
			limit = {{
				OR = {{
					AND = {{ var:spec_rv_ui_step > 0 var:spec_rv_ui_shown > var:spec_rv_ui_p }}
					AND = {{ var:spec_rv_ui_step < 0 var:spec_rv_ui_shown < var:spec_rv_ui_p }}
				}}
			}}
			set_variable = {{ name = spec_rv_ui_shown value = var:spec_rv_ui_p }}
			set_variable = {{ name = spec_rv_ui_step value = 0 }}
		}}
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
		limit = {{ has_variable = spec_rv_n_chosen var:spec_rv_n_chosen > 0 }}
		add_modifier = {{ name = spec_rv_upkeep multiplier = spec_rv_upkeep_total }}
	}}
}}

# a named rival's contest clock, if it has none: theirs if they named us too, else a new one (scope:target)
spec_rv_clock = {{
	if = {{
		limit = {{ NOT = {{ OR = {{ {" ".join(f"is_target_in_variable_list = {{ name = spec_rv_age_{k} target = scope:target }}" for k in range(MONTHS))} }} }} }}
{"".join(f"		{'if' if k == 0 else 'else_if'} = {{{chr(10)}			limit = {{ scope:target = {{ is_target_in_variable_list = {{ name = spec_rv_age_{k} target = prev }} }} }}{chr(10)}			add_to_variable_list = {{ name = spec_rv_age_{k} target = scope:target }}{chr(10)}		}}{chr(10)}" for k in range(MONTHS))}		else = {{
			add_to_variable_list = {{ name = spec_rv_age_0 target = scope:target }}
		}}
	}}
}}

# one more contest for spread thin (spec_rv_n_all)
spec_rv_tick = {{
	if = {{
		limit = {{ NOT = {{ has_variable = spec_rv_n_all }} }}
		set_variable = {{ name = spec_rv_n_all value = 0 }}
	}}
	change_variable = {{ name = spec_rv_n_all add = 1 }}
}}

# name scope:target a rival, or drop it; a player's rows follow at once
spec_rv_choose = {{
	add_to_variable_list = {{ name = spec_rv_chosen target = scope:target }}
	if = {{
		limit = {{ scope:target = {{ exists = capital }} }}
		add_involvement = {{ strategic_region = scope:target.capital.region value = {INVOLVE_START} }}
	}}
	spec_rv_clock = yes
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
				limit = {{ scope:spec_rv_x = {{ exists = capital }} }}
				add_involvement = {{ strategic_region = scope:spec_rv_x.capital.region value = {INVOLVE_MONTH} }}
			}}
			if = {{
				limit = {{ "relations(scope:spec_rv_x)" > relations_threshold:poor }}
				change_relations = {{ country = scope:spec_rv_x value = -{REL_DRIFT} }}
			}}
		}}
	}}
}}

# ending a contest before it settles forfeits it: it settles at once as a loss for this, a Decisive Loss (lure and
# all) if the bar already shows one, else a plain Loss, even from a draw or a lead. So quitting never beats waiting;
# what it buys is the slot, the upkeep and the relations (2026-11-16: a cheaper forfeit let a lost contest dodge its bill)
spec_rv_forfeit = {{
	if = {{
		limit = {{
			{exch}
			scope:target = {{ is_country_alive = yes {exch} }}
		}}
		custom_tooltip = spec_rv_forfeit_tt
		hidden_effect = {{
			save_scope_as = spec_rival_me
			save_scope_as = spec_rv_l
			scope:target = {{
				save_scope_as = spec_rv_w
				set_local_variable = {{ name = spec_rv_p value = spec_rv_rope }}
			}}
			set_local_variable = {{ name = spec_rv_big value = 0 }}
			if = {{
				limit = {{ local_var:spec_rv_p <= -{DECISIVE} }}
				set_local_variable = {{ name = spec_rv_big value = 1 }}
			}}
{ind(body.replace(note("won", "spec_rv_l"), "").replace(note("lost", "spec_rv_w"), ""), 3)}		}}
	}}
}}

# Clear the departing nomination immediately. A reciprocal nomination keeps its own clock and moves.
spec_rv_drop_pair = {{
    save_temporary_scope_as = spec_rv_departing
    remove_list_variable = {{ name = spec_rv_chosen target = scope:target }}
    remove_list_variable = {{ name = spec_rv_keep target = scope:target }}
{"".join(f"    remove_list_variable = {{ name = spec_rv_age_{k} target = scope:target }}{chr(10)}" for k in range(MONTHS))}
    if = {{
        limit = {{ NOT = {{ scope:target = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_departing }} }} }} }}
{"".join(f"        remove_list_variable = {{ name = {key} target = scope:target }}{chr(10)}        scope:target = {{ remove_list_variable = {{ name = {key} target = scope:spec_rv_departing }} }}{chr(10)}" for key in tuple(f"spec_rv_push_{k}" for k in range(1, PUSHES + 1)) + ("spec_rv_won", "spec_rv_lost", "spec_rv_big", "spec_rv_tied"))}    }}
}}

spec_rv_end = {{
	spec_rv_forfeit = yes
	spec_rv_drop_pair = yes
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
	spec_rv_did = {{ CODE = $CODE$ }}
	if = {{  # unset while a tooltip runs this without setting anything (2026-11-19: "value of type none" every frame)
		limit = {{ has_variable = spec_rv_did_amt }}
		save_scope_value_as = {{ name = spec_rv_event_amount value = var:spec_rv_did_amt }}
	}}
	scope:target = {{
		set_variable = {{ name = spec_rv_hit value = $CODE$ }}
		set_variable = {{ name = spec_rv_hit_by value = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_hit_ok value = local_var:spec_rv_ok }}
		set_variable = {{ name = spec_rv_hit_recent days = 365 }}
		if = {{
			limit = {{
				is_player = yes
				local_var:spec_rv_ok = 1
				NOT = {{ has_variable = spec_rv_ev_gap }}
			}}
			set_variable = {{ name = spec_rv_ev_gap days = {EV_GAP} }}
			trigger_event = {{ id = spec_rival.1 popup = yes }}
		}}
	}}
}}

# our latest action, for Our Last Move (actor scope; the action sets local spec_rv_did_amt and spec_rv_did_cost)
spec_rv_did = {{
	set_variable = {{ name = spec_rv_did value = $CODE$ }}
	set_variable = {{ name = spec_rv_did_on value = scope:target }}
	set_variable = {{ name = spec_rv_did_ok value = 1 }}
	if = {{
		limit = {{ has_local_variable = spec_rv_ok }}
		set_variable = {{ name = spec_rv_did_ok value = local_var:spec_rv_ok }}
	}}
	set_variable = {{ name = spec_rv_did_amt value = 0 }}
	if = {{
		limit = {{ has_local_variable = spec_rv_did_amt }}
		set_variable = {{ name = spec_rv_did_amt value = local_var:spec_rv_did_amt }}
	}}
	set_variable = {{ name = spec_rv_did_cost value = 0 }}
	if = {{
		limit = {{ has_local_variable = spec_rv_did_cost }}
		set_variable = {{ name = spec_rv_did_cost value = local_var:spec_rv_did_cost }}
	}}
	set_variable = {{ name = spec_rv_did_recent days = 365 }}
	if = {{
		limit = {{ is_player = yes }}
		spec_rv_ui = yes
	}}
}}

# Bear Raid's confidence hit, in the scope that takes it
{raid_expiry_effects()}
spec_rv_raided = {{
	spec_rv_migrate_raid = yes
	set_local_variable = {{ name = spec_rv_pm value = {round(RAID_HIT / RAID_MONTHS, 3):g} }}
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
	random_company = {{  # rattles a blue chip (bluechips.RATTLE_DAYS)
		limit = {{
			has_variable = spec_blue_chip
			NOT = {{ has_variable = spec_bc_fragile }}
		}}
		{BC.timed_status('spec_bc_fragile', BC.RATTLE_DAYS)}
	}}
	if = {{
		limit = {{ this = scope:spec_rv_actor }}
		set_variable = {{ name = spec_rv_raider value = scope:target }}
	}}
	else = {{
		set_variable = {{ name = spec_rv_raider value = scope:spec_rv_actor }}
	}}
	spec_rv_register_raid = yes
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
	set_local_variable = {{ name = spec_rv_did_amt value = {{ value = local_var:spec_rv_pm multiply = {RAID_MONTHS} }} }}
	set_local_variable = {{ name = spec_rv_did_cost value = spec_rv_cost }}
	spec_rv_log = {{ CODE = 1 }}
{_ok(chr(9))}{_log('act=raid', chr(9))}	}}
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
	set_local_variable = {{ name = spec_rv_did_amt value = local_var:spec_rv_share }}
	set_local_variable = {{ name = spec_rv_did_cost value = spec_rv_lure_debt }}
	spec_rv_log = {{ CODE = 2 }}
{_ok(chr(9))}{_log('act=lure', chr(9))}	}}
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
{_half("spec_rv_t", chr(9) * 2)}		set_local_variable = {{ name = spec_rv_before value = var:spec_centre_trust }}
{_lose("local_var:spec_rv_t", chr(9) * 2, "press_hit")}		set_local_variable = {{ name = spec_rv_t value = {{ value = local_var:spec_rv_before subtract = var:spec_centre_trust }} }}
	}}
	set_local_variable = {{ name = spec_rv_roll value = {{ fixed_range = {{ min = 0 max = 100 }} }} }}
	scope:target = {{ set_local_variable = {{ name = spec_rv_x value = spec_rv_press_expose }} }}
	if = {{
		limit = {{ local_var:spec_rv_roll < local_var:spec_rv_x }}
		set_local_variable = {{ name = spec_rv_ok value = -1 }}
		change_relations = {{ country = scope:target value = -{PRESS_REL} }}
{_lose(PRESS_TRUST, chr(9) * 2, "press_exposed")}	}}
	if = {{
		limit = {{ local_var:spec_rv_ok = 1 }}
		spec_rv_push = {{ BY = scope:spec_rv_actor ON = scope:target }}
	}}
	else = {{
		spec_rv_push = {{ BY = scope:target ON = scope:spec_rv_actor }}
	}}
	set_local_variable = {{ name = spec_rv_did_amt value = local_var:spec_rv_t }}
	if = {{
		limit = {{ local_var:spec_rv_ok = -1 }}
		set_local_variable = {{ name = spec_rv_did_amt value = {PRESS_TRUST} }}
	}}
	spec_rv_log = {{ CODE = 3 }}
{_ok(chr(9))}{_log('act=press', chr(9))}	}}
}}

spec_rv_hold = {{
	custom_tooltip = spec_rv_hold_fx
	hidden_effect = {{
	save_scope_as = spec_rv_actor
	set_local_variable = {{ name = spec_rv_did_cost value = spec_rv_cost }}
	add_treasury = spec_rv_cost_neg
	add_to_variable_list = {{ name = spec_rv_cd_hold target = scope:target days = {CD_DAYS} }}
	spec_rv_unpush = {{ BY = scope:target ON = scope:spec_rv_actor }}
	spec_rv_did = {{ CODE = 4 }}
{_log('act=hold', chr(9))}	}}
}}

spec_rv_shore = {{
	custom_tooltip = spec_rv_shore_fx
	hidden_effect = {{
	set_local_variable = {{ name = spec_rv_did_cost value = spec_rv_cost }}
	add_treasury = spec_rv_cost_neg
	# ponytail: a list's days take no script value, so two lengths: the Safe Harbour's (centres.NX, shore 1.4) or the
	# plain one; more steps here if more specialities lengthen it
	if = {{
		limit = {{ spec_nx_shore > 1.05 }}
		add_to_variable_list = {{ name = spec_rv_shield target = scope:target days = {round(SHORE_MONTHS * 30 * 1.4)} }}
		set_local_variable = {{ name = spec_rv_until value = {{ value = game_date add = {round(SHORE_MONTHS * 30 * 1.4)} }} }}
	}}
	else = {{
		add_to_variable_list = {{ name = spec_rv_shield target = scope:target days = {SHORE_MONTHS * 30} }}
		set_local_variable = {{ name = spec_rv_until value = {{ value = game_date add = {SHORE_MONTHS * 30} }} }}
	}}
	add_to_variable_list = {{ name = spec_rv_cd_shore target = scope:target days = {SHORE_CD * 365} }}
	add_to_variable_map = {{ name = spec_rv_protected_until key = scope:target value = local_var:spec_rv_until }}
	set_local_variable = {{ name = spec_rv_did_amt value = {{ value = local_var:spec_rv_until subtract = game_date }} }}
	set_local_variable = {{ name = spec_rv_ok value = 1 }}
	spec_rv_did = {{ CODE = 5 }}
	set_local_variable = {{ name = spec_rv_until value = {{ value = game_date add = {SHORE_CD * 365} }} }}
	add_to_variable_map = {{ name = spec_rv_shore_until key = scope:target value = local_var:spec_rv_until }}
{_log('act=shore', chr(9))}	}}
}}

# the AI against scope:target, every AI_EVERY days and one move a look across all its contests, by the player's rules (cooldowns, costs), from where its contest
# stands (spec_rv_ai_p, its side). It moves when the situation calls for it: just hit by this rival, losing, the
# bar near a result's edge, or not yet winning in the contest's last {AI_LATE} years. Else it waits.
# The move: Shore Up against whoever just hit it; nothing while safely decisive; else undo their push (sure), else push:
# Lure most (it cannot fail), Press next, a Bear Raid mostly when our score is the higher (it fails less)
spec_rv_ai_act = {{
	save_scope_as = spec_rival_me
{LG_N}	scope:target = {{ set_local_variable = {{ name = spec_rv_ai_p value = spec_rv_rope }} }}
	if = {{
		limit = {{
			NOT = {{ has_local_variable = spec_rv_ai_moved }}
			OR = {{
				has_global_variable = spec_rv_ai_force
				AND = {{ has_variable = spec_rv_hit_recent exists = var:spec_rv_hit_by var:spec_rv_hit_by = scope:target }}
				local_var:spec_rv_ai_p < -{DRAW:g}
				AND = {{ spec_rv_age_t >= {ROUND - AI_LATE} local_var:spec_rv_ai_p < {DRAW:g} }}
{"".join(f"				AND = {{ local_var:spec_rv_ai_p >= {round(e - AI_NEAR, 3):g} local_var:spec_rv_ai_p <= {round(e + AI_NEAR, 3):g} }}{chr(10)}" for e in (-DECISIVE, -DRAW, DRAW, DECISIVE))}			}}
		}}
{LG_E}		spec_rv_ai_move = yes
	}}
}}

# one AI move (spec_rv_ai_act): only what it can pay for (money with AI_RESERVE times the cost in reserve, Press with
# that much influence to spare), leaning on the actions its specialities strengthen (spec_nx_<action> above 1)
spec_rv_ai_move = {{
	if = {{
		limit = {{
			has_variable = spec_rv_hit_recent
			exists = var:spec_rv_hit_by
			var:spec_rv_hit_by = scope:target
			spec_can_rv_shore = yes
			gold_reserves >= spec_rv_ai_money
		}}
		spec_rv_shore = yes
{LG_SHORE}		set_local_variable = {{ name = spec_rv_ai_moved value = 1 }}
	}}
	else_if = {{
		limit = {{ local_var:spec_rv_ai_p >= {DECISIVE + PUSH:g} }}
{LG_WAIT}	}}
	else_if = {{
		limit = {{
			spec_can_rv_hold = yes
			gold_reserves >= spec_rv_ai_money
		}}
		spec_rv_hold = yes
{LG_HOLD}		set_local_variable = {{ name = spec_rv_ai_moved value = 1 }}
	}}
	else_if = {{
		limit = {{
			OR = {{
				AND = {{ spec_can_rv_lure = yes spec_lev < {AI_LEV} }}
				AND = {{ spec_can_rv_press = yes influence > {PRESS_INFL} }}
				AND = {{ spec_can_rv_raid = yes gold_reserves >= spec_rv_ai_money }}
			}}
		}}
{LG_PUSH}{LG_LURE}		set_local_variable = {{ name = spec_rv_ai_moved value = 1 }}
		random_list = {{
			3 = {{
				trigger = {{ spec_can_rv_lure = yes spec_lev < {AI_LEV} }}
				modifier = {{
					if = {{
						limit = {{ spec_nx_lure > 1.05 }}
						add = 3
					}}
				}}
				spec_rv_lure = yes
			}}
			2 = {{
				trigger = {{ spec_can_rv_press = yes influence > {PRESS_INFL} }}
					modifier = {{
					if = {{
						limit = {{ spec_nx_press > 1.05 }}
						add = 3
					}}
					if = {{
						limit = {{ scope:target = {{ spec_rv_press_expose <= 20 }} }}
						add = 2
					}}
					if = {{
						limit = {{ scope:target = {{ spec_rv_press_expose >= 50 }} }}
						add = -1
					}}
				}}
				spec_rv_press = yes
			}}
			1 = {{
				trigger = {{ spec_can_rv_raid = yes gold_reserves >= spec_rv_ai_money }}
				modifier = {{
					if = {{
						limit = {{ var:spec_centre_score >= scope:target.var:spec_centre_score }}
						add = 2
					}}
					if = {{
						limit = {{ spec_nx_raid > 1.05 }}
						add = 3
					}}
				}}
				spec_rv_raid = yes
			}}
		}}
	}}
}}

spec_rv_ai = {{
	every_country = {{
		limit = {{
			is_player = no
			{exch}
			NOT = {{ has_variable = spec_rv_ai_wait }}
		}}
		if = {{  # its own clock, the first one spread over the months so the AIs do not all move on one day
			limit = {{ NOT = {{ has_variable = spec_rv_ai_seen }} }}
			set_variable = spec_rv_ai_seen
			random_list = {{
{"".join(f"				1 = {{ set_variable = {{ name = spec_rv_ai_wait days = {d - 5} }} }}{chr(10)}" for d in range(0, AI_EVERY, 30) if d)}				1 = {{ }}
			}}
		}}
	}}
	every_country = {{
		limit = {{
			is_player = no
			{exch}
			NOT = {{ has_variable = spec_rv_ai_wait }}
		}}
		set_variable = {{ name = spec_rv_ai_wait days = {AI_EVERY - 5} }}  # 5 short: checked monthly
		save_scope_as = spec_rv_ai_me
		remove_local_variable = spec_rv_ai_moved  # one move a look, in whichever contest calls for it first
{LG_INIT}		every_in_list = {{
			variable = spec_rv_chosen
			limit = {{ is_country_alive = yes {exch} }}
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
		every_country = {{
			limit = {{
				is_country_alive = yes {exch}
				is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_ai_me }}
				NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }}
			}}
			save_scope_as = target
			scope:spec_rv_ai_me = {{ spec_rv_ai_act = yes }}
		}}
{LG_OUT}		spec_rv_ai_pick = yes
	}}
}}

# an AI's look (spec_rv_ai, every AI_EVERY days on its own clock; 2026-11-19: once a year, all on one day): it drops
# rivals out of reach, without an Exchange, rivalled by more than AI_CAP, or, early in a round, too far ahead to catch;
# then may fill one free slot among Exchanges fewer than AI_CAP rival (else everyone tied below one Exchange piles onto
# it) that it starts no further behind than AI_REACH, the best prize first: at once if one would start in its favour,
# else on AI_PICK_CHANCE
spec_rv_ai_pick = {{
	if = {{
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
					NOT = {{ has_variable = spec_centre_trust }}
					# (Standing drifting out of reach no longer drops one: quitting is a loss now, spec_rv_forfeit)
					any_country = {{ count = {AI_CAP + 1} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }}
					# no longer Engaged in their capital's region (INTEREST_TIER, which came after many contests began)
					NOT = {{ exists = capital }}
					scope:spec_rv_ai_me = {{ NOT = {{ has_strategic_region_interest_tier = {{ strategic_region = prev.capital.region value >= {INTEREST_TIER} }} }} }}
					# cutting a losing contest: a plain Loss now beats a Decisive Loss later; once the bar shows a
					# Decisive Loss quitting costs the same as staying, so it stays and hopes to recover
					AND = {{
						{exch}
						spec_rv_rope <= {AI_CUT}
						spec_rv_rope > -{DECISIVE}
						scope:spec_rv_ai_me = {{ NOT = {{ is_target_in_variable_list = {{ name = spec_rv_keep target = prev }} }} }}
					}}
				}}
			}}
			save_temporary_scope_as = spec_rv_x
			save_scope_as = target
{_settle_log('drop', 'spec_rv_ai_me', 'spec_rv_rope', chr(9) * 3)}			scope:spec_rv_ai_me = {{
				# a contest the Interest rule ends is dropped without a forfeit
				if = {{
					limit = {{ scope:spec_rv_x = {{ exists = capital }} has_strategic_region_interest_tier = {{ strategic_region = scope:spec_rv_x.capital.region value >= {INTEREST_TIER} }} }}
					spec_rv_forfeit = yes
				}}
				spec_rv_drop_pair = yes
			}}
		}}
		spec_rv_count = yes
		set_local_variable = {{ name = spec_rv_go value = 0 }}
		random = {{  # at most one new competitor a look, so the AIs fill their slots over years (2026-11-19: filled all at once)
			chance = {AI_PICK_CHANCE}
			set_local_variable = {{ name = spec_rv_go value = 1 }}
		}}
		if = {{  # an opening: an Exchange it may name that it would beat as things stand
			limit = {{ any_country = {{ is_country_alive = yes {exch} NOT = {{ this = scope:spec_rv_ai_me }} NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} var:spec_exch_stand >= local_var:spec_rv_lo var:spec_exch_stand <= local_var:spec_rv_hi spec_rv_rope >= {DRAW} NOT = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_ai_me }} }} exists = capital scope:spec_rv_ai_me = {{ has_strategic_region_interest_tier = {{ strategic_region = prev.capital.region value >= {INTEREST_TIER} }} }} NOT = {{ any_country = {{ count = {AI_CAP} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }} }}
			set_local_variable = {{ name = spec_rv_go value = 1 }}
		}}
		if = {{
			limit = {{ local_var:spec_rv_go = 1 }}
			if = {{
				limit = {{
					var:spec_rv_n_chosen < spec_rv_slots
					any_country = {{ is_country_alive = yes {exch} NOT = {{ this = scope:spec_rv_ai_me }} NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} var:spec_exch_stand >= local_var:spec_rv_lo var:spec_exch_stand <= local_var:spec_rv_hi spec_rv_rope >= {AI_REACH} NOT = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_ai_me }} }} exists = capital scope:spec_rv_ai_me = {{ has_strategic_region_interest_tier = {{ strategic_region = prev.capital.region value >= {INTEREST_TIER} }} }} NOT = {{ any_country = {{ count = {AI_CAP} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }}
				}}
				ordered_country = {{
					limit = {{ is_country_alive = yes {exch} NOT = {{ this = scope:spec_rv_ai_me }} NOT = {{ scope:spec_rv_ai_me = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} var:spec_exch_stand >= local_var:spec_rv_lo var:spec_exch_stand <= local_var:spec_rv_hi spec_rv_rope >= {AI_REACH} NOT = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = scope:spec_rv_ai_me }} }} exists = capital scope:spec_rv_ai_me = {{ has_strategic_region_interest_tier = {{ strategic_region = prev.capital.region value >= {INTEREST_TIER} }} }} NOT = {{ any_country = {{ count = {AI_CAP} is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }}
					order_by = spec_rv_ai_pick_v
					position = 0
					save_scope_as = target
				}}
				spec_rv_choose = yes
{_log('pick', chr(9) * 4)}			}}
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
{t}# contest clocks (spec_rv_age_<k>): an old save's pairs take the shared round's year; dropped rivals lose theirs
{t}every_country = {{
{t}	limit = {{ has_variable_list = spec_rv_chosen }}
{t}	save_temporary_scope_as = spec_rv_c
{t}	every_in_list = {{
{t}		variable = spec_rv_chosen
{t}		limit = {{ NOT = {{ scope:spec_rv_c = {{ OR = {{ {" ".join(f"is_target_in_variable_list = {{ name = spec_rv_age_{k} target = prev }}" for k in range(MONTHS))} }} }} }} }}
{t}		save_temporary_scope_as = spec_rv_x
{t}		scope:spec_rv_c = {{
{"".join(f"{t}			{'if' if k == 1 else 'else_if'} = {{ limit = {{ has_global_variable = spec_rv_round global_var:spec_rv_round = {k} }} add_to_variable_list = {{ name = spec_rv_age_{12 * k} target = scope:spec_rv_x }} }}{chr(10)}" for k in range(1, ROUND))}{t}			else = {{ add_to_variable_list = {{ name = spec_rv_age_0 target = scope:spec_rv_x }} }}
{t}		}}
{t}	}}
{"".join(f"""{t}	every_in_list = {{
{t}		variable = spec_rv_age_{k}
{t}		limit = {{ NOT = {{ scope:spec_rv_c = {{ is_target_in_variable_list = {{ name = spec_rv_chosen target = prev }} }} }} }}
{t}		save_temporary_scope_as = spec_rv_x
{t}		scope:spec_rv_c = {{ remove_list_variable = {{ name = spec_rv_age_{k} target = scope:spec_rv_x }} }}
{t}	}}
""" for k in range(MONTHS))}{t}}}
{t}# once: a save from before the clocks counted months has years in spec_rv_age_1..4; each becomes its months
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_rv_months }} }}
{t}	set_global_variable = spec_rv_months
{t}	every_country = {{
{t}		limit = {{ has_variable_list = spec_rv_chosen }}
{"".join(f"""{t}		every_in_list = {{
{t}			variable = spec_rv_age_{k}
{t}			save_temporary_scope_as = spec_rv_x
{t}			prev = {{ add_to_variable_list = {{ name = spec_rv_age_{12 * k} target = scope:spec_rv_x }} }}
{t}		}}
{t}		clear_variable_list = spec_rv_age_{k}
""" for k in range(ROUND - 1, 0, -1))}{t}	}}
{t}}}
{t}# spread thin: each side's contests (a pair that named each other counts twice), then what its score counts for
{t}every_country = {{
{t}	limit = {{ has_variable = spec_rv_n_all }}
{t}	remove_variable = spec_rv_n_all
{t}}}
{t}every_country = {{
{t}	limit = {{ has_variable_list = spec_rv_chosen }}
{t}	save_temporary_scope_as = spec_rv_f
{t}	every_in_list = {{
{t}		variable = spec_rv_chosen
{t}		spec_rv_tick = yes
{t}		scope:spec_rv_f = {{ spec_rv_tick = yes }}
{t}	}}
{t}}}
{t}every_country = {{
{t}	limit = {{ OR = {{ has_variable = spec_rv_n_all has_variable = spec_rv_focus }} }}
{t}	if = {{
{t}		limit = {{ has_variable = spec_rv_n_all }}
{t}		set_variable = {{ name = spec_rv_focus value = spec_rv_focus_sv }}
{t}	}}
{t}	else = {{
{t}		remove_variable = spec_rv_focus
{t}	}}
{t}}}
{t}# monthly: every contest's clock moves a month, and those at ROUND years settle (spec_rv_epoch_day: when, for the countdowns)
{t}if = {{
{t}	limit = {{ has_global_variable = spec_rival_started }}
{t}	set_global_variable = {{ name = spec_rv_epoch_day value = game_date }}
{t}	spec_rival_contest = yes
{t}}}
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_rival_year }} }}
{t}	set_global_variable = {{ name = spec_rival_year days = 365 }}
{t}	set_global_variable = {{ name = spec_rv_epoch_year value = year }}
{t}	set_global_variable = {{ name = spec_rv_epoch_month value = {{ value = month add = 1 }} }}
{t}	if = {{
{t}		limit = {{ NOT = {{ has_global_variable = spec_rival_started }} }}
{t}		set_global_variable = {{ name = spec_rv_epoch_day value = game_date }}
{t}	}}
{t}	if = {{
{t}		limit = {{ has_global_variable = spec_rival_started }}
{t}		every_country = {{
{t}			limit = {{ has_variable = spec_rv_raid_year }}
{t}			remove_variable = spec_rv_raid_year
{t}		}}
{_year_log(t + chr(9) * 2)}{t}	}}
{t}	set_global_variable = spec_rival_started
{t}}}
{t}if = {{  # each AI on its own AI_EVERY-day clock (spec_rv_ai_wait), checked monthly
{t}	limit = {{ has_global_variable = spec_rival_started }}
{t}	spec_rv_ai = yes
{t}}}
{t}every_country = {{
{t}	limit = {{ OR = {{ has_variable_list = spec_rv_observed_in has_variable_list = spec_rv_observed_out }} }}
{t}	clear_variable_list = spec_rv_observed_in
{t}	clear_variable_list = spec_rv_observed_out
{t}}}
{t}every_country = {{
{t}	limit = {{ has_variable_list = spec_rv_chosen }}
{t}	save_temporary_scope_as = spec_observed_challenger
{t}	every_in_list = {{
{t}		variable = spec_rv_chosen
{t}		limit = {{ is_country_alive = yes }}
{t}		save_temporary_scope_as = spec_observed_opponent
{t}		scope:spec_observed_challenger = {{ add_to_variable_list = {{ name = spec_rv_observed_out target = scope:spec_observed_opponent }} }}
{t}		add_to_variable_list = {{ name = spec_rv_observed_in target = scope:spec_observed_challenger }}
{t}	}}
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
				spec_rv_migrate_raid = yes
				if = {{
					limit = {{ NOT = {{ has_variable = spec_rv_raid_year }} }}
					set_variable = {{ name = spec_rv_raid_year value = 0 }}
				}}
				set_local_variable = {{
					name = spec_rv_h
					value = spec_rv_raid_applied
				}}
				change_variable = {{ name = spec_rv_raid_year add = local_var:spec_rv_h }}
				set_variable = {{ name = spec_c_rival value = {{ value = local_var:spec_rv_h multiply = -1 }} }}
				spec_rv_expire_raids = yes
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
					limit = {{ spec_rv_active_lure = yes }}
					set_local_variable = {{ name = spec_rv_amt value = {{ value = spec_pool_month multiply = var:spec_rv_lure_share max = investment_pool min = 0 }} }}
					var:spec_rv_lurer = {{ add_investment_pool = local_var:spec_rv_amt }}
					change_local_variable = {{ name = spec_rv_amt multiply = -1 }}
					add_investment_pool = local_var:spec_rv_amt
				}}
				change_variable = {{ name = spec_rv_lure add = -1 }}
				if = {{
					# a lurer gone (annexed, or never stored) ends it: the row showed a blank flag (2026-11-16)
					limit = {{
						OR = {{
							var:spec_rv_lure <= 0
							spec_rv_active_lure = no
						}}
					}}
					remove_variable = spec_rv_lure
					remove_variable = spec_rv_lurer
					remove_variable = spec_rv_lure_share
				}}
			}}
"""


def sguis():
    act = "".join(f"\nspec_sgui_rv_{a} = {{\n\tscope = country\n\tis_valid = {{ spec_can_rv_{a} = yes }}\n\teffect = {{ spec_rv_{a} = yes }}\n}}\n"
                  for a in ACTIONS + ("hold", "shore"))
    tests = {"active_lure": "spec_rv_active_lure = yes", "pair": "spec_rv_pair = yes", "out": "spec_rv_chose = yes", "in": "spec_rv_chosen_by = yes",
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

    # exists first: a list row can be drawn for a frame before its country is (2026-11-19, 22 errors on opening the picker)
    act += ("\nspec_sgui_rv_toggle = {\n\tscope = country\n\tis_shown = {\n\t\texists = scope:target\n\t\tNOT = { this = scope:target }\n"
            "\t\tOR = {\n\t\t\tspec_rv_chose = yes\n\t\t\tscope:target = { has_variable = spec_exch_stand }\n\t\t}\n\t}\n"
            "\tis_valid = { exists = scope:target spec_can_rv_toggle = yes }\n"
            "\teffect = {\n\t\tif = {\n\t\t\tlimit = { spec_rv_chose = yes spec_can_rv_end = yes }\n\t\t\tspec_rv_end = yes\n\t\t}\n"
            "\t\telse_if = {\n\t\t\tlimit = { spec_rv_chose = no spec_can_rv_choose = yes }\n\t\t\tspec_rv_choose = yes\n\t\t}\n\t}\n}\n"
            "\nspec_sgui_rv_end = {\n\tscope = country\n\tis_shown = { spec_rv_chose = yes }\n"
            "\tis_valid = { spec_can_rv_end = yes }\n\teffect = { spec_rv_end = yes }\n}\n")
    # the contest picker's list (_picker), filled on opening: every other Exchange we don't already contest, the ones
    # spec_can_rv_choose allows first, each part by score
    every = lambda ok: ("\t\tordered_country = {\n\t\t\tlimit = { is_country_alive = yes has_variable = spec_exch_stand NOT = { this = root } }\n"
                        "\t\t\torder_by = spec_centre_order\n\t\t\tmax = 999\n\t\t\tcheck_range_bounds = no\n\t\t\tsave_scope_as = target\n"
                        f"\t\t\troot = {{\n\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ spec_rv_chose = no {ok} }}\n"
                        "\t\t\t\t\tadd_to_variable_list = { name = spec_rv_cands target = scope:target }\n\t\t\t\t}\n\t\t\t}\n\t\t}\n")
    act += ("\nspec_sgui_rv_pick = {\n\tscope = country\n\teffect = {\n\t\tclear_variable_list = spec_rv_cands\n"
            + every("spec_can_rv_choose = yes") + every("NOT = { spec_can_rv_choose = yes }") + "\t}\n}\n")
    return act + "".join(f"\nspec_sgui_rv_is_{k} = {{\n\tscope = country\n\tis_shown = {{ "
                         f"{'' if k == 'active_lure' else 'exists = scope:target '}{t} }}\n}}\n" for k, t in tests.items())


def picture():
    """The rival event's picture: the mod's painting once it exists, else vanilla's videos by region."""
    if icons.has("picture_rival"):
        return f'\tevent_image = {{\n\t\ttexture = "{icons.path("picture_rival")}"\n\t}}\n'
    return __import__("stories").pictures({"west": "europenorthamerica_capitalists_meeting", "mideast": "middleeast_upperclass_party"})


def events():
    pick = lambda code, ok: f"var:spec_rv_hit ?= {code} var:spec_rv_hit_ok ?= {ok}"
    descs = [(1, 1), (1, 0), (2, 1), (3, 1), (3, -1)]
    by = lambda part: "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_rival.1.{part}{c}{'n' if o < 0 else o}\n"
                              f"\t\t\t\ttrigger = {{ {pick(c, o)} }}\n\t\t\t}}\n" for c, o in descs)
    title, flavor = by("t"), by("f")
    big = ("scope:target ?= { has_variable = spec_exch_stand } "
           "OR = { NOT = { has_variable = spec_exch_stand } scope:target.var:spec_exch_stand > var:spec_exch_stand }")
    small = ("has_variable = spec_exch_stand "
             "OR = { scope:target ?= { NOT = { has_variable = spec_exch_stand } } var:spec_exch_stand > scope:target.var:spec_exch_stand }")
    desc = "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_rival.1.d{c}{'n' if o < 0 else o}_{k}\n"
                   f"\t\t\t\ttrigger = {{ {pick(c, o)} {cond} }}\n\t\t\t}}\n"
                   for c, o in descs for k, cond in (("big", big), ("small", small), ("even", "")))
    back = " ".join(f"AND = {{ var:spec_rv_hit = {i} spec_rv_pay_{a} = yes }}" for i, a in enumerate(ACTIONS, 1))
    do = "".join(f"\t\tif = {{\n\t\t\tlimit = {{ var:spec_rv_hit = {i} }}\n\t\t\tcustom_tooltip = spec_rival.1.a_{i}\n"
                 f"\t\t\tspec_rv_{a} = yes\n\t\t}}\n" for i, a in enumerate(ACTIONS, 1))
    return f"""namespace = spec_rival

# a rival has acted against us (rivals.py): answer in kind, shore up, or keep calm
spec_rival.1 = {{
	type = country_event
	placement = root
	# each move its own title, scene and saying; the scene opens on who struck and the state of our market (loc)
	title = {{
		first_valid = {{
{title}			desc = spec_rival.1.t
		}}
	}}
	desc = {{
		# the state of our market, then who struck (by Standing) and the move in one key: only one part of an event's
		# text keeps ROOT and SCOPE, so names in a separate opening part came out blank (2026-11-16)
		first_valid = {{
			triggered_desc = {{
				desc = SPEC_RV_EV_PANIC
				trigger = {{ has_variable = spec_panic }}
			}}
			triggered_desc = {{
				desc = SPEC_RV_EV_MANIA
				trigger = {{ has_variable = spec_conf var:spec_conf >= 80 }}
			}}
			desc = SPEC_RV_EV_NONE
		}}
		first_valid = {{
{desc}			desc = spec_rival.1.desc
		}}
	}}
	flavor = {{
		first_valid = {{
{flavor}			desc = spec_rival.1.f
		}}
	}}
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
	option = {{  # the counter fitted to the move: steady the market, match their terms, answer in our papers
		name = spec_rival.1.d
		trigger = {{ var:spec_rv_hit ?= 1 }}
		custom_tooltip = spec_rival.1.d_tt
		hidden_effect = {{ add_treasury = spec_rv_counter_cost_neg }}
		hidden_effect = {{
			if = {{
				limit = {{ has_variable = spec_rv_raid_pm }}
				spec_rv_migrate_raid = yes
				set_variable = {{ name = spec_rv_raid_pm value = 0 }}
{"".join(f"\t\t\t\tif = {{ limit = {{ has_variable = spec_rv_due_{n} }} change_variable = {{ name = spec_rv_due_{n} multiply = 0.5 }} change_variable = {{ name = spec_rv_raid_pm add = var:spec_rv_due_{n} }} }}{chr(10)}" for n in RAID_TERMS)}
			}}
		}}
		ai_chance = {{
			base = 1
		}}
	}}
	option = {{
		name = spec_rival.1.e
		trigger = {{ var:spec_rv_hit ?= 2 }}
		custom_tooltip = spec_rival.1.e_tt
		hidden_effect = {{ add_treasury = spec_rv_counter_cost_neg }}
		hidden_effect = {{
			if = {{
				limit = {{ has_variable = spec_rv_lure_share }}
				change_variable = {{ name = spec_rv_lure_share multiply = 0.5 }}
			}}
		}}
		ai_chance = {{
			base = 1
		}}
	}}
	option = {{
		name = spec_rival.1.g
		trigger = {{ var:spec_rv_hit ?= 3 }}
		custom_tooltip = spec_rival.1.g_tt
		hidden_effect = {{ add_treasury = spec_rv_counter_cost_neg }}
		hidden_effect = {{
			if = {{
				limit = {{ has_variable = spec_centre_trust }}
{_gain(round(PRESS_TRUST * 0.6, 2), chr(9) * 4, "press_counter")}			}}
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
				set_local_variable = {{ name = spec_rv_calm value = 1 }}
				if = {{
					limit = {{ exists = scope:target scope:target = {{ has_variable = spec_exch_stand }} }}
					set_local_variable = {{ name = spec_rv_calm value = {{ value = scope:target.var:spec_exch_stand multiply = {CALM_STAND:g} add = 1 }} }}
				}}
{_gain(f"{{ value = local_var:spec_rv_calm multiply = {CALM_GAIN} }}", chr(9) * 4, "press_calm")}			}}
		}}
		ai_chance = {{
			base = 1
		}}
	}}
}}
"""


# vanilla has no modifier_newspaper_negative (2026-11-19: 71 missing-texture errors at load)
PRESS_ICON = icons.path("rival_press") if icons.has("rival_press") else "gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds"
MODIFIERS = "".join(f"""spec_rv_press_{n} = {{
	icon = {PRESS_ICON}
	country_influence_add = -{PRESS_INFL}
}}

""" for n in range(1, SLOTS + 1)) + """spec_rv_upkeep = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_influence_add = -1
}
"""


def diplo():
    """Compete With / Stop Competing as diplomatic actions, so a player can start a contest by right-clicking a country
    on the map, as vanilla's rivalry (2026-11-16). The same triggers and effects as the Exchanges list's toggle, with
    vanilla's scope:target_country renamed. The AI keeps its own monthly choosing (pass_), never these."""
    t = triggers()
    body = lambda name: t[t.index(name + " = {") + len(name) + 4:t.index("\n}\n", t.index(name + " = {"))]
    tc = lambda s: s.replace("scope:target", "scope:target_country")
    ai = "\tai = {\n\t\tevaluation_chance = { value = 0 }\n\t\twill_propose = { always = no }\n\t}\n"
    exch = "has_variable = spec_exch_stand"
    chose = "is_target_in_variable_list = { name = spec_rv_chosen target = scope:target_country }"
    act = lambda key, tex, pot, pos, eff: f"""{key} = {{
	groups = {{
		general
	}}
	requires_approval = no
	should_notify_third_parties = no
	show_effect_in_tooltip = yes
	texture = "{tex}"
	potential = {{
		{exch}
		scope:target_country = {{ {exch} }}
		{pot}
	}}
	possible = {{{tc(pos)}
	}}
	accept_effect = {{
		scope:target_country = {{ save_scope_as = target }}
		{eff}
	}}
{ai}}}
"""
    return ("# Compete With / Stop Competing on another Exchange (rivals.py diplo): the Exchanges list's toggle, from the map\n"
            + act("spec_rv_compete", icons.RIVALRY, f"NOT = {{ {chose} }}", body("spec_can_rv_choose"), "spec_rv_choose = yes")
            + "\n" + act("spec_rv_stop", icons.RIVALRY_OFF, chose, body("spec_can_rv_end"), "spec_rv_end = yes"))


def interest_tier():
    """Vanilla's Interest tiers list what each allows; copies of vanilla's blocks, read from the game, add Exchange
    contests to the list of every tier from INTEREST_TIER up. REPLACE, since INJECT refuses a second on_activate
    (2026-11-16 error log)."""
    src = Path(icons.GAME_GFX, "common/interest_tier_types/interest_tier_types.txt").read_text(encoding="utf-8-sig")
    out = "# Exchange contests need one of these tiers in the rival's capital region (rivals.py INTEREST_TIER)\n"
    for m in re.finditer(r"(?m)^(interest_tier_\w+) = \{\n.*?\n\}\n", src, re.S):
        block = m.group(0)
        if int(re.search(r"\brank = (\d+)", block).group(1)) < INTEREST_TIER:
            continue
        # into on_activate, which is not always last: from Influential on, on_deactivate follows it
        act = re.search(r"\ton_activate = \{\n.*?\n\t\}\n", block, re.S)
        assert block.count("on_activate = {") == 1 and act, f"vanilla's {m.group(1)} changed shape"
        cut = act.end() - len("\t}\n")
        out += "REPLACE:" + block[:cut] + "\t\tcustom_tooltip_no_bullet = spec_rv_interest_tier_effect\n" + block[cut:] + "\n"
    assert out.count("REPLACE:") == 4, out.count("REPLACE:")
    return out


def build(write):
    write("common/interest_tier_types/zzz_spec_interest_tiers.txt", interest_tier())
    write("common/diplomatic_actions/spec_rival_actions.txt", diplo())
    write("common/scripted_triggers/spec_rival_triggers.txt", triggers())
    write("common/script_values/spec_rival_values.txt", values())
    write("common/scripted_effects/spec_rival_effects.txt", effects())
    write("common/scripted_guis/spec_rival_sguis.txt", sguis())
    write("events/spec_rival_events.txt", events())
    write("common/static_modifiers/spec_rival_modifiers.txt", MODIFIERS)


# -- interface --------------------------------------------------------------------------------------------------------

ROW_H = 44  # a row: the contest's result over its bar
# columns, (x, width): flag and name | the contest | actions (4 tariff items, then the toggle on our rivals' rows)
C_NAME, C_SCORE, C_LEFT, C_ACT = (0, 70), (72, 214), (288, 52), (342, W - 342)  # the flag alone names the country
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
    silhouette of our rival icon while off, and the icon in colour on vanilla's rotating glow while on. Greyed while it
    can't be used (slots full, the first year's lock), its tooltip says why: always enabled, every row looked clickable
    and a full set of slots made every click do nothing (2026-11-16)."""
    # ponytail: icon sizes matched by eye-maths: a 21px rival icon draws its object at ~18px, as the 22px Specialities
    # icons do; repaint-independent normalising in icons.build if more families need matching
    call = lambda what: CALL.format("rv_toggle", what)
    on = shown("rv_is_out")
    pos = f"\tposition = {{ {x} 0 }}\n" if x is not None else ""
    side = lambda vis, tex, sound: f"""	button_icon_round_action = {{
		visible = "[{vis}]"
		size = {{ 100% 100% }}
		enabled = "[{call('IsValid')}]"
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
	visible = "[And({CAN_MANAGE}, {call('IsShown')})]"
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


def _flag(x=6, ctx=None):
    """The country's flag, which opens it, with vanilla's country tooltip: the flag alone, no name."""
    dc = f'\tdatacontext = "[{ctx}]"\n' if ctx else ""
    return f"""button = {{
{dc}	position = {{ {x} 0 }}
	size = {{ 34 24 }}
	parentanchor = vcenter
	onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
	tooltipwidget = {{
		FancyTooltip_Country = {{}}
	}}
	tiny_flag = {{
		parentanchor = center
		alwaystransparent = yes
	}}
}}
"""


# the contest bar from our side (rivals' spec_rv_rope): the score lead as a share of the higher, plus our pushes less theirs


def _sum(terms):
    out = terms[0]
    for x in terms[1:]:
        out = f"Add_CFixedPoint({out}, {x})"
    return out


def contest_value(cache, script):
    # The player has precomputed rows. Observers can switch country at any time, so
    # evaluate the same script value with the row as root and the viewed country as its opponent.
    pair = f"GuiScope.SetRoot({THEM}).AddScope('spec_rival_me', {US})"
    return (f"Select_CFixedPoint(GetMetaPlayer.IsObserver, {pair}.ScriptValue('{script}'), "
            f"{THEM}.Var('{cache}').GetValueWithDefault({fx(0)}))")


def rope():
    return contest_value("spec_rv_ui_p", "spec_rv_rope")


def pushes(key):
    if key == "push":
        return contest_value("spec_rv_ui_us", "spec_rv_n_push_me")
    return contest_value("spec_rv_ui_them", "spec_rv_n_push_it")


PAIR = f"And(Country.IsValid, {shown('rv_is_pair')})"


def _score():
    """The contest as a tug of war, drawn as the mod's Market Confidence bar (market_tab.tier_scale) on vanilla's
    double direction bar: the result it would settle at now above it, then from the centre line the fill slides
    green toward us (left) or red toward them, with vanilla's glow and, while one side has pushed more, the changed
    value chevrons running its way. Dividers part the five results, the decisive ends are tinted, and vanilla's
    active level frame rings the one it sits in. Without their Exchange there is no contest."""
    import interest_list as il
    x, w = C_SCORE
    bw = w - 6
    # 0 all ours, 50 even, 100 theirs; a player's bar glides weekly to the month's figure (spec_rv_ui_shown)
    glided = rope().replace(f"{THEM}.Var('spec_rv_ui_p').GetValueWithDefault({fx(0)})",
                            f"{THEM}.Var('spec_rv_ui_shown').GetValueWithDefault({THEM}.Var('spec_rv_ui_p').GetValueWithDefault({fx(0)}))")
    assert glided != rope()
    at = f"Subtract_CFixedPoint({fx(50)}, Multiply_CFixedPoint({fx(50)}, {glided}))"
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
	visible = "[And({CAN_MANAGE}, {shown('rv_is_locked')})]"
	position = {{ {x + 20} 4 }}
	size = {{ 14 14 }}
	alwaystransparent = yes
	texture = "gfx/interface/buttons/button_icons/lock.dds"
}}
"""


# what rival actions run on our market: (variable, icon, months it runs, who did it)
CHIPS = (("raid", "raid", RAID_MONTHS, "spec_rv_raider"), ("lure", "lure", LURE_MONTHS, "spec_rv_lurer"))


def _action_visible(var):
    if var == "lure":
        return f"GetScriptedGui('spec_sgui_rv_is_active_lure').IsShown(GuiScope.SetRoot({US}).End)"
    return f"{US}.Var('spec_rv_{var}').IsSet"


def _us_row(var, pic, months, by):
    """One action running on us, as a table row: its icon and who did it, what it does, and its months on a bar."""
    left = f"{US}.Var('spec_rv_{var}').GetValue"
    return f"""widget = {{
	visible = "[{_action_visible(var)}]"
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_RV_US_{var.upper()}_TT"
{ind(HOVER, 1)}	icon = {{
		position = {{ 8 0 }}
		size = {{ 32 32 }}
		parentanchor = vcenter
		texture = "{icons.path('rival_' + pic)}"
	}}
{ind(_flag(44, f"{US}.Var('{by}').GetCountry"), 1) if var != 'raid' else ''}	textbox = {{
		position = {{ 84 4 }}
		size = {{ 294 20 }}
		align = left|nobaseline
		elide = right
		fontsize_min = 13
		text = "SPEC_RV_US_{var.upper()}"
	}}
	textbox = {{
		position = {{ 84 23 }}
		size = {{ 294 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_RV_US_{var.upper()}_FX"
	}}
	textbox = {{
		position = {{ 390 4 }}
		size = {{ {W - 402} 18 }}
		align = right|nobaseline
		using = fontsize_small
		text = "SPEC_RV_US_LEFT_{var.upper()}"
	}}
	widget = {{
		position = {{ 390 24 }}
		size = {{ {W - 402} 12 }}
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


_did = lambda n: f"EqualTo_CFixedPoint({US}.Var('spec_rv_did').GetValueWithDefault({fx(0)}), {fx(n)})"
DID = f"{US}.Var('spec_rv_did_recent').IsSet"


def _did_row():
    """Our Last Move: what we did to whom, whether it worked, what it did and what it cost; kept a year."""
    pics = "".join(f"""	icon = {{
		visible = "[{_did(i)}]"
		position = {{ 8 0 }}
		size = {{ 32 32 }}
		parentanchor = vcenter
		texture = "{icons.path('rival_' + a)}"
	}}
""" for i, a in enumerate(ACTIONS + ("hold", "shore"), 1))
    pics += ind(_flag(44, f"{US}.Var('spec_rv_did_on').GetCountry"), 1)
    return f"""widget = {{
	visible = "[{DID}]"
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_RV_DID_TT"
{ind(HOVER, 1)}{pics}	textbox = {{
		position = {{ 84 4 }}
		size = {{ 294 20 }}
		align = left|nobaseline
		elide = right
		fontsize_min = 13
		text = "SPEC_RV_DID"
	}}
	textbox = {{
		position = {{ 84 23 }}
		size = {{ {W - 96} 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_RV_DID_ROW"
	}}
	textbox = {{
		position = {{ 390 4 }}
		size = {{ {W - 402} 18 }}
		align = right|nobaseline
		using = fontsize_small
		text = "SPEC_RV_DID_COST"
	}}
}}
"""


def _last_row():
    pics = "".join(f"""	icon = {{
		visible = "[{_hit(i)}]"
		position = {{ 8 0 }}
		size = {{ 32 32 }}
		parentanchor = vcenter
		texture = "{icons.path('rival_' + a)}"
	}}
""" for i, a in enumerate(ACTIONS, 1))
    pics += ind(_flag(44, f"{US}.Var('spec_rv_hit_by').GetCountry"), 1)
    return f"""widget = {{
	visible = "[{LAST}]"
	size = {{ {W} {ROW_H} }}
	tooltip = "SPEC_RV_US_LAST_TT"
{ind(HOVER, 1)}{pics}	textbox = {{
		position = {{ 84 4 }}
		size = {{ 294 20 }}
		align = left|nobaseline
		elide = right
		fontsize_min = 13
		text = "SPEC_RV_US_LAST"
	}}
	textbox = {{
		position = {{ 84 23 }}
		size = {{ {W - 96} 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_RV_US_LAST_FX"
	}}
	textbox = {{
		position = {{ 390 4 }}
		size = {{ {W - 402} 18 }}
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
        some = f"Or({_action_visible(v)}, {some})"
    raiders = f"""flowcontainer = {{
	direction = horizontal
	visible = "[{_action_visible('raid')}]"
	datamodel = "[{US}.GetList('spec_rv_attackers')]"
	item = {{
		widget = {{
			size = {{ 40 26 }}
			datacontext = "[Scope.GetCountry]"
{ind(_flag(2), 3)}		}}
	}}
}}
"""
    rows = _us_row(*CHIPS[0]) + raiders + _us_row(*CHIPS[1]) + _last_row()
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
    return section("SPEC_RV_CARD_TITLE", "spec_hide_rv_us", body, right="SPEC_RV_ROUND", right_visible=CAN_MANAGE, tooltip="SPEC_RV_US_TT")


def _shored_badge():
    """A small shield after their name while they are shored up against us."""
    return f"""icon = {{
	visible = "[{shown('rv_is_shielded')}]"
	position = {{ {(C_NAME[1] + 34) // 2 - 10} 0 }}  # over the centred flag's top right corner
	size = {{ 20 20 }}
	parentanchor = vcenter
	texture = "{icons.path('rival_shore')}"
	tooltip = "SPEC_RV_SHIELDED_TT"
}}
"""


def _slots():
    """Top of the Competition section: our contest slots as cards (a flag and the years left; a + while free; a lock
    past what our Standing allows), then the flags of every Exchange contesting us. The player sees at once how many
    contests they may run and why the compete buttons are greyed when the slots are full (2026-11-16)."""
    outs, ins = OUTGOING, INCOMING
    n = f"GetDataModelSize({outs})"
    sv = f"{US}.ScriptValue('spec_rv_slots')"
    bg = "\ticon = {\n\t\tsize = { 100% 100% }\n\t\tusing = entry_bg_simple\n\t\talwaystransparent = yes\n\t}\n"
    # click: a free card is a vanilla button that opens the picker (_picker); the others are plain cards
    card = lambda body, tt, vis=None, click=(): (("button = {\n\tusing = default_button\n"
                                                   + "".join(f'\tonclick = "[{c}]"\n' for c in click) if click else "widget = {\n")
                                                  + (f'\tvisible = "[{vis}]"\n' if vis else "")
                                                  + f"\tsize = {{ 58 52 }}\n\ttooltip = \"{tt}\"\n{'' if click else bg}{body}}}\n")
    big_icon = lambda tex, alpha: (f"\ticon = {{\n\t\tsize = {{ 24 24 }}\n\t\tparentanchor = center\n\t\talpha = {alpha}\n"
                                   f"\t\talwaystransparent = yes\n\t\ttexture = \"{tex}\"\n\t}}\n")
    used = card(f"""	button = {{
		position = {{ 0 6 }}
		size = {{ 34 24 }}
		parentanchor = hcenter
		onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
		tiny_flag = {{
			parentanchor = center
			alwaystransparent = yes
		}}
	}}
	icon = {{
		visible = "[{shown('rv_is_locked')}]"
		position = {{ -2 2 }}
		size = {{ 14 14 }}
		parentanchor = right
		tooltip = "SPEC_RV_SLOT_CANCEL_TT"
		texture = "gfx/interface/buttons/button_icons/lock.dds"
	}}
	close_button = {{
		visible = "[And({CAN_MANAGE}, Not({shown('rv_is_locked')}))]"
		position = {{ 0 0 }}
		size = {{ 18 18 }}
		parentanchor = right
		enabled = "[{CALL.format('rv_end', 'IsValid')}]"
		onclick = "[{CALL.format('rv_end', 'Execute')}]"
		tooltip = "SPEC_RV_SLOT_CANCEL_TT"
	}}
	textbox = {{
		position = {{ 0 -3 }}
		size = {{ 58 18 }}
		parentanchor = bottom|hcenter
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_RV_LEFT_SHORT"
	}}
""", "SPEC_RV_SLOT_USED_TT")
    free = "".join(card(big_icon("gfx/interface/buttons/button_icons/plus.dds", 0.8), "SPEC_RV_SLOT_FREE_TT",
                        f"And({CAN_MANAGE}, And(Not(GreaterThan_int32({n}, '(int32){k - 1}')), GreaterThan_CFixedPoint({sv}, {fx(k - 0.5)})))",
                        (f"GetScriptedGui('spec_sgui_rv_pick').Execute(GuiScope.SetRoot({US}).End)", f"GetVariableSystem.Toggle('{PICK}')"))
                   for k in range(1, NAMED_HIGH + 1))
    shut = "".join(card(big_icon("gfx/interface/buttons/button_icons/lock.dds", 0.5), "SPEC_RV_SLOT_SHUT_TT",
                        f"And(Not(GreaterThan_int32({n}, '(int32){k - 1}')), Not(GreaterThan_CFixedPoint({sv}, {fx(k - 0.5)})))")
                   for k in range(1, NAMED_HIGH + 1))
    some_in = f"GreaterThan_int32(GetDataModelSize({ins}), '(int32)0')"
    return f"""widget = {{
	size = {{ {W} 150 }}  # our contests, then those contesting us on their own row (2026-11-19: six cards crowded the flags)
	parentanchor = hcenter
	textbox = {{
		position = {{ 12 10 }}
		size = {{ 300 20 }}
		align = left|nobaseline
		text = "SPEC_RV_SLOTS"
		tooltip = "SPEC_RV_SLOTS_TT"
	}}
	flowcontainer = {{
		position = {{ 12 36 }}
		spacing = 6
		ignoreinvisible = yes
		flowcontainer = {{
			spacing = 6
			datamodel = "[{outs}]"
			item = {{
				widget = {{
					size = {{ 58 52 }}
					datacontext = "[Scope.GetCountry]"
{ind(used, 5)}				}}
			}}
		}}
{ind(free + shut, 2)}	}}
	textbox = {{
		position = {{ 12 94 }}
		size = {{ 300 20 }}
		align = left|nobaseline
		text = "SPEC_RV_AGAINST"
		tooltip = "SPEC_RV_AGAINST_TT"
	}}
	flowcontainer = {{
		visible = "[{some_in}]"
		position = {{ 12 120 }}
		spacing = 4
		datamodel = "[{ins}]"
		item = {{
			widget = {{
				size = {{ 34 24 }}
				datacontext = "[Scope.GetCountry]"
				button = {{
					size = {{ 100% 100% }}
					onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
					tooltipwidget = {{
						FancyTooltip_Country = {{}}
					}}
					tiny_flag = {{
						parentanchor = center
						alwaystransparent = yes
					}}
				}}
			}}
		}}
	}}
	textbox = {{
		visible = "[Not({some_in})]"
		position = {{ 12 122 }}
		size = {{ 300 20 }}
		align = left|nobaseline
		text = "SPEC_RV_AGAINST_NONE"
	}}
	divider_clean = {{
		parentanchor = bottom
		position = {{ 0 2 }}
	}}
}}
"""


def _picker():
    """Opened by a free slot card: every other Exchange, the ones we may contest first, each part by score (the
    spec_sgui_rv_pick effect fills spec_rv_cands on the click). A row starts the contest through the Exchanges list's
    toggle (spec_sgui_rv_toggle), so the rules and the greyed rows' reasons are that toggle's own. Drawn as vanilla's
    dropdown list (map_list_panel): default_background, default_button rows, vertical_scrollbar. Inline under the slots,
    not floating, so nothing after it draws over it.
    ponytail: no name search; vanilla's search bars are engine objects bound to their own panels, and the data system
    has no substring test. The contestable rows come first instead."""
    rows, call = f"{US}.GetList('spec_rv_cands')", lambda what: CALL.format("rv_toggle", what)
    room = (f"GreaterThan_CFixedPoint({US}.ScriptValue('spec_rv_slots'), "
            f"Add_CFixedPoint({US}.Var('spec_rv_n_out').GetValueWithDefault({fx(0)}), {fx(0.5)}))")
    w, row_w, list_h = W - 24, W - 48, 32 * 8  # eight rows show; the scrollbar sits in the 12px right of the rows
    col = lambda x, wd, key: (f"textbox = {{\n\tposition = {{ {x} 0 }}\n\tsize = {{ {wd} 32 }}\n\tparentanchor = right|vcenter\n"
                              f"\talign = right|nobaseline\n\talwaystransparent = yes\n\ttext = \"{key}\"\n}}\n")
    head = lambda x, wd, key: (f"textbox = {{\n\tposition = {{ {x} 32 }}\n\tsize = {{ {wd} 20 }}\n\tparentanchor = right\n"
                               f"\talign = right|nobaseline\n\tusing = fontsize_small\n\ttext = \"{key}\"\n}}\n")
    # each row washed in its Standing's colour, as the Exchange ranks are (centres.tint)
    stand = f"{THEM}.Var('spec_exch_stand').GetValueWithDefault({fx(0)})"
    # a child widget per Standing: a background's own visible is not read (2026-11-19, every row stayed plain)
    tints = ind("".join(f"widget = {{\n\tvisible = \"[EqualTo_CFixedPoint({stand}, {fx(t)})]\"\n\tsize = {{ 100% 100% }}\n"
                        f"\talwaystransparent = yes\n\tbackground = {{\n\t\tusing = fade_right_colored\n\t\tcolor = {{ {c} 1 }}\n"
                        f"\t\talpha = {__import__('centres').ROW_TINT}\n\t}}\n}}\n" for t, c in __import__("centres").TIER_COL.items()), 7)
    return f"""flowcontainer = {{
	visible = "[And({CAN_MANAGE}, And(GetVariableSystem.Exists('{PICK}'), {room}))]"
	direction = vertical
	parentanchor = hcenter
	margin_bottom = 8
	widget = {{
		size = {{ {w} {54 + list_h + 8} }}
		background = {{
			using = default_background
		}}
		textbox = {{
			position = {{ 12 4 }}
			size = {{ 300 28 }}
			align = left|nobaseline
			text = "SPEC_RV_PICK"
		}}
		close_button = {{
			position = {{ -6 6 }}
			size = {{ 24 24 }}
			parentanchor = right
			onclick = "[GetVariableSystem.Clear('{PICK}')]"
		}}
{ind(head(-(76 + 18), 120, "SPEC_RV_PICK_COL_STAND") + head(-(10 + 18), 60, "SPEC_RV_PICK_COL_SCORE"), 2)}		scrollarea = {{
			position = {{ 6 54 }}
			size = {{ {w - 12} {list_h} }}
			scrollbarpolicy_horizontal = always_off
			scrollbar_vertical = {{
				using = vertical_scrollbar
			}}
			scrollwidget = {{
				flowcontainer = {{
					direction = vertical
					datamodel = "[{rows}]"
					item = {{
						button = {{
							size = {{ {row_w} 32 }}
							using = default_button
							datacontext = "[Scope.GetCountry]"
							alpha = "[TransparentIfFalse({call('IsValid')})]"
							enabled = "[{call('IsValid')}]"
							onclick = "[{call('Execute')}]"
							onclick = "[GetVariableSystem.Clear('{PICK}')]"
							tooltip = "SPEC_RV_PICK_ROW_TT"
{tints}							textbox = {{
								position = {{ 8 0 }}
								size = {{ 272 32 }}
								parentanchor = vcenter
								align = left|nobaseline
								elide = right
								alwaystransparent = yes
								text = "[Country.GetName]"
							}}
{ind(col(-76, 120, "SPEC_RV_PICK_STAND") + col(-10, 60, "SPEC_RV_PICK_SCORE"), 7)}						}}
					}}
				}}
			}}
		}}
		textbox = {{
			visible = "[IsDataModelEmpty({rows})]"
			position = {{ 12 54 }}
			size = {{ {w - 24} 32 }}
			align = left|nobaseline
			text = "SPEC_RV_PICK_EMPTY"
		}}
	}}
}}
"""


def block():
    """The Rivalries section:our market (the rival actions running on us, when contests settle), then two
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
    left = f"""textbox = {{
	visible = "[{PAIR}]"
	position = {{ {C_LEFT[0]} 0 }}
	size = {{ {C_LEFT[1]} {ROW_H} }}
	parentanchor = vcenter
	align = center|nobaseline
	text = "SPEC_RV_LEFT_SHORT"
	tooltip = "SPEC_RV_LEFT_TT"
}}
"""
    row = _flag((C_NAME[1] - 34) // 2) + _shored_badge() + _score() + left + _strip(acts, C_ACT[0], CAN_MANAGE)
    columns = [(C_NAME, "SPEC_RV_COL_EXCH"), (C_SCORE, "SPEC_RV_COL_SCORE"),
               (C_LEFT, "SPEC_RV_COL_LEFT"), (C_ACT, "SPEC_RV_COL_ACT")]
    header = heads([(x, w, key, "center", bool(i)) for i, ((x, w), key) in enumerate(columns)],
                   visibility={"SPEC_RV_COL_ACT": CAN_MANAGE})
    return (_slots() + _picker() + _ours()
            + section("SPEC_RV_SUB_OUT", "spec_hide_rv_out", _did_row() + header + _list(OUTGOING, row, "SPEC_RV_EMPTY_OUT"),
                      right="SPEC_RV_SUB_OUT_RIGHT")
            + section("SPEC_RV_SUB_IN", "spec_hide_rv_in", header + _list(INCOMING, row, "SPEC_RV_EMPTY_IN"),
                      right="SPEC_RV_SUB_IN_RIGHT"))


def marker():
    """Leading Exchanges row, Rival column (the row's Country is the listed one): the rivalry icon button, framed
    while we rival them, and a small shield when they rival us."""
    return ind(_toggle(314) + _lock(314) + f"""icon = {{
    visible = "[And(GetMetaPlayer.IsObserver, {shown('rv_is_out')})]"
    position = {{ 314 0 }}
    size = {{ 32 32 }}
    parentanchor = vcenter
    texture = "{icons.RIVALRY}"
    tooltip = "SPEC_RV_ROW_TT"
}}
icon = {{
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
    did_ok = lambda n: f"EqualTo_CFixedPoint({US}.Var('spec_rv_did_ok').GetValueWithDefault({fx(0)}), {fx(n)})"
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
    bcs = "[Concept('concept_spec_blue_chip','$concept_spec_blue_chips$')]"
    thin = lambda n: f"#N {pc(1 / (1 + (n - 1) * THIN))}#! in #v {n}#!"
    every = lambda n: "once a year" if n == 1 else f"once every #v {n}#! years"
    # the Standing each slot past the first opens at (spec_rv_slots): "a 2nd contest slot at National, a 3rd at ..."
    stand_w = ("Provincial", "National", "International", "World Centre")
    opens = [f"#v {CONTESTS[t]}#! at {stand_w[t]}" for t in range(1, 4)]  # "2 at National, 4 at International and 6 at World Centre"
    opens = ", ".join(opens[:-1]) + " and " + opens[-1]
    rule = ("Our [concept_spec_exchange] can compete with other Exchanges for trust. This is separate from diplomatic rivalries.\\n"
            f"Each competitor costs #N {UPKEEP[0]}#! to #N {UPKEEP[-1]}#! influence in upkeep, more for a higher Standing, "
            "and cannot be dropped in its first year.\\n$TOOLTIP_DELIMITER$\\n"
            f"Each contest settles #v {ROUND}#! years after it starts and frees its slot for a new competitor. The bar starts from the two Exchanges' scores. "
            f"Each of a side's {bcs}, up to #v {BC.CAP}#!, pulls it #v {pc(BC.PULL)}#! that way. "
            f"Each action that works pushes it #v {pc(PUSH)}#!, up to #v {PUSHES}#! pushes a side. Near the middle it is a draw.\\n"
            f"Every contest past the first spreads us thin, so our score counts {thin(NAMED + 1)} contests and {thin(NAMED_HIGH)}.\\n$TOOLTIP_DELIMITER$\\n"
            f"A #P win#! takes #P {pc(WIN_X * STAKE / CALM)}#! trust from the loser, and a #P decisive win#!, at least #v {pc(DECISIVE)}#! to one side, "
            f"takes #P {pc(BIG_X * STAKE / CALM)}#! and lures #P {pc(LURE_SHARE)}#! of the loser's [concept_investment_pool] income for "
            f"#v {LURE_MONTHS}#! months, unless it is lured already. Beating a higher Standing pays more, and a lower one less. "
            f"With [concept_relations] Poor or worse, the loser loses #N x{BITTER:g}#! as much.\\n$TOOLTIP_DELIMITER$\\n"
            "Actions work on the Exchanges we compete with and on those competing with us. "
            f"Against a bigger Exchange they cost more and do less, from #v x{VS_LO:g}#! to #v x{VS_HI:g}#!. "
            "In a [concept_spec_financial_panic], fleeing money goes to a competitor first.")
    why = lambda sg: f"[AddLocalizationIf(Not({CALL.format(sg, 'IsValid')}), '{'SPEC_RV_WHY_' + sg.upper()}')]"
    head = lambda title: f"#header {title}#!\\n$TOOLTIP_DELIMITER$\\n"
    vs = lambda them: (f"Min_CFixedPoint({fx(VS_HI)}, Max_CFixedPoint({fx(VS_LO)}, Divide_CFixedPoint({num(them, 'spec_centre_score')}, "
                       f"Max_CFixedPoint({num(US, 'spec_centre_score')}, {fx(1)}))))")
    heft = lambda them: f"Divide_CFixedPoint({fx(1)}, {vs(them)})"
    EV = "SCOPE.sCountry('target').MakeScope"
    cost_of = lambda them: f"@money![Multiply_CFixedPoint({US}.ScriptValue('spec_rv_cost_base'), {vs(them)})|D]"
    debt_of = lambda them: f"#N @money![Multiply_CFixedPoint({US}.ScriptValue('spec_rv_lure_debt_base'), {vs(them)})|D]#!"
    cost, debt, cost_ev, debt_ev = cost_of(THEM), debt_of(THEM), cost_of(EV), debt_of(EV)
    def product(*factors):
        result = factors[0]
        for factor in factors[1:]:
            result = f"Multiply_CFixedPoint({result}, {factor})"
        return result

    def shield(them, backfire=False):
        key = 'shield' if backfire else 'shielded'
        active = f"GetScriptedGui('spec_sgui_rv_is_{key}').IsShown(GuiScope.SetRoot({US}).AddScope('target', {them}).End)"
        return f"Select_CFixedPoint({active}, {fx(0.5)}, {fx(1)})"

    def hit(them, backfire=False):
        victim = US if backfire else them
        mania = f"GreaterThanOrEqualTo_CFixedPoint({var(victim, 'spec_conf')}.GetValueWithDefault({fx(0)}), {fx(MANIA)})"
        amp = fx(1) if backfire else product(f"{US}.ScriptValue('spec_nx_raid')", heft(them))
        rate = product(fx(round(RAID_HIT / RAID_MONTHS, 3)), amp, f"Select_CFixedPoint({mania}, {fx(2)}, {fx(1)})", shield(them, backfire))
        return f"[{product(rate, fx(RAID_MONTHS))}|2]"

    def share(them):
        amount = product(fx(LURE_SHARE), product(f"{US}.ScriptValue('spec_nx_lure')", heft(them)), shield(them))
        return f"[{amount}|%2]"

    def trust_hit(victim, base):
        paid = product(base, f"{victim}.ScriptValue('spec_exch_loss')")
        return f"[Divide_CFixedPoint(Min_CFixedPoint({num(victim, 'spec_centre_trust')}, {paid}), {fx(CALM)})|%2]"

    def dent(them):
        return trust_hit(them, product(fx(PRESS_TRUST), product(f"{US}.ScriptValue('spec_nx_press')", heft(them)), shield(them)))
    upk = f"{US}.ScriptValue('spec_rv_upkeep_total')"
    stand_is = lambda t: f"EqualTo_CFixedPoint({num(THEM, 'spec_exch_stand')}, {fx(t)})"
    tier_cost = (f"[SelectLocalization({stand_is(3)}, 'SPEC_RV_COST_3', SelectLocalization({stand_is(2)}, 'SPEC_RV_COST_2', "
                 f"SelectLocalization({stand_is(1)}, 'SPEC_RV_COST_1', 'SPEC_RV_COST_0')))]")
    world_free = f"[AddLocalizationIf(EqualTo_CFixedPoint({num(US, 'spec_exch_stand')}, {fx(3)}), 'SPEC_RV_COST_WORLD')]"  # centres.WORLD_FX: the dearest is free
    r = rope()
    past = lambda f: f"GreaterThanOrEqualTo_CFixedPoint({r}, {fx(f)})"
    bands = (f"SelectLocalization({past(DECISIVE)}, 'SPEC_RV_BAND_BIGWIN', SelectLocalization({past(DRAW)}, 'SPEC_RV_BAND_WIN', "
             f"SelectLocalization(GreaterThan_CFixedPoint({r}, {fx(-DRAW)}), 'SPEC_RV_BAND_DRAW', "
             f"SelectLocalization(GreaterThan_CFixedPoint({r}, {fx(-DECISIVE)}), 'SPEC_RV_BAND_LOSS', 'SPEC_RV_BAND_BIGLOSS'))))")
    pair_scope = f"GuiScope.SetRoot({US}).AddScope('target', {THEM})"
    left = f"Subtract_CFixedPoint({fx(ROUND)}, {pair_scope}.ScriptValue('spec_rv_age_t'))"
    epoch = "GetGlobalVariable('spec_rv_epoch_year')"
    def date_at(day):  # dates as vanilla's truces show them: #v
        return f"#v {long_date(day)}#!"

    def settlement_date(term):
        return date_at(f"Add_CFixedPoint(GetGlobalVariable('spec_rv_epoch_day').GetValue, {product(term, fx(365))})")

    def time_left(term, fmt):  # vanilla's remaining time: '_SHORT' as the outliner's treaty timers, '' as journal timeouts
        days = (f"FixedPointToInt(Subtract_CFixedPoint(Add_CFixedPoint(GetGlobalVariable('spec_rv_epoch_day').GetValue, "
                f"{product(term, fx(365))}), {US}.ScriptValue('spec_rv_today')))")
        return f"[LabelingHelper.GetMultiTypeGameTimeDifferenceFromDays({days}, '(int32)2', '{fmt}')]"

    def short_left(key, term):  # the Competition countdown: 4.5 y down to a year, then 11 m, then days (user, 2026-11-19)
        days = (f"Subtract_CFixedPoint(Add_CFixedPoint(GetGlobalVariable('spec_rv_epoch_day').GetValue, "
                f"{product(term, fx(365))}), {US}.ScriptValue('spec_rv_today'))")
        at_least = lambda n: f"GreaterThanOrEqualTo_CFixedPoint({days}, {fx(n)})"
        month = round(365 / 12, 2)
        return [(key, f"[SelectLocalization({at_least(round(11.5 * month))}, '{key}_Y', SelectLocalization({at_least(month)}, '{key}_M', '{key}_D'))]"),
                (f"{key}_Y", f"[Max_CFixedPoint(Divide_CFixedPoint({days}, {fx(365)}), {fx(1)})|1] y"),
                (f"{key}_M", f"[{rounded(f'Divide_CFixedPoint({days}, {fx(month)})', 0)}|0] m"),
                (f"{key}_D", f"[Max_CFixedPoint({days}, {fx(0)})|0] d")]

    shore_protection = "$SPEC_DATE_SHORE_END$"  # dates as their own keys: each is a long calculation (long_date)
    shore_renewal = "$SPEC_DATE_SHORE_AGAIN$"
    shore_until = f"{pair_scope}.ScriptValue('spec_rv_shore_until_date')"
    protected_until = f"{pair_scope}.ScriptValue('spec_rv_protected_until_date')"
    st = lambda who: num(who, 'spec_exch_stand')
    stake = lambda w, l: (f"Select_CFixedPoint(GreaterThan_CFixedPoint({st(w)}, {st(l)}), "
                          f"Divide_CFixedPoint({fx(STAKE)}, Add_CFixedPoint(Subtract_CFixedPoint({st(w)}, {st(l)}), {fx(1)})), "
                          f"Multiply_CFixedPoint({fx(STAKE)}, Add_CFixedPoint(Max_CFixedPoint(Subtract_CFixedPoint({st(l)}, {st(w)}), {fx(0)}), {fx(1)})))")
    # trust as a share of CALM, as the Leading Exchanges show it
    gain = lambda w, l, k: f"Divide_CFixedPoint(Multiply_CFixedPoint({stake(w, l)}, {fx(k)}), {fx(CALM)})"
    loss = lambda w, l, k: (f"Multiply_CFixedPoint(Multiply_CFixedPoint({gain(w, l, k)}, {l}.ScriptValue('spec_exch_loss')), "
                            f"Select_CFixedPoint({shown('rv_is_bitter')}, {fx(BITTER)}, {fx(1)}))")
    swing = lambda k, we_win: (f"Our [concept_spec_exchange] gains #P [{gain(US, THEM, k)}|%0]#! trust, and [Country.GetNameNoFormatting]'s loses #N [{loss(US, THEM, k)}|%0]#!." if we_win else
                               f"Our [concept_spec_exchange] loses #N [{loss(THEM, US, k)}|%0]#! trust, and [Country.GetNameNoFormatting]'s gains #P [{gain(THEM, US, k)}|%0]#!.")
    def lure_outcome(loser, free, held):
        active = f"GetScriptedGui('spec_sgui_rv_is_active_lure').IsShown(GuiScope.SetRoot({loser}).End)"
        return f"[SelectLocalization({active}, '{held}', '{free}')]"

    win_income = lure_outcome(THEM, "SPEC_RV_LURE_WIN", "SPEC_RV_LURE_THEIRS_HELD")
    loss_income = lure_outcome(US, "SPEC_RV_LURE_LOSS", "SPEC_RV_LURE_OURS_HELD")
    effect = {"BIGWIN": swing(BIG_X, True) + "\\n" + win_income,
              "WIN": swing(WIN_X, True), "DRAW": "Neither side gains or loses trust.",
              "LOSS": swing(WIN_X, False), "BIGLOSS": swing(BIG_X, False) + "\\n" + loss_income}
    where = {"BIGWIN": f"The bar ends at least #v {pc(DECISIVE)}#! our way", "WIN": f"The bar ends #v {pc(DRAW)}#! to under #v {pc(DECISIVE)}#! our way",
             "DRAW": f"The bar ends less than #v {pc(DRAW)}#! from the middle", "LOSS": f"The bar ends #v {pc(DRAW)}#! to under #v {pc(DECISIVE)}#! their way",
             "BIGLOSS": f"The bar ends at least #v {pc(DECISIVE)}#! their way"}
    tiers = [(f"SPEC_RV_TIER_{k}_TT", f"#header $SPEC_RV_BAND_{k}$#!\\n{where[k]} when the contest settles.\\n$TOOLTIP_DELIMITER$\\n"
              f"{effect[k]}\\n$TOOLTIP_DELIMITER$\\nThe bar stands $SPEC_RV_BAR_AT$. $SPEC_RV_NOW_LINE$") for k in BANDS]
    # spec_rival.1's scene: the attacker and us, by name, city and Standing
    T, R = "SCOPE.sCountry('target')", "ROOT.GetCountry"
    them, them_city, us_city = f"#v [{T}.GetName]#!", f"#v [{T}.GetCapital.GetCityHubName]#!", f"#v [{R}.GetCapital.GetCityHubName]#!"
    them_stand = f"{T}.MakeScope.Var('spec_exch_stand').GetValueWithDefault({fx(0)})"
    us_stand = f"{R}.MakeScope.Var('spec_exch_stand').GetValueWithDefault({fx(0)})"
    lines = [
        ("SPEC_RV_LURE_WIN", f"#P {pc(LURE_SHARE)}#! of their [concept_investment_pool] income goes to us for {LURE_MONTHS} months"),
        ("SPEC_RV_LURE_LOSS", f"#N {pc(LURE_SHARE)}#! of our [concept_investment_pool] income goes to them for {LURE_MONTHS} months"),
        *((key, f"Existing capital lure continues to [{var(who, 'spec_rv_lurer')}.GetCountry.GetNameNoFormatting] for [{num(who, 'spec_rv_lure')}|0] more months")
          for key, who in (("SPEC_RV_LURE_THEIRS_HELD", THEM), ("SPEC_RV_LURE_OURS_HELD", US))),
        (f"SPEC_H_RIVAL", "Competition"),
        ("SPEC_H_RIVAL_TT", "#header Competition#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RIVAL_RULE$"),
        ("SPEC_H_RIVAL_RIGHT", f"#N -[{upk}|0]#! @inf!"),
        ("SPEC_RIVAL_RULE", rule),
        ("SPEC_RV_SUB_OUT", "Our Competitors"), ("SPEC_RV_SUB_OUT_RIGHT", f"#v [GetDataModelSize({OUTGOING})]#!"),
        ("SPEC_RV_SUB_IN", "Competing With Us"), ("SPEC_RV_SUB_IN_RIGHT", f"#v [GetDataModelSize({INCOMING})]#!"),
        ("SPEC_RV_COL_EXCH", "$concept_country$"),
        ("SPEC_RV_COL_SCORE", "Contest"), ("SPEC_RV_COL_SCORE_TT", f"Who is ahead, with our score next to theirs and how many times each side has pushed. Each contest settles #v {ROUND}#! years after it starts, and the side the bar ends on takes trust from the other."),
        ("SPEC_RV_COL_LEFT", "Ends"), ("SPEC_RV_COL_LEFT_TT", f"When this contest settles. Each one runs #v {ROUND}#! years, then it ends and frees its slot."),
        ("SPEC_RV_LEFT", f"[SelectLocalization({epoch}.IsSet, 'SPEC_RV_TERM_DATE', 'SPEC_RV_TERM_ROUNDS')]"),
        ("SPEC_RV_LEFT_SHORT", f"[SelectLocalization({epoch}.IsSet, 'SPEC_RV_TERM_SHORT', 'SPEC_RV_TERM_ROUNDS')]"),
        ("SPEC_RV_TERM_DATE", f"{time_left(left, '')} ($SPEC_DATE_TERM$)"), ("SPEC_DATE_TERM", settlement_date(left)),  # vanilla's "in 12 days (date)"
        *short_left("SPEC_RV_TERM_SHORT", left),
        ("SPEC_RV_TERM_ROUNDS", f"[{left}|0] yr"),
        ("SPEC_RV_LEFT_TT", f"#header Contest With [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n"
                            f"The bar stands $SPEC_RV_BAR_AT$. $SPEC_RV_NOW_LINE$\\n[{bands.replace('SPEC_RV_BAND_', 'SPEC_RV_SWING_')}]\\n"
                            f"$TOOLTIP_DELIMITER$\\nEach contest runs #v {ROUND}#! years, then it ends and frees its slot."),
        *((f"SPEC_RV_SWING_{k}", swing(BIG_X if k.startswith("BIG") else WIN_X, "WIN" in k) if k != "DRAW" else effect["DRAW"])
          for k in BANDS),
        ("SPEC_RV_COL_ACT", "Actions"), ("SPEC_RV_COL_ACT_TT", f"Our actions against them. A Bear Raid, Lure Capital or Press Campaign that works pushes the contest "
                                                              f"#P {pc(PUSH)}#! our way, up to #v {PUSHES}#! times. Hold the Line undoes one of their pushes, "
                                                              "and Shore Up halves what their actions do for a time."),
        ("SPEC_RV_COL_LAST", "Their Last Action"), ("SPEC_RV_COL_LAST_TT", "Their last action against us."),
        ("SPEC_RV_SCORE_TT", "#header Contest With [Country.GetNameNoFormatting]: $SPEC_RV_BAR_AT$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_SCORE_BODY$"
                             "\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_NOW_LINE$ Whichever side the bar ends on gains trust from the other."),
        ("SPEC_RV_BAR_AT", f"#v [Select_CFixedPoint(GreaterThanOrEqualTo_CFixedPoint({r}, {fx(0)}), {r}, Multiply_CFixedPoint({r}, {fx(-1)}))|%0]#! "
                           f"[SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({r}, {fx(0)}), 'SPEC_RV_OUR_WAY', 'SPEC_RV_THEIR_WAY')]"),
        ("SPEC_RV_NOW_LINE", f"If it settled now, it would be a [{bands}]. It settles in $SPEC_RV_LEFT$."),
        ("SPEC_RV_OUR_WAY", "our way"), ("SPEC_RV_THEIR_WAY", "their way"),
        ("SPEC_RV_SCORE_BODY", f"[Divide_CFixedPoint(Subtract_CFixedPoint(Multiply_CFixedPoint({num(US, 'spec_centre_score')}, {US}.Var('spec_rv_focus').GetValueWithDefault({fx(1)})), Multiply_CFixedPoint({num(THEM, 'spec_centre_score')}, {THEM}.Var('spec_rv_focus').GetValueWithDefault({fx(1)}))), "
                               f"Max_CFixedPoint(Max_CFixedPoint(Multiply_CFixedPoint({num(US, 'spec_centre_score')}, {US}.Var('spec_rv_focus').GetValueWithDefault({fx(1)})), Multiply_CFixedPoint({num(THEM, 'spec_centre_score')}, {THEM}.Var('spec_rv_focus').GetValueWithDefault({fx(1)}))), {fx(1)}))|+=%0] "
                               f"from [concept_spec_exchange] scores, ours #v {score(US)}#! to their #v {score(THEM)}#!"
                               f"[AddLocalizationIf(LessThan_CFixedPoint({US}.Var('spec_rv_focus').GetValueWithDefault({fx(1)}), {fx(0.99)}), 'SPEC_RV_THIN_US')]"
                               f"[AddLocalizationIf(LessThan_CFixedPoint({THEM}.Var('spec_rv_focus').GetValueWithDefault({fx(1)}), {fx(0.99)}), 'SPEC_RV_THIN_THEM')]\\n"
                               f"[Multiply_CFixedPoint({pushes('push')}, {fx(PUSH)})|+=%0] from our #v [{pushes('push')}|0]#! pushes\\n"
                               f"[Multiply_CFixedPoint({pushes('pushed')}, {fx(-PUSH)})|+=%0] from their #v [{pushes('pushed')}|0]#! pushes\\n"
                               f"[Multiply_CFixedPoint({US}.ScriptValue('spec_bc_counted'), {fx(BC.PULL)})|+=%0] from our "
                               f"#v [{US}.Var('spec_bc_n').GetValueWithDefault({fx(0)})|0]#! {bcs}\\n"
                               f"[Multiply_CFixedPoint({THEM}.ScriptValue('spec_bc_counted'), {fx(-BC.PULL)})|+=%0] from their "
                               f"#v [{THEM}.Var('spec_bc_n').GetValueWithDefault({fx(0)})|0]#! {bcs}\\n\\n"
                               f"Each action that works pushes the bar #v {pc(PUSH)}#!, up to #v {PUSHES}#! times a side."),
        ("SPEC_RV_THIN_US", f"\\n#indent_newline:2 We are #N spread thin#! across #v [{US}.Var('spec_rv_n_all').GetValueWithDefault({fx(0)})|0]#! contests, so our score counts #N [{US}.Var('spec_rv_focus').GetValueWithDefault({fx(1)})|%0]#!#!"),
        ("SPEC_RV_THIN_THEM", f"\\n#indent_newline:2 They are #P spread thin#! across #v [{THEM}.Var('spec_rv_n_all').GetValueWithDefault({fx(0)})|0]#! contests, so their score counts #P [{THEM}.Var('spec_rv_focus').GetValueWithDefault({fx(1)})|%0]#!#!"),
        ("SPEC_RV_ROUND", f"[AddLocalizationIf({var(US, 'spec_rv_next')}.GetCountry.IsValid, 'SPEC_RV_NEXT_SETTLEMENT')]"),
        # 2026-11-22: a sentence in place of "Next: X · 11 m" (the user: against our style)
        ("SPEC_RV_NEXT_SETTLEMENT", f"#v [{var(US, 'spec_rv_next')}.GetCountry.GetNameNoFormatting]#! settles in #v [SelectLocalization({epoch}.IsSet, 'SPEC_RV_NEXT_DATE', 'SPEC_RV_NEXT_ROUNDS')]#!"),
        *[(k, t.replace("] y", "] years").replace("] m", "] months").replace("] d", "] days"))
          for k, t in short_left("SPEC_RV_NEXT_DATE", num(US, 'spec_rv_next_year'))],
        ("SPEC_RV_NEXT_ROUNDS", f"[{num(US, 'spec_rv_next_year')}|0] years"),
        ("SPEC_RV_BAND_BIGWIN", "#P Decisive Win#!"), ("SPEC_RV_BAND_WIN", "#P Win#!"), ("SPEC_RV_BAND_DRAW", "Draw"),
        ("SPEC_RV_BAND_LOSS", "#N Loss#!"), ("SPEC_RV_BAND_BIGLOSS", "#N Decisive Loss#!"),
        ("SPEC_RV_SCORE_OFF", "#weak No Exchange#!"),
        ("SPEC_RV_NOW", f"[{bands}]"),
        *tiers,
        ("SPEC_RV_CARD_TITLE", "Competitor Actions on Us"),
        ("SPEC_RV_US_RAID", "#b Bear Raid#!"),
        ("SPEC_RV_US_RAID_FX", f"[SelectLocalization(GreaterThan_CFixedPoint({US}.ScriptValue('spec_rv_raid_applied'), {fx(0)}), 'SPEC_RV_RAID_RATE', 'SPEC_RV_RAID_CAPPED')]"),
        ("SPEC_RV_RAID_RATE", f"[concept_spec_market_confidence] #N -[{US}.ScriptValue('spec_rv_raid_applied')|2]#! a month"),
        ("SPEC_RV_RAID_CAPPED", "Annual raid limit reached"),
        ("SPEC_RV_US_RAID_TT", f"#header Bear Raid on Us#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_US_RAID_FX$\\nLast active raid ends in #v [{num(US, 'spec_rv_raid')}|0]#! months"),
        ("SPEC_RV_US_LURE", f"#b Capital Lured#! by [{var(US, 'spec_rv_lurer')}.GetCountry.GetNameNoFormatting]"),
        ("SPEC_RV_US_LURE_FX", f"#N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to them"),
        ("SPEC_RV_US_LURE_TT", f"#header Capital Lured from Us#!\\n$TOOLTIP_DELIMITER$\\n"
                               f"#N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to [{var(US, 'spec_rv_lurer')}.GetCountry.GetName]\\n"
                               f"#v [{num(US, 'spec_rv_lure')}|0]#! of #v {LURE_MONTHS}#! months left\\n$TOOLTIP_DELIMITER$\\n"
                               "#instruction Shore Up against them in their row to halve their next moves.#!"),
        ("SPEC_RV_US_LAST", f"#b {act(US)}#! by [{var(US, 'spec_rv_hit_by')}.GetCountry.GetNameNoFormatting]"),
        ("SPEC_RV_US_LAST_FX", f"[SelectLocalization({_hit(1)}, 'SPEC_RV_LAST_FAILED', SelectLocalization({_hit_ok(1)}, 'SPEC_RV_LAST_PRESS', 'SPEC_RV_LAST_EXPOSED'))]"),
        ("SPEC_RV_LAST_FAILED", "#P It failed#! and hurt their own market"),
        ("SPEC_RV_LAST_PRESS", "Our [concept_spec_exchange] lost trust"),
        ("SPEC_RV_LAST_EXPOSED", "#P It was exposed#!, costing them trust and goodwill"),
        ("SPEC_RV_US_LAST_WHEN", "#weak In the last year#!"),
        ("SPEC_RV_DID", "#b Our Last Move:#! $SPEC_RV_DID_WHAT$"),
        ("SPEC_RV_DID_WHAT", f"[SelectLocalization({_did(1)}, 'SPEC_RV_RAID', SelectLocalization({_did(2)}, 'SPEC_RV_LURE', "
                        f"SelectLocalization({_did(3)}, 'SPEC_RV_PRESS', SelectLocalization({_did(5)}, 'SPEC_RV_SHORE', 'SPEC_RV_HOLD'))))] "
                        f"[SelectLocalization({did_ok(1)}, 'SPEC_RV_DID_OK', SelectLocalization({did_ok(0)}, 'SPEC_RV_DID_FAIL', 'SPEC_RV_DID_EXPOSED'))]"),
        ("SPEC_RV_DID_OK", "#P worked#!"), ("SPEC_RV_DID_FAIL", "#N failed#!"), ("SPEC_RV_DID_EXPOSED", "#N was exposed#!"),
        *((key, f"[SelectLocalization({_did(1)}, SelectLocalization({did_ok(1)}, '{pre}11', '{pre}10'), "
                f"SelectLocalization({_did(2)}, '{pre}2', SelectLocalization({_did(3)}, "
                f"SelectLocalization({did_ok(1)}, '{pre}31', '{pre}3N'), SelectLocalization({_did(5)}, 'SPEC_RV_DID_SHORE', 'SPEC_RV_DID_FX4'))))]")
          for key, pre in (("SPEC_RV_DID_FX", "SPEC_RV_DID_FX"), ("SPEC_RV_DID_ROW", "SPEC_RV_DID_S"))),
        ("SPEC_RV_DID_S11", f"Their [concept_spec_market_confidence] up to #P -[{num(US, 'spec_rv_did_amt')}|2]#! over {RAID_MONTHS} months"),
        ("SPEC_RV_DID_FX11", f"$SPEC_RV_DID_S11$, contest #P {pc(PUSH)}#! our way"),
        ("SPEC_RV_DID_S10", f"It turned on us. Our [concept_spec_market_confidence] up to #N -[{num(US, 'spec_rv_did_amt')}|2]#! over {RAID_MONTHS} months"),
        ("SPEC_RV_DID_FX10", f"$SPEC_RV_DID_S10$, contest #N {pc(PUSH)}#! their way"),
        ("SPEC_RV_DID_S2", f"We take #P [{num(US, 'spec_rv_did_amt')}|%0]#! of their [concept_investment_pool] income for {LURE_MONTHS} months"),
        ("SPEC_RV_DID_FX2", f"$SPEC_RV_DID_S2$, contest #P {pc(PUSH)}#! our way"),
        ("SPEC_RV_DID_S31", f"Their trust #P -[Multiply_CFixedPoint({num(US, 'spec_rv_did_amt')}, {fx(round(1 / CALM, 6))})|%0]#!"),
        ("SPEC_RV_DID_FX31", f"$SPEC_RV_DID_S31$, contest #P {pc(PUSH)}#! our way"),
        ("SPEC_RV_DID_S3N", f"Relations #N -{PRESS_REL}#!, our trust #N -[Multiply_CFixedPoint({num(US, 'spec_rv_did_amt')}, {fx(round(1 / CALM, 6))})|%0]#!"),
        ("SPEC_RV_DID_FX3N", f"$SPEC_RV_DID_S3N$, contest #N {pc(PUSH)}#! their way"),
        ("SPEC_RV_DID_FX4", "One of their pushes on the contest undone"),
        ("SPEC_RV_DID_SHORE", f"Protected against [{US}.Var('spec_rv_did_on').GetCountry.GetName] for #v [{num(US, 'spec_rv_did_amt')}|0]#! days"),
        ("SPEC_RV_DID_COST", f"[SelectLocalization({_did(2)}, 'SPEC_RV_DID_COST2', SelectLocalization({_did(3)}, 'SPEC_RV_DID_COST3', 'SPEC_RV_DID_COST1'))]"),
        ("SPEC_RV_DID_COST1", f"Cost #N @money![{num(US, 'spec_rv_did_cost')}|D]#!"),
        ("SPEC_RV_DID_COST2", f"Debt #N +@money![{num(US, 'spec_rv_did_cost')}|D]#!"),
        ("SPEC_RV_DID_COST3", f"#N -{PRESS_INFL}#! @inf! for {PRESS_MONTHS} months"),
        ("SPEC_RV_DID_TT", "#header Our Last Move: $SPEC_RV_DID_WHAT$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_DID_FX$\\n$SPEC_RV_DID_COST$\\n$TOOLTIP_DELIMITER$\\n"
                           "#weak Shown for a year, or until our next move#!"),
        ("SPEC_RV_US_LAST_TT", "#header Last Move Against Us#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_RV_US_LAST$\\n$SPEC_RV_US_LAST_FX$\\n$TOOLTIP_DELIMITER$\\n"
                               "#instruction Shore Up against them in their row to halve their next moves.#!"),
        ("SPEC_RV_US_LEFT_RAID", f"#v [{num(US, 'spec_rv_raid')}|0]#! "
                                  f"[SelectLocalization(EqualTo_CFixedPoint({num(US, 'spec_rv_raid')}, {fx(1)}), 'SPEC_RV_MONTH_LEFT', 'SPEC_RV_MONTHS_LEFT')]"),
        ("SPEC_RV_MONTH_LEFT", "#weak month left#!"), ("SPEC_RV_MONTHS_LEFT", "#weak months left#!"),
        ("SPEC_RV_US_LEFT_LURE", f"#v [{num(US, 'spec_rv_lure')}|0]#! "
                                  f"[SelectLocalization(EqualTo_CFixedPoint({num(US, 'spec_rv_lure')}, {fx(1)}), 'SPEC_RV_MONTH_LEFT', 'SPEC_RV_MONTHS_LEFT')]"),
        ("SPEC_RV_CARD_NONE", "#weak No competitor actions are running on us#!"),
        ("SPEC_RV_YEAR", f"[SelectLocalization({shown('rv_is_won')}, 'SPEC_RV_YEAR_W', {sel(shown('rv_is_lost'), 'SPEC_RV_YEAR_L', 'SPEC_RV_YEAR_REST')})]"),
        ("SPEC_RV_YEAR_W", f"[{sel(shown('rv_is_big'), 'SPEC_RV_BAND_BIGWIN', 'SPEC_RV_BAND_WIN')}]"),
        ("SPEC_RV_YEAR_L", f"[{sel(shown('rv_is_big'), 'SPEC_RV_BAND_BIGLOSS', 'SPEC_RV_BAND_LOSS')}]"),
        ("SPEC_RV_YEAR_REST", f"[{sel(shown('rv_is_tied'), 'SPEC_RV_TIED', 'SPEC_RV_NONE')}]"),
        ("SPEC_RV_TIED", "Draw"), ("SPEC_RV_NONE", "#weak –#!"),
        ("SPEC_RV_THEIR_LAST", f"[SelectLocalization({by(US, 'Country.Self')}, 'SPEC_RV_THEIRS_IS', 'SPEC_RV_NONE')]"),
        ("SPEC_RV_THEIRS_IS", f"#v {act(US)}#!, {res(US)}"),
        ("SPEC_RV_US_TT", "#header Competitor Actions on Us#!\\n$TOOLTIP_DELIMITER$\\n"
                          "Each row is a competitor's move still running on our market, with the months it has left.\\n$TOOLTIP_DELIMITER$\\n"
                          "#instruction To halve a competitor's next moves, Shore Up against them in their row.#!"),
        ("SPEC_RV_SHIELDED_TT", "#header Shored Up Against Us#!\\n$TOOLTIP_DELIMITER$\\n"
                                "For now, our actions against them do #N half#! as much."),
        ("spec_rv_shield_tt", "We are not already shored up against them"),
        ("SPEC_RV_TOGGLE_TT", f"[SelectLocalization({shown('rv_is_out')}, 'SPEC_RV_TOGGLE_TT_ON', 'SPEC_RV_TOGGLE_TT_OFF')]{why('rv_toggle')}"),
        ("SPEC_RV_TOGGLE_TT_OFF", head("Compete With [Country.GetNameNoFormatting]") + "We contest their [concept_spec_exchange] for trust.\\n\\n"
                                  f"Costs {tier_cost} @inf! influence in upkeep.{world_free}\\n"
                                  f"[concept_relations] fall by #N {REL_HIT}#! at once, then by #N {REL_DRIFT}#! a month until they reach Poor.\\n\\n"
                                  "It takes one of our contest slots, and cannot be ended in its first year."),  # KEEP_DAYS
        ("SPEC_RV_TOGGLE_TT_ON", head("Competing With [Country.GetNameNoFormatting]") + "We are contesting their [concept_spec_exchange] for trust.\\n\\n"
                                 f"Costs {tier_cost} @inf! influence in upkeep.{world_free}\\n"
                                 f"[concept_relations] fall by #N {REL_DRIFT}#! a month until they reach Poor.\\n\\n"
                                 "Ending it before it settles counts as losing it, a $SPEC_RV_BAND_BIGLOSS$ if the contest already shows one."),
        ("SPEC_RV_WHY_RV_TOGGLE", f"\\n\\n[{CALL.format('rv_toggle', 'BuildTooltip')}]"),
        *((f"SPEC_RV_COST_{t}", f"#N {c}#!") for t, c in enumerate(UPKEEP)),
        ("SPEC_RV_COST_WORLD", " As a World Centre, we pay nothing for our most expensive competitor."),
        ("spec_rv_their_exch_tt", "They have an [concept_spec_exchange]"),
        ("spec_rv_keep_tt", "The competition is more than a year old"),
        ("spec_rv_mutual_tt", "They are not already contesting us"),
        ("spec_rv_interest_tt", "Our [concept_interest] in their capital's [concept_strategic_region] is at least #v $interest_tier_engaged$#!"),
        ("spec_rv_interest_tier_effect", "@checkmark! Allows contesting the [concept_spec_exchange] of a [concept_country] whose capital is in this "
                                         "[concept_strategic_region]"),
        ("spec_rv_forfeit_tt", "We #N forfeit#! the contest. Ending it before it settles counts as a $SPEC_RV_BAND_LOSS$, or a $SPEC_RV_BAND_BIGLOSS$ "
                               "if the contest already shows one."),
        ("SPEC_RV_EMPTY_OUT", f"[SelectLocalization(GetMetaPlayer.IsObserver, 'SPEC_RV_EMPTY_IN', 'SPEC_RV_EMPTY_OUT_PLAYER')]"),
        ("SPEC_RV_EMPTY_OUT_PLAYER", "#weak None yet. Fill a free contest slot above.#!"),
        # the contest slots strip (_slots) and the map's diplomatic actions (diplo)
        ("SPEC_RV_SLOTS", f"Our Contests #v [GetDataModelSize({OUTGOING})]#! of #v [{US}.ScriptValue('spec_rv_slots')|0]#!"),
        ("SPEC_RV_HOW", "Click a free slot and choose from the list, use the round button beside an Exchange in the Exchanges list, "
                        "or right-click its country on the map and choose #v Compete With Their Exchange#!."),
        ("SPEC_RV_SLOTS_TT", f"#header Contest Slots#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_spec_exchange] can run #v {NAMED}#! contest at Provincial "
                             f"Standing, {opens}.\\n\\n$SPEC_RV_NEED$\\n\\n$SPEC_RV_HOW$"),
        ("SPEC_RV_NEED", "We can only contest an Exchange where our [concept_interest] is at least #v $interest_tier_engaged$#! "
                         "in the [concept_strategic_region] of its capital, and not one already contesting us."),
        ("SPEC_RV_SLOT_USED_TT", "#header Contest With [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n"
                                 f"[SelectLocalization({PAIR}, 'SPEC_RV_ROW_NOW', 'SPEC_RV_SLOT_SETTLES')]"
                                 f"[AddLocalizationIf({CAN_MANAGE}, SelectLocalization({shown('rv_is_locked')}, 'SPEC_RV_SLOT_LOCKED', 'SPEC_RV_SLOT_END'))]"),
        ("SPEC_RV_SLOT_SETTLES", "It settles in $SPEC_RV_LEFT$.\\n\\n"),
        ("SPEC_RV_SLOT_CANCEL_TT", "#header End Contest With [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n"
                                   "It settles in $SPEC_RV_LEFT$. Ending it now counts as losing it, a $SPEC_RV_BAND_BIGLOSS$ "
                                   "if the contest already shows one.\\n\\n"
                                   # trust as a share of CALM, as the result tooltips show it (spec_rv_ui_forfeit is in points)
                                   f"Our [concept_spec_exchange] loses #N [Divide_CFixedPoint(Multiply_CFixedPoint({THEM}.Var('spec_rv_ui_forfeit').GetValueWithDefault({fx(0)}), "
                                   f"Multiply_CFixedPoint({US}.ScriptValue('spec_exch_loss'), Select_CFixedPoint({shown('rv_is_bitter')}, {fx(BITTER)}, {fx(1)}))), {fx(CALM)})|%0]#! trust, "
                                   f"and theirs gains #N [Divide_CFixedPoint({THEM}.Var('spec_rv_ui_forfeit').GetValueWithDefault({fx(0)}), {fx(CALM)})|%0]#!.\\n"
                                   f"[SelectLocalization(LessThan_CFixedPoint({rope()}, {fx(-DECISIVE + 0.0001)}), 'SPEC_RV_SLOT_CANCEL_LURE', 'SPEC_RV_EV_NONE')]"
                                   "The contest slot is freed."
                                   f"[SelectLocalization({shown('rv_is_locked')}, 'SPEC_RV_SLOT_CANCEL_LOCKED', 'SPEC_RV_SLOT_CANCEL_CLICK')]"),
        ("SPEC_RV_SLOT_CANCEL_LURE", loss_income + "\\n"),
        ("SPEC_RV_SLOT_CANCEL_LOCKED", "\\n\\n#N It began less than a year ago, so it can't be ended yet.#!"),
        ("SPEC_RV_SLOT_CANCEL_CLICK", "\\n\\n#instruction Click to end it.#!"),
        ("SPEC_RV_SLOT_LOCKED", "#N It began less than a year ago, so it can't be ended yet.#!"),
        ("SPEC_RV_SLOT_END", "#instruction Use the cross on this card to end it.#! #N Ending it early counts as losing it#!."),
        ("SPEC_RV_SLOT_FREE_TT", "#header Free Contest Slot#!\\n$TOOLTIP_DELIMITER$\\nPick another [concept_spec_exchange] to compete with.\\n\\n$SPEC_RV_NEED$\\n\\n"
                                 "#instruction Click to choose one from a list#!"),
        # the contest picker (_picker)
        ("SPEC_RV_PICK", "Choose an Exchange to Contest"),
        ("SPEC_RV_PICK_COL_STAND", "#weak Standing#!"), ("SPEC_RV_PICK_COL_SCORE", "#weak Score#!"),
        ("SPEC_RV_PICK_STAND", "$SPEC_CENTRE_STAND$"), ("SPEC_RV_PICK_SCORE", "$SPEC_CENTRE_SCORE$"),
        ("SPEC_RV_PICK_EMPTY", "#weak No other Exchanges yet#!"),
        ("SPEC_RV_PICK_ROW_TT", f"$SPEC_RV_TOGGLE_TT$[AddLocalizationIf({CALL.format('rv_toggle', 'IsValid')}, 'SPEC_RV_PICK_CLICK')]"),
        ("SPEC_RV_PICK_CLICK", "\\n\\n#instruction Click to start the contest#!"),
        ("SPEC_RV_SLOT_SHUT_TT", f"#header Locked Contest Slot#!\\n$TOOLTIP_DELIMITER$\\nOur [concept_spec_exchange] can run more contests at a higher Standing: {opens}."),
        ("SPEC_RV_AGAINST", f"Contesting Us #v [GetDataModelSize({INCOMING})]#!"),
        ("SPEC_RV_AGAINST_TT", "#header Contesting Us#!\\n$TOOLTIP_DELIMITER$\\nThe Exchanges that picked ours as a competitor. "
                               "Their contests take none of our slots."),
        ("SPEC_RV_AGAINST_NONE", "#weak No one#!"),
        *((f"spec_rv_compete{s}", "Compete With Their Exchange") for s in ("", "_action_name", "_action_propose_name")),
        ("spec_rv_compete_desc", "Pick their [concept_spec_exchange] as a competitor and fight it for trust. It takes one of our contest slots, "
                                 "and raises our [concept_involvement] in the [concept_strategic_region] of their capital while it runs."),
        ("spec_rv_compete_action_notification_name", "A New Competitor"),
        ("spec_rv_compete_action_notification_desc", "[INITIATOR_COUNTRY.GetName] has picked our [concept_spec_exchange] as a competitor."),
        *((f"spec_rv_stop{s}", "Stop Competing") for s in ("", "_action_name", "_action_propose_name")),
        ("spec_rv_stop_desc", "Drop their [concept_spec_exchange] as a competitor and free the contest slot."),
        ("spec_rv_stop_action_notification_name", "Competition Ended"),
        ("spec_rv_stop_action_notification_desc", "[INITIATOR_COUNTRY.GetName] no longer competes with our [concept_spec_exchange]."),
        ("SPEC_RV_EMPTY_IN", "#weak None#!"),
        ("spec_rv_upkeep", "Competing Exchanges"),
        ("spec_rv_upkeep_desc", "Our [concept_spec_exchange] spends influence keeping up with its competitors."),
        
        ("spec_rv_raid_fx", f"Over #v {RAID_MONTHS}#! months, their [concept_spec_market_confidence] falls by up to #P {hit(EV)}#! if it works, or ours by up to #N {hit(EV, True)}#! if it fails. The yearly raid cap applies. Costs #N {cost_ev}#! from our [concept_treasury]."),
        ("spec_rv_lure_fx", f"For #v {LURE_MONTHS}#! months, #P {share(EV)}#! of their [concept_investment_pool] income comes to ours. Our [concept_spec_outstanding_credit] grows by {debt_ev}."),
        ("spec_rv_press_fx", f"Their [concept_spec_exchange] loses #P {dent(EV)}#! trust. "
                             f"If exposed, relations fall by #N {PRESS_REL}#! and our trust by #N {trust_hit(US, fx(PRESS_TRUST))}#!. Costs #N {PRESS_INFL}#! influence for #v {PRESS_MONTHS}#! months."),
        ("spec_rv_hold_fx", f"One of their pushes in our contest is undone. Costs #N {cost_ev}#! from our [concept_treasury]."),
        ("spec_rv_pushed_tt", "They have pushed our contest their way"),
        ("SPEC_RV_HOLD", "Hold the Line"),
        ("spec_rv_shore_fx", f"Their actions do #P half#! as much until {shore_protection}. It can be used again on {shore_renewal}. Costs #N {cost_ev}#! from our [concept_treasury]."),
        ("SPEC_RV_SHORE_RENEWAL", "\\nIt can be used again on $SPEC_DATE_SHORE_UNTIL$."),
        ("SPEC_RV_SHORE_PROTECTED", "\\nTheir protection ends on $SPEC_DATE_PROTECTED_UNTIL$."),
        ("SPEC_DATE_SHORE_END", date_at(f"{US}.ScriptValue('spec_rv_shore_end_day')")),
        ("SPEC_DATE_SHORE_AGAIN", date_at(f"{US}.ScriptValue('spec_rv_shore_again_day')")),
        ("SPEC_DATE_SHORE_UNTIL", date_at(shore_until)), ("SPEC_DATE_PROTECTED_UNTIL", date_at(protected_until)),
        ("SPEC_RV_SHORE_OFFER", f"If used now, their actions do #P half#! as much until {shore_protection}. It can be used again on {shore_renewal}."),
        ("SPEC_RV_SHORE_WAIT", "Shore Up is on cooldown against this competitor."),
        ("SPEC_RV_LAST", f"[SelectLocalization({by(THEM, 'GetMetaPlayer.GetPlayedOrObservedCountry.Self')}, 'SPEC_RV_LAST_OURS', "
                         f"{sel(by(US, 'Country.Self'), 'SPEC_RV_LAST_THEIRS', 'SPEC_RV_LAST_NONE')})]"),
        ("SPEC_RV_LAST_OURS", f"Our last action was #v {act(THEM)}#!, and {res(THEM)}."),
        ("SPEC_RV_LAST_THEIRS", f"Their last action was #v {act(US)}#!, and {res(US)}."),
        ("SPEC_RV_LAST_NONE", "No actions between us yet"),
        ("SPEC_RV_OK", "#P it worked#!"), ("SPEC_RV_FAILED", "#N it failed#!"), ("SPEC_RV_EXPOSED", "#N it was exposed#!"),
        ("SPEC_RV_RAID", "Bear Raid"), ("SPEC_RV_LURE", "Lure Capital"), ("SPEC_RV_PRESS", "Press Campaign"), ("SPEC_RV_SHORE", "Shore Up"),
        ("SPEC_RV_ROW_TT", f"#header [Country.GetNameNoFormatting]#!\\n$TOOLTIP_DELIMITER$\\n[AddLocalizationIf({PAIR}, 'SPEC_RV_ROW_NOW')]$SPEC_RV_LAST$"),
        ("SPEC_RV_ROW_NOW", "The contest stands $SPEC_RV_BAR_AT$. $SPEC_RV_NOW_LINE$\\n\\n"),  # the row said only the last action
        ("SPEC_RV_MARK_TT", "#header They Compete With Us#!\\n$TOOLTIP_DELIMITER$\\nTheir [concept_spec_exchange] has made ours its competitor."),
        ("spec_rv_pair_tt", "Both countries have an [concept_spec_exchange]"),
        ("spec_rv_exch_tt", "Our country has an [concept_spec_exchange]"),
        ("spec_rv_room_tt", "We have a free contest slot"),
        ("spec_rv_cd_tt", "We have not used this against them in the last year"),
        ("spec_rv_shore_cd_tt", f"We have not shored up against them in the last #v {SHORE_CD}#! years"),
        ("spec_rv_gold_tt", "Our treasury can pay the cost"),
        ("spec_rv_panic_tt", "Our market is not in a [concept_spec_financial_panic]"),
        ("spec_rv_lured_tt", "No one is luring their capital already"),
        ("spec_rv_infl_tt", f"We have #v {PRESS_INFL}#! influence to spare"),
        ("spec_rv_slots_tt", f"We run fewer than #v {SLOTS}#! press campaigns"),
        ("spec_rv_press_1", "Press Campaign"), ("spec_rv_press_2", "Second Press Campaign"), ("spec_rv_press_3", "Third Press Campaign"),
        *((f"spec_rv_press_{n}_desc", "Newspapers abroad are paid to doubt a competing Exchange.") for n in range(1, SLOTS + 1)),
        # the scene: who struck (their Standing against ours), our market's state, the move, then what it costs
        ("SPEC_RV_EV_PANIC", "Our market was already in a panic, and our competitors chose their moment with care.\\n\\n"),
        ("SPEC_RV_EV_MANIA", "Our boom was at its height, and every investor already lay awake fearing the fall.\\n\\n"),
        ("SPEC_RV_EV_NONE", ""),
        ("spec_rival.1.t11", f"Bear Raid on {us_city}!"),
        ("spec_rival.1.d11", f"Before the opening bell, brokers acting for {them} threw great blocks of our railway and bank shares onto the floor at once. "
                             "Prices broke, the tickers fell behind, and by noon our own clerks were selling in a fright.\\n\\n"
                             f"This raid can cost up to #N [SCOPE.GetValue('spec_rv_event_amount')|2]#! [concept_spec_market_confidence] over {RAID_MONTHS} months."),
        ("spec_rival.1.f11", '\\"A run on the market may begin with a single rumor.\\"'),
        ("spec_rival.1.t10", "The Raid That Failed"),
        ("spec_rival.1.d10", f"Brokers acting for {them} dumped our shares onto the floor at once, expecting a rout. Instead our banks bought every lot "
                             "they offered, prices held, and by the closing bell it was the raiders who were nursing their losses.\\n\\n"
                             f"Their own [concept_spec_market_confidence] can fall by up to #P [SCOPE.GetValue('spec_rv_event_amount')|2]#! over {RAID_MONTHS} months."),
        ("spec_rival.1.f10", '\\"The bear who sells what he does not own had better be right.\\"'),
        ("spec_rival.1.t21", "Our Capital Is Being Courted"),
        ("spec_rival.1.d21", f"Agents from {them} have taken rooms at our finest hotels, and our largest investors are dining with them nightly. "
                             "Their offer is simple: a better rate, a safer harbour, and no awkward questions.\\n\\n"
                             f"For {LURE_MONTHS} months, #N [{num(US, 'spec_rv_lure_share')}|%0]#! of our [concept_investment_pool] income goes to them."),
        ("spec_rival.1.f21", '\\"Capital goes where it is well treated, and stays where it is well fed.\\"'),
        ("spec_rival.1.t31", "A Campaign of Whispers"),
        ("spec_rival.1.d31", f"The morning papers of {them} carry long columns on forged balance sheets and tottering banks in {us_city}. "
                             "None are signed and few are true, but they are read in every counting house on the continent.\\n\\n"
                             f"Our [concept_spec_exchange] lost #N [Divide_CFixedPoint(SCOPE.GetValue('spec_rv_event_amount'), {fx(CALM)})|%2]#! trust."),
        ("spec_rival.1.f31", '\\"A lie travels halfway around the world while the truth is still putting on its boots.\\"'),
        ("spec_rival.1.t3n", "A Paid Campaign Exposed"),
        ("spec_rival.1.d3n", f"The papers of {them} have been full of doubts about our [concept_spec_exchange]. But a clerk talked, and now "
                             "everyone knows whose money paid for the ink.\\n\\nWe lose trust, but so do they, and their name suffers abroad."),
        ("spec_rival.1.f3n", '\\"Mud thrown in the dark still leaves the hands dirty.\\"'),
        ("spec_rival.1.t", "A Competitor Moves Against Us"),
        ("spec_rival.1.f", '\\"A run on the market may begin with a single rumor.\\"'),
        ("spec_rival.1.a", "Give them a taste of their own medicine."), ("spec_rival.1.a_tt", "We answer in kind, even if we already moved against them this year."),
        ("spec_rival.1.a_1", "We launch a #v Bear Raid#! of our own."), ("spec_rival.1.a_2", "We #v Lure Their Capital#! in turn."),
        ("spec_rival.1.a_3", "We start a #v Press Campaign#! of our own."),
        ("spec_rival.1.b", "Close ranks against them."), ("spec_rival.1.b_tt", f"We #v Shore Up#! against them. Their actions do #P half#! as much until {shore_protection}, "
                                                                               f"and we can do it again on {shore_renewal}. Costs #N {cost_ev}#! from our [concept_treasury]."),
        ("spec_rival.1.c", "Carry on as if nothing happened."),
        ("spec_rival.1.c_tt", f"Our [concept_spec_exchange] gains #P [Multiply_CFixedPoint({fx(round(CALM_GAIN / CALM, 4))}, "
                              f"Add_CFixedPoint({fx(1)}, Multiply_CFixedPoint({fx(CALM_STAND)}, SCOPE.sCountry('target').MakeScope.Var('spec_exch_stand').GetValueWithDefault({fx(0)}))))|%0]#! "
                              f"trust for keeping its head. The bigger the Exchange we shrug off, the more it counts."),
        ("spec_rival.1.d", "Buy into the panic."),
        ("spec_rival.1.d_tt", f"Our banks buy what the raiders sell. The raid takes #P half#! as much [concept_spec_market_confidence]. "
                              f"Costs #N @money![ROOT.GetCountry.MakeScope.ScriptValue('spec_rv_counter_cost')|D]#! (#v {COUNTER_GDP:.0%}#! of our GDP)."),
        ("spec_rival.1.e", "Match their terms."),
        ("spec_rival.1.e_tt", f"We pay our investors to stay. They take #P half#! as much of our [concept_investment_pool]. "
                              f"Costs #N @money![ROOT.GetCountry.MakeScope.ScriptValue('spec_rv_counter_cost')|D]#! (#v {COUNTER_GDP:.0%}#! of our GDP)."),
        ("spec_rival.1.g", "Answer in our own papers."),
        ("spec_rival.1.g_tt", f"Our papers print the figures. Our [concept_spec_exchange] wins back #P {pc(round(PRESS_TRUST * 0.6, 2) / CALM)}#! trust. "
                              f"Costs #N @money![ROOT.GetCountry.MakeScope.ScriptValue('spec_rv_counter_cost')|D]#! (#v {COUNTER_GDP:.0%}#! of our GDP)."),
    ]
    lines += [
        ("SPEC_DRIVER_RIVAL", "Competitor Actions"),
        ("SPEC_DRIVER_RIVAL_TT", "#header Competitor Actions: [Country.MakeScope.Var('spec_c_rival').GetValueWithDefault('(CFixedPoint)0')|+=2]#!\\n$TOOLTIP_DELIMITER$\\n"
                                 f"A competitor's Bear Raid on our market takes [concept_spec_market_confidence] each month for #v {RAID_MONTHS}#! months. "
                                 f"Raids take at most #N {RAID_CAP:g}#! of it a year, however many come.\\n\\n"
                                 "#instruction Shore Up against a competitor in the Competition section to halve its next moves.#!"),
    ]
    intro = {"big": f"The great Exchange of {them_city} has noticed us at last, and it does not care for what it sees.",
             "even": f"For years the Exchanges of {them_city} and {us_city} have circled one another. It was only a matter of time.",
             "small": f"The upstarts of {them_city} have decided that {us_city} needs taking down a peg."}
    moves = [f"spec_rival.1.d{c}{'n' if o < 0 else o}" for c, o in ((1, 1), (1, 0), (2, 1), (3, 1), (3, -1))]
    lines += [(f"{k}_{w}", f"{s}\\n\\n{v}") for k, v in list(lines) if k in moves for w, s in intro.items()]
    lines.append(("spec_rival.1.desc", "A competitor has moved against our [concept_spec_exchange]."))
    out = "".join(f' {k}: "{t}"\n' for k, t in lines)
    tip = lambda a, title, body: (f' SPEC_RV_{a.upper()}_TT: "{head(title)}{body}{why("rv_" + a)}"\n'
                                  f' SPEC_RV_WHY_RV_{a.upper()}: "\\n\\n[{CALL.format("rv_" + a, "BuildTooltip")}]"\n')
    N = "\\n"
    D = N + "$TOOLTIP_DELIMITER$" + N
    them = "[Country.GetNameNoFormatting]"
    ours_way = f"the contest moves #P {pc(PUSH)}#! our way"
    theirs_way = f"the contest moves #N {pc(PUSH)}#! their way"
    cd = f" It can be used against {them} {every(CD_DAYS // 365)}."
    out += tip("raid", "Bear Raid",
               f"If it works, {them}'s [concept_spec_market_confidence] falls by up to #P {hit(THEM)}#! over #v {RAID_MONTHS}#! months, and {ours_way}.{N}"
               f"There is a #N [{fail}|0]%#! chance it fails. Then our own [concept_spec_market_confidence] falls by up to #N {hit(THEM, True)}#! "
               f"over #v {RAID_MONTHS}#! months, and {theirs_way}.{N}"
               f"Raids take at most #N {RAID_CAP:g}#! confidence a year from any country.{D}Costs #N {cost}#! from our [concept_treasury].{cd}")
    out += tip("lure", "Lure Capital",
               f"#P {share(THEM)}#! of {them}'s [concept_investment_pool] income comes to us for #v {LURE_MONTHS}#! months, and {ours_way}.{D}"
               f"Adds {debt} to our [concept_spec_outstanding_credit].{cd}")
    out += tip("press", "Press Campaign",
               f"If it works, {them}'s [concept_spec_exchange] loses #P {dent(THEM)}#! trust, and {ours_way}.{N}"
               f"There is a #N [{THEM}.ScriptValue('spec_rv_press_expose')|0]%#! chance it is exposed, higher where {them}'s press is free. "
               f"Then they still lose {dent(THEM)} trust, but our [concept_spec_exchange] loses #N {trust_hit(US, fx(PRESS_TRUST))}#!, "
               f"[concept_relations] with {them} fall by #N {PRESS_REL}#!, and {theirs_way}.{D}"
               f"Costs #N {PRESS_INFL}#! @inf! [concept_influence] for #v {PRESS_MONTHS}#! months.{cd}")
    out += tip("hold", "Hold the Line",
               f"Undoes one of {them}'s pushes, moving the contest #P {pc(PUSH)}#! back our way. "
               f"They have pushed it #v [{pushes('pushed')}|0]#! times.{D}"
               f"Costs #N {cost}#! from our [concept_treasury].{cd}")
    out += tip("shore", "Shore Up",
               f"[SelectLocalization({shown('rv_is_cd_shore')}, 'SPEC_RV_SHORE_WAIT', 'SPEC_RV_SHORE_OFFER')]"
               f"[AddLocalizationIf(And({shown('rv_is_shield')}, GreaterThan_CFixedPoint({protected_until}, {fx(0)})), 'SPEC_RV_SHORE_PROTECTED')]{D}"
               f"Costs #N {cost}#! from our [concept_treasury]. It can be used against {them} {every(SHORE_CD)}."
               f"[AddLocalizationIf(And({shown('rv_is_cd_shore')}, GreaterThan_CFixedPoint({shore_until}, {fx(0)})), 'SPEC_RV_SHORE_RENEWAL')]")
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
    assert used - {"SPEC_DATE_ZERO", "SPEC_DATE_MAY"} <= keys, used - keys  # market_tab.long_date's key
    script = triggers() + effects() + events()
    tts = set(re.findall(r"text = (spec_rv_\w+_tt)", script))
    assert tts <= keys, tts - keys
    contest = effects().split("spec_rival_contest = {")[1].split("# end spec_rival_contest")[0]
    # the notification testbed swaps these (not the trust recorder's, BC.record_trust)
    assert len(re.findall(r"is_player = yes(?! has_variable = spec_trust_review)", contest)) == 2 and contest.count("post_notification") == 2
    assert contest.count("spec_rv_rope") == 1 and "spec_rv_push = { BY = scope:target ON = scope:spec_rv_actor }" in effects()
    assert "spec_rv_reach" not in triggers() and "spec_can_rv_end = yes" in triggers()
    assert "multiplier = spec_rv_upkeep_total" in effects() and "spec_rv_upkeep = {" in MODIFIERS
    assert "rv_toggle" in marker() and "set_level_bar_item" in gui and "spec_rv_pairs" not in gui
    assert f"random = {{  # at most one new competitor a look" in effects() and f"chance = {AI_PICK_CHANCE}" in effects()
    assert "\t\tspec_rv_ai_pick = yes\n" in effects() and "spec_rv_ai_pick = yes" not in pass_()  # on each AI's own clock
    assert f"name = spec_rv_age_{MONTHS - 1} target" in effects() and f"spec_rv_age_{MONTHS}" not in effects() + pass_()
    assert effects().count("count = %d is_target" % AI_CAP) == 3 and "count = %d is_target" % (AI_CAP + 1) in effects()
    print("ok")
