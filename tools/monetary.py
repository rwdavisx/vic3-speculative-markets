"""Monetary Standard: an economy law group of three laws. Bimetallism leaves the mod's figures as they are; the Gold
Standard and Fiat Money each move a few of them. The figures change where they are worked out: journal.reform_parts
adds parts() to the spec_reform_* multipliers (boom, heat, panic_len, rescue), and centres' spec_exch_loss adds
tail("loss"). generate.main calls build(write) and adds loc() to the English."""
import textwrap

import icons
import tech_ties

GROUP = "lawgroup_spec_monetary_standard"
# bimetallism first: a country with no law in the group gets it, whether the game or fill() picks
LAWS = ["bimetallism", "gold_standard", "fiat_money"]
GOLD_LOAN = -0.1            # vanilla's loan interest under the Gold Standard
# law -> {key: multiplier}. boom, heat, panic_len and rescue are journal.REFORMS keys; loss is the Exchange's Trust losses
# Bimetallism: two metals mean more coin to support the banks with, but Gresham's law drains the dearer metal abroad
# when a boom ends, so the fall is deeper
FX = {"bimetallism": {"rescue": 0.9, "risk": 1.1},
      "gold_standard": {"panic_len": 1.2, "loss": 0.8},
      "fiat_money": {"panic_len": 0.8, "rescue": 0.75, "boom": 1.1, "heat": 1.2, "loss": 1.25}}
# law variants (vanilla's parent = ..., as Isolationism's Canton System): each takes its parent's place beside the
# Economic System it suits, with stronger figures. variant -> (parent, economic system law, {key: its own multiplier, in place of
# its parent's}, name, description). SWAP moves a country between parent and variant whenever a law changes.
VARIANTS = {
    # the classical liberal order: lenders trust it more still, but money cannot grow in a crisis
    "classical_gold": ("gold_standard", "laissez_faire", {"loss": 0.7, "panic_len": 1.3}, "Classical Gold Standard",
                       "Sound money for free markets. Lenders trust our money all the more, but in a crisis the banks "
                       "cannot issue more than their gold allows."),
    # money that stretches with trade: panics end sooner, but cheap money feeds speculation (boom stays Fiat's)
    "elastic_currency": ("fiat_money", "interventionism", {"panic_len": 0.6, "heat": 1.3}, "Elastic Currency",
                         "Money that stretches with the needs of trade. The state can issue enough to end a panic sooner, "
                         "but the same cheap money feeds speculation."),
}
for _v, (_p, _, _x, *_) in VARIANTS.items():  # a variant's figures: its parent's, with its own in place
    FX[_v] = {**FX[_p], **_x}
# Command Economy can be enacted while on gold. SWAP then moves the country to Fiat Money.
NO_GOLD = "command_economy"
GOLD_AT_START = ["GBR"]     # on gold since 1821; the rest of the world was on silver or both metals in 1836
FIAT_TECH = "central_banking"
# each key's display-only modifier in the law tooltip (tech_ties.TYPES)
SHOWN = {"panic_len": "country_spec_panic_length_mult", "rescue": "country_spec_rescue_cost_mult",
         "boom": "country_spec_boom_size_mult", "risk": "country_spec_boom_end_loss_mult", "heat": "country_spec_excess_growth_mult", "loss": "country_spec_trust_loss_mult"}
