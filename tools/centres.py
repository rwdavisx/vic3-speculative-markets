"""The world's Financial Centres: the PLACES largest money markets, ranked once a month and listed in the Speculation
tab. A place on the list gives prestige; a Financial Panic halves a market's score, which then grows
back over CALM quiet months.

Score = MONTHS of Investment Pool income + Outstanding Credit, times 0.5 to 1.5 by the months since the last panic,
then scaled so the leader has 100 (the Exchange: Size x Depth, against the top three; see SIZE_X). var:spec_centre_calm is this module's own count of quiet months
(journal's spec_calm is reset by the Commission of Inquiry). Global variables spec_centre_1..PLACES hold the listed
countries; var:spec_centre_rank a listed country's place. Separate from Foreign Lending.

The Exchange (EXCHANGE_ON, a trial; 0 builds the mod as before): var:spec_centre_trust (0 to CALM) takes the place of
the quiet months in the score. It grows in quiet months under sound Lending Standards, falls when booms end or banks
lend recklessly, is cut by PANIC_CUT when a panic starts (a fifth at no leverage to half at the ruin line, half that for a
panic caught from abroad) and halved again if the panic runs its full course unrescued.
var:spec_exch_stand is a market's Standing (0 Provincial, 1 National, 2 International, 3 World Centre): hotter booms,
more capital flight received. var:spec_exch_known is what it is known for (1 Commodity Exchange, 2 Deposit Banks,
3 Stock Exchange), chosen in spec_exchange.1 each time it reaches a Standing above var:spec_exch_best."""
import companies
import cycle
import icons
import leverage
import levers
import monetary
import power_bloc
import stories
import tuning
import vanilla_ties
from market_tab import P, W, BAR_W, fx, gt, v, ind, header, block, heads, sg

PLACES = 5
MONTHS = tuning.get("CENTRE_MONTHS", 6)
CALM = tuning.get("CENTRE_CALM", 120)
# prestige for each place from the bottom: 5 steps for the first. It also cut loan interest by as much until 1.2, which
# with vanilla's -50% for Great Powers and the mod's other cuts took loans past -100%
STEP = tuning.get("CENTRE_STEP", 0.02)
INCOME = "spec_lev_income" if leverage.ON else "spec_pool_month"
ROW_H = 40  # vanilla's ranked country rows (map_list_panel_item; was 35)
SLOT = lambda n: f"GetGlobalVariable('spec_centre_{n}')"

ON = tuning.get("EXCHANGE_ON", 1)
NATIONAL = tuning.get("EXCH_NATIONAL", 15)        # the score (% of the top three) a market needs to stand National, if it is not listed
HOLD = tuning.get("EXCH_HOLD", 2)                 # a National market keeps its Standing until this far under the line
HYPE = tuning.get("EXCH_HYPE", {1: 1.05, 2: 1.1, 3: 1.15})   # spec_hype_mult by Standing (Provincial 1)
# capital flight received by Standing (Provincial 1); only International or higher, or a Great Power, receives any
# (diplomacy.SAFE), so every flight bonus says so (FLIGHT_IF)
FLIGHT = tuning.get("EXCH_FLIGHT", {1: 1, 2: 2, 3: 2})  # World Centre was x3 before beta.12: the leader's pool grew fastest and kept it first
FLIGHT_IF = "at International Standing or higher, or as a [concept_great_power]"
PRESTIGE = tuning.get("EXCH_PRESTIGE", 0.02)      # above Provincial and unlisted: the listed places have their own modifier
MAIN_SHARE = 0.01  # a good with this share of the market's trade: its boom's end moves trust and gets a toast (generate.TOAST_SHARE)
TRUST_END = tuning.get("EXCH_TRUST_END", {1: 2, 2: -6, 3: -18})  # a boom's ending: Correction, Bust, Collapse
KNOWN_HYPE = tuning.get("EXCH_KNOWN_HYPE", 1.1)   # 1 Commodity Exchange: its booms
KNOWN_LOSS = tuning.get("EXCH_KNOWN_LOSS", 0.75)  # 2 Deposit Banks: share of each loss of trust it takes
KNOWN_CREDIT = tuning.get("EXCH_KNOWN_CREDIT", 1.1)  # 3 Stock Exchange: credit lent each month
WORLD_PLACES = tuning.get("EXCH_WORLD_PLACES", 3)  # beta.12: the top three are World Centres (was the first alone)
# 1.2: only the monetary standard (monetary.GOLD_LOAN) and Converted Debt (journal.CONVERT_RATE) make loans cheaper,
# -20% at most: with vanilla's -50% for a Great Power and Laissez-Faire's -25% that tops out at -95%, as vanilla's own
# extremes do. Ten small cuts here once stacked past -100% (the game then charges 0%). Dearer loans (fear, distrust,
# the Long Depression) stay.
WORLD_FX = tuning.get("EXCH_WORLD_FX", [["country_influence_mult", 0.1]])  # was also -5% loan interest
WORLD_SHELTER = tuning.get("EXCH_WORLD_SHELTER", 0.7)  # foreign panics' loss at a World Centre: the hub money runs to
GATE = "has_technology_researched = central_banking"  # as Credit Policy (generate.triggers)
CALM_VAR = "spec_centre_trust" if ON else "spec_centre_calm"
# Phase 1 (plan_levers.md): the score leaves out Outstanding Credit, and a place adds to the credit limit
BRAKE = ON and tuning.get("EXCH_BRAKE_ON", 1)
LIMIT_STEP = tuning.get("EXCH_LIMIT_STEP", 1)     # credit limit months for each place from the bottom
# The Exchange score (Exchange on): Size, the square root of the capital the Exchange draws on (its own, six months'
# pool income averaged over a year, and a share of smaller tied countries'), times Depth: wealth per head, Financial
# Districts, companies, finance technologies, rank, the economic system, trust and a Great Issue.
# Shown against the world's top three, and against its region's leader (by capital), which can also make it National
# or International. Size has diminishing returns so the largest countries do not win by size alone.
CAP_PER = tuning.get("EXCH_CAP_PER", 1000)   # pounds of six months' pool income for a unit of capital
SIZE_X = tuning.get("EXCH_SIZE_X", 10)       # points for each unit of the root of capital
# 2: the square root of capital; 4: its fourth root (beta.12), so the largest pool (Britain's, ~9x France's by 1855)
# leads by under 2x on capital alone instead of 3x
SIZE_ROOT = tuning.get("EXCH_SIZE_ROOT", 4)
assert SIZE_ROOT in (2, 4)
SMOOTH = tuning.get("EXCH_SMOOTH", 0.1)      # share of the gap to this month's pool income the average closes
REACH = tuning.get("EXCH_REACH", 0.25)       # share of a smaller tied country's capital drawn on; at most our own in all
WEALTH = tuning.get("EXCH_WEALTH", [0.75, 1.5])  # bounds of the wealth-per-head multiplier (the square root of the ratio); [0.5, 2] before beta.12
FD_STEP, FD_CAP = tuning.get("EXCH_FD_STEP", 0.01), tuning.get("EXCH_FD_CAP", 50)  # a Financial District level, up to
CO_STEP, CO_CAP = tuning.get("EXCH_CO_STEP", 0.03), tuning.get("EXCH_CO_CAP", 10)  # a company headquartered here, up to
RANK = tuning.get("EXCH_RANK", {"great_power": 1.15, "major_power": 1.05})
REG_NATIONAL = tuning.get("EXCH_REG_NATIONAL", 35)  # % of its region's leader that also makes a market National
REG_HOLD = tuning.get("EXCH_REG_HOLD", 5)           # and how far under that it keeps it
INTL_GATE = "has_technology_researched = stock_exchange"
# by the capital's geographic region, the first that holds; the last takes the rest
REGIONS = [(["europe"], "Europe"), (["latin_america"], "Latin America"), (["north_america"], "North America"),
           (["africa", "middle_east"], "Africa and the Middle East"), (["india"], "South Asia"), ([], "East Asia and the Pacific")]
SQ_STEPS = 10  # Newton's steps for a square root: there is none in script


def _newton(x):
    if x == 0:
        return 0
    r = x / 40 + 2
    for _ in range(SQ_STEPS):
        r = (x / r + r) / 2
    return r


assert all(abs(_newton(x) - x ** 0.5) <= 0.005 * x ** 0.5 + 0.005 for x in (0, 0.01, 0.3, 1, 7, 90, 1400, 50000, 1e6))
TECHS = tuning.get("EXCH_TECHS", {"banking": 0.05, "stock_exchange": 0.05, "central_banking": 0.05,
                                  "joint_stock_companies": 0.05, "mutual_funds": 0.05, "investment_banks": 0.1,
                                  "international_exchange_standards": 0.1, "modern_financial_instruments": 0.1})
ECON = tuning.get("EXCH_ECON", {"laissez_faire": 1.15, "interventionism": 1.05, "agrarianism": 0.95,
                                "traditionalism": 0.9, "extraction_economy": 0.9, "command_economy": 0.75,
                                "cooperative_ownership": 0.6})
PLEDGE_ON = ON and tuning.get("EXCH_PLEDGE_ON", 1)
PLEDGE_PANIC = tuning.get("EXCH_PLEDGE_PANIC", 0.5)     # share of a panic's usual trust loss it costs while pledged (was 25% of trust, not half)
# a panic's trust loss at its start: PANIC_CUT[0] at no leverage, up to PANIC_CUT[0] + PANIC_CUT[1] at the ruin line
PANIC_CUT = tuning.get("EXCH_PANIC_CUT", (0.2, 0.3))
CAUGHT_CUT = 0.5  # share of that a panic caught from abroad (spec_caught) costs
PANIC_OVER_CUT = 0.5  # share of the trust left a panic takes as it ends, if it ran its full course unrescued (PANIC_OVER)
TRUST_MONTH = CALM / 100  # one point of the 0-100 trust the bar shows (was a flat 1, 0.83 points)
# 2026-11-22 a calm month's trust by Lending Standards level (cycle.LAX_WORDS), in points, the stricter the faster:
# Strict +0.83 -> +2, Cautious +0.83 -> +1.5, Sound +0.83 -> +1, Lax 0, Reckless -0.83 -> -1 (times spec_exch_loss).
# Tuner keys, on a 0.5 grid
TRUST_BY_LAX = (tuning.get("TRUST_STRICT", 2), tuning.get("TRUST_CAUTIOUS", 1.5), tuning.get("TRUST_SOUND", 1),
                tuning.get("TRUST_LAX", 0), tuning.get("TRUST_RECKLESS", -1))  # each by name, for the tuner's parity check
PLEDGE_FLIGHT = tuning.get("EXCH_PLEDGE_FLIGHT", 1.5)   # capital flight received while pledged
PLEDGE_SHARE = tuning.get("EXCH_PLEDGE_COST", 0.75)     # the rescue's cost while pledged
PLEDGE_NOTICE = tuning.get("EXCH_PLEDGE_NOTICE", 24)    # months of notice to withdraw
PLEDGE_DEBT = tuning.get("EXCH_PLEDGE_DEBT", 0.5)       # most scaled_debt to make the pledge
PLEDGE_BREAK = tuning.get("EXCH_PLEDGE_BREAK", {"conf": 15, "legit": 10})  # a default breaks it: confidence, legitimacy (5 years)
PLEDGE_BROKEN_MONTHS = 60  # the Broken Pledge modifier's months
# Phase 4: what the Exchange is known for is earned once a year by building, not chosen in spec_exchange.1
EARN = ON and tuning.get("EXCH_EARN_ON", 1)
EARN_TC = tuning.get("EXCH_EARN_TC", 20)            # 1 Commodity Exchange: Trade Center levels
EARN_SOUND = tuning.get("EXCH_EARN_SOUND", 120)     # 2 Deposit Banks: quiet months under sound Lending Standards
EARN_CO = tuning.get("EXCH_EARN_CO", 4)             # 3 Share Market: companies with prosperity >= EARN_PROSPER
EARN_PROSPER = tuning.get("EXCH_EARN_PROSPER", 50)  # ponytail: scale assumed 0-100 (vanilla only shows >= 100); kco logs it
CO_STRENGTH = tuning.get("EXCH_CO_STRENGTH", 20)    # Home of Great Companies: prosperity per point (a company at 100 is 5)
EARN_BY = {1: "spec_earn_tc", 2: "spec_earn_snd", 3: "spec_earn_co"}

LINKS = ON and tuning.get("EXCH_LINKS_ON", 1)
LINK_MOOD = tuning.get("EXCH_LINK_MOOD", 1)          # Market Mood swings: x1.5 with no trust to x0.5 at full trust
LINK_RECOVER = tuning.get("EXCH_LINK_RECOVER", 1)    # confidence recovery: x0.75 with no trust to x1.5 at full trust
LINK_CRUNCH = tuning.get("EXCH_LINK_CRUNCH", 1)      # trust lost a month under Bad Debts, and the Standing cannot rise
CRUNCH = LINKS and LINK_CRUNCH and leverage.ON      # Bad Debts are leverage.py's
LINK_PROSPER = tuning.get("EXCH_LINK_PROSPER", 0.2)  # Market Mood a month per Share Market tally past its mark, within 0 to 0.3
LINK_IND = tuning.get("EXCH_LINK_IND", 0)            # Industrialists' political strength per Standing (Q2: ships at 0)
MOOD_REF = "\tmultiply = spec_exch_mood\n" if LINKS and LINK_MOOD else ""            # generate's spec_mood_scale
RECOVER_REF = "\tmultiply = spec_exch_recover\n" if LINKS and LINK_RECOVER else ""   # generate's spec_conf_recover
# after the roll is scaled, so the Market Mood tooltip's "This Month's Shift" includes it
LEAN = "\t\t\tchange_variable = { name = spec_mood_shift add = spec_exch_lean }\n" if LINKS and LINK_PROSPER else ""
# hooks for generate.py, empty when off
HYPE_REF = "\tmultiply = spec_exch_hype\n" if ON else ""
CREDIT = "\tmultiply = spec_exch_credit\n" if ON else ""
FLIGHT_REF = "\tmultiply = spec_exch_flight\n" if ON else ""
LIMIT_REF = "\tadd = spec_exch_limit\n" if BRAKE else ""
PLEDGE_COST = "\tmultiply = spec_pledge_cost\n" if PLEDGE_ON else ""  # spec_rescue_share
# after spec_start_panic's trust loss: the pledged rescue comes at once (spec_rescue pays as the button), if the treasury
# can pay it out of reserves and the country is not in default. If not, the panic runs unrescued, the pledge stands, and the
# panic event says so (spec_pledge_unmet)
PLEDGE_RESCUE = ("\tif = {\n\t\tlimit = { has_variable = spec_pledge }\n"
                 "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\tspec_can_rescue = yes\n\t\t\t\tin_default = no\n\t\t\t\tgold_reserves >= spec_rescue_cost\n\t\t\t}\n"
                 "\t\t\tspec_rescue = yes\n\t\t}\n"
                 "\t\telse = {\n\t\t\tset_variable = { name = spec_pledge_unmet days = 30 }\n"
                 "\t\t\tif = { limit = { in_default = yes } set_variable = { name = spec_pledge_reason value = 2 days = 30 } }\n"
                 "\t\t\telse_if = { limit = { NOT = { has_technology_researched = banking } } set_variable = { name = spec_pledge_reason value = 3 days = 30 } }\n"
                 "\t\t\telse_if = { limit = { gold_reserves < spec_rescue_cost }\n"
                 "\t\t\t\tset_variable = { name = spec_pledge_reason value = 1 days = 30 }\n"
                 "\t\t\t\tset_variable = { name = spec_pledge_required value = spec_rescue_cost days = 30 }\n"
                 "\t\t\t\tset_variable = { name = spec_pledge_shortfall value = { value = spec_rescue_cost subtract = gold_reserves } days = 30 }\n"
                 "\t\t\t}\n\t\t}\n\t}\n") if PLEDGE_ON else ""
# the panic event's last line, for generate.panic_loc
PLEDGE_UNMET = "[AddLocalizationIf(ROOT.GetCountry.MakeScope.Var('spec_pledge_unmet').IsSet, 'SPEC_PLEDGE_UNMET')]" if PLEDGE_ON else ""
LIMIT_LINE ="[AddLocalizationIf(Country.MakeScope.Var('spec_centre_rank').IsSet, 'SPEC_EXCH_LIMIT')]" if BRAKE else ""  # market_tab's credit limit
LOG = ((" stand=[THIS.Var('spec_exch_stand').GetValue] trust=[THIS.Var('spec_centre_trust').GetValue]"
        " cscore=[THIS.Var('spec_centre_score').GetValue] known=[THIS.Var('spec_exch_known').GetValue]"
        " xs=[THIS.Var('spec_xs_raw').GetValue] xreg=[THIS.Var('spec_xs_reg').GetValue] xsize=[THIS.Var('spec_xs_size_v').GetValue]"
        " xwl=[THIS.Var('spec_xs_wealth_v').GetValue] xrch=[THIS.Var('spec_xs_reach_v').GetValue] xrs=[THIS.Var('spec_xs_regshare').GetValue]")
       + (" climit=[THIS.ScriptValue('spec_credit_limit')]" if BRAKE and leverage.ON else "")
       + (" elimit=[THIS.ScriptValue('spec_exch_limit')]" if BRAKE else "")
       + (" pledge=[THIS.ScriptValue('spec_log_pledge')] pbroke=[THIS.ScriptValue('spec_log_pbroke')]" if PLEDGE_ON else "")
       + (" issue=[THIS.ScriptValue('spec_log_issue')]" if levers.ISSUE_ON else "")
       # the raw counts, not the plan's tallies x100: tally = count / its mark, and kco shows the prosperity scale
       + (" ktc=[THIS.ScriptValue('spec_log_ktc')] kco=[THIS.ScriptValue('spec_log_kco')] ksnd=[THIS.ScriptValue('spec_log_ksnd')]"
          if EARN else "")) if ON else ""


def _lose(by, t):
    """Trust down by `by` (a number, or a script value's lines), times spec_exch_loss (Deposit Banks, specialities),
    never below 0."""
    return (f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
            f"subtract = {{ value = {by} multiply = spec_exch_loss }} min = 0 }} }}\n")


def _gain(by, t):
    return f"{t}set_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust add = {by} max = {CALM} }} }}\n"


TRUST_CAUSES = ("goods", "panics", "lending", "debts", "rivals", "chips", "charter")
TRUST_RECORD = ["spec_trust_review", "spec_trust_change", *[f"spec_trust_{cause}_{period}"
                for cause in TRUST_CAUSES for period in ("pending", "last")]]


def _record_trust(effect, cause, t, why=None):
    import bluechips  # the recorder lives there, as rivals and bluechips record too
    return bluechips.record_trust(effect, cause, t, why)


def _trust_review(t):
    # Compare like points in consecutive monthly reviews. Count event effects after caps and charter reductions.
    snapshot = "".join(f"{t}\t\tset_variable = {{ name = spec_trust_{c}_last value = {{ value = 0 "
                       f"if = {{ limit = {{ has_variable = spec_trust_{c}_pending }} value = var:spec_trust_{c}_pending }} }} }}\n"
                       for c in TRUST_CAUSES)
    reset = "".join(f"{t}\tset_variable = {{ name = spec_trust_{c}_pending value = 0 }}\n" for c in TRUST_CAUSES)
    clear = "".join(f"{t}\tremove_variable = {key}\n" for key in TRUST_RECORD)
    return (f"{t}if = {{\n{t}\tlimit = {{ is_player = yes }}\n"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = spec_trust_review }}\n"
            f"{t}\t\tset_variable = {{ name = spec_trust_change value = {{ value = var:spec_centre_trust subtract = var:spec_trust_review }} }}\n"
            f"{snapshot}{t}\t}}\n{reset}{t}\tset_variable = {{ name = spec_trust_review value = var:spec_centre_trust }}\n"
            f"{t}}}\n{t}else_if = {{\n{t}\tlimit = {{ has_variable = spec_trust_review }}\n{clear}{t}}}\n")


def boom_end(g, sev, share, t="\t\t\t\t"):
    """In g's boom-ending branch, country scope, for goods that matter to the market (the boom-end toast's gate)."""
    if not ON:
        return ""
    d = TRUST_END[sev]
    apply = lambda d, t: _record_trust(_gain(d, t) if d > 0 else _lose(-d, t), "goods", t, f"end{sev}")
    if not levers.ISSUE_ON:
        return f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_centre_trust spec_weight_{g} >= {share:.3f} }}\n" + apply(d, t + "\t") + f"{t}}}\n"
    # a Great Issue on g (levers.py): the result counts ISSUE_TRUST times, then the issue is over and the market rests
    return (f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_centre_trust spec_weight_{g} >= {share:.3f} }}\n" + apply(d, t + "\t")
            + f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = spec_issue_{g} }}\n" + apply(d * (levers.ISSUE_TRUST - 1), t + "\t\t") + f"{t}\t}}\n{t}}}\n"
            f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_issue_{g} }}\n{t}\tremove_variable = spec_issue_{g}\n{t}\tremove_variable = spec_issue\n"
            f"{t}\tset_variable = {{ name = spec_issue_cool value = {levers.COOL_MONTHS} }}\n"  # pulses left (levers.spec_issue_clock)
            f"{t}\tspec_update_levers = yes\n{t}}}\n")  # the Restrain/Encourage buttons see the issue gone now, not next month


HALF = f"var:spec_centre_trust multiply = {PANIC_OVER_CUT:g}"
# in spec_start_panic; and in spec_end_panic before spec_rescued and spec_panic are cleared, so a rescued panic, or one that
# ended early as confidence came back, loses trust only once
PANIC = (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_centre_trust }}\n"
         f"{_record_trust(_lose('var:spec_centre_trust multiply = spec_exch_panic_cut', chr(9) * 2), 'panics', chr(9) * 2, 'panic_start')}\t}}\n") if ON else ""
PANIC_OVER = ("\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_centre_trust\n\t\t\tNOT = { has_variable = spec_rescued }\n"
              "\t\t\tvar:spec_panic <= 0\n\t\t}\n"
              f"{_record_trust(_lose(HALF, chr(9) * 2), 'panics', chr(9) * 2, 'panic_over')}" + ("\t\tset_variable = { name = spec_exch_sound value = 0 }\n" if EARN else "")
              + "\t}\n") if ON else ""
# a quiet month under sound Lending Standards counts towards Deposit Banks
SOUND = lambda t: f"{t}set_variable = {{ name = spec_exch_sound value = {{ value = spec_log_ksnd add = 1 }} }}\n" if EARN else ""


def _issue_score():
    """In spec_centre_size: a Great Issue running (levers.py). ponytail: inline, no spec_issue_score value."""
    return (f"\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_issue\n\t\t\thas_variable = spec_issue_w\n\t\t}}\n"
            f"\t\tmultiply = {{\n\t\t\tvalue = var:spec_issue_w\n\t\t\tmultiply = {levers.ISSUE_SCORE - 1:g}\n\t\t\tadd = 1\n\t\t}}\n\t}}\n"
            if levers.ISSUE_ON else "")


def _parts_values():
    """The score's parts as script values (Exchange on), read in the monthly pulse and kept for the calculator."""
    techs = "".join(f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n\t\tadd = {b:g}\n\t}}\n" for t, b in TECHS.items())
    ntech = "".join(f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n\t\tadd = 1\n\t}}\n" for t in TECHS)
    econ = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ has_law_or_variant = law_type:law_{k} }}\n"
                   f"\t\tvalue = {m:g}\n\t}}\n" for i, (k, m) in enumerate(ECON.items()))
    rank = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ country_rank >= rank_value:{k} }}\n"
                   f"\t\tvalue = {m:g}\n\t}}\n" for i, (k, m) in enumerate(RANK.items()))
    unit = f"\tmultiply = {MONTHS:g}\n\tdivide = {CAP_PER:g}\n"
    # (in the pulse: scope:spec_xs_me is the market, global spec_xs_me_inc its income) a tie: our market, our subject, our power bloc, or investment rights granted us; only smaller countries count,
    # so a hub draws on its hinterland and not the reverse
    tie = ("\t\t\t\tOR = {\n\t\t\t\t\tmarket ?= scope:spec_xs_me.market\n\t\t\t\t\tis_subject_of = scope:spec_xs_me\n"
           "\t\t\t\t\tAND = {\n\t\t\t\t\t\tis_in_power_bloc = yes\n\t\t\t\t\t\tpower_bloc ?= scope:spec_xs_me.power_bloc\n\t\t\t\t\t}\n"
           # granted us investment rights: listed by _xs_prep from our own treaties, not a treaty scan in every country
           f"\t\t\t\t\tis_in_list = {FIR_LIST}\n\t\t\t\t}}\n")
    return (f"spec_xs_own = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_xs_inc }}\n\t\tvalue = var:spec_xs_inc\n\t}}\n{unit}}}\n"
            f"spec_xs_reach = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_xs_inc }}\n\t\tevery_country = {{\n"
            f"\t\t\tlimit = {{\n\t\t\t\thas_variable = spec_xs_inc\n\t\t\t\tvar:spec_xs_inc < global_var:spec_xs_me_inc\n{tie}\t\t\t}}\n"
            f"\t\t\tadd = var:spec_xs_inc\n\t\t}}\n{power_bloc.REACH_REF}\t}}\n\tmultiply = {REACH:g}\n{unit}\tmax = spec_xs_own\n}}\n"
            # pool income per person (in millions) against the world's
            "spec_xs_ratio = {\n\tvalue = 0\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_xs_inc\n\t\t\ttotal_population > 0\n"
            "\t\t\thas_global_variable = spec_xs_world_pc\n\t\t\tglobal_var:spec_xs_world_pc > 0\n\t\t}\n\t\tvalue = var:spec_xs_inc\n"
            "\t\tdivide = {\n\t\t\tvalue = total_population\n\t\t\tdivide = 1000000\n\t\t\tmin = 0.001\n\t\t}\n"
            "\t\tdivide = global_var:spec_xs_world_pc\n\t}\n}\n"
            f"spec_xs_fd = {{\n{vanilla_ties.levels('building_financial_district')}}}\n"
            "spec_xs_co = {\n\tvalue = 0\n\tevery_company = {\n\t\tadd = 1\n\t}\n}\n"
            f"spec_xs_fdm = {{\n\tvalue = spec_xs_fd\n\tmax = {FD_CAP:g}\n\tmultiply = {FD_STEP:g}\n\tadd = 1\n}}\n"
            f"spec_xs_com = {{\n\tvalue = spec_xs_co\n\tmax = {CO_CAP:g}\n\tmultiply = {CO_STEP:g}\n\tadd = 1\n}}\n"
            f"spec_xs_tech = {{\n\tvalue = 1\n{techs}}}\n"
            f"spec_xs_ntech = {{\n\tvalue = 0\n{ntech}}}\n"
            f"spec_xs_rank = {{\n\tvalue = 1\n{rank}}}\n"
            f"spec_xs_econ = {{\n\tvalue = 1\n{econ}}}\n"
            "spec_xs_issue = {\n\tvalue = 1\n" + _issue_score() + "}\n")


XS_KEEP = ["fd", "co", "fdm", "com", "tech", "ntech", "rank", "econ"]


def _parts_keep(t):
    """In the monthly pulse: the parts as variables, for the calculator, and the score in points."""
    return (f"{t}set_variable = {{ name = spec_xs_raw value = var:spec_centre_score }}\n"
            + "".join(f"{t}set_variable = {{ name = spec_xs_{k}_v value = spec_xs_{k} }}\n" for k in XS_KEEP)
            + f"{t}set_variable = {{ name = spec_xs_trust_v value = spec_centre_calm_mult }}\n")


def _sqrt(src, dst, t):
    """dst = the square root of src (lines of a value, at least 0), by SQ_STEPS of Newton's method (_newton)."""
    inner = t + "\t"
    step = (f"{inner}set_local_variable = {{ name = spec_sq value = {{ value = local_var:spec_sq_x divide = local_var:spec_sq "
            f"add = local_var:spec_sq multiply = 0.5 }} }}\n")
    return (f"{t}set_local_variable = {{ name = spec_sq_x value = {{ value = {src} min = 0 }} }}\n"
            f"{t}if = {{\n{inner}limit = {{ local_var:spec_sq_x > 0 }}\n"
            f"{inner}set_local_variable = {{ name = spec_sq value = {{ value = local_var:spec_sq_x divide = 40 add = 2 }} }}\n"
            + step * SQ_STEPS + f"{inner}set_variable = {{ name = {dst} value = local_var:spec_sq }}\n{t}}}\n"
            f"{t}else = {{ set_variable = {{ name = {dst} value = 0 }} }}\n")


def _xs_world(t="\t"):
    """First in the ranking pass: each market's pool income averaged (spec_xs_inc), and the world's per person."""
    return (f"{t}# the Exchange score's yearly average and the world's pool income per person (centres.py)\n"
            f"{t}set_global_variable = {{ name = spec_xs_world_inc value = 0 }}\n"
            f"{t}set_global_variable = {{ name = spec_xs_world_pop value = 0 }}\n"
            f"{t}every_country = {{\n{t}\tlimit = {{ has_variable = spec_conf }}\n"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ NOT = {{ has_variable = spec_xs_inc }} }}\n"
            f"{t}\t\tset_variable = {{ name = spec_xs_inc value = spec_pool_month }}\n{t}\t}}\n"
            f"{t}\telse = {{\n{t}\t\tset_variable = {{ name = spec_xs_inc value = {{ value = spec_pool_month subtract = var:spec_xs_inc "
            f"multiply = {SMOOTH:g} add = var:spec_xs_inc }} }}\n{t}\t}}\n"
            f"{t}\tchange_global_variable = {{ name = spec_xs_world_inc add = var:spec_xs_inc }}\n"
            f"{t}\tchange_global_variable = {{ name = spec_xs_world_pop add = {{ value = total_population divide = 1000000 }} }}\n{t}}}\n"
            f"{t}set_global_variable = {{ name = spec_xs_world_pc value = {{ value = global_var:spec_xs_world_inc "
            f"divide = {{ value = global_var:spec_xs_world_pop min = 1 }} }} }}\n")


FIR_LIST = "spec_xs_fir"


def _xs_prep(t):
    """In the monthly pulse, before the score: Size and wealth per head (square roots), and the market's region."""
    reg = "".join(f"{t}{'if' if i == 0 else 'else_if'} = {{\n{t}\tlimit = {{\n{t}\t\tcapital ?= {{\n{t}\t\t\tOR = {{\n"
                  + "".join(f"{t}\t\t\t\tis_in_geographic_region = geographic_region_{g}\n" for g in gs)
                  + f"{t}\t\t\t}}\n{t}\t\t}}\n{t}\t}}\n{t}\tset_variable = {{ name = spec_xs_reg value = {i + 1} }}\n{t}}}\n"
                  for i, (gs, _) in enumerate(REGIONS[:-1]))
    reg += f"{t}else = {{\n{t}\tset_variable = {{ name = spec_xs_reg value = {len(REGIONS)} }}\n{t}}}\n"
    return (f"{t}save_temporary_scope_as = spec_xs_me\n"
            f"{t}set_global_variable = {{ name = spec_xs_me_inc value = var:spec_xs_inc }}\n"
            f"{t}set_variable = {{ name = spec_xs_own_v value = spec_xs_own }}\n"
            # the countries whose treaty with us grants us foreign investment rights (a directed article: they are its
            # source); the list lives for the whole ranking, so it is emptied again for the next country
            + f"{t}every_scope_treaty = {{\n{t}\tevery_scope_article = {{\n{t}\t\tlimit = {{\n"
            f"{t}\t\t\thas_type = foreign_investment_rights\n{t}\t\t\ttarget_country = scope:spec_xs_me\n{t}\t\t}}\n"
            f"{t}\t\tsource_country ?= {{\n{t}\t\t\tadd_to_temporary_list = {FIR_LIST}\n{t}\t\t}}\n{t}\t}}\n{t}}}\n"
            f"{t}set_variable = {{ name = spec_xs_reach_v value = spec_xs_reach }}\n"
            f"{t}every_in_list = {{\n{t}\tlist = {FIR_LIST}\n{t}\tremove_from_list = {FIR_LIST}\n{t}}}\n"
            + _sqrt("var:spec_xs_own_v add = var:spec_xs_reach_v", "spec_xs_size_v", t)
            + (_sqrt("var:spec_xs_size_v", "spec_xs_size_v", t) if SIZE_ROOT == 4 else "")
            + f"{t}set_variable = {{ name = spec_xs_size_v value = {{ value = var:spec_xs_size_v multiply = {SIZE_X:g} }} }}\n"
            f"{t}set_variable = {{ name = spec_xs_ratio_v value = spec_xs_ratio }}\n"
            + _sqrt("var:spec_xs_ratio_v", "spec_xs_wealth_v", t)
            + f"{t}set_variable = {{ name = spec_xs_wealth_v value = {{ value = var:spec_xs_wealth_v min = {WEALTH[0]:g} max = {WEALTH[1]:g} }} }}\n"
            + reg)


def _regions(t="\t"):
    """After the scores are scaled: each region's leading Exchange (spec_xs_regtop, global spec_xs_rlead_<n> and its
    score spec_xs_rbest_<n>), and every market's score as a share of its region's leader's (spec_xs_regshare)."""
    out = (f"{t}# each region's leading Exchange, and every market's share of it (centres.py)\n"
           f"{t}every_country = {{\n{t}\tlimit = {{ has_variable = spec_xs_regtop }}\n{t}\tremove_variable = spec_xs_regtop\n{t}}}\n")
    for i in range(1, len(REGIONS) + 1):
        out += (f"{t}if = {{\n{t}\tlimit = {{ has_global_variable = spec_xs_rlead_{i} }}\n{t}\tremove_global_variable = spec_xs_rlead_{i}\n{t}}}\n"
                f"{t}set_global_variable = {{ name = spec_xs_rbest_{i} value = 0 }}\n"
                f"{t}ordered_country = {{\n{t}\tlimit = {{\n{t}\t\thas_variable = spec_centre_score\n{t}\t\tvar:spec_xs_reg = {i}\n{t}\t}}\n"
                f"{t}\torder_by = spec_centre_order\n{t}\tposition = 0\n{t}\tcheck_range_bounds = no\n{t}\tset_variable = spec_xs_regtop\n"
                f"{t}\tset_global_variable = {{ name = spec_xs_rbest_{i} value = var:spec_xs_raw }}\n"
                f"{t}\tset_global_variable = {{ name = spec_xs_rlead_{i} value = this }}\n{t}}}\n")
    share = "".join(f"{t}\t{'if' if i == 1 else 'else_if'} = {{\n{t}\t\tlimit = {{\n{t}\t\t\tvar:spec_xs_reg = {i}\n"
                    f"{t}\t\t\tglobal_var:spec_xs_rbest_{i} > 0\n{t}\t\t}}\n"
                    f"{t}\t\tset_variable = {{ name = spec_xs_regshare value = {{ value = var:spec_xs_raw multiply = 100 "
                    f"divide = global_var:spec_xs_rbest_{i} }} }}\n{t}\t}}\n" for i in range(1, len(REGIONS) + 1))
    return out + (f"{t}every_country = {{\n{t}\tlimit = {{ has_variable = spec_centre_score }}\n"
                  f"{t}\tset_variable = {{ name = spec_xs_regshare value = 0 }}\n{share}{t}}}\n")


