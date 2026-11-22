"""Interest group stances on goods. Each vanilla interest group favors about two goods and may oppose one, rolled
per country from a historical weighted pool (POOLS), among the goods its market trades (spec_weight_<g> >= DEAL).
Stored on the country: spec_igs_<ig>_<g> is 1 (favored) or -1 (opposed); spec_igs_rolled marks the roll done, so
old saves and running campaigns roll on their first monthly pulse (MONTHLY).

Approval moves through timed modifiers on the group (MODS), x1 while Influential, x2 while Powerful and none while
Marginalized (vanilla's clout tiers, spec_igs_tier):
- a favored good booms (its interest word rises to Eager, boom()) or busts (a Bust or Collapse, boom_end());
- Encourage or Restrain on a good it cares about, or a Great Issue floated in it (levers.py calls
  spec_igs_lever_<kind>, LEVERS); a Bust or Collapse during the issue costs the groups that favor it twice, and ends
  the approval the issue gave them.
Stances shift rarely: a new group leader may re-roll one (spec_igs_new_leader); a Bust or Collapse in a favored good
may make the group drop it (DROP).

generate.py: MONTHLY in the monthly pulse, boom() after each good's word, boom_end() in each boom ending, build(), loc().
interest_list.row() places slot() in its Interest Groups column; levers.loc() places lever_lines() in the Encourage, Restrain and Great Issue tooltips."""

import sys
from functools import reduce
import market_news

P = "Country.MakeScope"  # as market_tab.P; not imported, market_tab imports levers, which imports this
DEAL = 0.1              # spec_weight: a share of the market's trade of 0.1 x generate.EXPOSURE_FULL (0.3%) counts as dealing in it
FAVORED = 2             # favored goods a group holds
DISLIKE_CHANCE = 50     # % a group opposes one good (2026-11-19: four groups had no opposed pool, so never did)
REROLL_CHANCE = 33      # % a new leader re-rolls one stance
DROP = {2: 25, 3: 50}   # % a group drops a favored good when it ends in a Bust (2) or Collapse (3)
EAGER = 5               # generate's interest word for Eager: rising to it is a boom
# modifier: approval for an Influential group (Powerful: twice it), days, vanilla icon
MODS = {"spec_igs_boom": (1, 180, "modifier_coins_positive"), "spec_igs_bust": (-1, 180, "modifier_coins_negative"),
        "spec_igs_backed": (1, 365, "modifier_flag_positive"), "spec_igs_crossed": (-1, 365, "modifier_flag_negative"),
        # a Great Issue (levers.py), as long as it runs (levers.ISSUE_MONTHS)
        "spec_igs_issue": (1, 730, "modifier_documents_positive"), "spec_igs_issue_against": (-1, 730, "modifier_documents_negative")}
# lever kind (levers.py) -> (the stance it pleases: 1 favored, -1 opposed; modifier for it, modifier for the other)
LEVERS = {"encourage": (1, "spec_igs_backed", "spec_igs_crossed"), "restrain": (-1, "spec_igs_backed", "spec_igs_crossed"),
          "issue": (1, "spec_igs_issue", "spec_igs_issue_against")}

# group (vanilla key without ig_): (icon file, {favored good: weight}, {opposed good: weight}). Goods the mod does not
# track (cotton, ironclads, manowars) are not in generate.GOODS; build() drops any pool good that is missing
POOLS = {
    "landowners": ("landowners", {"grain": 3, "sugar": 2, "tobacco": 2, "wine": 2, "tea": 1, "coffee": 1, "silk": 1,
                                  "dye": 1, "meat": 1}, {"steel": 1, "engines": 1}),
    # the Anti-Corn Law League: manufacturers wanted cheap bread for cheap wages
    "industrialists": ("industrialists", {"steel": 3, "tools": 3, "engines": 3, "coal": 2, "iron": 2, "fabric": 1,
                                          "explosives": 1, "glass": 1, "oil": 1, "rubber": 1, "electricity": 1,
                                          "automobiles": 1, "steamers": 1, "copper": 1}, {"grain": 1}),
    "armed_forces": ("armed_forces", {"small_arms": 3, "artillery": 3, "ammunition": 3, "explosives": 1, "tanks": 1,
                                      "aeroplanes": 1, "lead": 1, "sulfur": 1}, {"opium": 2, "liquor": 1}),  # shot and powder  # discipline in the ranks
    "devout": ("devout", {"grain": 2, "paper": 2, "clothes": 1, "groceries": 1, "fine_art": 1},
               {"liquor": 3, "opium": 3, "wine": 2}),
    "rural_folk": ("rural_folk", {"grain": 3, "meat": 3, "fabric": 2, "fish": 1, "fruit": 1, "wood": 1, "fertilizer": 1},
                   {"engines": 2, "tools": 1}),  # the Swing Riots: threshing machines took the winter's work
    "petty_bourgeoisie": ("petty_bourgeoisie", {"furniture": 3, "luxury_clothes": 2, "porcelain": 2, "liquor": 2,
                                                "luxury_furniture": 1, "clothes": 1, "groceries": 1, "glass": 1,
                                                "hardwood": 1, "clippers": 1, "merchant_marine": 1},  # cabinetmakers, shipowners
                          {"fabric": 2, "opium": 1}),  # mill cloth ruined the hand weavers
    "intelligentsia": ("intelligensia", {"paper": 3, "telephones": 2, "radios": 1, "glass": 1, "fine_art": 1,
                                         "electricity": 1}, {"opium": 3, "liquor": 1}),
    "trade_unions": ("trade_unions", {"groceries": 3, "clothes": 3, "coal": 1, "steel": 1, "furniture": 1, "fabric": 1},
                     {"liquor": 2, "opium": 1}),  # temperance ran deep in the labour movement
}
_POOLS = {}  # POOLS filtered to the tracked goods, by build()

