"""Game concepts for the mod's own terms: hoverable [concept_spec_x] links and entries in the concept browser."""
import companies
import cycle
import icons
import leverage
import tuning

# concept key suffix -> icon slot shown in its tooltip (None: no icon, like most vanilla concepts)
CONCEPTS = {"market_confidence": "je_markets", "speculative_mania": "state_mania", "financial_panic": "state_panic",
            "foreign_panic": "driver_foreign", "boom_end": "driver_crash", "correction": "driver_crash", "bust": "driver_crash", "collapse": "driver_crash", "investor_interest": "driver_boom",
            "credit_policy": None, "outstanding_credit": None, "long_depression": None,
            "speculative_excess": "crash_risk", "sound_finance": None, "banking_reforms": None,
            "intervention": None, "market_conditions": None, "baseline": None, "market_mood": None, "market_tie": None,
            "capital_flight": None, "war_news": None, "financial_centre": None, "blue_chip": "blue_chip", "company_strength": None, **({"leverage": None, "bad_debts": None} if leverage.ON else {}),
            **({"lending_standards": None} if cycle.ON else {}),
            **({"exchange": None} if tuning.get("EXCHANGE_ON", 1) else {})}  # centres.ON; its text is in centres.loc
LEVERAGE_LOC = "" if not leverage.ON else (
    ' concept_spec_leverage: "Credit Leverage"\n concept_spec_leverage_desc: "$concept_spec_leverage$ is the [concept_spec_outstanding_credit] of your [concept_country], '
    "measured in months of [concept_investment_pool] income.\\n\\n"
    f"Each whole month of it raises [concept_throughput] by #P {leverage.REWARD:+.0%}#!, up to #P {leverage.REWARD * leverage.REWARD_MAX:+.0%}#!. The bonus fades during a "
    f"[concept_spec_financial_panic] and while [concept_spec_bad_debts] remain. Beyond #v {leverage.SAFE}#! months, a "
    f'$concept_spec_financial_panic$ begins at a higher [concept_spec_market_confidence] and leaves $concept_spec_bad_debts$ behind."\n'
    ' concept_spec_bad_debts: "Bad Debts"\n concept_spec_bad_debts_desc: "$concept_spec_bad_debts$ are the losses a [concept_spec_financial_panic] leaves on the books of your banks. They grow with '
    f"[concept_spec_leverage] above #v {leverage.SAFE}#! months.\\n\\n"
    f"Each point reduces [concept_throughput] by #N {leverage.CRUNCH_THROUGHPUT:.1%}#! and investment by #N {leverage.CRUNCH_INVEST * 100:g}%#!. They build up for some months and then slowly decline, taking about "
    f'#v {round(leverage.CRUNCH_MAX / leverage.CRUNCH_FADE / 12)}#! years to clear at their worst. Banks will not lend while they remain. #v Lend to the Banks#! does not clear them, but #v Buy Up Bad Loans#! halves them, once while they last."\n')
# cycle.py's spec_lax: what the banks' care does and what moves it
LENDING_LOC = "" if not cycle.ON else (
    ' concept_spec_lending_standards: "Lending Standards"\n concept_spec_lending_standards_desc: "$concept_spec_lending_standards$ describe how '
    f'carefully the banks of your [concept_country] lend: {", ".join(f"#v {w}#!" for w in cycle.LAX_WORDS[:-1])} or #v {cycle.LAX_WORDS[-1]}#!. '
    "Laxer banks lend more into the [concept_investment_pool] and put more of it into booms, so those booms end harder and a Bank Rescue costs more."
    f"\\n\\nThey loosen a little in every month without a [concept_spec_financial_panic], from #v {cycle.LAX_WORDS[0]}#! to #v {cycle.LAX_WORDS[-1]}#! "
    f"in about #v {cycle.LAX_QUIET_YEARS}#! quiet years, and further after each Bank Rescue or #v Buy Up Bad Loans#!. They tighten when a boom ends, "
    'most of all when a $concept_spec_financial_panic$ runs its course without a Bank Rescue."\n')


