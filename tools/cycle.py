"""The slow loop of the credit cycle: three linked rules on top of the core system. CYCLE_ON 0 turns all three off.

A  Lending Standards: spec_lax, 0 (strict) to 1 (reckless). It rises a little every month without a panic and by
   LAX_RESCUE each time the government rescues the banks or buys up their bad loans; it falls with every point of
   Market Confidence a boom's ending costs, and by LAX_PANIC when a panic ends without a rescue. Careless banks lend
   more, lend more of it into booms (so those end harder, exposure.py), and cost more to rescue.
B  Booms build: while a good's interest is Eager or Feverish, its building group has a construction bonus. The supply
   added since the boom began (spec_sup_<g>, the market's sell orders when it started) makes its ending harder.
C  Busts land on people: a Bust or Collapse makes radicals in the states where the good's industry stands, among the
   strata the economic law makes its owners.
"""
import re

import tuning
import mod_sources

ON = tuning.get("CYCLE_ON", 1)

LAX_START = tuning.get("LAX_START", 0.4)
LAX_QUIET_YEARS = tuning.get("LAX_QUIET_YEARS", 20)  # years without a panic or a loss from strict to reckless
LAX_PER_CONF = tuning.get("LAX_PER_CONF", 0.02)      # lost per point of confidence a boom's ending costs
LAX_RESCUE = tuning.get("LAX_RESCUE", 0.25)          # gained when the government rescues the banks
LAX_PANIC = tuning.get("LAX_PANIC", 0.4)             # lost when a panic ends without a rescue
# what the two ends do, against the middle (Sound): credit lent, the share of it lent into booms, a rescue's cost
LAX_CREDIT = tuning.get("LAX_CREDIT", 0.25)
LAX_PULL = tuning.get("LAX_PULL", 0.5)
LAX_COST = tuning.get("LAX_COST", 0.5)
LAX_CUTS = [0.2, 0.4, 0.6, 0.8]
LAX_WORDS = ["Strict", "Cautious", "Sound", "Lax", "Reckless"]

BB_STEP = tuning.get("BB_STEP", 0.1)      # construction efficiency at Eager; twice it at Feverish
OVER_PER = tuning.get("OVER_PER", 0.5)    # a boom's ending is this much harder for supply doubled since it began
OVER_SHOWN = 0.05
BURN_LEVEL = 3  # a state is hit where one of the good's buildings is at least this big

# the building groups vanilla has a construction-efficiency modifier for; services, power and the arts have none
BUILD_GROUPS = ["agriculture", "extraction", "heavy_industry", "infrastructure", "light_industry", "military_industry",
                "plantations", "ranching"]
_GROUPS = {}  # group -> the goods whose boom speeds it (each building's main good)
_MAKERS = {}  # good -> every building making it

CREDIT = "\tmultiply = spec_lax_credit\n" if ON else ""
PULL = "\tmultiply = spec_lax_pull\n" if ON else ""
COST = "\tmultiply = spec_lax_cost\n" if ON else ""
TILE_REF = "$SPEC_TILE_CYCLE$" if ON else ""
NOTE_REF = "$SPEC_NOTE_CYCLE$" if ON else ""
# ScriptValue, not Var: an unset Var ends the log line
LOG = " lax=[THIS.ScriptValue('spec_lax_value')] bb=[THIS.ScriptValue('spec_bb_total')] over=[THIS.ScriptValue('spec_over_sum')]" if ON else ""


def setup(game, sells, upgrades):
    """Reads vanilla's buildings for each good's building group. Called once, where generate defines its goods."""
    def blocks(d):  # top-level name -> its text, up to the next name (vanilla's closing braces are not all at column 0)
        parts = re.split(r"^(\w+)\s*=\s*\{", "\n".join(
            f.read_text(encoding="utf-8-sig") for f in mod_sources.files(game, d)), flags=re.M)
        return zip(parts[1::2], parts[2::2])
    field = lambda body, key: (re.search(rf"^\t{key}\s*=\s*(\w+)", body, re.M) or [None, None])[1]
    parent = {name: field(body, "parent_group") for name, body in blocks("common/building_groups")}
    group = {name: field(body, "building_group") for name, body in blocks("common/buildings")}
    _GROUPS.clear()
    _MAKERS.clear()
    for file in sells.values():
        for b, g in file.items():
            _MAKERS.setdefault(g, []).append(b)
            bg = group[f"building_{b}"]
            while bg and bg[3:] not in BUILD_GROUPS:
                bg = parent.get(bg)
            if bg and g not in _GROUPS.setdefault(bg[3:], []):
                _GROUPS[bg[3:]].append(g)
    for b, ups in upgrades.items():
        for g, _ in ups:
            _MAKERS.setdefault(g, []).append(b)