MONTHLY = ("\t\t\t# interest group stances on goods: rolled once, also for old saves (ig_stances.py)\n"
           "\t\t\tif = {\n\t\t\t\tlimit = { NOT = { has_variable = spec_igs_rolled } }\n\t\t\t\tspec_igs_roll = yes\n\t\t\t}\n"
           "\t\t\tif = {\n\t\t\t\tlimit = { is_player = yes }\n\t\t\t\tspec_igs_mark = yes  # the list's stance filters, for saves from before them\n\t\t\t}\n")


def var(ig, g):
    return f"spec_igs_{ig}_{g}"


# in generate's spec_sguis.txt: the goods list's stance filter headers run it as they are clicked (interest_list.header),
# so the flags are there before the first monthly pulse
SGUI = "\nspec_sgui_igs_mark = {\n\tscope = country\n\teffect = { spec_igs_mark = yes }\n}\n"


def mark(goods):
    """spec_igs_mark: spec_igs_fv_<g> 1 while a group favors g, spec_igs_op_<g> 1 while one opposes it, else unset,
    for the goods list's stance filters (interest_list), so a row reads one variable, not every group's stance. Run
    wherever stances change (roll, reroll, a bust's drop) and monthly for players."""
    out = ""
    for g in goods:
        for flag, value, side in (("fv", 1, 1), ("op", -1, 2)):
            igs = [ig for ig in cares(g) if g in POOLS[ig][side]]
            if igs:
                out += (f"\tif = {{\n\t\tlimit = {{\n\t\t\tOR = {{\n" + "".join(f"\t\t\t\tvar:{var(ig, g)} ?= {value}\n" for ig in igs)
                        + f"\t\t\t}}\n\t\t}}\n\t\tset_variable = {{ name = spec_igs_{flag}_{g} value = 1 }}\n\t}}\n"
                        f"\telse_if = {{\n\t\tlimit = {{ has_variable = spec_igs_{flag}_{g} }}\n\t\tremove_variable = spec_igs_{flag}_{g}\n\t}}\n")
    return "# country scope: the goods list's stance flags (ig_stances.mark)\nspec_igs_mark = {\n" + out + "}\n"


def boom(g, t="\t\t\t"):
    """generate.monthly, after spec_word_<g> is set (local_var:spec_wold holds last month's word): a favored good booms."""
    return (f"{t}if = {{\n{t}\tlimit = {{ var:spec_word_{g} >= {EAGER} local_var:spec_wold > 0 local_var:spec_wold < {EAGER} }}\n"
            f"{t}\tspec_igs_on_boom_{g} = yes\n{t}}}\n") if cares(g) else ""


def boom_end(g, sev, t="\t\t\t\t"):
    """generate.monthly, where g's boom ends with severity sev: a Bust or Collapse costs the groups favoring it."""
    return f"{t}spec_igs_on_bust_{g} = {{ CHANCE = {DROP[sev]} }}\n" if sev in DROP and cares(g) else ""


# -- script ------------------------------------------------------------------------------------------------

def _ind(text, n):
    return "".join("\t" * n + line if line.strip() else line for line in text.splitlines(True))


# a player's toast when one of their groups' stances changes after the first roll (notify.py posts NOTES' messages)
NOTE_GROUP = "spec_igs_notification_group"
_IG, _GOOD = "[SCOPE.gsInterestGroup('spec_note_ig').GetName]", "[SCOPE.sGoods('spec_note_good').GetName]"
# the good first, so a group's name reads as singular or plural alike ("Catholic Church", "Landowners"); no body
NOTES = {f"spec_igs_{k}": (NOTE_GROUP, "goods", "neutral", f"{_GOOD} {what} by {_IG}", "") for k, what in (
    ("fav_new", "now supported"), ("fav_lost", "no longer supported"),
    ("dis_new", "now opposed"), ("dis_lost", "no longer opposed"))}
NOTE_GROUPS = {NOTE_GROUP: "Interest Group Stances"}


