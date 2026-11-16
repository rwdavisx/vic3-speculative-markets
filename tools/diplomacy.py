"""Vanilla diplomacy in the confidence model: diplomatic plays, embargoes and capital flight to Great Powers."""
import tuning

PLAY_TURMOIL = 0.5          # confidence lost a month in an active diplomatic play while not at war
WAR_COST = 0.6              # what an average war should cost a month: the target for WAR_ROWS, and War Risk's estimate
WAR_BASE = 0.35             # confidence any war costs a month, however it is going
WAR_ALL_MIN, WAR_ALL_MAX = -4, 0.5  # all of a country's wars together, a month

# A war's monthly change in confidence, row by row, on the country with scope:war set: key -> (name in the calculator,
# reading, script turning the reading into points, the row's worst, the row's best). Each row is capped by itself, so
# the rows always add up to the number shown, and the worst and best of the rows are the bounds of a war.
PCT = "#v [{r}|%0]#!"
WAR_ROWS = {
    # this month's losses, not the running total: the news moves the market, and confidence recovers as it always does
    "casualties": ("[concept_casualties] (" + PCT + " of our forces this month, #v [{t}|%0]#! in all)",
                   "add = spec_war_killed\n\tsubtract = var:spec_war_prev\n\tmin = 0\n\tdivide = spec_war_forces",
                   "multiply = -6", -0.75, 0),
    "blockade": ("[concept_gdp] in [Concept('concept_blockade','$concept_blockaded$')] [Concept('concept_state','$concept_states$')] (" + PCT + ")", 'add = "scope:war.blockaded_gdp_share(root)"', "multiply = -1", -0.35, 0),
    "gdp": ("[concept_gdp] since the war began (" + PCT + ")", 'add = "scope:war.gdp_change_since_war_start(root)"',
            "add = 0.1\n\tmax = 0", -0.35, 0),
    "devastation": ("[concept_devastation] (" + PCT + ")", "add = average_devastation", "multiply = -1", -0.2, 0),
    "battles": ("[Concept('concept_battle','$concept_battles$')] Won against Lost (" + PCT + ")",
                'add = "size_weighted_won_battles_fraction(scope:war)"\n\tsubtract = "size_weighted_lost_battles_fraction(scope:war)"\n\tmultiply = {\n\t\tvalue = "scope:war.num_significant_battles"\n\t\tdivide = define:NWar|WAR_SUPPORT_BATTLES_RAMP_THRESHOLD\n\t\tmax = 1\n\t}',
                "multiply = 0.25", -0.25, 0.25),
    "held": ("Enemy Land Occupied (" + PCT + ")", 'add = "enemy_side_occupation(scope:war)"', "multiply = 0.25", 0, 0.25),
    "pressure": ("[concept_war_pressure] (" + PCT + ")", 'add = "scope:war.enemy_pressure(root)"', "multiply = -0.35", -0.35, 0),
    "land": ("Land Lost to Enforced [Concept('concept_war_goal','$concept_war_goals$')] (" + PCT + ")", 'add = "scope:war.land_lost_since_war_start(root)"', "multiply = -1", -0.1, 0),
    "length": ("A Long War (#v [{r}|0]#! months)", 'add = "scope:war.war_duration_months"', "subtract = 12\n\tmin = 0\n\tmultiply = -0.0083", -0.2, 0),
    "stalemate": ("Stalemate", "if = {\n\t\tlimit = { scope:war = { war_is_in_stalemate = yes } }\n\t\tadd = 1\n\t}", "multiply = -0.1", -0.1, 0),
}
WAR_WORST = round(sum(row[3] for row in WAR_ROWS.values()) - WAR_BASE, 2)
WAR_BEST = round(sum(row[4] for row in WAR_ROWS.values()) - WAR_BASE, 2)
WAR_SLOTS = (1, 2, 3)       # wars named in the tooltip; the rest are summed
WAR_END = {"won": (4, 1), "lost": (-8, -2), "drawn": (-1, -1)}  # at full stakes: with a war goal enforced, without
WAR_END_SCOPES = {"won": "benefitted_from_wargoal", "lost": "victim_of_wargoal"}
WAR_STAKES_MIN = 0.25       # a war end's share of WAR_END when almost nobody died; a quarter of our forces lost is all of it
WAR_ON_ACTIONS = {"won": "on_won_war", "lost": "on_lost_war", "drawn": "on_inconclusive_war"}
SOURCES = 3                 # foreign panics named in the Abroad chip's tooltip in a month
# on a country catching root's panic: note root among the month's sources (spec_fp1 to 3, moved to spec_fs1 to 3
# for the tab once the month counts them)
NOTE_SRC = "".join(f"""		{'if' if n == 1 else 'else_if'} = {{
			limit = {{
"""
                   # Compare the saved reference without entering it. A previous source can disappear
                   # before another panic arrives; optional equality handles that stale link safely.
                   + "".join(f"\t\t\t\tNOT = {{ var:spec_fp{m} ?= root }}\n" for m in range(1, n))
                   + f"""				NOT = {{ has_variable = spec_fp{n} }}
			}}
			set_variable = {{ name = spec_fp{n} value = root }}
		}}
"""
                   for n in range(1, SOURCES + 1))
