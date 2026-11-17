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
            **({"exchange": None, "trust": None} if tuning.get("EXCHANGE_ON", 1) else {})}  # centres.ON; its text is in centres.loc
LEVERAGE_LOC = "" if not leverage.ON else (
    ' concept_spec_leverage: "Credit Leverage"\n concept_spec_leverage_desc: "#italic How much your banks have lent. It is your [concept_spec_outstanding_credit], '
    "counted in months of [concept_investment_pool] income.#!\\n\\n"
    f"#P {leverage.REWARD:+.0%}#! [concept_throughput] for each whole month of it, up to #P {leverage.REWARD * leverage.REWARD_MAX:+.0%}#!\\nThe bonus fades during a "
    f"[concept_spec_financial_panic] and while [concept_spec_bad_debts] remain\\n\\nOver #v {leverage.SAFE}#! months it gets risky:\\n"
    f'#N A $concept_spec_financial_panic$ starts sooner#!, at a higher [concept_spec_market_confidence]\\n#N It leaves $concept_spec_bad_debts$ behind#!"\n'
    ' concept_spec_bad_debts: "Bad Debts"\n concept_spec_bad_debts_desc: "#italic The losses a [concept_spec_financial_panic] leaves on the books of your banks.#!\\n\\nThey grow with '
    f"[concept_spec_leverage] over #v {leverage.SAFE}#! months\\n\\n"
    f"Each point: #N -{leverage.CRUNCH_THROUGHPUT:.1%}#! [concept_throughput] and #N -{leverage.CRUNCH_INVEST * 100:g}%#! investment\\nThey build up for some months, then slowly shrink\\nAt their worst they take about "
    f'#v {round(leverage.CRUNCH_MAX / leverage.CRUNCH_FADE / 12)}#! years to clear\\n#N Banks will not lend#! while they remain\\n\\n#v Lend to the Banks#! does not clear them\\n#v Buy Up Bad Loans#! halves them, once while they last"\n')
# cycle.py's spec_lax: what the banks' care does and what moves it
LENDING_LOC = "" if not cycle.ON else (
    ' concept_spec_lending_standards: "Lending Standards"\n concept_spec_lending_standards_desc: "#italic How '
    f'carefully the banks of your [concept_country] lend. It can be {", ".join(f"#v {w}#!" for w in cycle.LAX_WORDS[:-1])} or #v {cycle.LAX_WORDS[-1]}#!.#!\\n\\n'
    "Laxer banks lend more into the [concept_investment_pool] and put more of it into booms\\n#N So booms end harder#! and a Bank Rescue costs more"
    f"\\n\\n#N Get laxer#! a little each month without a [concept_spec_financial_panic], going from #v {cycle.LAX_WORDS[0]}#! to #v {cycle.LAX_WORDS[-1]}#! "
    f"in about #v {cycle.LAX_QUIET_YEARS}#! quiet years\\n#N Get laxer still#! after each Bank Rescue or #v Buy Up Bad Loans#!\\n#P Get stricter#! when a boom ends, "
    'most of all when a $concept_spec_financial_panic$ runs its course without a Bank Rescue"\n')


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
    how = {1: "a little", 2: f"more, about #v {rate[2] / rate[1]:g}#! times as much as a $concept_spec_correction$ after the same boom",
           3: f"sharply, about #v {rate[3] / rate[1]:.0f}#! times as much as a [concept_spec_correction] after the same boom"}
    rank = {1: "the mildest [concept_spec_boom_end]", 2: "a harsher [concept_spec_boom_end] than a [concept_spec_correction]",
            3: "the worst [concept_spec_boom_end]"}
    fall = {1: "falls back to", 2: "falls back to", 3: "falls all the way to"}
    techs = " and ".join(f"[GetTechnology('{t}').GetName]" for t in companies.TIE_TECHS)
    after = {3: "\\n\\nWorst of all, a $concept_spec_collapse$ in a big part of the [concept_market]'s trade can set off a [concept_spec_financial_panic]"}
    out = (f' concept_spec_boom_end: "Boom Ending"\n concept_spec_boom_ends: "Boom Endings"\n'
           f' concept_spec_boom_end_desc: "#italic What goes up comes down. A boom ends when [concept_spec_investor_interest] in a [concept_good] drops back after a '
           f'rise.#!\\n\\nThe higher it went, the harder it falls:\\nPeaked at #v Keen#!: a [concept_spec_correction]\\n'
           f'Peaked at #v Eager#!: a [concept_spec_bust]\\nPeaked at #v Feverish#!: a [concept_spec_collapse]'
           f'\\n\\n#N Lowers#! your [{mc}], more for bigger booms and for $concept_goods$ that are a bigger part of the [concept_market]\'s trade\\n'
           f'Investors then stay away while the $concept_good$ recovers\\nIf a [concept_company] makes it, that industry #N loses#! '
           f'[concept_throughput]\\n\\n#instruction The peak fades a little each month. A boom that cools slowly ends more gently, '
           f'or with no $concept_spec_boom_end$ at all.#!"\n')
    for sev, (key, name, peak, low) in ENDINGS.items():
        days = companies.UNWIND[sev][1]
        span = "a year" if days == 365 else f"#v {days}#! days"
        out += (f' concept_spec_{key}: "{name}"\n'
                f' concept_spec_{key}_desc: "#italic A $concept_spec_{key}$ is {rank[sev]}.#!\\n\\nHappens when '
                f'[concept_spec_investor_interest] in a [concept_good] that peaked at #v {peak}#! {fall[sev]} #v {low}#!'
                f'\\n\\n#N Lowers#! [{mc}] {how[sev]}\\nInvestors stay away from the $concept_good$ for '
                f'#v {k["GLUT_MONTHS"][sev]}#! months\\nIf a [concept_company] makes it, that industry loses '
                f'#N {-companies.COMPANY_BUST * companies.UNWIND[sev][0] * 100:g}%#! [concept_throughput] for {span}, '
                f'#N {companies.TIE_PER_TECH:.0%}#! more for each of {techs} researched{after.get(sev, "")}"\n')
    return out