def _note(ig, g, kind, t):
    """Country scope: the player's toast that group ig's stance on g changed (kind a NOTES key's end); none while
    the first stances are rolled (spec_igs_rolled is set after)."""
    detailed = (f"{t}\tig:ig_{ig} = {{ save_scope_as = spec_note_ig }}\n{t}\tg:{g} = {{ save_scope_as = spec_note_good }}\n"
                f"{t}\tpost_notification = spec_igs_{kind}\n")
    return (f"{t}if = {{\n{t}\tlimit = {{ is_player = yes has_variable = spec_igs_rolled }}\n"
            + market_news.alternate(detailed, 'opinions', t + "\t") + f"{t}}}\n")


def _pick(ig, pool, value):
    """Country scope: one more good from pool for group ig, by weight, among goods traded here it has no stance on."""
    cand = lambda g: f"spec_weight_{g} >= {DEAL} NOT = {{ has_variable = {var(ig, g)} }}"
    kind = "fav_new" if value > 0 else "dis_new"
    entries = "".join(f"\t\t{w} = {{\n\t\t\ttrigger = {{ {cand(g)} }}\n"
                      f"\t\t\tset_variable = {{ name = {var(ig, g)} value = {value} }}\n{_note(ig, g, kind, chr(9) * 3)}\t\t}}\n"
                      for g, w in pool.items())
    any_ = "".join(f"\t\t\tAND = {{ {cand(g)} }}\n" for g in pool)
    return f"if = {{\n\tlimit = {{\n\t\tOR = {{\n{any_}\t\t}}\n\t}}\n\trandom_list = {{\n{entries}\t}}\n}}\n"


def _drop(ig, pool, value):
    """Country scope: remove one of group ig's stances of this value, at random."""
    has = lambda g: f"var:{var(ig, g)} ?= {value}"
    kind = "fav_lost" if value > 0 else "dis_lost"
    entries = "".join(f"\t\t1 = {{\n\t\t\ttrigger = {{ {has(g)} }}\n\t\t\tremove_variable = {var(ig, g)}\n"
                      f"{_note(ig, g, kind, chr(9) * 3)}\t\t}}\n" for g in pool)
    any_ = "".join(f"\t\t\t{has(g)}\n" for g in pool)
    return f"if = {{\n\tlimit = {{\n\t\tOR = {{\n{any_}\t\t}}\n\t}}\n\trandom_list = {{\n{entries}\t}}\n}}\n"


def _each(body):
    """Country scope, param G: body(ig) for every group."""
    return "".join(body(ig) for ig in _POOLS)


def _approval(ig, mod, t="\t\t", x="x1"):
    """x: x1, or x2 for twice the usual approval."""
    return f"{t}ig:ig_{ig} ?= {{ spec_igs_approval = {{ M = {mod} DAYS = {MODS[mod][1]} X = {x} }} }}\n"


def cares(g):
    """The groups that can hold a stance on g (from the unfiltered POOLS, so usable before build())."""
    return [ig for ig, (_, fav, dis) in POOLS.items() if g in fav or g in dis]