tech_ties.TYPES.update({  # ponytail: registered with the tech lines so tech_ties writes their definitions and loc
    "country_spec_trust_loss_mult": ("pct", "bad", "[concept_spec_trust] Losses",
                                     "How much [concept_spec_trust] our [concept_spec_exchange] loses when booms end and in a [concept_spec_financial_panic]"),
    "country_spec_excess_growth_mult": ("pct", "bad", "[concept_spec_speculative_excess] Growth",
                                        "How fast [concept_spec_speculative_excess] builds while [concept_spec_market_confidence] is high"),
})
# interest group ideology -> views on (bimetallism, gold_standard, fiat_money)
VIEWS = {
    "ideology_laissez_faire": ("neutral", "approve", "disapprove"),         # Industrialists: sound money for creditors
    "ideology_liberal": ("neutral", "approve", "disapprove"),               # Intelligentsia: the classical economists
    "ideology_paternalistic": ("approve", "neutral", "disapprove"),         # Landowners: the bimetallist leagues
    "ideology_republican_paternalistic": ("approve", "neutral", "disapprove"),  # Landowners in a republic (history/global)
    "ideology_junker_paternalistic": ("approve", "neutral", "disapprove"),  # Prussia's: the Junkers led the bimetallists
    "ideology_magnatial": ("approve", "neutral", "disapprove"),  # British landed gentry
    "ideology_agrarian_jeffersonian": ("approve", "disapprove", "neutral"),
    "ideology_agrarian": ("approve", "disapprove", "neutral"),              # Rural Folk: indebted farmers, free silver
    "ideology_populist": ("neutral", "disapprove", "approve"),              # Trade Unions: the greenbackers
}
# Better Politics Mod strips law stances from the vanilla ideologies and gives them to its economy ideologies
# (ideology_eco_*), so they take the views of the vanilla ideology they are closest to. TRY_INJECT: skipped without BPM
BPM_VIEWS = {f"ideology_eco_{eco}": VIEWS[like] for like, ecos in {
    "ideology_laissez_faire": ("laissez_faire", "artisan", "modernizer"),  # creditors and gold-standard modernizers
    "ideology_paternalistic": ("traditional_agrarian", "conservative_agrarian", "serf_economy", "debt_serf_economy",
                               "trad_isolationist", "slave_economy", "antebellum_economy", "colonialist",
                               "slave_colonialist", "colonial_slavery_supporter"),  # the landed estates
    "ideology_agrarian": ("modern_agrarian", "agrarian_socialist", "agrarian_autarky", "distributist_economy"),  # indebted farmers
    "ideology_populist": ("interventionist", "modern_interventionist", "american_system", "socialist_mixed_economy",
                          "proletarian_economy", "socialist_autarky", "autarky", "centralized_economy"),  # money the state issues
}.items() for eco in ecos}


def has(law):
    return f"has_law = law_type:law_spec_{law}"


def parts(key):
    """(condition, multiplier) for each law and variant that changes this figure, as journal.reform_parts."""
    return [(has(law), fx[key]) for law, fx in FX.items() if key in fx]


def tail(key):
    """parts(key) as script value lines, multiplying whatever came before."""
    return "".join(f"\tif = {{\n\t\tlimit = {{ {c} }}\n\t\tmultiply = {n:g}\n\t}}\n" for c, n in parts(key))


# the year each went onto gold: from then the AI leans hard toward it (Germany after the French indemnity, the
# Scandinavian union, the Latin Monetary Union's limping standard, Austria-Hungary's crown, Witte's and Meiji reforms)
GOLD_DATES = {1854: ["POR"], 1871: ["GER", "PRU", "NGF"], 1873: ["USA", "SWE", "NOR", "DEN", "SCA"], 1875: ["NET"],
              1876: ["FRA", "BEL", "SWI", "ITA"], 1892: ["AUS", "HUN"], 1897: ["JAP", "RUS"]}
# those that suspended convertibility for their wars: greenbacks, the corso forzoso, Austrian and Russian paper
FIAT_AT_WAR = ["USA", "ITA", "SAR", "AUS", "RUS"]


def _add(cond, n):
    return f"\t\tif = {{\n\t\t\tlimit = {{ {cond} }}\n\t\t\tadd = {n}\n\t\t}}\n"


def _tags(tags):
    return "OR = { " + " ".join(f"c:{t} ?= this" for t in tags) + " }"


AI = {
    # silver's demonetization from 1873 left bimetallism a lost cause
    "bimetallism": "\t\tvalue = 0\n" + _add("game_date >= 1873.1.1", -50) + _add("game_date >= 1890.1.1", -50),
    # a bank of issue, a great power's standing and free trade made gold the respectable choice, more so as the
    # century went on; never in the middle of a war or a default
    "gold_standard": ("\t\tvalue = 0\n" + _add(f"has_technology_researched = {FIAT_TECH}", 50)
                      + _add("country_rank >= rank_value:great_power", 50) + _add("country_rank = rank_value:major_power", 25)
                      + _add("has_law = law_type:law_free_trade", 25)
                      + _add("game_date >= 1870.1.1", 50) + _add("game_date >= 1890.1.1", 50)
                      + "".join(_add(f"game_date >= {y}.1.1 {_tags(tags)}", 200) for y, tags in GOLD_DATES.items())
                      + _add("OR = { is_at_war = yes in_default = yes }", -150)),
    # paper money for a war, a default, crushing debt or a long slump; later, for a state that runs the economy
    "fiat_money": ("\t\tvalue = -50\n" + _add("is_at_war = yes", 150) + _add("in_default = yes", 150)
                   + _add("scaled_debt >= 0.5", 75) + _add("has_variable = spec_panic", 50) + _add("has_variable = spec_ld", 75)
                   + _add(f"is_at_war = yes {_tags(FIAT_AT_WAR)}", 100)
                   + _add("game_date >= 1900.1.1 has_law = law_type:law_interventionism", 50)
                   + _add("has_law = law_type:law_command_economy", 100)),
}


