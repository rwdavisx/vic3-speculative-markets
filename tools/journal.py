"""The Financial Markets journal entry (JOURNAL_DESIGN.md): a permanent entry for players that follows the market
through its stages, shows the bubble's heat (Speculative Excess) and the reforms made (Sound Finance), and holds the
choices the Speculation tab does not: Convert the National Debt, Relief Works, Suspend the Bank Act and the Commission
of Inquiry, whose report enacts one of the Banking Reforms.

Stage (spec_stage): 6 Long Depression, 5 Panic, 4 Aftermath (the 12 months after a panic), 3 Mania, 2 Buoyant,
1 Steady, 0 Wary. The reforms are variables, kept when the economic system shuts the mod off:
var:spec_note 1 Currency School or 2 Free Banking, spec_llr, spec_company_law. Their multipliers (spec_reform_*) are
read by generate.py's credit, boom, risk, heat, panic length and rescue values. AI countries reach the same choices by
rule (MONTHLY_AI); the reform event weighs their options by credit temperament.

generate.py calls build() and loc(k), uses entry(stances) for the journal entry, puts MONTHLY in spec_monthly for
everyone and MONTHLY_AI in its AI block, and BARS in its bar update.
"""
import investor_sentiment as sent
import calc
import cycle
import economy
import goods_panel
import icons
import leverage
import market_tab as mt
import monetary
import stories
import tuning

# the map mode's colours, by stage (spec_stage); stripes mark a country a foreign panic has just reached
MAP_COLORS = {"ld": "rgb{ 70 45 95 }", "panic": "rgb{ 170 30 35 }", "aftermath": "rgb{ 150 95 85 }", "mania": "rgb{ 235 185 40 }",
              "buoyant": "rgb{ 60 150 110 }", "steady": "rgb{ 150 150 135 }", "wary": "rgb{ 95 125 165 }", "caught": "rgb{ 45 20 25 }"}
OWNER = "SCOPE.sCountry('spec_map_owner').MakeScope"
MAP_STAGES = {6: "Long Depression", 5: "Panic", 4: "Aftermath", 3: "Mania", 2: "Buoyant", 1: "Steady", 0: "Wary"}

CONVERT_DEBT = 0.2          # scaled debt (debt / credit limit) needed to convert
CONVERT_RATE = -0.1         # loan interest while converted, and while the debt stays at CONVERT_DEBT (journal.MONTHLY)
CONVERT_YEARS, CONVERT_COOLDOWN_YEARS, CONVERT_CONF = 5, 10, 5
CONVERT_FROM = 60           # Market Confidence needed to convert
RELIEF_MONTHS = 12
SUSPEND_MONTHS, SUSPEND_CONF, SUSPEND_LEGIT, SUSPEND_YEARS = 2, 15, -10, 2
HAZARD_YEARS, HAZARD_HEAT = 10, 1.5   # after a suspension, investors count on the next one (was 1.25)
INQUIRY_CALM = 120          # months without a panic before an inquiry can sit outside an aftermath
INQUIRY_MONTHS, INQUIRY_AUTHORITY = 6, -0.1
# heat whose pop takes all the confidence a pop can find, generate.BURST_BELOW / BURST_PER_HEAT (Historical;
# Heightened volatility and a Railway Exchange get there sooner). Was 200, where the old -40 cap began
EXCESS_MAX = 300
REFORMS = {
    "currency": {"credit": 0.75, "heat": 0.75, "panic_len": 1.25},
    "free": {"credit": 1.25, "boom": 1.1, "risk": 1.1},
    "llr": {"rescue": 0.5, "rescue_months": -1},
    "company": {"risk": 0.7},
}
SOUND_PRESTIGE = 10  # Sound Finance was also -5% loan interest until 1.2 (centres.WORLD_FX)
SHELVE_CONF = 3  # Market Confidence when the inquiry is shelved
# the AI's journal rules (MONTHLY_AI), percent a month once it can, and its weights in the inquiry's report (spec_reform.1's
# ai_chance): Currency School and Free Banking each get REFORM_AI_TEMPER more from a Cautious or a Bold temperament
AI_INQUIRY_CHANCE = tuning.get("AI_INQUIRY_CHANCE", 10)
AI_CONVERT_CHANCE = tuning.get("AI_CONVERT_CHANCE", 10)
AI_RELIEF_CHANCE = tuning.get("AI_RELIEF_CHANCE", 20)
REFORM_AI_CURRENCY = tuning.get("REFORM_AI_CURRENCY", 10)
REFORM_AI_FREE = tuning.get("REFORM_AI_FREE", 10)
REFORM_AI_LLR = tuning.get("REFORM_AI_LLR", 25)
REFORM_AI_COMPANY = tuning.get("REFORM_AI_COMPANY", 15)
REFORM_AI_SHELVE = tuning.get("REFORM_AI_SHELVE", 5)
REFORM_AI_TEMPER = tuning.get("REFORM_AI_TEMPER", 30)
REFORM_AI = {"currency": REFORM_AI_CURRENCY, "free": REFORM_AI_FREE, "llr": REFORM_AI_LLR, "company": REFORM_AI_COMPANY, "shelve": REFORM_AI_SHELVE}
LOG = "--log" in __import__("sys").argv  # generate.py --log: a SPECJ line for each of the AI's journal actions


def _log(act, t, extra=""):
    """--log: SPECJ tag= date= act= [opt=] temper= for an AI's journal action (tools/tuner)."""
    if not LOG:
        return ""
    return (f"{t}if = {{ limit = {{ is_ai = yes }} debug_log = \"SPECJ tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] "
            f"act={act}{extra} temper=[THIS.Var('spec_temper').GetValue]\" }}\n")
# timed interest group modifiers: key, icon, approval, name
IG_MODIFIERS = [
    ("spec_rentiers_cut", "modifier_coins_negative", -2, "Rentier Income Cut"),  # no apostrophe: vanilla quotes modifier names in ADD_MODIFIER tooltips
    ("spec_relief_thanks", "modifier_flag_positive", 2, "Relief Works"),
    ("spec_dear_money", "modifier_coins_negative", -2, "Dear Money"),
    ("spec_free_issue", "modifier_coins_positive", 2, "Free Banking"),
    ("spec_disclosure_burden", "modifier_documents_negative", -1, "Disclosure Rules"),
    ("spec_disclosure_welcomed", "modifier_documents_positive", 1, "Disclosure Rules"),
    ("spec_report_shelved", "modifier_coins_positive", 2, "Business as Usual"),  # the inquiry shelved (spec_reform.1.e)
    ("spec_report_buried", "modifier_documents_negative", -2, "Inquiry Shelved"),
]
STAGES = [(6, "ld"), (5, "panic"), (4, "aftermath"), (3, "mania"), (2, "buoyant"), (1, "steady"), (0, "wary")]
INQUIRY_PICS = {"west": "unspecific_politicians_arguing", "asia": "asia_politician_parliament_motion"}
SOUND_PICS = {"west": "europenorthamerica_capitalists_meeting", "mideast": "middleeast_upperclass_party"}
C = "JournalEntry.GetCountry.MakeScope"


def mult(name, parts, base=1):
    """A script value: base, set or multiplied by each institution that changes it."""
    body = "".join(f"\tif = {{\n\t\tlimit = {{ {cond} }}\n\t\tmultiply = {n:g}\n\t}}\n" for cond, n in parts)
    return f"{name} = {{\n\tvalue = {base}\n{body}}}\n"


HAS = {"currency": "var:spec_note ?= 1", "free": "var:spec_note ?= 2", "llr": "has_variable = spec_llr",
       "company": "has_variable = spec_company_law"}


def reform_parts(key):
    return [(HAS[r], fx[key]) for r, fx in REFORMS.items() if key in fx] + monetary.parts(key)  # and the Monetary Standard


# Speculative Excess a cause a line (calc.py, excess_calc): what grows it, what cools it, the burst. generate's monthly update adds
# spec_xs_grow or spec_xs_cool, so the forecast is the update's own figure. ponytail: read at this month's confidence,
# the update at next month's, so it is off by the confidence change until Market Confidence is forecast too
XS_GROWING = "has_variable = spec_conf var:spec_conf >= spec_heat_from has_technology_researched = stock_exchange"
XS_LABELS = {"currency": "Currency School"}  # the institutions' names, as the lines say them
TIGHT = "[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]"


def conf_jump(driver, change, tabs=1):
    """Confidence moved at once by a one-off (a rescue, the mania event's cooling): the driver and this month's total
    take the change as it came out after the 0 to 100 limits, adding to any earlier jump this month rather than
    replacing it, so the tab's rows still add up to the total."""
    t = "\t" * tabs
    return (f"{t}set_local_variable = {{ name = spec_jump_was value = var:spec_conf }}\n"
            f"{t}set_variable = {{ name = spec_conf value = {{ value = var:spec_conf {change} }} }}\n"
            f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = {driver} }} }}\n{t}\tset_variable = {{ name = {driver} value = 0 }}\n{t}}}\n"
            f"{t}set_local_variable = {{ name = spec_jump value = {{ value = var:spec_conf subtract = local_var:spec_jump_was }} }}\n"
            f"{t}change_variable = {{ name = {driver} add = local_var:spec_jump }}\n"
            f"{t}change_variable = {{ name = spec_c_total add = local_var:spec_jump }}\n")


