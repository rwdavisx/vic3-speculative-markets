"""The wider economy in the confidence model: three monthly drivers (growth against the recent average, the
Industrialists' mood, easy money under Loose credit) and two risks the tab shows (diplomatic plays that could become
wars, debt near default). generate.py adds MONTHLY to spec_monthly and the drivers to spec_conf_pre; market_tab.py
groups the drivers into its pressure chips and shows the risks."""
from diplomacy import PLAY_TURMOIL, WAR_ALL_MIN, WAR_BASE, WAR_RISK_ARMY, WAR_RISK_NAVY

GROWTH_KEEP = 0.92          # the GDP average keeps this share a month: about a year's memory
GROWTH_K = 10               # confidence a month per 100% of GDP above its average (5% a year reads about +0.5)
GROWTH_MAX = 0.6
# growth reads against this normal rate: vanilla's typical country grows about 2% a year (20 to 31% a decade), and
# reading against 0 gave every country +0.18 a month, about 4 points of confidence above where it drifts back to
GROWTH_NORMAL = 0.02
# Industrialists' approval; even both ways: -0.6 and -0.3 below gave -0.1 to -0.16 a month as approval fell late game
BUSINESS = [(">=", 10, 0.4), (">=", 5, 0.2), ("<=", -10, -0.4), ("<=", -5, -0.2)]
DEFAULT_FROM = 0.8          # Default Risk shows from this share of the credit limit borrowed
DEFAULT_COST = 5            # what default costs a month (generate.monthly's turmoil)
REVOLUTION_COST = 2         # and a revolution
PLAYS = 3                   # plays named in the War Risk tooltip
BROKE_WEEKS = 20            # the warning starts this many weeks from bankruptcy at the current deficit, as vanilla's war support
BROKE_COST = 3              # confidence a month at the last moment, rising from 0 at BROKE_WEEKS; default itself costs DEFAULT_COST

STATE_VARS = (["spec_gdp_avg", "spec_growth", "spec_c_growth", "spec_c_business", "spec_wr_n",
               "spec_war_risk", "spec_wr_play", "spec_default_risk", "spec_broke_warned"]
              + [f"spec_wr{k}{n}" for n in range(1, PLAYS + 1) for k in ("", "c", "a", "s")])

