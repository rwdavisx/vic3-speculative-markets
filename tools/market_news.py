"""Domestic market news. A material bust or collapse interrupts; routine changes collect for three pulses. The bulletin
names what changed: its toast sums it up, its tooltip lists the goods by sector and the interest group stance changes.

Recorded on the country until delivery: spec_news_hot_<g> 1 once g turned feverish, spec_news_end_<g> the worst boom
ending (1-3, KINDS), and up to SLOTS stance changes (spec_news_ig<i>, spec_news_igg<i> the good, spec_news_igk<i>
ig_stances.STANCES' 1-based index); more are counted in spec_news_ig_more. Counts kept by older versions, which named
nothing, become spec_news_prior_<kind> and spec_news_ig_more (spec_migrate_market_news).

Delivery snapshots everything as scope values, so the toast reads what it was posted with: nested localization has no
notification SCOPE, so the description and tooltip test those values at the outer level and only localize static keys."""
from sectors import CATEGORIES, GROUPS

DETAILED = "has_game_rule = spec_goods_news_detailed"
KINDS = ("hot", "correction", "bust", "collapse")  # 0 a good turns feverish; 1-3 its boom ends, by severity
SLOTS = 6  # stance changes named in one bulletin
LEGACY = [f"spec_news_{cat}_{kind}" for cat in (*CATEGORIES, *GROUPS) for kind in KINDS] + ["spec_news_opinions"]
PRIOR = [f"spec_news_prior_{kind}" for kind in KINDS]
GOODS = []  # goods alternate() records, before generate runs effects() and loc()
# alternate() adds each good's two variables, before generate's state_vars() reads this
STATE = ["spec_news_age", "spec_news_urgent", "spec_news_ig_more", *PRIOR, *LEGACY,
         *(f"spec_news_{k}{i}" for i in range(1, SLOTS + 1) for k in ("igk", "ig", "igg"))]
RULE = """spec_goods_news = {
    default = spec_goods_news_bulletin
    spec_goods_news_bulletin = {}
    spec_goods_news_detailed = {}
}
"""
LINES = (("h", "hot", 1), ("3", "end", 3), ("2", "end", 2), ("1", "end", 1))  # a sector's lines: code, variable, value
SUMMARY = (("3", "COLLAPSE"), ("2", "BUST"), ("h", "HOT"), ("1", "CORRECTION"))  # the worst news first


def alternate(detailed, indent, good, kind, ig=None):
    """Individual Notices post detailed; Market Bulletins record the news instead. kind: KINDS' index for a good's
    news, or with ig, the stance change (ig_stances.STANCES' 1-based index)."""
    t = indent + "\t"
    if ig:
        queue = f"{t}spec_queue_ig_news = {{ IG = {ig} G = {good} K = {kind} }}\n"
    else:
        if good not in GOODS:
            GOODS.append(good)
            STATE.extend((f"spec_news_hot_{good}", f"spec_news_end_{good}"))
        queue = f"{t}spec_queue_market_news = yes\n"
        if kind == 0:
            queue += f"{t}set_variable = {{ name = spec_news_hot_{good} value = 1 }}\n"
        else:  # the worst ending is the one named
            end = f"spec_news_end_{good}"
            queue += (f"{t}if = {{\n{t}\tlimit = {{ OR = {{ NOT = {{ has_variable = {end} }} var:{end} < {kind} }} }}\n"
                      f"{t}\tset_variable = {{ name = {end} value = {kind} }}\n{t}}}\n")
        if kind >= 2:
            queue += f"{t}set_variable = spec_news_urgent\n"
    return (f"{indent}if = {{\n{indent}\tlimit = {{ {DETAILED} }}\n"
            + "".join("\t" + line for line in detailed.splitlines(True)) + f"{indent}}}\n"
            + f"{indent}else = {{\n{queue}{indent}}}\n")


def _sectors():
    return [(s, [g for g in goods.split() if g in GOODS]) for s, (_, goods) in GROUPS.items()
            if any(g in GOODS for g in goods.split())]


def _init(name, t="\t"):
    return f"{t}if = {{ limit = {{ NOT = {{ has_variable = {name} }} }} set_variable = {{ name = {name} value = 0 }} }}\n"


