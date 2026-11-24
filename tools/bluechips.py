"""Blue chips, beta.12 (design_companies.md section 3): what the status does, its moments, and Company of the Year.

companies.BLUE_UPDATE keeps the status itself (BLUE_PROSPER+ for BLUE_MONTHS months; BLUE_LOSE months below loses it)
and counts the country's blue chips (var:spec_bc_n). This file adds:
- steadiness: each blue chip, up to CAP, cuts the confidence lost to collapsing booms and foreign panics by SHELTER
  (spec_bc_shelter, in generate's spec_crash_scale and spec_catch_panic)
- a dividend: DIVIDEND Exchange trust a year for each, up to CAP
- a fall: losing the status costs FALL_TRUST trust and FALL_CONF confidence
- two moments, as country events (the AI picks by ai_chance):
  1 a new blue chip: ring the bell (trust) or issue new shares (pool money; the company turns fragile, losing the
    status after one month below the mark, for FRAGILE_YEARS)
  2 a blue chip slips below the mark: prop it up (a share of GDP from the treasury; its low months stop counting for
    PROP_MONTHS) or let the market decide
- Company of the Year: once a year the world's most prosperous blue chip; its country gains COTY_TRUST trust and a
  year's prestige (spec_coty), and gets event 3 if a player.
"""
import tuning

# 2026-11-22: every blue chip counts the same, up to CAP (was 5 in full and the next 5, then 3, at half). Vanilla
# allows 7 companies at most (5 techs, Technocracy, a power bloc principle), 8 with ours
CAP = tuning.get("BC_CAP", 8)                  # blue chips that count toward their effects
SHELTER = tuning.get("BC_SHELTER", 0.04)       # each: confidence lost to collapses and foreign panics
DIVIDEND = tuning.get("BC_DIVIDEND", 0.5)      # each: Exchange trust a year
FALL_TRUST = tuning.get("BC_FALL_TRUST", 2)    # trust lost when a blue chip loses the status
FALL_CONF = tuning.get("BC_FALL_CONF", 3)      # confidence lost then
BELL_TRUST = tuning.get("BC_BELL_TRUST", 2)    # event 1, ring the bell
SHARES_MONTHS = tuning.get("BC_SHARES", 2)     # event 1, issue new shares: months of investment pool income
FRAGILE_YEARS = tuning.get("BC_FRAGILE", 5)
PROP_GDP = tuning.get("BC_PROP_GDP", 0.003)    # event 2, prop it up: share of GDP
PROP_MONTHS = tuning.get("BC_PROP_MONTHS", 12)
COTY_TRUST = tuning.get("BC_COTY_TRUST", 3)
COTY_PRESTIGE = tuning.get("BC_COTY_PRESTIGE", 0.05)
# beta.12 second pass (the user: still lacklustre): the Blue Chip Index, a country modifier per blue chip counted, and
# each one counted moves every Exchange contest's bar PULL our way (rivals.spec_rv_rope); a Bear Raid that lands
# rattles one of the target's blue chips: fragile for RATTLE_DAYS (rivals.spec_rv_raided)
# until 1.2 also -1% loan interest each, and 0.006: with the Pockets pursuit about 35% more capital than vanilla's 0.30
INDEX = tuning.get("BC_INDEX", [["state_capitalists_investment_pool_contribution_add", 0.004]])
PULL = tuning.get("BC_PULL", 0.03)
PULL_MONTH = PULL * 50 / 60  # in a contest's points (0 to 100) a month, over its 60 (rivals.STEP)
RATTLE_DAYS = tuning.get("BC_RATTLE_DAYS", 365)

CO = "[SCOPE.sCompany('spec_bc_co').GetName]"
EXCH = "has_variable = spec_centre_trust"


# as centres._gain and _lose (not imported: companies builds BLUE_UPDATE from this file while centres imports companies)
CALM = 120  # centres.CALM, trust's ceiling; checked in __main__


LOG = "--log" in __import__("sys").argv  # generate.py --log: a SPECTR line for every trust change, any country


def log_trust(effect, why, t):
    """effect; in a --log build also a SPECTR line with its cause and size when it moved trust (tools/tuner/windows.py)."""
    if not LOG:
        return effect
    return (f"{t}set_local_variable = {{ name = spec_log_tb value = var:spec_centre_trust }}\n" + effect
            + f"{t}set_variable = {{ name = spec_log_td value = {{ value = var:spec_centre_trust subtract = local_var:spec_log_tb }} }}\n"
            f"{t}if = {{ limit = {{ NOT = {{ var:spec_log_td = 0 }} }} debug_log = \"SPECTR tag=[THIS.GetCountry.GetTagName] "
            f"date=[TimeKeeper.GetCurrentDate.GetString] why={why} d=[THIS.Var('spec_log_td').GetValue] "
            f"trust=[THIS.Var('spec_centre_trust').GetValue]\" }}\n")