MONTHLY = f"""			# growth: GDP against its average over about a year
			if = {{
				limit = {{ NOT = {{ has_variable = spec_gdp_avg }} }}
				set_variable = {{ name = spec_gdp_avg value = gdp }}
			}}
			set_variable = {{ name = spec_c_growth value = 0 }}
			if = {{
				limit = {{ var:spec_gdp_avg > 0 }}
				set_variable = {{ name = spec_growth value = {{ value = gdp subtract = var:spec_gdp_avg divide = var:spec_gdp_avg }} }}
				set_variable = {{ name = spec_c_growth value = {{ value = var:spec_growth subtract = {GROWTH_NORMAL} multiply = {GROWTH_K} min = -{GROWTH_MAX} max = {GROWTH_MAX} }} }}
			}}
			set_variable = {{ name = spec_gdp_avg value = {{ value = var:spec_gdp_avg multiply = {GROWTH_KEEP} add = {{ value = gdp multiply = {1 - GROWTH_KEEP:.2g} }} }} }}
			# business mood: the Industrialists' approval
			set_variable = {{ name = spec_c_business value = 0 }}
{"".join(f'''			{"if" if i == 0 else "else_if"} = {{
				limit = {{ ig:ig_industrialists ?= {{ ig_approval {op} {at} }} }}
				set_variable = {{ name = spec_c_business value = {val} }}
			}}
''' for i, (op, at, val) in enumerate(BUSINESS))}			# war risk: the plays short of war we are in, each the war it could become a month, by the enemy side's
			# share of both sides' armies and navies (diplomacy.WAR_RISK_ARMY, WAR_RISK_NAVY)
			set_variable = {{ name = spec_wr_n value = 0 }}
			set_variable = {{ name = spec_war_risk value = 0 }}
			remove_variable = spec_wr_play
{"".join(f"			remove_variable = spec_wr{k}{n}{chr(10)}" for n in range(1, PLAYS + 1) for k in ("", "c", "a", "s"))}			# every play worldwide (vanilla has no list of a country's own), kept where we take part; only scanned
			# while we are in one, as most countries are not in any
			if = {{
				limit = {{
					OR = {{
						is_diplomatic_play_committed_participant = yes
						is_diplomatic_play_undecided_participant = yes
					}}
				}}
				every_diplomatic_play = {{
					limit = {{
						is_war = no
						any_scope_play_involved = {{ this = root }}
					}}
					# the other side's leader: the target if it is against us, else the initiator (a play we back for a
					# subject or ally has our own side as its initiator or target)
					if = {{
						limit = {{ target = {{ is_diplomatic_play_enemy_of = root }} }}
						target = {{ save_scope_as = spec_rival }}
					}}
					else = {{
						initiator = {{ save_scope_as = spec_rival }}
					}}
					# each side's armies and navies: the enemy side, and ours (us and our backers)
{"".join(f"					set_local_variable = {{ name = spec_w{s} value = 0 }}{chr(10)}" for s in ("ea", "en", "oa", "on"))}					every_scope_play_involved = {{
						if = {{
							limit = {{ is_diplomatic_play_enemy_of = root }}
							change_local_variable = {{ name = spec_wea add = army_size }}
							change_local_variable = {{ name = spec_wen add = navy_size }}
						}}
						else_if = {{
							limit = {{
								OR = {{
									this = root
									is_diplomatic_play_ally_of = root
								}}
							}}
							change_local_variable = {{ name = spec_woa add = army_size }}
							change_local_variable = {{ name = spec_won add = navy_size }}
						}}
					}}
{"".join(f'''					set_local_variable = {{ name = spec_w{s} value = {{ value = local_var:spec_we{f} divide = {{ value = local_var:spec_we{f} add = local_var:spec_wo{f} min = 1 }} }} }}
''' for s, f in (("a", "a"), ("s", "n")))}					root = {{
						change_variable = {{ name = spec_wr_n add = 1 }}
						set_local_variable = {{ name = spec_wc value = {{ value = local_var:spec_wa multiply = local_var:spec_wa multiply = {WAR_RISK_ARMY}
							add = {{ value = local_var:spec_ws multiply = local_var:spec_ws multiply = {WAR_RISK_NAVY} }} add = {WAR_BASE} }} }}
						change_variable = {{ name = spec_war_risk add = local_var:spec_wc }}
{"".join(f'''						{"if" if n == 1 else "else_if"} = {{
							limit = {{ var:spec_wr_n = {n} }}
							set_variable = {{ name = spec_wr{n} value = scope:spec_rival }}
							set_variable = {{ name = spec_wrc{n} value = local_var:spec_wc }}
							set_variable = {{ name = spec_wra{n} value = local_var:spec_wa }}
							set_variable = {{ name = spec_wrs{n} value = local_var:spec_ws }}
						}}
''' for n in range(1, PLAYS + 1))}					}}
				}}
				# what war would add: it replaces the play's own cost (spec_monthly, paid while at no war), and all wars
				# together are capped as in diplomacy.MONTHLY
				if = {{
					limit = {{ is_at_war = no }}
					change_variable = {{ name = spec_war_risk add = -{PLAY_TURMOIL} }}
					set_variable = {{ name = spec_wr_play value = {PLAY_TURMOIL} }}
				}}
				clamp_variable = {{ name = spec_war_risk min = 0 max = {-WAR_ALL_MIN} }}
			}}
			# default risk: debt near the credit limit
			remove_variable = spec_default_risk
			if = {{
				limit = {{
					in_default = no
					OR = {{
						scaled_debt >= {DEFAULT_FROM}
						spec_nearly_broke = yes
					}}
				}}
				set_variable = {{ name = spec_default_risk value = scaled_debt }}
			}}
"""


# running out of money: confidence slides before default, a player hears of it, and the AI stops spending
BROKE_TRIGGER = f"""spec_nearly_broke = {{
	taking_loans = yes
	in_default = no
	weeks_until_bankruptcy < {BROKE_WEEKS}
}}
"""
BROKE_VALUES = f"""spec_ind_approval = {{
	value = 0
	if = {{
		limit = {{ exists = ig:ig_industrialists }}
		add = ig:ig_industrialists.ig_approval
	}}
}}
spec_broke_weeks = {{
	value = weeks_until_bankruptcy
}}
spec_broke_cost = {{
	value = {BROKE_WEEKS}
	subtract = weeks_until_bankruptcy
	divide = {BROKE_WEEKS}
	min = 0
	max = 1
	multiply = -{BROKE_COST}
}}
"""
# in spec_monthly's turmoil
BROKE_MONTHLY = """			remove_variable = spec_tm_broke
			if = {
				limit = { spec_nearly_broke = yes }
				set_variable = { name = spec_tm_broke value = spec_broke_cost }
				change_variable = { name = spec_c_turmoil add = var:spec_tm_broke }
				if = {
					limit = {
						is_player = yes
						NOT = { has_variable = spec_broke_warned }
					}
					post_notification = spec_nearly_broke
					set_variable = { name = spec_broke_warned days = 365 }
				}
			}
"""


def build(write):
    write("common/scripted_triggers/spec_economy_triggers.txt", BROKE_TRIGGER)
    write("common/script_values/spec_economy_values.txt", BROKE_VALUES)


if __name__ == "__main__":
    assert MONTHLY.count("{") == MONTHLY.count("}")
    assert "ig_approval >= 10" in MONTHLY and "ig_approval <= -5" in MONTHLY and "else_if" in MONTHLY
    assert MONTHLY.index("every_diplomatic_play") < MONTHLY.index("every_scope_play_involved")
    assert MONTHLY.index("is_diplomatic_play_committed_participant = yes") < MONTHLY.index("every_diplomatic_play")
    assert "remove_variable = spec_wrs3" in MONTHLY and f"multiply = {WAR_RISK_ARMY}" in MONTHLY and f"add = {WAR_BASE}" in MONTHLY
    print("economy ok")