def _hot(g, word, share):
    # .3f: the game rejects a comparison whose right side has 6 decimals ("Invalid right side ... 'none'")
    return f"AND = {{ has_variable = spec_word_{g} var:spec_word_{g} >= {word} spec_weight_{g} >= {share:.3f} }}"


def _boosted():
    return sorted({g for gs in _GROUPS.values() for g in gs})


def values(goods, share):
    """share: the part of the market's trade a good needs before its boom counts (the boom-end notification's)."""
    if not ON:
        return []
    out = ["spec_lax_value = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_lax }\n\t\tvalue = var:spec_lax\n\t}\n}",
           # -1 strict, 0 sound, 1 reckless; 0 before the first month
           "spec_lax_swing = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_lax }\n\t\tvalue = var:spec_lax\n"
           "\t\tsubtract = 0.5\n\t\tmultiply = 2\n\t}\n}"]
    out += [f"spec_lax_{k} = {{\n\tvalue = spec_lax_swing\n\tmultiply = {n}\n\tadd = 1\n}}"
            for k, n in (("credit", LAX_CREDIT), ("pull", LAX_PULL), ("cost", LAX_COST))]
    for grp, gs in _GROUPS.items():
        out.append(f"spec_bb_{grp} = {{\n\tvalue = 0\n" + "".join(
            f"\tif = {{\n\t\tlimit = {{ OR = {{ {' '.join(_hot(g, w, share) for g in gs)} }} }}\n\t\tvalue = {n}\n\t}}\n"
            for n, w in ((1, 5), (2, 6))) + "}")
    for g in goods:
        # ponytail: a market grown by conquest or a customs union reads as overbuilding too
        out.append(f"spec_over_{g} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_sup_{g} var:spec_sup_{g} > 0 }}\n"
                   f"\t\tvalue = spec_mv_{g}\n\t\tdivide = var:spec_sup_{g}\n\t\tsubtract = 1\n\t\tmin = 0\n\t\tmax = 1\n\t}}\n}}")
        out.append(f"spec_over_mult_{g} = {{\n\tvalue = spec_over_{g}\n\tmultiply = {OVER_PER}\n\tadd = 1\n}}")
    return out


def log_values(goods):
    """The LOG line's sums, for generate.log_values: a log build only."""
    if not ON:
        return []
    return ["spec_bb_total = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_bb_{grp}\n" for grp in _GROUPS) + "}",
            "spec_over_sum = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_over_{g}\n" for g in goods) + "}"]


def over_mult(g):
    """In spec_risk_raw_<g>: what the boom's ending costs."""
    return f"\tmultiply = spec_over_mult_{g}\n" if ON else ""


def _bump(by, t):
    how = f"add = {by} max = 1" if by > 0 else f"subtract = {-by} min = 0"
    return f"{t}set_variable = {{ name = spec_lax value = {{ value = var:spec_lax {how} }} }}\n"


def monthly(t="\t\t\t"):
    """Once a month, after the goods' interest and the month's confidence losses are worked out."""
    if not ON:
        return ""
    a = (f"{t}# lending standards and boom construction (cycle.py)\n"
         f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_lax }} }}\n"
         f"{t}\tset_variable = {{ name = spec_lax value = {LAX_START} }}\n{t}}}\n"
         # no drift to Reckless in a panic, under Tight credit or while Bad Debts last
         f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tNOT = {{ has_variable = spec_panic }}\n{t}\t\tNOT = {{ spec_stance_value = -1 }}\n"
         f"{t}\t\tNOT = {{ has_variable = spec_crunch }}\n{t}\t}}\n"
         f"{t}\tchange_variable = {{ name = spec_lax add = {1 / (12 * LAX_QUIET_YEARS):.5f} }}\n{t}}}\n"
         # spec_c_crash and spec_c_restrain are the month's loss from booms ending and wound down, negative numbers
         f"{t}change_variable = {{ name = spec_lax add = {{ value = var:spec_c_crash add = var:spec_c_restrain multiply = {LAX_PER_CONF} }} }}\n"
         f"{t}set_variable = {{ name = spec_lax value = {{ value = var:spec_lax min = 0 max = 1 }} }}\n")
    b = "".join(
        f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_bbv_{grp} }} }}\n"
        f"{t}\tset_variable = {{ name = spec_bbv_{grp} value = 0 }}\n{t}}}\n"
        f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ var:spec_bbv_{grp} = spec_bb_{grp} }} }}\n"
        f"{t}\tif = {{\n{t}\t\tlimit = {{ has_modifier = spec_boom_build_{grp} }}\n{t}\t\tremove_modifier = spec_boom_build_{grp}\n{t}\t}}\n"
        f"{t}\tif = {{\n{t}\t\tlimit = {{ spec_bb_{grp} > 0 }}\n"
        f"{t}\t\tadd_modifier = {{ name = spec_boom_build_{grp} multiplier = spec_bb_{grp} }}\n{t}\t}}\n"
        f"{t}\tset_variable = {{ name = spec_bbv_{grp} value = spec_bb_{grp} }}\n{t}}}\n" for grp in _GROUPS)
    return a + b


