"""Speculation story events: smaller events driven by the state of the market, for players only.

A monthly pulse picks at most one with a small chance, never while the mania or panic event is fresh, and at
most one every STORY_GAP days. AI countries get none; they follow generate.py's scripted rules.
build() writes the events, their modifiers, effects and pulse; loc() returns their localization.
"""
STORY_CHANCE = 8         # percent a month that a pulse with a valid event fires one
STORY_DELAY = 12         # days after the pulse, so the event's trigger is checked after the month's update
STORY_GAP = 730          # days after a story event before the pulse can fire another
HUSH = 120               # days after a mania or panic starts with no story events
CRASH_SEEN = -3          # a month's collapse confidence at or below this makes a story
FOREIGN_SEEN = -2        # and so does a foreign panic's hit
REMEMBER = 90            # days either is remembered for
WARN_EXPOSURE = 10       # confidence at risk from current booms for the press to sound the alarm

CAP = "[ROOT.GetCountry.GetCapital.GetCityHubName]"


def at_least(var, n):
    """var >= n, false while var is unset: a bare comparison on an unset variable logs three errors each check."""
    return (f"\t\ttrigger_if = {{\n\t\t\tlimit = {{ has_variable = {var} }}\n\t\t\tvar:{var} >= {n}\n\t\t}}\n"
            "\t\ttrigger_else = {\n\t\t\talways = no\n\t\t}\n")
VAR = "ROOT.GetCountry.MakeScope.Var"
G1, G2 = f"[{VAR}('spec_story_good').GetGoods.GetName]", f"[{VAR}('spec_story_good2').GetGoods.GetName]"
SRC = f"[{VAR}('spec_story_src').GetCountry.GetName]"
GC = f"[{VAR}('spec_story_crashed').GetGoods.GetName]"

# timed interest group modifiers: key, icon, approval, name
IG_MODS = [
    ("spec_story_relief_welcomed", "coins_positive", 2, "Relief for Producers"),
    ("spec_story_public_money", "coins_negative", -1, "Public Money for Speculators"),
    ("spec_story_sound_finance", "lightbulb_positive", 1, "Sound Finance"),
    ("spec_story_promoters_hounded", "documents_negative", -2, "Promoters Hounded"),
    ("spec_story_justice_done", "documents_positive", 2, "Swindlers Prosecuted"),
    ("spec_story_cover_up", "fist_negative", -2, "Swindle Hushed Up"),
    ("spec_story_quiet_kept", "flag_positive", 1, "Discretion Rewarded"),
    ("spec_story_investors_repaid", "coins_positive", 2, "Small Investors Repaid"),
    ("spec_story_depositors_saved", "coins_positive", 2, "Deposits Guaranteed"),
    ("spec_story_depositors_abandoned", "fist_negative", -2, "Depositors Abandoned"),
    ("spec_story_merchants_backed", "coins_positive", 1, "Merchant Houses Backed"),
    ("spec_story_foreign_blamed", "flag_positive", 1, "Foreign Bankers Blamed"),
    ("spec_story_revival_backed", "gear_positive", 2, "New Ventures Encouraged"),
    ("spec_story_lessons_unlearned", "lightbulb_negative", -1, "Lessons Unlearned"),
    ("spec_story_lobby_heard", "flag_positive", 2, "Deputation Heard"),
    ("spec_story_lobby_rebuffed", "flag_negative", -2, "Deputation Rebuffed"),
    ("spec_story_subsidy", "coins_positive", 1, "Credit Subsidy"),
    ("spec_story_trading_curbed", "documents_negative", -1, "Share Dealing Curbed"),
    ("spec_story_stamp_duty", "coins_negative", -2, "Stamp Duty on Shares"),
    ("spec_story_warning_dismissed", "lightbulb_negative", -1, "Warnings Dismissed"),
]
# timed country modifiers: key, icon, modifier line, name; money ones are scaled by vanilla's GDP multipliers
COUNTRY_MODS = [
    ("spec_story_producer_relief", "coins_negative", "country_expenses_add = 1", "Relief for Ruined Producers"),
    ("spec_story_compensation", "coins_negative", "country_expenses_add = 1", "Compensating Small Investors"),
    ("spec_story_deposit_guarantee", "coins_negative", "country_expenses_add = 1", "Deposit Guarantee"),
    ("spec_story_merchant_loans", "coins_negative", "country_expenses_add = 1", "Loans to Merchant Houses"),
    ("spec_story_industry_subsidy", "coins_negative", "country_expenses_add = 1", "Industrial Credit Subsidy"),
    ("spec_story_share_duty", "coins_positive", "country_tax_income_add = 1", "Stamp Duty on Share Transfers"),
    ("spec_story_fraud_trial", "documents_positive", "country_legitimacy_base_add = 5", "Fraud Trial"),
]
CONF_STEPS = set()  # confidence changes used, each gets a tooltip key