FLIGHT_GAIN = 2             # confidence a safe Great Power gains when a panic starts, before scaling by the two GDPs
FLIGHT_FROM = 40            # only at Steady or better
# the Exchange (centres.py, which imports market_tab and so cannot be imported here): an International or World
# Centre Exchange receives flight without being a Great Power
SAFE = ("OR = {\n\t\t\t\tcountry_rank = rank_value:great_power\n\t\t\t\tAND = {\n\t\t\t\t\thas_variable = spec_exch_stand\n"
        "\t\t\t\t\tvar:spec_exch_stand >= 2\n\t\t\t\t}\n\t\t\t}" if tuning.get("EXCHANGE_ON", 1) else "country_rank = rank_value:great_power")
WAR_VARS = [f"spec_war{n}{s}" for n in WAR_SLOTS for s in ["", "_c", "_killed", "_total", "_play"] + [f"_{key}{r}" for key in WAR_ROWS for r in ("", "_r")]]
STATE_VARS = (["spec_flight_pending", "spec_war_more", "spec_war_n", "spec_war_cost", "spec_war_sum", "spec_war_end", "spec_war_stakes_now", "spec_c_warend", "spec_c_flight", "spec_war_prev"]
              + WAR_VARS + [f"spec_wp{n}{s}" for n in WAR_SLOTS for s in ("", "_k")] + [f"spec_f{p}{n}" for p in "ps" for n in range(1, SOURCES + 1)])

# on a country iterated from root: true unless either has embargoed the other. Cuts the trade tie in spec_every_tied
# and in spec_find_risk_src.
TRIGGERS = """spec_no_embargo_with_root = {
	NOR = {
		has_diplomatic_pact = { who = root type = embargo }
		root = { has_diplomatic_pact = { who = prev type = embargo } }
	}
}
"""

# a war's end, on the country, spec_war_end set: the jump, held to 0 to 100, shown until the next monthly update
WAR_JUMP = """spec_war_jump = {
	set_variable = { name = spec_war_end value = { value = var:spec_conf add = var:spec_war_end min = 0 max = 100 subtract = var:spec_conf } }
	change_variable = { name = spec_conf add = var:spec_war_end }
	if = {
		limit = { NOT = { has_variable = spec_c_warend } }
		set_variable = { name = spec_c_warend value = 0 }
	}
	change_variable = { name = spec_c_warend add = var:spec_war_end }
	change_variable = { name = spec_c_total add = var:spec_war_end }
	remove_variable = spec_war_end
	spec_pick_driver = yes
	spec_update_band = yes
}
"""

# on a country that has just panicked, after spec_every_tied: money flees to calm Great Powers that are not tied to
# it (a tied one has just caught the panic). Applied on their next monthly update, in the Foreign Panics row.
# rival Exchanges (centres.RIVAL_ON): a rival on either side takes the fleeing money first, and more of it.
# centres imports market_tab, which imports this module, so its switch is read at build time
RIVALS = ("AND = { has_variable = spec_exch_stand root = { has_variable = spec_exch_stand } "
          "OR = { is_target_in_variable_list = { name = spec_rv_chosen target = root } "
          "root = { is_target_in_variable_list = { name = spec_rv_chosen target = prev } } } }")