def values():
    return ("spec_log_issue = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_issue }\n\t\tvalue = 1\n\t}\n}\n\n"
            if levers.ISSUE_ON else "") + f"""# the Financial Centres (centres.py)
spec_centre_calm_mult = {{
	value = 0
	if = {{
		limit = {{ has_variable = {CALM_VAR} }}
		add = var:{CALM_VAR}
	}}
	max = {CALM}
	divide = {CALM}
	add = 0.5
}}

{_parts_values() if ON else ""}
spec_centre_size = {{
{"""	value = var:spec_xs_size_v
	multiply = var:spec_xs_wealth_v
	multiply = spec_xs_fdm
	multiply = spec_xs_com
	multiply = spec_xs_tech
	multiply = spec_xs_rank
	multiply = spec_xs_econ
""" if ON else f"""	value = {INCOME}
	multiply = {MONTHS:g}
{"" if BRAKE else '''	if = {
		limit = { has_variable = spec_debt }
		add = var:spec_debt
	}
'''}	min = 0
"""}	multiply = spec_centre_calm_mult
{_issue_score()}}}

spec_centre_order = {{
	value = 0
	if = {{
		limit = {{ has_variable = spec_centre_score }}
		add = var:spec_centre_score
	}}
}}

# the modifier's size: {PLACES} steps for the first place, 1 for the last
spec_centre_mult = {{
	value = {PLACES + 1}
	subtract = var:spec_centre_new
}}
""" + _nx_values() + (_exch_values() if ON else "")


def _by_stand(name, by, tail="", var="spec_exch_stand"):
    steps = "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ var:{var} ?= {s} }}\n\t\tvalue = {x:g}\n\t}}\n"
                    for i, (s, x) in enumerate(sorted(by.items())))
    return f"{name} = {{\n\tvalue = 1\n{steps}{tail}}}\n"


def _limit_values():
    """A listed place adds credit-limit months with Central Banking, while Lending Standards are Sound or stricter. The
    limit stops at leverage.RUIN all the same: the place only reaches it sooner."""
    return f"""
# the Exchange's place adds to the credit limit (centres.py)
spec_exch_limit = {{
	value = 0
	if = {{
		limit = {{
			has_variable = spec_centre_rank
			{GATE}
			OR = {{
				NOT = {{ has_variable = spec_lax }}
				var:spec_lax < {cycle.LAX_CUTS[2]:g}
			}}
		}}
		value = {PLACES + 1}
		subtract = var:spec_centre_rank
		multiply = {LIMIT_STEP:g}
	}}
}}
"""


def _known(n, how):
    return f"\tif = {{\n\t\tlimit = {{ var:spec_exch_known ?= {n} }}\n\t\t{how}\n\t}}\n"


def _nx_values():
    """The renown paths' levers in the rest of the mod: each a multiplier, 1 with no speciality pulling it."""
    return "\n# renown paths' levers (centres.NAME_FX)\n" + "".join(
        f"spec_nx_{h} = {{\n\tvalue = 1\n{_name_tail(h)}}}\n" for h in NX_HOOKS)


def _exch_values():
    return ("\n# the Exchange (centres.py): its Standing and what it is known for\n"
            + _by_stand("spec_exch_hype", HYPE, _known(1, f"multiply = {KNOWN_HYPE:g}") + _name_tail("hype"))
            + "\n" + _by_stand("spec_exch_flight", FLIGHT, (_if_pledged(f"multiply = {PLEDGE_FLIGHT:g}") if PLEDGE_ON else "") + _name_tail("flight"))
            + "\n" + _by_stand("spec_exch_loss", {}, _known(2, f"value = {KNOWN_LOSS:g}") + _name_tail("loss") + monetary.tail("loss"))
            + "\n" + _by_stand("spec_exch_credit", {}, _known(3, f"value = {KNOWN_CREDIT:g}") + _name_tail("credit"))
            + (_limit_values() if BRAKE else "") + _panic_cut() + (_pledge_values() if PLEDGE_ON else "")
            + (_earn_values() if EARN or LEAN else "") + (_links_values() if LINKS else "")
            + (_name_values() if NAMES_ON else "")
            + "\n# the state with the most Financial District levels names the Exchange (centres._seat)\n"
            "spec_seat_fd = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_building = building_financial_district }\n"
            "\t\tvalue = b:building_financial_district.level\n\t}\n}\n")


def _links_values():
    """Phase 5: trust scales Market Mood's swings and confidence's recovery; prosperous companies lean the mood."""
    trust = lambda name, *ops: (f"{name} = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{ has_variable = spec_centre_trust }}\n"
                                f"\t\tvalue = var:spec_centre_trust\n\t\tdivide = {CALM}\n" + "".join(f"\t\t{o}\n" for o in ops) + "\t}\n}\n")
    # ponytail: the lean only for an Exchange of National Standing or better, and only upward: a -0.3 floor held mood
    # near -0.8 for an Exchange without prosperous companies (player report, 2026-11-16); LINK_PROSPER is the knob
    return ("\n# the Exchange's links (centres.py)\n"
            + trust("spec_exch_mood", "subtract = 0.5", f"multiply = {-LINK_MOOD:g}", "add = 1")
            + trust("spec_exch_recover", "multiply = 0.75", "subtract = 0.25", f"multiply = {LINK_RECOVER:g}", "add = 1")
            + ("" if not LEAN else
            "spec_exch_lean = {\n\tvalue = 0\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_exch_stand\n\t\t\tvar:spec_exch_stand >= 1\n\t\t}\n"
            f"\t\tvalue = spec_earn_co\n\t\tsubtract = 1\n\t\tmultiply = {LINK_PROSPER:g}\n\t\tmin = 0\n\t\tmax = 0.3\n\t}}\n}}\n"))


def links(trust, tally):
    """Python model of _links_values for the self-check: (mood scale, recovery scale, lean) for a National Exchange."""
    t = trust / CALM
    return 1 - LINK_MOOD * (t - 0.5), 1 + LINK_RECOVER * (t * 0.75 - 0.25), max(0, min(0.3, (tally - 1) * LINK_PROSPER))


def _earn_values():
    """The three counts (logged, and shown in the Exchange tooltip) and each one's tally: count / its mark."""
    return ("\n# what the Exchange is known for, earned by building (centres.py)\n"
            f"spec_log_ktc = {{\n{vanilla_ties.levels('building_trade_center')}}}\n"
            f"spec_log_kco = {{\n\tvalue = 0\n\tevery_company = {{\n\t\tlimit = {{ prosperity >= {EARN_PROSPER:g} }}\n\t\tadd = 1\n\t}}\n}}\n"
            # Company Strength (design_companies.md): every point of prosperity counts, so the honour rarely ties;
            # read in company scope, the only place the engine accepts it (probe: runs/sweep_prosperity_probe_r1)
            f"spec_log_kstr = {{\n\tvalue = 0\n\tevery_company = {{\n\t\tadd = prosperity\n\t}}\n\tdivide = {CO_STRENGTH:g}\n"
            f"\tadd = {{\n\t\tvalue = spec_log_kbc\n\t\tmultiply = {companies.BLUE_BONUS:g}\n\t}}\n}}\n"
            "spec_log_kbc = {\n\tvalue = 0\n\tevery_company = {\n\t\tlimit = { has_variable = spec_blue_chip }\n\t\tadd = 1\n\t}\n}\n"
            # nothing sets spec_exch_sound unless EARN is on (LINKS alone also writes these values)
            + ("spec_log_ksnd = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_exch_sound }\n\t\tvalue = var:spec_exch_sound\n\t}\n}\n"
               if EARN else "spec_log_ksnd = { value = 0 }\n")
            + "".join(f"{EARN_BY[n]} = {{\n\tvalue = spec_log_{k}\n\tdivide = {mark:g}\n}}\n"
                      for n, k, mark in ((1, "ktc", EARN_TC), (2, "ksnd", EARN_SOUND), (3, "kco", EARN_CO))))


# The charter and the names (plan step 5/6): the state grants the Exchange a charter (var:spec_exch_known, the AI's is
# still earned by _earn); once a year the world's three leaders in each field may take its name (spec_has_<key>), as
# many as the Standing allows. Every name moves two of the four hooks, one for the better and one for the worse.
NAMES_ON = EARN and tuning.get("EXCH_NAMES_ON", 1)
CHARTER_COST = tuning.get("EXCH_CHARTER_COST", 0.25)  # share of trust a change of charter costs (the first is free; 2026-11-22: 0.5 -> 0.25)
CHARTER_LOCK = tuning.get("EXCH_CHARTER_LOCK", 10)    # years before the charter can change again
# key, title, the charter it needs (0: any); the hand-out prefers them in this order
NAMES = [("price", "Price Setter", 1), ("harbour", "Safe Harbor", 2), ("companies", "Home of Great Companies", 3),
         ("futures", "Futures Pit", 1), ("lender", "Lender to Nations", 2), ("railway", "Railway Mania", 3),
         ("floor", "Busy Floor", 0), ("sound", "Sound Lending", 0), ("pockets", "Deep Pockets", 0), ("door", "Open Door", 0)]
# each path's flavour, the last line of its tooltip in vanilla's #lore style: one sentence, of the period
FLAVOR = {
    "price": "When our brokers call a price, merchants half a world away write it down.",
    "harbour": "In every storm, frightened money sails for our vaults and drops anchor.",
    "companies": "The great firms of the age list their shares here, and their names are known in every counting-house.",
    "futures": "Men shout over next year's harvest in the pit, so the farmer can sleep this year.",
    "lender": "Kings and republics alike come to our bankers, hat in hand.",
    "railway": "Every clerk holds shares in a line from nowhere to nowhere, and every clerk expects to grow rich.",
    "floor": "From the opening bell the floor roars with clerks, runners and the chatter of the telegraph.",
    "sound": "Our bankers lend slowly, ask a great many questions, and sleep soundly.",
    "pockets": "There is always another purse in this city willing to back a bold venture.",
    "door": "Foreign money comes and goes as it pleases, and nobody asks for its papers."}
NAME_FX = tuning.get("EXCH_NAME_FX", {  # beta.12: each path a trade-off: at least one cost against its gains
    "price": {"press": 1.35, "hype": 1.15, "loss": 1.2},          # feared and watched; a slip costs it dearly
    "futures": {"crash": 0.75, "hype": 0.9, "credit": 0.85},      # hedged: softer busts, slower booms, less lent
    "harbour": {"panic": 0.75, "shore": 1.4, "credit": 0.85},    # safe, and its banks cautious
    "lender": {"lure": 1.35, "tie_inv": 1.3, "bad": 1.2},         # rich, tied to its debtors, hurt by their defaults
    "companies": {"blue": 1.4, "crash": 1.1},                    # great firms, and their fall
    "railway": {"burst": 1.3, "crash": 1.2, "raid": 1.35},        # a mania
    "floor": {"tie_trade": 1.25, "flight": 1.15, "loss": 1.15},  # busy and exposed
    "sound": {"bad": 0.75, "loss": 0.75, "ceiling": 0.85},       # careful, and lends less
    "pockets": {"ceiling": 1.2, "bad": 1.2},                     # big and risky
    "door": {"flight": 1.25, "tie_trade": 1.2, "crash": 1.1}})   # open to the world, and its storms
# the hooks that reach outside the Exchange: spec_nx_<hook>, 1 unless a speciality changes it (_nx_values)
NX_HOOKS = ("press", "raid", "lure", "shore", "crash", "panic", "rescue", "tie_inv", "tie_trade", "blue", "burst",
            "bad", "ceiling")
# what each name is won by: script value lines for spec_name_<key>
NAME_BY = {
    # the market's trade times our share of its members' GDP (player report 2026-11-20: every member counted the whole
    # market's, so three of Britain's market members tied with it and took the top three places by list order)
    "price": ("\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_mv_total }\n\t\tvalue = var:spec_mv_total\n"
              "\t\tmultiply = {\n\t\t\tvalue = gdp\n\t\t\tdivide = {\n\t\t\t\tvalue = 0\n\t\t\t\tmarket ?= {\n"
              "\t\t\t\t\tevery_scope_country = {\n\t\t\t\t\t\tadd = gdp\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tmin = 1\n\t\t\t}\n"
              "\t\t\tmax = 1\n\t\t}\n\t}\n"),
    # ponytail: quiet months break a tie at full trust; they add at most ~0.1 a century
    "harbour": "\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_centre_trust }\n\t\tvalue = var:spec_centre_trust\n\t}\n"
               "\tif = {\n\t\tlimit = { has_variable = spec_centre_calm }\n\t\tadd = { value = var:spec_centre_calm divide = 10000 }\n\t}\n",
    "companies": "\tvalue = spec_log_kstr\n", "floor": "\tvalue = spec_log_ktc\n", "sound": "\tvalue = spec_log_ksnd\n",
    "pockets": "\tvalue = spec_pool_month\n",
    "door": "\tvalue = 0\n\tevery_scope_treaty = {\n\t\tadd = 1\n\t}\n",
    # beta.12 paths, one more per charter
    "futures": "\tvalue = 0\n\tevery_scope_state = {\n\t\tadd = 1\n\t}\n",
    # countries granting us foreign investment rights (as _xs_prep's list)
    "lender": ("\tvalue = 0\n\tsave_temporary_scope_as = spec_lender_me\n\tevery_scope_treaty = {\n\t\tevery_scope_article = {\n"
               "\t\t\tlimit = {\n\t\t\t\thas_type = foreign_investment_rights\n\t\t\t\ttarget_country = scope:spec_lender_me\n"
               "\t\t\t}\n\t\t\tadd = 1\n\t\t}\n\t}\n"
               # and subjects that granted us investment rights (a pact, not a treaty: vanilla 06_cuba.txt:196), the
               # commonest way a great power invests abroad
               "\tevery_direct_subject = {\n\t\tlimit = {\n\t\t\thas_diplomatic_pact = {\n"
               "\t\t\t\ttype = da_overlord_grant_investment_rights\n\t\t\t\twho = scope:spec_lender_me\n\t\t\t}\n\t\t}\n"
               "\t\tadd = 1\n\t}\n"),
    "railway": f"{vanilla_ties.levels('building_railway')}\tadd = {{\n{vanilla_ties.levels('building_port')}\t}}\n"}
SLOTS = "var:spec_exch_stand"  # names an Exchange may hold: National 1, International 2, World Centre 3
# the state may pursue names (var:spec_pu_<key>, its place in the order chosen), one more than its Exchange's Standing;
# each is held PURSUE_LOCK years once chosen, and builds up over PURSUE_MONTHS
# (var:spec_pw_<key>, 0 to 1) and ends at once when stopped (2026-11-19: faded as slowly). At full strength every other tally counts PURSUE_COST
# for each such pursuit. (2026-11-19: its own tally counted 1.25 too, removed with ranking only pursuers: among them it cancelled)
PURSUE_COST = tuning.get("EXCH_PURSUE_COST", 0.9)
TIE_EDGE = 0.001  # spec_rank_<key>: per place held, far under any real difference in a tally, so it only breaks ties (3 decimals: the engine's limit)
AI_CROWD = 0.25  # the AI's choice of speciality: its measure / (1 + this x Exchanges already pursuing the path), so they spread
AI_SWITCH = 2  # yearly, an AI with every slot full swaps its weakest unlocked speciality for a path measuring this many times better
CAN_RANK = "has_variable = spec_exch_stand var:spec_exch_stand >= 1"  # Exchanges that can be ranked on a path
PURSUE_MONTHS = tuning.get("EXCH_PURSUE_MONTHS", 12)
PURSUE_LOCK = tuning.get("EXCH_PURSUE_LOCK", 5)  # years a pursuit is held once chosen
PURSUE_BASE = 1  # specialities at Provincial Standing, one more per Standing above (spec_pursue_slots)
PURSUE_TOP = PURSUE_BASE + 3  # as a World Centre
# what a pursuit gives, by our place in its field at the yearly contest (outside the top three, third, second, first):
# the first modifier once for each step, the second at first place only; scaled by how far the pursuit has built up
PURSUE_FX = tuning.get("EXCH_PURSUE_FX", {
    # [grows with our place, first place only, *costs]. beta.12: each path themed to what it is won by; every path
    # carries a cost, and its costs grow with the place too (COST_SCALE), so leading a path stirs more resentment
    "floor": [["state_trade_capacity_mult", 0.03], ["building_trade_center_throughput_add", 0.1],
              ["interest_group_ig_landowners_approval_add", -1]],  # merchants over the land
    # careful banks win small savers' deposits (was -1% loan interest a step until 1.2: see LOAN_NOTE at WORLD_FX)
    "sound": [["state_shopkeepers_investment_pool_efficiency_mult", 0.02], ["interest_group_ig_petty_bourgeoisie_approval_add", 2],
              ["interest_group_ig_industrialists_approval_add", -1]],  # tight credit for new works
    # 0.05 (first place +0.20 on vanilla's 0.30) gave the top three Exchanges +33-43% investment pool / GDP over vanilla,
    # Britain +58-64%; without it +0-14%, and leverage or credit off changed nothing (runs/20261115_*_pool_*, 1.0.6).
    # At 0.02 (four games): top three +20% / +35% (1840s / 1850s), Britain +29% / +50%; the user chose first place +0.06
    "pockets": [["state_capitalists_investment_pool_contribution_add", 0.015], ["country_private_construction_allocation_mult", 0.1],
                ["state_tax_collection_mult", -0.02]],  # fortunes sheltered from the tax man
    "door": [["country_influence_mult", 0.02], ["country_mass_migration_attraction_mult", 0.15],
             ["country_leverage_resistance_mult", -0.04]],  # foreign money, foreign sway
    "price": [["state_trade_advantage_mult", 0.03], ["state_export_advantage_mult", 0.1],
              ["interest_group_ig_trade_unions_approval_add", -1]],  # dear bread
    "futures": [["building_group_bg_agriculture_throughput_add", 0.02], ["state_market_access_price_impact", 0.1],
                ["interest_group_ig_rural_folk_approval_add", -1]],  # speculators on the harvest
    "harbour": [["country_gold_reserve_limit_mult", 0.05], ["country_legitimacy_base_add", 3],
                ["country_private_construction_allocation_mult", -0.04]],  # safe money sits idle
    # first place was -5% loan interest until 1.2: a creditor nation is hard to pressure instead
    "lender": [["country_leverage_generation_mult", 0.05], ["country_leverage_resistance_mult", 0.1],
               ["state_capitalists_investment_pool_efficiency_mult", -0.02]],  # capital that could build at home
    "companies": [["country_company_throughput_bonus_add", 0.02], ["country_max_companies_add", 1],
                  ["interest_group_ig_petty_bourgeoisie_approval_add", -1]],  # small shops crushed
    "railway": [["building_railway_throughput_add", 0.03], ["state_infrastructure_mult", 0.1],
                ["building_group_bg_construction_laborers_mortality_mult", 0.04]]})  # the navvies' toll


def _pursue_given(k):
    """Log builds: the first modifier a name gives this month, as applied (its step for our place, times its build-up)."""
    a = PURSUE_FX[k][0][1]
    place = "".join(f"\t\t{'if' if r == 1 else 'else_if'} = {{\n\t\t\tlimit = {{ var:spec_lead_{k} ?= {r} }}\n"
                    f"\t\t\tmultiply = {5 - r}\n\t\t}}\n" for r in (1, 2, 3))
    return (f"spec_log_pf_{k} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_pw_{k} }}\n"
            f"\t\tvalue = var:spec_pw_{k}\n{place}\t\tmultiply = {a:g}\n\t}}\n}}")


LOG_GIVEN = [_pursue_given(k) for k in ("pockets", "companies")] if ON and NAMES_ON else []
LOG += (" pfpk=[THIS.ScriptValue('spec_log_pf_pockets')] pfco=[THIS.ScriptValue('spec_log_pf_companies')]"
        if LOG_GIVEN else "") + (" levpct=[THIS.ScriptValue('spec_lev_boom_pct')]" if ON and leverage.ON else "")
PLACE_WORDS = ["Outside the top three", "Third", "Second", "First"]
PLACE_SHORT = ["Unranked", "3rd", "2nd", "1st"]  # the tooltips' place lists
# trust's own effects at each level (Distrusted, Doubted, Respected, Trusted: a quarter of CALM each)
# 2026-11-22: stronger effects tried and put back (the user: not for 1.2, revisit in 1.3)
TRUST_FX = tuning.get("CENTRE_TRUST_FX", [
    [["country_loan_interest_rate_mult", 0.1]],
    [["country_loan_interest_rate_mult", 0.05]], [],
    [["interest_group_ig_industrialists_approval_add", 2]]])  # Trusted was also -5% loan interest until 1.2
ICON = lambda k: icons.path(f"name_{k}")  # icons.py: our painting, else its vanilla stand-in
ROUND = "gfx/interface/backgrounds/round_button_bg.dds"  # vanilla's gold-rimmed disc (company_panel's charter badges): order numbers


def _name_tail(hook):
    """A speciality's two hooks, the good and the bad alike, follow its strength (spec_pw_<key>): they build up over
    PURSUE_MONTHS once chosen and end at once when dropped, as its modifiers do."""
    if not NAMES_ON:
        return ""
    return "".join(f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pw_{k} var:spec_pw_{k} > 0 }}\n"
                   f"\t\tmultiply = {{ value = var:spec_pw_{k} multiply = {round(NAME_FX[k][hook] - 1, 4):g} add = 1 }}\n\t}}\n"
                   for k, *_ in NAMES if hook in NAME_FX[k])


def _name_values():
    def tail(k):
        # A save can already have the total before its first tick initializes a new path.
        return (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pw_sum }}\n"
                f"\t\tmultiply = {{\n\t\t\tvalue = var:spec_pw_sum\n"
                f"\t\t\tif = {{ limit = {{ has_variable = spec_pw_{k} }} subtract = var:spec_pw_{k} }}\n"
                f"\t\t\tmultiply = {PURSUE_COST - 1:g}\n\t\t\tadd = 1\n\t\t}}\n\t}}\n")
    # the order the places go by (2026-11-19): the tally, and on a tie the one holding the higher place keeps it, so
    # passing takes more, not as much. Its place last month while the ranking runs (spec_ldw), its place otherwise.
    rank = lambda k: (f"spec_rank_{k} = {{\n\tvalue = spec_name_{k}\n"
                      + "".join(f"\t{c} = {{\n\t\tlimit = {{ has_variable = {var} }}\n"
                                f"\t\tadd = {{ value = 4 subtract = var:{var} multiply = {TIE_EDGE:g} }}\n\t}}\n"
                                for c, var in (("if", f"spec_ldw_{k}"), ("else_if", f"spec_lead_{k}")))
                      + "}\n")
    return "\n# what each name is won by (centres.py)\n" + "".join(
        f"spec_name_{k} = {{\n{NAME_BY[k]}{tail(k)}}}\n{rank(k)}" for k, *_ in NAMES) + _pursue_values()


def _names_drop(t):
    """Take this country's places in the fields (its chosen specialities stay)."""
    if not NAMES_ON:
        return ""
    return "".join(f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_lead_{k} }}\n{t}\tremove_variable = spec_lead_{k}\n{t}}}\n"
                   for k, *_ in NAMES)


def _names(t="\t"):
    """In the ranking pass, monthly (2026-11-19: once a year, so a new speciality waited up to a year for its place):
    the three leaders of each field among the Exchanges pursuing it get var:spec_lead_<key> 1..3, which sets what it
    gives, and are the flags (spec_w_<key><place>). Once a year before that the AI rebalances charters and chooses its
    specialities, so its new ones are ranked at once. ponytail: ties fall as ordered_country lists them."""
    if not NAMES_ON:
        return ""
    T = lambda n: t + "\t" * n
    lead = ""
    for k, _, ch in NAMES:
        # last month's places kept aside (spec_ldw) while the new ones are found: a tie keeps the holder (spec_rank)
        lead += (f"{T(0)}every_country = {{\n{T(1)}limit = {{ has_variable = spec_lead_{k} }}\n"
                 f"{T(1)}set_variable = {{ name = spec_ldw_{k} value = var:spec_lead_{k} }}\n"
                 f"{T(1)}remove_variable = spec_lead_{k}\n{T(0)}}}\n"
                 + "".join(f"{T(0)}if = {{\n{T(1)}limit = {{ has_global_variable = spec_w_{k}{p} }}\n"
                           f"{T(1)}remove_global_variable = spec_w_{k}{p}\n{T(0)}}}\n" for p in (1, 2, 3)))
        slots = "".join(f"{T(1)}if = {{\n{T(2)}limit = {{ global_var:spec_name_next = {pos} }}\n"
                        f"{T(2)}set_global_variable = {{ name = spec_w_{k}{pos} value = this }}\n{T(1)}}}\n" for pos in (1, 2, 3))
        lead += (f"{T(0)}set_global_variable = {{ name = spec_name_next value = 1 }}\n"
                 f"{T(0)}ordered_country = {{\n{T(1)}limit = {{\n{_eligible(k, ch, T(2))}{T(1)}}}\n"
                 f"{T(1)}order_by = spec_rank_{k}\n{T(1)}max = 3\n{T(1)}check_range_bounds = no\n"
                 f"{T(1)}set_variable = {{ name = spec_lead_{k} value = global_var:spec_name_next }}\n"
                 f"{slots}{T(1)}change_global_variable = {{ name = spec_name_next add = 1 }}\n{T(0)}}}\n"
                 f"{T(0)}remove_global_variable = spec_name_next\n"
                 f"{T(0)}every_country = {{\n{T(1)}limit = {{ has_variable = spec_ldw_{k} }}\n"
                 f"{T(1)}remove_variable = spec_ldw_{k}\n{T(0)}}}\n")
    return (f"{t}# once a year (centres.py): the AI's charters and specialities\n"
            f"{t}if = {{\n{T(1)}limit = {{\n{T(2)}NOT = {{ has_global_variable = spec_names_year }}\n"
            f"{T(2)}any_country = {{\n{T(3)}has_variable = spec_exch_stand\n{T(3)}var:spec_exch_stand >= 1\n{T(2)}}}\n{T(1)}}}\n"
            f"{T(1)}set_global_variable = {{ name = spec_names_year days = 365 }}\n{_charter_balance(T(1))}"
            + _ai_best(T(1)) + f"{T(1)}every_country = {{\n{T(2)}limit = {{ has_variable = spec_exch_stand }}\n"
            + _pursue_ai(T(2)) + f"{T(1)}}}\n{t}}}\n"
            f"{t}# each field's three leaders among those pursuing it, monthly (centres.py)\n{lead}" + _leaders(t))


CHARTER_ROOM = 3  # places each charter path hands out: the AI spreads its charters to fill them


def _charter_balance(t):
    """Yearly, before the leaders: an AI Exchange of National Standing or better with no charter, or one whose path it
    cannot place on (a tally of 0), or one of more than CHARTER_ROOM holders while another charter has room, takes the
    charter with the fewest holders among those whose path it can place on (a tie: the first listed). The counts
    (spec_chn_<n>, holders that can place) move as it goes, so the AI fills every charter path's three places."""
    # every path of the charter (two each since beta.12): a dict of one path each kept only the last, so a Money Market
    # counted as placeable only on Lender to Nations' treaties and the AI almost never took it (no Safe Harbor either)
    paths = {c: [k for k, _, d in NAMES if d == c] for c in (1, 2, 3)}
    can = lambda n: (f"{SHARES} " if n == 3 else "") + "OR = { " + " ".join(f"spec_name_{k} > 0" for k in paths[n]) + " }"
    c = lambda n: f"global_var:spec_chn_{n}"
    held = lambda n: f"var:spec_exch_known ?= {n} {can(n)}"
    fewest = lambda n: can(n) + "".join(f" OR = {{ NOT = {{ AND = {{ {can(m)} }} }} {c(n)} <= {c(m)} }}" for m in (1, 2, 3) if m != n)
    T = lambda n: t + "\t" * n
    out = "".join(f"{t}set_global_variable = {{ name = spec_chn_{n} value = 0 }}\n" for n in (1, 2, 3))
    out += "".join(f"{t}every_country = {{\n{T(1)}limit = {{ has_variable = spec_exch_stand var:spec_exch_stand >= 1 {held(n)} }}\n"
                   f"{T(1)}change_global_variable = {{ name = spec_chn_{n} add = 1 }}\n{t}}}\n" for n in (1, 2, 3))
    move = "".join(
        f"{T(2)}{'if' if n == 1 else 'else_if'} = {{\n{T(3)}limit = {{\n{T(4)}{fewest(n)}\n{T(4)}OR = {{\n"
        f"{T(5)}NOR = {{ var:spec_exch_known ?= 1 var:spec_exch_known ?= 2 var:spec_exch_known ?= 3 }}\n"
        + "".join(f"{T(5)}AND = {{ var:spec_exch_known ?= {m} NOT = {{ AND = {{ {can(m)} }} }} }}\n"
                  f"{T(5)}AND = {{ {held(m)} {c(m)} > {CHARTER_ROOM} {c(n)} < {CHARTER_ROOM} }}\n" for m in (1, 2, 3) if m != n)
        + f"{T(4)}}}\n{T(3)}}}\n"
        + "".join(f"{T(3)}if = {{\n{T(4)}limit = {{ {held(m)} }}\n{T(4)}change_global_variable = {{ name = spec_chn_{m} add = -1 }}\n{T(3)}}}\n"
                  for m in (1, 2, 3) if m != n)
        + f"{T(3)}change_global_variable = {{ name = spec_chn_{n} add = 1 }}\n"
        f"{T(3)}set_variable = {{ name = spec_exch_known value = {n} }}\n" + _charter_stop(n, T(3)) + f"{T(2)}}}\n"
        for n in (1, 2, 3))
    return (f"{t}# the AI spreads its charters so each charter path has its three places (centres.py)\n{out}"
            f"{t}every_country = {{\n{T(1)}limit = {{ is_player = no has_variable = spec_exch_stand var:spec_exch_stand >= 1 }}\n"
            f"{move}{t}}}\n")


def charter_pick(counts, known, can):
    """Python model of _charter_balance for one AI: counts {n: holders that can place}, known (0: none), can {n: bool}.
    The counts include us if we hold `known` and can place on it."""
    ok = [n for n in (1, 2, 3) if can[n]]
    if not ok:
        return known
    n = min(ok, key=lambda m: (counts[m], m))
    stuck = known not in (1, 2, 3) or not can[known]
    return n if stuck or (counts[known] > CHARTER_ROOM and counts[n] < CHARTER_ROOM) else known


def _eligible(k, ch, t, pursued=True):
    """An Exchange in the running for name k: National Standing or better, the charter if the name needs one, and
    (2026-11-19) pursuing it, since only a pursuit gets a place's effects. pursued=False: any that could pursue it."""
    return (f"{t}is_country_alive = yes\n{t}has_variable = spec_exch_stand\n{t}var:spec_exch_stand >= 1\n"
            + (f"{t}var:spec_exch_known ?= {ch}\n" if ch else "") + (f"{t}has_variable = spec_pu_{k}\n" if pursued else "")
            + f"{t}spec_name_{k} > 0\n")


def _leaders(t):
    """Monthly, after the top three (_names): the bar's leader is first place (global spec_ld_<key>), with its tally
    (spec_ldv_<key>), and second's and third's (spec_t2/t3_<key>) for the bar's dividers. Nobody pursuing it: no
    leader, so any tally leads and the bar shows full; the AI's measure then is spec_bestv (_ai_best), never shown.
    (2026-11-19: a challenger had to stay on top 3 months to take the lead; now it takes only more, as a place does.)"""
    u, w = t + "\t", t + "\t\t"
    gone = lambda n: f"{t}if = {{\n{u}limit = {{ has_global_variable = {n} }}\n{u}remove_global_variable = {n}\n{t}}}\n"
    out = f"{t}# each field's leader, first place (centres.py)\n"
    for k, *_ in NAMES:
        place = lambda p, name, cap, extra="": (
            f"{t}if = {{\n{u}limit = {{ has_global_variable = spec_w_{k}{p} }}\n{extra}"
            f"{u}global_var:spec_w_{k}{p} = {{\n{w}set_global_variable = {{ name = {name}_{k} value = {{ value = spec_name_{k} {cap} }} }}\n"
            f"{u}}}\n{t}}}\n")
        out += ("".join(gone(n) for n in (f"spec_ld_{k}", f"spec_ldv_{k}", f"spec_ch_{k}", f"spec_chm_{k}"))  # spec_ch*: old saves
                + "".join(f"{t}set_global_variable = {{ name = spec_t{p}_{k} value = 0 }}\n" for p in (2, 3))
                + place(1, "spec_ldv", "min = 0.01", f"{u}set_global_variable = {{ name = spec_ld_{k} value = global_var:spec_w_{k}1 }}\n")
                + place(2, "spec_t2", f"max = global_var:spec_ldv_{k}") + place(3, "spec_t3", f"max = global_var:spec_t2_{k}"))
    return out


def _shares(t):
    """Monthly, for the player and every Exchange of National Standing or better: our tally as a share of each
    field's leader (spec_sh_<key>, up to 1.5) and last month's (spec_shl_<key>), for the contest bars."""
    if not NAMES_ON:
        return ""
    u, w = t + "\t", t + "\t\t"
    # our tally itself (spec_nv_<key>), for the Exchange tab: read as a script value there it was recomputed every frame
    each = "".join(f"{u}set_variable = {{ name = spec_nv_{k} value = spec_name_{k} }}\n"
                   f"{u}if = {{\n{w}limit = {{ has_global_variable = spec_ldv_{k} }}\n"
                   f"{w}if = {{\n{w}\tlimit = {{ has_variable = spec_sh_{k} }}\n"
                   f"{w}\tset_variable = {{ name = spec_shl_{k} value = var:spec_sh_{k} }}\n{w}}}\n"
                   f"{w}set_variable = {{ name = spec_sh_{k} value = {{ value = spec_name_{k} divide = global_var:spec_ldv_{k} max = 1.5 }} }}\n"
                   f"{u}}}\n{u}else_if = {{\n{w}limit = {{ has_variable = spec_sh_{k} }}\n"
                   f"{w}remove_variable = spec_sh_{k}\n{w}remove_variable = spec_shl_{k}\n{u}}}\n" for k, *_ in NAMES)
    return (f"{t}if = {{\n{u}limit = {{\n{w}has_variable = spec_exch_stand\n"
            f"{w}OR = {{\n{w}\tis_player = yes\n{w}\tvar:spec_exch_stand >= 1\n{w}}}\n{u}}}\n{each}{t}}}\n") + _near(t)