def _local_from(local, var, t="\t\t\t"):
    return (f"{t}set_local_variable = {{ name = {local} value = 0 }}\n"
            f"{t}if = {{ limit = {{ has_variable = {var} }} set_local_variable = {{ name = {local} value = var:{var} }} }}\n")


def _order(group, clauses, t="\t\t\t"):
    """Script: number a sentence's clauses (code, local variable holding its count) for _sentence: scope values
    snw<group><code>n the count, p 1 first, 2 middle, 3 last, w the count (+100 when it opens the sentence)."""
    out = f"{t}set_local_variable = {{ name = spec_news_n value = 0 }}\n" + "".join(
        f"{t}if = {{ limit = {{ local_var:{v} > 0 }} change_local_variable = {{ name = spec_news_n add = 1 }} }}\n"
        for _, v in clauses) + f"{t}set_local_variable = {{ name = spec_news_i value = 0 }}\n"
    for code, v in clauses:
        b = f"snw{group}{code}"
        out += (f"{t}save_scope_value_as = {{ name = {b}n value = local_var:{v} }}\n"
                f"{t}if = {{\n{t}\tlimit = {{ local_var:{v} > 0 }}\n"
                f"{t}\tchange_local_variable = {{ name = spec_news_i add = 1 }}\n"
                f"{t}\tset_local_variable = {{ name = spec_news_w value = local_var:{v} }}\n"
                f"{t}\tif = {{\n{t}\t\tlimit = {{ local_var:spec_news_i = 1 }}\n"
                f"{t}\t\tsave_scope_value_as = {{ name = {b}p value = 1 }}\n"
                f"{t}\t\tchange_local_variable = {{ name = spec_news_w add = 100 }}\n{t}\t}}\n"
                f"{t}\telse_if = {{\n{t}\t\tlimit = {{ local_var:spec_news_i = local_var:spec_news_n }}\n"
                f"{t}\t\tsave_scope_value_as = {{ name = {b}p value = 3 }}\n{t}\t}}\n"
                f"{t}\telse = {{ save_scope_value_as = {{ name = {b}p value = 2 }} }}\n"
                f"{t}\tsave_scope_value_as = {{ name = {b}w value = local_var:spec_news_w }}\n{t}}}\n"
                f"{t}else = {{\n{t}\tsave_scope_value_as = {{ name = {b}p value = 0 }}\n"
                f"{t}\tsave_scope_value_as = {{ name = {b}w value = 0 }}\n{t}}}\n")
    return out + f"{t}save_scope_value_as = {{ name = snw{group} value = local_var:spec_news_n }}\n"


def _snapshot(t="\t\t\t"):
    out = "".join(_local_from(f"spec_news_q{code}", f"spec_news_prior_{KINDS[i]}")
                  + f"{t}set_local_variable = {{ name = spec_news_t{code} value = local_var:spec_news_q{code} }}\n"
                  for i, code in enumerate(("h", "1", "2", "3")))
    for s, goods in _sectors():
        out += f"{t}set_local_variable = {{ name = spec_news_s value = 0 }}\n"
        for code, var, value in LINES:
            out += (f"{t}set_local_variable = {{ name = spec_news_n value = 0 }}\n"
                    + "".join(f"{t}spec_news_count = {{ VAR = spec_news_{var}_{g} S = {value} }}\n" for g in goods)
                    + f"{t}set_local_variable = {{ name = spec_news_i value = 0 }}\n"
                    + "".join(f"{t}spec_news_place = {{ VAR = spec_news_{var}_{g} S = {value} NAME = snw{code}_{g} }}\n" for g in goods)
                    + f"{t}save_scope_value_as = {{ name = snwn{code}_{s} value = local_var:spec_news_n }}\n"
                    f"{t}change_local_variable = {{ name = spec_news_s add = local_var:spec_news_n }}\n"
                    f"{t}change_local_variable = {{ name = spec_news_t{code} add = local_var:spec_news_n }}\n")
        out += f"{t}save_scope_value_as = {{ name = snwa_{s} value = local_var:spec_news_s }}\n"
    # the named stance changes; an empty slot still saves a group and a good, so its hidden line has scopes to read
    out += _local_from("spec_news_tm", "spec_news_ig_more") + f"{t}set_local_variable = {{ name = spec_news_ti value = local_var:spec_news_tm }}\n"
    for i in range(1, SLOTS + 1):
        out += (f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_news_igk{i} exists = var:spec_news_ig{i} exists = var:spec_news_igg{i} }}\n"
                f"{t}\tvar:spec_news_ig{i} = {{ save_scope_as = spec_news_ig{i} }}\n"
                f"{t}\tvar:spec_news_igg{i} = {{ save_scope_as = spec_news_igg{i} }}\n"
                f"{t}\tsave_scope_value_as = {{ name = snwk{i} value = var:spec_news_igk{i} }}\n"
                f"{t}\tchange_local_variable = {{ name = spec_news_ti add = 1 }}\n{t}}}\n"
                f"{t}else = {{\n{t}\trandom_interest_group = {{ save_scope_as = spec_news_ig{i} }}\n"
                f"{t}\tg:{GOODS[0]} = {{ save_scope_as = spec_news_igg{i} }}\n"
                f"{t}\tsave_scope_value_as = {{ name = snwk{i} value = 0 }}\n{t}}}\n")
    out += (f"{t}set_local_variable = {{ name = spec_news_qa value = local_var:spec_news_qh }}\n"
            + "".join(f"{t}change_local_variable = {{ name = spec_news_qa add = local_var:spec_news_q{c} }}\n" for c in "123")
            + f"{t}save_scope_value_as = {{ name = snwq value = local_var:spec_news_qa }}\n")  # the unnamed news, for Earlier News
    return (out + _order("s", [(c, f"spec_news_t{c}") for c, _ in SUMMARY])
            + _order("i", [("", "spec_news_ti")]) + _order("m", [("", "spec_news_tm")]))