def companies_loc():
    """Blue Chip and Company Strength (design_companies.md), read from the honour and the Companies rows."""
    import centres  # ponytail: imported here, centres is the heavier module and only CO_STRENGTH is needed
    cos = "[Concept('concept_company','$concept_companies$')]"
    return (' concept_spec_blue_chip: "Blue Chip"\n concept_spec_blue_chips: "Blue Chips"\n'
            ' concept_spec_blue_chip_desc: "#italic A star [concept_company] that has held '
            f"#v {companies.BLUE_PROSPER:g}#! or more [concept_prosperity] for #v {companies.BLUE_MONTHS:g}#! months in a row.#!\\n\\n"
            f"Each one adds #v {companies.BLUE_BONUS:g}#! to our [concept_spec_company_strength]\\n"
            + __import__("bluechips").effects_text().replace("[concept_spec_blue_chip]", "$concept_spec_blue_chip$") + "\\n\\n"
            f"#N Lost#! after #v {companies.BLUE_LOSE:g}#! months in a row below #v {companies.BLUE_PROSPER:g}#!, and then the "
            f"#v {companies.BLUE_MONTHS:g}#! months start over\\nOne month below resets a climb toward it\\n"
            'A [concept_country] that leaves the market economy keeps none"\n'
            ' concept_spec_company_strength: "Company Strength"\n'
            ' concept_spec_company_strength_desc: "#italic How strong a '
            f"[concept_country]'s {cos} are, all together.#!\\n\\nEach company adds its [concept_prosperity] divided by #v {centres.CO_STRENGTH:g}#!, so one at "
            f"#v 100#! adds #v {100 / centres.CO_STRENGTH:g}#!\\nEach [concept_spec_blue_chip] adds #v {companies.BLUE_BONUS:g}#! more\\n"
            'The strongest wins the Home of Great Companies honour"\n')


