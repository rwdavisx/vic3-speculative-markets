"""Credit Policy politics: the AI's lasting credit temperament, and the interest groups that care about the stance.

Temperament (var:spec_temper): -1 Cautious, 0 Balanced, 1 Bold, rolled once per AI country from its ruler, heir
and economic system. It shifts every confidence threshold of the AI's stance rules and its odds of rescuing the banks.
Industrialists in government want Loose credit, Intelligentsia in government want Tight; the AI leans their way."""
import tuning

IG_APPROVAL = 2        # vanilla's strong law stance; under the opposite stance the same modifier applies at -1
PREFS = {"industrialists": 1, "intelligentsia": -1}   # interest group -> preferred stance
TEMPER_SHIFT = tuning.get("TEMPER_SHIFT", 8)       # confidence points a Bold (+) or Cautious (-) AI moves its thresholds by
# the AI's credit rule (1.3.1) watches its margin: confidence over the Panic Threshold, plus AI_MARGIN_LEAN of its lean.
# From AI_MARGIN_FROM months of leverage it goes Tight under AI_MARGIN and stays so until AI_MARGIN_BACK. It goes Loose
# over AI_MARGIN_LOOSE, while it is AI_LOOSE_ROOM months or more short of its leverage limit (leverage.AI_LIMIT)
AI_MARGIN, AI_MARGIN_BACK, AI_MARGIN_LOOSE = tuning.get("AI_MARGIN", 10), tuning.get("AI_MARGIN_BACK", 16), tuning.get("AI_MARGIN_LOOSE", 15)
AI_MARGIN_FROM, AI_MARGIN_LEAN, AI_LOOSE_ROOM = tuning.get("AI_MARGIN_FROM", 4), tuning.get("AI_MARGIN_LEAN", 0.6), tuning.get("AI_LOOSE_ROOM", 0.5)
IG_SHIFT = tuning.get("IG_SHIFT", 4)           # and each preferring interest group in government
RESCUE_BASE = tuning.get("RESCUE_CHANCE", {-1: 15, 0: 30, 1: 50})   # percent a month, once the panic has more than the rescue's months left
RESCUE_SCALE = tuning.get("RESCUE_SCALE", 1.0)  # the three chances moved as one (tuning.scaled)
RESCUE_CHANCE = tuning.scaled(RESCUE_BASE, RESCUE_SCALE, whole=True)
NAMES = {"industrialists": "Industrialists", "intelligentsia": "Intelligentsia"}

# temperament weights: base, then additions by ruler trait, heir trait and economic system law. TEMPER_TILT moves base
# weight from Cautious to Bold (negative: the other way)
TEMPER_TILT = tuning.get("TEMPER_TILT", 0)
TEMPERS = {
    -1: (30 - TEMPER_TILT, [("ruler ?= { has_trait = cautious }", 30), ("heir ?= { has_trait = cautious }", 10),
              ("has_law_or_variant = law_type:law_traditionalism", 20),
              ("has_law_or_variant = law_type:law_agrarianism", 20)]),
    0: (40, [("has_law_or_variant = law_type:law_interventionism", 20)]),
    1: (30 + TEMPER_TILT, [("ruler ?= { has_trait = reckless }", 30), ("ruler ?= { has_trait = ambitious }", 15),
             ("heir ?= { has_trait = reckless }", 10), ("has_law_or_variant = law_type:law_laissez_faire", 20)]),
}


def _weight(base, adds):
    mods = "".join(f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {t} }}\n\t\t\t\t\tadd = {n}\n\t\t\t\t}}\n" for t, n in adds)
    return f"\t\t{base} = {{\n\t\t\tmodifier = {{\n{mods}\t\t\t}}\n"


def _ig_mods(effect):
    return "".join(f"\tig:ig_{ig} ?= {{\n{effect(ig, pref)}\t}}\n" for ig, pref in PREFS.items())