def _near(t):
    """Monthly, for a player: our place among the Exchanges pursuing each path (spec_rk_<key>: one more than those
    ahead of us, where we would stand if we do not pursue it), shown under the top three (2026-11-19: the three just
    ahead of us were, spec_ab1..3_<key>, left unused in older saves)."""
    T = lambda n: t + "\t" * n
    out = ""
    for k, _, ch in NAMES:
        ahead = f"{_eligible(k, ch, T(4))}{T(4)}spec_rank_{k} > local_var:spec_my_v\n"  # ties as the ranking breaks them
        out += (f"{T(1)}set_local_variable = {{ name = spec_my_v value = spec_rank_{k} }}\n"
                f"{T(1)}set_variable = {{ name = spec_rk_{k} value = {{\n{T(2)}value = 1\n{T(2)}every_country = {{\n{T(3)}limit = {{\n"
                f"{ahead}{T(3)}}}\n{T(3)}add = 1\n{T(2)}}}\n{T(1)}}} }}\n")
    return (f"{t}if = {{  # our place on each path (centres._near)\n{T(1)}limit = {{ is_player = yes has_variable = spec_exch_stand }}\n"
            f"{out}{t}}}\n")


def _charter_effects():
    """The state grants a charter: free the first time, then at a cost in trust (cut directly, not through the losses
    multiplier); the specialities only the old charter allowed are stopped (_charter_stop, also on the AI's yearly
    change of charter)."""
    return "".join(f"spec_charter_to_{n} = {{\n\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_exch_known\n"
                   f"\t\t\thas_variable = spec_centre_trust\n\t\t}}\n"
                   + _record_trust(f"\t\tset_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
                                   f"multiply = {1 - CHARTER_COST:g} }} }}\n", "charter", "\t\t")
                   + f"\t}}\n\tset_variable = {{ name = spec_exch_known value = {n} }}\n"
                   f"\tset_variable = {{ name = spec_charter_lock days = {CHARTER_LOCK * 365} }}\n"
                   + _charter_stop(n, "\t") + "}\n\n" for n in (1, 2, 3)) + _pursue_effects()


def _charter_stop(n, t):
    """Stop the specialities that need a charter other than n."""
    return "".join(f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_pu_{k} }}\n{t}\tspec_pursue_stop_{k} = yes\n{t}}}\n"
                   for k, _, c in NAMES if c and c != n)


SHARES = "has_technology_researched = stock_exchange"  # a Share Market needs the technology, for the player and the AI


def _charter_triggers():
    return "".join(f"""
spec_can_charter_{n} = {{
	has_technology_researched = banking
{"	" + SHARES + chr(10) if n == 3 else ""}	custom_tooltip = {{
		text = spec_charter_current_tt
		NOT = {{ var:spec_exch_known ?= {n} }}
	}}
	custom_tooltip = {{
		text = spec_charter_locked_tt
		NOT = {{ has_variable = spec_charter_lock }}
	}}
}}
""" for n in (1, 2, 3)) + _pursue_triggers()


def _pursue_values():
    """How many names the state may pursue at once: one more than its Exchange's Standing."""
    return (f"spec_pursue_slots = {{\n\tvalue = {PURSUE_BASE}\n"
            "\tif = {\n\t\tlimit = { has_variable = spec_exch_stand }\n\t\tadd = var:spec_exch_stand\n\t}\n}\n")


def _pursue_fx(k, lv):
    """The modifiers a pursuit of `k` gives at level lv (0 outside the top three .. 3 first)."""
    (m, base), extra, *costs = PURSUE_FX[k]
    return [(m, round(base * (lv + 1), 4))] + [_cost(c, x, lv) for c, x in costs] + ([tuple(extra)] if lv == 3 else [])


# a path's costs by place: unranked, 3rd, 2nd, 1st. 1.25 for third rounded to uneven steps (2/3/3/4, 4/5/6/8)
COST_SCALE = tuning.get("EXCH_COST_SCALE", [1, 1, 1.5, 2])
APPROVAL_COST = [1, 1, 1, 2]  # approval in whole points: -1, -1, -1, -2 for a -1 cost


def _cost(m, x, lv):
    if m.endswith("approval_add"):
        return (m, x * APPROVAL_COST[lv])
    pts = int(abs(x) * COST_SCALE[lv] * 100 + 0.5)  # whole percent, halves up
    return (m, (pts if x > 0 else -pts) / 100)


def _mod_list(fx):
    """Vanilla's modifier names with our values: green when good for the state, red when bad."""
    out = []
    for m, x in fx:
        good = x < 0 if m == "country_loan_interest_rate_mult" or m.endswith("mortality_mult") else x > 0
        val = f"{x:+g}" if m.endswith(("legitimacy_base_add", "max_companies_add", "approval_add")) else f"{x:+.1%}".replace(".0%", "%")
        out.append(f"#{'P' if good else 'N'} {val}#! ${m}$")
    return out


def _mod_words(fx, sep=", "):
    return sep.join(_mod_list(fx))


# a place's line in the speciality tooltips: its modifiers, then the place (2026-11-19: "1st: ..." labels)
PLACE_IN = ["outside the top three", "in third place", "in second place", "in first place"]


def _pursue_lv(k):
    """Pursue tooltip: what the pursuit gives at each place, ours in bold and the rest grey (vanilla's current-line style)."""
    now = lambda lv: (f"Not({P}.Var('spec_lead_{k}').IsSet)" if lv == 0
                      else f"EqualTo_CFixedPoint({v(f'spec_lead_{k}')}, {fx(4 - lv)})")
    # only our place's line (2026-11-19): the flags hold what each of the top three gives
    pick = f"'SPEC_PURSUE_LV_{k}_0_ON'"
    for lv in (1, 2, 3):
        pick = f"SelectLocalization({now(lv)}, 'SPEC_PURSUE_LV_{k}_{lv}_ON', {pick})"
    return f"[{pick}]"


def _pursue_lv_keys(k):
    """The place lines _pursue_lv picks between."""
    return "".join(f' SPEC_PURSUE_LV_{k}_{lv}_ON: "{_mod_words(_pursue_fx(k, lv))} #grey {PLACE_IN[lv]}#!"\n' for lv in range(4))


def _trust_words(i):
    return f"\\n$TOOLTIP_DELIMITER$\\n{_mod_words(TRUST_FX[i], chr(92) + 'n') if TRUST_FX[i] else '#weak No bonus or penalty#!'}"


def _mods(name, fxs, good):
    return (f"{name} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_coins_{'positive' if good else 'negative'}.dds\n"
            + "".join(f"\t{m} = {x:g}\n" for m, x in fxs) + "}\n")


def _effect_mods():
    """Static modifiers: each pursuit at each place, and trust's levels."""
    return (("".join(_mods(f"spec_pursue_{k}_{lv}", _pursue_fx(k, lv), True) for k, *_ in NAMES for lv in range(4))
             if NAMES_ON else "")
            + ("".join(_mods(f"spec_trust_{i}", f, i >= 2) for i, f in enumerate(TRUST_FX) if f) if ON else ""))


def _trust_mods(t):
    """Monthly: trust's effects follow its level, as the levels bar shows it."""
    u = t + "\t"
    out = ""
    n = len(TRUST_LV)  # the levels bar's bands, as the tooltips state them
    for i, f in enumerate(TRUST_FX):
        if not f:
            continue
        lim = ([f"var:spec_centre_trust >= {CALM * i / n:g}"] if i else []) + ([f"var:spec_centre_trust < {CALM * (i + 1) / n:g}"] if i < n - 1 else [])
        out += (f"{t}if = {{\n{u}limit = {{\n" + "".join(f"{u}\t{c}\n" for c in lim) + f"{u}}}\n"
                f"{u}if = {{\n{u}\tlimit = {{ NOT = {{ has_modifier = spec_trust_{i} }} }}\n{u}\tadd_modifier = {{ name = spec_trust_{i} }}\n{u}}}\n{t}}}\n"
                f"{t}else_if = {{\n{u}limit = {{ has_modifier = spec_trust_{i} }}\n{u}remove_modifier = spec_trust_{i}\n{t}}}\n")
    return out


def _pursue_effects():
    init = ("\tif = {\n\t\tlimit = { NOT = { has_variable = spec_pw_sum } }\n"
            + "".join(f"\t\tset_variable = {{ name = spec_pw_{k} value = 0 }}\n" for k, *_ in NAMES)
            + "\t\tset_variable = { name = spec_pw_sum value = 0 }\n\t\tset_variable = { name = spec_pursue_n value = 0 }\n\t}\n")
    # stopping one moves those chosen after it one place left: compared with its own place before it goes (a global copy
    # is never set while a button's tooltip previews the effect, and the comparison then errors)
    left = lambda k: "".join(f"\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_pu_{j}\n\t\t\tvar:spec_pu_{j} > var:spec_pu_{k}\n"
                             f"\t\t}}\n\t\tchange_variable = {{ name = spec_pu_{j} add = -1 }}\n\t}}\n" for j, *_ in NAMES if j != k)
    # the stop button's tooltip previews it after the pursuit is gone (2026-11-19: "Invalid right side ... 'var'")
    gone = lambda k: f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pu_{k} }}\n{left(k)}\t}}\n"  # ponytail: inner lines one tab shallow
    return "".join(f"spec_pursue_to_{k} = {{\n{init}\tchange_variable = {{ name = spec_pursue_n add = 1 }}\n"
                   f"\tset_variable = {{ name = spec_pu_{k} value = var:spec_pursue_n }}\n\tset_variable = spec_has_{k}\n"
                   f"\tset_variable = {{ name = spec_pu_lock_{k} value = {PURSUE_LOCK * 12} }}\n}}\n\n"  # months, counted down in _pursue_month
                   f"spec_pursue_stop_{k} = {{\n{gone(k)}"
                   # its effects end at once (2026-11-19: they faded over PURSUE_MONTHS)
                   f"\tset_variable = {{ name = spec_pw_{k} value = 0 }}\n"
                   + "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = spec_pursue_{k}_{lv} }}\n\t\tremove_modifier = spec_pursue_{k}_{lv}\n\t}}\n" for lv in range(4))
                   + f"\tremove_variable = spec_pu_{k}\n\tremove_variable = spec_has_{k}\n\tif = {{\n\t\tlimit = {{ has_variable = spec_pu_lock_{k} }}\n"
                   f"\t\tremove_variable = spec_pu_lock_{k}\n\t}}\n\tchange_variable = {{ name = spec_pursue_n add = -1 }}\n}}\n\n"
                   for k, *_ in NAMES) + "".join(
        f"spec_pursue_{d}_{k} = {{\n\tset_local_variable = {{ name = spec_to value = var:spec_pu_{k} }}\n"
        f"\tchange_local_variable = {{ name = spec_to add = {step} }}\n"
        + "".join(f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pu_{j} var:spec_pu_{j} = local_var:spec_to }}\n"
                  f"\t\tset_variable = {{ name = spec_pu_{j} value = var:spec_pu_{k} }}\n\t}}\n" for j, *_ in NAMES if j != k)
        + f"\tset_variable = {{ name = spec_pu_{k} value = local_var:spec_to }}\n}}\n\n"
        for k, *_ in NAMES for d, step in (("left", -1), ("right", 1)))


def _pursue_triggers():
    return "".join(f"""
spec_can_pursue_{k} = {{
	custom_tooltip = {{
		text = spec_pursue_current_tt
		NOT = {{ has_variable = spec_pu_{k} }}
	}}
	custom_tooltip = {{
		text = spec_pursue_room_tt
		OR = {{
			NOT = {{ has_variable = spec_pursue_n }}
			spec_pursue_slots > var:spec_pursue_n
		}}
	}}
""" + (f"""	custom_tooltip = {{
		text = spec_pursue_charter_tt_{ch}
		var:spec_exch_known ?= {ch}
	}}
""" if ch else "") + f"""}}

spec_can_pursue_stop_{k} = {{
	has_variable = spec_pu_{k}
	custom_tooltip = {{
		text = spec_pursue_locked_tt
		NOT = {{ has_variable = spec_pu_lock_{k} }}
	}}
}}

spec_can_pursue_left_{k} = {{
	has_variable = spec_pu_{k}
	custom_tooltip = {{
		text = spec_pursue_first_tt
		var:spec_pu_{k} > 1
	}}
}}

spec_can_pursue_right_{k} = {{
	has_variable = spec_pu_{k}
	custom_tooltip = {{
		text = spec_pursue_last_tt
		var:spec_pu_{k} < var:spec_pursue_n
	}}
}}
""" for k, _, ch in NAMES)


def _pursue_drop(u, mark=False):
    """Specialities beyond what the Standing allows are dropped, the last chosen first; the Standing falls by at most
    3 slots, so three passes drop as many. With mark, each dropped one is noted (spec_pu_lost_<key>) for the toast."""
    note = lambda k: f"{u}\tset_variable = spec_pu_lost_{k}\n" if mark else ""
    return "".join(f"{u}if = {{\n{u}\tlimit = {{\n{u}\t\thas_variable = spec_pu_{k}\n{u}\t\tvar:spec_pursue_n > spec_pursue_slots\n"
                   f"{u}\t\tvar:spec_pu_{k} = var:spec_pursue_n\n{u}\t}}\n{note(k)}{u}\tspec_pursue_stop_{k} = yes\n{u}}}\n"
                   for _p in range(3) for k, *_ in NAMES)


def _pursue_renumber(u):
    """Monthly, before the drop: the held specialities get places 1..n again, in their old order (a tie in NAMES
    order), and spec_pursue_n is their count. A won revolution can hand a country two sets with the same places and
    the wrong count (2026-11-19 save: Britain held 6 of 4, places 1,1,2,2,3,4, count 4), which the drop never saw."""
    n = len(NAMES)
    done = lambda k: f"local_var:spec_pu_d_{k}"
    return ("".join(f"{u}set_local_variable = {{ name = spec_pu_d_{k} value = 0 }}\n" for k, *_ in NAMES)
            + f"{u}set_local_variable = {{ name = spec_pu_at value = 0 }}\n"
            + "".join(f"{u}if = {{\n{u}\tlimit = {{ has_variable = spec_pu_{k} var:spec_pu_{k} = {p} {done(k)} = 0 }}\n"
                      f"{u}\tchange_local_variable = {{ name = spec_pu_at add = 1 }}\n"
                      f"{u}\tset_variable = {{ name = spec_pu_{k} value = local_var:spec_pu_at }}\n"
                      f"{u}\tset_local_variable = {{ name = spec_pu_d_{k} value = 1 }}\n{u}}}\n"
                      for p in range(1, n + 1) for k, *_ in NAMES)
            + f"{u}set_variable = {{ name = spec_pursue_n value = local_var:spec_pu_at }}\n")


def renumbered(places, order):
    """Python model of _pursue_renumber for the self-check: {key: place} -> {key: place}."""
    out, at = {}, 0
    for p in range(1, len(order) + 1):
        for k in order:
            if places.get(k) == p and k not in out:
                at += 1
                out[k] = at
    return out


def _pursue_fall(t):
    """The player's Standing has fallen: the specialities it no longer allows are dropped now, not next month, and
    noted until the next fall so the toast can name them."""
    if not NAMES_ON:
        return ""
    u = t + "\t"
    return ("".join(f"{t}if = {{\n{u}limit = {{ has_variable = spec_pu_lost_{k} }}\n{u}remove_variable = spec_pu_lost_{k}\n{t}}}\n"
                    for k, *_ in NAMES)
            + f"{t}if = {{\n{u}limit = {{ has_variable = spec_pursue_n }}\n{_pursue_drop(u, True)}{t}}}\n")


def _pursue_month(t):
    """Monthly: pursuits beyond what the Standing allows are dropped, the last chosen first; each builds up over
    PURSUE_MONTHS and ends at once when stopped; what it gives follows its strength and our place in its field."""
    if not NAMES_ON:
        return ""
    step = round(1 / PURSUE_MONTHS + 0.0005, 3)
    u = t + "\t"
    each = "".join(f"{u}if = {{\n{u}\tlimit = {{ has_variable = spec_pu_{k} }}\n"
                   f"{u}\tchange_variable = {{ name = spec_pw_{k} add = {step:g} }}\n{u}}}\n"
                   f"{u}else = {{\n{u}\tset_variable = {{ name = spec_pw_{k} value = 0 }}\n{u}}}\n"  # stopped: gone (was -step a month)
                   f"{u}clamp_variable = {{ name = spec_pw_{k} min = 0 max = 1 }}\n"
                   # the months a speciality must still be kept, as the Credit Policy's cooldown counts down
                   f"{u}if = {{\n{u}\tlimit = {{ has_variable = spec_pu_lock_{k} }}\n"
                   f"{u}\tchange_variable = {{ name = spec_pu_lock_{k} add = -1 }}\n"
                   f"{u}\tif = {{\n{u}\t\tlimit = {{ var:spec_pu_lock_{k} <= 0 }}\n{u}\t\tremove_variable = spec_pu_lock_{k}\n{u}\t}}\n{u}}}\n"
                   for k, *_ in NAMES)
    # Saves from before a path existed have spec_pw_sum but not that path's strength: start it at 0.
    each = "".join(f"{u}if = {{\n{u}\tlimit = {{ NOT = {{ has_variable = spec_pw_{k} }} }}\n"
                   f"{u}\tset_variable = {{ name = spec_pw_{k} value = 0 }}\n{u}}}\n" for k, *_ in NAMES) + each
    total = " ".join(f"add = var:spec_pw_{k}" for k, *_ in NAMES)
    drop = _pursue_renumber(u) + _pursue_drop(u)
    give = "".join(
        "".join(f"{u}if = {{\n{u}\tlimit = {{ has_modifier = spec_pursue_{k}_{lv} }}\n{u}\tremove_modifier = spec_pursue_{k}_{lv}\n{u}}}\n"
                for lv in range(4))
        + f"{u}if = {{\n{u}\tlimit = {{ var:spec_pw_{k} > 0 }}\n"
        + "".join(f"{u}\t{'if' if r == 1 else 'else_if'} = {{\n{u}\t\tlimit = {{ var:spec_lead_{k} ?= {r} }}\n"
                  f"{u}\t\tadd_modifier = {{ name = spec_pursue_{k}_{4 - r} multiplier = var:spec_pw_{k} }}\n{u}\t}}\n" for r in (1, 2, 3))
        + f"{u}\telse = {{\n{u}\t\tadd_modifier = {{ name = spec_pursue_{k}_0 multiplier = var:spec_pw_{k} }}\n{u}\t}}\n{u}}}\n"
        for k, *_ in NAMES)
    stale = "".join(f"{t}if = {{\n{u}limit = {{\n{u}\thas_variable = spec_has_{k}\n{u}\tNOT = {{ has_variable = spec_pu_{k} }}\n{u}}}\n"
                    f"{u}remove_variable = spec_has_{k}\n{t}}}\n" for k, *_ in NAMES)
    return stale + (f"{t}if = {{\n{u}limit = {{ has_variable = spec_pw_sum }}\n{drop}{each}"
            f"{u}set_variable = {{ name = spec_pw_sum value = {{ value = 0 {total} }} }}\n{give}{t}}}\n")


def _ai_best(t):
    """Yearly, before the AI chooses: the strongest tally among the Exchanges that could pursue each path
    (spec_bestv_<key>), the AI's yardstick where nobody pursues it yet. Never shown (2026-11-19: the bars used it)."""
    u = t + "\t"
    # and how many ranked Exchanges pursue each (spec_pun_<key>), which the AI's choices then add to (2026-11-19: the
    # Provincials, never ranked, counted too: some 200 on Busy Floor)
    return "".join(f"{t}set_global_variable = {{ name = spec_pun_{k} value = {{ value = 0 every_country = {{ limit = {{ {CAN_RANK} has_variable = spec_pu_{k} }} add = 1 }} }} }}\n"
                   f"{t}if = {{\n{u}limit = {{ has_global_variable = spec_bestv_{k} }}\n{u}remove_global_variable = spec_bestv_{k}\n{t}}}\n"
                   f"{t}ordered_country = {{\n{u}limit = {{\n{_eligible(k, ch, u + chr(9), pursued=False)}{u}}}\n"
                   f"{u}order_by = spec_name_{k}\n{u}position = 0\n{u}check_range_bounds = no\n"
                   f"{u}set_global_variable = {{ name = spec_bestv_{k} value = {{ value = spec_name_{k} min = 0.01 }} }}\n{t}}}\n"
                   for k, _, ch in NAMES)


def _pursue_ai(t):
    """Once a year an AI Exchange fills its free specialities, one a pass, each time the path it can be most dominant
    on: its tally against the leader's where Exchanges pursue it, else against the strongest that could (spec_bestv),
    up to 1.5, divided by 1 + AI_CROWD for each Exchange already on it; a tie goes to the first listed (2026-11-19:
    the strongest tied at 1 on many paths, so Deep Pockets and Open Door, listed last, were never taken). Provincial ones too (2026-11-19: they had no share, tied at 0 and all
    took the first path). Once a year one with every slot full first drops its weakest unlocked speciality if another
    path measures AI_SWITCH times better (2026-11-19: it never dropped one, so its first picks stood for good)."""
    v, u, w = t + "\t", t + "\t\t", t + "\t\t\t"
    sh = lambda k: f"local_var:spec_ai_sh_{k}"

    def measure(k, name, ind, held=False):
        # its tally against the leader's, else the strongest that could; up to 1.5; AI_CROWD less for each rival on it
        lv = f"local_var:{name}"
        return (f"{ind}set_local_variable = {{ name = {name} value = 0 }}\n"
                f"{ind}if = {{\n{ind}\tlimit = {{ has_global_variable = spec_ldv_{k} }}\n"
                f"{ind}\tset_local_variable = {{ name = {name} value = {{ value = spec_name_{k} divide = global_var:spec_ldv_{k} max = 1.5 }} }}\n{ind}}}\n"
                f"{ind}else_if = {{\n{ind}\tlimit = {{ has_global_variable = spec_bestv_{k} }}\n"
                f"{ind}\tset_local_variable = {{ name = {name} value = {{ value = spec_name_{k} divide = global_var:spec_bestv_{k} max = 1.5 }} }}\n{ind}}}\n"
                f"{ind}set_local_variable = {{ name = {name} value = {{ value = {lv} divide = {{ value = global_var:spec_pun_{k} "
                f"{'subtract = 1 ' if held else ''}multiply = {AI_CROWD} add = 1 }} }} }}\n")  # held: the others on it
    pun = lambda k, n: f"{w}if = {{\n{w}\tlimit = {{ var:spec_exch_stand >= 1 }}\n{w}\tchange_global_variable = {{ name = spec_pun_{k} add = {n} }}\n{w}}}\n"
    best = "".join(f"{u}set_local_variable = {{ name = spec_ai_sh_{k} value = -1 }}\n"
                   f"{u}if = {{\n{w}limit = {{ spec_can_pursue_{k} = yes }}\n{measure(k, f'spec_ai_sh_{k}', w)}"
                   f"{w}if = {{\n{w}\tlimit = {{ {sh(k)} > local_var:spec_ai_best }}\n"
                   f"{w}\tset_local_variable = {{ name = spec_ai_best value = {sh(k)} }}\n{w}}}\n{u}}}\n" for k, *_ in NAMES)
    take = "".join(f"{u}{'if' if i == 0 else 'else_if'} = {{\n{w}limit = {{ {sh(k)} >= 0 {sh(k)} = local_var:spec_ai_best }}\n"
                   f"{w}spec_pursue_to_{k} = yes\n{pun(k, 1)}{u}}}\n" for i, (k, *_) in enumerate(NAMES))
    room = "OR = { NOT = { has_variable = spec_pursue_n } spec_pursue_slots > var:spec_pursue_n }"
    # the swap: the weakest held one that is no longer locked (spec_ai_worst, spec_ai_drop its index) against the best
    # one it could take, both measured as the passes measure them
    scan = "".join(
        f"{u}if = {{\n{w}limit = {{ has_variable = spec_pu_{k} NOT = {{ has_variable = spec_pu_lock_{k} }} }}\n"
        f"{measure(k, 'spec_ai_m', w, held=True)}{w}if = {{\n{w}\tlimit = {{ local_var:spec_ai_m < local_var:spec_ai_worst }}\n"
        f"{w}\tset_local_variable = {{ name = spec_ai_worst value = local_var:spec_ai_m }}\n"
        f"{w}\tset_local_variable = {{ name = spec_ai_drop value = {i} }}\n{w}}}\n{u}}}\n"
        f"{u}else_if = {{\n{w}limit = {{ NOT = {{ has_variable = spec_pu_{k} }}{f' var:spec_exch_known ?= {ch}' if ch else ''} }}\n"
        f"{measure(k, 'spec_ai_m', w)}{w}if = {{\n{w}\tlimit = {{ local_var:spec_ai_m > local_var:spec_ai_best }}\n"
        f"{w}\tset_local_variable = {{ name = spec_ai_best value = local_var:spec_ai_m }}\n{w}}}\n{u}}}\n"
        for i, (k, _, ch) in enumerate(NAMES))
    drop = "".join(f"{w}{'if' if i == 0 else 'else_if'} = {{\n{w}\tlimit = {{ local_var:spec_ai_drop = {i} }}\n"
                   f"{w}\tspec_pursue_stop_{k} = yes\n{pun(k, -1).replace(w, w + chr(9))}{w}}}\n" for i, (k, *_) in enumerate(NAMES))
    swap = (f"{v}if = {{\n{u}limit = {{ var:spec_exch_stand >= 1 NOT = {{ {room} }} }}\n"  # ranked, every slot full
            f"{u}set_local_variable = {{ name = spec_ai_worst value = 99 }}\n{u}set_local_variable = {{ name = spec_ai_best value = -1 }}\n"
            f"{scan}{u}set_local_variable = {{ name = spec_ai_worst value = {{ value = local_var:spec_ai_worst multiply = {AI_SWITCH} }} }}\n"
            f"{u}if = {{\n{w}limit = {{ local_var:spec_ai_best > local_var:spec_ai_worst }}\n{drop}{u}}}\n{v}}}\n")
    passes = "".join(f"{t}\tif = {{\n{u}limit = {{ {room} }}\n{u}set_local_variable = {{ name = spec_ai_best value = -1 }}\n"
                     f"{best}{take}{t}\t}}\n" for _ in range(4))  # at most 4 specialities
    return f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tis_player = no\n{t}\t\thas_variable = spec_exch_stand\n{t}\t}}\n{swap}{passes}{t}}}\n"


def ai_pick(shares):
    """Python model of a _pursue_ai pass for the self-check: {key: share, or None if it cannot be chosen}."""
    ok = [k for k, x in shares.items() if x is not None]
    return max(ok, key=lambda k: (shares[k], -ok.index(k))) if ok else None


def name_icons():
    """World tab row: the names this market holds, by their icons, centred under the Specialities head (376 to 476)."""
    if not NAMES_ON:
        return ""
    return (f"\t\twidget = {{\n\t\t\tposition = {{ 376 0 }}\n\t\t\tsize = {{ 100 {ROW_H} }}\n"
            "\t\t\tflowcontainer = {\n\t\t\t\tparentanchor = center\n\t\t\t\tspacing = 2\n\t\t\t\tignoreinvisible = yes\n"
            + "".join(f"\t\t\t\ticon = {{\n\t\t\t\t\tvisible = \"[{P}.Var('spec_has_{k}').IsSet]\"\n\t\t\t\t\tsize = {{ 22 22 }}\n"
                      f"\t\t\t\t\ttexture = \"{ICON(k)}\"\n\t\t\t\t\ttooltip = \"SPEC_NAME_ICON_TT_{k}\"\n\t\t\t\t}}\n" for k, *_ in NAMES)
            + "\t\t\t}\n\t\t}\n")


def _charter_block():
    """Exchange tab: the three charters, the held one selected, each with its button."""
    cw = (W - 20) // 3
    held = lambda n: f"EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})"
    card = lambda n, tex: f"""widget = {{
	size = {{ {cw} 162 }}
	tooltip = "SPEC_EXCH_CARD_TT_{n}"
	using = entry_bg_fancy
	background = {{
		visible = "[{held(n)}]"
		using = paper_bg
	}}
	icon = {{
		visible = "[{held(n)}]"
		using = highlighted_square_selection
	}}
	icon = {{
		size = {{ 52 52 }}
		position = {{ 0 10 }}
		parentanchor = top|hcenter
		texture = "gfx/interface/icons/{tex}.dds"
	}}
	textbox = {{
		position = {{ 0 64 }}
		size = {{ 100% 22 }}
		parentanchor = top|hcenter
		align = center|nobaseline
		text = "SPEC_EXCH_CARD_H_{n}"
	}}
	textbox = {{
		position = {{ 0 86 }}
		size = {{ {cw - 12} 30 }}
		parentanchor = top|hcenter
		multiline = yes
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_EXCH_CARD_N_{n}"
	}}
	button = {{
		position = {{ 0 -12 }}
		size = {{ {cw - 28} 30 }}
		parentanchor = bottom|hcenter
		using = default_button
		align = center|nobaseline
		enabled = "{sg(f'charter_{n}', 'IsValid')}"
		onclick = "{sg(f'charter_{n}', 'Execute')}"
		text = "SPEC_CHARTER_BTN_{n}"
		tooltip = "SPEC_EXCH_CARD_TT_{n}"
	}}
}}
"""
    return f"""flowcontainer = {{
	parentanchor = hcenter
	spacing = 10
{ind("".join(card(n, tex) for n, tex in CARDS), 1)}}}
"""