def ig(key, mod, days="short_modifier_time"):
    return f"\t\tig:ig_{key} ?= {{\n\t\t\tadd_modifier = {{\n\t\t\t\tname = {mod}\n\t\t\t\tdays = {days}\n\t\t\t}}\n\t\t}}\n"


# supporting the banks: the cost and the interest groups' anger as one plain line each (spec_rescue_cost_tt,
# spec_bank_bailout_tt) instead of the raw add_treasury figure and the modifiers' own tooltips
RESCUE_PAY = ("\t\tcustom_tooltip = {\n\t\t\ttext = spec_rescue_cost_tt\n"
              "\t\t\tadd_treasury = { value = spec_rescue_cost multiply = -1 }\n\t\t}\n")
BAILOUT_IGS = ("\t\tcustom_tooltip = {\n\t\t\ttext = spec_bank_bailout_tt\n"
               + "".join("\t" + line for line in (ig("trade_unions", "spec_bank_bailout") + ig("rural_folk", "spec_bank_bailout")).splitlines(True))
               + "\t\t}\n")
# an event option that runs spec_rescue: spec_rescue's own cost line is hidden inside the effects line, so shown first
RESCUE_OPTION = ("\t\tcustom_tooltip = spec_rescue_cost_tt\n"
                 "\t\tcustom_tooltip = {\n\t\t\ttext = spec_markets.2.b.tt\n\t\t\tspec_rescue = yes\n\t\t}\n"
                 # the interest groups' anger is part of spec_rescue itself, so the tab's button costs the same
                 "\t\tcustom_tooltip = spec_bank_bailout_tt\n")


def country(mod, days, money=None):
    mult = f"\t\t\tmultiplier = money_amount_multiplier_{money}\n" if money else ""
    return f"\t\tadd_modifier = {{\n\t\t\tname = {mod}\n\t\t\tdays = {days}\n{mult}\t\t}}\n"


def conf(n):
    CONF_STEPS.add(n)
    return f"\t\tcustom_tooltip = {{\n\t\t\ttext = {conf_key(n)}\n\t\t\tspec_story_conf = {{ AMOUNT = {n} }}\n\t\t}}\n"


def conf_key(n):
    return f"spec_story_conf_{'up' if n > 0 else 'down'}_{abs(n)}"


def pops(kind, size, who):
    return f"\t\tadd_{kind} = {{ value = {size}_radicals {who} }}\n"  # vanilla sizes loyalists with these too


def option(eid, letter, body, ai, default=False, trigger=""):
    return (f"\toption = {{\n\t\tname = spec_story.{eid}.{letter}\n" + ("\t\tdefault_option = yes\n" if default else "")
            + (f"\t\ttrigger = {{ {trigger} }}\n" if trigger else "") + body
            + f"\t\tai_chance = {{\n\t\t\tbase = {ai}\n\t\t}}\n\t}}\n")


