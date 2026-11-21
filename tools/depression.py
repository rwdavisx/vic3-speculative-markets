"""The Long Depression: a rare world financial crisis.

It starts when a Great Power falls into a Financial Panic, from a year each game rolls for itself: EARLIEST_YEAR to
EARLIEST_SPREAD years later, so the date can't be learned (spec_ld_open marks it reached). That Great Power is remembered
(var:spec_ld_origin); a second can follow only from a different Great Power, COOLDOWN_YEARS after the first has ended,
and only in SECOND_CHANCE of games (rolled once, when the first ends). So a campaign typically sees one, sometimes two.
A cheap check runs each month from the global on_monthly_pulse. var:spec_ld_recent marks a panic that began within
WINDOW_DAYS: those countries join when it starts, with the countries strongly tied to the origin.
Global variables hold the phase (1 Crash, 2 Depression, 3 Recovery), the months left in it and the world's recovery
(0 to 100). The Depression ends when world recovery is full or after DEPRESSION_MAX months.
During the Crash it spreads in chains: each month every country that joined the month before passes it on once to
the countries tied to it at SPREAD_MIN or more (spec_every_tied: market and subject ties always, investment, trade and
ownership ties when strong enough), marked by var:spec_ld_spreading. Countries joining after the Crash do not pass it on. Each keeps
var:spec_ld, its own phase (3 early once its own recovery var:spec_ld_own is full), and gets the phase's modifier,
the phase's monthly pull on confidence (driver spec_c_world), the events and, for players, the journal entry.
Choices in the events add to the country's own recovery and the world's; a Great Power's count six times as much.

generate.py places ON_PANIC in spec_start_panic, MONTHLY in spec_monthly after the foreign panics, NO_CREDIT in the
credit limit, adds var:spec_c_world to spec_conf_pre, and calls build() and loc().
Console test (debug builds only): `event spec_depression.90 TAG` starts it now with TAG among the affected,
`event spec_depression.91 TAG` moves to the next phase, `event spec_depression.92 TAG` adds 25 world recovery.
"""
import re

import companies
import icons
import market_tab
import stories
import tuning

# three 20 year runs from 1836: one Great Power panic among them, so the first one starts it rather than a share of world GDP
EARLIEST_YEAR = tuning.get("EARLIEST_YEAR", 1868)  # 1845 started it in 1845 once Great Powers could panic; the real one began in 1873
EARLIEST_SPREAD = tuning.get("EARLIEST_SPREAD", 10)  # a fixed 1870 started 3 of 11 in 1870 itself, which reads as scripted
SECOND_CHANCE = tuning.get("SECOND_CHANCE", 50)    # percent of games where a second one can follow, from another Great Power
WINDOW_DAYS = 365       # countries whose panic began this recently join when it starts
MAX_PER_GAME = 2
COOLDOWN_YEARS = 25     # after the Recovery ends before another can start
CRASH_MONTHS = 4
# a tie at least this strong passes the crash on (generate.LINKS, scaled by vanilla_ties): market 1 and subject 0.8
# always, investment 0.6 always, trade 0.4 only under free trade (0.6); protectionism 0.28 and isolationism 0.04 never
SPREAD_MIN = tuning.get("SPREAD_MIN", 0.5)
DEPRESSION_MAX = tuning.get("DEPRESSION_MAX", 60)     # a backstop: WORLD_DRIFT alone takes 50 months
RECOVERY_MONTHS = 12
PHASES = {1: "World Crash", 2: "Depression", 3: "Recovery"}
# confidence a month by phase, against the drift back to 55.
# At -5 and -1 a 20 year run had half its panics come from the Long Depression; at -3 and -0.5 (0.9) confidence only
# fell from the mid 50s to the mid 40s and players found it too easy. At -4 and -0.75 (sweep cmp1) it fell to 25-31, the
# Depression held 12-14% of its months in a panic against 6% and began 56% of all panics, and the Recovery stayed near 37.
# At -4, -0.6 and +1 (sweep cmp2, 3 games): Crash 5 months, Depression 43; confidence 60 before, 43 in the Crash, 34 in
# the Depression, 53 in the Recovery; 10% of Depression months in a panic; half of all panics begin in the Crash or
# Depression; 7.9 panics per 100 country-years against 7.1 in 0.9; median GDP -12% to -15% over the Crash and Depression
PRESSURE = tuning.get("LD_PRESSURE", {1: -4, 2: -0.6, 3: 1})
# world recovery a month in the Depression, out of 100. An affected country gets an event about every 20 months
# (EVENT_CHANCE, then EVENT_GAP). Measured in 0.9 (drift 2, others 0.5): some 130 countries joined, their choices added
# about 3 a month and the Depression lasted 17 to 22 months, not the 36 to 42 meant. So the many small countries count
# for a fifth of what they did and the Great Powers decide it. At drift 1.5 (sweep cmp1) the choices added about 0.6 a
# month and it lasted 45 to 50 months, so 2
WORLD_DRIFT = tuning.get("WORLD_DRIFT", 2)
OWN_DRIFT = 1           # a country's own recovery a month in the Depression
WORLD = tuning.get("LD_WORLD", {"up": (3, 0.1), "big": (6, 0.2), "down": (-3, -0.1)})   # world recovery from a choice: Great Power, other
TARIFF_HIT = 4          # confidence a tied partner loses to our tariffs, before the tie weight and the two GDPs
EVENT_CHANCE = 10       # percent a month that an affected country in the Depression gets one of events 2 to 7
EVENT_GAP = 300         # days after one before the next
# ponytail: numbers untested in a run; calibrate how often it fires and how long the Depression lasts from a --log run

