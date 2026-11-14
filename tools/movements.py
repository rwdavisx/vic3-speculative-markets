"""Panics and manias move vanilla political movements, through timed decaying country modifiers on
state_pop_support_movement_<x>_mult, the way vanilla events nudge them (modifier_resurgent_labor_movement)."""

# after a panic, the movements whose core ideology wants the state to run or rein in the economy
# (Interventionism, Command Economy, Cooperative Ownership, Regulatory Bodies) gain support
PANIC = {"labor": 0.2, "socialist": 0.1, "communist": 0.1, "corporatist": 0.1, "bonapartist": 0.1}
# after a long or large mania, Laissez Faire's one vanilla backer gains and those against it lose
MANIA = {"orleanist": 0.15, "labor": -0.1, "socialist": -0.1}
DAYS = "normal_modifier_time"   # 5 years, decaying, as vanilla's modifier_corporatist_consolidation
HEAT_BASE = 70                  # each mania month at or above MANIA adds confidence minus this
HEAT = 120                      # 12 months at 80, 6 at 90, 4 at 100


def state_vars():
    return ["spec_mania_heat"]


def _mod(name, icon, support):
    lines = "".join(f"\tstate_pop_support_movement_{m}_mult = {v:g}\n" for m, v in support.items())
    return f"{name} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/{icon}.dds\n{lines}}}\n"


def _add(name, depth=1):
    """Re-adds the timed modifier so it restarts at full strength."""
    lines = ["if = {", f"\tlimit = {{ has_modifier = {name} }}", f"\tremove_modifier = {name}", "}",
             "add_modifier = {", f"\tname = {name}", f"\tdays = {DAYS}", "\tis_decaying = yes", "}"]
    return "".join("\t" * depth + line + "\n" for line in lines)


def script(k):
    effects = f"""# from spec_start_panic: the crash turns people against the free market, and ends any mania's goodwill
spec_panic_movements = {{
	if = {{
		limit = {{ has_modifier = spec_mania_movements }}
		remove_modifier = spec_mania_movements
	}}
{_add("spec_panic_movements")}}}

# monthly: a mania that runs long or high builds heat, and enough of it wins the free market friends
spec_update_movements = {{
	if = {{
		limit = {{
			has_variable = spec_mania
			var:spec_conf >= {k['MANIA']}
		}}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_mania_heat }} }}
			set_variable = {{ name = spec_mania_heat value = 0 }}
		}}
		change_variable = {{ name = spec_mania_heat add = {{ value = var:spec_conf subtract = {HEAT_BASE} }} }}
		# heat starts over, so a mania that keeps going renews it
		if = {{
			limit = {{ var:spec_mania_heat >= {HEAT} }}
{_add("spec_mania_movements", 3)}			remove_variable = spec_mania_heat
		}}
	}}
	else_if = {{
		limit = {{
			NOT = {{ has_variable = spec_mania }}
			has_variable = spec_mania_heat
		}}
		remove_variable = spec_mania_heat
	}}
}}
"""
    mods = (_mod("spec_panic_movements", "modifier_fist_negative", PANIC) + "\n"
            + _mod("spec_mania_movements", "modifier_statue_positive", MANIA))
    return {"common/scripted_effects/spec_movements_effects.txt": effects,
            "common/static_modifiers/spec_movements_modifiers.txt": mods}


LF = "[GetLawType('law_laissez_faire').GetName]"
MOVEMENTS = "[Concept('concept_political_movement','$concept_political_movements$')]"
# appended to the panic and mania event texts and the two concepts
PANIC_LINE = f"Many now want the state to rein in the markets, and {MOVEMENTS} against {LF} gain support."
MANIA_LINE = f"If it lasts, {MOVEMENTS} that favor {LF} will gain support."


def loc():
    return (' spec_panic_movements: "Distrust of the Markets"\n'
            f' spec_panic_movements_desc: "After the panic, many want the state to rein in the markets. {MOVEMENTS} against {LF} gain support. This fades over time."\n'
            ' spec_mania_movements: "Faith in the Markets"\n'
            f' spec_mania_movements_desc: "A long boom has convinced many that the markets are best left alone. {MOVEMENTS} that favor {LF} gain support. This fades over time."\n')


if __name__ == "__main__":
    out = script({"MANIA": 80})
    eff = out["common/scripted_effects/spec_movements_effects.txt"]
    assert eff.count("{") == eff.count("}"), "unbalanced braces"
    assert "is_decaying = yes" in eff and "spec_mania_heat >= 120" in eff
    print(eff)