def definitions():
    out = []
    for name, slot in CONCEPTS.items():
        tex = icons.path(icons.CONCEPT_ICON[name])
        out.append(f'concept_spec_{name} = {{\n\ttexture = "{tex}"\n}}\n' if tex else f"concept_spec_{name} = {{}}\n")
    return "\n".join(out)


# severity (generate.UNWINDS) -> concept, the interest a boom must peak at, the interest it falls to
ENDINGS = {1: ("correction", "Correction", "Keen", "Doubtful"), 2: ("bust", "Bust", "Eager", "Doubtful"),
           3: ("collapse", "Collapse", "Feverish", "Fleeing")}


def boom_end_loc(k, mc):
    """Boom Ending, and one concept per ending, as vanilla's concepts read: what it is, then what it does."""
    rate = {sev: r for sev, _, _, r, _ in k["UNWINDS"]}
    how = {1: "slightly", 2: f"more, about #v {rate[2] / rate[1]:g}#! times as much as a $concept_spec_correction$ for the same boom",
           3: f"sharply, about #v {rate[3] / rate[1]:.0f}#! times as much as a [concept_spec_correction] for the same boom"}
    rank = {1: "the mildest [concept_spec_boom_end]", 2: "a harsher [concept_spec_boom_end] than a [concept_spec_correction]",
            3: "the worst [concept_spec_boom_end]"}
    fall = {1: "falls back to", 2: "falls back to", 3: "falls all the way to"}
    techs = " and ".join(f"[GetTechnology('{t}').GetName]" for t in companies.TIE_TECHS)
    after = {3: " A $concept_spec_collapse$ in a large share of the [concept_market]'s trade can tip it into a [concept_spec_financial_panic]."}
    out = (f' concept_spec_boom_end: "Boom Ending"\n concept_spec_boom_ends: "Boom Endings"\n'
           f' concept_spec_boom_end_desc: "A boom ends when [concept_spec_investor_interest] in a [concept_good] falls back after a '
           f'rise, and the higher it went, the harder it falls: a boom that peaked at #v Keen#! ends in a [concept_spec_correction], '
           f'one that peaked at #v Eager#! in a [concept_spec_bust], and one that peaked at #v Feverish#! in a [concept_spec_collapse].'
           f'\\n\\nEach lowers your [{mc}], more for larger booms and for $concept_goods$ with a larger share of the [concept_market]\'s trade. '
           f'Investors then hold back while the $concept_good$ recovers, and where a [concept_company] makes it, its industry loses '
           f'[concept_throughput]. The peak it is measured from fades a little each month, so a boom that cools slowly ends more gently, '
           f'or without a $concept_spec_boom_end$ at all."\n')
    for sev, (key, name, peak, low) in ENDINGS.items():
        days = companies.UNWIND[sev][1]
        span = "a year" if days == 365 else f"#v {days}#! days"
        out += (f' concept_spec_{key}: "{name}"\n'
                f' concept_spec_{key}_desc: "A $concept_spec_{key}$ is {rank[sev]}. It occurs when '
                f'[concept_spec_investor_interest] in a [concept_good] that peaked at #v {peak}#! {fall[sev]} #v {low}#!.'
                f'\\n\\nIt lowers [{mc}] {how[sev]}. Investors then hold back from the $concept_good$ for '
                f'#v {k["GLUT_MONTHS"][sev]}#! months, and where a [concept_company] makes it, its industry loses '
                f'#N {-companies.COMPANY_BUST * companies.UNWIND[sev][0] * 100:g}%#! [concept_throughput] for {span}, '
                f'#N {companies.TIE_PER_TECH:.0%}#! more for each of {techs} researched.{after.get(sev, "")}"\n')
    return out


