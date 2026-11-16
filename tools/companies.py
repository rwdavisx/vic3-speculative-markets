"""Companies and Financial Districts.

Vanilla gives script no way to change a company's prosperity: no effect sets it, companies take no modifiers, and no
modifier type targets it. Prosperity's target rises with the productivity of the company's buildings against the world
average, so the closest lever is throughput. Investor interest in a good (var:spec_word_<g>) sets the throughput of the
buildings making it in every country, INTEREST_THROUGHPUT: a building modifier per good and tier, spec_investor_<g>_<tier>,
on each such building (building_throughput_add, as vanilla's event modifiers on buildings, agitators_4_modifiers.txt:765),
so it shows in the building's panel and not in the country's list. Each month a country's buildings of those types swap
theirs only where the tier changed or the building is new; Calm has none. Older saves' country modifiers,
spec_investor_<g> with var:spec_tier_<g>, are removed on the first update. When a boom ends, and the country has a company whose building types make the good, that industry's buildings
lose some more: a Correction a quarter of COMPANY_BUST for 3 months, a Bust half for 6, a Collapse all of it for a year.
Corporate Charters and Corporate Management each strengthen that glut. A panic cuts country_company_throughput_bonus_add,
the bonus every company adds to its own buildings. These add to the interventions' own throughput (levers.KINDS).
ponytail: the throughput reaches every building of the type in the country, not only company ones; script cannot tell
a company's buildings apart.

The company buildings' profits are what their headquarters earn, so these modifiers reach the HQ too. Headquarters and
Financial Districts make no goods (vanilla production_methods/14_companies.txt, 11_private_infrastructure.txt:454-505),
and the game does not create a throughput modifier type for them (docs/modifiers.log lists both only as potential types).

Financial Districts: Speculative Mania raises the Standard of Living of their employees and a panic lowers it, through
the building group modifier, which this file defines as vanilla defines building_group_bg_manor_houses_aristocrats_
standard_of_living_add (modifier_type_definitions/01_building_modifier_types.txt:239), for the same potential type.
Their investment already moves with the bands (generate.BAND_INVEST).

generate.py writes script(sells, upgrades), runs crash(g, sev) where a good's boom ends, adds band(t) to each confidence
band modifier and PANIC to the panic modifier, and calls spec_update_companies monthly and on shut down."""
import functools
import re

import icons
import tuning
import mod_sources