# the picture by the region of the capital, as vanilla's regional videos go; the triggers are exclusive and the last
# one is the fallback, so the order of the blocks cannot matter
REGIONS = ["mideast", "africa", "asia", "latam", "west"]
PICS = {
    1: {"west": "europenorthamerica_rich_and_poor", "latam": "unspecific_factory_closed",
        "mideast": "middleeast_police_breaking_door", "africa": "unspecific_factory_closed", "asia": "asia_poor_people_moving"},
    2: {"west": "unspecific_signed_contract", "mideast": "middleeast_courtroom_upheaval"},
    3: {"west": "unspecific_vandalized_storefront", "africa": "africa_public_protest"},
    4: {"west": "unspecific_steam_ship", "asia": "asia_westerners_arriving"},
    5: {"west": "unspecific_trains", "latam": "southamerica_factory_opening", "mideast": "middleeast_engineer_blueprint",
        "africa": "africa_construction_colony", "asia": "asia_farmers_market"},
    6: {"west": "europenorthamerica_capitalists_meeting", "latam": "southamerica_aristocrats",
        "mideast": "unspecific_politicians_arguing", "africa": "africa_leader_arguing", "asia": "asia_politician_parliament_motion"},
    7: {"west": "unspecific_world_fair", "mideast": "middleeast_middleclass_cafe", "africa": "africa_city_center",
        "asia": "asia_farmers_market"},
    8: {"west": "unspecific_politicians_arguing", "latam": "southamerica_election", "africa": "africa_leader_arguing",
        "asia": "asia_politician_parliament_motion"},
}
# when the goods or country a story names are known; otherwise its text falls back to generic wording
NEED = {1: "has_variable = spec_story_crashed", 2: "has_variable = spec_story_good", 4: "exists = var:spec_story_src",
        7: "has_variable = spec_story_good", 8: "has_variable = spec_story_good has_variable = spec_story_good2"}


def pictures(pics):
    """event_image blocks for each region; regions without their own picture use the west one."""
    return "".join(f'\tevent_image = {{\n\t\ttrigger = {{ spec_pic_{r} = yes }}\n\t\tvideo = "{pics.get(r, pics["west"])}"\n\t}}\n'
                   for r in REGIONS)


def field(key, need):
    """A title, desc or flavor key, with its generic version when the data it names may be missing."""
    if not need:
        return f"{key}\n"
    return (f"{{\n\t\tfirst_valid = {{\n\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = {key}\n\t\t\t\ttrigger = {{ {need} }}\n\t\t\t}}\n"
            f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = {key}_generic\n\t\t\t\ttrigger = {{ always = yes }}\n\t\t\t}}\n\t\t}}\n\t}}\n")


def event(eid, pics, icon, trigger, options, immediate="", cooldown="normal_modifier_time"):
    t, d, f = (field(f"spec_story.{eid}.{x}", None if isinstance(text, str) else NEED[eid])
               for x, text in zip("tdf", TEXT[eid]))
    return f"""
spec_story.{eid} = {{
	type = country_event
	placement = root
	title = {t}	desc = {d}	flavor = {f}	duration = 3
{pictures(pics)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/{icon}.dds"
	cooldown = {{ days = {cooldown} }}

	trigger = {{
		spec_story_quiet = yes
{trigger}	}}

	immediate = {{
		set_variable = {{ name = spec_story_cd value = yes days = {STORY_GAP} }}
{immediate}	}}

{"".join(options)}}}
"""