E = "gfx/interface/icons/event_icons"
MODS = {  # phase modifier -> vanilla icon, modifier lines
    "spec_ld_crash": ("coins_negative", {
        "state_capitalists_investment_pool_efficiency_mult": -0.3, "state_aristocrats_investment_pool_efficiency_mult": -0.3,
        "state_shopkeepers_investment_pool_efficiency_mult": -0.3, "country_loan_interest_rate_mult": 0.35,
        "state_construction_mult": -0.1, companies.FD_SOL: -2}),
    "spec_ld_depression": ("gear_negative", {
        "state_capitalists_investment_pool_efficiency_mult": -0.15, "state_aristocrats_investment_pool_efficiency_mult": -0.15,
        "state_shopkeepers_investment_pool_efficiency_mult": -0.15, "country_loan_interest_rate_mult": 0.2,
        "state_construction_mult": -0.15, "state_trade_quantity_mult": -0.15,
        "state_radicals_and_loyalists_from_sol_change_mult": 0.35, companies.FD_SOL: -1}),
}
MOD_NAMES = {"spec_ld_crash": "World Crash", "spec_ld_depression": "$SPEC_LD_NAME$"}
# timed interest group modifiers: key, icon, approval, name
IG_MODS = [
    ("spec_ld_austerity", "coins_negative", -2, "Austerity"),
    ("spec_ld_protection_won", "flag_positive", 2, "Tariff Protection"),
    ("spec_ld_free_trade_lost", "flag_negative", -1, "Free Trade Abandoned"),
    ("spec_ld_protection_denied", "flag_negative", -2, "Protection Denied"),
    ("spec_ld_free_trade_kept", "flag_positive", 1, "Free Trade Upheld"),
    ("spec_ld_relief_granted", "coins_positive", 2, "Relief Granted"),
    ("spec_ld_relief_refused", "fist_negative", -2, "Relief Refused"),
    ("spec_ld_rates_spared", "coins_positive", 1, "Ratepayers Spared"),
    ("spec_ld_deposits_frozen", "coins_negative", -1, "Deposits Frozen"),
    ("spec_ld_savings_lost", "fist_negative", -2, "Savings Lost"),
    ("spec_ld_sound_money", "coins_positive", 2, "Sound Money"),
    ("spec_ld_dear_money", "coins_negative", -2, "Dear Money"),
    ("spec_ld_easy_money", "coins_positive", 2, "Easy Money"),
    ("spec_ld_debased", "coins_negative", -2, "Currency Debased"),
    ("spec_ld_marchers_dispersed", "fist_negative", -2, "Marchers Dispersed"),
    ("spec_ld_order_kept", "rifle_positive", 1, "Order Kept"),
    ("spec_ld_marchers_heard", "flag_positive", 2, "Petition Heard"),
    ("spec_ld_inquiry_welcomed", "documents_positive", 2, "Inquiry Welcomed"),
    ("spec_ld_inquiry_resented", "documents_negative", -1, "Inquiry Resented"),
    ("spec_ld_reform_refused", "documents_negative", -2, "Reform Refused"),
    ("spec_ld_system_defended", "flag_positive", 1, "System Defended"),
]
# timed country modifiers: key, icon, line, name; money ones scaled by vanilla's GDP multipliers
COUNTRY_MODS = [
    ("spec_ld_exchange_support", "coins_negative", "country_expenses_add = 1", "Support for the Exchanges"),
    ("spec_ld_relief_works", "coins_negative", "country_expenses_add = 1", "Relief Works"),
    ("spec_ld_petition_relief", "coins_negative", "country_expenses_add = 1", "Relief for the Unemployed"),
    ("spec_ld_inquiry", "documents_positive", "country_legitimacy_base_add = 5", "Commission of Inquiry"),
]
# message key -> icon, color, toast title, toast text
NOTES = {
    "spec_ld_started": ("rank_down", "bad", "The $SPEC_LD_NAME$ begins",
                        "[Concept('concept_spec_financial_panic','$concept_spec_financial_panics$')] have spread across the world economy, "
                        "and the World Crash has begun. The [concept_spec_long_depression] will follow."),
    "spec_ld_deepens": ("rank_down", "bad", "The World Crash deepens",
                        "The World Crash has become the [concept_spec_long_depression]. Investment, construction and trade will stay weak until "
                        "the world recovers."),
    "spec_ld_lifts": ("rank_up", "good", "The depression lifts",
                      "The world has recovered from the [concept_spec_long_depression], and [concept_spec_market_confidence] will return over the coming year."),
    "spec_ld_over": ("rank_up", "neutral", "The world economy recovers",
                     "The world's recovery from the [concept_spec_long_depression] is complete."),
    "spec_ld_recovered": ("rank_up", "good", "Our economy recovers",
                          "Our economy has recovered from the [concept_spec_long_depression] ahead of the world, and "
                          "[concept_spec_market_confidence] returns here while others still struggle."),
}
OWN_STEPS, WORLD_STEPS = set(), set()

# for generate.py
ON_PANIC = (f"\tset_variable = {{ name = spec_ld_recent value = yes days = {WINDOW_DAYS} }}\n"
            # halve the phase modifier at once (spec_ld_apply)
            "\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_ld\n\t\t\thas_global_variable = spec_ld_phase\n\t\t}\n"
            "\t\tspec_ld_apply = yes\n\t}\n")
NO_CREDIT = "\t\t\t\t\tNOT = { has_modifier = spec_ld_crash }\n"
# set while the country has the World Crash's modifier, for the GUI, which cannot read modifiers. ponytail: an older
# save's crash gets it at its next spec_ld_apply (a panic starting or ending, or the next phase)
CRASH_FLAG = "spec_world_crash"
MONTHLY = f"""			# the Long Depression (depression.py): tariffs abroad, this month's pull, our own recovery
			if = {{
				limit = {{ has_variable = spec_ld_tariff }}
				change_variable = {{ name = spec_c_world subtract = var:spec_ld_tariff }}
				remove_variable = spec_ld_tariff
			}}
			if = {{
				limit = {{
					has_variable = spec_ld
					has_global_variable = spec_ld_phase
				}}
				if = {{
					limit = {{ var:spec_ld = 2 }}
					spec_ld_own = {{ AMOUNT = spec_ld_own_drift }}
				}}
				# a panic ended: the phase modifier back to full strength (spec_ld_apply)
				if = {{
					limit = {{
						has_variable = spec_ld_half
						NOT = {{ has_variable = spec_panic }}
					}}
					spec_ld_apply = yes
				}}
				set_variable = {{ name = spec_ld_conf value = spec_ld_pressure }}
				change_variable = {{ name = spec_c_world add = var:spec_ld_conf }}
				spec_ld_bars = yes
			}}
"""


def values():
    branches = "".join(f"\t{'if' if p == 1 else 'else_if'} = {{\n\t\tlimit = {{ var:spec_ld ?= {p} }}\n\t\tvalue = {n:g}\n\t}}\n"
                       for p, n in PRESSURE.items())
    return (f"# confidence a month from the phase the country is in\nspec_ld_pressure = {{\n\tvalue = 0\n{branches}}}\n"
            "# the phase modifier's strength: half during a Financial Panic (spec_ld_apply)\n"
            "spec_ld_strength = {\n\tvalue = 1\n\tif = {\n\t\tlimit = { has_variable = spec_ld_half }\n\t\tvalue = 0.5\n\t}\n}\n")