def effects(rival):
    more = (f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ OR = {{ {RIVALS} }} }}\n"
            f"\t\t\t\t\tmultiply = {tuning.get('EXCH_RIVAL_FLIGHT', 1.5):g}\n\t\t\t\t}}\n") if rival else ""
    return f"""spec_capital_flight = {{
	every_country = {{
		limit = {{
			NOT = {{ this = root }}
			{SAFE if not rival else 'OR = {' + SAFE + ' ' + RIVALS + ' }'}
			has_variable = spec_conf
			var:spec_conf >= {FLIGHT_FROM}
			NOT = {{ has_variable = spec_panic }}
			NOT = {{ has_variable = spec_foreign_pending }}
			is_at_war = no
			gdp > 0
		}}
		# ponytail: a second panic in the same month overwrites the first; rare enough not to keep the larger
		set_variable = {{
			name = spec_flight_pending
			value = {{
				value = root.var:spec_src_gdp
				divide = gdp
				max = 1
				multiply = {FLIGHT_GAIN}
				multiply = spec_flight_mult
{more}			}}
		}}
		set_variable = {{ name = spec_foreign_src value = root }}
{NOTE_SRC}	}}
}}
"""


# in spec_monthly, after spec_c_foreign is set from a pending contagion hit
MONTHLY = """			remove_variable = spec_c_flight
			if = {
				limit = { has_variable = spec_flight_pending }
				change_variable = { name = spec_c_foreign add = var:spec_flight_pending }
				set_variable = { name = spec_c_flight value = var:spec_flight_pending }
				remove_variable = spec_flight_pending
			}
"""


def war_values():
    """The readings (spec_wv_), the points they give (spec_wc_) and their sum, on a country with scope:war set."""
    out = ('spec_war_killed = {\n\tvalue = 0\n\tadd = "scope:war.num_country_casualties(root)"\n}\n'
           # in men, as vanilla's war_support_from_casualties: battalions are a thousand each
           "spec_war_forces = {\n\tvalue = 1000\n\tif = {\n\t\tlimit = { military_size > 0 }\n\t\tmultiply = military_size\n\t}\n}\n"
           "spec_war_total = {\n\tvalue = spec_war_killed\n\tdivide = spec_war_forces\n}\n")
    for key, (_, read, score, lo, hi) in WAR_ROWS.items():
        out += f"spec_wv_{key} = {{\n\tvalue = 0\n\t{read}\n}}\nspec_wc_{key} = {{\n\tvalue = spec_wv_{key}\n\t{score}\n\tmin = {lo}\n\tmax = {hi}\n}}\n"
    out += f"spec_war_month = {{\n\tvalue = -{WAR_BASE}\n" + "".join(f"\tadd = spec_wc_{key}\n" for key in WAR_ROWS) + "}\n"
    return out + f"spec_war_stakes = {{\n\tvalue = var:spec_war_end\n\tmultiply = 4\n\tmin = {WAR_STAKES_MIN}\n\tmax = 1\n}}\n"


def _slot(n):
    rows = "".join(f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_{key} value = spec_wc_{key} }}\n"
                   f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_{key}_r value = spec_wv_{key} }}\n" for key in WAR_ROWS)
    return (f"\t\t\t\t\t{'if' if n == 1 else 'else_if'} = {{\n\t\t\t\t\t\tlimit = {{ var:spec_war_n = {n} }}\n"
            f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n} value = scope:spec_enemy }}\n"
            f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_play value = scope:war.diplomatic_play }}\n"
            f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_c value = var:spec_war_cost }}\n"
            f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_killed value = spec_war_killed }}\n"
            f"\t\t\t\t\t\tset_variable = {{ name = spec_war{n}_total value = spec_war_total }}\n{rows}\t\t\t\t\t}}\n")