def names_block():
    """Exchange tab, Specialities: a card a slot, left to right in the order chosen (the last chosen dropped first).
    A held card moves earlier or later and drops; paths are chosen in the list below; locked ones point to the Standing."""
    n_slot = 4
    # beta.12 layout: a top strip (slot number left, Drop right), the icon between them, the name under it, and a
    # bottom strip under a rule with the two order arrows at its ends
    cw, ch = (W - 10 * (n_slot - 1)) // n_slot, 112
    from market_tab import FLAT
    n_held = v("spec_pursue_n")
    slots = f"{P}.ScriptValue('spec_pursue_slots')"
    card = lambda vis, tt, body: f"""widget = {{
	visible = "[{vis}]"
	size = {{ {cw} {ch} }}
	tooltip = "{tt}"
	using = entry_bg_fancy
""" + ind(body, 1) + "}\n"
    title = lambda key, y: f"""textbox = {{
	position = {{ 0 {y} }}
	size = {{ {cw - 10} 22 }}
	parentanchor = top|hcenter
	align = center|nobaseline
	elide = right
	fontsize_min = 12  # 2026-11-22: shrinks to fit Home of Great Companies, which was cut short
	text = "{key}"
}}
"""
    pic = lambda tex, y, n: f"""icon = {{
	position = {{ 0 {y} }}
	size = {{ {n} {n} }}
	parentanchor = top|hcenter
	texture = "{tex}"
}}
"""
    name = lambda key, y, h=40, al="center|nobaseline": f"""textbox = {{
	position = {{ 0 {y} }}
	size = {{ {cw - 12} {h} }}
	parentanchor = top|hcenter
	multiline = yes
	fontsize = 14
	align = {al}
	text = "{key}"
}}
"""
    badge = lambda i: f"""widget = {{
	position = {{ 6 6 }}
	size = {{ 24 24 }}
	icon = {{
		size = {{ 100% 100% }}
		texture = "{ROUND}"
	}}
	textbox = {{
		size = {{ 100% 100% }}
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_SLOT_NUM_{i}"
	}}
}}
"""
    move = lambda k, d, kind, x: f"""{kind} = {{
	position = {{ {x} -5 }}
	parentanchor = {'bottom|left' if d == 'left' else 'bottom|right'}
	size = {{ 22 22 }}
	enabled = "{sg(f'pursue_{d}_{k}', 'IsValid')}"
	onclick = "{sg(f'pursue_{d}_{k}', 'Execute')}"
	tooltip = "SPEC_PURSUE_{d.upper()}_TT_{k}"
}}
"""
    # a held card's controls, kept off its name: earlier and later beside the picture (the order is the order they are
    # lost in), Drop as the corner's close button
    rule = f"""icon = {{
	position = {{ 0 -32 }}
	size = {{ {cw - 16} 1 }}
	parentanchor = bottom|hcenter
	texture = "{FLAT}"
	color = {{ 1 1 1 0.15 }}
}}
"""
    foot = lambda k: (rule + move(k, "left", "button_icon_move_left", 8) + move(k, "right", "button_icon_move_right", -8) + f"""close_button = {{
	position = {{ -6 6 }}
	parentanchor = right
	size = {{ 24 24 }}
	enabled = "{sg(f'pursue_stop_{k}', 'IsValid')}"
	onclick = "{sg(f'pursue_stop_{k}', 'Execute')}"
	tooltip = "SPEC_PURSUE_STOP_TT_{k}"
}}
""")
    # picking: the slot is chosen first, then a path row below (rows only click while picking)
    pick_lit = f"""icon = {{
	visible = "[GetVariableSystem.Exists('spec_pick_slot')]"
	using = highlighted_square_selection
}}
"""
    pick_btn = "".join(f"""button = {{
	visible = "[{vis}]"
	position = {{ 0 -8 }}
	size = {{ {cw - 20} 28 }}
	parentanchor = bottom|hcenter
	using = default_button
	align = center|nobaseline
	onclick = "[{click}]"
	text = "{key}"
	tooltip = "{key}_TT"
}}
""" for vis, click, key in ((f"Not(GetVariableSystem.Exists('spec_pick_slot'))", "GetVariableSystem.Set('spec_pick_slot', '1')", "SPEC_SLOT_PICK"),
                            ("GetVariableSystem.Exists('spec_pick_slot')", "GetVariableSystem.Clear('spec_pick_slot')", "SPEC_SLOT_PICK_CANCEL")))
    at = lambda i: fx(i - 0.5)
    out = ""
    for i in range(1, n_slot + 1):
        out += "".join(card(f"EqualTo_CFixedPoint({v(f'spec_pu_{k}')}, {fx(i)})", f"SPEC_NAME_TT_{k}",
                            # 2026-11-22: a smaller picture, so a long name gets its two lines (Home of Great Companies was cut)
                            pic(ICON(k), 6, 36) + name(f"SPEC_NAME_H_{k}", 42, 38) + badge(i) + foot(k)) for k, *_ in NAMES)
        room = f"GreaterThan_CFixedPoint({slots}, {at(i)})"
        out += card(f"And({room}, EqualTo_CFixedPoint({n_held}, {fx(i - 1)}))", "SPEC_SLOT_OPEN_TT",
                    pick_lit + title("SPEC_SLOT_OPEN", (ch - 22) // 2 - 16) + badge(i) + pick_btn)
        if i > 1:
            out += card(f"And({room}, LessThan_CFixedPoint({n_held}, {at(i - 1)}))", "SPEC_SLOT_LATER_TT",
                        title("SPEC_SLOT_OPEN", (ch - 22) // 2) + badge(i))
            out += card(f"And(LessThan_CFixedPoint({slots}, {at(i)}), LessThan_CFixedPoint({n_held}, {at(i)}))",
                        f"SPEC_SLOT_LOCK_TT_{i - 1}", pic("gfx/interface/buttons/button_icons/lock.dds", 22, 28)
                        + name(f"SPEC_SLOT_LOCK_{i - 1}", 56, 40, "hcenter|top") + badge(i))
    return f"""flowcontainer = {{
	parentanchor = hcenter
	spacing = 10
	ignoreinvisible = yes
{ind(out, 1)}}}
"""


def contest_block():
    """Exchange tab, Paths to Renown: a row a path with its icon, our tally beside its name, last year's three
    leaders under 1st, 2nd and 3rd, and what it gives. The paths any Exchange can follow come first, the charters'
    own after. Choosing and dropping is on the Specialities cards above."""
    from market_tab import FLAT, CLEAR, BARS
    order = [x for x in NAMES if not x[2]] + [x for x in NAMES if x[2]]
    rh = 66  # beta.12: name, then the bar across the column, then our tally under it, so nothing is squeezed
    # the columns; beta.12: name and flags narrowed so Effects (short lines, FX_COLUMN) fits without wrapping
    NX, NW, FX0, GX, FS = 68, 186, 256, 368, 36  # FS: a flag's column, with room between the flags
    BAR_Y, BAR_H = 30, 12  # the bar's track, under the name
    BW = NW - 14  # the bar: the name column's width; our figure and its word sit under it
    GW = W - GX - 8

    def flag(k, pos):
        g = f"GetGlobalVariable('spec_w_{k}{pos}')"
        return f"""widget = {{
	position = {{ {FX0 + (pos - 1) * FS} {(rh - 20) // 2} }}
	size = {{ 30 20 }}
	tooltip = "SPEC_NAME_FLAG_TT_{k}{pos}"
	icon = {{
		visible = "[Not({g}.GetCountry.IsValid)]"
		size = {{ 27 18 }}
		parentanchor = top|hcenter
		texture = "{FLAT}"
		color = {{ 1 1 1 0.08 }}
	}}
	widget = {{
		visible = "[{g}.GetCountry.IsValid]"
		size = {{ 100% 100% }}
		datacontext = "[{g}.GetCountry]"
		tiny_flag = {{
			parentanchor = top|hcenter
			blockoverride "tooltip" {{ tooltip = "SPEC_NAME_FLAG_TT_{k}{pos}" }}  # the place's tooltip, not the country's
		}}
	}}
}}
"""

    def row(k, ch):
        has = f"{P}.Var('spec_has_{k}').IsSet"
        pu = f"{P}.Var('spec_pu_{k}').IsSet"
        open_ = f"EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(ch)})" if ch else ""
        sh = v(f"spec_sh_{k}")
        shl = f"{P}.Var('spec_shl_{k}').GetValueWithDefault({sh})"  # no last month: no change shown
        # all in leader's tallies: the bar runs to 1.15 x the larger of ours and the leader's, so first place shows
        ldv = f"GetGlobalVariable('spec_ldv_{k}').GetValue"
        at = lambda x: f"Divide_CFixedPoint({x}, Multiply_CFixedPoint(Max_CFixedPoint({sh}, {fx(1)}), {fx(1.15)}))"
        tp = lambda p: at(f"Divide_CFixedPoint(GetGlobalVariable('spec_t{p}_{k}').GetValue, {ldv})")
        from interest_list import chevrons
        zones = f"""icon = {{
	size = {{ 100% 100% }}
	texture = "{BARS}/progressbar_empty.dds"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	alpha = 0.8
}}
"""
        # vanilla's divider where each place begins (a marker rides the end of an unseen bar)
        lead_ok = f"GetGlobalVariable('spec_ld_{k}').GetCountry.IsValid"  # anyone pursues it
        # nobody pursues it: any tally of ours leads, so the bar is full (2026-11-19: it measured against non-pursuers)
        fill = f"Select_CFixedPoint({lead_ok}, {at(sh)}, Select_CFixedPoint({gt(v(f'spec_nv_{k}'), 0)}, {fx(1)}, {fx(0)}))"
        div = lambda x: f"""progressbar = {{
	visible = "[And({lead_ok}, {gt(x, 0.02)})]\"
	size = {{ 100% 100% }}
	progresstexture = "{CLEAR}"
	noprogresstexture = "{CLEAR}"
	min = 0
	max = 1
	value = "[{x}]"
	marker = {{
		widget = {{
			size = {{ 100% 100% }}
			icon = {{
				size = {{ 3 100% }}
				widgetanchor = right
				texture = "{BARS}/progressbar_center_divider.dds"
				texture_density = 2
			}}
		}}
	}}
}}
"""
        up = gt(f"Subtract_CFixedPoint({sh}, {shl})", 0.001)
        down = gt(f"Subtract_CFixedPoint({shl}, {sh})", 0.001)
        # our tally, lit as vanilla lights a bar: gold and chevrons running on while we gain on the leader,
        # red and chevrons running back while we fall behind, blue when steady
        ours = "".join(f"""progressbar = {{
	visible = "[{vis}]"
	size = {{ 100% 100% }}
	progresstexture = "{BARS}/progressbar_{c}.dds"
	noprogresstexture = "{CLEAR}"
	spriteType = Corneredtiled
	spriteborder = {{ 4 4 }}
	texture_density = 2
	using = progressbar_texture_properties
	min = 0
	max = 1
	value = "[{fill}]"
	marker = {{
		widget = {{
			size = {{ 100% 100% }}
			icon = {{
				size = {{ 30 100% }}
				widgetanchor = right
				alpha = 0.7
				texture = "{BARS}/progressbar_{c}_glow.dds"
				icon = {{
					size = {{ 3 100% }}
					parentanchor = right
					texture = "{BARS}/progressbar_{c}_glow_line.dds"
					spriteType = Corneredtiled
					spriteborder = {{ 0 0 }}
				}}
			}}
{ind(chevrons(up, down), 3)}		}}
	}}
}}
""" for vis, c in ((up, "gold"), (down, "bad"), (f"And(Not({up}), Not({down}))", "default")))
        # while a slot is being filled: the rows that can be chosen lit, the rest dimmed
        picking = "GetVariableSystem.Exists('spec_pick_slot')"
        ok = sg(f'pursue_{k}', 'IsValid')[1:-1]
        lit = f"""icon = {{
	visible = "[And({picking}, {ok})]"
	using = highlighted_square_selection
}}
"""
        # a path closed by our charter, or one that cannot fill the slot being picked, faded as vanilla fades what is
        # off (TransparentIfFalse): a dark overlay on top hid the bar's, tally's and flags' tooltips (2026-11-19)
        bright = f"Or(Not({picking}), {ok})"
        bright = f"And({open_}, {bright})" if ch else bright
        bar = zones + ours + div(tp(3)) + div(tp(2)) + div(at(fx(1)))
        pick = f"""button = {{
	visible = "[And({picking}, {ok})]"
	size = {{ 100% 100% }}
	tooltip = "SPEC_ROW_TT_{k}"
	onclick = "{sg(f'pursue_{k}', 'Execute')}"
	onclick = "[GetVariableSystem.Clear('spec_pick_slot')]"
	using = select_button_sound
}}
"""
        return f"""widget = {{
	size = {{ {W} {rh} }}
	alpha = "[TransparentIfFalse({bright})]"
	tooltip = "SPEC_ROW_TT_{k}"
	background = {{
		visible = "[Not({has})]"
		using = entry_bg_simple
	}}
	background = {{
		visible = "[{has}]"
		using = paper_bg
	}}
	icon = {{
		visible = "[And({pu}, Not({picking}))]"
		using = highlighted_square_selection
	}}
{ind(lit, 1)}	icon = {{
		position = {{ 10 0 }}
		size = {{ 48 48 }}
		parentanchor = vcenter
		texture = "{ICON(k)}"
	}}
	flowcontainer = {{
		position = {{ {NX} 4 }}
		spacing = 6
		ignoreinvisible = yes
		widget = {{
			visible = "[{pu}]"
			size = {{ 24 24 }}
			tooltip = "SPEC_PURSUE_SLOT_TT"
			icon = {{
				size = {{ 100% 100% }}
				texture = "{ROUND}"
			}}
			textbox = {{
				size = {{ 100% 100% }}
				align = center|nobaseline
				using = fontsize_small
				text = "SPEC_PURSUE_SLOT_{k}"
			}}
		}}
		textbox = {{
			size = {{ {NW - 30} 24 }}
			align = left|nobaseline
			elide = right
			fontsize_min = 13  # shrinks to fit the longest name (Home of Great Companies), as vanilla's elide_fontsize_min
			text = "SPEC_NAME_H_{k}"
		}}
	}}
	# framed as market_tab.framed_bar is: the frame sits 3 outside the fill, under it, so it never covers the fill
	widget = {{
		position = {{ {NX + 3} {BAR_Y} }}
		size = {{ {BW} {BAR_H} }}
		tooltip = "SPEC_NAME_BAR_TT_{k}"
		background = {{
			texture = "{BARS}/progressbar_frame.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
			margin = {{ 3 3 }}
		}}
		widget = {{
			size = {{ 100% 100% }}
			scissor = yes
{ind(bar, 3)}		}}
	}}
	widget = {{  # a textbox's own tooltip had no Country context (2026-11-19: FetchData failed on every hover)
		position = {{ {NX + 3} {BAR_Y + BAR_H + 3} }}
		size = {{ {NW - 6} 18 }}
		tooltip = "SPEC_NAME_VAL_TT_{k}"  # our count and what our place gives; the bar's own tooltip is the race
		textbox = {{
			size = {{ 100% 100% }}
			align = left|nobaseline
			elide = right
			using = fontsize_small
			text = "SPEC_NAME_TALLY_{k}"
		}}
	}}
{ind(flag(k, 1) + flag(k, 2) + flag(k, 3), 1)}	textbox = {{
		position = {{ {GX} 0 }}
		size = {{ {GW} {rh} }}
		multiline = yes
		align = left|nobaseline
		using = fontsize_small
		text = "SPEC_NAME_STATUS_{k}"
	}}
{ind(pick, 1)}}}
"""
    # the column heads as every other table's in the window (market_tab.heads); the places' cells are as narrow as
    # their flags, so their words sit without the usual margin
    cols = heads([(0, FX0 - 2, "SPEC_CONTEST_COL_NAME", "left", False), (GX - 2, W - GX + 2, "SPEC_CONTEST_COL_GIVES", "left", False)]
                 + [(FX0 - 2 + (p - 1) * FS, FS, f"SPEC_CONTEST_PLACE_{p}", "center", False) for p in (1, 2, 3)])
    cols = __import__("re").sub(r"\t*margin = \{ 10 0 \}\n(\t*align = center)", r"\1", cols)
    return f"""{cols}flowcontainer = {{
	parentanchor = hcenter
	direction = vertical
	spacing = 4
{ind("".join(row(k, ch) for k, _, ch in order), 1)}}}
"""


# the Effects column's words: one short line each (FX_WORDS, in full, are the tooltips')
FX_SHORT = {"hype": "Investor Reaction", "flight": "Capital flight in", "loss": "Trust losses", "credit": "Credit lent",
            "press": "Press Campaigns", "raid": "Bear Raids", "lure": "Lure Investors", "shore": "Shore Up length",
            "crash": "Bust losses", "panic": "Panic length", "rescue": "Rescue cost", "tie_inv": "Investment ties",
            "tie_trade": "Trade ties", "blue": "Blue Chip climb", "burst": "Bubble Bursts", "bad": "Bad Debts",
            "ceiling": "Credit ceiling"}
# a hook's words, and whether more of it helps (1), hurts (-1) or neither (0)
FX_WORDS = {"hype": ("Investor Reaction", 0), "flight": ("[concept_spec_capital_flight]", 1), "loss": ("Trust losses", -1),
            "credit": ("Credit lent", 1),
            # levers in the rest of the mod (NX_HOOKS)
            "press": ("Our Press Campaigns", 1), "raid": ("Our Bear Raids", 1),
            "lure": ("Our Lure Investors", 1), "shore": ("Our Shore Up lasts", 1),
            "crash": ("Confidence lost in busts", -1), "panic": ("[concept_spec_financial_panic] length", -1),
            "rescue": ("Rescue cost", -1), "tie_inv": ("Investment ties to other markets", 0),
            "tie_trade": ("Trade ties to other markets", 0), "blue": ("[concept_spec_blue_chip] climb", 1),
            "burst": ("Bubble Bursts", -1), "bad": ("[concept_spec_bad_debts] a panic leaves", -1),
            "ceiling": ("Credit ceiling", 1)}
NAMES_ABOUT = ("A country grants its Exchange one charter, either #v Commodity Exchange#!, #v Money Market#! or #v Share Market#!. "
               f"The Exchange holds #v {PURSUE_BASE}#! to #v {PURSUE_TOP}#! specialities from the #v {len(NAMES)}#! Paths to Renown, more as its "
               f"Standing rises, and cannot drop one in its first #v {PURSUE_LOCK}#! years.")
FX_COLUMN = {h: (FX_SHORT[h], g) for h, (_, g) in FX_WORDS.items()}


# a speciality's own effects, one value-first line each as the calculator tooltips (2026-11-19): FX_SHORT's words,
# with concept links where one exists
FX_LINE = {**FX_SHORT, "flight": "[concept_spec_capital_flight] received", "crash": "[concept_spec_bust] losses",
           "panic": "[concept_spec_financial_panic] length", "blue": "[concept_spec_blue_chip] climb",
           "bad": "[concept_spec_bad_debts]"}


def _fx_lines(k):
    def one(hook, x):
        good = FX_WORDS[hook][1]
        col = "v" if not good else "P" if (x > 1) == (good > 0) else "N"
        return f"#{col} {x - 1:+.0%}#! {FX_LINE[hook]}"
    return "\\n".join(one(h, x) for h, x in NAME_FX[k].items())

def _fx_words(k, sep, words=FX_WORDS):
    def one(hook, x):
        what, good = words[hook]
        col = "v" if not good else "P" if (x > 1) == (good > 0) else "N"
        return f"{what}: #{col} {x - 1:+.0%}#!"
    return sep.join(one(h, x) for h, x in NAME_FX[k].items())


ORD = ("1st", "2nd", "3rd")
# after "Ranked by ...": why a tally can sit under the figure it is ranked by (Safe Harbor's trust, 2026-11-20)
RANK_COST = f" Each other speciality a country pursues takes #N {1 - PURSUE_COST:.0%}#! off its score."


def _shown(k, x):
    """A tally as the tooltips show it: Safe Harbor's as a share of full trust, as the Exchange tab shows trust
    (player report 2026-11-20: "114 trust" beside a tab showing 85%)."""
    return f"Divide_CFixedPoint({x}, {fx(CALM)})" if k == "harbour" else x


def _rank_words(k, title, cur, f, unit, by, pu, ours_v):
    """The bar's tooltip (2026-11-19): what the path is ranked by; then, holding a place, the top three with ours in
    bold, else the three just ahead of us (_near) and us at our place; then the gap to the next place."""
    lead = v(f"spec_lead_{k}")
    held = gt(lead, 0.5)
    rk = v(f"spec_rk_{k}")
    w = lambda p: f"GetGlobalVariable('spec_w_{k}{p}')"
    val = lambda c: _shown(k, f"{c}.GetCountry.MakeScope.Var('spec_nv_{k}').GetValueWithDefault({fx(0)})")
    num = lambda x: f"#v {cur}[{x}|{f}]#! #grey {unit}#!"
    eq = lambda x, n: f"EqualTo_CFixedPoint({x}, {fx(n)})"
    out, ords = "", []

    def ordinal(x, key):  # ponytail: 21st and on read 21th; no path has that many pursuers
        ords.append(f' {key}: "#v [{x}|0]th#!"\n')  # not into out: `out += f"{ordinal()}"` read out first and lost it
        return (f"[SelectLocalization({eq(x, 1)}, 'SPEC_ORD_1', SelectLocalization({eq(x, 2)}, 'SPEC_ORD_2', "
                f"SelectLocalization({eq(x, 3)}, 'SPEC_ORD_3', '{key}')))]")

    # the gap to the next place; after the top three's rows, which end in a line break, no break before it
    gap = lambda them, sign, name, nl="": (f'"{nl}$TOOLTIP_DELIMITER$\\n#v {cur}+[{sign}|{f}]#! #grey {unit}#! {name} '
                                           f'[{them}.GetCountry.GetNameNoFormatting]"\n')
    # holding a place: the top three, ours in bold
    for p in (1, 2, 3):
        row = lambda b: f"#v {ORD[p - 1]}#! {b}[{w(p)}.GetCountry.GetName]{'#!' if b else ''} {num(val(w(p)))}\\n"
        out += (f" SPEC_RANK_W{p}_{k}: \"[SelectLocalization({eq(lead, p)}, 'SPEC_RANK_WU{p}_{k}', 'SPEC_RANK_WO{p}_{k}')]\"\n"
                f' SPEC_RANK_WU{p}_{k}: "{row("#b ")}"\n SPEC_RANK_WO{p}_{k}: "{row("")}"\n')
    out += (f" SPEC_RANK_TOP_{k}: \"" + "".join(f"[AddLocalizationIf({w(p)}.GetCountry.IsValid, 'SPEC_RANK_W{p}_{k}')]" for p in (1, 2, 3))
            + f"[SelectLocalization({eq(lead, 1)}, 'SPEC_RANK_G1_{k}', SelectLocalization({eq(lead, 2)}, 'SPEC_RANK_G2_{k}', 'SPEC_RANK_G3_{k}'))]\"\n"
            f" SPEC_RANK_G1_{k}: \"[AddLocalizationIf({w(2)}.GetCountry.IsValid, 'SPEC_RANK_AHEAD_{k}')]\"\n"
            f" SPEC_RANK_AHEAD_{k}: " + gap(w(2), f"Subtract_CFixedPoint({ours_v}, {val(w(2))})", "ahead of")
            + f" SPEC_RANK_G2_{k}: " + gap(w(1), f"Subtract_CFixedPoint({val(w(1))}, {ours_v})", "to pass")
            + f" SPEC_RANK_G3_{k}: " + gap(w(2), f"Subtract_CFixedPoint({val(w(2))}, {ours_v})", "to pass"))
    # outside the top three, or not pursuing it: the top three, then us where we stand or would (2026-11-19: the three
    # just ahead of us)
    near = "".join(f"[AddLocalizationIf({w(p)}.GetCountry.IsValid, 'SPEC_RANK_WO{p}_{k}')]" for p in (1, 2, 3))
    stand = v("spec_exch_stand")
    out += (f" SPEC_RANK_NEAR_{k}: \"{near}{ordinal(rk, f'SPEC_ORD_{k}_0')} #b [Country.GetName]#! {num(ours_v)}"
            f"[AddLocalizationIf(Not({pu}), 'SPEC_RANK_IFPU')][AddLocalizationIf(And({pu}, Not({gt(stand, 0.5)})), 'SPEC_RANK_NEEDNAT')]"
            f"[AddLocalizationIf({gt(rk, 3.5)}, 'SPEC_RANK_GN_{k}')][AddLocalizationIf(Not({w(1)}.GetCountry.IsValid), 'SPEC_NAME_NOLEAD')]\"\n"
            f" SPEC_RANK_GN_{k}: " + gap(w(3), f"Subtract_CFixedPoint({val(w(3))}, {ours_v})", "to pass", "\\n"))
    return (f' SPEC_NAME_BAR_TT_{k}: "#header {title}#!\\n$TOOLTIP_DELIMITER$\\nRanked by {by}.{RANK_COST}\\n$TOOLTIP_DELIMITER$\\n'
            f"[SelectLocalization({held}, 'SPEC_RANK_TOP_{k}', 'SPEC_RANK_NEAR_{k}')]\"\n" + out + "".join(ords))


def _names_loc(ui, known):
    """The charter cards' and the names' words; replaces the earned cards' (same keys)."""
    tc = "[GetBuildingType('building_trade_center').GetName]"
    by = {"price": ("the value of the goods our market deals in, times our share of the market's [concept_gdp]", "D"),
          "harbour": ("the [concept_spec_trust] our Exchange holds", "%0"),
          "companies": ("[concept_spec_company_strength], which is the [concept_prosperity] of our companies plus "
                        f"#v {companies.BLUE_BONUS:g}#! for each [concept_spec_blue_chip]. We hold #v [{v('spec_bc_n')}|0]#! "
                        f"@spec_blue_chip! [Concept('concept_spec_blue_chip','$concept_spec_blue_chips$')]", "1"), "floor": (f"{tc} levels", "0"),
          "sound": ("quiet months of sound lending", "0"),
          "pockets": ("money entering the [concept_investment_pool] each month", "D"),
          "door": ("treaties with other countries", "0"),
          "futures": ("the states our market reaches", "0"),
          "lender": ("countries granting us [concept_foreign_investment] rights", "0"),
          "railway": ("[GetBuildingType('building_railway').GetName] and [GetBuildingType('building_port').GetName] levels", "0")}
    drop = (" SPEC_EXCH_CARD_N_", " SPEC_EXCH_CARD_TT_", " SPEC_H_KNOWN_TT", " SPEC_EXCH_CARD_NOTE", " SPEC_EXCH_CARD_HELD")
    out = "".join(line for line in ui.splitlines(True) if not line.startswith(drop))
    short = [f"Investor Reaction: #v {KNOWN_HYPE - 1:+.0%}#!", f"Trust losses: #P {KNOWN_LOSS - 1:+.0%}#!",
             f"Credit lent: #P {KNOWN_CREDIT - 1:+.0%}#!"]
    # the tooltip's lines in full, as the Exchange row's tooltip words them
    full = [f"Investor Reaction to rising prices: #v {KNOWN_HYPE - 1:+.0%}#!", short[1],
            f"Credit lent each month: #P {KNOWN_CREDIT - 1:+.0%}#!"]
    only = {}
    for _, title, ch in NAMES:
        if ch:  # both of a charter's paths can be held at once
            only[ch] = f"{only[ch]}#! and #v {title}" if ch in only else title
    held = lambda n: f"EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})"
    for n in (1, 2, 3):
        key = f"charter_{n}"
        switching = f"And({P}.Var('spec_exch_known').IsSet, Not({held(n)}))"
        losses = "".join(f"[AddLocalizationIf({P}.Var('spec_pu_{k}').IsSet, 'SPEC_CHARTER_LOSES_{k}')]"
                         for k, _, charter in NAMES if charter and charter != n)
        out += (f' SPEC_EXCH_CARD_N_{n}: "{short[n - 1]}"\n'
                f' SPEC_EXCH_CARD_TT_{n}: "#header {known[n]}#!\\n{full[n - 1]}\\nLets us choose #v {only[n]}#! as specialities'
                f"[AddLocalizationIf({switching}, 'SPEC_CHARTER_CHANGE_{n}')]"
                f"[AddLocalizationIf(Not(GetScriptedGui('spec_sgui_{key}').IsValid(GuiScope.SetRoot({P}).End)), "
                f"'SPEC_CHARTER_WHY_{n}')]\"\n"
                f' SPEC_CHARTER_CHANGE_{n}: "\\n$SPEC_CHARTER_TRUST_CHANGE$' f'{losses}"\n'
                f' SPEC_CHARTER_WHY_{n}: "\\n\\n{sg(key, "BuildTooltip")}"\n'
                f" SPEC_CHARTER_BTN_{n}: \"[SelectLocalization({held(n)}, 'SPEC_CHARTER_HELD', 'SPEC_CHARTER_GRANT')]\"\n"
                f' SPEC_NAME_NEED_{n}: "{known[n]} only"\n'
                f' SPEC_NAME_NEEDS_{n}: "\\n#N Needs the {known[n]} charter#!"\n')
    trust = f"Divide_CFixedPoint({v('spec_centre_trust')}, {fx(CALM)})"
    out += (f' SPEC_CHARTER_TRUST_CHANGE: "Switching to this charter costs #N {-CHARTER_COST:.0%}#! [concept_spec_trust], '
            f'from #v [{trust}|%1]#! to #N [Multiply_CFixedPoint({trust}, {fx(1-CHARTER_COST)})|%1]#!."\n')
    out += "".join(f' SPEC_CHARTER_LOSES_{k}: "\\nWe lose the #v {title}#! speciality."\n' for k, title, charter in NAMES if charter)
    unit = {"price": "traded", "harbour": "trust", "companies": "strength", "floor": "levels", "sound": "months",
            "pockets": "income", "door": "treaties",
            "futures": "states", "lender": "countries", "railway": "levels"}
    for k, title, ch in NAMES:
        what, f = by[k]
        cur = "@money!" if f == "D" else ""  # the fields counted in money
        has = f"{P}.Var('spec_has_{k}').IsSet"
        pu = f"{P}.Var('spec_pu_{k}').IsSet"
        pw = v(f"spec_pw_{k}")
        live = f"GreaterThan_CFixedPoint({pw}, {fx(0.001)})"
        building = f"And({live}, Not({gt(pw, 0.999)}))"  # part-built or fading: the effects shown are at full strength
        ld = f"GetGlobalVariable('spec_ld_{k}')"
        ldv = f"GetGlobalVariable('spec_ldv_{k}').GetValue"
        sh = v(f"spec_sh_{k}")
        shl = f"{P}.Var('spec_shl_{k}').GetValueWithDefault({sh})"
        ours_v = _shown(k, v(f"spec_nv_{k}"))  # stored monthly (_shares)
        wsv = lambda p: f"GetGlobalVariable('spec_w_{k}{p}').GetCountry.MakeScope.ScriptValue('spec_name_{k}')"
        stat = f"[SelectLocalization({has}, 'SPEC_NAME_FX_{k}', 'SPEC_NAME_FXDIM_{k}')]"  # the build-up is in the row's tooltip
        flight = f"\\n#grey [concept_spec_capital_flight] received {FLIGHT_IF}#!" if "flight" in NAME_FX[k] else ""
        out += (f' SPEC_NAME_H_{k}: "#b {title}#!"\n'
                f' SPEC_NAME_FX_{k}: "{_fx_words(k, chr(92) + "n", FX_COLUMN)}"\n'
                f' SPEC_NAME_FXDIM_{k}: "$SPEC_NAME_FX_{k}$"\n'  # coloured as held: good green, bad red, neutral white
                # the effects always show, chartered or not (the user wants to see what a locked path gives);
                # the charter it needs is in the icon's tooltip
                + f' SPEC_NAME_STATUS_{k}: "{stat}"\n'
                # 2026-11-19: plain words, value first (was "+x% to our count on this path, of +25% at full strength, and building")
                # 2026-11-19: only the build-up (the +25% to its ranking went with ranking only pursuers)
                + f' SPEC_NAME_PW_TT_{k}: "\\n$TOOLTIP_DELIMITER$\\n#weak #v [{pw}|%0]#! of full strength, growing while it is our speciality#!"\n'
                f" SPEC_NAME_QTY_{k}: \"#b {cur}[{ours_v}|{f}]#!\"\n"
                f' SPEC_NAME_TALLY_{k}: "$SPEC_NAME_QTY_{k}$ #grey {unit[k]}#!'
                + (f"  @spec_blue_chip! #v [{v('spec_bc_n')}|0]#!" if k == "companies" else "") + '"\n'
                # the bar: the ranking. Our count and what our place gives are the tally's (SPEC_NAME_VAL_TT)
                + _rank_words(k, title, cur, f, unit[k], by[k][0], pu, ours_v)
                + f' SPEC_NAME_VAL_TT_{k}: "#header {title}: {cur}[{ours_v}|{f}] {unit[k]}#!\\n$TOOLTIP_DELIMITER$\\n'
                f'Ranked by {by[k][0]}.{RANK_COST}\\n$TOOLTIP_DELIMITER$\\n'
                f"[SelectLocalization({pu}, 'SPEC_NAME_VAL_PU_{k}', 'SPEC_NAME_VAL_NOT')]\"\n"
                f' SPEC_NAME_VAL_PU_{k}: "$SPEC_PURSUE_LV_{k}$\\n#weak What our place gives as a speciality, at full strength.#!"\n'
                + "".join(f" SPEC_NAME_FLAG_TT_{k}{p}: \"#header {('1st', '2nd', '3rd')[p - 1]} on {title}#!\\n"
                          f"[SelectLocalization(GetGlobalVariable('spec_w_{k}{p}').GetCountry.IsValid, 'SPEC_NAME_FW_{k}{p}', 'SPEC_NAME_NOONE')]"
                          f"\\n$TOOLTIP_DELIMITER$\\n{_mod_words(_pursue_fx(k, 4 - p), chr(92) + 'n')}\"\n"
                          f" SPEC_NAME_FW_{k}{p}: \"#v [GetGlobalVariable('spec_w_{k}{p}').GetCountry.GetNameNoFormatting]#! with "
                          f"#v {cur}[{_shown(k, wsv(p))}|{f}]#! #grey {unit[k]}#!\"\n"
                          for p in (1, 2, 3))
                + f' SPEC_NAME_ICON_TT_{k}: "$SPEC_NAME_TT_{k}$"\n'
                f' SPEC_PURSUE_STOP_TT_{k}: "#header Drop {title}#!\\nFrees its slot and ends its effects at once.'
                f"[AddLocalizationIf({P}.Var('spec_pu_lock_{k}').IsSet, 'SPEC_PURSUE_LEFT_{k}')]"
                f'\\n$TOOLTIP_DELIMITER$\\n{sg(f"pursue_stop_{k}", "BuildTooltip")}"\n'
                f' SPEC_PURSUE_LEFT_{k}: "\\n#N Locked for#! #v [{v(f"spec_pu_lock_{k}")}|0]#! #N more months#!"\n'
                f' SPEC_PURSUE_LV_{k}: "{_pursue_lv(k)}"\n'
                + _pursue_lv_keys(k) +
                # the row: what the path gives at each place, and while a slot is being filled whether it can be chosen
                f" SPEC_ROW_TT_{k}: \"$SPEC_NAME_TT_{k}$"
                f"[AddLocalizationIf(And(Not({pu}), GetVariableSystem.Exists('spec_pick_slot')), 'SPEC_ROW_CHOOSE_{k}')]\"\n"
                f" SPEC_ROW_CHOOSE_{k}: \"\\n$TOOLTIP_DELIMITER$\\n[SelectLocalization({sg(f'pursue_{k}', 'IsValid')[1:-1]}, "
                f"'SPEC_ROW_CLICK', 'SPEC_ROW_CANNOT')]\\n{sg(f'pursue_{k}', 'BuildTooltip')}\"\n"
                + "".join(f' SPEC_PURSUE_{d.upper()}_TT_{k}: "#header Move {w}#!\\n$SPEC_PURSUE_ORDER$\\n$TOOLTIP_DELIMITER$\\n'
                          f'{sg(f"pursue_{d}_{k}", "BuildTooltip")}"\n' for d, w in (("left", "Earlier"), ("right", "Later")))
                + ''
                f' SPEC_PURSUE_SLOT_{k}: "#v [{v(f"spec_pu_{k}")}|0]#!"\n'
                # the row: what the path is, in sections (2026-11-19): the charter it needs; its passive effects, held
                # whatever our place; what each place gives; its build-up; then its flavour as vanilla's #lore line
                f' SPEC_NAME_TT_{k}: "#header {title}#!'
                + (f"[AddLocalizationIf(Not({held(ch)}), 'SPEC_NAME_NEEDS_{ch}')]" if ch else "")
                + f'\\n$TOOLTIP_DELIMITER$\\n#b Passive Effects#!\\n{_fx_lines(k)}{flight}'
                f'\\n$TOOLTIP_DELIMITER$\\n#b Ranking Effects#!\\n'
                + "\\n".join(f"$SPEC_PURSUE_LV_{k}_{lv}_ON$" for lv in (3, 2, 1, 0))
                + f"[AddLocalizationIf({building}, 'SPEC_NAME_PW_TT_{k}')]\\n$TOOLTIP_DELIMITER$\\n#lore {FLAVOR[k]}#!" + '"\n')
    for ch in (1, 2, 3):
        out += f' spec_pursue_charter_tt_{ch}: "Our [concept_spec_exchange] is chartered as a #v {known[ch]}#!"\n'
    # value-first lines, as the calculator tooltips (2026-11-19: the sentences were too long)
    rule = (f"#v {PURSUE_BASE}#! slot at Provincial Standing, #v +1#! for each Standing above, up to #v {PURSUE_TOP}#!\\n"
            "Only Exchanges pursuing a path are ranked on it\\n"
            f"#N {PURSUE_COST - 1:+.0%}#! to our score in each path's ranking for every other speciality we hold\\n"
            f"#v {PURSUE_MONTHS}#! months to build up, its effects ending at once if dropped\\n"
            f"#v {PURSUE_LOCK}#! years before it can be dropped\\n"
            "#weak If our Standing falls, the last slots go first.#!")
    slots = f"{P}.ScriptValue('spec_pursue_slots')"
    out += (f' SPEC_PURSUE_RULE: "{rule}"\n SPEC_PURSUE_STOP: "Drop"\n'
            ' SPEC_NAME_VAL_NOT: "#weak Not ranked until we pursue it as a speciality.#!"\n'
            ' SPEC_RANK_IFPU: " #grey if we pursue it#!"\n SPEC_RANK_NEEDNAT: " #grey once we reach National Standing#!"\n'
            + "".join(f' SPEC_ORD_{n}: "#v {ORD[n - 1]}#!"\n' for n in (1, 2, 3)) +
            ' SPEC_NAME_BAR_RULE: "Each bar is how close we are to the leader, #P gold#! while we catch up and #N red#! while we fall behind."\n'
            ' SPEC_NAME_NOLEAD: "\\n$TOOLTIP_DELIMITER$\\n#grey No Exchange pursues this path yet#!"\n'
            ' SPEC_NAME_NOONE: "#grey No Exchange holds this place yet#!"\n'
            f' SPEC_H_NAMES_RIGHT: "#v [{v("spec_pursue_n")}|0]#! of #v [{slots}|0]#!"\n'
            ' SPEC_H_CONTEST: "Paths to Renown"\n'
            ' SPEC_H_CONTEST_TT: "#header Paths to Renown#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_NAME_RULE$ $SPEC_CONTEST_NOTE$\\n$SPEC_NAME_BAR_RULE$"\n'
            ' SPEC_CONTEST_PLACE_1: "#grey 1st#!"\n SPEC_CONTEST_PLACE_2: "#grey 2nd#!"\n SPEC_CONTEST_PLACE_3: "#grey 3rd#!"\n'            ' SPEC_CONTEST_NOTE: "The flags are this month\'s top three."\n'
            ' SPEC_CONTEST_COL_NAME: "#grey Path#!"\n'
            ' SPEC_CONTEST_COL_GIVES: "#grey Effects#!"\n'
            ' SPEC_SLOT_OPEN: "#grey Open#!"\n'
            ' SPEC_SLOT_OPEN_TT: "#header Open Speciality#!\\n$SPEC_PURSUE_RULE$\\n\\n#instruction Click Choose, then a Path to Renown in the list below#!"\n'
            + "".join(f' SPEC_SLOT_NUM_{i}: "#v {i}#!"\n' for i in (1, 2, 3, 4))
            # the card: two short lines that fit its width; the tooltip says it in full
            + "".join(f' SPEC_SLOT_LOCK_TT_{i}: "#header Locked Speciality#!\\nOpens when our [concept_spec_exchange] reaches #v {st}#! Standing."\n'
                      for i, st in ((1, "National"), (2, "International"), (3, "World Centre"))) +
            ' SPEC_SLOT_LOCK_1: "#grey Opens at#!\\n#v National#!"\n'
            ' SPEC_SLOT_LOCK_2: "#grey Opens at#!\\n#v International#!"\n'
            ' SPEC_SLOT_LOCK_3: "#grey Opens at#!\\n#v World Centre#!"\n'
            ' spec_pursue_current_tt: "Not already one of our specialities"\n'
            ' spec_pursue_room_tt: "We have a free speciality slot"\n'
            f' spec_pursue_locked_tt: "It was chosen at least #v {PURSUE_LOCK}#! years ago"\n'
            ' SPEC_SLOT_PICK: "Choose"\n SPEC_SLOT_PICK_CANCEL: "Cancel"\n'
            ' SPEC_ROW_CLICK: "#instruction Click to choose#!"\n SPEC_ROW_CANNOT: "#N Cannot be chosen#!"\n'
            ' SPEC_SLOT_PICK_TT: "#header Choose a Speciality#!\\n#instruction Click one of the lit Paths to Renown in the list below#!"\n'
            ' SPEC_SLOT_PICK_CANCEL_TT: "#header Cancel#!\\n#instruction Click to stop choosing a path for this slot#!"\n'
            ' SPEC_SLOT_LATER_TT: "#header Open Speciality#!\\nThe next speciality we choose goes in the first open slot.\\n\\n$SPEC_PURSUE_RULE$"\n'
            ' spec_pursue_first_tt: "Already first"\n spec_pursue_last_tt: "Already last"\n'
            ' SPEC_PURSUE_ORDER: "If our [concept_spec_exchange]\'s Standing falls, specialities are lost from the last slot first. '
            'Moving one earlier keeps it longer."\n'
            ' SPEC_PURSUE_SLOT_TT: "#header Speciality Slot#!\\nThis path is one of our specialities, in the slot this number shows. '
            'If our [concept_spec_exchange]\'s Standing falls, the last slots are dropped first."\n'
            + "".join(f' spec_pursue_{k}_{lv}: "{title}"\n spec_pursue_{k}_{lv}_desc: "The [concept_country]\'s [concept_spec_exchange] '
                      f'has made this its speciality, and stands {PLACE_WORDS[lv].lower()} on its path."\n' for k, title, _ in NAMES for lv in range(4))
            # the Standing-down toast (notify.py) names the specialities the fall cost (_pursue_fall)
            + ' SPEC_EXCH_DOWN_LOST: "' + "".join(f"[AddLocalizationIf(GetPlayer.MakeScope.Var('spec_pu_lost_{k}').IsSet, "
                                                  f"'SPEC_EXCH_LOST_{k}')]" for k, *_ in NAMES) + '"\n'
            + "".join(f' SPEC_EXCH_LOST_{k}: "\\n#v {title}#! is no longer one of its specialities."\n' for k, title, _ in NAMES))
    return out + (
        ' SPEC_NAME_RULE: "Every Exchange of #v National#! Standing or higher is ranked every month on each path it pursues."\n'
        ' SPEC_CHARTER_HELD: "Chartered"\n SPEC_CHARTER_GRANT: "Grant Charter"\n'
        # value-first lines, as the calculator tooltips (2026-11-19)
        f' SPEC_CHARTER_RULE: "#P Free#! to grant the first charter\\n'
        f'#N {-CHARTER_COST:.0%}#! [concept_spec_trust] to switch, and any speciality only the old charter allowed\\n'
        f'#v {CHARTER_LOCK}#! years before it can be changed again"\n'
        ' spec_charter_current_tt: "Our [concept_spec_exchange] does not already hold this charter"\n'
        f' spec_charter_locked_tt: "No charter has been granted in the last #v {CHARTER_LOCK}#! years"\n'
        ' SPEC_H_CHARTER: "Exchange Charter"\n'
        ' SPEC_H_CHARTER_TT: "#header Exchange Charter: $SPEC_H_KNOWN_RIGHT$#!\\n$TOOLTIP_DELIMITER$\\n$SPEC_EXCH_CARD_NOTE$\\n'
        '$TOOLTIP_DELIMITER$\\n$SPEC_CHARTER_RULE$"\n'
        ' SPEC_EXCH_CARD_NOTE: "Each charter gives its own bonus and opens Paths to Renown no other charter can pick."\n'
        ' SPEC_H_KNOWN_TT: "#header Specialities: $SPEC_H_NAMES_RIGHT$#!\\n$TOOLTIP_DELIMITER$\\nThe Paths to Renown our [concept_spec_exchange] pursues.\\n$TOOLTIP_DELIMITER$\\n$SPEC_PURSUE_RULE$"\n')


# Rival exchanges (rivals.py, design_rivals.md): named rivals each Exchange chooses, separate from vanilla rivalries
RIVAL_ON = NAMES_ON and tuning.get("EXCH_RIVAL_ON", 1)
RIVAL_VARS = __import__("rivals").STATE_VARS


def rival_block():
    return __import__("rivals").block()


def rival_button():
    return __import__("rivals").marker()


def _earn(t):
    """Once a year, in the ranking pass: the tally furthest past 1 names the Exchange; a tie, or none past 1, keeps
    the name it has (so names chosen in older saves stay until earned otherwise). A Share Market needs the Stock
    Exchange technology."""
    if not EARN:
        return ""
    pick = "".join(f"{t}\t{'if' if n == 1 else 'else_if'} = {{\n{t}\t\tlimit = {{\n{t}\t\t\t{me} >= 1\n"
                   + "".join(f"{t}\t\t\t{me} > {o}\n" for m, o in EARN_BY.items() if m != n)
                   + (f"{t}\t\t\t{SHARES}\n" if n == 3 else "")
                   + f"{t}\t\t\tNOT = {{ var:spec_exch_known ?= {n} }}\n{t}\t\t}}\n"
                   f"{t}\t\tset_variable = {{ name = spec_exch_known value = {n} }}\n"
                   # with the charters only the AI earns one here: it stops the specialities the new charter forbids
                   # (no trust cost or lock); the player's toast is for the earned names only
                   + (_charter_stop(n, t + "\t\t") if NAMES_ON else
                      f"{t}\t\tif = {{\n{t}\t\t\tlimit = {{ is_player = yes }}\n{t}\t\t\tpost_notification = spec_exch_known_new\n{t}\t\t}}\n")
                   + f"{t}\t}}\n" for n, me in EARN_BY.items())
    # with the charters, only a Provincial AI Exchange earns one here; _charter_balance hands out the rest
    ai = "is_player = no OR = { NOT = { has_variable = spec_exch_stand } var:spec_exch_stand < 1 } " if NAMES_ON else ""
    return (f"{t}if = {{\n{t}\tlimit = {{ {ai}NOT = {{ has_variable = spec_exch_tally }} }}\n"
            f"{t}\tset_variable = {{ name = spec_exch_tally days = 365 }}\n{pick}{t}}}\n")


def earned(tally, known):
    """Python model of _earn for the self-check: tally {n: count / mark}."""
    best = max(tally, key=tally.get)
    return best if tally[best] >= 1 and all(tally[best] > x for m, x in tally.items() if m != best) else known


def _if_pledged(how, var="spec_pledge"):
    return f"\tif = {{\n\t\tlimit = {{ has_variable = {var} }}\n\t\t{how}\n\t}}\n"


def _panic_cut():
    """Trust lost as a panic starts, a share: by leverage before the banks call in their loans (spec_lev_last, this
    month's), less for a panic caught from abroad or under the pledge."""
    stress = (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_lev_last }}\n\t\tvalue = var:spec_lev_last\n\t\tsubtract = {leverage.SAFE}\n"
              f"\t\tdivide = {leverage.RUIN - leverage.SAFE}\n\t\tmin = 0\n\t\tmax = 1\n\t\tmultiply = {PANIC_CUT[1]:g}\n\t\tadd = {PANIC_CUT[0]:g}\n\t}}\n"
              if leverage.ON else "")
    return (f"\nspec_exch_panic_cut = {{\n\tvalue = {PANIC_CUT[0] if leverage.ON else 0.5:g}\n{stress}"
            + _if_pledged(f"multiply = {PLEDGE_PANIC:g}") * bool(PLEDGE_ON) + _if_pledged(f"multiply = {CAUGHT_CUT:g}", "spec_caught") + "}\n")


def _panic_cut_model(lev, pledged=False, caught=False):
    """_panic_cut in Python, for the self-check."""
    s = min(max((lev - leverage.SAFE) / (leverage.RUIN - leverage.SAFE), 0), 1)
    return (PANIC_CUT[0] + PANIC_CUT[1] * s) * (PLEDGE_PANIC if pledged else 1) * (CAUGHT_CUT if caught else 1)


def _pledge_values():
    return ("\n# Pledge to Rescue the Banks (centres.py)\n"
            f"spec_pledge_cost = {{\n\tvalue = 1\n{_if_pledged(f'value = {PLEDGE_SHARE:g}')}}}\n"
            # telemetry: 0 none, 1 pledged, 2 pledged and giving notice
            f"spec_log_pledge = {{\n\tvalue = 0\n{_if_pledged('add = 1')}{_if_pledged('add = 1', 'spec_pledge_leave')}}}\n"
            f"spec_log_pbroke = {{\n\tvalue = 0\n{_if_pledged('value = var:spec_pledge_broken', 'spec_pledge_broken')}}}\n")


def _pledge_zero(t):
    import bluechips  # a broken pledge takes all trust: logged as the other changes are (bluechips.log_trust)
    return bluechips.log_trust(f"{t}set_variable = {{ name = spec_centre_trust value = 0 }}\n", "pledge", t)


def _pledge_month(t):
    """The pledge each month: a default breaks it; notice runs out; the AI makes it or gives notice."""
    if not PLEDGE_ON:
        return ""
    return f"""{t}if = {{
{t}	limit = {{
{t}		has_variable = spec_pledge
{t}		in_default = yes
{t}	}}
{_pledge_zero(t + chr(9))}{t}	spec_cool_conf = {{ AMOUNT = {PLEDGE_BREAK["conf"]} }}
{t}	add_modifier = {{ name = spec_pledge_broken months = {PLEDGE_BROKEN_MONTHS} }}
{t}	set_variable = {{ name = spec_pledge_broken value = {{ value = spec_log_pbroke add = 1 }} }}
{t}	remove_variable = spec_pledge
{t}	if = {{
{t}		limit = {{ has_variable = spec_pledge_leave }}
{t}		remove_variable = spec_pledge_leave
{t}	}}
{t}	if = {{
{t}		limit = {{ is_player = yes }}
{t}		post_notification = spec_pledge_broken
{t}	}}
{t}}}
{t}else_if = {{
{t}	limit = {{ has_variable = spec_pledge_leave }}
{t}	change_variable = {{ name = spec_pledge_leave add = -1 }}
{t}	if = {{
{t}		limit = {{ var:spec_pledge_leave <= 0 }}
{t}		remove_variable = spec_pledge_leave
{t}		remove_variable = spec_pledge
{t}	}}
{t}}}
{t}if = {{
{t}	limit = {{ is_player = no }}
{t}	if = {{
{t}		limit = {{
{t}			spec_can_pledge = yes
{t}			in_default = no
{t}			scaled_debt < 0.3
{t}			gold_reserves >= spec_rescue_cost
{t}		}}
{t}		spec_pledge_make = yes
{t}	}}
{t}	else_if = {{
{t}		limit = {{
{t}			spec_can_pledge_leave = yes
{t}			OR = {{
{t}				scaled_debt > 0.4
{t}				gold_reserves < spec_rescue_cost
{t}			}}
{t}		}}
{t}		spec_pledge_withdraw = yes
{t}	}}
{t}}}
"""


def _trust(t="\t\t\t"):
    """In the ranking pass, before the quiet months are counted: trust starts from them, then moves once a month
    outside a panic by the Lending Standards (always up without the credit cycle)."""
    if not ON:
        return ""
    u = t + "\t\t"
    # TRUST_BY_LAX: Strict +2, Cautious +1.5, Sound +1, Lax nothing, Reckless -1; no gain while Bad Debts drain it (_crunch)
    calm = "NOT = { has_variable = spec_crunch } " if CRUNCH else ""
    lose = _record_trust(_lose(round(-TRUST_BY_LAX[4] * TRUST_MONTH, 4), u), "lending", u)
    gain = _record_trust(_gain(TRUST_MONTH, u), "lending", u)
    # TRUST_BY_LAX: Strict and Cautious gain more than Sound, each its own branch
    v_ = u + "\t"
    graded = (f"{u}if = {{\n{v_}limit = {{ has_variable = spec_lax var:spec_lax < {cycle.LAX_CUTS[0]:g} }}\n"
              + _record_trust(_gain(round(TRUST_BY_LAX[0] * TRUST_MONTH, 4), v_ + "\t"), "lending", v_ + "\t") + f"{u}}}\n"
              f"{u}else_if = {{\n{v_}limit = {{ has_variable = spec_lax var:spec_lax < {cycle.LAX_CUTS[1]:g} }}\n"
              + _record_trust(_gain(round(TRUST_BY_LAX[1] * TRUST_MONTH, 4), v_ + "\t"), "lending", v_ + "\t") + f"{u}}}\n"
              f"{u}else = {{\n" + _record_trust(_gain(round(TRUST_BY_LAX[2] * TRUST_MONTH, 4), v_), "lending", v_) + f"{u}}}\n")
    month = (f"{t}\tif = {{\n{u}limit = {{ has_variable = spec_lax var:spec_lax >= {cycle.LAX_CUTS[3]:g} }}\n{lose}{t}\t}}\n"
             f"{t}\telse_if = {{\n{u}limit = {{ {calm}OR = {{ NOT = {{ has_variable = spec_lax }} var:spec_lax < {cycle.LAX_CUTS[2]:g} }} }}\n"
             f"{graded}{SOUND(u)}{t}\t}}\n"
             if cycle.ON else f"{t}\tif = {{\n{u}limit = {{ {calm}always = yes }}\n{gain}{SOUND(u)}{t}\t}}\n")
    # a new Exchange starts Respected (half of CALM), or from its quiet months if more
    return (f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_centre_trust }} }}\n"
            f"{t}\tset_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_calm min = {CALM / 2:g} max = {CALM} }} }}\n{t}}}\n"
            + _trust_review(t)
            + f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_panic }} }}\n{month}{t}}}\n"
            + levers.TR("pledge", t) + _pledge_month(t) + levers.TR("trustdone", t) + _pursue_month(t) + _trust_mods(t) + _shares(t) + _seat(t))