def record_trust(effect, cause, t, why=None):
    """effect, then the player's trust change it made added to spec_trust_<cause>_pending (centres._trust_review's
    monthly breakdown). Here, not in centres, as this file imports nothing centres needs. why: the --log line's cause."""
    tracking = "is_player = yes has_variable = spec_trust_review"
    pending = f"spec_trust_{cause}_pending"
    return (f"{t}if = {{ limit = {{ {tracking} }} set_local_variable = {{ name = spec_before_trust value = var:spec_centre_trust }} }}\n"
            + log_trust(effect, why or cause, t)
            + f"{t}if = {{ limit = {{ {tracking} }} change_variable = {{ name = {pending} "
              f"add = {{ value = var:spec_centre_trust subtract = local_var:spec_before_trust }} }} }}\n")


def _raw_gain(by, t):
    return f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust add = {by} max = {CALM} }} }}\n"


def _raw_lose(by, t):
    return (f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
            f"subtract = {{ value = {by} multiply = spec_exch_loss }} min = 0 }} }}\n")


def _gain(by, t):
    return record_trust(_raw_gain(by, t), "chips", t)


def _lose(by, t):
    return record_trust(_raw_lose(by, t), "chips", t)


def after_update(t="\t\t"):
    """In spec_update_companies, after BLUE_UPDATE's loop (country scope, its local flags set): the count, the fall's
    cost, and the events."""
    return f"""{t}set_local_variable = {{ name = spec_bc_was value = spec_bc_counted }}
{t}set_variable = {{ name = spec_bc_n value = local_var:spec_bc_cnt }}
{t}# the Blue Chip Index, re-applied when the count moves (a modifier's multiplier is fixed)
{t}if = {{
{t}	limit = {{
{t}		OR = {{
{t}			NOT = {{ local_var:spec_bc_was = spec_bc_counted }}
{t}			AND = {{
{t}				spec_bc_counted > 0
{t}				NOT = {{ has_modifier = spec_bc_index }}
{t}			}}
{t}		}}
{t}	}}
{t}	if = {{
{t}		limit = {{ has_modifier = spec_bc_index }}
{t}		remove_modifier = spec_bc_index
{t}	}}
{t}	if = {{
{t}		limit = {{ spec_bc_counted > 0 }}
{t}		add_modifier = {{ name = spec_bc_index multiplier = spec_bc_counted }}
{t}	}}
{t}}}
{t}if = {{
{t}	limit = {{ has_local_variable = spec_bc_fell }}
{t}	if = {{
{t}		limit = {{ {EXCH} }}
{_lose(f"{{ value = local_var:spec_bc_fell multiply = {FALL_TRUST} }}", t + chr(9) * 2)}{t}	}}
{t}	spec_story_conf = {{ AMOUNT = -{FALL_CONF} }}
{t}}}
{t}if = {{
{t}	limit = {{ OR = {{ has_local_variable = spec_bc_gained has_local_variable = spec_bc_wobbled }} }}
{t}	every_company = {{
{t}		limit = {{ OR = {{ has_variable = spec_bc_new has_variable = spec_bc_wobble }} }}
{t}		save_scope_as = spec_bc_co
{t}		if = {{
{t}			limit = {{ has_variable = spec_bc_wobble }}
{t}			owner = {{ trigger_event = {{ id = spec_bluechip.2 popup = yes }} }}
{t}		}}
{t}		else = {{ owner = {{ trigger_event = {{ id = spec_bluechip.1 }} }} }}
{t}	}}
{t}}}
"""


def counted(n, t):
    """Script math for the blue chips counted, from the held count n: each in full, up to CAP."""
    return f"{t}add = {{ value = {n} max = {CAP} }}\n"