# interest word (1 Fleeing to 6 Feverish) -> throughput of the good's buildings, in percent
INTEREST_THROUGHPUT = tuning.get("INTEREST_THROUGHPUT", {1: -10, 2: -5, 3: 0, 4: 3, 5: 5, 6: 8})
COMPANY_BUST = tuning.get("COMPANY_BUST", -0.1)      # after a good's boom collapses, for BUST_DAYS
# blue chips (design_companies.md): a company at BLUE_PROSPER+ for BLUE_MONTHS months running earns the status; below it
# for BLUE_LOSE months running loses it, and the count starts again. Counted on the company (companies keep variables:
# runs/sweep_company_vars_probe_r1). Each one adds BLUE_BONUS to Home of Great Companies' Company Strength (centres.py)
BLUE_PROSPER = tuning.get("BLUE_PROSPER", 70)
BLUE_MONTHS = tuning.get("BLUE_MONTHS", 12)  # beta.12: was 24; only 3-5 in the world by 1846 (runs/20261116_104250_calib_b_1846)
BLUE_LOSE = tuning.get("BLUE_LOSE", 3)
BLUE_BONUS = tuning.get("BLUE_BONUS", 2)
# beta.12 (bluechips.py): the loop also counts them (local spec_bc_cnt), flags a new one (spec_bc_new) and a first month
# below the mark (spec_bc_wobble) for the events, skips the low months while propped up (spec_bc_propped), and drops a
# fragile one (spec_bc_fragile, from issuing shares) at its first low month; bluechips.after_update acts on the flags
BLUE_UPDATE = f"""		set_local_variable = {{ name = spec_nx_bc value = spec_nx_blue }}
		set_local_variable = {{ name = spec_bc_cnt value = 0 }}
		every_company = {{
			if = {{
				limit = {{ prosperity >= {BLUE_PROSPER:g} }}
				remove_variable = spec_bc_low
				if = {{
					limit = {{ NOT = {{ has_variable = spec_blue_chip }} }}
					if = {{
						limit = {{ NOT = {{ has_variable = spec_bc_months }} }}
						set_variable = {{ name = spec_bc_months value = 0 }}
					}}
					change_variable = {{ name = spec_bc_months add = local_var:spec_nx_bc }}
					if = {{
						limit = {{ var:spec_bc_months >= {BLUE_MONTHS:g} }}
						set_variable = spec_blue_chip
						remove_variable = spec_bc_months
						set_variable = {{ name = spec_bc_new days = 60 }}
						set_local_variable = {{ name = spec_bc_gained value = 1 }}
					}}
				}}
			}}
			else = {{
				remove_variable = spec_bc_months
				if = {{
					limit = {{
						has_variable = spec_blue_chip
						NOT = {{ has_variable = spec_bc_propped }}
					}}
					if = {{
						limit = {{ NOT = {{ has_variable = spec_bc_low }} }}
						set_variable = {{ name = spec_bc_low value = 0 }}
					}}
					change_variable = {{ name = spec_bc_low add = 1 }}
					if = {{
						limit = {{
							OR = {{
								var:spec_bc_low >= {BLUE_LOSE:g}
								has_variable = spec_bc_fragile
							}}
						}}
						remove_variable = spec_blue_chip
						remove_variable = spec_bc_low
						remove_variable = spec_bc_wobble
						if = {{
							limit = {{ NOT = {{ has_local_variable = spec_bc_fell }} }}
							set_local_variable = {{ name = spec_bc_fell value = 0 }}
						}}
						change_local_variable = {{ name = spec_bc_fell add = 1 }}
					}}
					else_if = {{
						limit = {{ var:spec_bc_low = 1 }}
						set_variable = {{ name = spec_bc_wobble days = 60 }}
						set_local_variable = {{ name = spec_bc_wobbled value = 1 }}
					}}
				}}
			}}
			if = {{
				limit = {{ has_variable = spec_blue_chip }}
				change_local_variable = {{ name = spec_bc_cnt add = 1 }}
			}}
		}}
{__import__("bluechips").after_update()}"""
# a closed market keeps no blue chips: the count starts again when it reopens
BLUE_CLEAR = ("\t\tevery_company = {\n\t\t\tremove_variable = spec_blue_chip\n\t\t\tremove_variable = spec_bc_months\n"
              "\t\t\tremove_variable = spec_bc_low\n\t\t\tremove_variable = spec_bc_fragile\n\t\t\tremove_variable = spec_bc_propped\n\t\t}\n"
              "\t\tremove_variable = spec_bc_n\n\t\tif = {\n\t\t\tlimit = { has_modifier = spec_bc_index }\n\t\t\tremove_modifier = spec_bc_index\n\t\t}\n")
BUST_DAYS = 365
# severity of the boom's end (generate.UNWINDS) -> share of COMPANY_BUST, days
UNWIND = {3: (1, BUST_DAYS), 2: (0.5, 180), 1: (0.25, 90)}
TIE_TECHS = ("corporate_charters", "corporate_management")
TIE_PER_TECH = 0.25      # each tech multiplies both by this much more
PANIC_COMPANY = -0.05    # company throughput bonus in a panic; vanilla's base is +0.1, a rescue halves this
# the game logs these as unknown modifier types: resource buildings with no throughput modifier
NO_THROUGHPUT = {"logging_camp", "oil_rig", "banana_plantation"}
COMPANY_DIR = "common/company_types"
FD_SOL = "building_group_bg_financial_districts_standard_of_living_add"
FD_MANIA, FD_PANIC = 1, -2   # Standard of Living of Financial District employees; a rescue halves the panic's
FD_BANDS = {"mania": FD_MANIA}

PANIC = f"\tcountry_company_throughput_bonus_add = {PANIC_COMPANY:g}\n\t{FD_SOL} = {FD_PANIC:g}\n"