def script(goods):
    import levers  # imports this module; loaded by the time build() runs
    values = ["# interest group scope: vanilla's clout tiers, 0 Marginalized, 1 Influential, 2 Powerful\nspec_igs_tier = {\n"
              "\tvalue = 1\n\tif = {\n\t\tlimit = { is_marginal = yes }\n\t\tvalue = 0\n\t}\n"
              "\tif = {\n\t\tlimit = { is_powerful = yes }\n\t\tvalue = 2\n\t}\n}\n",
              "spec_igs_tier_x1 = {\n\tvalue = spec_igs_tier\n}\n",
              "spec_igs_tier_x2 = {\n\tvalue = spec_igs_tier\n\tmultiply = 2\n}\n"]
    values += [f"spec_igs_nf_{ig} = {{\n\tvalue = 0\n" + "".join(
        f"\tif = {{\n\t\tlimit = {{ var:{var(ig, g)} ?= 1 }}\n\t\tadd = 1\n\t}}\n" for g in fav) + "}\n"
        for ig, (_, fav, _) in _POOLS.items()]
    fx = ["# interest group stances on goods (tools/ig_stances.py); spec_igs_<group>_<good>: 1 favored, -1 opposed\n",
          "# interest group scope: a timed approval modifier by its clout tier, X x1 or x2 (twice); none while Marginalized\n"
          "spec_igs_approval = {\n\tif = {\n\t\tlimit = { is_marginal = no }\n"
          "\t\tadd_modifier = {\n\t\t\tname = $M$\n\t\t\tdays = $DAYS$\n\t\t\tmultiplier = spec_igs_tier_$X$\n\t\t}\n\t}\n}\n",
          mark(goods)]
    for ig, (_, fav, dis) in _POOLS.items():
        fx.append(f"spec_igs_fav_{ig} = {{\n{_ind(_pick(ig, fav, 1), 1)}}}\n")
        fill = "".join(f"\tif = {{\n\t\tlimit = {{ spec_igs_nf_{ig} < {FAVORED} }}\n\t\tspec_igs_fav_{ig} = yes\n\t}}\n"
                       for _ in range(FAVORED))
        # a new leader: drop a favored good (then fill back up to FAVORED), or re-roll the opposed one
        redis = ""
        if dis:
            fx.append(f"spec_igs_dis_{ig} = {{\n{_ind(_pick(ig, dis, -1), 1)}}}\n")
            redis = (f"\t\t1 = {{\n{_ind(_drop(ig, dis, -1), 3)}\t\t\trandom = {{\n\t\t\t\tchance = {DISLIKE_CHANCE}\n"
                     f"\t\t\t\tspec_igs_dis_{ig} = yes\n\t\t\t}}\n\t\t}}\n")
        fx.append(f"spec_igs_reroll_{ig} = {{\n\trandom_list = {{\n\t\t2 = {{\n{_ind(_drop(ig, fav, 1), 3)}\t\t}}\n"
                  f"{redis}\t}}\n{fill}\tspec_igs_mark = yes\n}}\n")
    roll = "".join(f"\tspec_igs_fav_{ig} = yes\n" * FAVORED
                   + (f"\trandom = {{\n\t\tchance = {DISLIKE_CHANCE}\n\t\tspec_igs_dis_{ig} = yes\n\t}}\n" if dis else "")
                   for ig, (_, _, dis) in _POOLS.items())
    fx.append(f"# each group's first stances, from the goods its market trades\nspec_igs_roll = {{\n{roll}"
              "\tspec_igs_mark = yes\n\tset_variable = { name = spec_igs_rolled value = 1 }\n}\n")
    # one effect per good, over only the groups whose pool holds it: a $G$ parameter would name every group-good pair,
    # and the game logs each pair no script sets as "used but never set"
    for g in goods:
        igs = cares(g)
        if not igs:
            continue
        fx.append(f"spec_igs_on_boom_{g} = {{\n" + "".join(
            f"\tif = {{\n\t\tlimit = {{ var:{var(ig, g)} ?= 1 }}\n{_approval(ig, 'spec_igs_boom')}\t}}\n" for ig in igs) + "}\n")
        bust = lambda ig: (f"\t\tif = {{\n\t\t\tlimit = {{ has_variable = spec_issue_{g} }}\n"
                           f"\t\t\tig:ig_{ig} ?= {{ remove_modifier = spec_igs_issue }}\n{_approval(ig, 'spec_igs_bust', chr(9) * 3, 'x2')}"
                           f"\t\t}}\n\t\telse = {{\n{_approval(ig, 'spec_igs_bust', chr(9) * 3)}\t\t}}\n") if levers.ISSUE_ON \
            else _approval(ig, 'spec_igs_bust')
        fx.append(f"spec_igs_on_bust_{g} = {{  # param CHANCE: the group may drop the good\n" + "".join(
            f"\tif = {{\n\t\tlimit = {{ var:{var(ig, g)} ?= 1 }}\n{bust(ig)}"
            f"\t\trandom = {{\n\t\t\tchance = $CHANCE$\n\t\t\tremove_variable = {var(ig, g)}\n{_note(ig, g, 'fav_lost', chr(9) * 3)}"
            f"\t\t}}\n\t}}\n" for ig in igs) + "\tspec_igs_mark = yes\n}\n")
    for kind, (up, pleased, crossed) in LEVERS.items():
        if kind == "issue" and not levers.ISSUE_ON:
            continue
        fx.append(f"# param G: lever {kind} goes on for good G (levers.py)\nspec_igs_lever_{kind} = {{\n\tspec_igs_lever_{kind}_$G$ = yes\n}}\n")
        for g in goods:  # every good, as levers.py can pass any; empty for goods no group cares about
            fx.append(f"spec_igs_lever_{kind}_{g} = {{\n" + "".join(
                f"\tif = {{\n\t\tlimit = {{ var:{var(ig, g)} ?= {up} }}\n{_approval(ig, pleased)}\t}}\n"
                f"\telse_if = {{\n\t\tlimit = {{ var:{var(ig, g)} ?= {-up} }}\n{_approval(ig, crossed)}\t}}\n"
                for ig in cares(g)) + "}\n")
    dispatch = "".join(f"\t\t\t\t{'if' if i == 0 else 'else_if'} = {{\n\t\t\t\t\tlimit = {{ is_interest_group_type = ig_{ig} }}\n"
                       f"\t\t\t\t\towner = {{ spec_igs_reroll_{ig} = yes }}\n\t\t\t\t}}\n" for i, ig in enumerate(_POOLS))
    on_actions = ("# Root = Character: a new interest group leader may re-roll one of the group's stances on goods\n"
                  "on_new_interest_group_leader = {\n\ton_actions = { spec_igs_new_leader }\n}\n\n"
                  "spec_igs_new_leader = {\n\ttrigger = {\n\t\tinterest_group ?= {\n\t\t\towner ?= {\n\t\t\t\thas_variable = spec_igs_rolled\n"
                  "\t\t\t\thas_variable = spec_mv_total\n\t\t\t\tvar:spec_mv_total > 0  # spec_weight_<g> divides by it\n\t\t\t}\n\t\t}\n\t}\n"
                  f"\teffect = {{\n\t\trandom = {{\n\t\t\tchance = {REROLL_CHANCE}\n\t\t\tinterest_group ?= {{\n{dispatch}\t\t\t}}\n\t\t}}\n\t}}\n}}\n")
    mods = "".join(f"{m} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/{icon}.dds\n\tinterest_group_approval_add = {a}\n}}\n\n"
                   for m, (a, _, icon) in MODS.items())
    return {"common/script_values/spec_igs_values.txt": "\n".join(values),
            "common/scripted_effects/spec_igs_effects.txt": "\n".join(fx),
            "common/on_actions/spec_igs_on_actions.txt": on_actions,
            "common/static_modifiers/spec_igs_modifiers.txt": mods}


