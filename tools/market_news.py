"""Domestic market notices. Interrupt for a material bust or collapse and collect routine changes for three pulses."""
from sectors import CATEGORIES, GROUPS

DETAILED = "has_game_rule = spec_goods_news_detailed"
KINDS = ("hot", "correction", "bust", "collapse")
ROWS = (*GROUPS, "prior")
COUNTERS = [f"spec_news_{cat}_{kind}" for cat in ROWS for kind in KINDS] + ["spec_news_opinions"]
STATE = ["spec_news_age", "spec_news_urgent", *COUNTERS]
RULE = """spec_goods_news = {
    default = spec_goods_news_bulletin
    spec_goods_news_bulletin = {}
    spec_goods_news_detailed = {}
}
"""


def alternate(detailed, field, indent, urgent=False):
    queue = f"{indent}\tspec_queue_market_news = {{ FIELD = {field} }}\n"
    if urgent:
        queue += f"{indent}\tset_variable = spec_news_urgent\n"
    return (f"{indent}if = {{\n{indent}\tlimit = {{ {DETAILED} }}\n"
            + "".join("\t" + line for line in detailed.splitlines(True)) + f"{indent}}}\n"
            + f"{indent}else = {{\n{queue}{indent}}}\n")


def effects():
    initialize = "".join(f"        set_variable = {{ name = {key} value = 0 }}\n" for key in COUNTERS)
    snapshot = "".join(f"            save_scope_value_as = {{ name = {key} value = var:{key} }}\n" for key in COUNTERS)
    clear = "".join(f"    remove_variable = {key}\n" for key in STATE)
    legacy = "".join(f"        change_variable = {{ name = spec_news_prior_{kind} add = var:spec_news_{cat}_{kind} }}\n"
                     f"        remove_variable = spec_news_{cat}_{kind}\n" for cat in CATEGORIES for kind in KINDS)
    fresh = initialize.replace("        set_variable = { name = spec_news_opinions value = 0 }\n", "")
    return f"""
spec_migrate_market_news = {{
    if = {{ limit = {{ has_variable = spec_news_staple_hot }}
{fresh}{legacy}    }}
}}
spec_queue_market_news = {{
    spec_migrate_market_news = yes
    if = {{
        limit = {{ NOT = {{ has_variable = spec_news_age }} }}
        set_variable = {{ name = spec_news_age value = 0 }}
{initialize}    }}
    change_variable = {{ name = spec_news_$FIELD$ add = 1 }}
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
{snapshot}            post_notification = spec_market_bulletin
            spec_clear_market_news = yes
        }}
    }}
}}
"""


def description():
    def count(field):
        return f"[SCOPE.GetValue('spec_news_{field}')|0]"
    lines = ["Feverish / Corrections / Busts / Collapses"]
    for cat in ROWS:
        checks = [f"GreaterThan_CFixedPoint(SCOPE.GetValue('spec_news_{cat}_{kind}'), '(CFixedPoint)0')" for kind in KINDS]
        test = f"Or(Or({checks[0]}, {checks[1]}), Or({checks[2]}, {checks[3]}))"
        # The nested localization for a row has no notification SCOPE. Format the saved
        # counts in the outer description and localize only the static sector label.
        values = [f"IntToString(FixedPointToInt(SCOPE.GetValue('spec_news_{cat}_{kind}')))" for kind in KINDS]
        counts = values[0]
        for value in values[1:]:
            counts = f"Concatenate({counts}, Concatenate(' / ', {value}))"
        lines[0] += f"[AddTextIf({test}, Concatenate(Localize('SPEC_NEWS_ROW_{cat.upper()}'), {counts}))]"
    lines.append(f"Interest group stance changes: {count('opinions')}")
    return r"\n".join(lines)


def loc():
    names = "".join(f' SPEC_SECTOR_{key.upper()}: "{title}"\n' for key, (title, _) in GROUPS.items())
    names += ' SPEC_SECTOR_PRIOR: "Before the sector update"\n'
    for cat in ROWS:
        names += f' SPEC_NEWS_ROW_{cat.upper()}: "\\n$SPEC_SECTOR_{cat.upper()}$   "\n'
    return names + ''' rule_spec_goods_news: "Domestic Market News"
 setting_spec_goods_news_bulletin: "Market Bulletins"
 setting_spec_goods_news_bulletin_desc: "Group goods and interest group news by market sector. Routine changes are reported after three monthly reviews. A material bust or collapse brings the bulletin forward."
 setting_spec_goods_news_detailed: "Individual Notices"
 setting_spec_goods_news_detailed_desc: "Report each material good entering feverish speculation, each material boom ending and each interest group stance change separately."
'''