def effects():
    assert GOODS, "generate's monthly() records the goods before the effects are written"
    clear = "".join(f"    remove_variable = {key}\n" for key in STATE)
    legacy = "".join(f"        if = {{ limit = {{ has_variable = spec_news_{cat}_{kind} }}\n"
                     f"            change_variable = {{ name = spec_news_prior_{kind} add = var:spec_news_{cat}_{kind} }}\n"
                     f"            remove_variable = spec_news_{cat}_{kind}\n        }}\n"
                     for cat in (*CATEGORIES, *GROUPS) for kind in KINDS)
    slots = "".join(f"""        {'if' if i == 1 else 'else_if'} = {{
            limit = {{ NOT = {{ has_variable = spec_news_igk{i} }} }}
            set_variable = {{ name = spec_news_igk{i} value = $K$ }}
            set_variable = {{ name = spec_news_ig{i} value = ig:ig_$IG$ }}
            set_variable = {{ name = spec_news_igg{i} value = g:$G$ }}
        }}
""" for i in range(1, SLOTS + 1))
    return f"""
# old saves: counts by category or sector, without names
spec_migrate_market_news = {{
    if = {{
        limit = {{ OR = {{ has_variable = spec_news_staple_hot has_variable = spec_news_food_hot has_variable = spec_news_opinions }} }}
{"".join(_init(p, "        ") for p in PRIOR)}{legacy}{_init("spec_news_ig_more", "        ")}        if = {{ limit = {{ has_variable = spec_news_opinions }}
            change_variable = {{ name = spec_news_ig_more add = var:spec_news_opinions }}
            remove_variable = spec_news_opinions
        }}
    }}
}}
spec_queue_market_news = {{
    spec_migrate_market_news = yes
    if = {{
        limit = {{ NOT = {{ has_variable = spec_news_age }} }}
        set_variable = {{ name = spec_news_age value = 0 }}
    }}
}}
spec_queue_ig_news = {{
    spec_queue_market_news = yes
    if = {{
        limit = {{ exists = ig:ig_$IG$ }}
{slots}        else = {{
{_init("spec_news_ig_more", "            ")}            change_variable = {{ name = spec_news_ig_more add = 1 }}
        }}
    }}
}}
# the delivery's sector lines: count VAR = S among a line's goods, then number each (1 first, 2 middle, 3 last) as NAME
spec_news_count = {{
    if = {{ limit = {{ var:$VAR$ ?= $S$ }} change_local_variable = {{ name = spec_news_n add = 1 }} }}
}}
spec_news_place = {{
    if = {{
        limit = {{ var:$VAR$ ?= $S$ }}
        change_local_variable = {{ name = spec_news_i add = 1 }}
        if = {{ limit = {{ local_var:spec_news_i = 1 }} save_scope_value_as = {{ name = $NAME$ value = 1 }} }}
        else_if = {{ limit = {{ local_var:spec_news_i = local_var:spec_news_n }} save_scope_value_as = {{ name = $NAME$ value = 3 }} }}
        else = {{ save_scope_value_as = {{ name = $NAME$ value = 2 }} }}
    }}
    else = {{ save_scope_value_as = {{ name = $NAME$ value = 0 }} }}
}}
spec_clear_market_news = {{
{clear}}}
spec_deliver_market_news = {{
    spec_migrate_market_news = yes
    if = {{
        limit = {{ has_variable = spec_news_age }}
        change_variable = {{ name = spec_news_age add = 1 }}
        if = {{
            limit = {{ OR = {{ has_variable = spec_news_urgent var:spec_news_age >= 3 }} }}
{_snapshot()}            post_notification = spec_market_bulletin
            spec_clear_market_news = yes
        }}
    }}
}}
"""


