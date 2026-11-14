"""The finance techs' effects in this mod, shown in their tooltips as vanilla shows its own: modifier lines.

The modifiers are display only. The scripts still test has_technology_researched, so the tuned values stay where
they are; generate.tech_table() reads each line's value from the same constants the scripts use. files() injects
the lines into each tech's modifier block, beside vanilla's and other mods' lines.
"""
import re
import sys

import tuning

VANILLA_FILE = "common/technology/technologies/30_society.txt"  # the finance techs, read to check they exist
TECH_FILE = "common/technology/technologies/zzz_spec_techs.txt"  # loads after other mods' tech files
VANILLA_LAWS = "common/laws/01_economic_system.txt", "common/laws/01_trade_policy.txt"
LAW_FILE = "common/laws/zzz_spec_laws.txt"

# modifier -> (kind: pct, add or bool, colour of a positive value, name, description)
TYPES = {
    "country_spec_boom_size_mult": ("pct", "neutral", "Speculative Boom Size",
                                    "How much [concept_spec_market_confidence] each booming [concept_good] adds"),
    "country_spec_bank_lending_mult": ("pct", "neutral", "Credit Lent",
                                       "How much banks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is high"),
    "country_spec_boom_end_loss_mult": ("pct", "bad", "Boom End Losses",
                                        "[concept_spec_market_confidence] lost when a boom ends"),
    "country_spec_interest_response_mult": ("pct", "neutral", "Investor Reaction",
                                            "How quickly [concept_spec_investor_interest] follows the [concept_market_price]"),
    "country_spec_confidence_recovery_mult": ("pct", "good", "Market Confidence Recovery",
                                              "How quickly [concept_spec_market_confidence] returns to normal, and the economy recovers from a [concept_spec_long_depression]"),
    "country_spec_capital_flight_mult": ("pct", "good", "Capital Flight Gains",
                                         "[concept_spec_market_confidence] a calm [concept_great_power]"
                                         + (", or an [concept_spec_exchange] of International Standing or higher," if tuning.get("EXCHANGE_ON", 1) else "")  # centres.ON
                                         + " gains when money flees a [concept_spec_financial_panic] elsewhere"),
    "country_spec_foreign_ties_mult": ("pct", "bad", "Market and Investment Ties",
                                       "How strongly a [concept_spec_foreign_panic] reaches a [concept_country] through a shared [concept_market] or foreign investment"),
    "country_spec_foreign_loss_mult": ("pct", "bad", "Foreign Panic Losses",
                                       "[concept_spec_market_confidence] lost to a [concept_spec_foreign_panic]"),
    "country_spec_company_bust_mult": ("pct", "bad", "Company Losses After a Boom",
                                       "The [concept_throughput] [Concept('concept_company','$concept_companies$')] lose for a while after their [concept_good]'s boom ends"),
    "country_spec_rescue_cost_mult": ("pct", "bad", "Bank Rescue Cost",
                                      "The cost of #v Lend to the Banks#! in a [concept_spec_financial_panic]"),
    "country_spec_rescue_months_add": ("add", "bad", "Panic Months after a Bank Rescue",
                                       "Months a [concept_spec_financial_panic] lasts after #v Lend to the Banks#!"),
    "country_spec_credit_limit_add": ("add", "good", "Lending Limit (Months)",
                                      "Months of [concept_investment_pool] income banks will lend before they stop"),
    "country_spec_rescue_bool": ("bool", "good", "Can #v Lend to the Banks#! in a [concept_spec_financial_panic]",
                                 "The government can spend from the [concept_treasury] to end a [concept_spec_financial_panic] sooner"),
    "country_spec_excess_bool": ("bool", "neutral", "#v [concept_spec_speculative_excess]#! builds during booms",
                                 "A bubble builds while [concept_spec_market_confidence] is high, and bursts when it falls back"),
    "country_spec_credit_policy_bool": ("bool", "good", "Can set [concept_spec_credit_policy]",
                                        "The government can set how freely banks lend"),
    "country_spec_banknote_bool": ("bool", "good", "[concept_spec_banking_reforms]: #v Banknote Rules#!",
                                   "A Commission of Inquiry can enact the Currency School or Free Banking"),
    "country_spec_llr_bool": ("bool", "good", "[concept_spec_banking_reforms]: #v Lender of Last Resort#!",
                              "A Commission of Inquiry can name a lender of last resort"),
    "country_spec_company_law_bool": ("bool", "good", "[concept_spec_banking_reforms]: #v Company Law#!",
                                      "A Commission of Inquiry can make companies publish their accounts"),
    "country_spec_panic_length_mult": ("pct", "bad", "[concept_spec_financial_panic] Length",
                                       "How long a [concept_spec_financial_panic] lasts"),
    "country_spec_trade_tie_mult": ("pct", "bad", "Trade Ties",
                                    "How much a [concept_spec_foreign_panic] costs through heavy trade with the country in panic"),
    "country_spec_off_bool": ("bool", "neutral", "Investors do not speculate",
                              "No booms, no [concept_spec_financial_panic] and no [concept_spec_market_confidence] under this law"),
}


def definitions():
    out = []
    for key, (kind, color, _, _) in TYPES.items():
        body = "\tboolean = yes\n" if kind == "bool" else f"\tdecimals = 0\n" + ("\tpercent = yes\n" if kind == "pct" else "")
        out.append(f"{key} = {{\n\tscript_only = yes\n{body}\tcolor = {color}\n\tgame_data = {{\n\t\tai_value = 0\n\t}}\n}}\n")
    return "\n".join(out)


def _line(key, value):
    if TYPES[key][0] == "bool":
        return f"\t\t{key} = yes\n"
    return f"\t\t{key} = {round(value, 2 if TYPES[key][0] == 'pct' else 3):g}\n"  # whole percents: the game truncates


def inject(table):
    """table's lines (tech -> [(modifier, value)]) added to each tech's modifier block, as PEC does: INJECT merges
    them with vanilla's lines and other mods', where a copy of vanilla's file hid theirs or ours."""
    return "".join(f"INJECT:{tech} = {{\n\tmodifier = {{\n{''.join(_line(k, v) for k, v in lines)}\t}}\n}}\n\n"
                   for tech, lines in table.items())


def files(game, table, law_table):
    unknown = {k for lines in [*table.values(), *law_table.values()] for k, _ in lines} - TYPES.keys()
    assert not unknown, unknown
    for vanilla, keys in (((VANILLA_FILE,), table), (VANILLA_LAWS, law_table)):
        found = {key for rel in vanilla for key in re.findall(r"^(\w+) = \{", (game / rel).read_text(encoding="utf-8-sig"), re.M)}
        if keys.keys() - found:
            sys.exit(f"{vanilla} changed, can't find {keys.keys() - found}")
    return {TECH_FILE: inject(table), LAW_FILE: inject(law_table),
            "common/modifier_type_definitions/spec_tech_modifier_types.txt": definitions()}


def loc():
    return "".join(f' {k}: "{name}"\n {k}_desc: "{desc}"\n' for k, (_, _, name, desc) in TYPES.items())