SEAT_MARGIN = tuning.get("EXCH_SEAT_MARGIN", 2)  # Financial District levels another state needs beyond the seat's


def _seat(t):
    """Monthly: the Exchange's seat (var:spec_exch_seat), the state it is named after, is the capital until another
    state leads in Financial District levels by SEAT_MARGIN, checked once a year so the name does not flip; a seat
    the country no longer holds goes back to its owned capital at once. A dead country has no Exchange seat."""
    outer, t = t, t + "\t"
    u, w = t + "\t", t + "\t\t"
    # A transferred/merged state can leave a set variable whose object no longer exists. Clear it even if this
    # country temporarily has no capital, and never compare owners until the saved state's owner resolves.
    drop = f"remove_variable = spec_exch_seat\n{{indent}}remove_variable = spec_exch_seat_t\n"
    living = (f"{t}if = {{\n{u}limit = {{ exists = var:spec_exch_seat.owner }}\n"
            f"{u}if = {{\n{w}limit = {{ NOT = {{ this = var:spec_exch_seat.owner }} }}\n"
            f"{w}{drop.format(indent=w)}{u}}}\n{t}}}\n"
            f"{t}else = {{\n{u}{drop.format(indent=u)}{t}}}\n"
            f"{t}if = {{\n{u}limit = {{\n{w}exists = capital.owner\n{w}NOT = {{ has_variable = spec_exch_seat }}\n{u}}}\n"
            f"{u}if = {{\n{w}limit = {{ this = capital.owner }}\n"
            f"{w}set_variable = {{ name = spec_exch_seat value = capital }}\n{u}}}\n{t}}}\n"
            f"{t}if = {{\n{u}limit = {{\n{w}exists = var:spec_exch_seat\n{w}NOT = {{ has_variable = spec_exch_seat_t }}\n{u}}}\n"
            f"{u}set_variable = {{ name = spec_exch_seat_t days = 365 }}\n"
            f"{u}var:spec_exch_seat = {{\n{w}save_temporary_scope_as = spec_seat_old\n"
            f"{w}set_variable = {{ name = spec_seat_need value = {{ value = spec_seat_fd add = {SEAT_MARGIN} }} }}\n{u}}}\n"
            f"{u}ordered_scope_state = {{\n{w}limit = {{\n{w}\thas_building = building_financial_district\n"
            f"{w}\tspec_seat_fd >= scope:spec_seat_old.var:spec_seat_need\n{w}}}\n"
            # Assign only inside a successful search. A saved candidate scope survives across the countries in
            # this ranking pass; reading it after an empty search could otherwise borrow another country's seat.
            f"{w}order_by = spec_seat_fd\n{w}position = 0\n{w}check_range_bounds = no\n"
            f"{w}owner = {{\n{w}\tset_variable = {{ name = spec_exch_seat value = prev }}\n{w}}}\n{u}}}\n"
            f"{u}scope:spec_seat_old = {{\n{w}remove_variable = spec_seat_need\n{u}}}\n"
            f"{t}}}\n")
    # Annexed countries can retain a capital target belonging to their annexer for the rest of this execution.
    # Existence alone is therefore insufficient: stop before any fallback can republish that foreign capital.
    return (f"{outer}if = {{\n{t}limit = {{ is_country_alive = no }}\n{t}{drop.format(indent=t)}{outer}}}\n"
            f"{outer}else = {{\n{living}{outer}}}\n")


def seat(levels, seat_at):
    """Python model of _seat's yearly check for the self-check: {state: levels} -> the new seat."""
    best = max(levels, key=levels.get)
    return best if levels[best] >= levels.get(seat_at, 0) + SEAT_MARGIN else seat_at


def _standing(t="\t"):
    """In the ranking pass, while spec_centre_new still holds the places: each market's Standing, the National
    modifier, and the choice of what it is known for when it first reaches a Standing."""
    if not ON:
        return ""
    stand = lambda n: f"set_variable = {{ name = spec_exch_stand value = {n} }}"
    return f"""{t}# the Exchange's Standing (centres.py)
{t}every_country = {{
{t}	limit = {{
{t}		OR = {{
{t}			has_variable = spec_centre_score
{t}			has_variable = spec_exch_stand
{t}		}}
{t}	}}
{t}	if = {{
{t}		limit = {{ NOT = {{ has_variable = spec_centre_score }} }}
{t}		remove_variable = spec_exch_stand
{_names_drop(t + chr(9) * 2)}{t}		if = {{
{t}			limit = {{ has_modifier = spec_exch_national }}
{t}			remove_modifier = spec_exch_national
{t}		}}
{t}		if = {{
{t}			limit = {{ has_modifier = spec_exch_world }}
{t}			remove_modifier = spec_exch_world
{t}		}}
{f"{t}{chr(9) * 2}remove_modifier = spec_exch_industry{chr(10)}" if LINKS and LINK_IND else ""}{t}	}}
{t}	else = {{
{t}		set_local_variable = {{ name = spec_exch_was value = 0 }}
{t}		if = {{
{t}			limit = {{ has_variable = spec_exch_stand }}
{t}			set_local_variable = {{ name = spec_exch_was value = var:spec_exch_stand }}
{t}		}}
{t}		if = {{
{t}			limit = {{
{t}				has_variable = spec_centre_new
{t}				var:spec_centre_new <= {WORLD_PLACES}
{t}				{GATE}
{t}			}}
{t}			{stand(3)}
{t}		}}
{t}		else_if = {{
{t}			limit = {{
{t}				OR = {{
{t}					has_variable = spec_centre_new
{t}					has_variable = spec_exch_hold  # ponytail: a year's grace, so places 5 and 6 swapping does not flip it monthly
{t}					has_variable = spec_xs_regtop
{t}				}}
{t}				{INTL_GATE}
{t}			}}
{t}			{stand(2)}
{t}		}}
{t}		else_if = {{
{t}			limit = {{
{t}				OR = {{
{t}					has_variable = spec_centre_new
{t}					var:spec_centre_score >= {NATIONAL:g}
{t}					var:spec_xs_regshare >= {REG_NATIONAL:g}
{t}					AND = {{
{t}						has_variable = spec_exch_stand
{t}						var:spec_exch_stand >= 1
{t}						OR = {{
{t}							var:spec_centre_score >= {NATIONAL - HOLD:g}
{t}							var:spec_xs_regshare >= {REG_NATIONAL - REG_HOLD:g}
{t}						}}
{t}					}}
{t}				}}
{t}			}}
{t}			{stand(1)}
{t}		}}
{t}		else = {{
{t}			{stand(0)}
{t}		}}
{levers.TR("crunch", t)}{_crunch(t + chr(9) * 2)}{levers.TR("crunchdone", t)}{t}		if = {{
{t}			limit = {{
{t}				OR = {{
{t}					has_variable = spec_centre_new
{t}					has_variable = spec_xs_regtop
{t}				}}
{t}			}}
{t}			set_variable = {{ name = spec_exch_hold days = 365 }}
{t}		}}
{t}		if = {{
{t}			limit = {{
{t}				var:spec_exch_stand >= 1
{t}				NOT = {{ has_variable = spec_centre_new }}  # a listed place has its own prestige
{t}				NOT = {{ has_modifier = spec_exch_national }}
{t}			}}
{t}			add_modifier = {{ name = spec_exch_national }}
{t}		}}
{t}		if = {{
{t}			limit = {{
{t}				var:spec_exch_stand = 3
{t}				NOT = {{ has_modifier = spec_exch_world }}
{t}			}}
{t}			add_modifier = {{ name = spec_exch_world }}
{t}		}}
{t}		else_if = {{
{t}			limit = {{
{t}				var:spec_exch_stand < 3
{t}				has_modifier = spec_exch_world
{t}			}}
{t}			remove_modifier = spec_exch_world
{t}		}}
{t}		else_if = {{
{t}			limit = {{
{t}				OR = {{
{t}					var:spec_exch_stand = 0
{t}					has_variable = spec_centre_new
{t}				}}
{t}				has_modifier = spec_exch_national
{t}			}}
{t}			remove_modifier = spec_exch_national
{t}		}}
{"" if EARN else f'''{t}		if = {{
{t}			limit = {{
{t}				var:spec_exch_stand >= 1
{t}				OR = {{
{t}					NOT = {{ has_variable = spec_exch_best }}
{t}					var:spec_exch_stand > var:spec_exch_best
{t}				}}
{t}			}}
{t}			set_variable = {{ name = spec_exch_best value = var:spec_exch_stand }}
{t}			trigger_event = {{ id = spec_exchange.1 popup = yes }}
{t}		}}
{t}		# a toast when the Standing moves, unless the event above already says so
'''}{t}		{"if" if EARN else "else_if"} = {{
{t}			limit = {{
{t}				is_player = yes
{t}				local_var:spec_exch_was < var:spec_exch_stand
{t}			}}
{t}			post_notification = spec_exch_up
{t}		}}
{t}		else_if = {{
{t}			limit = {{
{t}				is_player = yes
{t}				local_var:spec_exch_was > var:spec_exch_stand
{t}			}}
{_pursue_fall(t + chr(9) * 3)}{t}			post_notification = spec_exch_down
{t}		}}
{levers.TR("earn", t)}{_earn(t + chr(9) * 2)}{levers.TR("earndone", t)}{_industry(t + chr(9) * 2)}{t}	}}
{t}}}
"""


def _crunch(t):
    """Under Bad Debts the Standing cannot rise above last month's, and trust falls each month."""
    if not CRUNCH:
        return ""
    loss = _record_trust(_lose(LINK_CRUNCH, t + "\t"), "debts", t + "\t")
    return (f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_crunch }}\n{loss}"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_exch_stand > local_var:spec_exch_was }}\n"
            f"{t}\t\tset_variable = {{ name = spec_exch_stand value = local_var:spec_exch_was }}\n{t}\t}}\n{t}}}\n")


def _industry(t):
    """The Industrialists' strength by Standing: re-applied when the Standing moves (a modifier's multiplier is fixed)."""
    if not (LINKS and LINK_IND):
        return ""
    return (f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tOR = {{\n{t}\t\t\tNOT = {{ local_var:spec_exch_was = var:spec_exch_stand }}\n"
            f"{t}\t\t\tNOT = {{ has_modifier = spec_exch_industry }}\n{t}\t\t}}\n{t}\t}}\n"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ has_modifier = spec_exch_industry }}\n{t}\t\tremove_modifier = spec_exch_industry\n{t}\t}}\n"
            f"{t}\tif = {{\n{t}\t\tlimit = {{ var:spec_exch_stand >= 1 }}\n"
            f"{t}\t\tadd_modifier = {{ name = spec_exch_industry multiplier = var:spec_exch_stand }}\n{t}\t}}\n{t}}}\n")


def _note(key, n):
    """A Financial Centre toast for the player; with the Exchange its Standing toasts say it instead."""
    t = "\t" * n
    return "" if ON else f"{t}if = {{\n{t}\tlimit = {{ is_player = yes }}\n{t}\tpost_notification = {key}\n{t}}}\n"


def _exch_clear():
    """Leaving the market economy clears the Exchange immediately; the ranking pass also repairs older saves.
    Permanent modifiers and the whole local state go together, so switching back cannot revive half an Exchange.
    Timed punishment for a broken pledge remains until it expires. The world's list refreshes at its next ranking."""
    mods = ([f"spec_trust_{i}" for i, f in enumerate(TRUST_FX) if f] + ["spec_exch_national", "spec_exch_world", "spec_financial_centre"]
            + (["spec_exch_industry"] if LINKS and LINK_IND else [])
            + ([f"spec_pursue_{k}_{lv}" for k, *_ in NAMES for lv in range(4)] if NAMES_ON else []))
    keep = (["spec_centre_score", "spec_centre_rank", "spec_centre_new", "spec_centre_also", "spec_centre_pos", "spec_exch_stand",
             "spec_centre_trust", "spec_centre_calm", "spec_centre_yrs", "spec_exch_known", "spec_exch_tally",
             "spec_exch_sound", "spec_exch_hold", "spec_charter_lock", "spec_exch_seat", "spec_exch_seat_t", "spec_pledge",
             "spec_pledge_leave", "spec_xs_inc", "spec_xs_raw", "spec_xs_reg", "spec_xs_regtop", "spec_xs_regshare", "spec_xs_trust_v"]
            + TRUST_RECORD + (["spec_exch_best"] if not EARN else [])  # current builds never set the legacy standing-choice variable
            + [f"spec_xs_{k}_v" for k in XS_KEEP + ["own", "reach", "size", "ratio", "wealth"]]
            + (["spec_pursue_n", "spec_pw_sum"] + [f"spec_{p}_{k}" for k, *_ in NAMES
                                                   for p in ("pu", "pw", "has", "pu_lock", "pu_lost", "lead", "sh", "shl")] if NAMES_ON else []))
    return ("spec_exch_clear = {\n" + "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m in mods)
            + "".join(f"\tremove_variable = {x}\n" for x in keep) + "}\n\n")


def effects():
    # A bounded iteration visits existing countries once. `position` beyond the list logs an error even with
    # check_range_bounds=no, then repeats its final country; that is unsafe in near-unified or test worlds.
    old_slots = "".join(f"\t\t\tif = {{\n\t\t\t\tlimit = {{ global_var:spec_centre_next = {n} }}\n"
                        f"\t\t\t\tset_global_variable = {{ name = spec_centre_{n} value = this }}\n\t\t\t}}\n"
                        for n in range(1, PLACES + 1)) if not ON else ""
    listed = f"""		set_global_variable = {{ name = spec_centre_next value = 1 }}
		ordered_country = {{
			limit = {{
				has_variable = spec_centre_score
				var:spec_centre_score > 0
			}}
			order_by = spec_centre_order
			max = {PLACES}
			check_range_bounds = no
			set_variable = {{ name = spec_centre_new value = global_var:spec_centre_next }}
{old_slots}			change_global_variable = {{ name = spec_centre_next add = 1 }}
		}}
		remove_global_variable = spec_centre_next
"""
    # with the Exchange the World tab lists every market of National Standing or above, numbered among themselves (the
    # top PLACES are always National, so their numbers are their places)
    # each takes the best not yet listed: a position past the end would repeat the last market, as check_range_bounds = no
    # clamps it, while the first of an empty list is nothing
    shown = "".join(f"""	ordered_country = {{
		limit = {{
			has_variable = spec_exch_stand
			var:spec_exch_stand >= 1
			NOT = {{ has_variable = spec_centre_pos }}
		}}
		order_by = spec_centre_order
		position = 0
		check_range_bounds = no
		set_variable = spec_centre_pos
{"		set_variable = spec_centre_also" + chr(10) if n > PLACES else ""}		set_global_variable = {{ name = spec_centre_{n} value = this }}
	}}
""" for n in range(1, SHOWN + 1)) + """	every_country = {
		limit = { has_variable = spec_centre_pos }
		remove_variable = spec_centre_pos
	}
""" if ON else ""
    unlist = "".join(f"\tif = {{\n\t\tlimit = {{ has_global_variable = spec_centre_{n} }}\n"
                     f"\t\tremove_global_variable = spec_centre_{n}\n\t}}\n" for n in range(1, SHOWN + 1))
    off = "if = {\n\tlimit = { has_modifier = spec_financial_centre }\n\tremove_modifier = spec_financial_centre\n}\n"
    pre = _exch_clear() if ON else ""
    if PLEDGE_ON:
        pre += ("spec_pledge_make = {\n\tset_variable = spec_pledge\n}\n\n"
                  f"spec_pledge_withdraw = {{\n\tset_variable = {{ name = spec_pledge_leave value = {PLEDGE_NOTICE} }}\n}}\n\n")
    if NAMES_ON:
        pre += _charter_effects()
    return pre + f"""# the Financial Centres (centres.py): once a month, for the whole world
spec_rank_centres = {{
{_xs_world() if ON else ''}	every_country = {{
		if = {{
			limit = {{ has_variable = spec_conf }}
			if = {{
				limit = {{ NOT = {{ has_variable = spec_centre_calm }} }}
				set_variable = {{ name = spec_centre_calm value = 0 }}
				if = {{
					limit = {{ has_variable = spec_calm }}
					set_variable = {{ name = spec_centre_calm value = var:spec_calm }}
				}}
			}}
{_trust()}			if = {{
				limit = {{ has_variable = spec_panic }}
				set_variable = {{ name = spec_centre_calm value = 0 }}
			}}
			else = {{
				change_variable = {{ name = spec_centre_calm add = 1 }}
			}}
			set_variable = {{ name = spec_centre_yrs value = {{ value = var:spec_centre_calm divide = 12 floor = yes }} }}
{_xs_prep(chr(9) * 3) if ON else ''}			set_variable = {{ name = spec_centre_score value = spec_centre_size }}
{_parts_keep(chr(9) * 3) if ON else ''}		}}
		else_if = {{
			limit = {{
				OR = {{
					has_variable = spec_centre_score
					has_variable = spec_centre_trust
					has_variable = spec_exch_seat  # spec_shut_down already took the two above; set monthly for every Exchange
				}}
			}}
			remove_variable = spec_centre_score
{"			spec_exch_clear = yes" + chr(10) if ON else ""}		}}
	}}
{TOP}{unlist}{ALSO_CLEAR}	if = {{
		limit = {{ global_var:spec_centre_top > 0 }}
		every_country = {{
			limit = {{ has_variable = spec_centre_score }}
			set_variable = {{ name = spec_centre_score value = {{ value = var:spec_centre_score multiply = 100 divide = global_var:spec_centre_top }} }}
		}}
{listed}	}}
	remove_global_variable = spec_centre_top
{_regions() if ON else ''}{_standing()}{_names()}{__import__("rivals").pass_() if RIVAL_ON else ""}{__import__("bluechips").pass_()}{COUNTS}{shown}	# ponytail: a market hovering between the last place and the next gets a toast each time it crosses; hold a place
	# for a few months if that proves noisy
	every_country = {{
		limit = {{
			OR = {{
				has_variable = spec_centre_rank
				has_variable = spec_centre_new
			}}
		}}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_centre_new }} }}
{ind(off, 3)}			remove_variable = spec_centre_rank
{_note("spec_centre_lost", 3)}		}}
		else = {{
			if = {{
				limit = {{ NOT = {{ has_variable = spec_centre_rank }} }}
				set_variable = {{ name = spec_centre_rank value = 0 }}
{_note("spec_centre_gained", 4)}			}}
			if = {{
				limit = {{ NOT = {{ var:spec_centre_rank = var:spec_centre_new }} }}
{ind(off, 4)}				add_modifier = {{ name = spec_financial_centre multiplier = spec_centre_mult }}
				set_variable = {{ name = spec_centre_rank value = var:spec_centre_new }}
			}}
			remove_variable = spec_centre_new
		}}
	}}
}}
"""