TRIGGERS = """# in a Financial Panic, or one began within the window
spec_ld_in_window = {
	OR = {
		has_variable = spec_panic
		has_variable = spec_ld_recent
	}
}

spec_ld_is_gp = {
	country_rank = rank_value:great_power
}
"""


def effects():
    # the phase's modifier at half strength during a Financial Panic, whose own modifier already hits investment;
    # var:spec_ld_half remembers which strength is on (MONTHLY reapplies when the panic starts or ends)
    phase_mods = ("\tif = {\n\t\tlimit = { has_variable = spec_panic }\n\t\tset_variable = spec_ld_half\n\t}\n"
                  "\telse_if = {\n\t\tlimit = { has_variable = spec_ld_half }\n\t\tremove_variable = spec_ld_half\n\t}\n")
    phase_mods += "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m in MODS)
    phase_mods += f"\tremove_variable = {CRASH_FLAG}\n"
    phase_mods += "".join(f"\t{'if' if p == 1 else 'else_if'} = {{\n\t\tlimit = {{ var:spec_ld = {p} }}\n"
                          f"\t\tadd_modifier = {{\n\t\t\tname = {m}\n\t\t\tmultiplier = spec_ld_strength\n\t\t}}\n"
                          + (f"\t\tset_variable = {CRASH_FLAG}\n" if m == "spec_ld_crash" else "") + "\t}\n"
                          for p, m in ((1, "spec_ld_crash"), (2, "spec_ld_depression")))
    unmod = "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m in MODS)
    # Keep the historical origin and event cooldown: reopening the market economy must not let the same
    # country start the world's second depression or immediately replay its paid events.
    leave = unmod + "".join(f"\tremove_variable = {v}\n" for v in (
        "spec_ld", "spec_ld_own", "spec_ld_conf", "spec_ld_half", "spec_ld_spreading", "spec_ld_spread_now",
        "spec_ld_tariff", "spec_ld_recent", CRASH_FLAG))
    return f"""# monthly from on_monthly_pulse, no scope: the phase clock while it runs, otherwise the check whether it starts
spec_ld_tick = {{
	# Repair old saves whose market economy closed with phase modifiers still active, or whose crisis state
	# outlived the world's crisis. Normal market shutdown calls spec_ld_leave immediately.
	every_country = {{
		limit = {{
			OR = {{
				has_variable = spec_ld
				has_modifier = spec_ld_crash
				has_modifier = spec_ld_depression
			}}
			OR = {{
				NOT = {{ has_variable = spec_conf }}
				NOT = {{ spec_law_mult > 0 }}
				NOT = {{ has_global_variable = spec_ld_phase }}
			}}
		}}
		spec_ld_leave = yes
	}}
	# this game's own earliest year, rolled once in months
	if = {{
		limit = {{
			game_date >= {EARLIEST_YEAR}.1.1
			NOT = {{ has_global_variable = spec_ld_open }}
		}}
		if = {{
			limit = {{ NOT = {{ has_global_variable = spec_ld_wait }} }}
			set_global_variable = {{ name = spec_ld_wait value = {{ fixed_range = {{ min = 0 max = {EARLIEST_SPREAD * 12} }} }} }}
		}}
		change_global_variable = {{ name = spec_ld_wait add = -1 }}
		if = {{
			limit = {{
				OR = {{
					global_var:spec_ld_wait <= 0
					game_date >= {EARLIEST_YEAR + EARLIEST_SPREAD}.1.1
				}}
			}}
			set_global_variable = spec_ld_open
			remove_global_variable = spec_ld_wait
		}}
	}}
	if = {{
		limit = {{ has_global_variable = spec_ld_phase }}
		# the Crash spreads: last month's joiners pass it on once along their strong ties. Two passes, so a country
		# reached this month waits for the next whether or not the event fires at once
		if = {{
			limit = {{ global_var:spec_ld_phase = 1 }}
			every_country = {{
				limit = {{ has_variable = spec_ld_spreading }}
				remove_variable = spec_ld_spreading
				set_variable = spec_ld_spread_now
			}}
			every_country = {{
				limit = {{ has_variable = spec_ld_spread_now }}
				remove_variable = spec_ld_spread_now
				trigger_event = {{ id = spec_depression.99 }}
			}}
		}}
		change_global_variable = {{ name = spec_ld_months add = -1 }}
		if = {{
			limit = {{ global_var:spec_ld_phase = 2 }}
			spec_ld_world = {{ AMOUNT = {WORLD_DRIFT} }}
		}}
		if = {{
			limit = {{
				OR = {{
					global_var:spec_ld_months <= 0
					AND = {{
						global_var:spec_ld_phase = 2
						global_var:spec_ld_progress >= 100
					}}
				}}
			}}
			spec_ld_next_phase = yes
		}}
	}}
	else_if = {{
		limit = {{
			has_global_variable = spec_ld_open
			NOT = {{ has_global_variable = spec_ld_cooldown }}
			OR = {{
				NOT = {{ has_global_variable = spec_ld_count }}
				AND = {{
					global_var:spec_ld_count < {MAX_PER_GAME}
					has_global_variable = spec_ld_second
				}}
			}}
		}}
		# a Great Power in a Financial Panic, not the one that started an earlier Long Depression
		random_country = {{
			limit = {{
				spec_ld_is_gp = yes
				has_variable = spec_panic
				spec_law_mult > 0
				NOT = {{ has_variable = spec_ld_origin }}
			}}
			set_variable = spec_ld_origin
			spec_ld_start = yes
		}}
	}}
}}

spec_ld_start = {{
	set_global_variable = {{ name = spec_ld_phase value = 1 }}
	set_global_variable = {{ name = spec_ld_months value = {CRASH_MONTHS} }}
	set_global_variable = {{ name = spec_ld_progress value = 0 }}
	if = {{
		limit = {{ has_global_variable = spec_ld_count }}
		change_global_variable = {{ name = spec_ld_count add = 1 }}
	}}
	else = {{
		set_global_variable = {{ name = spec_ld_count value = 1 }}
	}}
	every_country = {{
		limit = {{ spec_ld_in_window = yes }}
		spec_ld_join = yes
	}}
	# the origin's strong ties join now, from an event on it (spec_every_tied needs it as root); the rest spreads monthly
	trigger_event = {{ id = spec_depression.99 }}
	spec_ld_notify = {{ TYPE = spec_ld_started }}
}}

# from spec_every_tied: a tie at SPREAD_MIN or more passes the crash on. WEIGHT is a number or a script value
# name, so it is compared through a local
spec_ld_tied_join = {{
	set_local_variable = {{ name = spec_ld_w value = $WEIGHT$ }}
	if = {{
		limit = {{ local_var:spec_ld_w >= {SPREAD_MIN:g} }}
		spec_ld_join = yes
	}}
}}

# on a country: it enters the Long Depression in the current phase. Never reads root.
spec_ld_join = {{
	if = {{
		limit = {{
			has_variable = spec_conf
			spec_law_mult > 0
			NOT = {{ has_variable = spec_ld }}
			has_global_variable = spec_ld_phase
		}}
		set_variable = {{ name = spec_ld value = 0 }}
		set_variable = {{ name = spec_ld_own value = 0 }}
		# joined during the Crash: passes it on next month (spec_ld_tick)
		if = {{
			limit = {{ global_var:spec_ld_phase = 1 }}
			set_variable = spec_ld_spreading
		}}
		# credit freezes: the banks call in part of what they lent, unless a panic already has, now or in the last year
		if = {{
			limit = {{
				has_variable = spec_debt
				NOT = {{ has_variable = spec_panic }}
				NOT = {{ has_variable = spec_panic_cooldown }}  # ponytail: the 12 months after a panic ends, at least 12 since it began
			}}
			set_variable = {{ name = spec_clawed value = spec_clawback }}
			add_investment_pool = {{ value = var:spec_clawed multiply = -1 }}
			change_variable = {{ name = spec_debt subtract = var:spec_clawed }}
		}}
		add_radicals = {{ value = small_radicals pop_type = capitalists }}
		spec_ld_apply = yes
		if = {{
			limit = {{
				is_player = yes
				# a Great Power that started it can be reached twice in one tick: as the one in a panic and as a tie
				NOT = {{ has_journal_entry = je_spec_depression }}
			}}
			add_journal_entry = {{ type = je_spec_depression }}
		}}
		trigger_event = {{ id = spec_depression.1 popup = yes }}
	}}
}}

# on an affected country: var:spec_ld is the world's phase, or Recovery once its own recovery is full, and only
# that phase's modifier applies
spec_ld_apply = {{
	set_variable = {{ name = spec_ld value = global_var:spec_ld_phase }}
	if = {{
		limit = {{
			var:spec_ld = 2
			var:spec_ld_own >= 100
		}}
		set_variable = {{ name = spec_ld value = 3 }}
	}}
{phase_mods}}}

# no scope: the next phase, or the end after the Recovery
spec_ld_next_phase = {{
	if = {{
		limit = {{ global_var:spec_ld_phase = 1 }}
		set_global_variable = {{ name = spec_ld_phase value = 2 }}
		set_global_variable = {{ name = spec_ld_months value = {DEPRESSION_MAX} }}
		every_country = {{
			limit = {{ has_variable = spec_ld }}
			remove_variable = spec_ld_spreading
			spec_ld_apply = yes
		}}
		spec_ld_notify = {{ TYPE = spec_ld_deepens }}
	}}
	else_if = {{
		limit = {{ global_var:spec_ld_phase = 2 }}
		set_global_variable = {{ name = spec_ld_phase value = 3 }}
		set_global_variable = {{ name = spec_ld_months value = {RECOVERY_MONTHS} }}
		set_global_variable = {{ name = spec_ld_progress value = 100 }}
		every_country = {{
			limit = {{ has_variable = spec_ld }}
			spec_ld_apply = yes
			trigger_event = {{ id = spec_depression.8 popup = yes }}
		}}
		spec_ld_notify = {{ TYPE = spec_ld_lifts }}
	}}
	else = {{
		every_country = {{
			limit = {{ has_variable = spec_ld }}
			spec_ld_leave = yes
		}}
		remove_global_variable = spec_ld_phase
		remove_global_variable = spec_ld_months
		remove_global_variable = spec_ld_progress
		set_global_variable = {{ name = spec_ld_cooldown value = yes days = {COOLDOWN_YEARS * 365} }}
		random = {{
			chance = {SECOND_CHANCE}
			set_global_variable = spec_ld_second
		}}
		spec_ld_notify = {{ TYPE = spec_ld_over }}
	}}
}}

# on a country: stop the lasting crisis effects when the crisis ends or the market economy closes
spec_ld_leave = {{
{leave}}}

spec_ld_notify = {{
	every_country = {{
		limit = {{ is_player = yes }}
		post_notification = $TYPE$
	}}
}}

# on an affected country: its own recovery, which takes it into the Recovery early once full
spec_ld_own = {{
	if = {{
		limit = {{ has_variable = spec_ld_own }}
		change_variable = {{ name = spec_ld_own add = $AMOUNT$ }}
		clamp_variable = {{ name = spec_ld_own min = 0 max = 100 }}
		if = {{
			limit = {{
				var:spec_ld = 2
				var:spec_ld_own >= 100
			}}
			spec_ld_apply = yes
			if = {{
				limit = {{ is_player = yes }}
				post_notification = spec_ld_recovered
			}}
		}}
		spec_ld_bars = yes
	}}
}}

spec_ld_world = {{
	if = {{
		limit = {{ has_global_variable = spec_ld_progress }}
		change_global_variable = {{ name = spec_ld_progress add = $AMOUNT$ }}
		clamp_global_variable = {{ name = spec_ld_progress min = 0 max = 100 }}
	}}
}}

# root is the country
spec_ld_bars = {{
	je:je_spec_depression ?= {{
		set_bar_progress = {{ name = spec_ld_world_bar value = global_var:spec_ld_progress }}
		set_bar_progress = {{ name = spec_ld_own_bar value = root.var:spec_ld_own }}
	}}
}}

# on a country tied to root, which has raised its tariffs: lost confidence, applied on its next monthly update
spec_ld_tariff_hit = {{
	if = {{
		limit = {{
			has_variable = spec_conf
			gdp > 0
		}}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_ld_tariff }} }}
			set_variable = {{ name = spec_ld_tariff value = 0 }}
		}}
		change_variable = {{
			name = spec_ld_tariff
			add = {{
				value = root.gdp
				divide = gdp
				max = 1
				multiply = {TARIFF_HIT}
				multiply = $WEIGHT$
			}}
		}}
	}}
}}
"""