def band(t):
    return f"\t{FD_SOL} = {FD_BANDS[t]:g}\n" if t in FD_BANDS else ""


def band_tip(t):
    return f"\\n${FD_SOL}$: #P +{FD_BANDS[t]:g}#!" if t in FD_BANDS else ""


@functools.cache
def _companies(game):
    """company type -> its building types, from vanilla."""
    out = {}
    for f in mod_sources.files(game, COMPANY_DIR):
        for m in re.finditer(r"^(\w+)\s*=\s*\{(.*?)^\}", f.read_text(encoding="utf-8-sig"), re.M | re.S):
            bt = re.search(r"\n\tbuilding_types\s*=\s*\{([^}]*)\}", m.group(2))
            if bt:
                out[m.group(1)] = bt.group(1).split()
    return out


def _industry(sells, upgrades):
    """good -> the buildings making it."""
    out = {}
    for m in sells.values():
        for b, g in m.items():
            if b not in NO_THROUGHPUT:
                out.setdefault(g, []).append(b)
    for b, ups in upgrades.items():
        for g, _ in ups:
            if b not in NO_THROUGHPUT:
                out.setdefault(g, []).append(b)
    return out


# for the Companies section (company_section.py): global variable BT_SLOT.format(n) + building type key -> the n-th good
# its buildings make, the main good first; the GUI has no way from a building type to its goods.
# ponytail: set once under BT_MAP; bump its number when the mapping changes (a dropped slot would stay set)
BT_MAP = "spec_bt_map_1"
if mod_sources.MR:
    BT_MAP = "spec_bt_map_morgenroete_1"  # populate extra building mappings in existing saves too
BT_SLOT = "spec_bt_g{}_"
BT_SLOTS = 3  # the most goods one building type makes (automotive industry)


def building_goods(sells, upgrades):
    """building -> the goods with a throughput modifier on it, main good first."""
    out = {b: [g] for m in sells.values() for b, g in m.items() if b not in NO_THROUGHPUT}
    for b, ups in upgrades.items():
        if b in out:
            out[b] += [g for g, _ in ups]
    return out


_GOODS = {}     # good -> trigger: the country has a company making it
_INDUSTRY = {}  # good -> its buildings, for loc()
LEGACY = "spec_company_boom_{}"  # older saves' boom modifier per good: kept empty, removed on the first update
SWEEP = 3  # months between building passes when no tier changed, for buildings built since
ON = "spec_investor_on"  # a country whose buildings carry interest modifiers, so shutting down clears them once
LEGACY_DONE = "spec_legacy_done"  # set once older saves' empty modifiers are gone
TIER_WORDS = {1: "fleeing", 2: "doubtful", 3: "calm", 4: "keen", 5: "eager", 6: "feverish"}


def _gate(game, buildings):
    types = sorted(c for c, bts in _companies(game).items() if any(f"building_{b}" in bts for b in buildings))
    return "any_company = { OR = { " + " ".join(f"is_company_type = company_type:{c}" for c in types) + " } }" if types else ""


def crash(g, sev=3):
    """Lines run where the boom in g ends with severity sev. A Collapse replaces the glut modifier; a milder end
    leaves one already running alone."""
    gate = _GOODS.get(g)
    if not gate:
        return ""
    m = f"spec_company_bust_{g}"
    if sev == 3:
        head = (f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {gate} }}\n"
                f"\t\t\t\t\tif = {{\n\t\t\t\t\t\tlimit = {{ has_modifier = {m} }}\n\t\t\t\t\t\tremove_modifier = {m}\n\t\t\t\t\t}}\n")
    else:
        head = f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{\n\t\t\t\t\t\t{gate}\n\t\t\t\t\t\tNOT = {{ has_modifier = {m} }}\n\t\t\t\t\t}}\n"
    tie = "spec_company_tie" if sev == 3 else f"spec_company_tie_{sev}"
    return (head + f"\t\t\t\t\tadd_modifier = {{\n\t\t\t\t\t\tname = {m}\n\t\t\t\t\t\tdays = {UNWIND[sev][1]}\n"
            f"\t\t\t\t\t\tmultiplier = {tie}\n\t\t\t\t\t}}\n\t\t\t\t}}\n")


