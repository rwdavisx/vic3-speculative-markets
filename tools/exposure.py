"""Bank exposure (design_exposure.md): where the banks' credit went, and what that does to a boom's ending.

spec_exp_<g> is the share of outstanding credit (spec_debt) lent into good g, 0 to 1; the rest is general lending. A share,
not money, so everything that shrinks spec_debt (repayment, a panic's clawback, the depression's recall, the legacy-save
write-down) leaves it right: only new lending (lend()), debt running out (clear()) and the boom ending (ended(): half written
off, the rest counted as general lending) touch it.

Lending: new credit goes into the booming goods by pull, a good's share of the market's trade times its heat (how far its
Investor Interest sits above Calm, full at Feverish), halved while restrained. Boom lending is PULL times the total pull,
at most SHARE_MAX of the month's credit. Encourage needs no rule of its own: it raises interest, and so the pull.
Effect: a good's boom-end confidence loss, and the cost of winding it down while restrained, are multiplied by
1 + PER_MONTH x the months of pool income lent into it (share x leverage), at most MULT_MAX. Panics and Bad Debts are as before."""
import cycle
import levers
import tuning

PULL = tuning.get("EXP_PULL", 2)              # boom lending is this times the booming goods' share of trade, heat-weighted
SHARE_MAX = tuning.get("EXP_SHARE_MAX", 0.6)  # most of a month's credit that goes into booms
PER_MONTH = tuning.get("EXP_PER_MONTH", 0.1)  # a boom's ending is this much harder per month of income lent into it
MULT_MAX = tuning.get("EXP_MULT_MAX", 1.5)  # exp1 at 0.25 and 2 doubled panics (0.85 to 1.7 a big country in 20 years)
RESTRAINED = 0.5  # a restrained good's pull: harder to raise money for it, not forbidden
HEAT_FROM, HEAT_FULL = 1, 6  # Calm's middle and the start of Feverish (generate.PEAK_FOR_CRASH)
SHOWN = 0.01  # shares below this are left out of the chart and the tooltips


def values(goods):
    out = []
    for g in goods:
        out.append(f"spec_lend_heat_{g} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_hype_{g} }}\n\t\tvalue = var:spec_hype_{g}\n"
                   f"\t\tsubtract = {HEAT_FROM}\n\t\tdivide = {HEAT_FULL - HEAT_FROM}\n\t\tmin = 0\n\t\tmax = 1\n\t}}\n}}")
        out.append(f"spec_pull_{g} = {{\n\tvalue = spec_mv_{g}\n\tdivide = var:spec_mv_total\n\tmultiply = spec_lend_heat_{g}\n"
                   f"\tif = {{\n\t\tlimit = {{ has_variable = spec_restrain_{g} }}\n\t\tmultiply = {RESTRAINED}\n\t}}\n}}")
        out.append(f"spec_exp_share_{g} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_exp_{g} }}\n\t\tvalue = var:spec_exp_{g}\n\t}}\n}}")
        # months of pool income lent into the good: share x leverage
        out.append(f"spec_exp_months_{g} = {{\n\tvalue = spec_exp_share_{g}\n\tmultiply = spec_lev\n}}")
        # a Great Issue on g (levers.py): its loans weigh ISSUE_EXPO times as much
        issue = (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_issue_{g} }}\n\t\tmultiply = {levers.ISSUE_EXPO:g}\n\t}}\n"
                 if levers.ISSUE_ON else "")
        out.append(f"spec_exp_mult_{g} = {{\n\tvalue = spec_exp_months_{g}\n\tmultiply = {PER_MONTH}\n{issue}\tadd = 1\n\tmax = {MULT_MAX}\n}}")
    out.append("spec_pull_total = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_pull_{g}\n" for g in goods) + "}")
    out.append(f"spec_boom_share = {{\n\tvalue = spec_pull_total\n\tmultiply = {PULL}\n{cycle.PULL}\tmax = {SHARE_MAX}\n}}")
    out.append("spec_exp_booms = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_exp_share_{g}\n" for g in goods) + "\tmax = 1\n}")
    return out


def lend(goods, t="\t\t\t\t"):
    """Before this month's credit is added to spec_debt (generate.monthly): each share becomes
    (share x debt + its part of the new credit) / (debt + new credit). Every month with credit, all-general ones too."""
    per = "".join(
        f"{t}\tif = {{\n{t}\t\tlimit = {{ OR = {{ has_variable = spec_exp_{g} spec_pull_{g} > 0 }} }}\n"
        f"{t}\t\tset_variable = {{ name = spec_exp_{g} value = {{\n{t}\t\t\tvalue = 0\n"
        f"{t}\t\t\tif = {{\n{t}\t\t\t\tlimit = {{ has_variable = spec_exp_{g} }}\n{t}\t\t\t\tadd = {{ value = var:spec_exp_{g} multiply = local_var:spec_exp_d }}\n{t}\t\t\t}}\n"
        f"{t}\t\t\tif = {{\n{t}\t\t\t\tlimit = {{ local_var:spec_exp_pt > 0 }}\n"
        f"{t}\t\t\t\tadd = {{ value = spec_pull_{g} divide = local_var:spec_exp_pt multiply = local_var:spec_exp_new }}\n{t}\t\t\t}}\n"
        f"{t}\t\t\tdivide = local_var:spec_exp_t\n{t}\t\t\tmin = 0\n{t}\t\t\tmax = 1\n{t}\t\t}} }}\n{t}\t}}\n" for g in goods)
    return (f"{t}# bank exposure: where this month's credit goes (exposure.py)\n"
            f"{t}set_local_variable = {{ name = spec_exp_d value = {{ value = var:spec_debt min = 0 }} }}\n"
            f"{t}set_local_variable = {{ name = spec_exp_t value = {{ value = local_var:spec_exp_d add = var:spec_credit_given }} }}\n"
            f"{t}set_local_variable = {{ name = spec_exp_new value = {{ value = var:spec_credit_given multiply = spec_boom_share }} }}\n"
            # the sum over every good, once: read twice for each good below
            f"{t}set_local_variable = {{ name = spec_exp_pt value = spec_pull_total }}\n"
            f"{t}if = {{\n{t}\tlimit = {{ local_var:spec_exp_t > 0 }}\n{per}{t}}}\n")


