"""Financial Integration: a power bloc principle group of three levels, bought with mandates like vanilla's.

1. A Financial Panic in one participant costs the others SHELTER of the confidence it would (spec_catch_panic).
2. Members may lend up to SHARE of the months by which the leader's Lending Limit exceeds theirs.
3. The leader's Exchange draws on its members' capital once more (centres.spec_xs_reach; still at most its own).

The modifiers named country_spec_bloc_* are display only, as tech_ties': the scripts test the principle itself.
ponytail: a cross-border Lend to the Banks was left out (a second rescue path, a target picker and its GUI).
The loan cuts (members -10%, leader -5%) went in 1.2: they stacked past -100% with vanilla's (centres.WORLD_FX).
"""
import icons
import leverage

GROUP = "principle_group_spec_financial_integration"
LEVELS = [f"principle_spec_financial_integration_{n}" for n in (1, 2, 3)]
SHELTER = 0.75     # share of a bloc member's panic hit a participant takes
SHARE = 0.5        # share of the leader's Lending Limit lead a member gains, whole months
ICON = "principle_financial_integration"

# hooks: generate's spec_credit_limit and centres.spec_xs_reach (scope:spec_xs_me is the market); generate's
# spec_catch_panic multiplies by spec_pb_shelter
LIMIT_REF = "\tadd = spec_pb_limit\n" if leverage.ON else ""
REACH_REF = (f"\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\tis_power_bloc_leader = yes\n\t\t\t\tpower_bloc = {{ has_principle = principle:{LEVELS[2]} }}\n\t\t\t}}\n"
             "\t\t\tevery_country = {\n\t\t\t\tlimit = {\n\t\t\t\t\thas_variable = spec_xs_inc\n\t\t\t\t\tNOT = { this = scope:spec_xs_me }\n"
             "\t\t\t\t\tis_in_power_bloc = yes\n\t\t\t\t\tpower_bloc ?= scope:spec_xs_me.power_bloc\n\t\t\t\t}\n"
             "\t\t\t\tadd = var:spec_xs_inc\n\t\t\t}\n\t\t}\n")

TYPES = {  # key: (kind, colour of a positive value, name, description), as tech_ties.TYPES
    "country_spec_bloc_contagion_mult": ("pct", "bad", "Panic Losses from the Power Bloc",
                                         "[concept_spec_market_confidence] lost when a [concept_spec_financial_panic] starts in another country of our [concept_power_bloc]"),
    "country_spec_bloc_credit_bool": ("bool", "good", "Banks share the Lending Limit of the [concept_power_bloc_leader]",
                                      f"Our Lending Limit rises by #v {SHARE:.0%}#! of the months by which the Lending Limit of the $concept_power_bloc_leader$ exceeds ours"),
    "country_spec_bloc_reach_bool": ("bool", "good", "Our [concept_spec_exchange] draws on the capital of the [concept_power_bloc]",
                                     "The capital of every member counts toward the size of our $concept_spec_exchange$ once more, up to our own"),
}


def principle(n):
    # the engine rejects the doc's participant_modifier: member_modifier is the whole bloc, non_leader_modifier the
    # members without the leader (as vanilla's principle_exploit_members)
    blocks = {"member_modifier": {"country_spec_bloc_contagion_mult": SHELTER - 1},
              "non_leader_modifier": {"country_spec_bloc_credit_bool": "yes"} if n >= 2 else {},
              "leader_modifier": {"country_spec_bloc_reach_bool": "yes"} if n >= 3 else {}}
    mods = "".join(f"\t{name} = {{\n" + "".join(f"\t\t{k} = {v:g}\n" if isinstance(v, float) else f"\t\t{k} = {v}\n" for k, v in d.items())
                   + "\t}\n" for name, d in blocks.items() if d)
    return (f"{LEVELS[n - 1]} = {{\n\ticon = \"{icons.path(ICON)}\"\n"
            f"\tbackground = \"gfx/interface/icons/principles_icons/principle_tier_{n}.dds\"\n\n"
            + ("\tvisible = {\n\t\thas_dlc_feature = power_bloc_features\n\t}\n\n" if n == 1 else "")
            + mods + "\n" + ai_weight(n) + "}\n")