def script(k):
    lean = (f"spec_ai_lean = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_temper }}\n"
            f"\t\tadd = {{\n\t\t\tvalue = var:spec_temper\n\t\t\tmultiply = {TEMPER_SHIFT}\n\t\t}}\n\t}}\n"
            + "".join(f"\tif = {{\n\t\tlimit = {{ ig:ig_{ig} ?= {{ is_in_government = yes }} }}\n\t\tadd = {pref * IG_SHIFT}\n\t}}\n"
                      for ig, pref in PREFS.items()) + "}")
    # when the AI starts and stops encouraging Calm goods (levers.py): it stops from at most CONF_START - 1, above the
    # highest starting point, WARY + TEMPER_SHIFT + IG_SHIFT
    at = {"loose": tuning.get("AI_LOOSE", k["WARY"]), "unloose": k["CREDIT_FROM"]}
    clamp = {"unloose": f"\tmax = {k['CONF_START'] - 1}\n"}
    assert AI_MARGIN < AI_MARGIN_BACK, "the AI would tighten and loosen in turn"
    values = [lean] + [f"spec_ai_{n}_at = {{\n\tvalue = {v}\n\tadd = spec_ai_lean\n{clamp.get(n, '')}}}" for n, v in at.items()]
    values += [f"spec_ai_margin = {{\n\tvalue = spec_ai_lean\n\tmultiply = {AI_MARGIN_LEAN}\n\tadd = var:spec_conf\n\tsubtract = spec_panic_at\n}}",
               f"spec_ai_loose_lev = {{\n\tvalue = spec_ai_lev_limit\n\tsubtract = {AI_LOOSE_ROOM}\n}}"]

    picks = "".join(_weight(base, adds) + f"\t\t\tset_variable = {{ name = spec_temper value = {t} }}\n\t\t}}\n"
                    for t, (base, adds) in TEMPERS.items())
    rescue_adds = [(f"var:spec_temper = {t}", c - RESCUE_CHANCE[0]) for t, c in RESCUE_CHANCE.items() if t]
    # random_list entries are relative weights. Keep both branches summing to
    # 100 so RESCUE_CHANCE remains a percentage for every temperament.
    skip_adds = [(trigger, -delta) for trigger, delta in rescue_adds]
    clear = lambda ig, pref: "".join(f"\t\tif = {{\n\t\t\tlimit = {{ has_modifier = spec_{s}_credit }}\n\t\t\tremove_modifier = spec_{s}_credit\n\t\t}}\n"
                                     for s in ("loose", "tight"))
    add = lambda n, s: lambda ig, pref: (f"\t\tif = {{\n\t\t\tlimit = {{ is_in_government = yes }}\n"
                                         f"\t\t\tadd_modifier = {{ name = spec_{s}_credit{'' if pref == n else ' multiplier = -1'} }}\n\t\t}}\n")
    # under stance n, an interest group in government without the stance's modifier, or out of it with it
    stale = lambda n, s: (f"\t\t\t\tAND = {{\n\t\t\t\t\tspec_stance_value = {n}\n\t\t\t\t\tOR = {{\n"
                          + "".join(f"\t\t\t\t\t\tig:ig_{ig} ?= {{ is_in_government = yes NOT = {{ has_modifier = spec_{s}_credit }} }}\n"
                                    f"\t\t\t\t\t\tig:ig_{ig} ?= {{ is_in_government = no has_modifier = spec_{s}_credit }}\n" for ig in PREFS)
                          + "\t\t\t\t\t}\n\t\t\t\t}\n")
    effects = f"""# once per AI country, kept until the market economy is left
spec_ai_temper = {{
	if = {{
		limit = {{ NOT = {{ has_variable = spec_temper }} }}
	random_list = {{
{picks}	}}
	}}
}}

# the AI's monthly chance to lend to the banks, by temperament
spec_ai_rescue_roll = {{
	random_list = {{
{_weight(RESCUE_CHANCE[0], rescue_adds)}			spec_rescue = yes
		}}
{_weight(100 - RESCUE_CHANCE[0], skip_adds)}		}}
	}}
}}

spec_remove_credit_igs = {{
{_ig_mods(clear)}}}

# from a stance change, and from spec_refresh_credit_igs when the government changes
spec_update_credit_igs = {{
	spec_remove_credit_igs = yes
	if = {{
		limit = {{ spec_stance_value = 1 }}
{_ig_mods(add(1, 'loose'))}	}}
	else_if = {{
		limit = {{ spec_stance_value = -1 }}
{_ig_mods(add(-1, 'tight'))}	}}
}}

# monthly: only when an interest group has entered or left the government since the modifiers were set
spec_refresh_credit_igs = {{
	if = {{
		limit = {{
			OR = {{
{stale(1, 'loose')}{stale(-1, 'tight')}			}}
		}}
		spec_update_credit_igs = yes
	}}
}}
"""
    return {"common/script_values/spec_credit_ai_values.txt": "\n\n".join(values) + "\n",
            "common/scripted_effects/spec_credit_ai_effects.txt": effects}