# the yardstick the scores are scaled to: the leader's, or with the Exchange the average of the top three
_top = lambda n, set_: f"""	ordered_country = {{
		limit = {{ has_variable = spec_centre_score }}
		order_by = spec_centre_order
		position = {n}
		check_range_bounds = no
{set_}	}}
"""
TOP = ("\tset_global_variable = { name = spec_centre_top value = 0 }\n" + (
    "\tset_global_variable = { name = spec_xs_topn value = 0 }\n"
    # A single capped iteration counts each available market once, even when fewer than three exist.
    + "\tordered_country = {\n\t\tlimit = { has_variable = spec_centre_score }\n"
      "\t\torder_by = spec_centre_order\n\t\tmax = 3\n\t\tcheck_range_bounds = no\n"
      "\t\tchange_global_variable = { name = spec_centre_top add = var:spec_centre_score }\n"
      "\t\tchange_global_variable = { name = spec_xs_topn add = 1 }\n\t}\n"
    + "\tif = {\n\t\tlimit = { global_var:spec_xs_topn > 0 }\n\t\tset_global_variable = { name = spec_centre_top value = "
      "{ value = global_var:spec_centre_top divide = global_var:spec_xs_topn } }\n\t}\n"
    if ON else _top(0, "\t\tset_global_variable = { name = spec_centre_top value = var:spec_centre_score }\n")))


ON_ACTIONS = """on_monthly_pulse = {
	on_actions = { spec_centre_pulse }
}

spec_centre_pulse = {
	effect = { spec_rank_centres = yes }
}
"""

MODIFIER = f"""spec_financial_centre = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_prestige_mult = {STEP:g}
}}
""" + (f"""
spec_exch_national = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_prestige_mult = {PRESTIGE:g}
}}
spec_exch_world = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
{''.join(f'{chr(9)}{m} = {x:g}{chr(10)}' for m, x in WORLD_FX)}}}
""" if ON else "") + (f"""
spec_pledge_broken = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_legitimacy_base_add = {-PLEDGE_BREAK["legit"]}
}}
""" if PLEDGE_ON else "") + (f"""
spec_exch_industry = {{
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	interest_group_ig_industrialists_pol_str_mult = {LINK_IND:g}
}}
""" if LINKS and LINK_IND else "") + _effect_mods()

KNOWN_PICS = {"west": "europenorthamerica_capitalists_meeting", "mideast": "middleeast_upperclass_party"}  # as Sound Finance


def events():
    option = lambda n, letter: f"""	option = {{
		name = spec_exchange.1.{letter}
{'		default_option = yes' + chr(10) if n == 1 else ''}		custom_tooltip = {{
			text = spec_exchange_known_{n}_tt
			set_variable = {{ name = spec_exch_known value = {n} }}
		}}
		ai_chance = {{
			base = 1
		}}
	}}
"""
    return f"""namespace = spec_exchange

# the Exchange reaches a Standing it has not held before: what it is to be known for (centres.py). The AI picks at random
spec_exchange.1 = {{
	type = country_event
	placement = root
	title = spec_exchange.1.t
	desc = {{
		first_valid = {{
			triggered_desc = {{
				desc = spec_exchange.1.d3
				trigger = {{ var:spec_exch_stand ?= 3 }}
			}}
			triggered_desc = {{
				desc = spec_exchange.1.d2
				trigger = {{ var:spec_exch_stand ?= 2 }}
			}}
			triggered_desc = {{
				desc = spec_exchange.1.d1
				trigger = {{ always = yes }}
			}}
		}}
	}}
	flavor = spec_exchange.1.f
	duration = 3
{stories.pictures(KNOWN_PICS)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

{option(1, 'a')}{option(2, 'b')}{option(3, 'c')}}}
"""


def triggers():
    """As generate.triggers' Credit Policy ones: the reasons a button cannot be used, in its tooltip."""
    return ("" if not PLEDGE_ON else f"""
spec_can_pledge = {{
	has_technology_researched = banking
	custom_tooltip = {{
		text = spec_pledge_stand_tt
		AND = {{
			has_variable = spec_exch_stand
			var:spec_exch_stand >= 1
		}}
	}}
	custom_tooltip = {{
		text = spec_pledge_debt_tt
		scaled_debt <= {PLEDGE_DEBT:g}
	}}
	custom_tooltip = {{
		text = spec_pledge_panic_tt
		NOT = {{ has_variable = spec_panic }}
	}}
	custom_tooltip = {{
		text = spec_pledge_made_tt
		NOT = {{ has_variable = spec_pledge }}
	}}
}}

spec_can_pledge_leave = {{
	custom_tooltip = {{
		text = spec_pledge_none_tt
		has_variable = spec_pledge
	}}
	custom_tooltip = {{
		text = spec_pledge_leaving_tt
		NOT = {{ has_variable = spec_pledge_leave }}
	}}
}}
""") + (_charter_triggers() if NAMES_ON else "")


def sguis():
    return "".join(f"""
spec_sgui_{k} = {{
	scope = country
	is_valid = {{ spec_can_{k} = yes }}
	effect = {{ spec_{e} = yes }}
}}
""" for k, e in [x for x in (("pledge", "pledge_make"), ("pledge_leave", "pledge_withdraw")) if PLEDGE_ON]
              + [(f"charter_{n}", f"charter_to_{n}") for n in (1, 2, 3) if NAMES_ON]
              + [(f"pursue_{k}", f"pursue_to_{k}") for k, *_ in NAMES if NAMES_ON]
              + [(f"pursue_stop_{k}", f"pursue_stop_{k}") for k, *_ in NAMES if NAMES_ON]
              + [(f"pursue_{d}_{k}", f"pursue_{d}_{k}") for k, *_ in NAMES for d in ("left", "right") if NAMES_ON]
              )


# the toast when a pledge is broken, as notify.messages()
PLEDGE_MESSAGE = """
spec_pledge_broken = {
	type = country
	group = "spec_exchange_notification_group"

	texture = "gfx/interface/icons/notification_icons/company.dds"

	notification_type = toast
	color = bad
}
""" if PLEDGE_ON else ""


BUTTONS = PLEDGE_ON or NAMES_ON or RIVAL_ON  # the Exchange's buttons: triggers and scripted guis


def build(write):
    write("common/script_values/spec_centre_values.txt", values())
    write("common/scripted_effects/spec_centre_effects.txt", effects())
    write("common/on_actions/spec_centre_on_actions.txt", ON_ACTIONS)
    write("common/static_modifiers/spec_centre_modifiers.txt", MODIFIER)
    if ON and not EARN:
        write("events/spec_exchange_events.txt", events())
    if BUTTONS:
        write("common/scripted_triggers/spec_centre_triggers.txt", triggers())
        write("common/scripted_guis/spec_centre_sguis.txt", sguis())
    if PLEDGE_ON:
        write("common/messages/spec_centre_messages.txt", PLEDGE_MESSAGE)
    if RIVAL_ON:
        __import__("rivals").build(write)
    __import__("bluechips").build(write)


def text(x, w, key, align="left"):
    return (f"textbox = {{\n\tposition = {{ {x} 0 }}\n\tsize = {{ {w} {ROW_H} }}\n\talign = {align}|nobaseline\n"
            f"\telide = right\n\ttext = \"{key}\"\n}}\n")


RANKED = f"{SLOT(1)}.IsSet"
# with the Exchange the World tab lists this many markets, by Standing; the Financial Centre places stay PLACES
SHOWN = 40 if ON else PLACES  # ponytail: rows for 40 National markets; more go unlisted, raise if a game reaches it
# our market has a score and is not one of the listed: it gets a row of its own
UNPLACED = (f"And({RANKED}, And({P}.Var('spec_centre_score').IsSet, "
            f"Not(Or({P}.Var('spec_centre_rank').IsSet, {P}.Var('spec_centre_also').IsSet))))")
# the third column: with the Exchange its trust (the Standing is the tier the row sits in)
THIRD = "TRUST" if ON else "CALM"
# the columns: #, flag and name | score | rival | specialities | trust (heads carry a 10 margin each side)
HEADS = ([(0, 40, "gfx/interface/buttons/sort_button_icons/sort_icon_rank.dds", "center", "SPEC_CENTRE_COL_RANK_TT"), (40, 176, "SPEC_CENTRE_COL_NAME", "left", False),  # the place numbers' own head
          (216, 80, "SPEC_CENTRE_COL_SCORE", "right", True)]
         + ([(296, 80, "SPEC_CENTRE_COL_RIVAL", "center", True)] if RIVAL_ON else [])
         + ([(376, 100, "SPEC_CENTRE_COL_KNOWN", "center", True)] if NAMES_ON else [])
         + [(476, 64, f"SPEC_CENTRE_COL_{THIRD}", "right", True)])
STAND_IS = lambda t: f"EqualTo_CFixedPoint({v('spec_exch_stand')}, {fx(t)})"
TIER_N = lambda t: f"GetGlobalVariable('spec_exch_n_{t}').GetValue"
ALSO_CLEAR = """	every_country = {
		limit = { has_variable = spec_centre_also }
		remove_variable = spec_centre_also
	}
""" if ON else ""
# how many markets hold each Standing, for the World tab's tiers
COUNTS = ("".join(f"\tset_global_variable = {{ name = spec_exch_n_{t} value = 0 }}\n" for t in range(4))
          + "\tevery_country = {\n\t\tlimit = { has_variable = spec_exch_stand }\n"
          + "".join(f"\t\tif = {{\n\t\t\tlimit = {{ var:spec_exch_stand = {t} }}\n"
                    f"\t\t\tchange_global_variable = {{ name = spec_exch_n_{t} add = 1 }}\n\t\t}}\n" for t in range(4))
          + "\t}\n") if ON else ""


def tint(t):
    """A tiered row's Standing colour: a faint wash fading right. A child widget, as the row's clean_button draws
    over its own backgrounds (2026-11-19)."""
    if t is None:
        return ""
    return f"""		widget = {{
			size = {{ 100% 100% }}
			alwaystransparent = yes
			background = {{
				using = fade_right_colored
				color = {{ {TIER_COL[t]} 1 }}
				alpha = {ROW_TINT}
			}}
		}}
"""


def row(n=None, t=None):
    """Listed market n, laid out as vanilla's ranked country rows are (the diplomatic overview); without n, our own
    market when it is not listed. With t, shown only while the market's Standing is t (the tier it sits in).
    Inside the inner widget the Country is the listed one, so P reads its variables."""
    placed = n and n <= PLACES
    return f"""flowcontainer = {{
	ignoreinvisible = yes
	visible = "[{f'{SLOT(n)}.IsSet' if n else UNPLACED}]"
	button = {{  # the whole row one button: hover, click, right click, map highlight. default_button as the rival picker's rows
		size = {{ {W} {ROW_H} }}  # (2026-11-19: clean_button, transparent, showed the tint muddy over the panel)
		using = default_button
		{f'datacontext = "[{SLOT(n)}.GetCountry]"' if n else ""}
		{f'visible = "[{STAND_IS(t)}]"' if t is not None else ""}
		tooltip = "SPEC_CENTRE_TT_{n if placed else 'OWN'}"
		onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
		onrightclick = "[RightClickMenuManager.ShowForCountry(Country.AccessSelf)]"
		onmousehierarchyenter = "[AccessHighlightManager.HighlightCountry(Country.Self)]"
		onmousehierarchyleave = "[AccessHighlightManager.RemoveHighlight]"
		widget = {{
			visible = "[Country.IsLocalPlayer]"
			size = {{ 100% 100% }}
			alwaystransparent = yes
			background = {{
				using = paper_bg
			}}
		}}
{tint(t)}{ind(text(0, 40, f"SPEC_CENTRE_N_{n or 'NONE'}", "center"), 2)}		textbox = {{  # flag and name as one link, as vanilla's ranked lists (map_list_panel)
			position = {{ 44 0 }}
			size = {{ 168 {ROW_H} }}
			margin_left = 4
			align = nobaseline
			parentanchor = vcenter
			elide = right
			text = "[Country.GetName]"
		}}
{ind(text(226, 60, "SPEC_CENTRE_SCORE", "right") + text(476, 54, f"SPEC_CENTRE_{THIRD}", "right"), 2)}{rival_button() if RIVAL_ON else ""}{name_icons()}	}}
}}
"""


# each Standing's colour in the World tab, after its badge: gold, silver, bronze, stone
TIER_COL = {3: "0.86 0.69 0.32", 2: "0.72 0.77 0.84", 1: "0.76 0.47 0.26", 0: "0.5 0.5 0.5"}
# a row's wash in its Standing's colour, a step under the tier band's 0.45: rows are vanilla's opaque default_button
# now, and 0.18 read muddy over it (2026-11-19)
ROW_TINT = 0.3


def tier(t):
    """A Standing's band in the World tab: its badge, its name and how many markets hold it, then those listed."""
    # a plain band in the expand button's look: it opens nothing, so it is not a button. Its textures without the
    # template's button effects (gfxtype, effectname), which a plain widget cannot create
    return f"""widget = {{
	size = {{ {W} 48 }}
	tooltip = "SPEC_EXCH_TIER_TT_{t}"
	background = {{
		texture = "gfx/interface/buttons/expand_button_bg.dds"
		spriteType = Corneredtiled
		spriteborder = {{ 20 20 }}
		texture_density = 2
		modify_texture = {{
			texture = "gfx/interface/buttons/default_button_bg_gradient.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 0 0 }}
			blend_mode = overlay
			alpha = 0.5
		}}
		modify_texture = {{
			texture = "gfx/interface/textures/default_noise_texture.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 0 0 }}
			blend_mode = overlay
		}}
		modify_texture = {{
			texture = "gfx/interface/masks/fade_horizontal_center.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 0 0 }}
			blend_mode = alphamultiply
		}}
	}}
	background = {{
		using = fade_right_colored
		color = {{ {TIER_COL[t]} 1 }}
		alpha = 0.45
	}}
	icon = {{
		size = {{ 40 40 }}
		position = {{ 6 0 }}
		parentanchor = vcenter
		texture = "{icons.path(f'exch_tier_{t}')}"
	}}
	textbox = {{
		position = {{ 56 0 }}
		size = {{ 300 30 }}
		parentanchor = vcenter
		align = left|nobaseline
		using = fontsize_large
		default_format = "#white"
		text = "SPEC_EXCH_W_{t}"
	}}
	textbox = {{
		visible = "[Not(EqualTo_CFixedPoint({TIER_N(t)}, {fx(0)}))]"
		position = {{ -12 0 }}
		size = {{ 170 30 }}
		parentanchor = right|vcenter
		align = right|nobaseline
		text = "SPEC_EXCH_TIER_N_{t}"
	}}
}}
{"".join(row(n, t) for n in range(1, {3: WORLD_PLACES + 1, 0: 1}.get(t, SHOWN + 1))) + row(None, t)}textbox = {{
	size = {{ {W} 30 }}
	visible = "[EqualTo_CFixedPoint({TIER_N(t)}, {fx(0)})]"
	align = center|nobaseline
	alpha = 0.5
	text = "SPEC_EXCH_TIER_EMPTY"
}}
"""


def section():
    rows = ("".join(tier(t) for t in (3, 2, 1, 0)) if ON else
            "".join(row(n) for n in range(1, PLACES + 1)) + row())
    body = f"""flowcontainer = {{
	direction = vertical
	ignoreinvisible = yes
	visible = "[{RANKED}]"
	widget = {{
		size = {{ {W} 30 }}
{ind(heads(HEADS), 2)}	}}
{ind(rows, 1)}}}
empty_state = {{
	blockoverride "visible" {{
		visible = "[Not({RANKED})]"
	}}
	blockoverride "text" {{
		text = "SPEC_CENTRE_EMPTY"
	}}
}}
"""
    return block(header("SPEC_H_CENTRES", "SPEC_CENTRE_PLACE", "SPEC_CENTRE_PLACE_TT", f"{P}.Var('spec_centre_rank').IsSet"),
                 body)


def gauge(label, value, expr, top, tt, vis=None):
    """A named figure over a vanilla progress bar."""
    return f"""widget = {{
{f'	visible = "[{vis}]"' + chr(10) if vis else ""}	size = {{ {W} 46 }}
	parentanchor = hcenter
	tooltip = "{tt}"
	divider_clean = {{
		parentanchor = bottom
		position = {{ 0 2 }}
	}}
	textbox = {{
		position = {{ 20 4 }}
		size = {{ 320 20 }}
		align = left|nobaseline
		text = "{label}"
	}}
	textbox = {{
		position = {{ -20 4 }}
		size = {{ 160 20 }}
		parentanchor = right
		align = right|nobaseline
		text = "{value}"
	}}
	widget = {{
		position = {{ 20 28 }}
		size = {{ {BAR_W} 10 }}
		default_progressbar_horizontal = {{
			size = {{ 100% 100% }}
			blockoverride "values" {{
				min = 0
				max = {top}
				value = "[{expr}]"
			}}
		}}
	}}
}}
"""

TRUST_LV = ["Distrusted", "Doubted", "Respected", "Trusted"]
TRUST_COL = ["N", "grey", "v", "P"]  # the level's colour where it is shown alone (the trust heading)
TRUST_PICK = lambda: _pick(f"Subtract_CFixedPoint(Multiply_CFixedPoint(Divide_CFixedPoint({v('spec_centre_trust')}, {fx(CALM)}), "
                           f"{fx(4)}), {fx(0.5)})", "SPEC_EXCH_TRUST_LV", 3)


def levels_bar(segs, w=W, tt=""):
    """vanilla's levels_progressbar (progressbars.gui:107), as legitimacy and interests show theirs: a bar in equal
    segments, one per level, the active one lit and shimmering. Built by hand: its datamodel is the engine's.
    segs: (progress 0-1, is active, tooltip) for each level; a progress past 1 or under 0 shows full or empty."""
    def seg(i, prog, active, stt):
        last = i == len(segs) - 1
        return f"""widget = {{
	size = {{ 0 15 }}
	layoutpolicy_horizontal = expanding
	tooltip = "{stt}"
	using = tooltip_se
	widget = {{
		visible = "[{active}]"
		size = {{ 100% 100% }}
		background = {{
			using = dark_area
			alpha = 0.4
		}}
	}}
	### hidden below 2% (2026-11-22: a level not yet reached showed a pixel of fill, the bar's end drawn at no width)
	default_progressbar_horizontal = {{
		visible = "[GreaterThan_CFixedPoint({prog}, {fx(0.02)})]"
		size = {{ 100% 100% }}
		blockoverride "background" {{}}
		blockoverride "frame" {{}}
		blockoverride "glow_visible" {{
			visible = "[{active}]"
		}}
		blockoverride "values" {{
			min = 0
			max = 1
			value = "[FixedPointToFloat({prog})]"
		}}
	}}
{"" if last else """	widget = {
		size = { 3 100% }
		position = { 3 0 }
		parentanchor = right
		background = {
			margin = { 0 1 }
			texture = "gfx/interface/progressbar/progressbar_center_divider.dds"
			spriteType = Corneredstretched
			spriteborder = { 0 0 }
			texture_density = 2
		}
	}
"""}	widget = {{
		visible = "[{active}]"
		size = {{ 100% 100% }}
		icon = {{
			size = {{ 100% 100% }}
			texture = "gfx/interface/progressbar/progressbar_active_level.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
			using = shimmer
		}}
	}}
}}
"""
    return f"""widget = {{
	size = {{ {w} 21 }}
	parentanchor = hcenter
{f'	tooltip = "{tt}"' + chr(10) if tt else ""}	hbox = {{
		size = {{ 100% 100% }}
		margin = {{ 3 3 }}
		spacing = 3
		background = {{
			texture = "gfx/interface/progressbar/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
			alpha = 0.8
		}}
		background = {{
			texture = "gfx/interface/progressbar/progressbar_frame.dds"
			spriteType = Corneredstretched
			spriteborder = {{ 6 6 }}
			texture_density = 2
		}}
{ind("".join(seg(i, *x) for i, x in enumerate(segs)), 2)}	}}
}}
"""


SCORE_V = lambda c: f"{c}.MakeScope.Var('spec_centre_score').GetValueWithDefault({fx(0)})"


def score_segs():
    """The score as the Standings' levels, one segment per card (standing_block), each how far through that Standing:
    Provincial up to National's score, National up to fifth place's, International up to first's, World Centre full."""
    sc = v("spec_centre_score")
    far = fx(10000)
    at = lambda n: f"Select_CFixedPoint({SLOT(n)}.IsSet, {SCORE_V(SLOT(n) + '.GetCountry')}, {far})"
    fifth, first = at(PLACES), at(WORLD_PLACES)  # first: the lowest World Centre's score
    span = lambda lo, hi: f"Divide_CFixedPoint(Subtract_CFixedPoint({sc}, {lo}), Max_CFixedPoint(Subtract_CFixedPoint({hi}, {lo}), {fx(1)}))"
    segs = [(span(fx(0), fx(NATIONAL)), STAND_IS(0), "SPEC_EXCH_TIER_TT_0"),
            (span(fx(NATIONAL), fifth), STAND_IS(1), "SPEC_EXCH_TIER_TT_1"),
            (span(fifth, first), STAND_IS(2), "SPEC_EXCH_TIER_TT_2"),
            (f"Add_CFixedPoint(Subtract_CFixedPoint({sc}, {first}), {fx(1)})", STAND_IS(3), "SPEC_EXCH_TIER_TT_3")]
    # the Standing held decides, the score only fills its own segment: those below it full, those above it empty.
    # The score alone neither grants nor loses one (World Centre needs GATE, International comes also from first in
    # the region): Russia showed World Centre full at third without GATE, then National part-filled while
    # International as first in its region (2026-11-16)
    stand = v("spec_exch_stand")
    segs = [(f"Select_CFixedPoint(GreaterThan_CFixedPoint({stand}, {fx(i)}), {fx(1)}, "
             f"Select_CFixedPoint(LessThan_CFixedPoint({stand}, {fx(i)}), {fx(0)}, {p}))", on, tt)
            for i, (p, on, tt) in enumerate(segs)]
    return segs


def hero(label, num, tt, tex):
    """A headline value, as vanilla's big numbers (fontsize_xxl): icon, name, the value large. The score's
    and trust's headings were small and timid (2026-11-16)."""
    rule = lambda mirror: f"""	icon = {{
		size = {{ 70 3 }}
		parentanchor = vcenter
		texture = "gfx/interface/dividers/divider_clean.dds"
		alpha = 0.7{chr(10) + chr(9) * 2 + "mirror = horizontal" if mirror else ""}
	}}
"""
    return f"""widget = {{
	size = {{ {W} 48 }}
	parentanchor = hcenter
	tooltip = "{tt}"
	flowcontainer = {{
		parentanchor = center
		spacing = 10
		icon = {{
			size = {{ 34 34 }}
			parentanchor = vcenter
			texture = "{tex}"
		}}
		textbox = {{
			autoresize = yes
			parentanchor = vcenter
			align = left|nobaseline
			using = fontsize_xl
			text = "{label}"
		}}
		textbox = {{
			autoresize = yes
			parentanchor = vcenter
			align = left|nobaseline
			using = fontsize_xxl
			text = "{num}"
		}}
	}}
}}
"""


def trust_levels():
    """Trust as vanilla shows legitimacy (politics_panel_overview.gui:543): "Trust 18%", each level's name over its
    own segment of the levels bar (the held one lit, the rest dimmed), each segment's tooltip what that level does.
    2026-11-16: the one long tooltip read badly; the bar now explains itself."""
    share = f"Divide_CFixedPoint({v('spec_centre_trust')}, {fx(CALM)})"
    held = lambda i: (f"And(Not(LessThan_CFixedPoint({share}, {fx(i / 4)})), "
                      f"LessThan_CFixedPoint({share}, {fx((i + 1) / 4 if i < 3 else 2)}))")
    segs = [(f"Multiply_CFixedPoint(Subtract_CFixedPoint({share}, {fx(i / 4)}), {fx(4)})", held(i), f"SPEC_EXCH_TRUST_LV_TT_{i}")
            for i in range(4)]
    cw = (BAR_W - 6) // 4
    names = "".join(f"""	textbox = {{
		position = {{ {(W - BAR_W) // 2 + 3 + i * (cw + 2)} 0 }}
		size = {{ {cw} 20 }}
		align = center|nobaseline
		using = fontsize_small
		elide = right
		tooltip = "SPEC_EXCH_TRUST_LV_TT_{i}"
		using = tooltip_se
		text = "[SelectLocalization({held(i)}, 'SPEC_EXCH_TRUST_LV_{i}', 'SPEC_EXCH_TRUST_LV_DIM_{i}')]"
	}}
""" for i in range(4))
    return f"""{hero("SPEC_EXCH_TRUST_LBL", "SPEC_EXCH_TRUST_NUM", "SPEC_EXCH_G_TRUST_TT", icons.path("concept_trust"))}widget = {{
	size = {{ {W} 20 }}
	parentanchor = hcenter
{names}}}
{levels_bar(segs, BAR_W)}"""


def _parts_loc():
    """The score's calculator in vanilla's breakdown form (as market_tab.why_lines): the base value from the capital the
    Exchange draws on, then each multiplier "from" its cause, those at x1 left out, the parts with more to them in
    nested tooltips; then where that places us, against the world's top three and our region's leader."""
    p = lambda name, f="0": f"[{v(name)}|{f}]"
    nest = lambda key, text: f"#tooltippable #tooltip:[Country.GetTooltipTag],{key} {text}#!#!"
    money = lambda name: f"@money![Multiply_CFixedPoint({v(name)}, {fx(CAP_PER)})|D]"
    x = lambda name: f"#Â§ x{p(name, '2')}#!"  # Â§: the colour, P above x1 and N below (SPEC_XS_ROW_<k> and _N)
    mults = {"WEALTH": ("spec_xs_wealth_v", f"{nest('SPEC_XS_WEALTH_TT', x('spec_xs_wealth_v'))} from Wealth per Head"),
             "FD": ("spec_xs_fdm_v", f"{x('spec_xs_fdm_v')} from #v {p('spec_xs_fd_v')}#! "
                                     "[GetBuildingType('building_financial_district').GetName] levels"),
             "CO": ("spec_xs_com_v", f"{x('spec_xs_com_v')} from #v {p('spec_xs_co_v')}#! companies headquartered here"),
             "TECH": ("spec_xs_tech_v", f"{nest('SPEC_XS_TECH_TT', x('spec_xs_tech_v'))} from #v {p('spec_xs_ntech_v')}#! "
                                        f"of #v {len(TECHS)}#! Finance Technologies"),
             "RANK": ("spec_xs_rank_v", f"{x('spec_xs_rank_v')} from [concept_rank]"),
             "ECON": ("spec_xs_econ_v", f"{nest('SPEC_XS_ECON_TT', x('spec_xs_econ_v'))} from Economic System"),
             "TRUST": ("spec_xs_trust_v", f"{x('spec_xs_trust_v')} from Trust")}
    issue = (f"[AddLocalizationIf({P}.Var('spec_issue').IsSet, 'SPEC_XS_ROW_ISSUE')]" if levers.ISSUE_ON else "")
    regs = "".join(f"[AddLocalizationIf(EqualTo_CFixedPoint({v('spec_xs_reg')}, {fx(i)}), 'SPEC_XS_REGLINE_{i}')]"
                   for i in range(1, len(REGIONS) + 1))
    calc = (f"#header [concept_spec_exchange] Score: #v {p('spec_centre_score')}#!#!\\n$TOOLTIP_DELIMITER$\\n"
            f"{nest('SPEC_XS_CAP_TT', '#v ' + p('spec_xs_size_v') + '#!')} base, from #v {money('spec_xs_own_v')}#! of our own Capital "
            f"and #v {money('spec_xs_reach_v')}#! from our ties"
            + "".join(f"[AddLocalizationIf(GreaterThan_CFixedPoint({v(n)}, {fx(1)}), 'SPEC_XS_ROW_{k}')]"
                      f"[AddLocalizationIf(LessThan_CFixedPoint({v(n)}, {fx(1)}), 'SPEC_XS_ROW_{k}_N')]" for k, (n, _) in mults.items())
            + issue + f"\\n$TOOLTIP_DELIMITER$\\nThese make #v {p('spec_xs_raw')}#!, scored against the world's top three, "
            f"whose average counts as #v 100#!.{regs}")
    techs = "".join(f"\\n${t}$: #P +{b:.0%}#!" for t, b in TECHS.items())
    econ = "".join(f"\\n$law_{k}$: #{'v' if m == 1 else 'P' if m > 1 else 'N'} x{m:g}#!" for k, m in ECON.items())
    tech = lambda k: f"[GetTechnology('{k}').GetName]"
    reach = (f"#v {REACH:.0%}#! of the money of each smaller [concept_country] in our [concept_market], our [Concept('concept_subject','$concept_subjects$')], "
             f"our [concept_power_bloc], or any that gives us [concept_foreign_investment] rights, never more than our own")
    return (f' SPEC_EXCH_CALC_TT: "{calc}"\n'
            + "".join(f' SPEC_XS_ROW_{k}: "\\n{line.replace("Â§", "P")}"\n SPEC_XS_ROW_{k}_N: "\\n{line.replace("Â§", "N")}"\n'
                      for k, (_, line) in mults.items())
            + f' SPEC_XS_ROW_ISSUE: "\\n#P x[Add_CFixedPoint(Multiply_CFixedPoint({P}.Var(\'spec_issue_w\').GetValueWithDefault(\'(CFixedPoint)0\'), \'(CFixedPoint){levers.ISSUE_SCORE - 1:g}\'), \'(CFixedPoint)1\')|2]#! from a Great Issue"\n'
            + "".join(f' SPEC_XS_REGLINE_{i}: "\\nWe score #v {p("spec_xs_regshare")}%#! of '
                      f"[GetGlobalVariable('spec_xs_rlead_{i}').GetCountry.GetName]'s, the leader in {name}.\"\n"
                      for i, (_, name) in enumerate(REGIONS, 1))
            + f' SPEC_XS_CAP_TT: "#header Capital: #v @money![Multiply_CFixedPoint(Add_CFixedPoint({v("spec_xs_own_v")}, {v("spec_xs_reach_v")}), '
            f'{fx(CAP_PER)})|D]#!#!\\n$TOOLTIP_DELIMITER$\\n'
            f"#v {money('spec_xs_own_v')}#! from our own [concept_investment_pool] income, #v {MONTHS:g}#! months of it at its yearly average\\n"
            f"#v {money('spec_xs_reach_v')}#! from our ties, {reach}\\n$TOOLTIP_DELIMITER$\\n"
            f"More money raises the score less and less. It takes #v {2 ** SIZE_ROOT}#! times the money to double it.\"\n"
            f' SPEC_XS_WEALTH_TT: "#header Wealth per Head: #v x{p("spec_xs_wealth_v", "2")}#!#!\\n$TOOLTIP_DELIMITER$\\n'
            f"Our [concept_investment_pool] income per person is #v {p('spec_xs_ratio_v', '2')}#! times the world average. "
            f'The score takes its square root, between #v x{WEALTH[0]:g}#! and #v x{WEALTH[1]:g}#!."\n'
            f' SPEC_XS_TECH_TT: "#header Finance Technologies: #v x{p("spec_xs_tech_v", "2")}#!#!\\n$TOOLTIP_DELIMITER$\\n'
            f'Each one researched raises the score:{techs}'
            f"\\n$TOOLTIP_DELIMITER$\\n{tech('stock_exchange')} is also needed for #v International#! Standing, and "
            f"{tech('central_banking')} for #v World Centre#!.\"\n"
            f' SPEC_XS_ECON_TT: "#header Economic System: #v x{p("spec_xs_econ_v", "2")}#!#!\\n$TOOLTIP_DELIMITER$\\n'
            f'Our economic law changes the score:{econ}"\n')


def standing_block():
    """Exchange tab, first: the score, then the four Standings as cards with ours lit, each card's foot its own segment
    of the score's levels (score_segs), then the trust that moves it. 2026-11-16: the cards and a separate score bar
    read as two things; each card now fills as the score climbs through it."""
    segs = score_segs()
    cw = (W - 30) // 4
    def rung(t):
        reached = f"Not(LessThan_CFixedPoint({v('spec_exch_stand')}, {fx(t)}))"
        prog, active, _ = segs[t]
        badge = lambda shown, extra: f"""	icon = {{
		size = {{ 64 64 }}
		position = {{ 0 8 }}
		parentanchor = top|hcenter
		visible = "[{shown}]"
		texture = "{icons.path(f'exch_tier_{t}')}"
{extra}	}}
"""
        return f"""widget = {{
	size = {{ {cw} 118 }}
	tooltip = "SPEC_EXCH_TIER_TT_{t}"
	background = {{
		visible = "[Not({STAND_IS(t)})]"
		using = entry_bg_simple
	}}
	background = {{
		visible = "[{STAND_IS(t)}]"
		using = paper_bg
	}}
	icon = {{
		visible = "[{STAND_IS(t)}]"
		using = highlighted_square_selection
	}}
{badge(reached, "")}{badge(f"Not({reached})", "		alpha = 0.3" + chr(10))}	textbox = {{
		position = {{ 0 -24 }}
		size = {{ 100% 22 }}
		parentanchor = bottom|hcenter
		align = center|nobaseline
		elide = right
		text = "SPEC_EXCH_W_{t}"
	}}
	widget = {{
		position = {{ 0 -9 }}
		size = {{ {cw - 16} 11 }}
		parentanchor = bottom|hcenter
		background = {{
			texture = "gfx/interface/progressbar/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = {{ 4 4 }}
			texture_density = 2
		}}
		default_progressbar_horizontal = {{
			visible = "[GreaterThan_CFixedPoint({prog}, {fx(0.02)})]"  # 2026-11-22: an empty card showed a sliver of fill
			size = {{ 100% 100% }}
			blockoverride "background" {{}}
			blockoverride "frame" {{}}
			blockoverride "glow_visible" {{
				visible = "[{active}]"
			}}
			blockoverride "values" {{
				min = 0
				max = 1
				value = "[FixedPointToFloat({prog})]"
			}}
		}}
	}}
}}
"""
    return f"""{hero("SPEC_EXCH_SCORE_LBL", "SPEC_EXCH_SCORE_NUM", "SPEC_EXCH_CALC_TT", icons.path("concept_exchange"))}flowcontainer = {{
	parentanchor = hcenter
	spacing = 10
{ind("".join(rung(t) for t in range(4)), 1)}}}
widget = {{
	size = {{ {W} 10 }}
}}
{trust_levels()}"""


CARDS = [(1, "building_icons/building_trade_center"), (2, "invention_icons/banking"), (3, "invention_icons/stock_exchanges")]