# in spec_monthly's turmoil: each war by its rows, the first few kept for the tooltip, then the limit on them all
WAR_MONTHLY = ("".join(f"""			remove_variable = spec_wp{n}
			remove_variable = spec_wp{n}_k
			if = {{
				limit = {{ exists = var:spec_war{n} has_variable = spec_war{n}_killed }}
				set_variable = {{ name = spec_wp{n} value = var:spec_war{n} }}
				set_variable = {{ name = spec_wp{n}_k value = var:spec_war{n}_killed }}
			}}
""" for n in WAR_SLOTS) + "".join(f"\t\t\tremove_variable = {name}\n" for name in WAR_VARS) + f"""			remove_variable = spec_war_more
			remove_variable = spec_tm_warcap
			set_variable = {{ name = spec_war_n value = 0 }}
			set_variable = {{ name = spec_war_sum value = 0 }}
			every_scope_war = {{
				save_scope_as = war
				if = {{
					limit = {{ attacker_warleader = {{ has_war_with = root }} }}
					attacker_warleader = {{ save_scope_as = spec_enemy }}
				}}
				else = {{
					defender_warleader = {{ save_scope_as = spec_enemy }}
				}}
				root = {{
					# what this war had killed by last month, found by its enemy; a war past the kept ones counts no new losses
					set_variable = {{ name = spec_war_prev value = 0 }}
					if = {{
						limit = {{ var:spec_war_n >= {len(WAR_SLOTS)} }}
						set_variable = {{ name = spec_war_prev value = spec_war_killed }}
					}}
{"".join(f"""					if = {{
						limit = {{
							has_variable = spec_wp{n}
							exists = var:spec_wp{n}  # last month's enemy may since have been annexed
						}}
						if = {{
							limit = {{ var:spec_wp{n} = {{ this = scope:spec_enemy }} }}
							set_variable = {{ name = spec_war_prev value = var:spec_wp{n}_k }}
						}}
					}}
""" for n in WAR_SLOTS)}					set_variable = {{ name = spec_war_cost value = spec_war_month }}
					change_variable = {{ name = spec_war_n add = 1 }}
					change_variable = {{ name = spec_war_sum add = var:spec_war_cost }}
{"".join(_slot(n) for n in WAR_SLOTS)}					else = {{
						if = {{
							limit = {{ NOT = {{ has_variable = spec_war_more }} }}
							set_variable = {{ name = spec_war_more value = 0 }}
						}}
						change_variable = {{ name = spec_war_more add = var:spec_war_cost }}
					}}
					remove_variable = spec_war_cost
				}}
			}}
			change_variable = {{ name = spec_c_turmoil add = var:spec_war_sum }}
			if = {{
				limit = {{ var:spec_war_sum < {WAR_ALL_MIN} }}
				set_variable = {{ name = spec_tm_warcap value = {{ value = {WAR_ALL_MIN} subtract = var:spec_war_sum }} }}
			}}
			else_if = {{
				limit = {{ var:spec_war_sum > {WAR_ALL_MAX} }}
				set_variable = {{ name = spec_tm_warcap value = {{ value = {WAR_ALL_MAX} subtract = var:spec_war_sum }} }}
			}}
			if = {{
				limit = {{ has_variable = spec_tm_warcap }}
				change_variable = {{ name = spec_c_turmoil add = var:spec_tm_warcap }}
			}}
""")


def war_log():
    """A test build's line for each war, every reading and its points."""
    return "".join(f"""			if = {{
				limit = {{ has_variable = spec_war{n} }}
				debug_log = "SPECWAR tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] enemy=[THIS.Var('spec_war{n}').GetCountry.GetTagName] cost=[THIS.Var('spec_war{n}_c').GetValue]{''.join(f" {key}=[THIS.Var('spec_war{n}_{key}').GetValue] {key}_r=[THIS.Var('spec_war{n}_{key}_r').GetValue]" for key in WAR_ROWS)}"
			}}
""" for n in WAR_SLOTS)


# A war's end: its stakes from the losses last seen in it. A set variable can still point to a destroyed
# opponent (especially a defeated civil-war country), so resolve both objects before entering a cached scope.
# Keep the comparison in a nested block: trigger conjunctions must not evaluate a stale link for diagnostics.
STAKES = ("\t\t\tset_variable = { name = spec_war_end value = 0 }\n"
          + "".join(f"\t\t\tif = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\texists = var:spec_war{n}\n"
                    f"\t\t\t\t\texists = scope:enemy_country\n\t\t\t\t\thas_variable = spec_war{n}_total\n\t\t\t\t}}\n"
                    f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ var:spec_war{n} = {{ this = scope:enemy_country }} }}\n"
                    f"\t\t\t\t\tset_variable = {{ name = spec_war_end value = var:spec_war{n}_total }}\n\t\t\t\t}}\n\t\t\t}}\n" for n in WAR_SLOTS)
          + "\t\t\tset_variable = { name = spec_war_end value = spec_war_stakes }\n"
          "\t\t\tset_variable = { name = spec_war_stakes_now value = var:spec_war_end }\n")