def companies_loc():
    """Blue Chip and Company Strength (design_companies.md), read from the honour and the Companies rows."""
    import centres  # ponytail: imported here, centres is the heavier module and only CO_STRENGTH is needed
    cos = "[Concept('concept_company','$concept_companies$')]"
    return (' concept_spec_blue_chip: "Blue Chip"\n concept_spec_blue_chips: "Blue Chips"\n'
            ' concept_spec_blue_chip_desc: "A $concept_spec_blue_chip$ is a [concept_company] that has held '
            f"#v {companies.BLUE_PROSPER:g}#! or more [concept_prosperity] for #v {companies.BLUE_MONTHS:g}#! months running. "
            f"Each one adds #v {companies.BLUE_BONUS:g}#! to our [concept_spec_company_strength].\\n\\n"
            f"#v {companies.BLUE_LOSE:g}#! months running below #v {companies.BLUE_PROSPER:g}#! end the status, and the "
            f"#v {companies.BLUE_MONTHS:g}#! months must then be held again. A month below resets a climb towards it. "
            'A [concept_country] that leaves the market economy keeps none."\n'
            ' concept_spec_company_strength: "Company Strength"\n'
            ' concept_spec_company_strength_desc: "$concept_spec_company_strength$ is the [concept_prosperity] of all of a '
            f"[concept_country]'s {cos} added together and divided by #v {centres.CO_STRENGTH:g}#!, so a company at "
            f"#v 100#! counts #v {100 / centres.CO_STRENGTH:g}#!, plus #v {companies.BLUE_BONUS:g}#! for each "
            '[concept_spec_blue_chip]. The Home of Great Companies honour goes to the strongest."\n')