def on_actions():
    picks = "".join(f"\t\t100 = spec_depression.{i}\n" for i in range(2, 8))
    return f"""on_monthly_pulse = {{
	on_actions = {{ spec_ld_pulse }}
}}

spec_ld_pulse = {{
	effect = {{
		spec_ld_tick = yes
	}}
}}

on_monthly_pulse_country = {{
	on_actions = {{ spec_ld_country_pulse }}
}}

spec_ld_country_pulse = {{
	trigger = {{
		var:spec_ld ?= 2
		NOT = {{ has_variable = spec_ld_event_cd }}
	}}
	random_events = {{
		chance_to_happen = {EVENT_CHANCE}
{picks}	}}
}}
"""


def modifiers():
    out = ["# the phase modifiers, one at a time from spec_ld_apply\n"]
    out += [f"{k} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_{icon}.dds\n"
            + "".join(f"\t{t} = {n:g}\n" for t, n in lines.items()) + "}\n\n" for k, (icon, lines) in MODS.items()]
    out.append("# timed interest group and country modifiers from the events\n")
    out += [f"{k} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_{icon}.dds\n\tinterest_group_approval_add = {n}\n}}\n\n"
            for k, icon, n, _ in IG_MODS]
    out += [f"{k} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_{icon}.dds\n\t{line}\n}}\n\n"
            for k, icon, line, _ in COUNTRY_MODS]
    return "".join(out)