def excess_calc(k):
    """(script values, [(script value, label key, label)]) of the Excess forecast; spec_xs_next is the total."""
    parts = ([(HAS[r], fx["heat"], XS_LABELS[r]) for r, fx in REFORMS.items() if "heat" in fx]
             + [(monetary.has(law), fx["heat"], f"[GetLawType('law_spec_{law}').GetName]") for law, fx in monetary.FX.items() if "heat" in fx]
             + [("has_variable = spec_hazard", HAZARD_HEAT, "$spec_act_suspended$")])
    assert [(c, n) for c, n, _ in parts] == reform_parts("heat") + [("has_variable = spec_hazard", HAZARD_HEAT)]  # spec_reform_heat's
    # counted from the threshold, so it starts at 0 (was confidence - 70 everywhere: a jump to +5 at 75 on Historical)
    base = f"\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {XS_GROWING} }}\n\t\tvalue = var:spec_conf\n\t\tsubtract = spec_heat_from\n\t}}\n"
    grow, names = calc.chain("spec_xs_grow", base, [(c, n) for c, n, _ in parts])
    cooling = (f"has_variable = spec_heat has_variable = spec_conf var:spec_conf >= {k['BURST_BELOW']} "
               f"NOT = {{ AND = {{ {XS_GROWING} }} }}")
    one = lambda name, cond, value: (f"{name} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {cond} }}\n\t\tvalue = var:spec_heat\n"
                                     f"\t\tmultiply = {value:.4g}\n\t}}\n}}\n")
    script = (grow + one("spec_xs_cool_0", cooling, k["HEAT_COOL"] - 1)
              + one("spec_xs_cool_1", f"{cooling} spec_stance_value < 0", k["HEAT_COOL_TIGHT"] - k["HEAT_COOL"])
              + "spec_xs_cool = {\n\tvalue = spec_xs_cool_0\n\tadd = spec_xs_cool_1\n}\n"
              + one("spec_xs_pop", f"has_variable = spec_heat has_variable = spec_conf var:spec_conf < {k['BURST_BELOW']}", -1)
              + "spec_xs_next = {\n\tvalue = spec_xs_grow\n\tadd = spec_xs_cool\n\tadd = spec_xs_pop\n}\n"
              # the base shown as two lines, so a Mania's part reads apart: the same total, display only
              + f"spec_xs_mania = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {XS_GROWING} var:spec_conf > {k['MANIA']} }}\n"
              f"\t\tvalue = var:spec_conf\n\t\tsubtract = {k['MANIA']}\n\t}}\n}}\n"
              "spec_xs_boom = {\n\tvalue = spec_xs_grow_0\n\tsubtract = spec_xs_mania\n}\n")
    labels = ["[concept_spec_market_confidence] above #v [GetPlayer.MakeScope.ScriptValue('spec_heat_from')|0]#!"] + [l for *_, l in parts]
    rows = ([("spec_xs_boom", "SPEC_XS_P0", labels[0]),
             ("spec_xs_mania", "SPEC_XS_PMANIA", f"a Mania, [concept_spec_market_confidence] above #v {k['MANIA']}#!")]
            + [(n, f"SPEC_XS_P{i}", l) for i, (n, l) in enumerate(zip(names, labels)) if i]
            + [("spec_xs_cool_0", "SPEC_XS_PCOOL", f"cooling, #v {1 - k['HEAT_COOL']:.0%}#! a month"),
               ("spec_xs_cool_1", "SPEC_XS_PTIGHT", f"a {TIGHT} credit policy, #v {k['HEAT_COOL'] - k['HEAT_COOL_TIGHT']:.0%}#! more"),
               ("spec_xs_pop", "SPEC_XS_PPOP", f"bursting, [concept_spec_market_confidence] below #v {k['BURST_BELOW']}#!")])
    return script, rows


def values(k):
    stage ="".join(f"\telse_if = {{\n\t\tlimit = {{ {cond} }}\n\t\tvalue = {n}\n\t}}\n" for n, cond in [
        (5, "has_variable = spec_panic"), (4, "has_variable = spec_panic_cooldown"),
        (3, f"has_variable = spec_conf var:spec_conf >= {k['MANIA']}"),
        # Journal/map labels follow the confidence bands, not the lending threshold.
        (2, f"has_variable = spec_conf var:spec_conf >= {mt.TIERS[3][1]}"), (0, "has_variable = spec_conf var:spec_conf < 40")])
    flag = lambda name, trigger: f"{name} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {trigger} }}\n\t\tvalue = 1\n\t}}\n}}\n"
    count = "".join(f"\tif = {{\n\t\tlimit = {{ {c} }}\n\t\tadd = 1\n\t}}\n"
                    for c in ("has_variable = spec_note", HAS["llr"], HAS["company"]))
    return ("# the journal entry's stage: 6 Long Depression, 5 Panic, 4 Aftermath, 3 Mania, 2 Buoyant, 1 Steady, 0 Wary\n"
            "spec_stage = {\n\tvalue = 1\n\tif = {\n\t\tlimit = { has_variable = spec_ld var:spec_ld < 3 }\n\t\tvalue = 6\n\t}\n"
            f"{stage}}}\n\n"
            "# the Sound Finance institutions' multipliers, read by generate.py\n"
            + mult("spec_reform_credit", reform_parts("credit"))
            + mult("spec_reform_heat", reform_parts("heat") + [("has_variable = spec_hazard", HAZARD_HEAT)])
            + mult("spec_reform_boom", reform_parts("boom"))
            + mult("spec_reform_risk", reform_parts("risk"))
            + mult("spec_reform_panic_len", reform_parts("panic_len"))
            + mult("spec_reform_rescue", reform_parts("rescue"))
            + f"spec_reform_rescue_months = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {HAS['llr']} }}\n"
              f"\t\tvalue = {REFORMS['llr']['rescue_months']}\n\t}}\n}}\n"
            + f"spec_reform_count = {{\n\tvalue = 0\n{count}}}\n"
            # display only: what the bubble would cost if it burst now, and the months until a calm inquiry
            + "spec_burst_now = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_heat }\n\t\tvalue = var:spec_heat\n"
              f"\t\tmultiply = spec_burst_per_heat\n\t\tmultiply = spec_nx_burst\n\t\tmax = {k['BURST_BELOW']}\n\t}}\n}}\n"
            # and the Bad Debts it would leave at the least, bursting just under BURST_BELOW (leverage.ON_BURST)
            + ("" if not leverage.ON else
               "spec_xs_bad_now = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_heat }\n\t\tvalue = var:spec_heat\n"
               f"\t\tmultiply = spec_burst_per_heat\n\t\tmultiply = spec_nx_burst\n\t\tsubtract = {k['BURST_BELOW']}\n\t\tmultiply = spec_nx_bad\n\t\tmin = 0\n\t}}\n}}\n")
              + "spec_heat_shown = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_heat }\n\t\tvalue = var:spec_heat\n\t}\n}\n"
            + excess_calc(k)[0]
            + f"spec_calm_left = {{\n\tvalue = {INQUIRY_CALM}\n\tif = {{\n\t\tlimit = {{ has_variable = spec_calm }}\n"
              "\t\tsubtract = var:spec_calm\n\t}\n\tmin = 0\n}\n"
            + flag("spec_reform_open_v", "spec_reform_open = yes")
            + flag("spec_currency_v", HAS["currency"]) + flag("spec_free_v", HAS["free"])
            + flag("spec_llr_v", HAS["llr"]) + flag("spec_company_v", HAS["company"])
            + flag("spec_has_stock_exchange", "has_technology_researched = stock_exchange")
            # where confidence would land if the Risks row's risks struck now, for the Panic Risk alert:
            # market_tab.RISK_FLOOR in script, each risk counted only while its chip shows (market_tab.RISK_PARTS)
            + "spec_after_risks = {\n\tvalue = 100\n\tif = {\n\t\tlimit = { has_variable = spec_conf }\n\t\tvalue = var:spec_conf\n"
              "\t\tif = {\n\t\t\tlimit = { has_variable = spec_risk_top var:spec_risk_top >= 1 }\n"
              "\t\t\tsubtract = { value = var:spec_risk_top max = var:spec_conf }\n\t\t}\n"
              "\t\tif = {\n\t\t\tlimit = { has_variable = spec_risk_src_hit var:spec_risk_src_hit >= 2 }\n\t\t\tsubtract = var:spec_risk_src_hit\n\t\t}\n"
              "\t\tif = {\n\t\t\tlimit = { has_variable = spec_war_risk var:spec_war_risk > 0 }\n\t\t\tsubtract = var:spec_war_risk\n\t\t}\n"
              f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = spec_default_risk }}\n\t\t\tsubtract = {economy.DEFAULT_COST}\n\t\t}}\n"
              "\t\tif = {\n\t\t\tlimit = { spec_burst_now > 0.05 }\n\t\t\tsubtract = spec_burst_now\n\t\t}\n"
              "\t\tmin = 0\n\t}\n}\n")