def _gt(name, n=0):  # no spaces: the tooltip repeats these hundreds of times
    return f"GreaterThan_CFixedPoint(SCOPE.GetValue('{name}'),'(CFixedPoint){n}')"


def _eq(name, n):
    return f"EqualTo_CFixedPoint(SCOPE.GetValue('{name}'),'(CFixedPoint){n}')"


def _join(v, key):
    """One name in a list: v is its place (_order's p), key the name's localization."""
    return _sep(v) + f"[AddLocalizationIf({_gt(v)},'{key}')]"


def _sep(v):  # keys, not literals: vanilla never puts a comma inside a quoted argument
    return f"[AddLocalizationIf({_eq(v, 2)},'SPEC_NEWS_COMMA')][AddLocalizationIf({_eq(v, 3)},'SPEC_NEWS_AND')]"


def _sentence(group, clauses):
    """Loc for _order's clauses (code, SPEC_NEWS_SUM_<key>): "Two goods turned feverish and one boom ended in a Bust."."""
    out = ""
    for code, key in clauses:
        b = f"snw{group}{code}"
        out += (_sep(b + "p") + "".join(f"[AddLocalizationIf({_eq(b + 'w', k)},'SPEC_NEWS_N{k}')]"
                          f"[AddLocalizationIf({_eq(b + 'w', 100 + k)},'SPEC_NEWS_NC{k}')]" for k in range(1, 10))
                + f"[AddTextIf({_gt(b + 'n', 9)},ToString_int32(FixedPointToInt(SCOPE.GetValue('{b}n'))))]"
                f"[AddLocalizationIf({_eq(b + 'n', 1)},'SPEC_NEWS_SUM_{key}_ONE')]"
                f"[AddLocalizationIf({_gt(b + 'n', 1)},'SPEC_NEWS_SUM_{key}_MANY')]")
    return out + f"[AddTextIf({_gt('snw' + group)},'.')]"


def description():
    """The toast: one sentence on the goods, one on the interest groups."""
    return (_sentence("s", SUMMARY) + f"[AddTextIf(And({_gt('snws')}, {_gt('snwi')}), ' ')]"
            + _sentence("i", [("", "IG")]))


TIP = "$SPEC_NEWS_DETAIL$"  # notify's tooltip for the bulletin: the title, then this, without the toast's summary
VERBS = ("now support", "no longer support", "now oppose", "no longer oppose")  # ig_stances.STANCES' order


def _sector(s, goods):
    out = f"[AddLocalizationIf({_gt('snwa_' + s)},'SPEC_NEWS_HEAD_{s.upper()}')]"
    for code, *_ in LINES:
        n = f"snwn{code}_{s}"
        names = "".join(_join(f"snw{code}_{g}", g) for g in goods)
        if code == "h":
            out += f"[AddTextIf({_gt(n)},'\\n')]{names}[AddLocalizationIf({_gt(n)},'SPEC_NEWS_L_HOT')]"
        else:
            out += (f"[AddLocalizationIf({_gt(n)},'SPEC_NEWS_L_THE')]{names}[AddLocalizationIf({_eq(n, 1)},'SPEC_NEWS_L_{code}_ONE')]"
                    f"[AddLocalizationIf({_gt(n, 1)},'SPEC_NEWS_L_{code}_MANY')]")
    return out