def known_block():
    """Exchange tab: the three things an Exchange can be known for, each with how far the country has built toward it."""
    if NAMES_ON:
        return _charter_block()
    cw = (W - 20) // 3
    card = lambda n, tex: f"""widget = {{
	size = {{ {cw} 172 }}
	tooltip = "SPEC_EXCH_CARD_TT_{n}"
	using = entry_bg_fancy
	background = {{
		visible = "[EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})]"
		using = paper_bg
	}}
	icon = {{
		visible = "[EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})]"
		using = highlighted_square_selection
	}}
	icon = {{
		size = {{ 56 56 }}
		position = {{ 0 8 }}
		parentanchor = top|hcenter
		texture = "gfx/interface/icons/{tex}.dds"
	}}
	textbox = {{
		position = {{ 0 68 }}
		size = {{ 100% 22 }}
		parentanchor = top|hcenter
		align = center|nobaseline
		text = "SPEC_EXCH_CARD_H_{n}"
	}}
	textbox = {{
		position = {{ 0 90 }}
		size = {{ {cw - 12} 38 }}
		parentanchor = top|hcenter
		multiline = yes
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_EXCH_CARD_N_{n}"
	}}
	widget = {{
		position = {{ 0 132 }}
		size = {{ {cw - 28} 10 }}
		parentanchor = top|hcenter
		default_progressbar_horizontal = {{
			size = {{ 100% 100% }}
			blockoverride "values" {{
				min = 0
				max = 1
				value = "[{P}.ScriptValue('{EARN_BY[n]}')]"
			}}
		}}
	}}
	textbox = {{
		position = {{ 0 146 }}
		size = {{ 100% 20 }}
		parentanchor = top|hcenter
		visible = "[EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})]"
		align = center|nobaseline
		using = fontsize_small
		text = "SPEC_EXCH_CARD_HELD"
	}}
}}
"""
    return f"""flowcontainer = {{
	parentanchor = hcenter
	spacing = 10
{ind("".join(card(n, tex) for n, tex in CARDS), 1)}}}
"""


def pledge_row():
    """In the Bank Rescue block, under the panic card and in its style: where the pledge stands, what it does, and one
    button, Make the Pledge or, once pledged, Withdraw the Pledge."""
    if not PLEDGE_ON:
        return ""
    from market_tab import BTN_W, BTN_H
    pledged = f"{P}.Var('spec_pledge').IsSet"
    button = lambda key, sgui, shown: f"""	button = {{
		size = {{ {BTN_W} {BTN_H} }}
		position = {{ -20 0 }}
		parentanchor = right|vcenter
		using = default_button_primary
		align = center|nobaseline
		visible = "[{shown}]"
		enabled = "{sg(sgui, 'IsValid')}"
		onclick = "{sg(sgui, 'Execute')}"
		text = "SPEC_PLEDGE_{key}"
		tooltip = "SPEC_PLEDGE_{key}_TT"
	}}
"""
    text_w = W - 70 - BTN_W - 30
    return f"""widget = {{
	size = {{ {W} 64 }}
	tooltip = "[SelectLocalization({pledged}, 'SPEC_PLEDGE_OUT_TT', 'SPEC_PLEDGE_MAKE_TT')]"
	background = {{
		using = entry_bg
	}}
	icon = {{
		size = {{ 40 40 }}
		position = {{ 16 0 }}
		parentanchor = vcenter
		texture = "{icons.path('rescue_pledge')}"
	}}
	textbox = {{
		position = {{ 70 10 }}
		size = {{ {text_w} 24 }}
		align = left|nobaseline
		elide = right
		text = "SPEC_PLEDGE_STATE"
	}}
	textbox = {{
		position = {{ 70 34 }}
		size = {{ {text_w} 20 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_PLEDGE_SUB"
	}}
{button('MAKE', 'pledge', f'Not({pledged})')}{button('OUT', 'pledge_leave', pledged)}}}
"""


def _pledge_loc():
    about = (f"The state rescues the banks at once in #P every#! [concept_spec_financial_panic], #P {1 - PLEDGE_SHARE:.0%}#! cheaper, "
             "while the [concept_treasury] can pay from reserves and we are not in [concept_default].\\n"
             f"#P {PLEDGE_PANIC - 1:+.0%}#! trust lost by our [concept_spec_exchange] in a panic\\n"
             f"#P {PLEDGE_FLIGHT - 1:+.0%}#! [concept_spec_capital_flight] received"
             + ("\\n#N Each rescue loosens#! [concept_spec_lending_standards]" if cycle.ON else "") + "\\n$TOOLTIP_DELIMITER$\\n"
             f"If we go into [concept_default], the Pledge breaks: all trust is lost, [concept_spec_market_confidence] falls by "
             f"#N {PLEDGE_BREAK['conf']}#!, and [concept_legitimacy] is #N -{PLEDGE_BREAK['legit']}#! for #v {PLEDGE_BROKEN_MONTHS // 12}#! years.")
    notice = f"\\nWithdrawing the Pledge takes #v {PLEDGE_NOTICE}#! months' notice."
    why = lambda k: (f"[AddLocalizationIf(Not(GetScriptedGui('spec_sgui_{k}').IsValid(GuiScope.SetRoot({P}).End)), "
                     f"'SPEC_PLEDGE_{k.upper()}_WHY')]")
    pledged, leaving = f"{P}.Var('spec_pledge').IsSet", f"{P}.Var('spec_pledge_leave').IsSet"
    out = (' SPEC_PLEDGE_MAKE: "Make the Pledge"\n'
           ' SPEC_PLEDGE_OUT: "Withdraw the Pledge"\n'
           f" SPEC_PLEDGE_STATE: \"[SelectLocalization({pledged}, SelectLocalization({leaving}, 'SPEC_PLEDGE_LEAVING', 'SPEC_PLEDGE_ON'), 'SPEC_PLEDGE_NONE')]\"\n"
           ' SPEC_PLEDGE_NONE: "No Pledge to Rescue the Banks"\n'
           ' SPEC_PLEDGE_ON: "Pledged to Rescue the Banks"\n'
           f' SPEC_PLEDGE_SUB: "Every panic rescued at once, #P {1 - PLEDGE_SHARE:.0%}#! cheaper"\n'
           f' SPEC_PLEDGE_LEAVING: "Withdrawing: [{v("spec_pledge_leave")}|0] months left"\n'
           f' SPEC_PLEDGE_MAKE_TT: "#header Pledge to Rescue the Banks#!\\n$TOOLTIP_DELIMITER$\\n{about}{notice}{why("pledge")}"\n'
           f' SPEC_PLEDGE_OUT_TT: "#header $SPEC_PLEDGE_OUT$#!\\n$TOOLTIP_DELIMITER$\\nStarts #v {PLEDGE_NOTICE}#! months\' notice to end the Pledge, '
           f'which holds until the notice runs out.\\n$TOOLTIP_DELIMITER$\\n{about}{why("pledge_leave")}"\n'
           ' spec_pledge_stand_tt: "Our [concept_spec_exchange] stands #v National#! or higher"\n'
           f' spec_pledge_debt_tt: "Our debt is no more than #v {PLEDGE_DEBT:.0%}#! of our [concept_credit]"\n'
           ' spec_pledge_panic_tt: "There is no [concept_spec_financial_panic]"\n'
           ' spec_pledge_made_tt: "We have not already made the Pledge"\n'
           ' spec_pledge_none_tt: "We have made the Pledge"\n'
           ' spec_pledge_leaving_tt: "We are not already withdrawing it"\n'
           # Nested localization in the player's panic popup no longer carries the event ROOT.
           ' SPEC_PLEDGE_UNMET: "\\n\\n#N The pledged rescue did not take place.#!'
           + "".join(f"[AddLocalizationIf(EqualTo_CFixedPoint(GetPlayer.MakeScope.Var('spec_pledge_reason').GetValueWithDefault({fx(0)}), {fx(n)}), 'SPEC_PLEDGE_{cause}')]"
                     for n, cause in enumerate(("CASH", "DEFAULT", "TECH"), 1))
           + "\\n[SelectLocalization(GetPlayer.MakeScope.Var('spec_pledge').IsSet, SelectLocalization(GetPlayer.MakeScope.Var('spec_pledge_leave').IsSet, 'SPEC_PLEDGE_NOTICE_STATUS', 'SPEC_PLEDGE_ON'), 'SPEC_PLEDGE_NONE')]\"\n"
           ' SPEC_PLEDGE_CASH: " The rescue needed #v @money![GetPlayer.MakeScope.Var(\'spec_pledge_required\').GetValue|D]#!, and our reserves fell short by #N @money![GetPlayer.MakeScope.Var(\'spec_pledge_shortfall\').GetValue|D]#!."\n'
           ' SPEC_PLEDGE_DEFAULT: " The country was in [concept_default] when the panic began."\n'
           ' SPEC_PLEDGE_TECH: " A rescue requires [GetTechnology(\'banking\').GetName]."\n'
           ' SPEC_PLEDGE_NOTICE_STATUS: "Pledge under notice Â· #v [GetPlayer.MakeScope.Var(\'spec_pledge_leave\').GetValue|0]#! months left"\n'
           ' spec_pledge_broken: "Broken Pledge"\n'
           ' spec_pledge_broken_desc: "The [concept_country] pledged to rescue its banks, then went into [concept_default]."\n'
           ' notification_spec_pledge_broken_name: "Our default breaks the Pledge"\n'
           ' notification_spec_pledge_broken_desc: "Our default has broken our Pledge to Rescue the Banks, and the '
           '$SPEC_EXCH_CITY_ME$ Exchange has lost all the trust it held."\n'
           ' notification_spec_pledge_broken_tooltip: "#header $notification_spec_pledge_broken_name$#!\\n$TOOLTIP_DELIMITER$\\n'
           '$notification_spec_pledge_broken_desc$"\n')
    for k in ("pledge", "pledge_leave"):
        out += f' SPEC_PLEDGE_{k.upper()}_WHY: "\\n\\n{sg(k, "BuildTooltip")}"\n'
    return out


def loc():
    pct = lambda n: f"{(PLACES + 1 - n) * STEP:.0%}"
    lim = lambda n: f"{(PLACES + 1 - n) * LIMIT_STEP:g}"  # credit limit months (BRAKE)
    score, yrs, rank = f"[{v('spec_centre_score')}|0]", f"[{v('spec_centre_yrs')}|0]", f"[{v('spec_centre_rank')}|0]"
    centres = "[Concept('concept_spec_financial_centre','$concept_spec_financial_centres$')]"
    stats = (f"Score: #v {score}#!\\n" + ("[concept_spec_exchange] Standing: $SPEC_CENTRE_STAND$\\nTrust: #v $SPEC_EXCH_TRUST$#!\\n" if ON else "")
             + "Years without a [concept_spec_financial_panic]: $SPEC_CENTRE_CALM$")
    lim_now = f"{P}.ScriptValue('spec_exch_limit')"
    out = (' SPEC_H_CENTRES: "Leading Exchanges"\n'
           ' SPEC_H_CENTRES_TT: "#header $concept_spec_financial_centres$#!\\n$concept_spec_financial_centre_desc$"\n'
           ' concept_spec_financial_centre: "Leading Exchange"\n'
           ' concept_spec_financial_centres: "Leading Exchanges"\n'
           f' concept_spec_financial_centre_desc: "The $concept_spec_financial_centres$ are the #v {PLACES}#! '
           + ("[Concept('concept_country','$concept_countries$')] with the highest [concept_spec_exchange] score, ranked each month.\\n\\n" if ON else
              "[Concept('concept_country','$concept_countries$')] whose Exchanges lead the world, ranked each month.\\n\\n"
              f"Your Exchange's score is #v {MONTHS:g}#! months of [concept_investment_pool] income plus its "
              "[concept_spec_outstanding_credit]. A [concept_spec_financial_panic] cuts this to #v half#!. It then grows "
              f"month by month, to #v one and a half times#! after #v {CALM // 12}#! years without another. The leader's "
              "score is shown as #v 100#!.\\n\\n")
           + f"First place gives #P +{pct(1)}#! [concept_prestige]"
           + (f" and #P +{lim(1)}#! months of Lending Limit" if BRAKE else "")
           + f", down to #P +{pct(PLACES)}#!"
           + (f" and #P +{lim(PLACES)}#! month{'s' * (lim(PLACES) != '1')}" if BRAKE else "")
           + f" in place #v {PLACES}#!."
           + (" The Lending Limit bonus needs [GetTechnology('central_banking').GetName] and [concept_spec_lending_standards] "
              f"#v {cycle.LAX_WORDS[2]}#! or stricter." if BRAKE else "") + '"\n'
           f' SPEC_CENTRE_PLACE: "#v ##{rank}#!"\n'
           # what our place gives now, as our row's tooltip lists it
           f' SPEC_CENTRE_PLACE_TT: "#header [concept_spec_financial_centre] #v ##{rank}#!#!\\n$TOOLTIP_DELIMITER$\\n'
           f"[concept_prestige]: #P +[Multiply_CFixedPoint(Subtract_CFixedPoint({fx(PLACES + 1)}, {v('spec_centre_rank')}), {fx(STEP)})|%0]#!"
           + (f"[SelectLocalization({gt(lim_now)}, 'SPEC_CENTRE_PLACE_LIMIT', 'SPEC_EXCH_LIMIT_OFF')]" if BRAKE else "") + '"\n'
           + (f" SPEC_CENTRE_PLACE_LIMIT: \"\\nLending Limit: #P +[{lim_now}|0]#! "
              f"[SelectLocalization({gt(lim_now, 1.5)}, 'SPEC_CENTRE_MONTHS', 'SPEC_CENTRE_MONTH')]\"\n"
              ' SPEC_CENTRE_MONTH: "month"\n SPEC_CENTRE_MONTHS: "months"\n' if BRAKE else "") +
           ' SPEC_CENTRE_EMPTY: "No $concept_spec_financial_centres$"\n'
           ' SPEC_CENTRE_COL_NAME: "$concept_country$"\n'
           ' SPEC_CENTRE_COL_RANK_TT: "The [concept_spec_exchange]\'s place among all Exchanges, by score"\n'
           ' SPEC_CENTRE_COL_SCORE: "Score"\n'
           ' SPEC_CENTRE_COL_SCORE_TT: "How strong the [concept_spec_exchange] is. It grows with the money it can draw on, and wealth per head, '
           'Financial Districts, companies, finance technologies, [concept_rank], economic system and trust all change it. '
           + ("#v 100#! is the average of the world\'s top three." if ON else "#v 100#! is the leader\'s.") + '"\n'
           ' SPEC_CENTRE_COL_CALM: "Years of Calm"\n'
           ' SPEC_CENTRE_COL_CALM_TT: "Years since the last [concept_spec_financial_panic] in the [concept_country]"\n'
           f' SPEC_CENTRE_SCORE: "#v {score}#!"\n'
           f' SPEC_CENTRE_YEARS: "#v {yrs}#!"\n'
           ' SPEC_CENTRE_PANIC: "#N $concept_spec_financial_panic$#!"\n'
           f" SPEC_CENTRE_CALM: \"[SelectLocalization({P}.Var('spec_panic').IsSet, 'SPEC_CENTRE_PANIC', 'SPEC_CENTRE_YEARS')]\"\n"
           ' SPEC_CENTRE_N_NONE: "-"\n'
           f' SPEC_CENTRE_TT_OWN: "#header [Country.GetName]#!\\nNot one of the world\'s #v {PLACES}#! {centres}\\n'
           f'$TOOLTIP_DELIMITER$\\n{stats}"\n'
           ' spec_financial_centre: "Leading Exchange"\n'
           f' spec_financial_centre_desc: "The [concept_country]\'s [concept_spec_exchange] is one of the world\'s {centres}, and capital from every quarter seeks it out."\n')
    out += "".join(f' SPEC_CENTRE_N_{n}: "{n}"\n' for n in range(PLACES + 1, SHOWN + 1))
    for n in range(1, PLACES + 1):
        out += (f' SPEC_CENTRE_N_{n}: "#b {n}#!"\n'
                f' SPEC_CENTRE_TT_{n}: "#header [Country.GetName]#!\\n[concept_spec_financial_centre] #v ##{n}#!\\n'
                f'$TOOLTIP_DELIMITER$\\n{stats}\\n\\n[concept_prestige]: #P +{pct(n)}#!'
                + (f"\\nLending Limit: #P +{lim(n)}#! month{'s' * (lim(n) != '1')}\\n#weak The Lending Limit bonus needs [GetTechnology('central_banking').GetName] "
                   f"and [concept_spec_lending_standards] #v {cycle.LAX_WORDS[2]}#! or stricter.#!" if BRAKE else "") + '"\n')
    if not ON:
        return out
    limit = f"{P}.ScriptValue('spec_exch_limit')"
    lx = cycle.LAX_WORDS
    # lines of the Lending Limit's calculator (market_tab's SPEC_LEV_LIMIT), which ends at leverage.RUIN
    brake = (f" SPEC_EXCH_LIMIT: \"[SelectLocalization({gt(limit)}, 'SPEC_EXCH_LIMIT_ON', 'SPEC_EXCH_LIMIT_OFF')]\"\n"
             f' SPEC_EXCH_LIMIT_ON: "\\n[{limit}|+=0] from our place among the {centres}"\n'
             f' SPEC_EXCH_LIMIT_OFF: "\\nOur place among the {centres} adds nothing before [GetTechnology(\'central_banking\').GetName], '
             f'or while [concept_spec_lending_standards] are #v {lx[3]}#! or #v {lx[4]}#!."\n')
    return out + _exch_loc(score, rank, centres) + (brake if BRAKE else "") + (_pledge_loc() if PLEDGE_ON else "")


def _pick(expr, prefix, n):
    """Words for a whole-number variable 0..n: prefix_0 up to prefix_n."""
    picks = "".join(f"SelectLocalization(LessThan_CFixedPoint({expr}, {fx(i + 0.5)}), '{prefix}_{i}', " for i in range(n))
    return f"[{picks}'{prefix}_{n}'{')' * n}]"


def _exch_loc(score, rank, centres):
    """The Exchange: its row under Lending Standards in Budget > Banking, the Standing in the Financial Centres rows,
    its concept, the choice event and the toasts (notify.py)."""
    city = "[ROOT.GetCountry.GetCapital.GetCityHubName]"
    up = lambda x: f"{x - 1:+.0%}"
    stand = lambda scope: f"{scope}.Var('spec_exch_stand').GetValueWithDefault({fx(0)})"
    is_stand = lambda op, n: f"{op}_CFixedPoint({stand(P)}, {fx(n)})"
    pct = lambda name: f"#v [Subtract_CFixedPoint({P}.ScriptValue('{name}'), {fx(1)})|+%0]#!"
    words = ["Provincial", "National", "International", "World Centre"]
    credit = f"{P}.ScriptValue('spec_exch_credit')"
    moved = lambda hook: f"Not(EqualTo_CFixedPoint({P}.ScriptValue('spec_exch_{hook}'), {fx(1)}))"
    bank = "[GetTechnology('central_banking').GetName]"
    stock = "[GetTechnology('stock_exchange').GetName]"
    # trust as vanilla's calculators: this month's change a cause a line, as _trust and _crunch move it, then what
    # events would take at once. Trust points read as the share of CALM the bar shows
    share = lambda x: f"Divide_CFixedPoint({x}, {fx(CALM)})"
    loss = f"{P}.ScriptValue('spec_exch_loss')"
    calm = f"Not({P}.Var('spec_panic').IsSet)"
    sound = f"And({calm}, Not({P}.Var('spec_crunch').IsSet))" if CRUNCH else calm
    lax_set, lax, lx = f"{P}.Var('spec_lax').IsSet", f"{P}.Var('spec_lax').GetValueWithDefault({fx(0)})", cycle.LAX_WORDS
    low = lambda i: f"And({lax_set}, LessThan_CFixedPoint({lax}, {fx(cycle.LAX_CUTS[i])}))"
    month = ([("STRICT", f"And({sound}, {low(0)})", share(fx(TRUST_BY_LAX[0] * TRUST_MONTH)), f"#v {lx[0]}#! [concept_spec_lending_standards]"),
              ("CAUTIOUS", f"And({sound}, And(Not({low(0)}), {low(1)}))", share(fx(TRUST_BY_LAX[1] * TRUST_MONTH)),
               f"#v {lx[1]}#! [concept_spec_lending_standards]"),
              ("SOUND", f"And({sound}, And(Not({low(1)}), Or(Not({lax_set}), LessThan_CFixedPoint({lax}, {fx(cycle.LAX_CUTS[2])}))))",
               share(fx(TRUST_BY_LAX[2] * TRUST_MONTH)), f"#v {lx[2]}#! [concept_spec_lending_standards]"),
              ("RECKLESS", f"And({calm}, And({lax_set}, GreaterThanOrEqualTo_CFixedPoint({lax}, {fx(cycle.LAX_CUTS[3])})))",
               f"Multiply_CFixedPoint({share(fx(TRUST_BY_LAX[4] * TRUST_MONTH))}, {loss})", f"#v {lx[-1]}#! [concept_spec_lending_standards]")]
             if cycle.ON else [("SOUND", sound, share(fx(TRUST_MONTH)), "a calm month")])
    if CRUNCH:
        month.append(("CRUNCH", f"{P}.Var('spec_crunch').IsSet", f"Multiply_CFixedPoint({share(fx(-LINK_CRUNCH))}, {loss})",
                      "[concept_spec_bad_debts]"))
    change = fx(0)
    for _, cond, val, _ in month:
        change = f"Add_CFixedPoint({change}, Select_CFixedPoint({cond}, {val}, {fx(0)}))"
    # _gain stops at CALM and _lose at 0, so the total is what is left to either bound; the line shows the cut
    held = share(v("spec_centre_trust"))
    total = (f"Max_CFixedPoint(Min_CFixedPoint({change}, Subtract_CFixedPoint({fx(1)}, {held})), "
             f"Multiply_CFixedPoint({held}, {fx(-1)}))")
    cut = f"Subtract_CFixedPoint({total}, {change})"
    month_cut = f"Or({gt(cut, 0.0001)}, LessThan_CFixedPoint({cut}, {fx(-0.0001)}))"
    ends = {1: "correction", 2: "bust", 3: "collapse"}  # TRUST_END's severities
    end_val = lambda d: share(fx(d)) if d > 0 else f"Multiply_CFixedPoint({share(fx(d))}, {loss})"  # _lose takes spec_exch_loss
    # what trust does now: the score's multiplier (_parts) and Phase 5's links
    does = ([f"our score by #v x[{v('spec_xs_trust_v', 1)}|2]#!"]
            + ([f"[concept_spec_market_mood] swings by #v x[{P}.ScriptValue('spec_exch_mood')|2]#!"] if MOOD_REF else [])
            + ([f"[concept_spec_market_confidence] recovery by #v x[{P}.ScriptValue('spec_exch_recover')|2]#!"] if RECOVER_REF else []))
    does = ", ".join(does[:-1]) + " and " + does[-1] if len(does) > 1 else does[0]
    # 2026-11-22 rewrite: trust reads as a number out of 100 as Market Confidence does, every change in those points,
    # the tooltip in vanilla sentences (no "Label: value"); what builds it and what costs it, then last month's review
    points = lambda key: f"Multiply_CFixedPoint({share(v(key))}, {fx(100)})"
    pts = lambda x: f"Multiply_CFixedPoint({x}, {fx(100)})"
    changes = {c: points(f"spec_trust_{c}_last") for c in TRUST_CAUSES}
    net = points("spec_trust_change")
    nonzero = lambda x: f"Or({gt(x, 0.05)}, LessThan_CFixedPoint({x}, {fx(-0.05)}))"
    cause_words = {"goods": "boom endings", "panics": "[concept_spec_financial_panic]", "lending": "[concept_spec_lending_standards]",
                   "debts": "[concept_spec_bad_debts]", "rivals": "rival Exchanges", "chips": "our blue chip companies",
                   "charter": "changing our charter"}
    held_pts = pts(held)
    panic_now = f"Multiply_CFixedPoint(Multiply_CFixedPoint({P}.ScriptValue('spec_exch_panic_cut'), {loss}), {held_pts})"
    panic_rest = f"Multiply_CFixedPoint(Multiply_CFixedPoint({fx(PANIC_OVER_CUT)}, {loss}), Subtract_CFixedPoint({held_pts}, {panic_now}))"
    trust_loc = (' SPEC_EXCH_G_TRUST_TT: "#header [concept_spec_trust]#!\\n$TOOLTIP_DELIMITER$\\n'
                 f"Investors trust our [concept_spec_exchange] #v $SPEC_EXCH_TRUST$#! out of #v 100#!, so it is {TRUST_PICK()}. "
                 f"Trust multiplies {does}.\\n\\n"
                 f"It changes by #v [{pts(total)}|+=1]#! a month as things stand.#indent_newline:3 "
                 + "".join(f"[AddLocalizationIf({cond}, 'SPEC_TRUST_M_{key}')]" for key, cond, _, _ in month)
                 + f"[AddLocalizationIf({month_cut}, 'SPEC_TRUST_M_CUT')]#!"
                 + f"[AddLocalizationIf({P}.Var('spec_trust_change').IsSet, 'SPEC_TRUST_LAST_REVIEW')]"
                 + "\\n$TOOLTIP_DELIMITER$\\n"
                 + (f"Trust grows in calm months while [concept_spec_lending_standards] are #v {lx[2]}#! or stricter, and falls while "
                    f"they are #v {lx[-1]}#!. A Money Market charter softens its losses.\\n\\n" if cycle.ON else "Trust grows in calm months.\\n\\n")
                 + f"A [concept_spec_financial_panic] now would cost #N [{panic_now}|0]#! of it, and #N [{panic_rest}|0]#! more "
                 "if it ran its full course without a Bank Rescue."
                 + (" The higher our [concept_spec_leverage] when it starts, the more it costs." if leverage.ON else "")
                 + f"\\n\\nThe end of a boom in a good worth #v {MAIN_SHARE:.0%}#! or more of our trade moves it at once.#indent_newline:3 "
                 + "".join(f"\\n[{pts(end_val(d))}|+=1] from a [concept_spec_{ends[sev]}]" for sev, d in sorted(TRUST_END.items()))
                 + (f"\\n#v x{levers.ISSUE_TRUST:g}#! for the good of a Great Issue" if levers.ISSUE_ON else "")
                 + f"#!\\n\\nChanging our charter costs #N {CHARTER_COST:.0%}#! of it. Contests with rival Exchanges, their Press "
                 "Campaigns and our blue chip companies also move it."
                 + '\\n\\n#instruction Hover a level on the bar to see what it does.#!"\n'
                 + "".join(f' SPEC_TRUST_M_{key}: "\\n[{pts(val)}|+=1] from {label}"\n' for key, _, val, label in month)
                 + f' SPEC_TRUST_M_CUT: "\\n[{pts(cut)}|+=1] as it nears its limit"\n'
                 + f' SPEC_TRUST_LAST_REVIEW: "\\n\\nLast month it changed by #v [{net}|+=1]#!.#indent_newline:3 '
                 + "".join(f"[AddLocalizationIf({nonzero(changes[c])}, 'SPEC_TRUST_LAST_{c.upper()}')]" for c in TRUST_CAUSES)
                 + "#!\"\n"
                 + "".join(f' SPEC_TRUST_LAST_{c.upper()}: "\\n[{changes[c]}|+=1] from {cause_words[c]}"\n' for c in TRUST_CAUSES))
    # Phase 5's links, in the Exchange row's tooltip
    links = ((f"\\n[concept_spec_market_mood] swings: #v x[{P}.ScriptValue('spec_exch_mood')|2]#!" if MOOD_REF else "")
             + (f"\\n[concept_spec_market_confidence] recovery: #v x[{P}.ScriptValue('spec_exch_recover')|2]#!" if RECOVER_REF else "")
             + (f"[AddLocalizationIf({P}.Var('spec_crunch').IsSet, 'SPEC_EXCH_FX_CRUNCH')]" if CRUNCH else "")
             + (f"[AddLocalizationIf({is_stand('GreaterThan', 0.5)}, 'SPEC_EXCH_FX_LEAN')]" if LEAN else "")
             + (f"[AddLocalizationIf({is_stand('GreaterThan', 0.5)}, 'SPEC_EXCH_FX_IND')]" if LINKS and LINK_IND else ""))
    links_loc = ((f' SPEC_EXCH_FX_CRUNCH: "\\nUnder [concept_spec_bad_debts] the Standing cannot rise, and trust falls '
                  f'#N [Multiply_CFixedPoint({share(fx(LINK_CRUNCH))}, {loss})|%1]#! a month"\n'
                  if CRUNCH else "")
                 + (f' SPEC_EXCH_FX_LEAN: "\\n[concept_spec_market_mood] from prosperous companies: '
                    f"#v [{P}.ScriptValue('spec_exch_lean')|+=2]#! a month\"\n" if LEAN else "")
                 + (f' SPEC_EXCH_FX_IND: "\\nIndustrialists\' political strength: #P +[Multiply_CFixedPoint({stand(P)}, {fx(LINK_IND)})|%0]#!"\n'
                    ' spec_exch_industry: "Exchange Standing"\n'
                    ' spec_exch_industry_desc: "The Industrialists gain strength from the [concept_country]\'s [concept_spec_exchange]."\n'
                    if LINKS and LINK_IND else ""))
    nxt = [f"#instruction To reach National#!, we need a score of #v {NATIONAL:g}%#! of the top three's, #v {REG_NATIONAL:g}%#! of our region's leader's, "
           f"or a place among the {centres}",
           f"#instruction To reach International#!, we need a place among the #v {PLACES}#! {centres} or first place in our region, plus {stock}",
           f"#instruction To reach World Centre#!, we need a top #v {WORLD_PLACES}#! place among the {centres}, plus {bank}",
           f"#v World Centre#! is the top. We keep it while we hold a top #v {WORLD_PLACES}#! place"]
    known = ["None yet", "Commodity Exchange", "Money Market", "Share Market"]  # not "Stock Exchange": that is a vanilla technology
    tc = "[GetBuildingType('building_trade_center').GetName]"
    known_me = _pick(f"GetPlayer.MakeScope.Var('spec_exch_known').GetValueWithDefault({fx(0)})", "SPEC_EXCH_KNOWN", 3)
    sv = lambda name, f="0": f"#v [{P}.ScriptValue('{name}')|{f}]#!"
    # how far along each of the three is, in the Exchange row's tooltip
    earn = (f"Our Exchange becomes known for what the country builds, checked once a year:\\n"
            f"#v Commodity Exchange#!: {tc} levels {sv('spec_log_ktc')} of #v {EARN_TC:g}#!\\n"
            f"#v Share Market#!: companies with high [concept_prosperity] {sv('spec_log_kco')} of #v {EARN_CO:g}#!\\n"
            f"#v Money Market#!: years of sound lending #v [Divide_CFixedPoint({P}.ScriptValue('spec_log_ksnd'), {fx(12)})|1]#! "
            f"of #v {EARN_SOUND / 12:g}#!\\n"
            "The one furthest past its mark wins. Until one is reached, the Exchange keeps its name.\\n") if EARN and not NAMES_ON else ""
    def room(t):
        """The specialities (spec_pursue_slots) and contests (rivals' spec_rv_slots) a Standing holds."""
        parts = []
        if NAMES_ON:
            parts.append(f"#v {t + 1}#! specialit{'y' if t == 0 else 'ies'}")
        if RIVAL_ON:
            rv = __import__("rivals")
            c = rv.CONTESTS[t]
            parts.append(f"#v {c}#! contest{'s' * (c != 1)}")
        return "".join(f"\\n{p}" for p in parts)
    # 2026-11-19: sectioned as the speciality tooltips, value first, no "Label: value" lines
    about = ["Every Exchange begins here, trading for its own region.",
             "The country's own market, where its companies raise money.",
             "Foreign money trades here, and runs here when panics strike abroad.",
             "One of the few markets that set the world's prices."]
    tier_fx = lambda t: (f"#v {up(HYPE[t])}#! Investor Reaction to rising prices"
                         f"\\n#P +{PRESTIGE:.0%}#! [concept_prestige] while not among the {centres}"
                         + (f"\\n#P x{FLIGHT[t]:g}#! [concept_spec_capital_flight] received from panics abroad" if t >= 2 else "")
                         + (f"\\n#P {WORLD_SHELTER - 1:+.0%}#! losses from a [concept_spec_foreign_panic]\\n{_mod_words(WORLD_FX, chr(92) + 'n')}"
                            "\\n#v 1#! contest free of upkeep" if t == 3 else ""))
    reach = [[],
             [f"#v {NATIONAL:g}%#! of the top three's score, #v {REG_NATIONAL:g}%#! of our region's leader's, or a place among the {centres}"],
             [f"A top #v {PLACES}#! place among the {centres}, or first in our region", f"{stock} researched"],
             [f"A top #v {WORLD_PLACES}#! place among the {centres}", f"{bank} researched",
              f"#weak Kept while we hold a top #v {WORLD_PLACES}#! place.#!"]]
    hold = lambda t: f"[AddLocalizationIf(EqualTo_CFixedPoint(GetPlayer.MakeScope.Var('spec_exch_stand').GetValueWithDefault({fx(0)}), {fx(t)}), 'SPEC_EXCH_TIER_OURS')]"
    tier_tt = lambda t: (f"#header {words[t]}#!{hold(t)}\\n$TOOLTIP_DELIMITER$\\n{about[t]}"
                         + (f"\\n$TOOLTIP_DELIMITER$\\n#b Effects#!\\n{tier_fx(t)}" if t else "")
                         + f"\\n$TOOLTIP_DELIMITER$\\n#b Room#!{room(t)}"
                         + (f"\\n$TOOLTIP_DELIMITER$\\n#b To Reach It#!\\n" + "\\n".join(reach[t])
                            + ("\\n#weak It cannot rise while we carry [concept_spec_bad_debts].#!" if CRUNCH else "") if t else ""))
    card_fx = [f"Investor Reaction: #v {up(KNOWN_HYPE)}#!", f"Trust losses: #P {KNOWN_LOSS - 1:+.0%}#!",
               f"Up to #P {up(KNOWN_CREDIT)}#! credit lent into the [concept_investment_pool] each month"]
    card_by = [(f"{tc} levels", sv("spec_log_ktc"), EARN_TC),
               ("Years of sound lending", f"#v [Divide_CFixedPoint({P}.ScriptValue('spec_log_ksnd'), {fx(12)})|1]#!", EARN_SOUND / 12),
               ("Prosperous companies", sv("spec_log_kco"), EARN_CO)]
    ui = (' SPEC_EXCH_TIER_OURS: " #grey (ours)#!"\n'
          + "".join(f' SPEC_EXCH_TIER_TT_{t}: "{tier_tt(t)}"\n'
                  + f" SPEC_EXCH_TIER_N_{t}: \"Exchanges: #v [GetGlobalVariable('spec_exch_n_{t}').GetValue|0]#!\"\n" for t in range(4))
          + "".join(f' SPEC_EXCH_CARD_H_{n}: "#b $SPEC_EXCH_KNOWN_{n}$#!"\n' for n in (1, 2, 3))
          + "".join(f' SPEC_EXCH_CARD_N_{n}: "{what}\\n{now} of #v {mark:g}#!"\n'
                    f' SPEC_EXCH_CARD_TT_{n}: "#header {known[n]}#!\\n{card_fx[n - 1]}\\n$TOOLTIP_DELIMITER$\\n'
                    f'Earned from: {what}, {now} of #v {mark:g}#!"\n' for n, (what, now, mark) in enumerate(card_by, 1))
          + ' SPEC_EXCH_TIER_EMPTY: "No Exchange holds this Standing"\n'
          ' SPEC_CENTRE_COL_TRUST: "Trust"\n'
          ' SPEC_CENTRE_COL_RIVAL: "Compete"\n'
          ' SPEC_CENTRE_COL_RIVAL_TT: "Whether we contest that [concept_spec_exchange]. Click the button in its row to start a contest, '
          'or to end ours."\n'
          ' SPEC_CENTRE_COL_KNOWN: "Specialities"\n'
          ' SPEC_CENTRE_COL_KNOWN_TT: "The Paths to Renown the [concept_country]\'s [concept_spec_exchange] has chosen"\n'
          ' SPEC_CENTRE_COL_TRUST_TT: "How much investors trust the [concept_country]\'s [concept_spec_exchange], from #v 0#! to #v 100#!. '
          'Trust multiplies its score, and low trust raises what the [concept_country] pays to borrow."\n'
          ' SPEC_CENTRE_TRUST: "#v $SPEC_EXCH_TRUST$#!"\n'
          + ' SPEC_EXCH_SCORE_LBL: "[Concept(\'concept_spec_financial_centre\',\'$concept_spec_exchange$\')] Score"\n'
          + f' SPEC_EXCH_SCORE_NUM: "#b [{v("spec_centre_score")}|0]#!"\n'
          + _parts_loc()
          + "".join(f' SPEC_EXCH_TRUST_LV_{i}: "#{TRUST_COL[i]} {w}#!"\n' for i, w in enumerate(TRUST_LV))
          + "".join(f' SPEC_EXCH_TRUST_LV_DIM_{i}: "#weak {w}#!"\n' for i, w in enumerate(TRUST_LV))
          + "".join(f' SPEC_EXCH_TRUST_LV_TT_{i}: "#header {w}#!\\nTrust #v {i * band:g}#! to #v {(i + 1) * band:g}#!{_trust_words(i)}"\n'
                    for band in (100 / len(TRUST_LV),) for i, w in enumerate(TRUST_LV))
          + ' SPEC_EXCH_TRUST_LBL: "[concept_spec_trust]"\n'
          + f''' SPEC_EXCH_TRUST_NUM: "#b $SPEC_EXCH_TRUST$#!"\n'''
          + f''' SPEC_TRUST_REVIEW_DELTA: " ([Multiply_CFixedPoint(Divide_CFixedPoint({v("spec_trust_change")}, {fx(CALM)}), {fx(100)})|+=1])"\n'''
          + trust_loc
          + ' SPEC_H_KNOWN: "Specialities"\n'
          ' SPEC_H_KNOWN_TT: "#header Known For#!\\n$SPEC_EXCH_CARD_NOTE$"\n'
          f' SPEC_H_KNOWN_RIGHT: "#v {_pick(v("spec_exch_known"), "SPEC_EXCH_KNOWN", 3)}#!"\n'
          ' SPEC_EXCH_CARD_HELD: "#P Known for this#!"\n'
          ' SPEC_EXCH_CARD_NOTE: "An Exchange becomes known for what its country builds. Once a year, the one furthest past '
          'its mark gives the Exchange its name. Until one is reached, it keeps the name it has."\n')
    if NAMES_ON:
        ui = _names_loc(ui, known)
    if RIVAL_ON:
        ui += __import__("rivals").loc()
    return (ui + "".join(f' SPEC_EXCH_W_{i}: "{w}"\n' for i, w in enumerate(words))
            + "".join(f' SPEC_EXCH_NEXT_{i}: "{w}"\n' for i, w in enumerate(nxt))
            + "".join(f' SPEC_EXCH_KNOWN_{i}: "{w}"\n' for i, w in enumerate(known))
            + f' SPEC_CENTRE_STAND: "#v {_pick(stand(P), "SPEC_EXCH_W", 3)}#!"\n'
            f' SPEC_EXCH_STAND_ME: "{_pick(stand("GetPlayer.MakeScope"), "SPEC_EXCH_W", 3)}"\n'
            f' SPEC_EXCH_TRUST: "[Multiply_CFixedPoint(Divide_CFixedPoint({v("spec_centre_trust")}, {fx(CALM)}), {fx(100)})|0]"\n'
            ' SPEC_H_EXCH: "$SPEC_EFFECT_EXCH$"\n'
            ' SPEC_H_EXCH_TT: "#header $SPEC_EFFECT_EXCH$#!\\n$TOOLTIP_DELIMITER$\\n$concept_spec_exchange_desc$"\n'
            # named after its seat (_seat), the capital until it is first set
            + "".join(f' SPEC_EXCH_CITY{me}: "[SelectLocalization({c}.MakeScope.Var(\'spec_exch_seat\').GetState.IsValid, \'SPEC_EXCH_SEAT{me}\', '
                      f"'SPEC_EXCH_CAPITAL{me}')]\"\n"
                      f" SPEC_EXCH_SEAT{me}: \"[{c}.MakeScope.Var('spec_exch_seat').GetState.GetCityHubName]\"\n"
                      f' SPEC_EXCH_CAPITAL{me}: "[{c}.GetCapital.GetCityHubName]"\n' for me, c in (("", "Country"), ("_ME", "GetPlayer")))
            + ' SPEC_EFFECT_EXCH: "$SPEC_EXCH_CITY$ Exchange"\n'
            f" SPEC_EFFECT_EXCH_VALUE: \"$SPEC_CENTRE_STAND$[AddLocalizationIf({P}.Var('spec_centre_rank').IsSet, 'SPEC_EXCH_PLACE')]\"\n"
            f' SPEC_EXCH_PLACE: ", #v ##{rank}#!"\n'
            f' SPEC_EFFECT_EXCH_TT: "#header $SPEC_EFFECT_EXCH$: $SPEC_EFFECT_EXCH_VALUE$#!\\n'
            f'$TOOLTIP_DELIMITER$\\n[Concept(\'concept_spec_financial_centre\',\'$concept_spec_exchange$\')] Score: #v {score}#!\\n[concept_spec_trust]: #v $SPEC_EXCH_TRUST$#!\\n'
            f"{'Exchange Charter' if NAMES_ON else 'Known for'}: #v {_pick(v('spec_exch_known'), 'SPEC_EXCH_KNOWN', 3)}#!\\n{earn}$TOOLTIP_DELIMITER$\\n"
            f'Investor Reaction to rising prices: {pct("spec_exch_hype")}\\n'
            f"[SelectLocalization({is_stand('GreaterThan', 1.5)}, 'SPEC_EXCH_FX_FLIGHT', 'SPEC_EXCH_FX_FLIGHT_GP')]"
            f"[AddLocalizationIf(And({is_stand('GreaterThan', 0.5)}, Not({P}.Var('spec_centre_rank').IsSet)), 'SPEC_EXCH_FX_PRESTIGE')]"
            f"[AddLocalizationIf({moved('loss') if NAMES_ON else f"LessThan_CFixedPoint({P}.ScriptValue('spec_exch_loss'), {fx(1)})"}, 'SPEC_EXCH_FX_LOSS')]"
            f"[AddLocalizationIf({moved('credit') if NAMES_ON else gt(credit, 1)}, 'SPEC_EXCH_FX_CREDIT')]{links}"
            f"\\n$TOOLTIP_DELIMITER$\\n{_pick(stand(P), 'SPEC_EXCH_NEXT', 3)}\"\n"
            f' SPEC_EXCH_FX_FLIGHT: "Receives [concept_spec_capital_flight]: #v x[{P}.ScriptValue(\'spec_exch_flight\')|{1 if NAMES_ON else 0}]#!"\n'
            ' SPEC_EXCH_FX_FLIGHT_GP: "Receives [concept_spec_capital_flight] only as a [concept_great_power]"\n'
            f' SPEC_EXCH_FX_PRESTIGE: "\\n[concept_prestige]: #P +{PRESTIGE:.0%}#!"\n'
            + (f' SPEC_EXCH_FX_LOSS: "\\nTrust losses: {pct("spec_exch_loss")}"\n' if NAMES_ON else
             f' SPEC_EXCH_FX_LOSS: "\\nTrust losses: #P {KNOWN_LOSS - 1:+.0%}#!"\n')
            +
            (f' SPEC_EXCH_FX_CREDIT: "\\nCredit lent each month: {pct("spec_exch_credit")}"\n' if NAMES_ON else
               f' SPEC_EXCH_FX_CREDIT: "\\nCredit lent each month: #P {up(KNOWN_CREDIT)}#!"\n')
            +
            # the concept
            ' concept_spec_exchange: "Exchange"\n'
            ' concept_spec_trust: "Trust"\n'
            ' concept_spec_trust_desc: "How much investors believe in a [concept_country]\'s [concept_spec_exchange], from #v 0#! to #v 100#!.'
            '\\n\\nIt rises in calm months and falls with every [concept_spec_financial_panic], bust and collapse. '
            'Its level is #N Distrusted#!, Doubted, #v Respected#! or #P Trusted#!, and the lower levels raise what the [concept_country] pays to borrow."\n'
            ' concept_spec_exchange_desc: "A [concept_country]\'s $concept_spec_exchange$ is where its shares, bonds and credit change hands. Its score '
            "grows with the [concept_investment_pool] money it can draw on, and wealth per head, Financial Districts, companies, finance technologies, "
            "[concept_rank], economic system and trust all change it. The world's top three average #v 100#!, and the best #v "
            f"{PLACES}#! are the [Concept('concept_spec_financial_centre','$concept_spec_financial_centres$')]. Its Standing "
            "follows its score, rising from #v Provincial#! through #v National#! and "
            f"#v International#!, which needs {stock}, to #v World Centre#!, which needs {bank}. A higher Standing makes investors "
            "react more strongly to rising prices, and from #v International#! the Exchange receives [concept_spec_capital_flight].\\n\\n"
            + (NAMES_ABOUT if NAMES_ON else
               f"An Exchange becomes known for what its country builds, checked once a year. A #v Commodity Exchange#! gives "
               f"higher Investor Reaction and comes from {tc} levels. A #v Money Market#! gives smaller Trust losses and comes "
               "from years of sound lending. A #v Share Market#! gives more credit and comes from prosperous companies. "
               "The one furthest past its mark wins. Until one is reached, the Exchange keeps its name."
               if EARN else
               "Each time an Exchange first reaches a higher Standing, it chooses what it is to be known for, either a "
               "#v Commodity Exchange#! for higher Investor Reaction, a #v Money Market#! for smaller Trust losses, or a "
               "#v Share Market#! for more credit.")
            + "\\n\\nTrust rises in calm years" + (" under sound lending" if cycle.ON else "")
            + ", and falls with [Concept('concept_spec_financial_panic','$concept_spec_financial_panics$')]"
            + (", [concept_spec_bad_debts]" if CRUNCH else "")
            + f' and a [concept_spec_bust] or [concept_spec_collapse] in a good worth {MAIN_SHARE:.0%} or more of the market\'s trade. Low trust raises the interest rate on the [concept_country]\'s [concept_loans]."\n'
            ' spec_exch_world: "World Centre"\n'
            ' spec_exch_national: "Exchange Standing"\n'
            + "".join(f' spec_trust_{i}: "{TRUST_LV[i]} Exchange"\n spec_trust_{i}_desc: "The '
                      f'[concept_country]\'s [concept_spec_exchange] is #v {TRUST_LV[i]}#! by investors."\n' for i, f in enumerate(TRUST_FX) if f) +
            ' spec_exch_national_desc: "The [concept_country]\'s [concept_spec_exchange] is known well beyond its own city, though it '
            'is not yet one of the $concept_spec_financial_centres$."\n'
            + (f' SPEC_EXCH_KNOWN_ME: "{known_me}"\n' if EARN else _choice_loc(city)) + links_loc)