def journal():
    status = "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_ld_status_{p}\n\t\t\t\ttrigger = {{ global_var:spec_ld_phase ?= {p} }}\n\t\t\t}}\n"
                     for p in (1, 2))
    return f"""je_spec_depression = {{
	icon = "{icons.path('event_panic')}"
	group = je_group_internal_affairs

	# added to affected players by spec_ld_join; AI countries decide through the events. Shown (and so activated)
	# for an affected player, so an entry left inactive comes back by itself (generate.py's je_spec_markets)
	is_shown_when_inactive = {{
		is_player = yes
		has_variable = spec_ld
	}}
	activation_description = {{
		always = yes
	}}
	outcome = {{
		header = je_standard_completion_header
		effect_header = je_standard_on_completion_header
		color = "gold_positive"
		conclusion_desc = je_standard_completion_conclusion_desc
		trigger = {{
			custom_tooltip = {{
				text = spec_ld_complete_tt
				NOR = {{
					global_var:spec_ld_phase ?= 1
					global_var:spec_ld_phase ?= 2
				}}
			}}
		}}
	}}
	outcome = {{
		flags = {{ hidden invalid_outcome }}
		conclusion_desc = je_standard_failure_conclusion_desc
		trigger = {{ NOT = {{ has_variable = spec_ld }} }}
	}}

	status_desc = {{
		first_valid = {{
{status}		}}
	}}

	scripted_progress_bar = spec_ld_world_bar
	scripted_progress_bar = spec_ld_own_bar

	weight = 10
}}
"""


def bars():
    return "".join(f"""{b} = {{
	name = "{b}"
	desc = "{b}_desc"
	start_value = 0
	min_value = 0
	max_value = 100
	default_green = yes
}}

""" for b in ("spec_ld_world_bar", "spec_ld_own_bar"))


def messages():
    return "\n".join(f"""{key} = {{
	type = country
	group = "spec_ld_notification_group"

	texture = "gfx/interface/icons/notification_icons/{icon}.dds"

	notification_type = toast
	color = {color}
}}
""" for key, (icon, color, *_) in NOTES.items())


# -- events ------------------------------------------------------------------------------------------------

def step_key(what, n):
    return f"spec_ld_{what}_{'up' if n > 0 else 'down'}_{abs(n):g}".replace(".", "_")


def own(n):
    OWN_STEPS.add(n)
    return f"\t\tcustom_tooltip = {{\n\t\t\ttext = {step_key('own', n)}\n\t\t\tspec_ld_own = {{ AMOUNT = {n:g} }}\n\t\t}}\n"


def world(kind):
    """World recovery from a choice: a Great Power's counts for more."""
    gp, other = WORLD[kind]
    WORLD_STEPS.update((gp, other))
    tip = lambda n: (f"\t\t\tcustom_tooltip = {{\n\t\t\t\ttext = {step_key('world', n)}\n"
                     f"\t\t\t\tspec_ld_world = {{ AMOUNT = {n:g} }}\n\t\t\t}}\n")
    return f"\t\tif = {{\n\t\t\tlimit = {{ spec_ld_is_gp = yes }}\n{tip(gp)}\t\t}}\n\t\telse = {{\n{tip(other)}\t\t}}\n"


TARIFF = "\t\tcustom_tooltip = {\n\t\t\ttext = spec_ld_tariff_tt\n\t\t\tspec_every_tied = { EFFECT = spec_ld_tariff_hit }\n\t\t}\n"


def temper(t, n):
    # as generate.py's: the AI's credit temperament, -1 Cautious, 1 Bold (credit_ai.py)
    return f"\t\t\tmodifier = {{\n\t\t\t\ttrigger = {{ var:spec_temper ?= {t} }}\n\t\t\t\tadd = {n}\n\t\t\t}}\n"


def option(n, letter, body, ai, tempers=(), default=False):
    return (f"\toption = {{\n\t\tname = spec_depression.{n}.{letter}\n" + ("\t\tdefault_option = yes\n" if default else "")
            + body + f"\t\tai_chance = {{\n\t\t\tbase = {ai}\n" + "".join(temper(t, w) for t, w in tempers) + "\t\t}\n\t}\n")


def event(n, pics, icon, trigger, options, mid=True):
    """Events 2 to 7 come from the monthly pulse during the Depression, at most one per EVENT_GAP and each once
    in five years; 1 and 8 open and close it."""
    head = ("\tcooldown = { days = normal_modifier_time }\n\n" if mid else "")
    imm = (f"\timmediate = {{\n\t\tset_variable = {{ name = spec_ld_event_cd value = yes days = {EVENT_GAP} }}\n\t}}\n\n"
           if mid else "")
    return f"""
spec_depression.{n} = {{
	type = country_event
	placement = root
	title = spec_depression.{n}.t
	desc = spec_depression.{n}.d
	flavor = spec_depression.{n}.f
	duration = 3
{stories.pictures(pics)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "{icon}"
{head}	trigger = {{
{trigger}	}}

{imm}{"".join(options)}}}
"""