def build(write, goods):
    _POOLS.clear()
    for ig, (icon, fav, dis) in POOLS.items():
        _POOLS[ig] = (icon, {g: w for g, w in fav.items() if g in goods}, {g: w for g, w in dis.items() if g in goods})
    for rel, text in script(goods).items():
        write(rel, text)


# -- interface ---------------------------------------------------------------------------------------------

def _stance(ig):
    """GUI value: the group's stance on the context's good, 1, -1 or 0."""
    return f"{P}.Var(Concatenate('{var(ig, '')}', Goods.GetKey)).GetValueWithDefault('(CFixedPoint)0')"


def _ig(ig):
    """GUI and text: the country's interest group of this type, with its own name, texture and clout."""
    return f"Country.GetInterestGroupOfType('ig_{ig}')"


def _amount(mod, scope="InterestGroup"):
    """GUI value: the approval a modifier gives the group, by its clout tier (spec_igs_tier)."""
    return f"Multiply_CFixedPoint({scope}.MakeScope.ScriptValue('spec_igs_tier'), '(CFixedPoint){MODS[mod][0]}')"


def _years(mod):
    days = MODS[mod][1]
    if days < 365:
        return f"{days // 30} months"
    d = days // 365
    return "a year" if d == 1 else f"{d} years"


# the goods row's Favored and Opposed columns (interest_list.COL['fav'] and ['dis'], after Risk): as vanilla's pop
# shows the group it leans to (pops_overview.gui), the strongest group holding that stance, and a +N for the rest
SLOT_W = 38
LEAD_ICON = 30
SIDES = (("GreaterThan", "FAV", "Max_CFixedPoint"), ("LessThan", "DIS", "Min_CFixedPoint"))


def _has(st, op):
    """GUI test: the group (st its stance reader) holds the stance op (GreaterThan: favors, LessThan: opposes)."""
    return lambda ig: f"{op}_CFixedPoint({st(ig)}, '(CFixedPoint)0')"


def _count(st, side, clip):
    """GUI value: how many of the groups side hold the stance clip keeps (Max: favor, Min: oppose)."""
    terms = [f"{clip}({st(ig)}, '(CFixedPoint)0')" for ig in side]
    return f"Abs_CFixedPoint({reduce(lambda a, b: f'Add_CFixedPoint({a}, {b})', terms)})"


def _outranks(i, side, has):
    """GUI test: side[i] has more clout than every other group holding the stance (ties: the first); None if alone."""
    clout = lambda ig: f"{_ig(ig)}.GetClout"
    tests = [f"Or(Not({has(o)}), {'GreaterThan' if j < i else 'GreaterThanOrEqualTo'}_CFixedPoint({clout(side[i])}, {clout(o)}))"
             for j, o in enumerate(side) if j != i]
    return reduce(lambda a, b: f"And({a}, {b})", tests) if tests else None


def _markers(cmp, badge, corner):
    """The approve and disapprove markers over an icon's corner, each shown by cmp(op) on the stance."""
    return "".join(f"""icon = {{
	visible = "[{cmp(op)}]"
	size = {{ {badge} {badge} }}
	parentanchor = bottom|{corner}
	texture = "gfx/interface/icons/generic_icons/{tex}.dds"
	alwaystransparent = yes
}}
""" for op, tex in (("GreaterThan", "approval_icon"), ("LessThan", "disapproval_icon")))


def _side(g, op):
    """The groups that may hold stance op on good g (its pools), or every group for a list row (g None)."""
    return [ig for ig in POOLS if g in POOLS[ig][1 if op == "GreaterThan" else 2]] if g else list(POOLS)