def script(game, sells, upgrades, icon):
    """{mod path: text}; icon(name) gives a vanilla timed modifier icon path."""
    industry = _industry(sells, upgrades)
    _GOODS.clear()
    _GOODS.update({g: gate for g, bs in industry.items() if (gate := _gate(game, bs))})
    _INDUSTRY.clear()
    _INDUSTRY.update(industry)
    rm = lambda m, t: f"{t}if = {{\n{t}\tlimit = {{ has_modifier = {m} }}\n{t}\tremove_modifier = {m}\n{t}}}\n"
    mods, update, clear, legacy_update = [], [], [], []
    for g in sorted(_GOODS):
        bust = f"spec_company_bust_{g}"
        mods.append(f"{bust} = {{\n\ticon = {icon('modifier_gear_negative')}\n"
                    + "".join(f"\tbuilding_{b}_throughput_add = {COMPANY_BUST:g}\n" for b in industry[g]) + "}\n")
        mods.append(f"{LEGACY.format(g)} = {{\n\ticon = {icon('modifier_gear_positive')}\n}}\n")
        clear.append(rm(bust, "\t\t"))
    tiers = [(k, p) for k, p in INTEREST_THROUGHPUT.items() if p]
    bm = lambda g, k: f"spec_investor_{g}_{k}"
    makers = {}  # building type -> the goods it makes
    for g in sorted(industry):
        for b in industry[g]:
            makers.setdefault(b, []).append(g)
        m, t = f"spec_investor_{g}", f"spec_tier_{g}"
        # older saves' country modifier, now empty: removed with its tier variable on the first update
        mods.append(f"{m} = {{\n\ticon = {icons.path('interest_calm')}\n}}\n")
        mods += [f"{bm(g, k)} = {{\n\ticon = {icons.path('interest_' + TIER_WORDS[k])}\n\tbuilding_throughput_add = {p / 100:g}\n}}\n"
                 for k, p in tiers]
        legacy = rm(LEGACY.format(g), "\t\t\t") if g in _GOODS else ""
        # ponytail: the old var:spec_tier_<g> is no longer named (the game logs a never-set variable it sees removed);
        # older saves keep it, unused. The empty modifiers go once, on the first update (LEGACY_DONE)
        old = rm(m, "\t\t\t") + legacy
        legacy_update.append(old)
        clear.append(old.replace("\t\t\t", "\t\t"))

    def apply(g, tab):
        """In a building's scope: the modifier for its owner's tier in g, the others gone; none at Calm."""
        out = "".join(f"{tab}if = {{\n{tab}\tlimit = {{\n{tab}\t\towner = {{ var:spec_word_{g} = {k} }}\n"
                      f"{tab}\t\tNOT = {{ has_modifier = {bm(g, k)} }}\n{tab}\t}}\n"
                      + "".join(rm(bm(g, u), tab + "\t") for u, _ in tiers if u != k)
                      + f"{tab}\tadd_modifier = {{ name = {bm(g, k)} }}\n{tab}}}\n" for k, _ in tiers)
        still = " ".join(f"var:spec_word_{g} = {k}" for k, _ in tiers)
        return out + (f"{tab}if = {{\n{tab}\tlimit = {{ owner = {{ NOR = {{ {still} }} }} }}\n"
                      + "".join(rm(bm(g, u), tab + "\t") for u, _ in tiers) + f"{tab}}}\n")

    types = sorted(makers)
    is_type = "\t\t\tlimit = { OR = { " + " ".join(f"is_building_type = building_{b}" for b in types) + " } }\n"
    # the building pass runs on the first update, when a tier differs from the one last applied (var:spec_ia_<g>), and
    # every SWEEP months for buildings built since; otherwise a country's buildings are not visited. Outside a sweep it
    # touches only the goods whose tier changed (local_var:spec_iat_<g> = 1). The type chain is the only type check: an
    # OR of every type in front of it tested each building's type twice
    goods = sorted(industry)
    # a good added since the save (electricity in 0.9) has no spec_ia_<g> yet: that counts as changed, unread
    changed = " ".join(f"NOT = {{ has_variable = spec_ia_{g} }} NOT = {{ var:spec_ia_{g} = var:spec_word_{g} }}" for g in goods)
    sweep = (f"\t\tset_local_variable = {{ name = spec_ia_all value = 0 }}\n\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\tOR = {{\n"
             f"\t\t\t\t\tNOT = {{ has_variable = {ON} }}\n\t\t\t\t\tvar:spec_ia_n >= {SWEEP}\n\t\t\t\t}}\n\t\t\t}}\n"
             "\t\t\tset_local_variable = { name = spec_ia_all value = 1 }\n\t\t}\n")
    todo = "".join(f"\t\t\tset_local_variable = {{ name = spec_iat_{g} value = local_var:spec_ia_all }}\n"
                   f"\t\t\tif = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\tlocal_var:spec_ia_all = 0\n"
                   f"\t\t\t\t\tOR = {{\n\t\t\t\t\t\tNOT = {{ has_variable = spec_ia_{g} }}\n\t\t\t\t\t\tNOT = {{ var:spec_ia_{g} = var:spec_word_{g} }}\n\t\t\t\t\t}}\n\t\t\t\t}}\n"
                   f"\t\t\t\tset_local_variable = {{ name = spec_iat_{g} value = 1 }}\n\t\t\t}}\n" for g in goods)
    only = lambda g: (f"\t\t\t\t\tif = {{\n\t\t\t\t\t\tlimit = {{ local_var:spec_iat_{g} = 1 }}\n"
                      + apply(g, "\t\t\t\t\t\t") + "\t\t\t\t\t}\n")
    passes = "".join(f"\t\t\t\t{'if' if i == 0 else 'else_if'} = {{\n\t\t\t\t\tlimit = {{ is_building_type = building_{b} }}\n"
                     + "".join(only(g) for g in makers[b]) + "\t\t\t\t}\n" for i, b in enumerate(types))
    # a differential pass (most months: a few goods changed) looks up each changed good's building types in each state
    # (one building per type and state) instead of testing every building against the whole type chain
    direct = "".join(f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ OR = {{ "
                     + " ".join(f"local_var:spec_iat_{g} = 1" for g in makers[b])
                     + f" }} }}\n\t\t\t\t\tevery_scope_state = {{\n\t\t\t\t\t\tb:building_{b} ?= {{\n"
                     + "".join(only(g) for g in makers[b])  # ponytail: inner blocks keep the chain's indent
                     + "\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n" for b in types)
    update.append(f"\t\tif = {{\n\t\t\tlimit = {{ NOT = {{ has_variable = {LEGACY_DONE} }} }}\n{''.join(legacy_update)}"
                  f"\t\t\tset_variable = {LEGACY_DONE}\n\t\t}}\n")
    update.append(f"\t\tif = {{\n\t\t\tlimit = {{ NOT = {{ has_variable = spec_ia_n }} }}\n\t\t\tset_variable = {{ name = spec_ia_n value = 0 }}\n\t\t}}\n"
                  "\t\tchange_variable = { name = spec_ia_n add = 1 }\n" + sweep
                  + f"\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\tOR = {{\n\t\t\t\t\tNOT = {{ has_variable = {ON} }}\n"
                  f"\t\t\t\t\tvar:spec_ia_n >= {SWEEP}\n\t\t\t\t\t{changed}\n\t\t\t\t}}\n\t\t\t}}\n"
                  f"\t\t\tset_variable = {{ name = {ON} value = 1 }}\n"
                  # Differential passes visit only changed goods. Resetting the sweep clock on those passes lets
                  # frequent changes in one good starve new/conquered buildings of every other good indefinitely.
                  "\t\t\tif = {\n\t\t\t\tlimit = { local_var:spec_ia_all = 1 }\n"
                  "\t\t\t\tset_variable = { name = spec_ia_n value = 0 }\n\t\t\t}\n" + todo
                  + "".join(f"\t\t\tset_variable = {{ name = spec_ia_{g} value = var:spec_word_{g} }}\n" for g in goods)
                  + "\t\t\tif = {\n\t\t\t\tlimit = { local_var:spec_ia_all = 1 }\n\t\t\t\tevery_scope_building = {\n" + passes
                  + "\t\t\t\t}\n\t\t\t}\n\t\t\telse = {\n" + direct + "\t\t\t}\n\t\t}\n")
    clear.append(f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = {ON} }}\n\t\t\tremove_variable = {ON}\n\t\t\tremove_variable = spec_ia_n\n"
                 + "".join(f"\t\t\tremove_variable = spec_ia_{g}\n" for g in goods)
                 + "\t\t\tevery_scope_building = {\n\t" + is_type
                 + "".join(rm(bm(g, k), "\t\t\t\t") for g in goods for k, _ in tiers) + "\t\t\t}\n\t\t}\n")
    bg = building_goods(sells, upgrades)
    assert max(map(len, bg.values())) <= BT_SLOTS
    # the map is read only by the tab's GUI, which the game does not count: one script read keeps it from logging every
    # slot as set but never used, each time scripts load
    bt_read = ("\tif = {\n\t\tlimit = {\n\t\t\talways = no\n"
               + "".join(f"\t\t\texists = global_var:{BT_SLOT.format(i + 1)}building_{b}\n"
                         for b, gs in sorted(bg.items()) for i, _ in enumerate(gs)) + "\t\t}\n\t}\n")
    bt_map = bt_read + (f"\tif = {{\n\t\tlimit = {{ NOT = {{ has_global_variable = {BT_MAP} }} }}\n"
              f"\t\tset_global_variable = {{ name = {BT_MAP} value = 1 }}\n"
              + "".join(f"\t\tset_global_variable = {{ name = {BT_SLOT.format(i + 1)}building_{b} value = g:{g} }}\n"
                        for b, gs in sorted(bg.items()) for i, g in enumerate(gs)) + "\t}\n")
    tie ="".join(f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n\t\tadd = {TIE_PER_TECH:g}\n\t}}\n" for t in TIE_TECHS)
    return {
        "common/static_modifiers/spec_company_modifiers.txt":
            "# a good's buildings by investor interest in it, added with the tier's percent as the multiplier; for a while\n"
            "# after its boom ends, added with spec_company_tie; and the old boom modifiers, kept empty for older saves\n"
            + "\n".join(mods),
        "common/script_values/spec_company_values.txt": f"spec_company_tie = {{\n\tvalue = 1\n{tie}}}\n" + "".join(
            f"spec_company_tie_{sev} = {{\n\tvalue = spec_company_tie\n\tmultiply = {share:g}\n}}\n"
            for sev, (share, _) in UNWIND.items() if sev != 3),
        "common/scripted_effects/spec_company_effects.txt":
            "# monthly, after the interest words are set: each good's interest modifier, changed only when its tier did;\n"
            "# on shut down: every modifier here goes; once: the goods of each building type, for the tab\n"
            f"spec_update_companies = {{\n{bt_map}\tif = {{\n\t\tlimit = {{ has_variable = spec_conf }}\n{''.join(update)}{BLUE_UPDATE}\t}}\n"
            f"\telse = {{\n{''.join(clear)}{BLUE_CLEAR}\t}}\n}}\n",
        # as vanilla's building_group_bg_service_standard_of_living_add (01_building_modifier_types.txt:497)
        "common/modifier_type_definitions/spec_modifier_types.txt":
            f"{FD_SOL} = {{\n\tdecimals = 1\n\tcolor = good\n\tgame_data = {{\n\t\tai_value = 0\n\t}}\n}}\n",
    }