def values():
    return f"""# blue chips (bluechips.py): the share of collapse and foreign panic losses kept, by the blue chips counted
spec_bc_shelter = {{
	value = 1
	subtract = {{ value = spec_bc_counted multiply = {SHELTER:g} }}
}}

# Monthly updates at the owner's current rate, from the company's saved progress.
spec_bc_updates_left = {{
	value = {__import__("companies").BLUE_MONTHS}
	if = {{ limit = {{ has_variable = spec_bc_months }} subtract = var:spec_bc_months }}
	divide = owner.spec_nx_blue
	min = 0
	ceiling = yes
}}

# the blue chips counted toward their effects: each in full, up to CAP
spec_bc_counted = {{
	value = 0
	if = {{
		limit = {{ has_variable = spec_bc_n }}
{counted('var:spec_bc_n', chr(9) * 2)}	}}
}}

# Prop It Up's cost
spec_bc_prop_cost = {{
	value = gdp
	multiply = {PROP_GDP:g}
}}

spec_bc_prop_cost_neg = {{
	value = spec_bc_prop_cost
	multiply = -1
}}

spec_bc_shares = {{
	value = spec_pool_month
	multiply = {SHARES_MONTHS}
}}
"""


def pass_(t="\t"):
    """In centres' monthly ranking pass (global): once a year the dividend, then Company of the Year."""
    return f"""{t}# blue chips (bluechips.py): once a year their dividend in trust, then Company of the Year
{t}if = {{
{t}	limit = {{ NOT = {{ has_global_variable = spec_coty_year }} }}
{t}	set_global_variable = {{ name = spec_coty_year days = 365 }}
{t}	every_country = {{
{t}		limit = {{ {EXCH} has_variable = spec_bc_n var:spec_bc_n > 0 }}
{_gain(f"{{ value = spec_bc_counted multiply = {DIVIDEND:g} }}", t + chr(9) * 2)}{t}	}}
{t}	set_global_variable = {{ name = spec_coty_p value = 0 }}
{t}	every_country = {{
{t}		limit = {{ has_variable = spec_bc_n var:spec_bc_n > 0 }}
{t}		every_company = {{
{t}			limit = {{ has_variable = spec_blue_chip }}
{t}			remove_variable = spec_coty
{t}			if = {{
{t}				limit = {{ prosperity > global_var:spec_coty_p }}
{t}				set_global_variable = {{ name = spec_coty_p value = prosperity }}
{t}				save_scope_as = spec_coty_co
{t}			}}
{t}		}}
{t}	}}
{t}	scope:spec_coty_co ?= {{
{t}		set_variable = {{ name = spec_coty days = 365 }}
{t}		owner = {{
{t}			add_modifier = {{ name = spec_coty days = 365 }}
{t}			if = {{
{t}				limit = {{ {EXCH} }}
{_gain(COTY_TRUST, t + chr(9) * 4)}{t}			}}
{t}			if = {{
{t}				limit = {{ is_player = yes }}
{t}				trigger_event = {{ id = spec_bluechip.3 popup = yes }}
{t}			}}
{t}		}}
{t}	}}
{t}	remove_global_variable = spec_coty_p
{t}}}
"""


def _event(n, pic, flag, options, icon="event_industry"):
    pics = __import__("stories").pictures(pic)
    company_scope = "spec_coty_co" if n == 3 else "spec_bc_co"
    consume = "" if n == 3 else f" remove_variable = {flag}"
    return f"""
spec_bluechip.{n} = {{
	type = country_event
	placement = root
	title = spec_bluechip.{n}.t
	desc = spec_bluechip.{n}.d
	flavor = spec_bluechip.{n}.f
	duration = 3
{pics}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/{icon}.dds"

	trigger = {{
		exists = scope:{company_scope}
		scope:{company_scope} ?= {{ owner = root has_variable = {flag} }}
	}}

	immediate = {{
		scope:{company_scope} = {{ save_scope_as = spec_bc_co{consume} }}
	}}
{"".join(options)}}}
"""


def _option(n, letter, body, ai, trigger="", default=False):
    return (f"\n\toption = {{\n\t\tname = spec_bluechip.{n}.{letter}\n" + ("\t\tdefault_option = yes\n" if default else "")
            + (f"\t\ttrigger = {{ {trigger} }}\n" if trigger else "") + body
            + f"\t\tai_chance = {{\n\t\t\tbase = {ai}\n\t\t}}\n\t}}\n")


def timed_status(name, days):
    return f"set_variable = {{ name = {name} value = {{ value = game_date add = {days} }} days = {days} }}"