def slot(rd, g=None, close=""):
    """The goods row's Favored and Opposed cells, (favored, opposed) (interest_list.row; rd its variable reader; g a
    fixed row's good, else every group is tested). The strongest group holding the stance is vanilla's ig_button
    (politics_panel_types.gui: clickable, the powerful frame shown), and a +N counts the others; the
    button's tooltip names them all (SPEC_IGS_ROW_*_ALL_TT). Opening a group's panel wants a group it may change, which
    Country.GetInterestGroupOfType does not give, so the button is an item of the country's own list of groups, shown
    for the one leading. close: onclick lines run before the interest group panel opens (the Finance window's own
    close)."""
    st = lambda ig: rd(var(ig, "")[:-1])
    goods = f"GetGoods('{g}')" if g else "Scope.GetGoods"

    def item(side, op, key):
        # per group: holds the stance (one read), then, only for a holder (hidden parents skip their children),
        # outranks the other holders; only the leader's list of groups runs. Was one test of every group in every
        # item of the list: 8 x 8 x 8 stance reads a cell each frame on a sorted (list) row
        has = _has(st, op)

        def one(i, ig):
            beats = _outranks(i, side, has)
            return f"""container = {{
	parentanchor = center
	visible = "[{has(ig)}]"
	container = {{{f'''
		visible = "[{beats}]"''' if beats else ""}
		datamodel = "[Country.AccessAllInterestGroups]"
		item = {{
			ig_button = {{
				datacontext = "[{goods}]"
				# the row's good (as the row gets it), for the tooltip: it sees only the button's own contexts
				visible = "[ObjectsEqual(InterestGroup.Self, {_ig(ig)})]"
				size = {{ {LEAD_ICON} {LEAD_ICON} }}
				blockoverride "in_government_icon" {{}}
				blockoverride "onclick" {{
{_ind(close, 3)}					onclick = "[InformationPanelBar.OpenInterestGroupPanel(InterestGroup.AccessSelf)]"
					onrightclick = "[RightClickMenuManager.ShowForIG(InterestGroup.AccessSelf)]"
				}}
				blockoverride "tooltip" {{
					tooltip = "SPEC_IGS_ROW_{key}_ALL_TT"
				}}
			}}
		}}
	}}
}}
"""
        return "".join(one(i, ig) for i, ig in enumerate(side))

    def cell(op, key, clip):
        side = _side(g, op)
        if not side:
            return ""
        n = _count(st, side, clip)
        more = "" if len(side) < 2 else f"""textbox = {{
	visible = "[GreaterThanOrEqualTo_CFixedPoint({n}, '(CFixedPoint)2')]"
	parentanchor = bottom|right
	size = {{ 22 18 }}
	align = right|nobaseline
	fontsize = 14
	raw_text = "+[Subtract_CFixedPoint({n}, '(CFixedPoint)1')|0]"
	alwaystransparent = yes
}}
"""
        return item(side, op, key) + more

    return tuple(cell(*s) for s in SIDES)


def lever_lines(kind):
    """Text for the Encourage (kind encourage) or Restrain tooltip: under a title as vanilla's approval changes from a
    law, a line for each group whose approval it moves, as vanilla lists a law's (IG_APPROVES_OF_LAW_CHANGE): marker,
    name, clout, change."""
    up, down = ("GreaterThan", "LessThan") if LEVERS[kind][0] > 0 else ("LessThan", "GreaterThan")
    # a Marginalized group's approval does not move: no line
    test = lambda ig, op: f"And({op}_CFixedPoint({_stance(ig)}, '(CFixedPoint)0'), Not({_ig(ig)}.IsMarginal))"
    cares_any = reduce(lambda a, b: f"Or({a}, {b})", [test(ig, "NotEqualTo") for ig in POOLS])
    k = "ISSUE_" if kind == "issue" else ""
    return (f"[SelectLocalization({cares_any}, 'SPEC_IGS_LEVER_HEAD', 'SPEC_LEVER_NONE')]"
            + "".join(f"[SelectLocalization({test(ig, up)}, 'SPEC_IGS_{k}UP_{ig}', SelectLocalization({test(ig, down)}, "
                      f"'SPEC_IGS_{k}DOWN_{ig}', 'SPEC_LEVER_NONE'))]" for ig in POOLS))


# before Political Movements' dropdown, after the Ideologies section
PANEL_ANCHOR = ('\t\t\t\t\tflowcontainer = {\n\t\t\t\t\t\tparentanchor = hcenter\n\t\t\t\t\t\tdirection = vertical\n\n'
                '\t\t\t\t\t\tbackground = {\n\t\t\t\t\t\t\tusing = dropdown_background\n\t\t\t\t\t\t\tmargin = { 0 -2 }\n'
                '\t\t\t\t\t\t}\n\n\t\t\t\t\t\t### POSSIBLE LEADER IDEOLOGIES - DROPDOWN\n')
IDEO_W, IDEO_H = 260, 40  # as the Ideologies grid's items (addcolumn 260, an icon and name 40 high)


def _stance_text(cmp, depth):
    """The stance's tooltip text, one textbox per stance: inside SelectLocalization the text lost its Goods."""
    box = lambda op, key: f'custom_tooltip_textbox_with_empty_line = {{\n\tvisible = "[{cmp(op)}]"\n\ttext = "{key}"\n}}\n'
    return _ind(box("GreaterThan", "SPEC_IGS_FAV_TT") + box("LessThan", "SPEC_IGS_DIS_TT"), depth)