def events(log=False):
    ig, country, pops, conf = stories.ig, stories.country, stories.pops, stories.conf
    affected = "\t\thas_variable = spec_ld\n\t\thas_variable = spec_conf\n\t\tspec_law_mult > 0\n"
    mid = "\t\tvar:spec_ld ?= 2\n\t\thas_variable = spec_conf\n\t\tspec_law_mult > 0\n"
    out = [
        # opening, on joining
        event(1, {"west": "unspecific_factory_closed", "africa": "africa_public_protest", "asia": "asia_poor_people_moving"},
              icons.path("event_panic"), affected, [
                  option(1, "a", own(10) + ig("trade_unions", "spec_ld_austerity"), 50, [(-1, 30)], default=True),
                  option(1, "b", conf(6) + world("up") + country("spec_ld_exchange_support", "very_short_modifier_time", "small"),
                         50, [(1, 30)]),
              ], mid=False),
        # tariffs
        event(2, {"west": "unspecific_steam_ship", "asia": "asia_westerners_arriving"}, f"{E}/event_trade.dds", mid, [
            option(2, "a", own(20) + world("down") + TARIFF + ig("industrialists", "spec_ld_protection_won")
                   + ig("landowners", "spec_ld_protection_won") + ig("intelligentsia", "spec_ld_free_trade_lost"), 40, [(-1, 30)]),
            option(2, "b", world("big") + conf(-3) + ig("industrialists", "spec_ld_protection_denied")
                   + ig("landowners", "spec_ld_protection_denied") + ig("intelligentsia", "spec_ld_free_trade_kept"), 40, [(1, 30)], default=True),
        ]),
        # relief works
        event(3, {"west": "unspecific_trains", "latam": "southamerica_factory_opening", "mideast": "middleeast_engineer_blueprint",
                  "africa": "africa_construction_colony"}, f"{E}/event_industry.dds", mid, [
            option(3, "a", country("spec_ld_relief_works", "short_modifier_time", "medium") + own(12) + world("up")
                   + pops("loyalists", "small", "strata = lower") + ig("trade_unions", "spec_ld_relief_granted"), 40, [(1, 30)]),
            option(3, "b", pops("radicals", "small", "strata = lower") + ig("trade_unions", "spec_ld_relief_refused")
                   + ig("petty_bourgeoisie", "spec_ld_rates_spared"), 40, [(-1, 30)], default=True),
        ]),
        # a run on the banks
        event(4, {"west": "unspecific_vandalized_storefront", "mideast": "middleeast_police_breaking_door",
                  "africa": "africa_public_protest"}, f"{E}/event_protest.dds", mid, [
            option(4, "a", conf(4) + own(5) + ig("petty_bourgeoisie", "spec_ld_deposits_frozen"), 40, default=True),
            option(4, "b", stories.RESCUE_PAY + conf(10) + own(10) + world("up") + stories.BAILOUT_IGS, 30, [(1, 30)]),
            option(4, "c", conf(-6) + own(4) + pops("radicals", "small", "strata = middle")
                   + ig("petty_bourgeoisie", "spec_ld_savings_lost") + ig("intelligentsia", "spec_story_sound_finance"), 30, [(-1, 30)]),
        ]),
        # sound money or easy credit
        event(5, {"west": "europenorthamerica_capitalists_meeting", "latam": "southamerica_aristocrats",
                  "mideast": "unspecific_politicians_arguing", "africa": "africa_leader_arguing",
                  "asia": "asia_politician_parliament_motion"}, f"{E}/event_scales.dds", mid, [
            option(5, "a", conf(5) + own(-5) + world("up") + ig("landowners", "spec_ld_sound_money")
                   + ig("rural_folk", "spec_ld_dear_money"), 50, [(-1, 30)], default=True),
            option(5, "b", own(15) + conf(-5) + world("down") + ig("rural_folk", "spec_ld_easy_money")
                   + ig("landowners", "spec_ld_debased"), 50, [(1, 30)]),
        ]),
        # the unemployed march on the capital
        event(6, {"west": "europenorthamerica_rich_and_poor", "mideast": "middleeast_police_breaking_door",
                  "africa": "africa_soldiers_breaking_protest", "asia": "asia_union_leader"}, f"{E}/event_protest.dds", mid, [
            option(6, "a", pops("radicals", "medium", "strata = lower") + ig("trade_unions", "spec_ld_marchers_dispersed")
                   + ig("armed_forces", "spec_ld_order_kept"), 40, [(-1, 20)], default=True),
            option(6, "b", country("spec_ld_petition_relief", "very_short_modifier_time", "small") + own(5)
                   + pops("loyalists", "small", "strata = lower") + ig("trade_unions", "spec_ld_marchers_heard"), 40, [(1, 20)]),
        ]),
        # calls for reform
        event(7, {"west": "unspecific_politicians_arguing", "latam": "southamerica_election", "africa": "africa_leader_arguing",
                  "asia": "asia_politician_parliament_motion"}, f"{E}/event_newspaper.dds", mid, [
            option(7, "a", country("spec_ld_inquiry", "short_modifier_time") + own(5) + ig("intelligentsia", "spec_ld_inquiry_welcomed")
                   + ig("industrialists", "spec_ld_inquiry_resented"), 50, [(-1, 20)], default=True),
            option(7, "b", conf(3) + pops("radicals", "small", "strata = middle") + ig("industrialists", "spec_ld_system_defended")
                   + ig("intelligentsia", "spec_ld_reform_refused"), 50, [(1, 20)]),
        ]),
        # closing, when the world enters the Recovery
        event(8, {"west": "unspecific_world_fair", "latam": "southamerica_factory_opening", "mideast": "middleeast_engineer_blueprint",
                  "africa": "africa_city_center", "asia": "asia_farmers_market"}, f"{E}/event_industry.dds", affected, [
            option(8, "a", conf(3) + ig("intelligentsia", "spec_prudent_counsel"), 50, [(-1, 30)], default=True),
            option(8, "b", conf(8) + ig("industrialists", "spec_boom_riding") + ig("intelligentsia", "spec_story_lessons_unlearned"),
                   50, [(1, 30)]),
        ], mid=False),
    ]
    hidden = [
        # console tests, excluded from the release build
        (90, "if = { limit = { NOT = { has_global_variable = spec_ld_phase } } spec_ld_start = yes } spec_ld_join = yes"),
        (91, "if = { limit = { has_global_variable = spec_ld_phase } spec_ld_next_phase = yes }"),
        (92, "spec_ld_world = { AMOUNT = 25 }"),
    ] if log else []
    hidden += [
        # on a country in the Crash, once: the countries strongly tied to it join
        (99, "if = { limit = { global_var:spec_ld_phase ?= 1 has_variable = spec_conf spec_law_mult > 0 } "
             "remove_variable = spec_ld_spreading spec_every_tied = { EFFECT = spec_ld_tied_join } }"),
    ]
    out += [f"\nspec_depression.{n} = {{\n\ttype = country_event\n\thidden = yes\n\timmediate = {{ {effect} }}\n}}\n"
            for n, effect in hidden]
    return "namespace = spec_depression\n" + "".join(out)