def events(k):
    hot = k["HOT_HYPE"]
    no_panic = "\t\tNOT = { has_variable = spec_panic }\n"
    def copy(to, src):  # a goods variable for the text, or none so the text goes generic
        return (f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = {src} }}\n\t\t\tset_variable = {{ name = {to} value = var:{src} }}\n\t\t}}\n"
                f"\t\telse = {{\n\t\t\tremove_variable = {to}\n\t\t}}\n")
    top = copy("spec_story_good", "spec_top1")
    out = [
        # 1: a boom collapsed without a panic
        event(1, PICS[1], "event_trade",
              "\t\thas_variable = spec_story_crash\n\t\thas_variable = spec_story_crashed\n" + no_panic, [
                  option(1, "a", country("spec_story_producer_relief", "short_modifier_time", "small") + conf(6)
                         + ig("industrialists", "spec_story_relief_welcomed") + ig("trade_unions", "spec_story_public_money"), 25),
                  option(1, "b", conf(-4) + pops("radicals", "small", "pop_type = capitalists")
                         + ig("intelligentsia", "spec_story_sound_finance"), 50, default=True),
                  option(1, "c", conf(-2) + ig("industrialists", "spec_story_promoters_hounded")
                         + pops("loyalists", "small", "strata = lower"), 25),
              ], immediate="\t\tremove_variable = spec_story_crash\n", cooldown="short_modifier_time"),
        # 2: a promoter's swindle comes to light while greed runs high
        event(2, PICS[2], "event_scales",
              f"\t\tvar:spec_conf >= 60\n{at_least('spec_top1_v', hot)}" + no_panic, [
                  option(2, "a", conf(-8) + country("spec_story_fraud_trial", "short_modifier_time")
                         + ig("petty_bourgeoisie", "spec_story_justice_done") + ig("industrialists", "spec_story_promoters_hounded"),
                         50, default=True),
                  option(2, "b", conf(-2) + pops("radicals", "small", "strata = middle")
                         + ig("petty_bourgeoisie", "spec_story_cover_up") + ig("industrialists", "spec_story_quiet_kept"), 30),
                  option(2, "c", country("spec_story_compensation", "very_short_modifier_time", "small") + conf(-4)
                         + pops("loyalists", "small", "strata = middle") + ig("petty_bourgeoisie", "spec_story_investors_repaid"), 20),
              ], immediate=top),
        # 3: a bank fails during a panic
        event(3, PICS[3], "event_protest",
              f"\t\tNOT = {{ has_variable = spec_rescued }}\n{at_least('spec_panic', 3)}", [
                  option(3, "a", country("spec_story_deposit_guarantee", "very_short_modifier_time", "medium") + conf(5)
                         + pops("loyalists", "small", "strata = middle") + ig("petty_bourgeoisie", "spec_story_depositors_saved"), 30),
                  option(3, "b", conf(-5) + pops("radicals", "small", "strata = middle")
                         + ig("petty_bourgeoisie", "spec_story_depositors_abandoned"), 50, default=True),
                  option(3, "c", RESCUE_OPTION, 20, trigger="spec_can_rescue = yes"),
              ]),
        # 4: a panic abroad has reached our markets
        event(4, PICS[4], "event_map",
              "\t\thas_variable = spec_story_foreign\n\t\texists = var:spec_story_src\n" + no_panic, [
                  option(4, "a", country("spec_story_merchant_loans", "very_short_modifier_time", "small") + conf(6)
                         + ig("industrialists", "spec_story_merchants_backed"), 30),
                  option(4, "b", conf(-3), 50, default=True),
                  option(4, "c", "\t\tspec_story_blame_foreign = yes\n", 20,
                         trigger="exists = var:spec_story_src"),
              ], immediate="\t\tremove_variable = spec_story_foreign\n"),
        # 5: the panic is over and money comes back
        event(5, PICS[5], "event_industry",
              f"{no_panic}{at_least('spec_panic_cooldown', k['PANIC_COOLDOWN'] - 3)}"
              "\t\tvar:spec_conf >= 40\n", [
                  option(5, "a", conf(8) + ig("industrialists", "spec_story_revival_backed")
                         + ig("intelligentsia", "spec_story_lessons_unlearned"), 50),
                  option(5, "b", conf(3) + ig("intelligentsia", "spec_prudent_counsel"), 50, default=True),
              ]),
        # 6: the Industrialists want the banks lending again
        event(6, PICS[6], "event_portrait",
              f"\t\tspec_stance_value = -1\n\t\tNOT = {{ has_variable = spec_stance_cooldown }}\n\t\texists = ig:ig_industrialists\n" + no_panic, [
                  option(6, "a", "\t\tcustom_tooltip = {\n\t\t\ttext = spec_story.6.a.tt\n\t\t\tspec_stance_to_normal = yes\n\t\t}\n"
                         + ig("industrialists", "spec_story_lobby_heard"), 40, trigger="spec_can_stance_normal = yes"),
                  option(6, "b", ig("industrialists", "spec_story_lobby_rebuffed") + ig("intelligentsia", "spec_prudent_counsel"),
                         40, default=True),
                  option(6, "c", country("spec_story_industry_subsidy", "short_modifier_time", "small")
                         + ig("industrialists", "spec_story_subsidy"), 20),
              ]),
        # 7: the middle classes are dealing in shares
        event(7, PICS[7], "event_trade",
              f"\t\thas_variable = spec_mania\n\t\tvar:spec_conf >= {k['MANIA']}\n" + no_panic, [
                  option(7, "a", conf(3) + pops("loyalists", "small", "strata = middle")
                         + ig("petty_bourgeoisie", "spec_boom_riding"), 50, default=True),
                  option(7, "b", conf(-6) + ig("petty_bourgeoisie", "spec_story_trading_curbed")
                         + ig("intelligentsia", "spec_prudent_counsel"), 30),
                  option(7, "c", country("spec_story_share_duty", "very_short_modifier_time", "small") + conf(-4)
                         + ig("petty_bourgeoisie", "spec_story_stamp_duty"), 20),
              ], immediate=top),
        # 8: someone says in print that it is a bubble, before it becomes a mania
        event(8, PICS[8], "event_newspaper",
              f"\t\tNOT = {{ has_variable = spec_mania }}\n\t\tvar:spec_conf >= 60\n{at_least('spec_top1_v', hot)}"
              f"{at_least('spec_exposure', WARN_EXPOSURE)}" + no_panic, [
                  option(8, "a", conf(-6) + ig("intelligentsia", "spec_prudent_counsel") + ig("industrialists", "spec_boom_warning"), 30),
                  option(8, "b", conf(2) + ig("industrialists", "spec_boom_riding")
                         + ig("intelligentsia", "spec_story_warning_dismissed"), 50, default=True),
              ], immediate=top + copy("spec_story_good2", "spec_top2")),
    ]
    return "namespace = spec_story\n" + "".join(out)