TRIGGERS = f"""# a Sound Finance institution its technology allows and the country has not yet made
spec_reform_open = {{
	OR = {{
		AND = {{
			has_technology_researched = banking
			NOT = {{ has_variable = spec_note }}
		}}
		AND = {{
			has_technology_researched = central_banking
			NOT = {{ {HAS['llr']} }}
		}}
		AND = {{
			has_technology_researched = joint_stock_companies
			NOT = {{ {HAS['company']} }}
		}}
	}}
}}

spec_can_inquire = {{
	custom_tooltip = {{
		text = spec_inquiry_reform_tt
		spec_reform_open = yes
	}}
	custom_tooltip = {{
		text = spec_inquiry_no_panic_tt
		NOT = {{ has_variable = spec_panic }}
	}}
	custom_tooltip = {{
		text = spec_inquiry_when_tt
		OR = {{
			AND = {{
				has_variable = spec_panic_cooldown
				NOT = {{ has_variable = spec_inquired }}
			}}
			AND = {{
				has_variable = spec_calm
				var:spec_calm >= {INQUIRY_CALM}
			}}
		}}
	}}
}}

spec_can_convert = {{
	custom_tooltip = {{
		text = spec_convert_conf_tt
		NOT = {{ has_variable = spec_panic }}
		has_variable = spec_conf
		var:spec_conf >= {CONVERT_FROM}
	}}
	custom_tooltip = {{
		text = spec_convert_debt_tt
		scaled_debt >= {CONVERT_DEBT}
	}}
	custom_tooltip = {{
		text = spec_convert_cd_tt
		NOT = {{ has_variable = spec_converted }}
	}}
}}

spec_in_slump = {{
	OR = {{
		has_variable = spec_panic
		AND = {{
			has_variable = spec_ld
			var:spec_ld < 3
		}}
	}}
}}

spec_can_relief = {{
	custom_tooltip = {{
		text = spec_relief_when_tt
		spec_in_slump = yes
	}}
	custom_tooltip = {{
		text = spec_relief_cd_tt
		NOT = {{ has_variable = spec_relief }}
	}}
	in_default = no
}}

spec_can_suspend = {{
	custom_tooltip = {{
		text = spec_suspend_panic_tt
		has_variable = spec_panic
	}}
	custom_tooltip = {{
		text = spec_suspend_note_tt
		{HAS['currency']}
	}}
	custom_tooltip = {{
		text = spec_rescued_tt
		NOT = {{ has_variable = spec_rescued }}
	}}
}}
"""


def ig(key, mod, time):
    return f"\tig:ig_{key} ?= {{\n\t\tadd_modifier = {{\n\t\t\tname = {mod}\n\t\t\t{time}\n\t\t}}\n\t}}\n"


def effects():
    return f"""spec_do_convert = {{
	add_modifier = {{
		name = spec_debt_converted
		years = {CONVERT_YEARS}
	}}
{ig('landowners', 'spec_rentiers_cut', f'years = {CONVERT_YEARS}')}	custom_tooltip = {{
		text = spec_convert_conf_cost_tt
		spec_cool_conf = {{ AMOUNT = {CONVERT_CONF} }}
		set_variable = {{ name = spec_converted years = {CONVERT_COOLDOWN_YEARS} }}
	}}
}}

spec_do_relief = {{
	add_modifier = {{
		name = spec_relief_works
		days = {RELIEF_MONTHS * 31}
	}}
	add_modifier = {{
		name = spec_relief_costs
		days = {RELIEF_MONTHS * 31}
		multiplier = money_amount_multiplier_medium
	}}
{ig('trade_unions', 'spec_relief_thanks', f'days = {RELIEF_MONTHS * 31}')}	hidden_effect = {{
		set_variable = {{ name = spec_relief months = {RELIEF_MONTHS} }}
	}}
}}

# a Treasury letter lets the bank lend beyond the Act's limit: the panic ends soon, at no cost to the treasury, but
# investors learn that the government will step in, and the next bubble grows faster
spec_do_suspend = {{
	add_modifier = {{
		name = spec_act_suspended
		years = {SUSPEND_YEARS}
	}}
	custom_tooltip = {{
		text = spec_suspend_tt
		set_variable = {{ name = spec_panic value = {{ value = var:spec_panic max = {SUSPEND_MONTHS} }} }}
{conf_jump("spec_c_rescue", f"add = {SUSPEND_CONF} max = 100", 2)}		set_variable = spec_rescued
{cycle.rescued(2)}		set_variable = {{ name = spec_hazard years = {HAZARD_YEARS} }}
		spec_pick_driver = yes
		spec_update_band = yes
	}}
}}

spec_do_inquiry = {{
	add_modifier = {{
		name = spec_inquiry_sitting
		days = {INQUIRY_MONTHS * 31}
	}}
	hidden_effect = {{
		set_variable = spec_inquired
		set_variable = {{ name = spec_calm value = 0 }}
	}}
	trigger_event = {{ id = spec_reform.1 popup = yes }}
}}

# after an institution is made: the count for the bar, and Sound Finance once all three stand
spec_reform_done = {{
	set_variable = {{ name = spec_reforms value = spec_reform_count }}
	je:je_spec_markets ?= {{
		set_bar_progress = {{ name = spec_finance_bar value = root.var:spec_reforms }}
	}}
	if = {{
		limit = {{
			spec_reform_count >= 3
			NOT = {{ has_variable = spec_sound }}
		}}
		set_variable = spec_sound
		trigger_event = {{ id = spec_reform.2 popup = yes }}
	}}
}}
"""


def modifiers():
    icon = lambda n: f"\ticon = gfx/interface/icons/timed_modifier_icons/{n}.dds\n"
    timed = "".join(f"{key} = {{\n{icon(i)}\tinterest_group_approval_add = {n}\n}}\n\n" for key, i, n, _ in IG_MODIFIERS)
    return f"""spec_debt_converted = {{
{icon('modifier_coins_positive')}	country_loan_interest_rate_mult = {CONVERT_RATE:g}
}}

# public works in the slump, as vanilla's work camps; their cost is the expense modifier below
spec_relief_works = {{
{icon('modifier_flag_positive')}	state_welfare_payments_add = 0.15
	state_construction_mult = 0.1
	state_radicals_from_political_movements_mult = -0.25
}}

spec_relief_costs = {{
{icon('modifier_coins_negative')}	country_expenses_add = 1
}}

spec_act_suspended = {{
{icon('modifier_documents_negative')}	country_legitimacy_base_add = {SUSPEND_LEGIT}
}}

spec_inquiry_sitting = {{
{icon('modifier_documents_negative')}	country_authority_mult = {INQUIRY_AUTHORITY:g}
}}

spec_sound_finance = {{
{icon('modifier_statue_positive')}	country_prestige_add = {SOUND_PRESTIGE}
}}

{timed}"""


def button(key, visible, possible, effect, selected=None):
    sel = f"\tselected = {{ root = {{ {selected} }} }}\n" if selected else ""
    return f"""{key} = {{
	name = "{key}"
	desc = "{key}_desc"
	possible = {{ root = {{ {possible} }} }}
{sel}	effect = {{ root = {{ {effect} }} }}
	ai_chance = {{
		value = 0
	}}
}}
"""


# the journal's responses: button key, a short name,
# visible, possible, effect, selected
RESPONSES = [
    ("spec_suspend_act", "suspend", f"has_variable = spec_panic {HAS['currency']}", "spec_can_suspend = yes", "spec_do_suspend = yes", None),
    ("spec_relief_works_button", "relief", "spec_in_slump = yes", "spec_can_relief = yes", "spec_do_relief = yes", "has_variable = spec_relief"),
    ("spec_convert_debt", "convert", "scaled_debt > 0", "spec_can_convert = yes", "spec_do_convert = yes", None),
    ("spec_inquiry", "inquiry", "spec_reform_open = yes", "spec_can_inquire = yes", "spec_do_inquiry = yes", None),
]
BUTTONS = [r[0] for r in RESPONSES]


def buttons():
    return "\n".join(button(key, visible, possible, effect, selected) for key, _, visible, possible, effect, selected in RESPONSES)