def _law(law):
    parent, econ = VARIANTS[law][:2] if law in VARIANTS else (law, None)
    lines = ([("country_loan_interest_rate_mult", GOLD_LOAN)] if parent == "gold_standard" else []) + [
        (SHOWN[k], round(n - 1, 2)) for k, n in FX.get(law, {}).items()]
    tech = f"\tunlocking_technologies = {{\n\t\t{FIAT_TECH}\n\t}}\n\n" if parent == "fiat_money" else ""
    if parent == "gold_standard":
        tech = f"\tdisallowing_laws = {{\n\t\tlaw_{NO_GOLD}\n\t}}\n\n"
    # Show each variant beside its Economic System, and its parent elsewhere.
    var = [e for p, e, *_ in VARIANTS.values() if p == law]
    vis = (f"\tparent = law_spec_{parent}\n\n\tis_visible = {{\n\t\thas_law_or_variant = law_type:law_{econ}\n\t}}\n\n" if econ
           else f"\tis_visible = {{\n\t\tNOT = {{ has_law_or_variant = law_type:law_{var[0]} }}\n\t}}\n\n" if var else "")
    return (f"law_spec_{law} = {{\n\tgroup = {GROUP}\n{vis}\ticon = \"{icons.path(f'law_spec_{parent}')}\"\n\n"
            f"\tprogressiveness = {50 if parent == 'fiat_money' else 0}\n\n{tech}"
            "\tmodifier = {\n" + "".join(f"\t\t{k} = {v:g}\n" for k, v in lines) + "\t}\n\n"
            f"\tai_enact_weight_modifier = {{\n{AI[parent]}\t}}\n}}\n")


# whenever a law changes (on_law_activated, the owner's scope): a parent becomes its variant beside the variant's
# Economic System and back elsewhere; a Gold Standard under a Command Economy becomes Fiat Money
SWAP = "".join(
    f"\t\tif = {{\n\t\t\tlimit = {{ {has(p)} has_law_or_variant = law_type:law_{e} }}\n\t\t\tactivate_law = law_type:law_spec_{v}\n\t\t}}\n"
    f"\t\telse_if = {{\n\t\t\tlimit = {{ {has(v)} NOT = {{ has_law_or_variant = law_type:law_{e} }} }}\n"
    f"\t\t\tactivate_law = law_type:law_spec_{p}\n\t\t}}\n" for v, (p, e, *_) in VARIANTS.items()) + (
    f"\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\tOR = {{ {has('gold_standard')} {has('classical_gold')} }}\n"
    f"\t\t\t\thas_law_or_variant = law_type:law_{NO_GOLD}\n\t\t\t}}\n\t\t\tactivate_law = law_type:law_spec_fiat_money\n\t\t}}\n")


# a country with no law in the group (a save from before 1.2, or one the game left empty) gets one
FILL = (f"\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\tNOR = {{\n" + "".join(f"\t\t\t\t\t{has(law)}\n" for law in [*LAWS, *VARIANTS])
        + "\t\t\t\t}\n\t\t\t}\n"
        + "".join(f"\t\t\t{'if' if i == 0 else 'else_if'} = {{\n\t\t\t\tlimit = {{ c:{tag} ?= this }}\n"
                  f"\t\t\t\tactivate_law = law_type:law_spec_gold_standard\n\t\t\t}}\n" for i, tag in enumerate(GOLD_AT_START))
        + "\t\t\telse = {\n\t\t\t\tactivate_law = law_type:law_spec_bimetallism\n\t\t\t}\n\t\t}\n")