def panel_patch(gui):
    """The vanilla interest group panel (gui/interest_group_panel.gui) with a Goods section after Ideologies, laid out
    as it is: a header, then the goods the group favors (left column) and opposes (right), each vanilla's goods list
    icon (market_panel.gui goods_list_item) with the Finance list's marker, and its name. Its tooltip is vanilla's goods
    tooltip ending with the stance (SPEC_IGS_FAV_TT / _DIS_TT). The panel shows one group, any country's: one set of
    goods per group type, shown for the type the panel holds; the stances are read from the group's own country.
    Run after build()."""
    if gui.count(PANEL_ANCHOR) != 1:
        sys.exit(f"interest_group_panel.gui changed, can't find: {PANEL_ANCHOR!r}")
    st = lambda ig, g: f"InterestGroup.GetCountry.MakeScope.Var('{var(ig, g)}').GetValueWithDefault('(CFixedPoint)0')"
    cmp = lambda ig, g, op: f"{op}_CFixedPoint({st(ig, g)}, '(CFixedPoint)0')"

    def item(ig, g, op, w):
        return f"""widget = {{
	datacontext = "[GetGoods('{g}')]"
	visible = "[{cmp(ig, g, op)}]"
	size = {{ {w} {IDEO_H} }}
	tooltipwidget = {{
		FancyTooltip_Goods = {{
			blockoverride "goods_trend" {{  # the type itself fills tooltip_content_before, so ours went unseen
{_stance_text(lambda o: cmp(ig, g, o), 4)}			}}
		}}
	}}
	using = tooltip_above
	icon = {{
		size = {{ {IDEO_H} {IDEO_H} }}
		texture = "gfx/interface/market_view/trade_good_icon_bg.dds"
		color = "[Goods.GetCategoryColor]"
		icon = {{
			size = {{ 30 30 }}
			parentanchor = center
			texture = "[Goods.GetTexture]"
		}}
{_ind(_markers(lambda o: cmp(ig, g, o), 20, 'right'), 2)}	}}
	textbox = {{
		position = {{ {IDEO_H + 5} 0 }}
		size = {{ {w - IDEO_H - 5} {IDEO_H} }}
		align = nobaseline
		elide = right
		fontsize_min = 14
		text = "[Goods.GetNameNoFormatting]"
	}}
}}
"""

    groups = ""
    for ig, (_, fav, dis) in _POOLS.items():
        goods = list(fav) + [g for g in dis if g not in fav]
        if not goods:
            continue
        held = cmp(ig, goods[0], "NotEqualTo")
        for g in goods[1:]:
            held = f"Or({held}, {cmp(ig, g, 'NotEqualTo')})"
        col = lambda pool, op, w: (f"flowcontainer = {{\n\tdirection = vertical\n\tmin_width = {w}\n\tspacing = 5\n"
                                   f"\tignoreinvisible = yes\n{''.join(_ind(item(ig, g, op, w), 1) for g in pool)}}}\n")
        # rows 45 apart as Ideologies' (addrow), its second column nudged 10 right (its nudge widget and hbox spacing)
        # and as wide in all (2 x 260), so the two sections, each centered, line up. The right column always, empty when
        # the group opposes nothing (2026-11-19: without it the section was half as wide and sat centered)
        groups += f"""flowcontainer = {{
	visible = "[ObjectsEqual(InterestGroup.Self, InterestGroup.GetCountry.GetInterestGroupOfType('ig_{ig}'))]"
	spacing = 10
	ignoreinvisible = yes
{_ind(col(fav, "GreaterThan", IDEO_W) + col(dis, "LessThan", IDEO_W - 10), 1)}	textbox = {{
		visible = "[Not({held})]"
		size = {{ {2 * IDEO_W} {IDEO_H} }}
		align = nobaseline
		using = empty_state_text_properties
		text = "SPEC_IGS_PANEL_NONE"
	}}
}}
"""
    section = f"""flowcontainer = {{
	name = "spec_goods_stances"
	direction = vertical
	parentanchor = hcenter
	using = ig_panel_section_margins
	spacing = @gutter
	background = {{
		margin_left = 20
		margin_right = 20
		using = ig_panel_section_background
	}}
	textbox = {{
		autoresize = yes
		text = "SPEC_IGS_PANEL_HEAD"
		tooltip = "SPEC_IGS_PANEL_TT"
		align = nobaseline
		parentanchor = left
	}}
{_ind(groups, 1)}}}
"""
    return gui.replace(PANEL_ANCHOR, _ind(section, 5) + "\n" + PANEL_ANCHOR)