def events():
    bell = (f"\t\tcustom_tooltip = spec_bluechip.1.a.tt\n\t\thidden_effect = {{\n\t\t\tif = {{\n\t\t\t\tlimit = {{ {EXCH} }}\n"
            f"{_gain(BELL_TRUST, chr(9) * 4)}\t\t\t}}\n\t\t}}\n")
    shares = ("\t\tcustom_tooltip = spec_bluechip.1.b.tt\n\t\thidden_effect = {\n\t\t\tadd_investment_pool = spec_bc_shares\n"
              f"\t\t\tscope:spec_bc_co = {{ {timed_status('spec_bc_fragile', FRAGILE_YEARS * 365)} }}\n\t\t}}\n")
    prop = ("\t\tcustom_tooltip = spec_bluechip.2.a.tt\n\t\thidden_effect = {\n\t\t\tadd_treasury = spec_bc_prop_cost_neg\n"
            f"\t\t\tscope:spec_bc_co = {{\n\t\t\t\t{timed_status('spec_bc_propped', PROP_MONTHS * 30)}\n"
            "\t\t\t\tremove_variable = spec_bc_low\n\t\t\t}\n\t\t}\n")
    ride = "\t\tcustom_tooltip = spec_bluechip.2.b.tt\n"
    proud = "\t\tcustom_tooltip = spec_bluechip.3.a.tt\n"
    return ("namespace = spec_bluechip\n"
            # 1: one of our companies has become a blue chip
            + _event(1, {"west": "unspecific_signed_contract", "asia": "asia_westerners_arriving"}, "spec_bc_new", [
                _option(1, "a", bell, 60, default=True),
                _option(1, "b", shares, 40),
            ])
            # 2: a blue chip has slipped below the mark
            + _event(2, {"west": "europenorthamerica_capitalists_meeting", "latam": "southamerica_aristocrats",
                         "mideast": "unspecific_politicians_arguing", "africa": "africa_leader_arguing",
                         "asia": "asia_politician_parliament_motion"}, "spec_bc_wobble", [
                _option(2, "a", prop, 50, trigger="gold_reserves >= spec_bc_prop_cost"),
                _option(2, "b", ride, 50, default=True),
            ], icon="event_scales")
            # 3: ours is Company of the Year (players only; the award itself is in pass_)
            + _event(3, {"west": "unspecific_world_fair", "mideast": "middleeast_middleclass_cafe", "africa": "africa_city_center",
                         "asia": "asia_farmers_market"}, "spec_coty", [_option(3, "a", proud, 1, default=True)]))


MODIFIERS = f"""spec_coty = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_prestige_mult = {COTY_PRESTIGE:g}
}}

spec_bc_index = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
{"".join(f"	{k} = {v:g}{chr(10)}" for k, v in INDEX)}}}
"""


def build(write):
    write("common/script_values/spec_bluechip_values.txt", values())
    write("events/spec_bluechip_events.txt", events())
    write("common/static_modifiers/spec_bluechip_modifiers.txt", MODIFIERS)