def loc():
    companies = "[Concept('concept_company','$concept_companies$')]"
    names = "".join(f' {LEGACY.format(g)}: "${g}$ Boom"\n spec_company_bust_{g}: "${g}$ Recovering"\n'
                    f' spec_company_bust_{g}_desc: "The ${g}$ boom has ended, leaving the industry with more works than its buyers need. Until it recovers, buildings making ${g}$ lose [concept_throughput] and the {companies} that own them earn less."\n'
                    for g in sorted(_GOODS))
    desc = lambda g: f"Buildings making ${g}$ gain [concept_throughput] while [concept_spec_investor_interest] in it is high, and lose it while interest is low."
    names += "".join(f' spec_investor_{g}{k}: "Investor Interest in ${g}$"\n spec_investor_{g}{k}_desc: "{desc(g)}"\n'
                     for g in sorted(_INDUSTRY) for k in [""] + [f"_{t}" for t, p in INTEREST_THROUGHPUT.items() if p])
    # worded as vanilla's building_group_bg_service_standard_of_living_add (modifiers_l_english.yml:1609)
    return names + (f' {FD_SOL}: "Financial District Employee [concept_sol]"\n'
                    f' {FD_SOL}_desc: "A bonus or penalty to the [concept_sol] of employees in Financial Districts"\n')