def loc():
    # the goods row's icon tooltip, before vanilla's interest group tooltip (context InterestGroup and Goods)
    amt = lambda mod: f"[{_amount(mod)}|+=0] approval for {_years(mod)}"
    import levers  # imports this module
    scaled = "Their [concept_approval] changes twice as much while [concept_powerful], and not at all while [concept_marginalized]."
    enc, res = "if we Encourage Investment in it", "if we Restrain Speculation in it"
    assert _years('spec_igs_backed') == _years('spec_igs_crossed')
    both = lambda m1, w1, m2, w2: f"[{_amount(m1)}|+=0] approval {w1}, [{_amount(m2)}|+=0] {w2}, for {_years(m1)}"
    iss = "if we float a Great Issue in it"
    fav_issue = (f"\\n• {amt('spec_igs_issue')} {iss}, and twice the loss from a [concept_spec_bust] or "
                 "[concept_spec_collapse] while it runs") if levers.ISSUE_ON else ""
    dis_issue = f"\\n• {amt('spec_igs_issue_against')} {iss}" if levers.ISSUE_ON else ""
    out = (f' SPEC_IGS_FAV_TT: "@approves! #bold Supports [Goods.GetNameNoFormatting]#!\\n{scaled}'
           f"\\n• {amt('spec_igs_boom')} when [concept_spec_investor_interest] in it rises to #v Eager#!"
           f"\\n• {amt('spec_igs_bust')} when its boom ends in a [concept_spec_bust] or [concept_spec_collapse], "
           f"and they may stop supporting it\\n• {both('spec_igs_backed', enc, 'spec_igs_crossed', res)}{fav_issue}\"\n"
           f' SPEC_IGS_DIS_TT: "@disapproves! #bold Opposes [Goods.GetNameNoFormatting]#!\\n{scaled}'
           f"\\n• {both('spec_igs_backed', res, 'spec_igs_crossed', enc)}{dis_issue}\"\n"
           # the column's header
           ' SPEC_IL_COL_IGS_TT: "#header [concept_interest_group] Stances#!\\n$TOOLTIP_DELIMITER$\\nEach '
           "$concept_interest_group$ @approves! supports a few of the [Concept('concept_good','$concept_goods$')] our "
           "[concept_market] trades, and some @disapproves! oppose one.\\n\\nTheir [concept_approval] rises and falls "
           "with the booms and busts of these goods and with our interventions in them, twice as much while "
           "[concept_powerful] and not at all while [concept_marginalized]. A new leader may change one of the group's stances.\"\n"
           # the interest group panel's section (panel_patch), headed as its Ideologies (IDEOLOGY_HEADER)
           " SPEC_IGS_PANEL_HEAD: \"[Concept('concept_good','$concept_goods$')]\"\n"
           ' SPEC_IGS_PANEL_TT: "#header Stances on Goods#!\\n$TOOLTIP_DELIMITER$\\nThe [InterestGroup.GetName] '
           "@approves! support a few of the goods their country trades, and may @disapproves! oppose one. Their "
           "[concept_approval] rises and falls with the booms and busts of these goods and with the government's "
           "interventions in them, twice as much while [concept_powerful] and not at all while [concept_marginalized]."
           "\\n\\nA new leader may change one of "
           'these stances."\n'
           ' SPEC_IGS_PANEL_NONE: "No stance on any good traded here"\n'
           # the Encourage and Restrain tooltips, as vanilla's approval changes from a law
           ' SPEC_IGS_LEVER_HEAD: "\\n\\n#title [concept_interest_group] approval changes#!"\n')
    # the strongest group's icon: every group holding the stance, strongest or not (context Goods, from the row)
    for op, key, _ in SIDES:
        has = _has(_stance, op)
        word, mark = ("Supported", "approves") if key == "FAV" else ("Opposed", "disapproves")
        out += (f' SPEC_IGS_ROW_{key}_ALL_TT: "#header {word} by#!\\n$TOOLTIP_DELIMITER$'
                + "".join(f"[AddLocalizationIf({has(ig)}, 'SPEC_IGS_WHO_{key}_{ig}')]" for ig in POOLS) + '"\n')
        out += "".join(f' SPEC_IGS_WHO_{key}_{ig}: "\\n@{mark}! [{_ig(ig)}.GetName] ([{_ig(ig)}.GetClout|v%1] '
                       f'[concept_clout])"\n' for ig in POOLS)
    for ig in POOLS:
        who = f"[{_ig(ig)}.GetName] ([{_ig(ig)}.GetClout|v%1] [concept_clout])"
        for k, up, down in (("", "spec_igs_backed", "spec_igs_crossed"), ("ISSUE_", "spec_igs_issue", "spec_igs_issue_against")):
            out += (f' SPEC_IGS_{k}UP_{ig}: "\\n@approves! {who}: [{_amount(up, _ig(ig))}|+=0] for {_years(up)}"\n'
                    f' SPEC_IGS_{k}DOWN_{ig}: "\\n@disapproves! {who}: [{_amount(down, _ig(ig))}|+=0] for {_years(down)}"\n')
    names = {"spec_igs_boom": ("Supported Trade Booming", "Investors are pouring money into a trade this group holds dear."),
             "spec_igs_bust": ("Supported Trade Bust", "A trade this group holds dear has gone bust, and they blame the government that let it happen."),
             "spec_igs_backed": ("Government Backs Their Trade", "The government has stepped into a market this group cares about, as they wished."),
             "spec_igs_crossed": ("Government Crosses Their Trade", "The government has stepped into a market this group cares about, against their wishes."),
             "spec_igs_issue": ("Shares in Their Trade", "The government has floated a Great Issue in a trade this group holds dear, and they have bought in."),
             "spec_igs_issue_against": ("Great Issue in a Trade They Oppose", "The government has floated a Great Issue in a trade this group opposes.")}
    out += "".join(f' {m}: "{n}"\n {m}_desc: "{d}"\n' for m, (n, d) in names.items())
    return out
