"""Game concepts for the mod's own terms: hoverable [concept_spec_x] links and entries in the concept browser."""
import companies
import cycle
import icons
import leverage
import tuning

# concept key suffix -> icon slot shown in its tooltip (None: no icon, like most vanilla concepts)
CONCEPTS = {"market_sector": "je_markets", "market_confidence": "je_markets", "speculative_mania": "state_mania", "financial_panic": "state_panic",
            "foreign_panic": "driver_foreign", "boom_end": "driver_crash", "correction": "driver_crash", "bust": "driver_crash", "collapse": "driver_crash", "investor_interest": "driver_boom",
            "credit_policy": None, "outstanding_credit": None, "long_depression": None,
            "speculative_excess": "excess_alert", "sound_finance": None, "banking_reforms": None,
            "intervention": None, "market_conditions": None, "baseline": None, "market_mood": None, "market_tie": None,
            "capital_flight": None, "war_news": None, "financial_centre": None, "blue_chip": "blue_chip", "company_strength": None, **({"leverage": None, "bad_debts": None} if leverage.ON else {}),
            **({"lending_standards": None} if cycle.ON else {}),
            **({"exchange": None, "trust": None} if tuning.get("EXCHANGE_ON", 1) else {})}  # centres.ON; its text is in centres.loc
LEVERAGE_LOC = "" if not leverage.ON else (
    ' concept_spec_leverage: "Credit Leverage"\n concept_spec_leverage_desc: "How much a [concept_country]\'s banks have lent, its [concept_spec_outstanding_credit] '
    "counted in months of [concept_investment_pool] income. "
    f"Each whole month of it gives #P {leverage.REWARD * 100:+g}%#! [concept_throughput], up to #P {leverage.REWARD * leverage.REWARD_MAX * 100:+g}%#!. The bonus fades during a "
    f"[concept_spec_financial_panic] and while [concept_spec_bad_debts] remain.\\n\\nPast #v {leverage.SAFE}#! months it gets risky. "
    f'A $concept_spec_financial_panic$ then starts sooner, at a higher [concept_spec_market_confidence], and leaves $concept_spec_bad_debts$ behind."\n'
    ' concept_spec_bad_debts: "Bad Debts"\n concept_spec_bad_debts_desc: "The losses left on the books of a [concept_country]\'s banks. A [concept_spec_financial_panic] leaves more of them '
    f"the further [concept_spec_leverage] is past #v {leverage.SAFE}#! months, and a burst of [concept_spec_speculative_excess] leaves whatever "
    "[concept_spec_market_confidence] cannot cover.\\n\\n"
    f"Each point costs #N {leverage.CRUNCH_THROUGHPUT:.1%}#! [concept_throughput] and #N {leverage.CRUNCH_INVEST * 100:g}%#! investment. They build up for some months, "
    f"then slowly shrink, and at their worst take about #v {round((leverage.CRUNCH_MAX / leverage.CRUNCH_RAMP + leverage.CRUNCH_MAX / leverage.CRUNCH_FADE) / 12)}#! years to clear, "
    f"or #v {round((leverage.CRUNCH_MAX / leverage.CRUNCH_RAMP + leverage.CRUNCH_MAX / leverage.CRUNCH_FADE_TIGHT) / 12)}#! under "
    "[Concept('concept_spec_credit_policy','$concept_spec_credit_policy_tight$')]. Banks lend less the more of them there are, "
    f"and nothing past #v {leverage.BAD_STOP}#! at Sound [concept_spec_lending_standards], "
    f"#v {leverage.BAD_STOP * (1 - cycle.LAX_BADSTOP):g}#! at the strictest and #v {leverage.BAD_STOP * (1 + cycle.LAX_BADSTOP):g}#! at the most reckless."
    f'\\n\\n#v Lend to the Banks#! does not clear them, but #v Buy Up Bad Loans#! clears {leverage.BAILOUT_CUT:.0%} of them, once while they last."\n')
