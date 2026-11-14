"""Vanilla mechanics feeding the market: trade policy and finance techs scale the contagion ties and hype, and
heavy government debt weighs on confidence. Contagion uses the receiving country's law and techs: they decide how
exposed its own market is, and the tab can then show the player's own figures."""
import tuning

# trade policy law (variants included) -> scaling of the trade tie
TRADE_TIE = {"free_trade": 1.5, "protectionism": 0.7, "mercantilism": 0.7, "isolationism": 0.1}
EXCHANGE_TIE = 1.25         # international_exchange_standards: market and investment ties
STOCK_HYPE = 1.1            # joint_stock_companies: hype
DEBT_FROM = 0.5             # principal as a share of credit where debt starts to weigh: vanilla's healthy economy line
DEBT_MAX = tuning.get("DEBT_MAX", 1)                # confidence lost a month at the credit limit
# speculation depth: Financial District levels as a share of all building levels scale hype and the crash loss.
# No districts gives DEPTH_MIN, FD_SHARE_FULL gives 1, more rises to DEPTH_MAX.
# calibrated on a 1858 --log run: Austria's 3% share reads about 1, Britain, France, the US and Prussia sit near the
# top, and the 58% of countries with no districts at all keep mild cycles
FD_SHARE_FULL = 0.03
DEPTH_MIN, DEPTH_MAX = tuning.get("DEPTH_MIN", 0.8), tuning.get("DEPTH_MAX", 1.2)  # it scales both hype and crashes, so it compounds
DEPTH_WORDS = (0.9, 1.1)    # Shallow below the first, Moderate below the second, Deep above (depth runs 0.8 to 1.2)
# Manor Houses outnumber districts almost everywhere (0.6 to 1 of the two in 1858), so steadiness is measured from the
# typical share: an economy more landed than MANOR_TYPICAL moves less, a more financial one moves more, within the clamp
MANOR_TYPICAL, MANOR_STEADY = 0.9, 0.5
STEADY_MIN, STEADY_MAX = tuning.get("STEADY_MIN", 0.85), tuning.get("STEADY_MAX", 1.1)
# monthly, before the goods: the two ownership building counts, one pass over the states each
MONTHLY = ("\t\t\tset_variable = { name = spec_fd value = spec_fd_levels }\n"
           "\t\t\tset_variable = { name = spec_mh value = spec_mh_levels }\n")
STATE_VARS = ["spec_fd", "spec_mh"]


def levels(b):
    """Script value body: the country's levels of building type b."""
    return (f"\tvalue = 0\n\tevery_scope_state = {{\n\t\tlimit = {{ has_building = {b} }}\n"
            f"\t\tadd = b:{b}.level\n\t}}\n")


def script(k):
    links = k["LINKS"]
    trade = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ has_law_or_variant = law_type:law_{law} }}\n"
                    f"\t\tmultiply = {n:g}\n\t}}\n" for i, (law, n) in enumerate(TRADE_TIE.items()))
    exchange = f"\tif = {{\n\t\tlimit = {{ has_technology_researched = international_exchange_standards }}\n\t\tmultiply = {EXCHANGE_TIE:g}\n\t}}\n"
    sv = [f"spec_tie_market = {{\n\tvalue = {links['market']:g}\n{exchange}}}",
          f"spec_tie_investment = {{\n\tvalue = {links['investment']:g}\n{exchange}}}",
          f"spec_tie_trade = {{\n\tvalue = {links['trade']:g}\n{trade}}}",
          # the share of this country's GDP owned by scope:spec_tie_src (set by spec_every_tied and spec_find_risk_src)
          "spec_owned_share = {\n\tvalue = 0\n\tif = {\n\t\tlimit = {\n\t\t\texists = scope:spec_tie_src\n\t\t\tgdp > 0\n\t\t}\n"
          "\t\tvalue = \"gdp_owned_by(scope:spec_tie_src)\"\n\t\tdivide = gdp\n\t\tmax = 1\n\t}\n}",
          f"spec_tie_owned = {{\n\tvalue = spec_owned_share\n\tmultiply = {links['owned'] / k['OWNED_FULL']:g}\n\tmax = {links['owned']:g}\n}}",
          f"spec_tech_hype = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{ has_technology_researched = joint_stock_companies }}\n"
          f"\t\tvalue = {STOCK_HYPE:g}\n\t}}\n}}",
          # scaled_debt: principal over credit; default has its own, larger loss in spec_c_turmoil
          f"spec_debt_drag = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{\n\t\t\tin_default = no\n\t\t\tscaled_debt > {DEBT_FROM:g}\n\t\t}}\n"
          f"\t\tvalue = scaled_debt\n\t\tsubtract = {DEBT_FROM:g}\n\t\tmultiply = {-DEBT_MAX / (1 - DEBT_FROM):g}\n\t\tmin = {-DEBT_MAX:g}\n\t}}\n}}",
          "spec_debt_share = {\n\tvalue = scaled_debt\n\tmin = 0\n}",  # display only
          f"spec_fd_levels = {{\n{levels('building_financial_district')}}}",
          f"spec_mh_levels = {{\n{levels('building_manor_house')}}}",
          # 1 until the first monthly count, so the tab and the first month read a neutral figure
          f"spec_depth = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{ has_variable = spec_fd }}\n"
          f"\t\tvalue = var:spec_fd\n\t\tdivide = {{\n\t\t\tvalue = building_levels\n\t\t\tmin = 1\n\t\t}}\n"
          f"\t\tdivide = {FD_SHARE_FULL:g}\n\t\tmultiply = {1 - DEPTH_MIN:g}\n\t\tadd = {DEPTH_MIN:g}\n\t\tmax = {DEPTH_MAX:g}\n\t}}\n}}",
          # 1 at the typical Manor House share of the two, less above it, more below it
          f"spec_steady = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_mh\n\t\t\tvar:spec_mh > 0\n\t\t}}\n"
          f"\t\tsubtract = {{\n\t\t\tvalue = var:spec_mh\n\t\t\tdivide = {{\n\t\t\t\tvalue = var:spec_mh\n\t\t\t\tadd = var:spec_fd\n\t\t\t}}\n"
          f"\t\t\tsubtract = {MANOR_TYPICAL:g}\n\t\t\tmultiply = {MANOR_STEADY:g}\n\t\t}}\n\t\tmin = {STEADY_MIN:g}\n\t\tmax = {STEADY_MAX:g}\n\t}}\n}}"]
    return {"common/script_values/spec_ties_values.txt": "\n\n".join(sv) + "\n"}


def loc(k):
    p = "GetPlayer.MakeScope"
    return f""" SPEC_DRIVER_DEBT: "Government Debt"
 SPEC_DRIVER_DEBT_TT: "#header Government Debt: [{p}.Var('spec_c_debt').GetValue|+=2]#!\\n$TOOLTIP_DELIMITER$\\n[concept_credit] used: #v [{p}.ScriptValue('spec_debt_share')|%0]#! ([concept_principal])\\nInvestors accept up to #v {DEBT_FROM:.0%}#!\\n$TOOLTIP_DELIMITER$\\nEach #v 10%#! above that lowers [concept_spec_market_confidence] by #v {DEBT_MAX / (1 - DEBT_FROM) / 10:g}#! a month, up to #N -{DEBT_MAX:g}#!."
"""