def build(write):
    write("common/law_groups/spec_law_groups.txt",
          f"{GROUP} = {{\n\tlaw_group_category = economy\n\tideological_opinion_impact = 0.5\n}}\n")
    # each variant after its parent: the law panel lists them in file order
    write("common/laws/spec_monetary_laws.txt", "\n".join(
        _law(law) for p in LAWS for law in [p] + [v for v, (vp, *_) in VARIANTS.items() if vp == p]))
    # INJECT adds the views beside vanilla's and other mods'; zzz_ loads after files that REPLACE these ideologies
    write("common/ideologies/zzz_spec_monetary_ideologies.txt", "".join(
        f"{mode}:{ideology} = {{\n\t{GROUP} = {{\n" + "".join(f"\t\tlaw_spec_{law} = {v}\n" for law, v in zip(LAWS, views))
        + "\t}\n}\n\n" for mode, views_of in (("INJECT", VIEWS), ("TRY_INJECT", BPM_VIEWS))
        for ideology, views in views_of.items()))
    # a new campaign: the historical standards, then everyone else on Bimetallism; a running campaign: monthly
    starts = "".join(f"\t\tc:{tag} ?= {{\n\t\t\tactivate_law = law_type:law_spec_gold_standard\n\t\t}}\n" for tag in GOLD_AT_START)
    every = "\t\tevery_country = {\n" + textwrap.indent(FILL, "\t") + "\t\t}\n"
    write("common/on_actions/spec_monetary_on_actions.txt",
          "on_game_started = {\n\ton_actions = { spec_money_start }\n}\n\n"
          "on_monthly_pulse_country = {\n\ton_actions = { spec_money_pulse }\n}\n\n"
          "on_law_activated = {\n\ton_actions = { spec_money_swap }\n}\n\n"
          f"spec_money_start = {{\n\teffect = {{\n{starts}{every}\t}}\n}}\n\n"
          f"spec_money_pulse = {{\n\teffect = {{\n{FILL}\t}}\n}}\n\n"
          f"spec_money_swap = {{\n\teffect = {{\n\t\towner = {{\n{textwrap.indent(SWAP, chr(9))}\t\t}}\n\t}}\n}}\n")


def loc():
    return ("".join(f' law_spec_{v}: "{name}"\n law_spec_{v}_desc: "{desc}"\n' for v, (*_, name, desc) in VARIANTS.items())
            + f' {GROUP}: "Monetary Standard"\n'
            f' {GROUP}_desc: "What stands behind the currency, and how freely it can be issued."\n'
            ' law_spec_bimetallism: "Bimetallism"\n'
            ' law_spec_bimetallism_desc: "The mint coins both gold and silver at a fixed ratio, so there is more coin to go '
            'round. But whenever the market strays from that ratio, the dearer metal is hoarded or sent abroad."\n'
            ' law_spec_gold_standard: "Gold Standard"\n'
            ' law_spec_gold_standard_desc: "Every banknote may be exchanged for a fixed weight of gold. Lenders trust such '
            f'money, but in a panic the banks can issue no more than their gold allows."\n'
            ' law_spec_fiat_money: "Fiat Money"\n'
            ' law_spec_fiat_money_desc: "The currency rests on nothing but the government\'s word. New money can rescue the '
            f'banks and keep credit flowing, but investors put less faith in it."\n')


if __name__ == "__main__":
    out = {}
    build(lambda rel, text: out.__setitem__(rel, text))
    for rel, text in out.items():
        assert text.count("{") == text.count("}"), rel
    laws = out["common/laws/spec_monetary_laws.txt"]
    assert laws.index("law_spec_bimetallism") < laws.index("law_spec_gold_standard")
    assert "country_spec_panic_length_mult = 0.2" in laws and "country_spec_rescue_cost_mult = -0.25" in laws
    assert "country_loan_interest_rate_mult = -0.1" in laws and laws.count("unlocking_technologies") == 2
    assert tail("loss").count("multiply") == 4 and not parts("credit")
    assert FX["classical_gold"] == {"panic_len": 1.3, "loss": 0.7} and FX["elastic_currency"] == {**FX["fiat_money"], "panic_len": 0.6, "heat": 1.3}
    # classical gold: -30% Trust losses, +32% panic length, beside Laissez-Faire only; plain gold hidden there
    assert "parent = law_spec_gold_standard" in laws and "country_spec_trust_loss_mult = -0.3" in laws
    assert "NOT = { has_law_or_variant = law_type:law_laissez_faire }" in laws
    assert laws.index("law_spec_gold_standard =") < laws.index("law_spec_classical_gold =") < laws.index("law_spec_fiat_money =")
    ideo = out["common/ideologies/zzz_spec_monetary_ideologies.txt"]
    assert len(BPM_VIEWS) == 25 and ideo.count("TRY_INJECT:ideology_eco_") == 25 and "TRY_INJECT:ideology_liberal" not in ideo
    on = out["common/on_actions/spec_monetary_on_actions.txt"]
    assert "activate_law = law_type:law_spec_elastic_currency" in on and "law_command_economy" in SWAP
    assert "law_spec_classical_gold" in FILL and "common/laws/zzz_spec_monetary_inject.txt" not in out
    assert "disallowing_laws = {\n\t\tlaw_command_economy" in laws and "With [" not in loc()
    assert "country_spec_rescue_cost_mult = -0.1" in laws and "country_spec_boom_end_loss_mult = 0.1" in laws
    assert "game_date >= 1871.1.1 OR = { c:GER ?= this" in laws and laws.count("add = 200") == 2 * len(GOLD_DATES)  # gold and its variant
    print("monetary ok")
