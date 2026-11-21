"""A monthly PROBE line per country of things vanilla has too (GDP, living standards, debt, investment, war,
default), so a vanilla control run can be set beside ours: generate.py adds it to --log builds, and observe.py
--vanilla runs it alone as a tiny logging-only mod.

Usage: py -3 tools/probe.py <folder> writes the logging-only mod there."""
import json
import sys
from pathlib import Path

MARKER = "SPEC_PROBE init OK"
VALUES = "common/script_values/spec_probe_values.txt"
ACTIONS = "common/on_actions/spec_probe_on_actions.txt"
FIELDS = {"gdp": "gdp", "sol": "average_sol", "debt": "principal", "inv": "investment_pool_income"}
FLAGS = {"war": "is_at_war = yes", "default": "in_default = yes"}
FINANCE_TECHS = ("banking", "currency_standards", "international_trade", "stock_exchange", "joint_stock_companies",
                 "central_banking", "investment_banks", "international_exchange_standards", "mutual_funds",
                 "modern_financial_instruments", "macroeconomics")
# weekly construction goods spending (all, private) and construction points used: engine data functions, no script value
CALLS = {"cg": "GetConstructionGoodsExpenses", "pcg": "GetPrivateConstructionGoodsExpenses", "cu": "CalcUsedConstruction"}


def files(*, fiscal=False):
    sampled, flags = FIELDS, FLAGS
    if fiscal:
        sampled = {**FIELDS, "cash": "gold_reserves", "sdebt": "scaled_debt", "net": "net_total_income",
                   "auth": "authority", "grant": "spec_lever_spend", "levy": "spec_lever_levy", "used": "spec_lever_authority"}
        flags = {**FLAGS, "near": "spec_nearly_broke = yes", "gp": "country_rank = rank_value:great_power",
                 "ind": "ig:ig_industrialists ?= { is_in_government = yes }",
                 "intel": "ig:ig_intelligentsia ?= { is_in_government = yes }"}
        flags.update((tech, f"has_technology_researched = {tech}") for tech in FINANCE_TECHS)
    values = "".join(f"spec_probe_{k} = {{\n\tvalue = {v}\n}}\n" for k, v in sampled.items())
    values += "".join(f"spec_probe_{k} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {t} }}\n\t\tvalue = 1\n\t}}\n}}\n"
                      for k, t in flags.items())
    fields = " ".join(f"{k}=[THIS.ScriptValue('spec_probe_{k}')]" for k in (*sampled, *flags))
    fields += "".join(f" {k}=[THIS.GetCountry.{f}]" for k, f in CALLS.items())
    # only on_actions lists on the vanilla on_actions, never an effect block, which would replace vanilla's
    actions = f"""on_monthly_pulse_country = {{
	on_actions = {{ spec_probe_monthly }}
}}

spec_probe_monthly = {{
	effect = {{
		debug_log = "PROBE tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] {fields}"
	}}
}}
"""
    return {VALUES: values, ACTIONS: actions}


def build(write, log):
    """Adds the probe to a --log build of our mod; a release build gets none (generate.py clears the files)."""
    if log:
        for rel, text in files().items():
            write(rel, text)


def standalone(folder):
    """The logging-only mod for a vanilla control, with its own start marker."""
    folder = Path(folder)
    meta = {"name": "Speculative Markets probe", "id": "speculative_markets_probe", "version": "0.1.0",
            "supported_game_version": "1.14.*", "short_description": "Logging only.", "tags": [],
            "relationships": [], "game_custom_data": {"multiplayer_synchronized": True}}
    out = {".metadata/metadata.json": json.dumps(meta, indent=2), **files()}
    out[ACTIONS] = (f"on_game_started_after_lobby = {{\n\ton_actions = {{ spec_probe_marker }}\n}}\n\n"
                    f"spec_probe_marker = {{\n\teffect = {{\n\t\tdebug_log = \"{MARKER}\"\n\t}}\n}}\n\n" + out[ACTIONS])
    for rel, text in out.items():
        p = folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8" if rel.endswith(".json") else "utf-8-sig", newline="\n")
    return folder


if __name__ == "__main__":
    print(standalone(sys.argv[1]))