def check_modifiers(game, mod):
    """Every modifier type used here is defined by vanilla or by the mod (companies.py)."""
    defs = "\n".join(p.read_text(encoding="utf-8-sig") for p in (game / "common/modifier_type_definitions").glob("*.txt"))
    defs += (mod / "common/modifier_type_definitions/spec_modifier_types.txt").read_text(encoding="utf-8-sig")
    known = set(re.findall(r"^(\w+)\s*=\s*\{", defs, re.M))
    used = {t for _, lines in MODS.values() for t in lines} | {line.split()[0] for *_, line, _ in COUNTRY_MODS} | {"interest_group_approval_add"}
    assert used <= known, f"unknown modifier types: {sorted(used - known)}"


def build(write, game, mod, log=False):
    write("common/script_values/spec_depression_values.txt", values())
    write("common/scripted_triggers/spec_depression_triggers.txt", TRIGGERS)
    write("common/scripted_effects/spec_depression_effects.txt", effects())
    write("common/on_actions/spec_depression_on_actions.txt", on_actions())
    write("common/static_modifiers/spec_depression_modifiers.txt", modifiers())
    write("common/journal_entries/spec_depression_journal.txt", journal())
    write("common/scripted_progress_bars/spec_depression_bars.txt", bars())
    write("common/messages/spec_depression_messages.txt", messages())
    write("events/spec_depression_events.txt", events(log))  # before stories.loc(), which lists the conf() tooltips used here
    check_modifiers(game, mod)


# -- localization ------------------------------------------------------------------------------------------

CAP = stories.CAP
GPS = "[Concept('concept_great_power','$concept_great_powers$')]"
TEXT = {  # event -> title, desc, flavor, options
    1: ("The $SPEC_LD_NAME$",
        "The panics on the world's exchanges have joined into one. Credit has stopped moving between the great houses, prices "
        "are falling everywhere at once, and orders that kept our mills and mines busy are being cancelled by cable. Every "
        "market leans on every other, and all of them are falling together.\\n\\nThe crash will last some months, and a long "
        f"depression will follow. How soon we recover depends on what we do now, and on what the {GPS} do.",
        '"We have had panics before. This time there is nowhere for the money to run."',
        ["We must retrench.", "Steady the exchanges."]),
    2: ("A Wall of Tariffs",
        "The owners of our largest works have petitioned the government, and the great landowners have joined them. "
        "Foreign goods and cheap foreign grain, they say, are sold in our markets at any price their makers can get, and "
        "our own factories and estates cannot sell at a price that pays their wages. They ask for higher duties on "
        "everything that competes with home industry and home harvests.\\n\\nProtection would shelter our own recovery, "
        "but our trading partners would suffer for it, and the world's recovery with them.",
        '"Every nation builds a wall around its own market, and each wonders why its exports do not recover."',
        ["Protect our industry.", "Keep our markets open."]),
    3: ("Relief Works",
        f"Thousands of men stand idle in {CAP}, and the relief funds are exhausted. The city engineers have a list of works "
        "that could employ them, from drains and roads to embankments and a new market hall, if the treasury will pay for them.",
        '"A man who digs a drain for his daily wage is no pauper, and he knows it."',
        ["Fund the works.", "Charity is a private matter."]),
    4: ("The Banks Under Siege",
        f"Word has spread that the banks of {CAP} lent heavily to firms that are now failing. Since morning depositors have "
        "queued to withdraw their savings, and by evening the banks will have no coin left to pay them. Their directors "
        "ask the government to act.",
        '"A bank is perfectly sound until everyone believes it is not."',
        ["Declare a bank holiday.", "Bail out the banks.", "Let them fail."]),
    5: ("The Currency Question",
        "Falling prices have divided the country. Farmers and small borrowers say money has grown too dear, and that every "
        "debt weighs heavier each year that prices fall. They want more money issued and credit made easy. Bankers and "
        "creditors answer that only sound money will win back the confidence of investors at home and abroad.",
        '"My mortgage is the same as it was five years ago. My wheat fetches half the price."',
        ["Sound money above all.", "Make credit easy."]),
    6: ("March of the Unemployed",
        f"A column of unemployed men has marched into {CAP} behind banners reading 'Work or Bread'. They have camped "
        "before the government offices and ask to present a petition. The police say they can clear the square by nightfall.",
        '"We do not ask for charity. We ask for work."',
        ["Disperse them.", "Hear their petition."]),
    7: ("Calls for Reform",
        "The newspapers ask why the depression has lasted so long, and who grew rich on the speculation that came before "
        "it. Members of the legislature have called for an inquiry into the banks, the exchanges and the conduct of the "
        "government itself.",
        '"The question is no longer whether the system failed, but who will answer for it."',
        ["Commission an inquiry.", "The system is sound."]),
    8: ("The $SPEC_LD_NAME$ Lifts",
        "For the first time in years, orders are rising faster than they are cancelled. Prices have found a floor, the banks "
        "are lending again, and works that stood idle are taking on hands. The depression is over, though few who lived "
        "through it will soon forget it.",
        '"Trade is improving, they say. I shall believe it when my own order book says so."',
        ["Lessons have been learned.", "Back to business."]),
}


EFFECT_LABELS = [("Investment", "state_capitalists_investment_pool_efficiency_mult"),
                 ("Construction", "state_construction_mult"), ("Trade", "state_trade_quantity_mult"),
                 ("[concept_loans] interest rate", "country_loan_interest_rate_mult")]
BAD_UP = {"country_loan_interest_rate_mult"}