def test_events():
    """Debug builds only: console `event spec_markets.<n> <tag>` sets up the state a story needs and fires it."""
    # the goods the stories name, in case the monthly ranking has not run for this country yet
    goods = "".join(f"if = {{ limit = {{ NOT = {{ has_variable = spec_{k} }} }} set_variable = {{ name = spec_{k} value = g:{g} }} }} "
                    for k, g in (("top1", "coal"), ("top2", "iron"), ("top3", "grain")))
    unhush = "remove_variable = spec_story_hush " + goods
    tests = [
        (95, 1, "set_variable = { name = spec_story_crashed value = var:spec_top1 } set_variable = { name = spec_story_crash value = yes days = 90 }"),
        (96, 2, "set_variable = { name = spec_conf value = 70 } set_variable = { name = spec_top1_v value = 4 }"),
        (97, 3, "if = { limit = { NOT = { has_variable = spec_panic } } spec_start_panic = yes } set_variable = spec_story_panic_seen"),
        (98, 4, "random_country = { limit = { NOT = { this = root } gdp > 0 } save_scope_as = spec_test_src } "
                "set_variable = { name = spec_story_src value = scope:spec_test_src } set_variable = { name = spec_story_foreign value = yes days = 90 }"),
        (99, 5, "set_variable = { name = spec_panic_cooldown value = 12 } set_variable = { name = spec_conf value = 45 }"),
        (100, 6, "spec_stance_to_tight = yes remove_variable = spec_stance_cooldown"),
        (101, 7, "set_variable = { name = spec_conf value = 85 } set_variable = spec_mania set_variable = spec_story_mania_seen"),
        (102, 8, "set_variable = { name = spec_conf value = 70 } remove_variable = spec_mania set_variable = { name = spec_top1_v value = 4 } "
                 "set_variable = { name = spec_exposure value = 12 }"),
    ]
    return "\nnamespace = spec_markets\n" + "".join(f"""
spec_markets.{n} = {{
	type = country_event
	hidden = yes
	immediate = {{ {unhush}{setup} trigger_event = {{ id = spec_story.{e} popup = yes }} }}
}}
""" for n, e, setup in tests)