# cycle.py's spec_lax: what the banks' care does and what moves it
LENDING_LOC = "" if not cycle.ON else (
    ' concept_spec_lending_standards: "Lending Standards"\n concept_spec_lending_standards_desc: "How '
    f'carefully a [concept_country]\'s banks lend, from #v {cycle.LAX_WORDS[0]}#! through {", ".join(f"#v {w}#!" for w in cycle.LAX_WORDS[1:-2])} '
    f'and #v {cycle.LAX_WORDS[-2]}#! to #v {cycle.LAX_WORDS[-1]}#!. '
    "Laxer banks lend more into the [concept_investment_pool] and put more of it into booms, so booms end harder, a [concept_spec_financial_panic] calls back more of their loans and a Bank Rescue costs more."
    f"\\n\\nUnder Normal or Loose Credit, banks get a little laxer each month without a [concept_spec_financial_panic] or [concept_spec_bad_debts], going from #v {cycle.LAX_WORDS[0]}#! to #v {cycle.LAX_WORDS[-1]}#! "
    f"in about #v {cycle.LAX_QUIET_YEARS}#! quiet years. Under Tight Credit, quiet months bring lax banks back toward #v Sound#!. A Bank Rescue or #v Buy Up Bad Loans#! makes them laxer. They get stricter when a boom ends, "
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
    how = {1: "a little", 2: f"more, about #v {rate[2] / rate[1]:g}#! times as much as a $concept_spec_correction$ after the same boom",
           3: f"sharply, about #v {rate[3] / rate[1]:.0f}#! times as much as a [concept_spec_correction] after the same boom"}
    rank = {1: "The mildest [concept_spec_boom_end]", 2: "A harsher [concept_spec_boom_end] than a [concept_spec_correction]",
            3: "The worst [concept_spec_boom_end]"}
    fall = {1: "falls back to", 2: "falls back to", 3: "falls all the way to"}
    techs = " and ".join(f"[GetTechnology('{t}').GetName]" for t in companies.TIE_TECHS)
    after = {3: " If the $concept_good$ is a big part of the [concept_market]'s trade, it can also set off a [concept_spec_financial_panic]."}
    out = (f' concept_spec_boom_end: "Boom Ending"\n concept_spec_boom_ends: "Boom Endings"\n'
           f' concept_spec_boom_end_desc: "A boom ends when [concept_spec_investor_interest] in a [concept_good] drops back after a rise. '
           f'The higher it peaked, the harder it falls. A peak at #v Keen#! ends in a [concept_spec_correction], one at #v Eager#! '
           f'in a [concept_spec_bust], and one at #v Feverish#! in a [concept_spec_collapse].'
           f'\\n\\nIt lowers [{mc}], more for bigger booms and for $concept_goods$ that are a bigger part of the [concept_market]\'s trade. '
           f'Investors then stay away while the $concept_good$ recovers, and if a [concept_company] makes it, that industry loses '
           f'[concept_throughput].\\n\\nThe peak fades a little each month, so a boom that cools slowly ends more gently, '
           f'or with no $concept_spec_boom_end$ at all."\n')
    for sev, (key, name, peak, low) in ENDINGS.items():
        days = companies.UNWIND[sev][1]
        span = "a year" if days == 365 else f"#v {days}#! days"
        out += (f' concept_spec_{key}: "{name}"\n'
                f' concept_spec_{key}_desc: "{rank[sev]}. It happens when '
                f'[concept_spec_investor_interest] in a [concept_good] that peaked at #v {peak}#! {fall[sev]} #v {low}#!.'
                f'\\n\\nIt lowers [{mc}] {how[sev]}, and investors stay away from the $concept_good$ for '
                f'#v {k["GLUT_MONTHS"][sev]}#! months. If a [concept_company] makes it, that industry loses '
                f'#N {-companies.COMPANY_BUST * companies.UNWIND[sev][0] * 100:g}%#! [concept_throughput] for {span}, '
                f'#N {companies.TIE_PER_TECH:.0%}#! more for each of {techs} researched.{after.get(sev, "")}"\n')
    return out


def companies_loc():
    """Blue Chip and Company Strength (design_companies.md), read from the honour and the Companies rows."""
    import centres  # ponytail: imported here, centres is the heavier module and only CO_STRENGTH is needed
    import bluechips as bc
    cos = "[Concept('concept_company','$concept_companies$')]"
    at = f"#v {companies.BLUE_PROSPER:g}#! [concept_prosperity]"
    pool = dict(bc.INDEX)["state_capitalists_investment_pool_contribution_add"] * 100
    return (' concept_spec_blue_chip: "Blue Chip"\n concept_spec_blue_chips: "Blue Chips"\n'
            f' concept_spec_blue_chip_desc: "A star [concept_company] that has held {at} or more for #v {companies.BLUE_MONTHS:g}#! months in a row. '
            f"One month below resets the climb. It loses the status after #v {companies.BLUE_LOSE:g}#! months in a row below, or after one "
            "while #N Fragile#!, which a Bear Raid against us causes for a year. A [concept_country] that leaves the market economy keeps none.\\n\\n"
            f"Each one adds #v {companies.BLUE_BONUS:g}#! to our [concept_spec_company_strength], cuts the [concept_spec_market_confidence] lost when booms end and "
            f"in [Concept('concept_spec_foreign_panic','$concept_spec_foreign_panics$')] by #P {bc.SHELTER * 100:.0f}%#!, adds #P {bc.DIVIDEND / 1.2:.1f}%#! [concept_spec_exchange] trust a year, pulls [concept_spec_exchange] "
            f"contests #P {bc.PULL * 100:.0f}%#! our way, and raises the Capitalists' [concept_investment_pool] contribution by #P {pool:.1f}%#!. The first "
            f"#v {bc.CAP}#! count in full and the next #v {bc.CAP2 - bc.CAP}#! half as much. Losing one costs #N {bc.FALL_TRUST / 1.2:.1f}%#! "
            f"[concept_spec_exchange] trust and #N {bc.FALL_CONF}#! [concept_spec_market_confidence].\\n\\n"
            f"If ours is the world's most prosperous, it is Company of the Year, worth #P {bc.COTY_TRUST / 1.2:.1f}%#! [concept_spec_exchange] trust and "
            f'#P {bc.COTY_PRESTIGE:.0%}#! [concept_prestige] for a year."\n'
            ' concept_spec_company_strength: "Company Strength"\n'
            f" concept_spec_company_strength_desc: \"How strong a [concept_country]'s {cos} are, all together. Each company adds its [concept_prosperity] "
            f"divided by #v {centres.CO_STRENGTH:g}#!, so one at #v 100#! adds #v {100 / centres.CO_STRENGTH:g}#!, and each [concept_spec_blue_chip] adds "
            f'#v {companies.BLUE_BONUS:g}#! more. The strongest [concept_country] can claim Home of Great Companies as a speciality of its '
            '[concept_spec_exchange]."\n')


def loc(k):
    goods = "[Concept('concept_good','$concept_goods$')]"
    buildings = "[Concept('concept_building','$concept_buildings$')]"
    mc = "concept_spec_market_confidence"
    return f""" concept_spec_market_confidence: "Market Confidence"
 concept_spec_market_confidence_desc: "How investors feel about a [concept_country]'s [concept_market], from #v 0#! to #v 100#!. Fear slows investment and makes [concept_loans] cost more, while greed speeds investment up.\\n\\nIt rises with booming {goods} and falls with [Concept('concept_spec_boom_end','$concept_spec_boom_ends$')], [Concept('concept_spec_foreign_panic','$concept_spec_foreign_panics$')], [Concept('concept_diplomatic_play','$concept_diplomatic_plays$')] and [concept_war]. Booms and their endings move it more where $building_financial_district$ make up more of the economy, and less where $building_manor_house$ outnumber them.\\n\\nAbove #v {k['CREDIT_FROM']}#! banks lend into the [concept_investment_pool]. At #v {k['MANIA']}#! or more a [concept_spec_speculative_mania] begins, and below #v {k['PANIC']}#! a [concept_spec_financial_panic] begins{". High [concept_spec_leverage] raises that line, and few $building_financial_district$ lower it a little" if leverage.ON else ""}."
 concept_spec_speculative_mania: "Speculative Mania"
 concept_spec_speculative_mania_desc: "A [concept_market] gone wild with greed. It lasts while [{mc}] is #v {k['MANIA']}#! or more. Banks lend most freely into the [concept_investment_pool], but every [concept_spec_boom_end] costs more $concept_spec_market_confidence$.\\n\\nA long or very high mania helps [Concept('concept_political_movement','$concept_political_movements$')] that want [GetLawType('law_laissez_faire').GetName] for some years after."
 concept_spec_financial_panic: "Financial Panic"
 concept_spec_financial_panics: "Financial Panics"
 concept_spec_financial_panic_desc: "A crash, when investors flee and the banks pull their money back. It begins when [{mc}] falls below #v {k['PANIC']}#!.{' Past #v ' + str(leverage.SAFE) + '#! months of [concept_spec_leverage] that line rises, up to #v ' + str(k['PANIC'] + leverage.PANIC_SPAN) + '#!, and the panic lasts longer and cuts deeper into [concept_private_construction], stopping it entirely at #v ' + str(leverage.DANGER) + '#! months.' if leverage.ON else ''}{' With few $building_financial_district$ the line drops, down to #v ' + str(k['PANIC'] - k['PANIC_SHALLOW']) + '#!.' if k['PANIC_SHALLOW'] else ''}\\n\\nWhile it lasts, every building has less [concept_throughput], fewer taxes are collected and the [concept_treasury] pays each week to help the jobless. [concept_private_construction] and investment slow, [Concept('concept_company','$concept_companies$')] get a smaller $concept_throughput$ bonus, some investors turn [Concept('concept_radical','$concept_radicals$')], and the banks pull [concept_spec_outstanding_credit] back from the [concept_investment_pool].\\n\\nThe panic spreads to each tied [concept_country] as a [concept_spec_foreign_panic], and money flees to calm [Concept('concept_great_power','$concept_great_powers$')]. Afterward, [Concept('concept_political_movement','$concept_political_movements$')] against [GetLawType('law_laissez_faire').GetName] gain support for some years."
 concept_spec_foreign_panic: "Foreign Panic"
 concept_spec_foreign_panics: "Foreign Panics"
 concept_spec_foreign_panic_desc: "A panic abroad that spills over into a [concept_market]. When a [concept_spec_financial_panic] starts in a [concept_country] tied to ours, our [{mc}] drops, more the closer the tie.\\n\\nCountries are tied by a shared [concept_market], one being the other's subject, investment rights, heavy trade, or one owning part of the other's economy. [GetLawType('law_free_trade').GetName] makes trade ties stronger and other trade policies make them weaker, while an [concept_embargo] cuts the trade tie."
{boom_end_loc(k, mc)} concept_spec_investor_interest: "Investor Interest"
 concept_spec_investor_interest_desc: "How keen investors are on the {buildings} that make a [concept_good], from #v Fleeing#! to #v Feverish#!. It rises while the [concept_market_price] is above its long-run average, and falls while it is below.\\n\\nThose buildings' [concept_throughput] follows it, from #N {companies.INTEREST_THROUGHPUT[1]:+g}%#! at #v Fleeing#! up to #P {companies.INTEREST_THROUGHPUT[6]:+g}%#! at #v Feverish#!, and so does the [concept_prosperity] of [Concept('concept_company','$concept_companies$')] making the $concept_good$. A booming $concept_good$ raises [{mc}], and when interest drops back the boom ends in a [concept_spec_boom_end]."
 concept_spec_credit_policy: "Credit Policy"
 concept_spec_credit_policy_tight: "Tight Credit"
 concept_spec_credit_policy_normal: "Normal Credit"
 concept_spec_credit_policy_loose: "Loose Credit"
 concept_spec_credit_policy_desc: "How freely banks lend into the [concept_investment_pool], once [GetTechnology('central_banking').GetName] is researched. It can be $concept_spec_credit_policy_tight$, $concept_spec_credit_policy_normal$ or $concept_spec_credit_policy_loose$.\\n\\nTighter credit slows investment, and pulls [{mc}] down when it runs high. Looser credit adds to [concept_spec_outstanding_credit]. Once changed, it is locked for #v {k['STANCE_COOLDOWN']}#! months."
{LEVERAGE_LOC}{LENDING_LOC}{companies_loc()} concept_spec_outstanding_credit: "Outstanding Credit"
 concept_spec_outstanding_credit_desc: "Money the banks have lent into the [concept_investment_pool] and not yet got back. Banks lend while [{mc}] is above #v {k['CREDIT_FROM']}#!, up to a Lending Limit of #v {leverage.SAFE}#! months of pool income. [GetTechnology('{leverage.LADDER_TECHS[0]}').GetName] adds #v {leverage.LADDER_STEPS[0]}#! months, and [GetTechnology('{leverage.LADDER_TECHS[1]}').GetName] and [GetTechnology('{leverage.LADDER_TECHS[2]}').GetName] add #v {leverage.LADDER_STEPS[1]}#! each.\\n\\nA little is paid back from the pool each month. When a [concept_spec_financial_panic] starts, the banks pull part of it back."
"""