def conf_progress(drivers):
    """The confidence bar's tooltip: this month's change by driver, as Uneasy Raj itemizes its bars,
    skipping any the tooltip would show as 0.0 (it cuts to one decimal). The bar's
    periodic progress adds these before the journal entry's pulse; the pulse then sets the bar to var:spec_conf, so
    they only describe the month."""
    return "".join(f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = {var} OR = {{ var:{var} >= 0.1 var:{var} <= -0.1 }} }}\n\t\t\tadd = {{\n\t\t\t\tdesc = \"SPEC_DRIVER_{key.upper()}\"\n"
                   f"\t\t\t\tvalue = var:{var}\n\t\t\t}}\n\t\t}}\n" for key, var in drivers)


def bars(k):
    return f"""spec_excess_bar = {{
	name = "spec_excess_bar"
	desc = "spec_excess_bar_desc"
	start_value = 0
	min_value = 0
	max_value = {EXCESS_MAX}
	default_bad = yes
	# next month's change a cause a line, for the tooltip (excess); the journal entry's pulse sets the bar to var:spec_heat
	monthly_progress = {{
{calc.progress([(n, key) for n, key, _ in excess_calc(k)[1]])}	}}
}}

spec_finance_bar = {{
	name = "spec_finance_bar"
	desc = "spec_finance_bar_desc"
	start_value = 0
	min_value = 0
	max_value = 3
	default_green = yes
}}
"""


GLIDE = mt.GLIDE  # weekly steps the shown confidence takes to reach each month's figure (market_tab.SHOWN)
GLIDE_VARS = ["spec_conf_shown", "spec_conf_aim", "spec_conf_step"]
# a new month's figure sets the step; a panic or a Mania shows at once, as do the first weeks
GLIDE_EFFECT = f"""			root = {{
				if = {{
					limit = {{ has_variable = spec_conf }}
					if = {{
						limit = {{ OR = {{ NOT = {{ has_variable = spec_conf_shown }} has_variable = spec_panic var:spec_conf >= {mt.TIERS[-1][1]} }} }}
						set_variable = {{ name = spec_conf_shown value = var:spec_conf }}
						set_variable = {{ name = spec_conf_aim value = var:spec_conf }}
						set_variable = {{ name = spec_conf_step value = 0 }}
					}}
					else = {{
						if = {{
							limit = {{ NOT = {{ var:spec_conf_aim = var:spec_conf }} }}
							set_variable = {{ name = spec_conf_aim value = var:spec_conf }}
							set_variable = {{ name = spec_conf_step value = {{ value = var:spec_conf subtract = var:spec_conf_shown divide = {GLIDE} }} }}
						}}
						change_variable = {{ name = spec_conf_shown add = var:spec_conf_step }}
						if = {{
							limit = {{ OR = {{ AND = {{ var:spec_conf_step > 0 var:spec_conf_shown > var:spec_conf }} AND = {{ var:spec_conf_step < 0 var:spec_conf_shown < var:spec_conf }} }} }}
							set_variable = {{ name = spec_conf_shown value = var:spec_conf }}
						}}
					}}
				}}
			}}
"""


def entry(stances):
    status = "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_je_status_{name}\n"
                     f"\t\t\t\ttrigger = {{ spec_stage = {n} }}\n\t\t\t}}\n" for n, name in STAGES)
    more = "".join(f"\tscripted_button = {b}\n" for b in BUTTONS)
    painted = "owner ?= {{ has_variable = spec_conf spec_law_mult > 0 spec_stage = {} }}"
    paint = "".join(f"\t\t{'if' if i == 0 else 'else_if'} = {{\n\t\t\tlimit = {{ {painted.format(n)} }}\n\t\t\tvalue = \"spec_map_{name}\"\n\t\t}}\n"
                    for i, (n, name) in enumerate(STAGES))
    return f"""je_spec_markets = {{
	icon = "{icons.path('je_markets')}"
	group = je_group_internal_affairs
	# Each country already has its own finance entry. A victorious revolution
	# must not copy the defeated parent's entry over that existing instance.
	can_revolution_inherit = no

	# players get it from spec_monthly; AI countries follow scripted rules instead of buttons (journal.MONTHLY_AI).
	# Shown (and so activated) for a player whenever investors are let in: an entry left inactive, as one was for
	# Britain in a 2026-10-31 test (add_journal_entry then reports it already there), comes back by itself, and not
	# before the first monthly update, which ranks the goods the text names
	is_shown_when_inactive = {{
		is_player = yes
		spec_law_mult > 0
		has_variable = spec_top1
	}}
	activation_description = {{
		always = yes
	}}
	# gone while the economic system keeps investors out; spec_monthly adds it back
	outcome = {{
		flags = {{ hidden invalid_outcome }}
		conclusion_desc = je_standard_failure_conclusion_desc
		trigger = {{ NOT = {{ spec_law_mult > 0 }} }}
	}}

	status_desc = {{
		first_valid = {{
{status}		}}
	}}

	# the stage's picture in a confidence ring where the icon sits, and the last three years of confidence
	widget = {{
		gui = "gui/spec_journal_widgets.gui"
		name = "spec_je_header"
		container = "custom_widget_container_je_icon"
	}}
	widget = {{
		gui = "gui/spec_journal_widgets.gui"
		name = "spec_je_history"
		container = "custom_widget_container_4"
	}}
	widget = {{
		gui = "gui/spec_journal_widgets.gui"
		name = "spec_je_news"
		container = "custom_widget_container_1"
	}}
	widget = {{
		gui = "gui/spec_journal_widgets.gui"
		name = "spec_je_marker"
		container = "custom_widget_container_7"
	}}

	# on activation (a new player, or a switch to this country) the bars show their start values until the first
	# pulse: Market Confidence read 55 in a panic at 18 (2026-11-16), so set them now
	# spec_je: the entry itself, for the Finance window to open its panel under it (market_tab.JE_PANEL), whose map
	# mode is the only way to show this one's
	immediate = {{
		je:je_spec_markets ?= {{
			set_bar_progress = {{ name = spec_confidence_bar value = root.var:spec_conf }}
{BARS}			root = {{ set_variable = {{ name = spec_je value = prev }} }}
		}}
	}}

	# the shown confidence glides to each month's figure in GLIDE weekly steps (market_tab.SHOWN)
	# as do a player's Investor Interest bars and contest bars (interest_board.glide, rivals' spec_rv_glide)
	on_weekly_pulse = {{
		effect = {{
{GLIDE_EFFECT}			root = {{
				if = {{
					limit = {{ is_player = yes }}
					spec_ui_glide_all = yes
					spec_rv_glide = yes
				}}
			}}
		}}
	}}

	# after the bars' periodic progress, which only itemizes the month for their tooltips
	on_monthly_pulse = {{
		effect = {{
			je:je_spec_markets ?= {{
				set_bar_progress = {{ name = spec_confidence_bar value = root.var:spec_conf }}
{BARS}				root = {{ set_variable = {{ name = spec_je value = prev }} }}
			}}
		}}
	}}

	# the world's markets by stage, on the journal entry map mode; root is a state
	map_color = {{
{paint}	}}
	map_color_second = {{
		if = {{
			limit = {{ owner ?= {{ has_variable = spec_caught }} }}
			value = "spec_map_caught"
		}}
	}}
	map_tooltip = {{
		# Resolve this state's owner before saving or reading it; an unowned state must not reuse a prior tooltip's scope.
		owner ?= {{
			save_scope_as = spec_map_owner
			if = {{
				limit = {{
					has_variable = spec_conf
					spec_law_mult > 0
				}}
				custom_tooltip_no_bullet = spec_map_tt
				if = {{
					limit = {{ has_variable = spec_caught }}
					custom_tooltip_no_bullet = spec_map_tt_caught
				}}
			}}
		}}
	}}

	scripted_progress_bar = spec_confidence_bar
	scripted_progress_bar = spec_excess_bar
	scripted_progress_bar = spec_finance_bar
{more}
	weight = 10
}}
"""


RANKED_GOODS = (("SPEC_JE_FAVOURED", "fav"), ("SPEC_JE_SHUNNED", "shun"))


def goods_row(label, kind):
    """Active investor preferences in the journal and Finance: every good with a running term (investor_sentiment.LISTS)."""
    # ponytail: one line of 30px icons, about 11 fit; wrap it if more terms ever run at once
    chips = [f'''textbox = {{
                visible = "[Not({mt.gt(mt.v(f'spec_{kind}_n'))})]"
                text = "NONE"
                align = left|vcenter
            }}''', f"""flowcontainer = {{
                spacing = 6
                datamodel = "[{mt.P}.GetList('spec_{kind}_goods')]"
                item = {{
                    icon = {{
                        datacontext = "[Scope.GetGoods]"
                        size = {{ 30 30 }}
                        texture = "[Goods.GetTexture]"
                        tooltip = "{label}_GOOD_TT"
                    }}
                }}
            }}"""]
    return mt.card_row(label, f"{label}_TT", "\n".join(chips))


def widgets():
    """The journal entry's two widgets, built from the Speculation tab's parts (market_tab) in the player's context, as the tab uses (the
    entry is the player's own; JournalEntry.GetCountry left the ring and pictures blank):
    the header, vanilla's journal illustration with the stage's painting in the tab's confidence ring, and the tab's
    history chart in a budget row."""
    P, conf = mt.P, mt.SHOWN
    slump = f"Or({mt.IN_PANIC}, And({P}.Var('spec_ld').IsSet, LessThan_CFixedPoint({mt.v('spec_ld')}, {mt.fx(3)})))"
    after = f"{P}.Var('spec_panic_cooldown').IsSet"
    calm = f"Not(Or({slump}, {after}))"
    pics = [("panic", slump), ("wary", f"And(Not({slump}), Or({after}, {mt.tier_test(conf, 0, mt.TIERS[1][2])}))")] + [
        (key, f"And({calm}, {mt.tier_test(conf, lo, hi)})") for key, lo, hi in mt.TIERS[2:]]
    low = f"Or({mt.IN_PANIC}, Or({mt.PANIC_ZONE}, {mt.MANIA_ZONE}))"
    gauge = "".join(f"""			round_progress_{kind} = {{
				size = {{ 96 96 }}
				parentanchor = center
				visible = "[{vis}]"
				value = "[{mt.share(conf)}]"
			}}
""" for kind, vis in [("default", f"Not({low})"), ("bad", low)])
    pictures = "".join(f"""			icon = {{
				size = {{ 74 74 }}
				parentanchor = center
				visible = "[{vis}]"
				texture = "{icons.path(f'state_{key}')}"
			}}
""" for key, vis in pics)
    width = mt.HISTORY * (mt.COL_W + mt.COL_GAP) - mt.COL_GAP
    box_h = 4 * 36 + mt.CHART_H + 12 + 12  # two chip rows, two goods rows, the history, margins
    return f"""widget = {{
	name = "spec_je_header"
	datacontext = "[GetPlayer]"
	size = {{ 560 158 }}
	parentanchor = hcenter
	widget = {{
		size = {{ 560 120 }}
		background = {{
			texture = "gfx/interface/illustrations/journal/top_illu_journal_entries.dds"
			using = top_illu_properties
		}}
		widget = {{
			size = {{ 116 116 }}
			parentanchor = center
			tooltip = "SPEC_CARD_RING_TT"
			background = {{
				using = circle_bg_simple_dark
			}}
			icon = {{
				size = {{ 116 116 }}
				parentanchor = center
				texture = "gfx/interface/backgrounds/round_frame_dec.dds"
			}}
{mt.ind(gauge + pictures, 1)}		}}
	}}
	# under the illustration: our Exchange on the left (centres.py), the Finance window on the right
	textbox = {{
		position = {{ 24 -2 }}
		size = {{ 320 30 }}
		parentanchor = bottom|left
		align = left|nobaseline
		elide = right
		text = "SPEC_JE_EXCH"
		tooltip = "SPEC_JE_EXCH_TT"
	}}
	button = {{
		using = default_button
		size = {{ 170 30 }}
		position = {{ -24 -2 }}
		parentanchor = bottom|right
		text = "SPEC_OPEN_TAB"
		tooltip = "SPEC_OPEN_TAB_TT"
		onclick = "{goods_panel.OPEN_TAB}"
	}}
}}

# a headline from the financial pages, by the stage, above the status
widget = {{
	name = "spec_je_news"
	datacontext = "[GetPlayer]"
	size = {{ 504 56 }}
	parentanchor = hcenter
	using = entry_bg_fancy
	icon = {{
		size = {{ 40 40 }}
		position = {{ 10 0 }}
		parentanchor = vcenter
		texture = "gfx/interface/icons/event_icons/event_newspaper.dds"
	}}
	textbox = {{
		position = {{ 60 0 }}
		size = {{ 432 50 }}
		parentanchor = vcenter
		multiline = yes
		align = left|nobaseline
		fontsize_min = 12
		text = "SPEC_JE_NEWS"
	}}
}}

# the month at a glance: the Speculation card's chip rows, the goods investors favour and shun, and the history
widget = {{
	name = "spec_je_history"
	datacontext = "[GetPlayer]"
	size = {{ 504 {box_h} }}
	parentanchor = hcenter
	background = {{
		using = entry_bg
	}}
	flowcontainer = {{
		direction = vertical
		parentanchor = hcenter
		position = {{ 0 6 }}
{mt.ind(mt.chip_rows() + "".join(goods_row(label, keys) for label, keys in RANKED_GOODS), 2)}		widget = {{
			size = {{ {mt.W - 2 * mt.CARD_X} {mt.CHART_H + 12} }}
			parentanchor = hcenter
			tooltip = "SPEC_HISTORY_TT"
			textbox = {{
				size = {{ {mt.LABEL_W} 30 }}
				parentanchor = vcenter
				align = left|nobaseline
				elide = right
				text = "SPEC_HISTORY"
			}}
			widget = {{
				position = {{ 110 0 }}
				size = {{ {width} {mt.CHART_H} }}
				parentanchor = vcenter
{mt.ind(mt.history_chart(width), 4)}			}}
		}}
	}}
}}

# marks this entry for journal_entry.gui, which hides the Progress Conditions section here (generate.journal_entry_gui)
widget = {{
	name = "spec_je_marker"
	size = {{ 0 0 }}
}}
"""