def rescued(tabs=1):
    """Where the government rescues the banks (spec_rescue) or buys up their bad loans (leverage.bailout_effect)."""
    t = "\t" * tabs
    return f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_lax }}\n{_bump(LAX_RESCUE, t + chr(9))}{t}}}\n" if ON else ""


def panic_over(t="\t"):
    """In spec_end_panic, before spec_rescued is cleared: a panic left to run its course sobers the banks."""
    if not ON:
        return ""
    return (f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_lax\n{t}\t\tNOT = {{ has_variable = spec_rescued }}\n{t}\t}}\n"
            f"{_bump(-LAX_PANIC, t + chr(9))}{t}}}\n")


def over_track(g, t="\t\t\t"):
    """After the boom-ending branches: the market's supply when the boom began, kept until it ends."""
    if not ON:
        return ""
    return (f"{t}if = {{\n{t}\tlimit = {{ var:spec_sev_{g} >= 1 NOT = {{ has_variable = spec_sup_{g} }} }}\n"
            f"{t}\tset_variable = {{ name = spec_sup_{g} value = spec_mv_{g} }}\n{t}}}\n"
            f"{t}else_if = {{\n{t}\tlimit = {{ var:spec_sev_{g} = 0 has_variable = spec_sup_{g} }}\n"
            f"{t}\tremove_variable = spec_sup_{g}\n{t}}}\n")


def burn(g, sev, share, t="\t\t\t\t"):
    """Where g's boom ends as a Bust (2) or Collapse (3), country scope: radicals where its industry stands.
    spec_note_ppl_<g> picks the notification's sentence: 1 the workers, 2 the owners, 3 the owners and savers."""
    if not ON or sev < 2 or g not in _MAKERS:
        return ""
    u = t + "\t\t\t"
    where = (f"{t}\t\tevery_scope_state = {{\n{u}limit = {{\n{u}\tany_scope_building = {{\n{u}\t\tOR = {{ "
             + " ".join(f"is_building_type = building_{b}" for b in _MAKERS[g])
             + f" }}\n{u}\t\tlevel >= {BURN_LEVEL}\n{u}\t}}\n{u}}}\n")
    rad = lambda size, strata, tt: f"{tt}add_radicals_in_state = {{ value = {size} strata = {strata} }}\n"
    note = lambda n, tt: f"{tt}if = {{\n{tt}\tlimit = {{ is_player = yes }}\n{tt}\tset_variable = {{ name = spec_note_ppl_{g} value = {n} days = 28 }}\n{tt}}}\n"
    big, small = ("very_large_radicals", "large_radicals") if sev == 3 else ("large_radicals", "medium_radicals")
    savers = (rad(small, "middle", t + "\t\t\t") if sev == 3 else
              # a Bust reaches the middle strata only where finance is freest
              f"{t}\t\t\tif = {{\n{t}\t\t\t\tlimit = {{ owner = {{ has_law_or_variant = law_type:law_laissez_faire }} }}\n"
              + rad("small_radicals", "middle", t + "\t\t\t\t") + f"{t}\t\t\t}}\n")
    # ponytail: under a command economy the state owns the industry and nobody is burned; a Treasury loss if wanted
    return (f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tspec_weight_{g} >= {share:.3f}\n"
            f"{t}\t\tNOT = {{ has_law_or_variant = law_type:law_command_economy }}\n{t}\t}}\n"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ has_law_or_variant = law_type:law_cooperative_ownership }}\n"
            + where + rad(big, "lower", u) + f"{t}\t\t}}\n" + note(1, t + "\t\t") + f"{t}\t}}\n"
            f"{t}\telse = {{\n" + where + rad(big, "upper", u) + savers + f"{t}\t\t}}\n" + note(sev, t + "\t\t") + f"{t}\t}}\n{t}}}\n")