def effects():
    return f"""# Recheck at response time: the country can disappear while the foreign-panic story is open.
# Keep the whole response together, so an absent target gives no confidence or approval for blaming it.
spec_story_blame_foreign = {{
	if = {{
		limit = {{ exists = var:spec_story_src }}
		change_relations = {{
			country = var:spec_story_src
			value = -15
		}}
{conf(2)}{ig("petty_bourgeoisie", "spec_story_foreign_blamed")}	}}
}}

# confidence up or down by AMOUNT within 0 to 100, shown in the tab as this month's government change
spec_story_conf = {{
	# An event can remain open while a law change closes the market economy. Its eventual option must not
	# recreate confidence (or read cleared driver variables) after spec_shut_down.
	if = {{
		limit = {{
			has_variable = spec_conf
			spec_law_mult > 0
		}}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_c_caution }} }}
			set_variable = {{ name = spec_c_caution value = 0 }}
		}}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_c_total }} }}
			set_variable = {{ name = spec_c_total value = 0 }}
		}}
		set_variable = {{ name = spec_story_was value = var:spec_conf }}
		set_variable = {{ name = spec_conf value = {{ value = var:spec_conf add = $AMOUNT$ min = 0 max = 100 }} }}
		change_variable = {{ name = spec_c_caution add = {{ value = var:spec_conf subtract = var:spec_story_was }} }}
		change_variable = {{ name = spec_c_total add = {{ value = var:spec_conf subtract = var:spec_story_was }} }}
		remove_variable = spec_story_was
		spec_pick_driver = yes
		spec_update_band = yes
	}}
}}

# monthly, players only: what the stories need to know, whichever order the mod's pulses run in
spec_story_track = {{
	# a mania or panic new since last month keeps the stories away for a while
	if = {{
		limit = {{
			has_variable = spec_mania
			NOT = {{ has_variable = spec_story_mania_seen }}
		}}
		set_variable = spec_story_mania_seen
		set_variable = {{ name = spec_story_hush value = yes days = {HUSH} }}
	}}
	else_if = {{
		limit = {{
			NOT = {{ has_variable = spec_mania }}
			has_variable = spec_story_mania_seen
		}}
		remove_variable = spec_story_mania_seen
	}}
	if = {{
		limit = {{
			has_variable = spec_panic
			NOT = {{ has_variable = spec_story_panic_seen }}
		}}
		set_variable = spec_story_panic_seen
		set_variable = {{ name = spec_story_hush value = yes days = {HUSH} }}
	}}
	else_if = {{
		limit = {{
			NOT = {{ has_variable = spec_panic }}
			has_variable = spec_story_panic_seen
		}}
		remove_variable = spec_story_panic_seen
	}}
	# a collapsed boom and a panic abroad that reached us, remembered for a season
	if = {{
		limit = {{
			has_variable = spec_crashed
			var:spec_c_crash <= {CRASH_SEEN}
		}}
		set_variable = {{ name = spec_story_crashed value = var:spec_crashed }}
		set_variable = {{ name = spec_story_crash value = yes days = {REMEMBER} }}
	}}
	if = {{
		limit = {{
			has_variable = spec_foreign_src
			var:spec_c_foreign <= {FOREIGN_SEEN}
		}}
		set_variable = {{ name = spec_story_src value = var:spec_foreign_src }}
		set_variable = {{ name = spec_story_foreign value = yes days = {REMEMBER} }}
	}}
}}
"""


def triggers():
    return """# the region of the capital, for the events' pictures; exactly one of these is true
spec_pic_mideast = {
	capital ?= {
		OR = {
			is_in_geographic_region = geographic_region_middle_east
			is_in_geographic_region = geographic_region_north_africa_egypt
		}
	}
}
spec_pic_africa = {
	NOT = { spec_pic_mideast = yes }
	capital ?= { is_in_geographic_region = geographic_region_africa }
}
spec_pic_asia = {
	NOT = { spec_pic_mideast = yes }
	capital ?= {
		is_in_geographic_region = geographic_region_asia
		NOT = { is_in_geographic_region = geographic_region_australasia }
	}
}
spec_pic_latam = {
	capital ?= { is_in_geographic_region = geographic_region_latin_america }
}
# Europe, North America, Australasia and anything else
spec_pic_west = {
	NOR = {
		spec_pic_mideast = yes
		spec_pic_africa = yes
		spec_pic_asia = yes
		spec_pic_latam = yes
	}
}

# a story may fire: a player, the market system running, and no mania or panic event fresh
spec_story_quiet = {
	is_player = yes
	has_variable = spec_conf
	spec_law_mult > 0
	NOT = { has_variable = spec_story_hush }
	NOT = {
		AND = {
			has_variable = spec_mania
			NOT = { has_variable = spec_story_mania_seen }
		}
	}
	NOT = {
		AND = {
			has_variable = spec_panic
			NOT = { has_variable = spec_story_panic_seen }
		}
	}
}
"""