# in spec_monthly for every country with investors, after the panic countdowns
MONTHLY = f"""			# converted debt paid down: the lower rate goes with it (journal.py)
			if = {{
				limit = {{
					has_modifier = spec_debt_converted
					scaled_debt < {CONVERT_DEBT}
				}}
				remove_modifier = spec_debt_converted
			}}
			# months without a panic, for a Commission of Inquiry outside an aftermath (journal.py)
			if = {{
				limit = {{ has_variable = spec_panic }}
				set_variable = {{ name = spec_calm value = 0 }}
				remove_variable = spec_inquired
			}}
			else = {{
				if = {{
					limit = {{ NOT = {{ has_variable = spec_calm }} }}
					set_variable = {{ name = spec_calm value = 0 }}
				}}
				change_variable = {{ name = spec_calm add = 1 }}
			}}
"""

# in the AI block (is_player = no), after the AI's bank rescue roll
MONTHLY_AI = f"""				# the journal entry's choices by rule (journal.py): an inquiry when one can sit, debt converted in good
				# times, relief in a slump, and the Bank Act suspended when the state cannot lend to the banks
				if = {{
					limit = {{
						spec_reform_open = yes
						spec_can_inquire = yes
					}}
					random = {{
						chance = {AI_INQUIRY_CHANCE:g}
						spec_do_inquiry = yes
{_log("inquiry", chr(9) * 6)}					}}
				}}
				if = {{
					limit = {{ spec_can_convert = yes }}
					random = {{
						chance = {AI_CONVERT_CHANCE:g}
						spec_do_convert = yes
{_log("convert", chr(9) * 6)}					}}
				}}
				if = {{
					limit = {{
						spec_can_relief = yes
						scaled_debt < 0.5
						NOT = {{ spec_nearly_broke = yes }}
					}}
					random = {{
						chance = {AI_RELIEF_CHANCE:g}
						spec_do_relief = yes
{_log("relief", chr(9) * 6)}					}}
				}}
				if = {{
					limit = {{
						spec_can_suspend = yes
						var:spec_panic > {SUSPEND_MONTHS}
						OR = {{
							in_default = yes
							NOT = {{ has_technology_researched = banking }}
							gold_reserves < spec_rescue_cost
						}}
					}}
					spec_do_suspend = yes
{_log("suspend", chr(9) * 5)}				}}
"""

# the bar updates, inside generate.py's je:je_spec_markets ?= block
BARS = """				if = {
					limit = { root = { has_variable = spec_heat } }
					set_bar_progress = { name = spec_excess_bar value = { value = root.var:spec_heat max = """ + str(EXCESS_MAX) + """ } }
				}
				else = {
					set_bar_progress = { name = spec_excess_bar value = 0 }
				}
				if = {
					limit = { root = { has_variable = spec_reforms } }
					set_bar_progress = { name = spec_finance_bar value = root.var:spec_reforms }
				}
"""


def events():
    R = REFORM_AI

    def temper(t, n):
        return f"\t\t\tmodifier = {{\n\t\t\t\ttrigger = {{ var:spec_temper ?= {t} }}\n\t\t\t\tadd = {n}\n\t\t\t}}\n"

    def option(letter, need, body, base, temper_line=""):
        return (f"\toption = {{\n\t\tname = spec_reform.1.{letter}\n\t\ttrigger = {{ {need} }}\n{body}"
                f"\t\tspec_reform_done = yes\n{_log('reform', chr(9) * 2, f' opt={letter}')}\t\tai_chance = {{\n\t\t\tbase = {base}\n{temper_line}\t\t}}\n\t}}\n")

    def tt(key, *lines):
        inner = "".join(f"\t\t\t{x}\n" for x in lines)
        return f"\t\tcustom_tooltip = {{\n\t\t\ttext = {key}\n{inner}\t\t}}\n"

    ig2 = lambda key, mod: "".join(f"\t{line}\n" for line in ig(key, mod, "days = short_modifier_time").splitlines())
    note = "has_technology_researched = banking NOT = { has_variable = spec_note }"
    return f"""namespace = spec_reform

# the Commission of Inquiry's report: one Sound Finance institution, or none
spec_reform.1 = {{
	type = country_event
	placement = root
	title = spec_reform.1.t
	desc = {{
		first_valid = {{
			triggered_desc = {{
				desc = spec_reform.1.d_panic
				trigger = {{ has_variable = spec_panic_cooldown }}
			}}
			triggered_desc = {{
				desc = spec_reform.1.d_calm
				trigger = {{ always = yes }}
			}}
		}}
	}}
	flavor = spec_reform.1.f
	duration = 3
{stories.pictures(INQUIRY_PICS)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_scales.dds"

{option('a', note, tt('spec_reform_currency_tt', 'set_variable = { name = spec_note value = 1 }') + ig2('industrialists', 'spec_dear_money'), R['currency'], temper(-1, REFORM_AI_TEMPER))}
{option('b', note, tt('spec_reform_free_tt', 'set_variable = { name = spec_note value = 2 }') + ig2('industrialists', 'spec_free_issue'), R['free'], temper(1, REFORM_AI_TEMPER))}
{option('c', 'has_technology_researched = central_banking NOT = { has_variable = spec_llr }', tt('spec_reform_llr_tt', 'set_variable = spec_llr'), R['llr'])}
{option('d', 'has_technology_researched = joint_stock_companies NOT = { has_variable = spec_company_law }', tt('spec_reform_company_tt', 'set_variable = spec_company_law') + ig2('industrialists', 'spec_disclosure_burden') + ig2('intelligentsia', 'spec_disclosure_welcomed'), R['company'])}
	option = {{  # shelve it: the money men are relieved and the market with them, the reformers are not
		name = spec_reform.1.e
		default_option = yes
{ig2('industrialists', 'spec_report_shelved')}{ig2('intelligentsia', 'spec_report_buried')}{stories.conf(SHELVE_CONF)}{_log('reform', chr(9) * 2, ' opt=e')}		ai_chance = {{
			base = {R['shelve']:g}
		}}
	}}
}}

# all three institutions made
spec_reform.2 = {{
	type = country_event
	placement = root
	title = spec_reform.2.t
	desc = spec_reform.2.d
	flavor = spec_reform.2.f
	duration = 3
{stories.pictures(SOUND_PICS)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	option = {{
		name = spec_reform.2.a
		default_option = yes
		add_modifier = {{ name = spec_sound_finance }}
	}}
}}
"""


BUBBLE_ALERT = 10   # the bubble alert shows once a burst would cost this much confidence


# an alert can only open a vanilla panel, so the alert row's button (generate.alert_row) knows ours by name and
# opens the Finance window's tab instead (Alert.GetTexture can't be compared, 2026-11-20). Speculation shows the Risk
# marker on the confidence card and the goods' Risk column; Excess cools under Tight credit on Banking
ALERT_TABS = {"spec_panic_risk_alert": "booms", "spec_bubble_alert": "banking"}