if __name__ == "__main__":
    from pathlib import Path
    game = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game")
    out = script(game, {"x": {"steel_mill": "steel", "glassworks": "glass"}}, {"steel_mill": [("tanks", "t")]}, str)
    mods, fx = out["common/static_modifiers/spec_company_modifiers.txt"], out["common/scripted_effects/spec_company_effects.txt"]
    assert "spec_investor_steel_1 = {" in mods and "building_throughput_add = -0.1\n" in mods and "spec_investor_steel_3" not in mods
    assert "spec_investor_steel = {\n\ticon" in mods and "building_steel_mill_throughput_add" not in mods.split("spec_investor_steel = {")[1][:120]
    assert "spec_company_boom_steel = {\n\ticon = modifier_gear_positive\n}" in mods  # legacy, empty
    assert f"NOT = {{ has_variable = {LEGACY_DONE} }}" in fx and "remove_modifier = spec_company_boom_steel" in fx and "spec_tier_steel" not in fx
    assert "owner = { var:spec_word_steel = 1 }\n\t\t\t\t\t\t\t\tNOT = { has_modifier = spec_investor_steel_1 }" in fx
    assert "limit = { local_var:spec_iat_steel = 1 }" in fx and fx.count("OR = { is_building_type") == 1  # the clear pass only
    assert fx.index("set_local_variable = { name = spec_iat_glass value = local_var:spec_ia_all }") < fx.index("set_variable = { name = spec_ia_glass value")
    assert "var:spec_ia_n >= 3" in fx and "NOT = { var:spec_ia_steel = var:spec_word_steel }" in fx
    # A full pass remains due every SWEEP months even when another good changes tier every month.
    assert "limit = { local_var:spec_ia_all = 1 }\n\t\t\t\tset_variable = { name = spec_ia_n value = 0 }" in fx
    assert fx.count("set_variable = { name = spec_ia_n value = 0 }") == 2  # initialization and full-pass reset
    assert "add_modifier = { name = spec_investor_steel_6 }" in fx and "var:spec_word_steel = 3 " not in fx  # Calm has none
    assert "is_building_type = building_steel_mill" in fx and f"has_variable = {ON}" in fx
    assert "set_global_variable = { name = spec_bt_g1_building_steel_mill value = g:steel }" in fx
    assert "spec_bt_g2_building_steel_mill value = g:tanks" in fx and "spec_bt_g1_building_glassworks value = g:glass" in fx
    assert building_goods({"x": {"oil_rig": "oil"}}, {}) == {}
    assert fx.count("{") == fx.count("}")
    assert "spec_investor_glass_6:" in loc() and "spec_investor_glass:" in loc() and "spec_company_boom_steel_desc" not in loc()
    assert "spec_company_bust_steel" in crash("steel") and crash("nothing") == ""
    assert "multiplier = spec_company_tie_1" in crash("steel", 1) and "NOT = { has_modifier" in crash("steel", 2)
    assert "spec_company_tie_2 = {\n\tvalue = spec_company_tie\n\tmultiply = 0.5" in out["common/script_values/spec_company_values.txt"]
    assert "building_oil_rig" not in out["common/static_modifiers/spec_company_modifiers.txt"]
    assert FD_SOL in out["common/modifier_type_definitions/spec_modifier_types.txt"] and FD_SOL in PANIC
    assert band("mania").strip() == f"{FD_SOL} = {FD_MANIA}" and band("wary") == "" and band_tip("panic") == ""
    print("ok")