def loc():
    sectors = _sectors()
    out = "".join(f' SPEC_SECTOR_{key.upper()}: "{title}"\n' for key, (title, _) in GROUPS.items())
    out += "".join(f' SPEC_NEWS_HEAD_{s.upper()}: "\\n\\n#b $SPEC_SECTOR_{s.upper()}$#!"\n' for s, _ in sectors)
    out += "".join(f' SPEC_NEWS_SEC_{s.upper()}: "{_sector(s, goods)}"\n' for s, goods in sectors)
    # each slot's sentence is its own key, so a translation can reorder it (vanilla's picked keys hold [names] too)
    pairs = [(i, j) for i in range(1, SLOTS + 1) for j in range(1, len(VERBS) + 1)]
    slots = "".join(f"[AddLocalizationIf({_eq(f'snwk{i}', j)},'SPEC_NEWS_IG_{i}_{j}')]" for i, j in pairs)
    out += "".join(f' SPEC_NEWS_IG_{i}_{j}: "\\nThe [SCOPE.gsInterestGroup(\'spec_news_ig{i}\').GetName] {VERBS[j - 1]} '
                   f'[SCOPE.sGoods(\'spec_news_igg{i}\').GetName]."\n' for i, j in pairs)
    detail = ("".join(f"$SPEC_NEWS_SEC_{s.upper()}$" for s, _ in sectors)
              + f"[AddLocalizationIf({_gt('snwq')},'SPEC_NEWS_HEAD_PRIOR')]"
              + f"[AddLocalizationIf({_gt('snwi')},'SPEC_NEWS_HEAD_IG')]" + slots
              + f"[AddTextIf({_gt('snwm')},'\\n')]" + _sentence("m", [("", "MORE")]))
    out += f' SPEC_NEWS_DETAIL: "{detail}"\n'
    words = "one two three four five six seven eight nine".split()
    out += "".join(f' SPEC_NEWS_N{k}: "{w}"\n SPEC_NEWS_NC{k}: "{w.capitalize()}"\n' for k, w in enumerate(words, 1))
    for key, one, many in (("COLLAPSE", " boom ended in a #N Collapse#!", " booms ended in #N Collapses#!"),
                           ("BUST", " boom ended in a #N Bust#!", " booms ended in #N Busts#!"),
                           ("HOT", " good turned #v feverish#!", " goods turned #v feverish#!"),
                           ("CORRECTION", " boom ended in a Correction", " booms ended in Corrections"),
                           ("IG", " interest group changed its stance on a good", " interest groups changed their stances on goods"),
                           ("MORE", " more stance changed", " more stances changed")):
        out += f' SPEC_NEWS_SUM_{key}_ONE: "{one}"\n SPEC_NEWS_SUM_{key}_MANY: "{many}"\n'
    out += ' SPEC_NEWS_COMMA: ", "\n SPEC_NEWS_AND: " and "\n SPEC_NEWS_L_HOT: " turned #v feverish#!."\n SPEC_NEWS_L_THE: "\\nThe "\n'
    for code, one, many in (("3", "a #N Collapse#!", "#N Collapses#!"), ("2", "a #N Bust#!", "#N Busts#!"),
                            ("1", "a Correction", "Corrections")):
        out += f' SPEC_NEWS_L_{code}_ONE: " boom ended in {one}."\n SPEC_NEWS_L_{code}_MANY: " booms ended in {many}."\n'
    return out + ''' SPEC_NEWS_HEAD_PRIOR: "\\n\\n#b Earlier News#!\\nSome of this news came in before the update, which did not record names."
 SPEC_NEWS_HEAD_IG: "\\n\\n#b Interest Groups#!"
 rule_spec_goods_news: "Domestic Market News"
 setting_spec_goods_news_bulletin: "Market Bulletins"
 setting_spec_goods_news_bulletin_desc: "Group goods and interest group news by market sector. Routine changes are reported after three monthly reviews. A material bust or collapse brings the bulletin forward."
 setting_spec_goods_news_detailed: "Individual Notices"
 setting_spec_goods_news_detailed_desc: "Report each material good entering feverish speculation, each material boom ending and each interest group stance change separately."
'''