def note(g, t="\t\t\t\t\t"):
    """Beside exposure.note(): what the supply built during the boom did to its ending, for the notification."""
    return f"{t}set_variable = {{ name = spec_note_over_{g} value = spec_over_mult_{g} days = 28 }}\n" if ON else ""


def ui(goods, share, t="\t\t\t"):
    """For generate.monthly's tab block: each good's tile tooltip figures (GUI text can't read a script value by key)."""
    if not ON:
        return ""
    over = "".join(
        f"{t}if = {{\n{t}\tlimit = {{ spec_over_{g} >= {OVER_SHOWN} }}\n"
        f"{t}\tset_variable = {{ name = spec_ui_over_{g} value = spec_over_{g} }}\n"
        f"{t}\tset_variable = {{ name = spec_ui_overx_{g} value = spec_over_mult_{g} }}\n{t}}}\n"
        f"{t}else = {{\n{t}\tremove_variable = spec_ui_over_{g}\n{t}\tremove_variable = spec_ui_overx_{g}\n{t}}}\n" for g in goods)
    build = "".join(
        f"{t}if = {{\n{t}\tlimit = {{ {_hot(g, 5, share)} }}\n"
        f"{t}\tset_variable = {{ name = spec_ui_bb_{g} value = {{ value = var:spec_word_{g} subtract = 4 multiply = {BB_STEP} }} }}\n{t}}}\n"
        f"{t}else = {{\n{t}\tremove_variable = spec_ui_bb_{g}\n{t}}}\n" for g in _boosted())
    return over + build


def state_vars(goods):
    if not ON:
        return []
    return (["spec_lax"] + [f"spec_bbv_{grp}" for grp in _GROUPS] + [f"spec_ui_bb_{g}" for g in _boosted()]
            + [f"spec_{k}_{g}" for g in goods for k in ("sup", "ui_over", "ui_overx", "note_over", "note_ppl")])


def modifiers():
    return "".join(
        f"spec_boom_build_{grp} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds\n"
        f"\tbuilding_group_bg_{grp}_construction_efficiency_add = {BB_STEP}\n}}\n\n" for grp in _GROUPS) if ON else ""


def shut_down(t="\t"):
    return "".join(f"{t}if = {{\n{t}\tlimit = {{ has_modifier = spec_boom_build_{grp} }}\n"
                   f"{t}\tremove_modifier = spec_boom_build_{grp}\n{t}}}\n" for grp in _GROUPS) if ON else ""