def _choice_loc(city):
    """The choice event spec_exchange.1 (not written with EARN)."""
    up = lambda x: f"{x - 1:+.0%}"
    return (f' spec_exchange.1.t: "The {city} Exchange"\n'
            f' spec_exchange.1.d1: "Dealing on the {city} Exchange has grown until it is the money market of the whole nation. '
            'Its members agree that it should make its name in one trade above all others, but not on which, and each '
            'faction has friends in the government."\n'
            f' spec_exchange.1.d2: "Foreign houses now keep agents on the floor of the {city} Exchange, and its prices are '
            'quoted in newspapers abroad. Its members ask what it should be known for beyond our borders."\n'
            f' spec_exchange.1.d3: "No market in the world moves more money than the {city} Exchange. Where it leads, the '
            'world\'s markets follow, and its members ask what it should be known for in every counting house from '
            'Calcutta to Valparaiso."\n'
            ' spec_exchange.1.f: "\\"A great exchange rests on one thing only: that a man\'s word, once given on its floor, is kept.\\""\n'
            ' spec_exchange.1.a: "Let the merchants deal in grain, cotton and coal."\n'
            ' spec_exchange.1.b: "Let the banks gather the nation\'s savings."\n'
            ' spec_exchange.1.c: "Let companies sell their shares to the public."\n'
            f' spec_exchange_known_1_tt: "Our [concept_spec_exchange] becomes known as a #v Commodity Exchange#!: its booms '
            f'run #v {KNOWN_HYPE - 1:.0%}#! hotter"\n'
            f' spec_exchange_known_2_tt: "Our [concept_spec_exchange] becomes a #v Money Market#!: every loss of '
            f'trust is #P {1 - KNOWN_LOSS:.0%}#! smaller"\n'
            f' spec_exchange_known_3_tt: "Our [concept_spec_exchange] becomes known as a #v Share Market#!: '
            f'up to #P {up(KNOWN_CREDIT)}#! credit lent into the [concept_investment_pool] each month"\n')


if __name__ == "__main__":
    import re
    script, words = effects(), loc()
    gui = section() + pledge_row() + ((standing_block() + known_block() + (names_block() + contest_block() if NAMES_ON else "")
                                       + (rival_block() if RIVAL_ON else "")) if ON else "")
    hooks = [boom_end("grain", sev, 0.333) for sev in TRUST_END] + [PANIC, PANIC_OVER, PLEDGE_COST, PLEDGE_RESCUE]
    rules = [triggers(), sguis(), PLEDGE_MESSAGE] if BUTTONS else []
    for s in (script, values(), gui, ON_ACTIONS, MODIFIER, events() if ON else "", *hooks, *rules):
        assert s.count("{") == s.count("}"), s
        assert not re.search(r"\d\.\d{4,}", s), s  # the engine fails to compare longer decimals
    if ON:
        assert script.count("spec_exch_stand value =") == 4 + bool(CRUNCH) and ("spec_exchange.1" in script and "spec_exchange.1.c" in words) != EARN
        # the Standing toasts replace the Financial Centre ones; each Standing has a word and a next step
        assert "spec_exch_down" in script and "spec_centre_gained" not in script and "SPEC_EXCH_NEXT_3" in words

        # a model of trust: CALM quiet months under sound Lending Standards fill it; a panic halves it, and halves it
        # again if it runs its course unrescued (Money Market: each loss is cut by KNOWN_LOSS)
        def panic(trust, rescued, loss=1):
            trust -= trust * 0.5 * loss
            return trust if rescued else trust - trust * 0.5 * loss
        trust = 0
        for _ in range(CALM):
            trust = min(CALM, trust + 1)
        assert trust == CALM and panic(trust, False) == CALM / 4 and panic(trust, True) == CALM / 2
        assert panic(trust, False, KNOWN_LOSS) == CALM * (1 - 0.5 * KNOWN_LOSS) ** 2
        if KNOWN_LOSS == 0.75:
            assert panic(trust, False, KNOWN_LOSS) == CALM * 0.625 ** 2  # Deposit Banks: a quarter off each loss
        # a new Exchange starts Respected; the Exchange's seat; leaving the market economy clears it; the 1st and 5th places
        # are read only when set
        assert f"min = {CALM / 2:g} max = {CALM}" in script and "spec_seat_fd = {" in values() and "spec_exch_clear = yes" in script
        clr = _exch_clear()  # Fix first #14: caught after spec_shut_down took the score and trust
        assert "has_variable = spec_exch_seat  #" in script and "remove_variable = spec_exch_seat\n" in clr
        assert all(f"remove_modifier = spec_trust_{i}\n" in clr for i, f in enumerate(TRUST_FX) if f) and "remove_variable = spec_xs_wealth_v\n" in clr
        assert "remove_modifier = spec_financial_centre" in clr
        assert all(f"remove_variable = {key}\n" in clr for key in ("spec_exch_stand", "spec_centre_rank", "spec_xs_regtop"))
        assert ("remove_variable = spec_exch_best" in clr) != EARN
        assert script.count("spec_exch_seat value =") == 2 and "SPEC_EXCH_CITY_ME" in words and "$SPEC_EXCH_CITY$ Exchange" in words
        assert "spec_seat_new" not in _seat("\t")  # no candidate scope shared by different countries' searches
        assert re.search(r"owner = \{\n\s+set_variable = \{ name = spec_exch_seat value = prev \}", _seat("\t"))
        assert seat({"cap": 3, "ny": 4}, "cap") == "cap" and seat({"cap": 3, "ny": 5}, "cap") == "ny" and seat({"cap": 0}, "cap") == "cap"
        assert "spec_rules" not in script + values() + words + gui and " SPEC_H_EXCH:" in words
        assert all(f"Select_CFixedPoint(GetGlobalVariable('spec_centre_{n}').IsSet" in gui for n in (WORLD_PLACES, PLACES))
        assert all(f"remove_modifier = spec_trust_{i}" in script for i, f in enumerate(TRUST_FX) if f) and len(TRUST_FX) == len(TRUST_LV)
        assert 0.5 + panic(trust, False) / CALM == 0.75  # the score's multiplier after an unrescued panic
    if BRAKE:
        assert "spec_debt" not in values() and "spec_exch_limit" in values() and "SPEC_EXCH_LIMIT_ON" in words
    if PLEDGE_ON:
        # a pledged panic leaves 3/4 of trust: no pledge in a panic, and the rescue runs when it starts, so the
        # unrescued second cut at its end cannot happen while pledged
        assert "spec_rescue = yes" in PLEDGE_RESCUE and "spec_exch_panic_cut" in PANIC and "spec_pledge_cost" in PLEDGE_COST
        assert "text = spec_pledge_panic_tt\n\t\tNOT = { has_variable = spec_panic }" in rules[0] and "spec_sgui_pledge_leave" in rules[1]
        assert "SPEC_PLEDGE_LEAVING" in words and "spec_pledge_make" in script
        # no money or a default: no rescue, the pledge stands (only _pledge_month's default breaks it), and the event says so
        assert "gold_reserves >= spec_rescue_cost" in PLEDGE_RESCUE and "spec_pledge_broken" not in PLEDGE_RESCUE and "spec_pledge_unmet" in PLEDGE_RESCUE
        assert "SPEC_PLEDGE_UNMET:" in words and PLEDGE_RESCUE.count("{") == PLEDGE_RESCUE.count("}")
    if ON:
        # trust lost at a panic's start: x0.8 at no leverage, x0.5 at the ruin line, half that cut when caught; the second
        # cut only for a panic that ran its full course
        assert abs(_panic_cut_model(0) - 0.2) < 1e-9 and abs(_panic_cut_model(leverage.RUIN + 3) - 0.5) < 1e-9
        assert abs(_panic_cut_model(leverage.RUIN, caught=True) - 0.25) < 1e-9 and "spec_exch_panic_cut = {" in values()
        assert "var:spec_panic <= 0" in PANIC_OVER and (not BRAKE or GATE in _limit_values())
    if levers.ISSUE_ON:
        # a Great Issue: the boom end's trust counts ISSUE_TRUST times (doubled Correction +4, Bust -12, Collapse -36
        # at the defaults), and the issue is cleared whether or not the good weighed enough to move trust
        got = {}
        for sev in TRUST_END:
            s = boom_end("grain", sev, 0.333)
            got[sev] = (sum(float(x) for x in re.findall(r"add = (-?[\d.]+) max", s))
                        - sum(float(x) for x in re.findall(r"subtract = \{ value = ([\d.]+) ", s)))
            assert s.rindex("remove_variable = spec_issue_grain") > s.rindex("spec_centre_trust") and "spec_issue_cool" in s
        assert got == {sev: d * levers.ISSUE_TRUST for sev, d in TRUST_END.items()}, got
        if TRUST_END == {1: 2, 2: -6, 3: -18} and levers.ISSUE_TRUST == 2:
            assert got == {1: 4, 2: -12, 3: -36}
        assert f"value = var:spec_issue_w\n\t\t\tmultiply = {levers.ISSUE_SCORE - 1:g}" in values() and "spec_log_issue" in values() + LOG
    if EARN:
        # the yearly tally: one branch per name, a panic run unrescued restarts the sound years, and the tooltip shows all three
        assert "spec_exchange." not in script + words and script.count("set_variable = { name = spec_exch_known value =") == 3 + 6 * bool(NAMES_ON)
        assert "spec_exch_sound value = 0" in PANIC_OVER and script.count("spec_log_ksnd add = 1") == 1 and "days = 365" in script
        assert all(f"\n{k} = {{" in values() for k in EARN_BY.values()) and "prosperity >= " in values()
        assert (NAMES_ON or all(f"ScriptValue('spec_log_{k}')" in words for k in ("ktc", "kco", "ksnd"))) and "SPEC_EXCH_KNOWN_ME" in words
        assert earned({1: 0.5, 2: 0.9, 3: 0.2}, 2) == 2   # none at its mark: keeps its name
        assert earned({1: 1.5, 2: 1.5, 3: 0}, 3) == 3     # a tie: keeps its name
        assert earned({1: 1.5, 2: 1.2, 3: 2}, 1) == 3     # furthest past its mark wins
        assert earned({1: 1, 2: 0, 3: 0}, 0) == 1
    if CRUNCH:
        # Bad Debts: trust falls and does not grow
        crunch_line = words.split(" SPEC_EXCH_FX_CRUNCH:")[1].split("\n")[0]  # the rate _lose takes: x spec_exch_loss
        assert script.count("NOT = { has_variable = spec_crunch } ") == 1 and f"{fx(LINK_CRUNCH)}, {fx(CALM)})" in crunch_line
        assert "ScriptValue('spec_exch_loss')" in crunch_line
    if NAMES_ON:
        # the AI picks its free speciality by its share of each leader, the first listed on a tie; a charter change
        # (the player's or the AI's) stops what the new charter forbids; the charter's cost is a straight cut
        assert ai_pick({"floor": 0.4, "sound": 0.9, "door": None}) == "sound" and ai_pick({"floor": 0.5, "sound": 0.5}) == "floor"
        assert ai_pick({"price": None}) is None and script.count("spec_ai_best value = -1") == 4 + 1  # 4 passes, the swap
        assert "GetGlobalVariable" not in script and "spec_exch_stand >= 1 has_variable = spec_pu_door" in script  # 2026-11-19: RANKED clash
        assert script.count("spec_pursue_stop_") >= len(NAMES) and f"multiply = {AI_SWITCH} }}" in script and "spec_ai_drop = 9 }" in script
        # the AI's charter: none or a dead path takes the fewest it can place on; a crowded one moves only to room
        y = {1: True, 2: True, 3: True}
        assert charter_pick({1: 5, 2: 1, 3: 1}, 0, y) == 2 and charter_pick({1: 5, 2: 1, 3: 0}, 1, {**y, 3: False}) == 2
        assert charter_pick({1: 4, 2: 3, 3: 3}, 1, y) == 1 and charter_pick({1: 2, 2: 0, 3: 0}, 1, {**y, 1: False}) == 2
        assert charter_pick({1: 0, 2: 0, 3: 0}, 0, {1: False, 2: False, 3: False}) == 0
        # charters 2 and 3, player and AI; the monthly Standing-fall passes and the player's at the fall itself
        assert script.count("spec_pursue_stop_price = yes") == 2 * 3 + 3 + 3 + 1  # + the AI's charter balance, its swap
        assert f"multiply = {1 - CHARTER_COST:g} }}" in script and "spec_exch_known_new" not in script
        assert "has_technology_researched = stock_exchange" in rules[0] and script.count(SHARES) > 2  # International's gate and the AI's charters
        # a field's leader is cleared once nobody qualifies; the bar's tooltip says so
        assert script.count("remove_global_variable = spec_ldv_") == len(NAMES) and "SPEC_NAME_NOLEAD" in words
        # a speciality's hooks follow its strength, the drawback as much as the benefit
        hook_count = sum(len(NAME_FX[k]) for k, *_ in NAMES)
        assert "has_variable = spec_has_" not in values() and values().count("multiply = { value = var:spec_pw_") == hook_count + len(NAMES)  # the hooks, and the cost of other pursuits
        assert words.count(f"[concept_spec_capital_flight] received {FLIGHT_IF}") == sum("flight" in NAME_FX[k] for k, *_ in NAMES)
    if NAMES_ON:
        # the hand-out: first places before seconds before thirds, no more than the Standing allows; every name
        # helps one hook and hurts another; the player's charter is a button, the AI's is still earned
        assert all(2 <= len(NAME_FX[k]) <= 3 and set(NAME_FX[k]) <= set(FX_WORDS) for k, *_ in NAMES)
        assert set(FX_WORDS) == {"hype", "flight", "loss", "credit", *NX_HOOKS}
        # monthly leader, runner-ups, the top three, the ones just ahead of a player (_near), and the AI's yardstick
        # (the top three and _near go by spec_rank: a tie keeps the place's holder)
        assert script.count("order_by = spec_name_") == len(NAMES) and script.count("order_by = spec_rank_") == len(NAMES)
        assert "name = spec_t3_door value = {" in script and script.count("set_variable = { name = spec_ldw_") == len(NAMES)
        # _near: counting down from our place, the j-th step lands on the one j places ahead
        assert "name = spec_rk_door value" in _near("") and "spec_ab" not in _near("") + words
        assert script.count("set_variable = spec_has_") == len(NAMES) and "is_player = no OR = { NOT = { has_variable = spec_exch_stand }" in script
        assert all(f"spec_sgui_charter_{n} = " in rules[1] and f"spec_can_charter_{n} = " in rules[0] for n in (1, 2, 3))
        assert all(f" SPEC_NAME_TT_{k}:" in words and f"\nspec_name_{k} = " in values() for k, *_ in NAMES)
        # each place's tooltip on its flag, not the country's, and one for outside the top three
        cb = contest_block()
        assert cb.count('blockoverride "tooltip"') == 3 * len(NAMES)
        # the row's tooltip in sections: passive effects, then every place's, then the flavour after a delimiter
        assert all(f"#b Ranking Effects#!\\n$SPEC_PURSUE_LV_{k}_3_ON$" in words and f"$SPEC_PURSUE_LV_{k}_0_ON$" in words
                   and f"\\n$TOOLTIP_DELIMITER$\\n#lore {FLAVOR[k]}#!" in words for k, *_ in NAMES)
        assert words.count(" SPEC_EXCH_CARD_NOTE:") == 1 and words.count(" SPEC_EXCH_CARD_TT_1:") == 1
        # the podium and the pursuit: three leaders a field by country, one tally up and the rest down
        assert script.count("set_global_variable = { name = spec_w_") == 3 * len(NAMES)
        assert all(f"spec_sgui_pursue_{k} = " in rules[1] and f" SPEC_NAME_STATUS_{k}:" in words for k, *_ in NAMES)
        assert all(f"spec_sgui_pursue_stop_{k} = " in rules[1] for k, *_ in NAMES)
        # only pursuers are ranked; a path nobody pursues still has a tally to measure against (the AI's choice)
        assert "has_variable = spec_pu_price" in _eligible("price", 1, "") and "spec_pu_" not in _eligible("price", 1, "", pursued=False)
        # the leader's tally only where Exchanges pursue it; the AI's yardstick elsewhere is never shown
        assert script.count("set_global_variable = { name = spec_ldv_") == len(NAMES) and script.count("name = spec_bestv_") == len(NAMES)
        assert "spec_bestv" not in words and "spec_bestv" not in contest_block()
        assert "spec_pursue_slots = {" in values() and script.count("spec_pursue_to_") >= 3 * len(NAMES)
        # slots by Standing, dropped last-chosen first; each pursuit's bonus by place; trust's effects by level
        assert script.count("var:spec_pursue_n > spec_pursue_slots") == 6 * len(NAMES) and "spec_pu_lock_door" in script
        # the save's Britain: two sets merged by a revolution get places 1..6, so the drop can trim them to the slots
        got = renumbered(dict(railway=1, price=1, floor=2, futures=2, sound=3, pockets=4), [k for k, *_ in NAMES])
        assert sorted(got.values()) == [1, 2, 3, 4, 5, 6] and got["sound"] == 5 and got["pockets"] == 6
        assert script.count("set_variable = { name = spec_pursue_n value = local_var:spec_pu_at }") == 1
        # the fall's toast names what it cost; the 5-year keep counts down in months and the Drop tooltip shows it
        assert script.count("set_variable = spec_pu_lost_") == 3 * len(NAMES) and "spec_pu_lost_door" in words + script
        assert script.index("set_variable = spec_pu_lost_door") < script.index("post_notification = spec_exch_down")
        assert f"name = spec_pu_lock_door value = {PURSUE_LOCK * 12}" in script and "name = spec_pu_lock_door add = -1" in script
        assert "days = " not in script.split("spec_pursue_to_door = {")[1].split("}\n\n")[0] and " SPEC_PURSUE_LEFT_door:" in words
        # while a slot is filled the rows that can be chosen are lit and say so; the row shows what each place gives
        assert gui.count("[And(GetVariableSystem.Exists('spec_pick_slot'), And(Country.IsLocalPlayer") == 2 * len(NAMES)  # click, light
        # the split (2026-11-19): the row has the path and its #lore line, the tally our place, the bar the race
        assert all(f"#lore {FLAVOR[k]}#!" in words and f" SPEC_NAME_VAL_TT_{k}:" in words and f"$SPEC_PURSUE_LV_{k}$" in words
                   for k, *_ in NAMES) and " SPEC_ROW_CLICK:" in words and "SPEC_NAME_PLACES_" not in words
        assert _pursue_fx("railway", 3) == [("building_railway_throughput_add", 0.12), ("building_group_bg_construction_laborers_mortality_mult", 0.08), ("state_infrastructure_mult", 0.1)]
        assert _pursue_fx("floor", 0) == [("state_trade_capacity_mult", 0.03), ("interest_group_ig_landowners_approval_add", -1)]
        assert "spec_pursue_harbour_3 = {" in MODIFIER
        assert _mod_words(TRUST_FX[0]).startswith("#N +10%#! $country_loan_interest_rate_mult$")
        assert _mod_words(TRUST_FX[3]) == "#P +2#! $interest_group_ig_industrialists_approval_add$"
        assert script.count("add_modifier = { name = spec_trust_") == sum(1 for f in TRUST_FX if f)
        assert "clamp_variable = { name = spec_pw_door min = 0 max = 1 }" in script
        assert "spec_now_" not in script and "set_global_variable = { name = spec_ld_door value = global_var:spec_w_door1 }" in script
        assert "is_country_alive = yes" in _eligible("price", 1, "")  # annexed leaders may retain their Exchange fields
        assert all(f"name = spec_sh_{k} value" in script and f" SPEC_NAME_QTY_{k}:" in words for k, *_ in NAMES)
        assert round(1 / PURSUE_MONTHS + 0.0005, 3) * PURSUE_MONTHS >= 1  # a pursuit reaches full strength
    if RIVAL_ON:
        assert "rival_raid.dds" in gui and " SPEC_RV_RAID_TT:" in words and "spec_rival_contest = yes" in script
        assert "spec_sgui_rival" not in gui + script + "".join(rules) and "spec_rival_pick" not in script
    if LINKS:
        # the links at the defaults: mood x1.5 to x0.5 and recovery x0.75 to x1.5 over no trust to full; the lean
        # stays within 0.3 either way; Bad Debts cap the Standing at last month's
        if (LINK_MOOD, LINK_RECOVER, LINK_PROSPER) == (1, 1, 0.2):
            assert links(0, 1) == (1.5, 0.75, 0) and links(CALM, 1) == (0.5, 1.5, 0) and links(CALM / 2, 2)[:2] == (1, 1.125)
        assert links(0, 99)[2] == 0.3 >= links(0, 1.5)[2] and links(0, 0)[2] == 0
        assert all(f"\n{k} = {{" in values() for k in ("spec_exch_mood", "spec_exch_recover")) and bool(LEAN) == ("SPEC_EXCH_FX_LEAN" in words) == ("spec_exch_lean" in values())
        assert not CRUNCH or ("value = local_var:spec_exch_was" in script and "SPEC_EXCH_FX_CRUNCH" in words)
        assert ("spec_exch_industry" in MODIFIER + script + words) == bool(LINK_IND)
    assert script.count("ordered_country") == 1 + SHOWN * ON + (1 + len(REGIONS) if ON else 1) + 2 * len(NAMES) * bool(NAMES_ON)
    assert f"max = {PLACES}\n\t\t\tcheck_range_bounds = no" in script and "name = spec_centre_new value = global_var:spec_centre_next" in script
    if ON:
        assert TOP.count("ordered_country") == 1 and "max = 3" in TOP and "position =" not in TOP
        assert "ordered_country" not in _leaders("\t") and _leaders("\t").count("max = global_var:spec_t2_") == len(NAMES)
    assert "+10%" in words and "-2%" in words  # the first and the last place at the default step
    keys = {line.split(":")[0].strip() for line in words.splitlines()}
    used = {k.strip('"') for k in __import__("re").findall(r'"SPEC_[A-Z0-9_]+"', gui)}
    assert used <= keys, used - keys
    picked = set(__import__("re").findall(r"'(SPEC_\w+)'", words))  # Select/AddLocalizationIf picks (2026-11-19: SPEC_ORD_<key>_<n> missing)
    assert {p for p in picked if not p.startswith("SPEC_DATE_")} <= keys, sorted(picked - keys)[:8]  # dates: market_tab.py
    print("ok")