def alerts(k):
    """Two alerts in vanilla's row under the top bar: the Risks bar's risks striking would set off a panic, and a bubble worth
    bursting. Players can hide either in the alert settings, as any vanilla alert."""
    return f"""spec_panic_risk_alert = {{
	script_context = player_country
	texture = "gfx/interface/icons/alert_icons/company_losing_prosperity.dds"

	valid = {{
		has_variable = spec_conf
		NOT = {{ has_variable = spec_panic }}
		NOT = {{ has_variable = spec_panic_cooldown }}
		spec_after_risks < {leverage.panic_limit(k['PANIC'])}
	}}

	# the alert row opens Finance for it (ALERT_TABS); this is the popup's fallback
	open_panel = journal
	type = alert
	color = red
}}

spec_bubble_alert = {{
	script_context = player_country
	texture = "{icons.path('excess_alert')}"

	valid = {{
		NOT = {{ has_variable = spec_panic }}
		spec_burst_now >= {BUBBLE_ALERT}
	}}

	open_panel = journal
	type = alert
	color = yellow
}}

# something the player can do now: both buttons are on the Finance window's Banking tab, reached from the journal entry
spec_rescue_alert = {{
	script_context = player_country
	texture = "gfx/interface/icons/alert_icons/can_establish_company.dds"

	valid = {{
		spec_can_rescue = yes
	}}

	open_panel = journal
	type = alert
	color = yellow
}}
""" + ("" if not leverage.ON else """
spec_bailout_alert = {
	script_context = player_country
	texture = "gfx/interface/icons/alert_icons/market_over_capacity.dds"

	valid = {
		spec_can_bailout = yes
	}

	open_panel = journal
	type = alert
	color = yellow
}
""")


def build(write, k):
    write("common/script_values/spec_journal_values.txt", values(k))
    write("common/scripted_triggers/spec_journal_triggers.txt", TRIGGERS)
    write("common/scripted_effects/spec_journal_effects.txt", effects())
    write("common/static_modifiers/spec_journal_modifiers.txt", modifiers())
    write("common/scripted_buttons/spec_journal_buttons.txt", buttons())
    write("common/scripted_progress_bars/spec_journal_bars.txt", bars(k))
    write("events/spec_reform_events.txt", events())
    write("gui/spec_journal_widgets.gui", widgets())
    write("common/alert_types/spec_alert_types.txt", alerts(k))
    write("common/named_colors/spec_map_colors.txt", "colors = {\n" + "".join(f"\tspec_map_{n} = {c}\n" for n, c in MAP_COLORS.items()) + "}\n")