def loc():
    pc = lambda x: f"{x:.0%}"
    bc = "[concept_spec_blue_chip]"
    trust = "[concept_spec_exchange] trust"
    return (
        ' spec_coty: "Company of the Year"\n'
        f' spec_coty_desc: "The world\'s most prosperous {bc} is ours this year"\n'
        ' spec_bc_index: "Blue Chip Index"\n'
        f' spec_bc_index_desc: "Our {bc}s pull savings into the market. Each one makes it stronger, up to {CAP}."\n'
        ' spec_bluechip.1.t: "A New Blue Chip"\n'
        f' spec_bluechip.1.d: "After a year of steady profits, {CO} is now counted among the blue chips. Its shares are '
        'sought by every bank and widow in the land, and the brokers ask whether it will stay content with its standing or '
        'ask the market for more."\n'
        ' spec_bluechip.1.f: "Safe as the Bank, they say."\n'
        ' spec_bluechip.1.a: "Ring the bell for them"\n'
        f' spec_bluechip.1.a.tt: "We gain #P +{BELL_TRUST / 1.2:.1f}#! {trust}"\n'
        ' spec_bluechip.1.b: "Let them issue new shares"\n'
        f' spec_bluechip.1.b.tt: "Our [concept_investment_pool]: #P +[ROOT.GetCountry.MakeScope.ScriptValue(\'spec_bc_shares\')|D]#! @money!\\n'
        f'{CO} turns fragile for #v {FRAGILE_YEARS}#! years, so one month below #v {__import__("companies").BLUE_PROSPER:g}#! '
        '[concept_prosperity] means it is no longer a blue chip"\n'
        ' spec_bluechip.2.t: "A Blue Chip Slips"\n'
        f' spec_bluechip.2.d: "{CO} has fallen below the mark of a blue chip. If its profits do not recover within '
        f'{__import__("companies").BLUE_LOSE} months, the market will strike it from the list, and our Exchange will feel it."\n'
        ' spec_bluechip.2.f: "A house that stood for a generation can fall in a season."\n'
        ' spec_bluechip.2.a: "Prop it up"\n'
        f' spec_bluechip.2.a.tt: "Costs #N [ROOT.GetCountry.MakeScope.ScriptValue(\'spec_bc_prop_cost\')|D]#! @money!\\n'
        f'{CO} keeps its status for #v {PROP_MONTHS}#! months, whatever its profits"\n'
        ' spec_bluechip.2.b: "Let the market decide"\n'
        f' spec_bluechip.2.b.tt: "If it stays below the mark for #v {__import__("companies").BLUE_LOSE}#! months:\\n'
        f'We lose #N {FALL_TRUST / 1.2:.1f}#! {trust} and #N {FALL_CONF}#! [concept_spec_market_confidence]"\n'
        ' spec_bluechip.3.t: "Company of the Year"\n'
        f' spec_bluechip.3.d: "The financial press of every capital agrees that {CO} is the most prosperous company in the '
        'world this year. Our Exchange basks in its glory."\n'
        ' spec_bluechip.3.f: "Every clerk in the City wants a share of it."\n'
        ' spec_bluechip.3.a: "A proud day"\n'
        f' spec_bluechip.3.a.tt: "We gain #P +{COTY_TRUST / 1.2:.1f}#! {trust}, and $spec_coty$ gives #P +{pc(COTY_PRESTIGE)}#! [concept_prestige] for a year"\n'
    )


# what a blue chip does, for the header tooltip and the concept (company_section, concepts)
def effect_lines(val, each=False):
    """One line per effect, vanilla style. val(per_one, fmt) gives the figure: one blue chip's, or our total's; each
    adds one blue chip's figure after it, faint."""
    idx = dict(INDEX)
    # 2026-11-22: modifier lines, the figure first (no "Label: value"); trust in points of 100, as its bar shows
    rows = [("less [concept_spec_market_confidence] lost when booms end and in [Concept('concept_spec_foreign_panic','$concept_spec_foreign_panics$')]", "", SHELTER * 100, "0", "%"),
            ("[concept_spec_exchange] trust a year", "+", DIVIDEND * 100 / 120, "1", ""),
            ("a month in our [concept_spec_exchange] contests", "+", PULL_MONTH, "2", ""),
            ("Capitalists' [concept_investment_pool] contribution", "+", idx["state_capitalists_investment_pool_contribution_add"] * 100, "1", "%")]
    return "\\n".join(f"#P {sign}{val(x, f)}{unit}#! {name}" + (f" #grey ({sign}{x:.{f}f}{unit} each)#!" if each else "")
                      for name, sign, x, f, unit in rows)


def risk_text():
    import companies  # not at the top: companies imports this file
    return (f"We lose one after #v {companies.BLUE_LOSE}#! months in a row below #v {companies.BLUE_PROSPER:g}#! [concept_prosperity]. "
            f"Losing it costs #N -{FALL_TRUST * 100 / 120:.1f}#! [concept_spec_exchange] trust and #N -{FALL_CONF}#! "
            f"[concept_spec_market_confidence].\\n"
            f"A Bear Raid that hits us makes one #N Fragile#! for a year, so a single month below "
            f"#v {companies.BLUE_PROSPER:g}#! [concept_prosperity] is enough to lose it.\\n\\n"
            f"If ours is the world's most prosperous company, it becomes Company of the Year: we gain #P +{COTY_TRUST * 100 / 120:.1f}#! "
            f"[concept_spec_exchange] trust, and #P +{COTY_PRESTIGE:.0%}#! [concept_prestige] for a year.")



if __name__ == "__main__":
    e = events()
    assert e.count("spec_bluechip.") >= 3 and e.count("option = {") == 5, e.count("option = {")
    assert e.count("{") == e.count("}") and pass_().count("{") == pass_().count("}") and values().count("{") == values().count("}")
    assert after_update().count("{") == after_update().count("}")
    assert "remove_variable = spec_coty }" not in e  # event 3 leaves the award's mark in place
    import centres
    assert centres.CALM == CALM and _raw_gain("2", "") == centres._gain("2", "") and _raw_lose("2", "") == centres._lose("2", "")
    print("ok")