def phase_effects(m):
    """The phase modifier's main lines for the journal entry, e.g. Investment -10%, from MODS."""
    lines = MODS[m][1]
    return ", ".join(f"{label} {'#N' if (lines[key] < 0) != (key in BAD_UP) else '#P'} {lines[key]:+.0%}#!"
                     for label, key in EFFECT_LABELS if key in lines)


def span(months):
    n, unit = (months // 12, "year") if months % 12 == 0 else (months, "month")
    return f"#v {n}#! {unit}{'' if n == 1 else 's'}"


def loc():
    gv = lambda name: f"GetGlobalVariable('{name}').GetValue"
    world = market_tab.v("spec_c_world")
    tariff = f"Subtract_CFixedPoint({world}, {market_tab.v('spec_ld_conf')})"
    stages = [f"{'#N' if n < 0 else '#P'} {n:+g}#! in the {PHASES[p]}" for p, n in PRESSURE.items()]
    out = [
        ' concept_spec_long_depression: "Long Depression"',
        ' concept_spec_long_depression_desc: "A crisis of the whole world economy. It '
        "begins when a [concept_great_power] falls into a [concept_spec_financial_panic], then reaches every country "
        "already in a panic and spreads along close ties such as a shared [concept_market], subjects and overlords, investment "
        "rights, heavy trade and foreign ownership.\\n\\n"
        f"It opens with a {PHASES[1]} of {span(CRASH_MONTHS)}, in which credit freezes and [concept_spec_market_confidence] drains away. "
        f"The {PHASES[2]} follows for up to {span(DEPRESSION_MAX)}, slowing investment, construction and trade and turning some pops "
        f"[Concept('concept_radical','$concept_radicals$')]. In the {PHASES[3]}, which lasts {span(RECOVERY_MONTHS)}, $concept_spec_market_confidence$ returns.\\n\\n"
        "A country's choices speed up its own recovery and the world's, and a $concept_great_power$'s count the most.\"",
        ' je_spec_depression: "The $SPEC_LD_NAME$"',
        ' SPEC_LD_LONG: "Long Depression"',
        ' SPEC_LD_GREAT: "Great Depression"',
        f' SPEC_LD_NAME: "[SelectLocalization(GreaterThan_CFixedPoint({gv("spec_ld_count")}, \'(CFixedPoint)1\'), \'SPEC_LD_GREAT\', \'SPEC_LD_LONG\')]"',
        ' je_spec_depression_reason: "Panics on the great exchanges have become a world crisis. Investment and building have '
        "slowed, trade has fallen, and the unemployed grow restless. The [concept_spec_long_depression] ends when the world has "
        f"recovered, or after #v {DEPRESSION_MAX // 12}#! years at the most.\\n\\nOur choices hasten our own recovery and the "
        f"world's, and those of {GPS} count for more. Once our own recovery is complete, [concept_spec_market_confidence] returns here before it "
        'returns elsewhere."',
        f' spec_ld_status_1: "The #n {PHASES[1]}#! ends in #v [{gv("spec_ld_months")}|0]#! months.\\n{phase_effects("spec_ld_crash")}"',
        f' spec_ld_status_2: "The #n {PHASES[2]}#! ends within #v [{gv("spec_ld_months")}|0]#! months.\\n{phase_effects("spec_ld_depression")}"',
        ' spec_ld_world_bar: "World Recovery"',
        ' spec_ld_world_bar_desc: "The world has recovered #v [JournalEntry.GetCurrentBarValue(ScriptedProgressBar.Self)|0]#! of #v 100#!."',
        f' spec_ld_complete_tt: "World Recovery reaches #v 100#!, or {span(DEPRESSION_MAX)} pass"',
        ' spec_ld_own_bar: "Our Recovery"',
        ' spec_ld_own_bar_desc: "We have recovered #v [JournalEntry.GetCurrentBarValue(ScriptedProgressBar.Self)|0]#! of #v 100#!."',
        ' spec_ld_tariff_tt: "Countries tied to us lose [concept_spec_market_confidence]. The bigger our economy is next to theirs, the more they lose."',
        ' SPEC_DRIVER_WORLD: "$SPEC_LD_NAME$"',
        f' SPEC_WORLD_TARIFF: "\\n[{tariff}|+=2] from tariffs raised by countries tied to us"',
        f' SPEC_DRIVER_WORLD_TT: "#header $SPEC_LD_NAME$: [{world}|+=1]#!\\n$TOOLTIP_DELIMITER$\\n'
        f'[{market_tab.v("spec_ld_conf")}|+=1] from the current stage of the slump'
        f'[AddLocalizationIf({market_tab.nonzero(tariff, 0.01)}, \'SPEC_WORLD_TARIFF\')]\\n$TOOLTIP_DELIMITER$\\n#weak Each month the slump moves [concept_spec_market_confidence] by '
        + ", ".join(stages[:-1]) + f" and {stages[-1]}.#!" + '"',
        ' spec_ld_notification_group: "Long Depression"',
    ]
    out += [f' {step_key("own", n)}: "Our recovery {"rises" if n > 0 else "falls"} by #v {abs(n):g}#!"' for n in sorted(OWN_STEPS)]
    out += [f' {step_key("world", n)}: "World recovery {"rises" if n > 0 else "falls"} by #v {abs(n):g}#!"' for n in sorted(WORLD_STEPS)]
    for key, (*_, name, desc) in NOTES.items():
        n = f"notification_{key}"
        out += [f' {n}_name: "{name}"', f' {n}_desc: "{desc}"', f' {n}_tooltip: "#header ${n}_name$#!\\n$TOOLTIP_DELIMITER$\\n${n}_desc$"']
    for eid, (t, d, f, opts) in TEXT.items():
        out += [f' spec_depression.{eid}.t: "{t}"', f' spec_depression.{eid}.d: "{d}"', f' spec_depression.{eid}.f: "{f}"']
        out += [f' spec_depression.{eid}.{chr(97 + i)}: "{o}"' for i, o in enumerate(opts)]
    out += [f' {key}: "{name}"' for key, name in MOD_NAMES.items()]
    out += [' spec_ld_crash_desc: "Credit has frozen across the world as the [concept_spec_long_depression] begins."',
            ' spec_ld_depression_desc: "The [concept_spec_long_depression] weighs on investment, construction and trade."']
    out += [f' {key}: "{name}"' for key, *_, name in IG_MODS + COUNTRY_MODS]
    return "\n".join(out) + "\n"
