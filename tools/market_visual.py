"""Trade shares by investor interest, shown in tooltips rather than a section of their own: each Investor Interest
band's tooltip carries its share of the market's trade (market_tab, SPEC_SEP_<WORD>_TT), and the confidence card's
downside marker tooltip (SPEC_DOWNSIDE_TT) names the share that could collapse (SPEC_RISK_SHARE).

Script (generate.monthly, country scope): script_reset(), script_tally() per good, then script_shares(). Each month
var:spec_heat_<w> is the share of the market's trade value in interest word w (1 Fleeing .. 6 Feverish, spec_word),
spec_heat_boom the Eager and Feverish share and spec_heat_collapse the share of goods whose boom would end in a
Collapse (spec_sev 3). generate.py adds loc()."""
import market_tab as mt

WORDS = range(1, 7)          # spec_word, cold to hot
SHARES = [f"spec_heat_{w}" for w in WORDS] + ["spec_heat_collapse"]
STATE_VARS = SHARES + ["spec_heat_boom"]
SHOWN = 0.005                # under this a share would read 0%


# -- script (generate.monthly, country scope) --------------------------------------------------------------

def script_reset():
    return "".join(f"set_variable = {{ name = {s} value = 0 }}\n" for s in SHARES)


def script_tally(g):
    """Add a traded good's trade value to its interest word, and to the collapse share if its boom would end in one."""
    word = "".join(f"{'if' if w == 1 else 'else_if'} = {{\n\tlimit = {{ var:spec_word_{g} = {w} }}\n"
                   f"\tchange_variable = {{ name = spec_heat_{w} add = spec_mv_{g} }}\n}}\n" for w in WORDS)
    return word + (f"if = {{\n\tlimit = {{\n\t\tvar:spec_word_{g} > 0\n\t\tvar:spec_sev_{g} = 3\n\t}}\n"
                   f"\tchange_variable = {{ name = spec_heat_collapse add = spec_mv_{g} }}\n}}\n")


def script_shares():
    return ("".join(f"change_variable = {{ name = {s} divide = var:spec_mv_total }}\n" for s in SHARES)
            + "set_variable = { name = spec_heat_boom value = var:spec_heat_5 }\n"
            "change_variable = { name = spec_heat_boom add = var:spec_heat_6 }\n")


# -- the GUI's tests and loc -------------------------------------------------------------------------------

def share(w):
    return mt.v(f"spec_heat_{w}")


def loc(k):
    return (f" SPEC_RISK_SHARE: \"\\n#N [{mt.v('spec_heat_collapse')}|%0]#! of our trade is in booms that would end "
            "in a [concept_spec_collapse].\"\n")