def ai_weight(n):
    """The leader's (root) case for each level, against vanilla's 100-300 for a new group and 1000 for an upgrade.
    Each level pays off differently: 1 shelters a bloc whose markets panic, 2 lends the leader's credit to members, 3
    feeds the leader's Exchange, so each weighs what that level buys."""
    def when(limit, op):
        return f"\t\tif = {{\n\t\t\tlimit = {{ {limit} }}\n\t\t\t{op}\n\t\t}}\n"
    panicked = ("power_bloc ?= { any_power_bloc_member = { count >= 2 OR = { has_variable = spec_panic "
                "has_variable = spec_panic_cooldown } } }")
    stand = lambda s: f"has_variable = spec_exch_stand var:spec_exch_stand >= {s}"
    small = "power_bloc ?= { num_power_bloc_members < 3 }"  # a bloc of two or three gains little
    lines = {
        # a bloc that has felt panics, a leader with credit and an Exchange; worth 300 with all of them, as vanilla's best
        1: ["value = 50", when(panicked, "add = 100"), when("has_variable = spec_panic", "add = 50"),
            when(stand(1), "add = 50"), when(stand(2), "add = 50"),
            when("has_technology_researched = central_banking", "add = 25"),
            when("has_strategy = ai_strategy_economic_imperialism", "multiply = 1.5"), when(small, "multiply = 0.5")],
        # members borrow on the leader's Lending Limit: worth it once the bloc is a real one
        2: ["value = 1000", when(small, "multiply = 0.3")],
        # the leader's Exchange counts members' capital: nothing to feed without one of standing
        3: ["value = 1000", when("NOT = { has_variable = spec_exch_stand }", "multiply = 0.2"),
            when("has_variable = spec_exch_stand var:spec_exch_stand < 1", "multiply = 0.3"), when(small, "multiply = 0.3")],
    }[n]
    return "\tai_weight = {\n" + "".join(l if l.startswith("\t") else f"\t\t{l}\n" for l in lines) + "\t}\n"


def values():
    base = leverage.limit(__import__("centres").LIMIT_REF).replace("spec_credit_limit", "spec_pb_base_limit", 1)
    either = f"OR = {{ has_principle = principle:{LEVELS[1]} has_principle = principle:{LEVELS[2]} }}"
    return (
        # in spec_catch_panic: root panicked, this country catches it
        f"spec_pb_shelter = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{\n\t\t\tis_in_power_bloc = yes\n\t\t\tis_in_same_power_bloc = root\n"
        f"\t\t\tpower_bloc = {{ has_principle_group = principle_group:{GROUP} }}\n\t\t}}\n\t\tvalue = {SHELTER:g}\n\t}}\n}}\n"
        + (f"# spec_credit_limit without this module's share, so the leader's is read without recursion\n{base}\n"
           f"spec_pb_limit = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{\n\t\t\tis_in_power_bloc = yes\n\t\t\tis_power_bloc_leader = no\n"
           f"\t\t\tpower_bloc = {{ {either} }}\n\t\t}}\n\t\tvalue = power_bloc.power_bloc_leader.spec_pb_base_limit\n"
           f"\t\tsubtract = spec_pb_base_limit\n\t\tmultiply = {SHARE:g}\n\t\tfloor = yes\n\t\tmin = 0\n\t}}\n}}\n"
           if leverage.ON else ""))


def definitions():
    return "\n".join(f"{k} = {{\n\tscript_only = yes\n" + ("\tboolean = yes\n" if kind == "bool" else "\tdecimals = 0\n\tpercent = yes\n")
                     + f"\tcolor = {color}\n\tgame_data = {{\n\t\tai_value = 0\n\t}}\n}}\n" for k, (kind, color, _, _) in TYPES.items())


def build(write):
    write("common/power_bloc_principle_groups/spec_bloc_principle_groups.txt",
          f"# open to every identity, primary for none (power_bloc.py)\n{GROUP} = {{\n\tlevels = {{\n"
          + "".join(f"\t\t{p}\n" for p in LEVELS) + "\t}\n}\n")
    write("common/power_bloc_principles/spec_bloc_principles.txt", "\n".join(principle(n) for n in (1, 2, 3)))
    write("common/script_values/spec_bloc_values.txt", values())
    write("common/modifier_type_definitions/spec_bloc_modifier_types.txt", definitions())


def loc():
    panic = "[Concept('concept_spec_financial_panic','$concept_spec_financial_panic$')]"
    return (f' {GROUP}: "Financial Integration"\n'
            f" {GROUP}_desc: \"The banks and exchanges of the [Concept('concept_power_bloc_member', '$concept_power_bloc_members_short|q$')] "
            f"lend to one another and to the [Concept('concept_power_bloc_leader','$concept_power_bloc_leader_short|q$')], so that a "
            f"{panic} in one market shakes the others less and the leader's money market serves the whole $concept_power_bloc$.\"\n"
            + "".join(f' {p}_desc: "${GROUP}_desc$"\n' for p in LEVELS)
            + "".join(f' {k}: "{name}"\n {k}_desc: "{desc}"\n' for k, (_, _, name, desc) in TYPES.items()))