def on_actions():
    picks = "".join(f"\t\t100 = spec_story.{i}\n" for i in range(1, 9))
    return f"""on_monthly_pulse_country = {{
	on_actions = {{ spec_story_pulse }}
}}

spec_story_pulse = {{
	trigger = {{
		is_player = yes
		has_variable = spec_conf
	}}
	effect = {{
		spec_story_track = yes
	}}
	on_actions = {{ spec_story_pick }}
}}

spec_story_pick = {{
	trigger = {{
		NOT = {{ has_variable = spec_story_cd }}
	}}
	random_events = {{
		chance_to_happen = {STORY_CHANCE}
		delay = {{ days = {STORY_DELAY} }}
{picks}	}}
}}
"""


def modifiers():
    out = ["# timed interest group modifiers from the story events\n"]
    out += [f"{key} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_{icon}.dds\n\tinterest_group_approval_add = {n}\n}}\n\n"
            for key, icon, n, _ in IG_MODS]
    out.append("# timed country modifiers from the story events\n")
    out += [f"{key} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_{icon}.dds\n\t{line}\n}}\n\n"
            for key, icon, line, _ in COUNTRY_MODS]
    return "".join(out)


def build(write, k, log=False):
    write("events/spec_markets_story_events.txt", events(k) + (test_events() if log else ""))
    write("common/static_modifiers/spec_story_modifiers.txt", modifiers())
    write("common/scripted_effects/spec_story_effects.txt", effects())
    write("common/scripted_triggers/spec_story_triggers.txt", triggers())
    write("common/on_actions/spec_story_on_actions.txt", on_actions())