def clear(goods, t="\t\t\t"):
    """After repayment: no debt left, no shares."""
    return (f"{t}if = {{\n{t}\tlimit = {{ var:spec_debt < 1 }}\n"
            + "".join(f"{t}\tremove_variable = spec_exp_{g}\n" for g in goods) + f"{t}}}\n")


def ui(goods, t="\t\t\t"):
    """For generate.monthly's tab block: each good's months of income lent into it and its multiplier, for its row's
    tooltip, while its share is at least SHOWN (GUI text can't read a script value by the good's key)."""
    return "".join(
        f"{t}if = {{\n{t}\tlimit = {{ spec_exp_share_{g} >= {SHOWN} }}\n"
        f"{t}\tset_variable = {{ name = spec_ui_expm_{g} value = spec_exp_months_{g} }}\n"
        f"{t}\tset_variable = {{ name = spec_ui_expx_{g} value = spec_exp_mult_{g} }}\n{t}}}\n"
        f"{t}else = {{\n{t}\tremove_variable = spec_ui_expm_{g}\n{t}\tremove_variable = spec_ui_expx_{g}\n{t}}}\n" for g in goods)


def note(g):
    """In the boom-ending block, before its notification: the multiplier the ending took, for the notification's text."""
    return f"set_variable = {{ name = spec_note_bank_{g} value = spec_exp_mult_{g} days = 28 }}\n"


def ended(g, t="\t\t\t\t"):
    """In the boom-ending block, after note(): the banks write off half of what they had lent into the boom."""
    return f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_exp_{g} }}\n{t}\tchange_variable = {{ name = spec_exp_{g} multiply = 0.5 }}\n{t}}}\n"


def state_vars(goods):
    return [f"spec_{k}_{g}" for g in goods for k in ("exp", "ui_expm", "ui_expx", "note_bank")]


def loc():
    from market_tab import fx, good_var
    # Cache after repayment/lending with the chart; use its presence to avoid reading missing tooltip values.
    has = f"GreaterThanOrEqualTo_CFixedPoint({good_var('spec_ui_expx')}, {fx(1)})"
    # Captured in the notification's event chain, not resolved through a country's Var argument.
    note = "SCOPE.GetValue('spec_note_bank')"
    return (f' SPEC_TILE_BANKS: "[SelectLocalization({has}, \'SPEC_TILE_BANKS_ON\', \'SPEC_GOODS_NONE\')]{cycle.TILE_REF}"\n'
            f' SPEC_TILE_BANKS_ON: "\\n\\n#title Bank Loans:#! #v [{good_var("spec_exp")}|%0]#! of [concept_spec_outstanding_credit], '
            f'#v [{good_var("spec_ui_expm")}|1]#! months of pool income\\nIf its boom ended, [concept_spec_market_confidence] would fall '
            f'#v x[{good_var("spec_ui_expx")}|2]#! as far as a boom no bank had lent into"\n'
            ' SPEC_NOTE_BANKS: ""\n'
            f' SPEC_NOTE_BANKS_ON: " The banks had lent heavily into it, so the fall was #N x[{note}|2]#! as hard."\n')


if __name__ == "__main__":
    import generate
    g = generate.GOODS
    assert HEAT_FULL == generate.PEAK_FOR_CRASH
    v = "\n".join(values(g))
    assert v.count("{") == v.count("}"), "values unbalanced"
    l = lend(g)
    assert l.count("{") == l.count("}"), "lend unbalanced"
    assert l.count("spec_pull_total") == 1, "the total is worked out once a month, not once per good"
    c = clear(g)
    assert c.count("{") == c.count("}") and c.count("remove_variable") == len(g)
    x = ended("steel")
    assert x.count("{") == x.count("}") and "spec_exp_steel multiply = 0.5" in x, "a boom's end halves its share"

    # the share update conserves money: a model of lend() over a few months
    debt, shares, money = 0.0, {}, {}  # money: what is really lent into each good, to check the shares against
    for credit, pulls in ((100, {"steel": 0.2, "coal": 0.1}), (50, {}), (80, {"steel": 0.4})):
        total = sum(pulls.values())
        boom = min(total * PULL, SHARE_MAX) * credit
        new_debt = debt + credit
        shares = {k: (shares.get(k, 0) * debt + (pulls.get(k, 0) / total * boom if total else 0)) / new_debt
                  for k in set(shares) | set(pulls)}
        money = {k: money.get(k, 0) + (pulls.get(k, 0) / total * boom if total else 0) for k in set(money) | set(pulls)}
        debt, money = new_debt * 0.98, {k: m * 0.98 for k, m in money.items()}  # repayment leaves shares as they are
        assert 0 <= sum(shares.values()) <= 1, shares
    assert all(abs(shares[k] * debt - money[k]) < 1e-9 for k in money), (shares, money)
    print("exposure ok")