def loc(k):
    sv = lambda name: f"{C}.ScriptValue('{name}')"
    at = lambda name, n: f"GreaterThanOrEqualTo_CFixedPoint({sv(name)}, '(CFixedPoint){n}')"
    on = lambda name: f"GreaterThan_CFixedPoint({sv(name)}, '(CFixedPoint)0')"
    var = lambda name, fmt="|0": f"[{C}.Var('{name}').GetValue{fmt}]"
    good = lambda key: f"#v [{C}.Var('spec_{key}').GetGoods.GetName]#!"
    top = f"{good('top1')}, {good('top2')} and {good('top3')}"
    low = f"{good('low1')} and {good('low2')}"
    # SelectLocalization from the highest stage down
    chain = "'SPEC_JE_STAGE_0'"
    for n, _ in reversed(STAGES[:-1]):
        chain = f"SelectLocalization({at('spec_stage', n)}, 'SPEC_JE_STAGE_{n}', {chain})"
    inst = "".join(f"[SelectLocalization({on(f'spec_{r}_v')}, 'SPEC_JE_INST_{r.upper()}', 'SPEC_JE_NONE')]"
                   for r in ("currency", "free", "llr", "company"))
    # the status line is also shown outside the entry's panel, where only ROOT is the country (as vanilla's status texts)
    R = "ROOT.GetCountry.MakeScope"
    rsv = lambda name: f"{R}.ScriptValue('{name}')"
    stance = (f"[SelectLocalization(GreaterThan_CFixedPoint({rsv('spec_has_central_banking')}, '(CFixedPoint)0'), "
              f"SelectLocalization(GreaterThan_CFixedPoint({rsv('spec_stance_value')}, "
              f"'(CFixedPoint)0'), 'SPEC_JE_CREDIT_LOOSE', SelectLocalization(GreaterThan_CFixedPoint('(CFixedPoint)0', "
              f"{rsv('spec_stance_value')}), 'SPEC_JE_CREDIT_TIGHT', 'SPEC_JE_CREDIT_NORMAL')), 'SPEC_JE_NONE')]")
    # Bad Debts take the credit policy's place on the status line: no bank is lending while they last
    stance = f"[SelectLocalization({R}.Var('spec_crunch').IsSet, 'SPEC_JE_BAD_DEBTS', {stance[len('[') :-1]})]"
    mc, fp = "[concept_spec_market_confidence]", "[concept_spec_financial_panic]"
    excess = "[concept_spec_speculative_excess]"
    G = "GetPlayer.MakeScope.ScriptValue"
    tech = lambda t: f"[GetTechnology('{t}').GetName]"
    status = {"ld": "#n [concept_spec_long_depression]#!", "panic": f"#n {fp}#! ends in #v [{R}.Var('spec_panic').GetValue|0]#! months",
              "aftermath": "#v Aftermath#!", "mania": "#n Mania#!", "buoyant": "#v Buoyant#!", "steady": "#v Steady#!",
              "wary": "#v Wary#!"}
    cap = "[JournalEntry.GetCountry.GetCapital.GetCityHubName]"
    stage = {
        6: f"The [concept_spec_long_depression] hangs over {cap}. Investors hoard what they have and lend to no one, and "
           "each recovery so far has faltered within months. The world's recovery is followed in a journal entry of its own.\\n\\n"
           "Relief Works can put the unemployed to work and keep them fed while the slump lasts.",
        5: f"Panic has gripped {cap}. Depositors queue outside the banks from first light, loans are called in, and "
           f"[concept_private_construction] is #N [{sv('spec_panic_cut_shown')}|%0]#! lower for #v {var('spec_panic')}#! more months unless the government acts."
           "\\n\\n#v Lend to the Banks#! would end it sooner and halve its effects. Relief Works can put the unemployed to work "
           f"and keep them fed.[SelectLocalization({on('spec_currency_v')}, 'SPEC_JE_SUSPEND_HINT', 'SPEC_JE_NONE')]",
        4: f"The panic has passed, leaving failed houses and half-built works behind it. Investors are counting their "
           f"losses, and no new panic can start for #v {var('spec_panic_cooldown')}#! months."
           f"[SelectLocalization({on('spec_reform_open_v')}, 'SPEC_JE_INQUIRY_HINT', 'SPEC_JE_NONE')]",
        3: f"The exchange in {cap} has gone mad. Clerks and widows buy shares in {top} with borrowed money, and every "
           f"month that {mc} stands at #v [{sv('spec_heat_from')}|0]#! or more adds to the {excess}. When $concept_spec_market_confidence$ falls below #v {k['BURST_BELOW']}#! the "
           "bubble bursts, and the greater the excess, the harder the fall.\\n\\nRestraining speculation in the hottest "
           "goods, or tightening credit, would let the air out slowly.",
        2: f"Money is easy and investors are buoyant. New companies in {top} are oversubscribed within the hour, and the "
           f"banks lend freely against their shares. With {mc} at #v [{sv('spec_heat_from')}|0]#! or more, the {excess} starts to build."
           "\\n\\nGood times are also the moment to convert our national debt to a lower rate.",
        1: f"Trade on the exchange in {cap} is orderly. Investors favor {top} and shun {low}.",
        0: f"Investors in {cap} are wary. Burned by recent losses, they keep their money close and shun {low}. Loose "
           "credit, or encouragement to invest in a good, may coax them back.",
    }
    # the headline above the status: as the stage chain, read on the player (the widgets' context)
    gp = "GetPlayer.MakeScope"
    news_chain = "'SPEC_JE_NEWS_0'"
    for n, _ in reversed(STAGES[:-1]):
        news_chain = f"SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({gp}.ScriptValue('spec_stage'), '(CFixedPoint){n}'), 'SPEC_JE_NEWS_{n}', {news_chain})"
    hot, city = f"[{gp}.Var('spec_top1').GetGoods.GetName]", "[GetPlayer.GetCapital.GetCityHubName]"
    news = {
        6: "Another Lean Year: Mills Stand Silent and the Banks Will Not Lend",
        5: f"RUN ON THE BANKS! Crowds Besiege the Counting Houses of {city}",
        4: "Exchange Reopens to Thin Trading as Creditors Count the Cost",
        3: f"Fever on the {city} Exchange: Clerks and Widows Buy {hot} on Borrowed Money",
        2: f"New {hot} Issue Oversubscribed Within the Hour as Banks Lend Freely",
        1: f"Quiet Day in {city}: {hot} Shares Firm, the Rest Unchanged",
        0: f"Money Shy in {city}: Brokers Idle as Investors Keep Their Purses Shut",
    }
    ig_tt = lambda key: next(f"{n:+d}" for k2, _, n, _ in IG_MODIFIERS if k2 == key)
    # the map's tooltip: the stage's short name, by the same chain as the entry's text, on the state's owner
    map_chain = "'SPEC_MAP_STAGE_0'"
    for n, _ in reversed(STAGES[:-1]):
        map_chain = f"SelectLocalization(GreaterThanOrEqualTo_CFixedPoint({OWNER}.ScriptValue('spec_stage'), '(CFixedPoint){n}'), 'SPEC_MAP_STAGE_{n}', {map_chain})"
    lines = {
        "spec_map_tt": f"#header [SCOPE.sCountry('spec_map_owner').GetName]#!\\n[{map_chain}]\\n[concept_spec_market_confidence]: #v [{OWNER}.Var('spec_conf').GetValue|0]#!",
        "spec_map_tt_caught": f"Hit by the [concept_spec_financial_panic] in #v [{OWNER}.Var('spec_foreign_src').GetCountry.GetName]#!",
        **{f"SPEC_MAP_STAGE_{n}": t for n, t in MAP_STAGES.items()},
        "je_spec_markets": "Financial Markets",
        "je_spec_markets_reason": f"[{chain}]\\n\\n[SelectLocalization({on('spec_reform_count')}, 'SPEC_JE_INST_SOME', 'SPEC_JE_INST_NONE')]{inst}",
        # the widgets (widgets()), in the player's context
        "SPEC_JE_NEWS": f"[{news_chain}]",
        **{f"SPEC_JE_NEWS_{n}": f"#italic {t}#!" for n, t in news.items()},
        "SPEC_JE_EXCH": ("[SelectLocalization(GetPlayer.MakeScope.Var('spec_exch_stand').IsSet, 'SPEC_JE_EXCH_ON', 'SPEC_JE_NONE')]"
                         if __import__("centres").ON else ""),
        "SPEC_JE_EXCH_ON": "$SPEC_EXCH_CITY_ME$ Exchange: #v $SPEC_EXCH_STAND_ME$#!",
        "SPEC_JE_EXCH_TT": "Our [concept_spec_exchange] and its Standing, which rises and falls with its score. A higher Standing makes booms run hotter and fall harder. The #bold $SPEC_FIN_TAB_EXCHANGE$#! tab of the #bold $SPEC_FINANCE$#! window shows its charter and specialities.",
        "SPEC_JE_FAVOURED": "Favored",
        "SPEC_OBS_RV_OUT": "Competitors named by [GetMetaPlayer.GetPlayedOrObservedCountry.GetName]",
        "SPEC_OBS_RV_IN": "Exchanges contesting [GetMetaPlayer.GetPlayedOrObservedCountry.GetName]",
        "SPEC_JE_FAVOURED_TT": f"#header $SPEC_JE_FAVOURED$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_FAV_IMPACT$ This [concept_spec_investor_sentiment] lasts #v {sent.MONTHS}#! months. Its effect on [concept_spec_investor_interest] starts from #P +{sent.BONUS:.0%}#! and grows the further the price runs above [concept_base_price], the larger the good's share of our market and the higher our [concept_spec_market_confidence]. It fades over the last #v {sent.FADE_FROM}#! months. The good's producers get half of it as [concept_throughput].\\n\\n$SPEC_FAV_REASON$\\n\\n$SPEC_TERM_ODDS$",
        "SPEC_JE_SHUNNED": "Shunned",
        "SPEC_JE_SHUNNED_TT": f"#header $SPEC_JE_SHUNNED$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_SHUN_IMPACT$ This [concept_spec_investor_sentiment] lasts #v {sent.MONTHS}#! months. Its effect on [concept_spec_investor_interest] starts from #N −{sent.BONUS:.0%}#! and grows the further the price falls below [concept_base_price], the larger the good's share of our market and the lower our [concept_spec_market_confidence]. It fades over the last #v {sent.FADE_FROM}#! months. The good's producers get half of it as [concept_throughput].\\n\\n$SPEC_SHUN_REASON$\\n\\n$SPEC_TERM_ODDS$",
        "SPEC_FAV_REASON": f"A good can become $SPEC_JE_FAVOURED$ after #v {sent.QUALIFY}#! straight months with sell orders and a price at least #v {sent.PREMIUM:.0%}#! above its [concept_base_price].",
        "SPEC_SHUN_REASON": f"A good can become $SPEC_JE_SHUNNED$ after #v {sent.QUALIFY}#! straight months with sell orders and a price at least #v {sent.PREMIUM:.0%}#! below its [concept_base_price].",
        "SPEC_FAV_IMPACT": "Investors are more willing to finance buildings that produce these goods.",
        "SPEC_SHUN_IMPACT": "Investors are less willing to finance buildings that produce these goods.",
        "SPEC_FAV_PLAY": "Check input costs and boom exposure before expanding production.",
        "SPEC_SHUN_PLAY": "An industry that uses this good can benefit from cheap inputs and support demand.",
        "SPEC_TERM_ODDS": f"Small goods can qualify too. A run of #v {sent.MATURE}#! months or more, or at least #v {sent.SHARE:.0%}#! of our market's supply by value, improves a good's chances. Each good already $SPEC_JE_FAVOURED$ or $SPEC_JE_SHUNNED$ makes new terms less likely. High [concept_spec_market_confidence] makes $SPEC_JE_FAVOURED$ terms more likely, and low confidence makes $SPEC_JE_SHUNNED$ terms more likely.",
        **{f"SPEC_JE_STAGE_{n}": t for n, t in stage.items()},
        **{f"spec_je_status_{key}": f"{t}{stance}" for key, t in status.items()},
        "SPEC_JE_BAD_DEBTS": f", [concept_spec_bad_debts] #N -[{G}('spec_crunch_tp_pct')|1]%#! for #v [{G}('spec_crunch_months')|0]#! months",
        "SPEC_JE_CREDIT_TIGHT": ", [concept_spec_credit_policy] #v Tight#!",
        "SPEC_JE_CREDIT_NORMAL": ", [concept_spec_credit_policy] #v Normal#!",
        "SPEC_JE_CREDIT_LOOSE": ", [concept_spec_credit_policy] #v Loose#!",
        "SPEC_JE_NONE": "",
        "SPEC_JE_SUSPEND_HINT": " Suspending the Bank Act ends it quickly at no cost to the treasury, but teaches investors "
                                "to count on the next rescue.",
        "SPEC_JE_INQUIRY_HINT": "\\n\\nNow is the moment to ask how it happened. A Commission of Inquiry can reform how our "
                                "banks lend and our companies report.",
        "SPEC_JE_INST_NONE": "We have passed no [concept_spec_banking_reforms] yet.",
        "SPEC_JE_INST_SOME": "We have passed these [concept_spec_banking_reforms]:",
        "SPEC_JE_INST_CURRENCY": "\\nThe #bold Currency School#! means less credit, a slower bubble and longer panics.",
        "SPEC_JE_INST_FREE": "\\n#bold Free Banking#! means more credit, and larger booms and falls.",
        "SPEC_JE_INST_LLR": "\\nA #bold Lender of Last Resort#! makes #v Lend to the Banks#! cheaper and faster.",
        "SPEC_JE_INST_COMPANY": "\\n#bold Company Law#! makes booms cost less when they end.",
        "spec_excess_bar": "Speculative Excess",
        "concept_spec_speculative_excess": "Speculative Excess",
        "concept_spec_speculative_excess_desc": f"The size of the bubble in a [concept_country]'s [concept_market], once it has {tech('stock_exchange')}. It grows each month [concept_spec_market_confidence] is #v [{G}('spec_heat_from')|0]#! or more, faster the higher $concept_spec_market_confidence$ is. Between #v {k['BURST_BELOW']}#! and #v [{G}('spec_heat_from')|0]#! it slowly shrinks, faster under a [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')] credit policy.\\n\\nIf $concept_spec_market_confidence$ falls below #v {k['BURST_BELOW']}#!, the bubble bursts and $concept_spec_market_confidence$ loses #N [{G}('spec_burst_per_heat')|%0]#! of its size{'. Whatever it cannot cover becomes the same amount of [concept_spec_bad_debts]' if leverage.ON else ', down to zero at most'}.",
        "concept_spec_sound_finance": "Sound Finance",
        "concept_spec_sound_finance_desc": f"The reward for passing all three [concept_spec_banking_reforms], Banknote Rules, a Lender of Last Resort and Company Law. A [concept_country] that has all three gains #P +{SOUND_PRESTIGE}#! [concept_prestige].",
        "concept_spec_banking_reforms": "Banking Reforms",
        "concept_spec_banking_reform": "Banking Reform",
        "concept_spec_banking_reforms_desc": f"The rules a [concept_country]'s banks and companies play by, each changing how booms and panics go. There are three, each unlocked by a technology. #b Banknote Rules#! ({tech('banking')}) are either the #b Currency School#! or #b Free Banking#!. Then come a #b Lender of Last Resort#! ({tech('central_banking')}) and #b Company Law#! ({tech('joint_stock_companies')}).\\n\\nA Commission of Inquiry passes one reform at a time. It can sit after a [concept_spec_financial_panic], or after #v {INQUIRY_CALM // 12}#! calm years with no panic. Passing all three earns [concept_spec_sound_finance].",
        "alert_spec_panic_risk_alert_name": "Panic Risk",
        "spec_panic_risk_alert_setting_name": "Panic Risk",
        "alert_spec_panic_risk_alert_desc": f"If our current risks all strike, {mc} drops to #N [{G}('spec_after_risks')|0]#!.\\nA {fp} starts below #v {f"[{G}('spec_panic_at')|0]" if leverage.ON else k['PANIC']}#!.",
        "alert_spec_panic_risk_alert_hint": "To lower the risk, Restrain Speculation in the riskiest goods on the #bold $SPEC_FIN_TAB_BOOMS$#! tab, or tighten [concept_spec_credit_policy] on the #bold $SPEC_FIN_TAB_BANKING$#! tab.",
        "alert_spec_panic_risk_alert_action": "$SPEC_FINANCE$",
        "alert_spec_bubble_alert_name": "Speculative Excess",
        "spec_bubble_alert_setting_name": "Speculative Excess",
        "alert_spec_bubble_alert_desc": f"Our {excess} is #v [GetPlayer.MakeScope.Var('spec_heat').GetValue|0]#!. It bursts if {mc} drops below #v {k['BURST_BELOW']}#!. If it burst now, $concept_spec_market_confidence$ would fall by #N [{G}('spec_burst_now')|0]#! at once.",
        "alert_spec_bubble_alert_hint": f"To let it down gently, restrain the booming goods or tighten [concept_spec_credit_policy].\\n#P Grows#! while {mc} is #v [{G}('spec_heat_from')|0]#! or more\\n#v Shrinks#! slowly while it is between #v {k['BURST_BELOW']}#! and #v [{G}('spec_heat_from')|0]#!, faster with a [Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')] credit policy",
        "alert_spec_bubble_alert_action": "$SPEC_FINANCE$",
        "alert_spec_rescue_alert_name": "Bank Rescue Available",
        "spec_rescue_alert_setting_name": "Bank Rescue Available",
        "alert_spec_rescue_alert_desc": f"A {fp} is on, and we have not lent to the banks yet.",
        "alert_spec_rescue_alert_hint": f"Use #v Lend to the Banks#! in the #bold $SPEC_FIN_TAB_BANKING$#! tab of the #bold $SPEC_FINANCE$#! window. Once per panic.\\n#P Ends#! the panic sooner\\n#P Halves#! its penalties for the months it has left\\n{mc} #P +{k['RESCUE_CONF']}#!\\n\\n#weak Does not cut $spec_panic_relief$ payments{', clear [concept_spec_bad_debts]' if leverage.ON else ''} or win back people already radicalized#!",
        "alert_spec_rescue_alert_action": "Journal",
        "alert_spec_bailout_alert_name": "Buy Up Bad Loans Available",
        "spec_bailout_alert_setting_name": "Buy Up Bad Loans Available",
        "alert_spec_bailout_alert_desc": "[concept_spec_bad_debts] are slowing our [concept_throughput] and investment, and we have not bought up the bad loans yet.",
        "alert_spec_bailout_alert_hint": f"Use #v Buy Up Bad Loans#! in the #bold $SPEC_FIN_TAB_BANKING$#! tab of the #bold $SPEC_FINANCE$#! window. Only once while they last.\\n#P Clears {leverage.BAILOUT_CUT:.0%}#! of the remaining [concept_spec_bad_debts]\\nCosts #v @money![{G}('spec_bailout_cost')|D]#!",
        "alert_spec_bailout_alert_action": "Journal",
        "spec_excess_bar_desc": f"[SelectLocalization({on('spec_has_stock_exchange')}, 'SPEC_EXCESS_ON', 'SPEC_EXCESS_OFF')]",
        "SPEC_EXCESS_ON": f"{excess}: #v [{sv('spec_heat_shown')}|0]#![SelectLocalization({on('spec_burst_now')}, 'SPEC_EXCESS_COST', 'SPEC_JE_NONE')]",
        "SPEC_EXCESS_COST": f"\\nIf it burst now, {mc} would fall by #N [{sv('spec_burst_now')}|1]#!",
        "SPEC_EXCESS_OFF": f"{excess} builds up once [GetTechnology('stock_exchange').GetName] is researched",
        **{key: label for _, key, label in excess_calc(k)[1]},  # the Excess forecast's causes (excess), for the bar and the Finance tooltip
        "spec_finance_bar": "Sound Finance",
        "spec_finance_bar_desc": "[concept_spec_sound_finance]: #v [JournalEntry.GetCurrentBarValue(ScriptedProgressBar.Self)|0]#! of #v 3#! [concept_spec_banking_reforms]",
        "spec_inquiry_no_panic_tt": f"No {fp} is under way",
        "spec_inquiry_reform_tt": "Our technology unlocks a [Concept('concept_spec_banking_reforms','$concept_spec_banking_reform$')] we have not passed yet",
        "spec_suspend_panic_tt": f"A {fp} is under way",
        "spec_suspend_note_tt": "We picked the Currency School for our Banknote Rules",
        "spec_inquiry_when_tt": f"A {fp} ended in the last year and no inquiry has sat since, or #v {INQUIRY_CALM // 12}#! "
                                f"calm years have passed with no panic (#v [ROOT.GetCountry.MakeScope.ScriptValue('spec_calm_left')|0]#! months to go)",
        "spec_convert_conf_tt": f"{mc} is at least #v {CONVERT_FROM}#!",
        "spec_convert_debt_tt": f"Our debt is at least #v {CONVERT_DEBT:.0%}#! of our [concept_credit] limit",
        "spec_convert_cd_tt": f"We have not converted the debt in the last #v {CONVERT_COOLDOWN_YEARS}#! years",
        "spec_convert_conf_cost_tt": f"{mc} #N -{CONVERT_CONF}#!",
        "spec_relief_when_tt": f"A {fp} or the [concept_spec_long_depression] is on",
        "spec_relief_cd_tt": f"No Relief Works in the last #v {RELIEF_MONTHS}#! months",
        "spec_suspend_tt": f"The {fp} #P ends#! within #v {SUSPEND_MONTHS}#! months, but hits at full strength until then\\n{mc} #P +{SUSPEND_CONF}#!\\n"
                           f"For #v {HAZARD_YEARS}#! years after, the {excess} grows #N {HAZARD_HEAT - 1:.0%}#! faster"
                           + ("\\n[concept_spec_lending_standards] loosen, just like after a Bank Rescue" if cycle.ON else ""),
        "spec_suspend_act": "Suspend the Bank Act",
        "spec_suspend_act_desc": "Let the bank print more notes than the Act allows. The panic dies down within months and costs the "
                                 "treasury nothing. The catch is that investors learn we will always bail them out. This counts as "
                                 "#v Lend to the Banks#! for this panic.",
        "spec_relief_works_button": "Relief Works",
        "spec_relief_works_button_desc": f"Pay for public works and relief while the slump lasts. For #v {RELIEF_MONTHS}#! months it lifts "
                                         "welfare and construction and pulls support away from the radicals. The bigger our [concept_gdp], the more it costs each week.",
        "spec_convert_debt": "Convert the National Debt",
        "spec_convert_debt_desc": "While investors are in a good mood, swap our loans for new ones with lower interest. People who lived "
                                  "on the old interest will not thank us.",
        "spec_inquiry": "Commission of Inquiry",
        "spec_inquiry_desc": "Ask a commission to hear bankers, brokers and ruined savers and say how our banks and "
                             f"companies should be run. Its report passes one [Concept('concept_spec_banking_reforms','$concept_spec_banking_reform$')] our technology unlocks. "
                             f"It keeps the government busy for #v {INQUIRY_MONTHS}#! months.",
        "spec_debt_converted": "Converted Debt",
        "spec_debt_converted_desc": "Our loans were converted to a lower rate while investors were eager to lend. "
                                    f"It ends once our debt falls below #v {CONVERT_DEBT:.0%}#! of our [concept_credit] limit.",
        "spec_relief_works": "Relief Works",
        "spec_relief_works_desc": "Public works and relief are provided for those the slump has thrown out of work.",
        "spec_relief_costs": "Relief Works Costs",
        "spec_relief_costs_desc": "The treasury bears the cost of public works and relief.",
        "spec_act_suspended": "Bank Act Suspended",
        "spec_act_suspended_desc": "The government has set aside its own law to end a panic.",
        "spec_inquiry_sitting": "Commission of Inquiry",
        "spec_inquiry_sitting_desc": "A commission is hearing evidence on the conduct of our banks and companies.",
        "spec_sound_finance": "Sound Finance",
        "spec_sound_finance_desc": "Our currency, banks and companies are run by rules that investors trust.",
        **{key: name for key, _, _, name in IG_MODIFIERS},
        "spec_reform_currency_tt": f"Banks lend #v {1 - REFORMS['currency']['credit']:.0%}#! less, the {excess} grows "
                                   f"#v {1 - REFORMS['currency']['heat']:.0%}#! slower, and [Concept('concept_spec_financial_panic','$concept_spec_financial_panics$')] last #v {REFORMS['currency']['panic_len'] - 1:.0%}#! longer\\n"
                                   "You can suspend the Bank Act in a panic",
        "spec_reform_free_tt": f"Banks lend #v {REFORMS['free']['credit'] - 1:.0%}#! more, booms get #v {REFORMS['free']['boom'] - 1:.0%}#! bigger, and "
                               f"when they end they cost #v {REFORMS['free']['risk'] - 1:.0%}#! more {mc}",
        "spec_reform_llr_tt": f"#v Lend to the Banks#! costs #v {1 - REFORMS['llr']['rescue']:.0%}#! less and ends the panic #v {-REFORMS['llr']['rescue_months']}#! month sooner",
        "spec_reform_company_tt": f"When booms end, they cost #v {1 - REFORMS['company']['risk']:.0%}#! less {mc}",
        "spec_reform.1.t": "Commission of Inquiry",
        "spec_reform.1.d_panic": "The commission appointed after the panic has delivered its report in three volumes of testimony from "
                                 "bankers, brokers and ruined depositors. Its members agree that the panic was no act of God. On "
                                 "almost everything else they disagree, and each remedy has its champions in the chamber.",
        "spec_reform.1.d_calm": "With the markets quiet, a commission has spent the year hearing bankers, brokers and political "
                                "economists on how to keep the next boom from ending in ruin. Its report sets out several remedies, "
                                "and each has its champions in the chamber.",
        "spec_reform.1.f": "\"In wild periods of alarm, one failure makes many, and the best way to prevent the derivative failures is "
                           "to arrest the primary failure which causes them.\"",
        "spec_reform.1.a": "Bind the issue of notes to the gold in the vaults.",
        "spec_reform.1.b": "Let every sound bank issue its own notes.",
        "spec_reform.1.c": "Name a lender of last resort.",
        "spec_reform.1.d": "Make companies publish their accounts.",
        "spec_reform.1.e": "Thank the commission, and shelve its report.",
        "spec_reform.2.t": "Sound Finance",
        "spec_reform.2.d": "Our banks issue their notes by rule, a lender stands ready when panic strikes, and our companies must "
                           "show investors what they own and what they owe. Abroad, our bonds now sell at a premium, and "
                           "[ROOT.GetCountry.GetCapital.GetCityHubName] is spoken of as a safe harbor for capital.",
        "spec_reform.2.f": "\"A banker's first duty is not to make money but to keep it.\"",
        "spec_reform.2.a": "Confidence is the foundation of credit.",
    }
    return "".join(f' {key}: "{text}"\n' for key, text in lines.items())