def loc():
    if not ON:
        return ""
    from market_tab import fx, good_var, sv, v
    gt = lambda a, b: f"GreaterThan_CFixedPoint({a}, {fx(b)})"
    pct = lambda name: f"#v [Subtract_CFixedPoint({sv(name)}, {fx(1)})|+%0]#!"
    lax = v("spec_lax", LAX_START)
    picks = "".join(f"SelectLocalization(LessThan_CFixedPoint({lax}, {fx(c)}), 'SPEC_LAXW_{i}', " for i, c in enumerate(LAX_CUTS))
    # Each toast carries its own captured numbers, including when several goods end together.
    over, ppl = "SCOPE.GetValue('spec_note_over')", "SCOPE.GetValue('spec_note_ppl')"
    return ("".join(f' spec_boom_build_{grp}: "Boom Construction"\n' for grp in _GROUPS)
            + "".join(f' SPEC_LAXW_{i}: "{w}"\n' for i, w in enumerate(LAX_WORDS))
            + f' SPEC_EFFECT_LAX: "Lending Standards"\n'
            f' SPEC_EFFECT_LAX_VALUE: "#v [{picks}\'SPEC_LAXW_{len(LAX_CUTS)}\'{")" * len(LAX_CUTS)}]#!"\n'
            f' SPEC_EFFECT_LAX_TT: "#header [concept_spec_lending_standards]#!\\n$SPEC_EFFECT_LAX_VALUE$\\n$TOOLTIP_DELIMITER$\\n'
            f'Credit lent each month: {pct("spec_lax_credit")}\\nShare of it lent into booms: {pct("spec_lax_pull")}\\n'
            f'Bank Rescue cost: {pct("spec_lax_cost")}\\n$TOOLTIP_DELIMITER$\\n'
            f'Banks grow careless in years without losses, and after each Bank Rescue. They grow careful again '
            f'only by taking losses: when a boom ends, and most of all when a [concept_spec_financial_panic] runs its course without a Bank Rescue.'
            f'\\n\\n#title To keep them careful:#!\\n- Set [concept_spec_credit_policy] to Tight: they stop growing careless\\n'
            f'- Restrain booms before they end badly\\n- Let a panic run without a Bank Rescue, or Suspend the Bank Act less often'
            f'\\n\\nLevels: {", ".join(f"#v {w}#!" for w in LAX_WORDS)}"\n'
            f' SPEC_TILE_CYCLE: "[SelectLocalization({gt(good_var("spec_ui_overx"), 1)}, \'SPEC_TILE_OVER_ON\', \'SPEC_GOODS_NONE\')]'
            f'[SelectLocalization({gt(good_var("spec_ui_bb"), 0)}, \'SPEC_TILE_BB_ON\', \'SPEC_GOODS_NONE\')]"\n'
            f' SPEC_TILE_OVER_ON: "\\n\\n#title Overbuilding:#! supply is up #v [{good_var("spec_ui_over")}|%0]#! since this boom began\\n'
            f'If its boom ended, [concept_spec_market_confidence] would fall #v x[{good_var("spec_ui_overx")}|2]#! as far"\n'
            f' SPEC_TILE_BB_ON: "\\n\\n#title Boom Construction:#! #P +[{good_var("spec_ui_bb")}|%0]#! construction efficiency '
            f'for its industry while investors stay this keen"\n'
            ' SPEC_NOTE_CYCLE: "'
            f'[SelectLocalization({gt(ppl, 2.5)}, \'SPEC_NOTE_PPL_3\', SelectLocalization({gt(ppl, 1.5)}, \'SPEC_NOTE_PPL_2\', '
            f'SelectLocalization({gt(ppl, 0.5)}, \'SPEC_NOTE_PPL_1\', \'SPEC_GOODS_NONE\')))]"\n'
            f' SPEC_NOTE_OVER_ON: " So much had been built during the boom that the fall was #N x[{over}|2]#! as hard."\n'
            f' SPEC_NOTE_PPL_1: " The workers who owned its industry bore the losses, and some have become [Concept(\'concept_radical\', \'$concept_radicals$\')] in the states where it stands."\n'
            f' SPEC_NOTE_PPL_2: " Its owners bore the losses, and some have become [Concept(\'concept_radical\', \'$concept_radicals$\')] in the states where it stands."\n'
            f' SPEC_NOTE_PPL_3: " Its owners and ordinary savers bore the losses, and many have become [Concept(\'concept_radical\', \'$concept_radicals$\')] in the states where it stands."\n')


if __name__ == "__main__":
    import generate
    g = generate.GOODS
    setup(generate.GAME, generate.SELLS, generate.UPGRADES)  # generate set up its own copy of this module, not __main__
    share = generate.TOAST_SHARE / generate.EXPOSURE_FULL
    assert "steel" in _GROUPS["heavy_industry"] and "grain" in _GROUPS["agriculture"] and "coal" in _GROUPS["extraction"], _GROUPS
    assert set(_GROUPS) <= set(BUILD_GROUPS) and "fine_art" not in _boosted()
    assert "spec_over_sum" not in "\n".join(values(g, share)) and "spec_over_sum = {" in log_values(g)[1]
    for name, text in (("values", "\n".join(values(g, share))), ("monthly", monthly()), ("rescued", rescued()),
                       ("panic_over", panic_over()), ("ui", ui(g, share)), ("modifiers", modifiers()), ("shut_down", shut_down()),
                       *((f"burn {x} {s}", burn(x, s, share)) for x in g for s in (2, 3)),
                       *((f"over_track {x}", over_track(x)) for x in g)):
        assert text and text.count("{") == text.count("}"), name + " unbalanced or empty"
    assert burn("steel", 1, share) == "" and all(k.startswith("spec_") for k in state_vars(g))

    # a model of spec_lax: twenty quiet years take the banks from strict to reckless; an unrescued panic sobers them
    lax = 0.0
    for _ in range(12 * LAX_QUIET_YEARS):
        lax = min(1, lax + 1 / (12 * LAX_QUIET_YEARS))
    assert abs(lax - 1) < 1e-9
    assert max(0, lax - LAX_PANIC) < 0.8 < min(1, 0.6 + LAX_RESCUE)
    print("cycle ok", {k: len(v) for k, v in _GROUPS.items()})