def war_actions(log):
    """War ends, by on_actions lists: a one-off jump in confidence, scaled by what the war cost us. A mod's effect block
    would replace vanilla's."""
    out = "".join(f"{action} = {{\n\ton_actions = {{ spec_war_{kind} }}\n}}\n\n" for kind, action in WAR_ON_ACTIONS.items())
    for kind, (full, plain) in WAR_END.items():
        scope = WAR_END_SCOPES.get(kind)
        size = (f"\t\t\tif = {{\n\t\t\t\tlimit = {{ exists = scope:{scope} }}\n\t\t\t\tchange_variable = {{ name = spec_war_end multiply = {full} }}\n\t\t\t}}\n"
                f"\t\t\telse = {{\n\t\t\t\tchange_variable = {{ name = spec_war_end multiply = {plain} }}\n\t\t\t}}\n"
                if scope else f"\t\t\tchange_variable = {{ name = spec_war_end multiply = {full} }}\n")
        note = (f"\t\t\tdebug_log = \"SPECWAREND tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] kind={kind} "
                "end=[THIS.Var('spec_war_end').GetValue] stakes=[THIS.Var('spec_war_stakes_now').GetValue]\"\n") if log else ""
        out += (f"spec_war_{kind} = {{\n\teffect = {{\n\t\tif = {{\n\t\t\tlimit = {{ has_variable = spec_conf {UNSETTLED} }}\n"
                f"{STAKES}{size}{note}\t\t\tspec_war_jump = yes\n{SETTLED}\t\t}}\n\t}}\n}}\n\n")
    return out + capitulation_actions()


# Capitulation does not fire on_lost_war in 1.15.1. Its only named scope is the
# diplomatic play; cache that identity with each monthly war row, rather than
# borrowing casualties from an unrelated simultaneous war. Enforcement callbacks
# precede capitulation and identify the actual victims, including allied targets.
UNSETTLED = """NOT = {
    scope:diplomatic_play ?= {
        root = { is_target_in_variable_list = { name = spec_settled_plays target = prev } }
    }
}"""
SETTLED = """            if = {
                limit = { exists = scope:diplomatic_play }
                add_to_variable_list = { name = spec_settled_plays target = scope:diplomatic_play days = 2 }
            }
"""


def capitulation_actions():
    cached = "".join(f"""            if = {{
                limit = {{ var:spec_war{n}_play ?= scope:diplomatic_play has_variable = spec_war{n}_total }}
                set_variable = {{ name = spec_war_end value = var:spec_war{n}_total }}
            }}
""" for n in WAR_SLOTS)
    full, plain = WAR_END["lost"]
    return f"""on_wargoal_enforced = {{ on_actions = {{ spec_record_defeat_goal }} }}
spec_record_defeat_goal = {{
    effect = {{
        if = {{
            limit = {{ exists = scope:diplomatic_play exists = scope:target }}
            scope:target = {{
                if = {{
                    limit = {{ has_variable = spec_conf }}
                    add_to_variable_list = {{ name = spec_defeat_goal_plays target = scope:diplomatic_play days = 2 }}
                }}
            }}
        }}
    }}
}}
on_capitulation = {{ on_actions = {{ spec_war_capitulated }} }}
spec_war_capitulated = {{
    effect = {{
        if = {{
            limit = {{ has_variable = spec_conf exists = scope:diplomatic_play {UNSETTLED} }}
            set_variable = {{ name = spec_war_end value = 0 }}
{cached}            set_variable = {{ name = spec_war_end value = spec_war_stakes }}
            set_variable = {{ name = spec_war_stakes_now value = var:spec_war_end }}
            if = {{
                limit = {{ is_target_in_variable_list = {{ name = spec_defeat_goal_plays target = scope:diplomatic_play }} }}
                change_variable = {{ name = spec_war_end multiply = {full} }}
            }}
            else = {{ change_variable = {{ name = spec_war_end multiply = {plain} }} }}
            spec_war_jump = yes
{SETTLED}        }}
    }}
}}
"""


def build(write, log):
    write("common/scripted_triggers/spec_diplomacy_triggers.txt", TRIGGERS)
    write("common/scripted_effects/spec_diplomacy_effects.txt", effects(__import__("centres").RIVAL_ON) + WAR_JUMP)
    write("common/script_values/spec_war_values.txt", war_values())
    write("common/on_actions/spec_war_on_actions.txt", war_actions(log))