def loc(k):
    goods = "[Concept('concept_good','$concept_goods$')]"
    buildings = "[Concept('concept_building','$concept_buildings$')]"
    mc = "concept_spec_market_confidence"
    return f""" concept_spec_market_confidence: "Market Confidence"
 concept_spec_market_confidence_desc: "$concept_spec_market_confidence$ measures how investors view the [concept_market] of your [concept_country], from #v 0#! (#v Panic#!) to #v 100#! (#v Mania#!). Fear slows investment and raises the interest on [concept_loans], while greed quickens it.\\n\\nBooming {goods} raise it, while [Concept('concept_spec_boom_end','$concept_spec_boom_ends$')], [Concept('concept_spec_foreign_panic','$concept_spec_foreign_panics$')], [Concept('concept_diplomatic_play','$concept_diplomatic_plays$')] and [concept_war] lower it. Booms and their endings are stronger where $building_financial_district$ make up more of the economy, and weaker where $building_manor_house$ outnumber them.\\n\\nAbove #v {k['CREDIT_FROM']}#! banks lend into the [concept_investment_pool], at #v {k['MANIA']}#! the market enters [concept_spec_speculative_mania], and below #v {k['PANIC']}#! a [concept_spec_financial_panic] begins."
 concept_spec_speculative_mania: "Speculative Mania"
 concept_spec_speculative_mania_desc: "Your [concept_market] is in $concept_spec_speculative_mania$ while [{mc}] is at #v {k['MANIA']}#! or more. Banks lend most freely into the [concept_investment_pool], but every [concept_spec_boom_end] costs more $concept_spec_market_confidence$. A long or very high mania lends support to [Concept('concept_political_movement','$concept_political_movements$')] that favor [GetLawType('law_laissez_faire').GetName] for some years afterward."
 concept_spec_financial_panic: "Financial Panic"
 concept_spec_financial_panics: "Financial Panics"
 concept_spec_financial_panic_desc: "A $concept_spec_financial_panic$ begins when your [{mc}] falls below its Panic Threshold of #v {k['PANIC']}#!.{' Past #v ' + str(leverage.SAFE) + '#! months of [concept_spec_leverage] the threshold rises, up to #v ' + str(k['PANIC'] + leverage.PANIC_SPAN) + '#!.' if leverage.ON else ''}{' With few $building_financial_district$ it is lower, down to #v ' + str(k['PANIC'] - k['PANIC_SHALLOW']) + '#!.' if k['PANIC_SHALLOW'] else ''}\\n\\nIt cuts the [concept_throughput] of every building and the taxes collected, draws on the [concept_treasury] each week for the relief of the jobless until it ends, slows [concept_private_construction] and investment, lowers the $concept_throughput$ bonus of [Concept('concept_company','$concept_companies$')], turns some investors into [Concept('concept_radical','$concept_radicals$')], and makes banks withdraw [concept_spec_outstanding_credit] from the [concept_investment_pool].\\n\\nEach linked [concept_country] suffers a [concept_spec_foreign_panic], while money flees to calm [Concept('concept_great_power','$concept_great_powers$')] elsewhere. For some years afterward, [Concept('concept_political_movement','$concept_political_movements$')] against [GetLawType('law_laissez_faire').GetName] gain support."
 concept_spec_foreign_panic: "Foreign Panic"
 concept_spec_foreign_panics: "Foreign Panics"
 concept_spec_foreign_panic_desc: "A $concept_spec_foreign_panic$ lowers your [{mc}] when a [concept_spec_financial_panic] begins in a [concept_country] tied to yours by a shared [concept_market], subjecthood, investment rights, heavy trade or ownership of your economy. Closer ties cause larger losses. [GetLawType('law_free_trade').GetName] strengthens trade ties, and other trade policies weaken them. An [concept_embargo] cuts the trade tie."
{boom_end_loc(k, mc)} concept_spec_investor_interest: "Investor Interest"
 concept_spec_investor_interest_desc: "$concept_spec_investor_interest$ is how attractive investors find the {buildings} producing a [concept_good]. It rises while the [concept_market_price] is above its long-run average and falls while it is below, from #v Fleeing#! to #v Feverish#!.\\n\\nThe [concept_throughput] of those buildings follows it, from #N {companies.INTEREST_THROUGHPUT[1]:+g}%#! at #v Fleeing#! to #P {companies.INTEREST_THROUGHPUT[6]:+g}%#! at #v Feverish#!, and so does the [concept_prosperity] of [Concept('concept_company','$concept_companies$')] making the $concept_good$. A booming $concept_good$ raises [{mc}]. When interest falls back, the boom ends in a [concept_spec_boom_end]."
 concept_spec_credit_policy: "Credit Policy"
 concept_spec_credit_policy_tight: "Tight Credit"
 concept_spec_credit_policy_normal: "Normal Credit"
 concept_spec_credit_policy_loose: "Loose Credit"
 concept_spec_credit_policy_desc: "$concept_spec_credit_policy$ sets how freely banks lend into the [concept_investment_pool]. It becomes available with [GetTechnology('central_banking').GetName] and can be $concept_spec_credit_policy_tight$, $concept_spec_credit_policy_normal$ or $concept_spec_credit_policy_loose$. Tighter credit slows investment and pulls [{mc}] down when it runs high, while looser credit adds to [concept_spec_outstanding_credit]. Once changed, it cannot be changed again for #v {k['STANCE_COOLDOWN']}#! months."
{LEVERAGE_LOC}{LENDING_LOC}{companies_loc()} concept_spec_outstanding_credit: "Outstanding Credit"
 concept_spec_outstanding_credit_desc: "$concept_spec_outstanding_credit$ is the credit banks have lent into the [concept_investment_pool] that has not yet been repaid. Banks lend while [{mc}] is above #v {k['CREDIT_FROM']}#!, up to a Lending Limit of #v {leverage.SAFE}#! months of pool income. [GetTechnology('{leverage.LADDER_TECHS[0]}').GetName] adds #v {leverage.LADDER_STEPS[0]}#! months, and [GetTechnology('{leverage.LADDER_TECHS[1]}').GetName] and [GetTechnology('{leverage.LADDER_TECHS[2]}').GetName] add #v {leverage.LADDER_STEPS[1]}#! each.\\n\\nA little of it is repaid from the pool each month, and when a [concept_spec_financial_panic] begins, the banks withdraw part of it.\\n\\n#lore Banks lent against railway shares in the 1840s, cotton in 1837 and building land in Vienna in 1873, and were caught when those booms broke.#!"
"""