# a field is its text, or (text, generic) when it names goods or a country that may be missing: NEED says when
TEXT = {
    1: (("The [GC] Market Breaks", "A Market Breaks"),
        (f"The rush into {GC} is over. Prices that climbed for a year have fallen in a month, and the companies floated at "
         "the height of the craze cannot meet their bills. Merchants who bought at any price are left with warehouses they "
         "cannot empty, and the banks that lent against their stock are counting the cost.",
         "The rush into the season's favorite goods is over. Prices that climbed for a year have fallen in a month, and the "
         "companies floated at the height of the craze cannot meet their bills. Merchants who bought at any price are left "
         "with warehouses they cannot empty, and the banks that lent against their stock are counting the cost."),
        (f'"I have been in the {GC} trade for thirty years, and I never saw men so eager to buy, nor so desperate to sell, '
         'as I have seen this twelvemonth."',
         '"I have been in this trade for thirty years, and I never saw men so eager to buy, nor so desperate to sell, '
         'as I have seen this twelvemonth."'),
        ["Extend relief to the ruined producers.", "Let the weakest houses fail.", "Inquire into the promoters."]),
    2: ("A Swindle Exposed",
        (f"The directors of the {CAP} {G1} Company have fled the country, and its books show that the handsome dividends "
         "of the past two years were paid out of new subscriptions. Thousands of clerks, widows and shopkeepers held its "
         f"shares. Every newspaper in {CAP} now asks how many other prospectuses were written by the same hand.",
         f"The directors of a celebrated {CAP} share company have fled the country, and its books show that the handsome "
         "dividends of the past two years were paid out of new subscriptions. Thousands of clerks, widows and shopkeepers "
         f"held its shares. Every newspaper in {CAP} now asks how many other prospectuses were written by the same hand."),
        (f"#bold Wanted on a Charge of Fraud#!\\nThe managing director of the {CAP} {G1} Company, aged about fifty, well "
         "dressed and plausible in manner. Last seen at the docks.",
         f"#bold Wanted on a Charge of Fraud#!\\nThe managing director of a {CAP} share company, aged about fifty, well "
         "dressed and plausible in manner. Last seen at the docks."),
        ["Prosecute the directors.", "Keep the matter quiet.", "Compensate the small investors."]),
    3: ("A Run on the Banks",
        f"Depositors besieged one of the oldest banks in {CAP} this morning, and by noon its doors were shut. Its notes are "
        "refused all over the city, and the firms that kept their accounts there cannot pay their hands this week. The queues "
        "outside every other bank grow longer by the hour.",
        '"My father kept his savings in that bank, and his father before him. They told us it was as safe as the Treasury."',
        ["Guarantee its deposits.", "It must stand or fall alone.", "We must lend to the banks."]),
    4: ((f"Panic in {SRC}", "Panic Abroad"),
        (f"News has reached {CAP} of a [concept_spec_financial_panic] in {SRC}. Its banks are calling in their loans abroad, and our firms "
         f"that sold to {SRC} or borrowed there are suddenly short of money. Every merchant on the exchange wants to know "
         "whether the trouble will spread.",
         f"News has reached {CAP} of a financial panic abroad. Foreign banks are calling in their loans, and our firms that "
         "sold or borrowed overseas are suddenly short of money. Every merchant on the exchange wants to know whether the "
         "trouble will spread."),
        (f'"When {SRC} sneezes, our exchange takes to its bed."', '"When our neighbors sneeze, our exchange takes to its bed."'),
        ["Lend to our merchant houses.", "Their troubles are not ours.", "Blame the reckless foreign bankers."]),
    5: ("Confidence Returns",
        "The worst of the panic is over. The firms that survived are taking on hands again, the banks have begun to lend to "
        "sound customers, and a few bold investors are buying shares at a fraction of last year's prices. No one expects a "
        f"quick return to the old excesses, but {CAP} is open for business once more.",
        '"The men who sold everything in the spring are buying it back in the autumn, and at a better price than they sold it."',
        ["Encourage new ventures.", "Lending must be sound this time."]),
    6: ("The Manufacturers' Deputation",
        "A deputation of manufacturers and merchants has called on the government. Their new works stand half finished for "
        "want of credit, they say, while their rivals abroad borrow freely and take their markets. They ask that the banks be "
        "allowed to lend again.",
        '"Your caution, sir, has saved us from a crash by making certain there is nothing left to crash."',
        ["Ease credit.", "Credit stays tight.", "Offer them a subsidy instead."]),
    7: ("A Craze for Shares",
        (f"Clerks, shopkeepers and schoolmasters crowd the coffee houses of {CAP} to trade shares in companies they have "
         f"never seen. Shares in {G1} ventures change hands several times a day, most of them bought with borrowed money. It "
         "is said that servants are pawning their Sunday clothes for a part in the next flotation.",
         f"Clerks, shopkeepers and schoolmasters crowd the coffee houses of {CAP} to trade shares in companies they have "
         "never seen. Shares in the newest ventures change hands several times a day, most of them bought with borrowed "
         "money. It is said that servants are pawning their Sunday clothes for a part in the next flotation."),
        (f'"My barber gave me a tip on {G1} shares this morning. I took it, and gave him one in return: sell."',
         '"My barber gave me a tip on shares this morning. I took it, and gave him one in return: sell."'),
        ["Let the people share in the wealth.", "Forbid dealing on borrowed money.", "Levy a stamp duty on share transfers."]),
    8: ("Warnings of a Bubble",
        (f"A respected economist has written to the leading newspaper of {CAP} that the rise in {G1} and {G2} cannot last, "
         "and that the banks have lent against prices no sober man would pay. The brokers call it the croaking of an old "
         "woman. Yet the letter is being read aloud in every club and counting house in the city.",
         f"A respected economist has written to the leading newspaper of {CAP} that the rise in the most favored goods of "
         "the day cannot last, and that the banks have lent against prices no sober man would pay. The brokers call it the "
         "croaking of an old woman. Yet the letter is being read aloud in every club and counting house in the city."),
        '"A price is only what the last buyer was willing to pay. I ask my readers to consider how many buyers remain."',
        ["The warning is timely.", "Alarmist nonsense."]),
}


def loc(k):
    out = []
    for eid, (*fields, opts) in TEXT.items():
        for field, text in zip("tdf", fields):
            text = (text,) if isinstance(text, str) else text
            out += [f' spec_story.{eid}.{field}{suffix}: "{t.replace("[GC]", GC)}"' for suffix, t in zip(("", "_generic"), text)]
        out += [f' spec_story.{eid}.{chr(97 + i)}: "{o}"' for i, o in enumerate(opts)]
    out.append(f' spec_story.6.a.tt: "[concept_spec_credit_policy] becomes #v Normal#! and is locked for #v {k["STANCE_COOLDOWN"]}#! months"')
    out += [f' {conf_key(n)}: "[concept_spec_market_confidence] {"rises" if n > 0 else "falls"} by #v {abs(n)}#!"'
            for n in sorted(CONF_STEPS)]
    out += [f' {key}: "{name}"' for key, *_, name in IG_MODS + COUNTRY_MODS]
    return "\n".join(out) + "\n"