def loc(k):
    goods = "[Concept('concept_good','$concept_goods$')]"
    buildings = "[Concept('concept_building','$concept_buildings$')]"
    mc = "concept_spec_market_confidence"
    return f""" concept_spec_market_confidence: "Market Confidence"
 concept_spec_market_confidence_desc: "#italic How investors feel about the [concept_market] of your [concept_country], from #v 0#! (#v Panic#!) to #v 100#! (#v Mania#!).#!\\n\\nFear #N slows investment#! and makes [concept_loans] cost more\\nGreed #P speeds investment up#!\\n\\n#P Rises#! with booming {goods}\\n#N Falls#! with [Concept('concept_spec_boom_end','$concept_spec_boom_ends$')], [Concept('concept_spec_foreign_panic','$concept_spec_foreign_panics$')], [Concept('concept_diplomatic_play','$concept_diplomatic_plays$')] and [concept_war]\\nBooms and their endings are bigger where $building_financial_district$ make up more of the economy, and smaller where $building_manor_house$ outnumber them\\n\\nBanks lend into the [concept_investment_pool] above #v {k['CREDIT_FROM']}#!\\nA [concept_spec_speculative_mania] comes at #v {k['MANIA']}#! or more\\nA [concept_spec_financial_panic] begins below #v {k['PANIC']}#!{"\\nHigh [concept_spec_leverage] raises that line\\nFew $building_financial_district$ lower it a little" if leverage.ON else ""}"
 concept_spec_speculative_mania: "Speculative Mania"
 concept_spec_speculative_mania_desc: "#italic Your [concept_market] has gone wild with greed.#!\\n\\nIt lasts while [{mc}] is #v {k['MANIA']}#! or more\\n#P Banks lend most freely#! into the [concept_investment_pool]\\n#N Every [concept_spec_boom_end] costs more#! $concept_spec_market_confidence$\\n\\nA long or very high mania helps [Concept('concept_political_movement','$concept_political_movements$')] that want [GetLawType('law_laissez_faire').GetName] for some years after"
 concept_spec_financial_panic: "Financial Panic"
 concept_spec_financial_panics: "Financial Panics"
 concept_spec_financial_panic_desc: "#italic A crash, when investors flee and the banks pull their money back.#!\\n\\nStarts when your [{mc}] falls below #v {k['PANIC']}#!.{' Over #v ' + str(leverage.SAFE) + '#! months of [concept_spec_leverage], that line rises, up to #v ' + str(k['PANIC'] + leverage.PANIC_SPAN) + '#!.' if leverage.ON else ''}{' With few $building_financial_district$ it drops, down to #v ' + str(k['PANIC'] - k['PANIC_SHALLOW']) + '#!.' if k['PANIC_SHALLOW'] else ''}\\n\\nWhile it lasts:\\n#N Less#! [concept_throughput] in every building, and fewer taxes collected\\n#N Drains#! the [concept_treasury] every week to help the jobless\\n#N Slower#! [concept_private_construction] and investment\\n#N Smaller#! $concept_throughput$ bonus for [Concept('concept_company','$concept_companies$')]\\n#N Some investors turn#! [Concept('concept_radical','$concept_radicals$')]\\n#N Banks pull back#! [concept_spec_outstanding_credit] from the [concept_investment_pool]\\n\\nIt spreads to each linked [concept_country] as a [concept_spec_foreign_panic], and money flees to calm [Concept('concept_great_power','$concept_great_powers$')]\\nAfterward, [Concept('concept_political_movement','$concept_political_movements$')] against [GetLawType('law_laissez_faire').GetName] gain support for some years"
 concept_spec_foreign_panic: "Foreign Panic"
 concept_spec_foreign_panics: "Foreign Panics"
 concept_spec_foreign_panic_desc: "#italic A panic abroad that spills over into your market.#!\\n\\nWhen a [concept_spec_financial_panic] starts in a [concept_country] tied to yours, your [{mc}] #N drops#!\\nCountries are tied by a shared [concept_market], one being the other's subject, investment rights, lots of trade, or owning part of your economy\\n#N Closer ties, bigger drop#!\\n\\n[GetLawType('law_free_trade').GetName] makes trade ties stronger\\nOther trade policies make them weaker\\nAn [concept_embargo] cuts the trade tie"
{boom_end_loc(k, mc)} concept_spec_investor_interest: "Investor Interest"
 concept_spec_investor_interest_desc: "#italic How keen investors are on the {buildings} that make a [concept_good], from #v Fleeing#! to #v Feverish#!.#!\\n\\n#P Rises#! while the [concept_market_price] is above its long-run average\\n#N Falls#! while it is below\\n\\nThose buildings' [concept_throughput] follows it, from #N {companies.INTEREST_THROUGHPUT[1]:+g}%#! at #v Fleeing#! up to #P {companies.INTEREST_THROUGHPUT[6]:+g}%#! at #v Feverish#!\\nSo does the [concept_prosperity] of [Concept('concept_company','$concept_companies$')] making the $concept_good$\\nA booming $concept_good$ raises [{mc}]\\nWhen interest drops back, the boom ends in a [concept_spec_boom_end]"
 concept_spec_credit_policy: "Credit Policy"
 concept_spec_credit_policy_tight: "Tight Credit"
 concept_spec_credit_policy_normal: "Normal Credit"
 concept_spec_credit_policy_loose: "Loose Credit"
 concept_spec_credit_policy_desc: "#italic How freely banks lend into the [concept_investment_pool].#!\\n\\nUnlocked by [GetTechnology('central_banking').GetName]\\nCan be $concept_spec_credit_policy_tight$, $concept_spec_credit_policy_normal$ or $concept_spec_credit_policy_loose$\\n\\n#v Tighter#! credit slows investment, and pulls [{mc}] down when it runs high\\n#v Looser#! credit adds to [concept_spec_outstanding_credit]\\n\\nOnce changed, it is locked for #v {k['STANCE_COOLDOWN']}#! months"
{LEVERAGE_LOC}{LENDING_LOC}{companies_loc()} concept_spec_outstanding_credit: "Outstanding Credit"
 concept_spec_outstanding_credit_desc: "#italic Money the banks have lent into the [concept_investment_pool] and not yet got back.#!\\n\\nBanks lend while [{mc}] is above #v {k['CREDIT_FROM']}#!\\nThey stop at a Lending Limit of #v {leverage.SAFE}#! months of pool income\\n[GetTechnology('{leverage.LADDER_TECHS[0]}').GetName] adds #v {leverage.LADDER_STEPS[0]}#! months\\n[GetTechnology('{leverage.LADDER_TECHS[1]}').GetName] and [GetTechnology('{leverage.LADDER_TECHS[2]}').GetName] add #v {leverage.LADDER_STEPS[1]}#! each\\n\\nA little is paid back from the pool each month\\nWhen a [concept_spec_financial_panic] starts, the banks #N pull part of it back#!\\n\\n#lore Banks lent against railway shares in the 1840s, cotton in 1837 and building land in Vienna in 1873, and were caught when those booms broke.#!"
"""