# the AI's monthly choice of Credit Policy, for generate.monthly. A Mania fever (leverage.FEVER) keeps it from tightening
_EXIT = f"""spec_stance_value = -1
spec_lev < spec_ai_lev_limit
NOT = {{ has_variable = spec_crunch }}
OR = {{
	spec_lev < {AI_MARGIN_FROM}
	spec_ai_margin >= {AI_MARGIN_BACK}
}}"""
_LOOSE = f"""spec_ai_margin > {AI_MARGIN_LOOSE}
spec_lev < spec_ai_loose_lev
NOT = {{ has_variable = spec_panic }}"""


def _tabs(text, n):
    return "\n".join("\t" * n + line for line in text.split("\n"))


def _choice(word, limit, stance):
    return f"\t\t\t\t{word} = {{\n\t\t\t\t\tlimit = {{\n{_tabs(limit, 6)}\n\t\t\t\t\t\tspec_can_stance_{stance} = yes\n\t\t\t\t\t}}\n\t\t\t\t\tspec_stance_to_{stance} = yes\n\t\t\t\t}}\n"


STANCE = (
    _choice("if", f"""OR = {{
	spec_lev >= spec_ai_lev_limit
	has_variable = spec_crunch
	AND = {{
		spec_lev >= {AI_MARGIN_FROM}
		spec_ai_margin < {AI_MARGIN}
	}}
}}
NOT = {{ has_variable = spec_ai_fever }}
NOT = {{ spec_stance_value = -1 }}""", "tight")
    + _choice("else_if", f"""OR = {{
	spec_stance_value = 0
	AND = {{
{_tabs(_EXIT, 2)}
	}}
}}
{_LOOSE}""", "loose")
    + _choice("else_if", _EXIT, "normal")
    + _choice("else_if", f"""spec_stance_value = 1
NOT = {{
	AND = {{
{_tabs(_LOOSE, 2)}
	}}
}}""", "normal"))


def ig_lines(stance):
    """Tooltip lines for a stance's button: who approves, who disapproves, like a law's supporters."""
    n = {"loose": 1, "tight": -1}[stance]
    yes = [ig for ig, p in PREFS.items() if p == n]
    no = [ig for ig, p in PREFS.items() if p == -n]
    return "\\n".join([f"@{ig}! {NAMES[ig]} [concept_in_government]: #P +{IG_APPROVAL}#! [concept_approval]" for ig in yes]
                      + [f"@{ig}! {NAMES[ig]} [concept_in_government]: #N -{IG_APPROVAL}#! [concept_approval]" for ig in no])


if __name__ == "__main__":
    k = {"MANIA": 80, "MANIA_RESET": 65, "WARY": 40, "CREDIT_FROM": 60, "CONF_START": 55}
    out = script(k)
    fx = out["common/scripted_effects/spec_credit_ai_effects.txt"]
    assert fx.count("{") == fx.count("}"), "unbalanced effects"
    v = out["common/script_values/spec_credit_ai_values.txt"]
    assert "\tmax = 54\n" in v and "spec_ai_margin = {" in v
    assert STANCE.count("{") == STANCE.count("}") and "{{" not in STANCE, "unbalanced STANCE"
    assert k["WARY"] + TEMPER_SHIFT + IG_SHIFT < k["CONF_START"] - 1, "the highest loosen point must stay below the unloose cap"
    assert "ig:ig_intelligentsia ?= { is_in_government = no has_modifier = spec_tight_credit }" in fx
    assert "spec_tight_credit multiplier = -1" in fx and "spec_loose_credit multiplier = -1" in fx
    assert ig_lines("loose").startswith("@industrialists! Industrialists") and "Intelligentsia" in ig_lines("loose")
    print(fx)
