"""The world's Financial Centres: the PLACES largest money markets, ranked once a month and listed in the Speculation
tab. A place on the list gives prestige and cheaper loans; a Financial Panic halves a market's score, which then grows
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
import stories
import tuning
import vanilla_ties
from market_tab import P, W, BAR_W, fx, gt, v, ind, header, block, heads, sg

PLACES = 5
MONTHS = tuning.get("CENTRE_MONTHS", 6)
CALM = tuning.get("CENTRE_CALM", 120)
STEP = tuning.get("CENTRE_STEP", 0.02)  # prestige and loan interest for each place from the bottom: 5 steps for the first
INCOME = "spec_lev_income" if leverage.ON else "spec_pool_month"
ROW_H = 35  # vanilla's ranked country rows
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
TRUST_END = tuning.get("EXCH_TRUST_END", {1: 2, 2: -6, 3: -18})  # a boom's ending: Correction, Bust, Collapse
KNOWN_HYPE = tuning.get("EXCH_KNOWN_HYPE", 1.1)   # 1 Commodity Exchange: its booms
KNOWN_LOSS = tuning.get("EXCH_KNOWN_LOSS", 0.75)  # 2 Deposit Banks: share of each loss of trust it takes
KNOWN_CREDIT = tuning.get("EXCH_KNOWN_CREDIT", 1.1)  # 3 Stock Exchange: credit lent each month
WORLD_PLACES = tuning.get("EXCH_WORLD_PLACES", 3)  # beta.12: the top three are World Centres (was the first alone)
WORLD_FX = tuning.get("EXCH_WORLD_FX", [["country_loan_interest_rate_mult", -0.1], ["country_influence_mult", 0.1]])
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
PLEDGE_FLIGHT = tuning.get("EXCH_PLEDGE_FLIGHT", 1.5)   # capital flight received while pledged
PLEDGE_SHARE = tuning.get("EXCH_PLEDGE_COST", 0.75)     # the rescue's cost while pledged
PLEDGE_NOTICE = tuning.get("EXCH_PLEDGE_NOTICE", 24)    # months of notice to withdraw
PLEDGE_DEBT = tuning.get("EXCH_PLEDGE_DEBT", 0.5)       # most scaled_debt to make the pledge
PLEDGE_BREAK = tuning.get("EXCH_PLEDGE_BREAK", {"conf": 15, "legit": 10})  # a default breaks it: confidence, legitimacy (5 years)
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
LINK_PROSPER = tuning.get("EXCH_LINK_PROSPER", 0.2)  # Market Mood a month per Share Market tally past its mark, within +-0.3
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
                 "\t\telse = {\n\t\t\tset_variable = { name = spec_pledge_unmet days = 30 }\n\t\t}\n\t}\n") if PLEDGE_ON else ""
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


def boom_end(g, sev, share, t="\t\t\t\t"):
    """In g's boom-ending branch, country scope, for goods that matter to the market (the boom-end toast's gate)."""
    if not ON:
        return ""
    d = TRUST_END[sev]
    apply = lambda d, t: _gain(d, t) if d > 0 else _lose(-d, t)
    if not levers.ISSUE_ON:
        return f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_centre_trust spec_weight_{g} >= {share:.3f} }}\n" + apply(d, t + "\t") + f"{t}}}\n"
    # a Great Issue on g (levers.py): the result counts ISSUE_TRUST times, then the issue is over and the market rests
    return (f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_centre_trust spec_weight_{g} >= {share:.3f} }}\n" + apply(d, t + "\t")
            + f"{t}\tif = {{\n{t}\t\tlimit = {{ has_variable = spec_issue_{g} }}\n" + apply(d * (levers.ISSUE_TRUST - 1), t + "\t\t") + f"{t}\t}}\n{t}}}\n"
            f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_issue_{g} }}\n{t}\tremove_variable = spec_issue_{g}\n{t}\tremove_variable = spec_issue\n"
            f"{t}\tset_variable = {{ name = spec_issue_cool value = {levers.COOL_MONTHS} }}\n"  # pulses left (levers.spec_issue_clock)
            f"{t}\tspec_update_levers = yes\n{t}}}\n")  # the Restrain/Encourage buttons see the issue gone now, not next month


HALF = "var:spec_centre_trust multiply = 0.5"
# in spec_start_panic; and in spec_end_panic before spec_rescued and spec_panic are cleared, so a rescued panic, or one that
# ended early as confidence came back, loses trust only once
PANIC = (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_centre_trust }}\n"
         f"{_lose('var:spec_centre_trust multiply = spec_exch_panic_cut', chr(9) * 2)}\t}}\n") if ON else ""
PANIC_OVER = ("\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_centre_trust\n\t\t\tNOT = { has_variable = spec_rescued }\n"
              "\t\t\tvar:spec_panic <= 0\n\t\t}\n"
              f"{_lose(HALF, chr(9) * 2)}" + ("\t\tset_variable = { name = spec_exch_sound value = 0 }\n" if EARN else "")
              + "\t}\n") if ON else ""
# a quiet month under sound Lending Standards counts towards Deposit Banks
SOUND = lambda t: f"{t}set_variable = {{ name = spec_exch_sound value = {{ value = spec_log_ksnd add = 1 }} }}\n" if EARN else ""


def _issue_score():
    """In spec_centre_size: a Great Issue running (levers.py). ponytail: inline, no spec_issue_score value."""
    return (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_issue }}\n\t\tmultiply = {levers.ISSUE_SCORE:g}\n\t}}\n"
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
            f"\t\t\tadd = var:spec_xs_inc\n\t\t}}\n\t}}\n\tmultiply = {REACH:g}\n{unit}\tmax = spec_xs_own\n}}\n"
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
    step = (f"{t}set_local_variable = {{ name = spec_sq value = {{ value = local_var:spec_sq_x divide = local_var:spec_sq "
            f"add = local_var:spec_sq multiply = 0.5 }} }}\n")
    return (f"{t}set_local_variable = {{ name = spec_sq_x value = {{ value = {src} min = 0 }} }}\n"
            f"{t}set_local_variable = {{ name = spec_sq value = {{ value = local_var:spec_sq_x divide = 40 add = 2 }} }}\n"
            + step * SQ_STEPS + f"{t}set_variable = {{ name = {dst} value = local_var:spec_sq }}\n")


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
            + "\n" + _by_stand("spec_exch_loss", {}, _known(2, f"value = {KNOWN_LOSS:g}") + _name_tail("loss"))
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
    # ponytail: the lean only for an Exchange of National Standing or better, so countries without companies are not
    # pulled down; the 0.3 bound is fixed, LINK_PROSPER is the knob
    return ("\n# the Exchange's links (centres.py)\n"
            + trust("spec_exch_mood", "subtract = 0.5", f"multiply = {-LINK_MOOD:g}", "add = 1")
            + trust("spec_exch_recover", "multiply = 0.75", "subtract = 0.25", f"multiply = {LINK_RECOVER:g}", "add = 1")
            + ("" if not LEAN else
            "spec_exch_lean = {\n\tvalue = 0\n\tif = {\n\t\tlimit = {\n\t\t\thas_variable = spec_exch_stand\n\t\t\tvar:spec_exch_stand >= 1\n\t\t}\n"
            f"\t\tvalue = spec_earn_co\n\t\tsubtract = 1\n\t\tmultiply = {LINK_PROSPER:g}\n\t\tmin = -0.3\n\t\tmax = 0.3\n\t}}\n}}\n"))


def links(trust, tally):
    """Python model of _links_values for the self-check: (mood scale, recovery scale, lean) for a National Exchange."""
    t = trust / CALM
    return 1 - LINK_MOOD * (t - 0.5), 1 + LINK_RECOVER * (t * 0.75 - 0.25), max(-0.3, min(0.3, (tally - 1) * LINK_PROSPER))


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
CHARTER_COST = tuning.get("EXCH_CHARTER_COST", 0.5)   # share of trust a change of charter costs (the first is free)
CHARTER_LOCK = tuning.get("EXCH_CHARTER_LOCK", 10)    # years before the charter can change again
# key, title, the charter it needs (0: any); the hand-out prefers them in this order
NAMES = [("price", "Price Setter", 1), ("harbour", "Safe Harbor", 2), ("companies", "Home of Great Companies", 3),
         ("futures", "Futures Pit", 1), ("lender", "Lender to Nations", 2), ("railway", "Railway Mania", 3),
         ("floor", "Busy Floor", 0), ("sound", "Sound Lending", 0), ("pockets", "Deep Pockets", 0), ("door", "Open Door", 0)]
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
    "price": "\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_mv_total }\n\t\tvalue = var:spec_mv_total\n\t}\n",
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
               "\t\t\t}\n\t\t\tadd = 1\n\t\t}\n\t}\n"),
    "railway": f"{vanilla_ties.levels('building_railway')}\tadd = {{\n{vanilla_ties.levels('building_port')}\t}}\n"}
SLOTS = "var:spec_exch_stand"  # names an Exchange may hold: National 1, International 2, World Centre 3
# the state may pursue names (var:spec_pu_<key>, its place in the order chosen), one more than its Exchange's Standing;
# each is held PURSUE_LOCK years once chosen, and builds up over PURSUE_MONTHS
# (var:spec_pw_<key>, 0 to 1) and fades as slowly once stopped. At full strength its tally counts PURSUE_BOOST, and
# every other tally PURSUE_COST for each such pursuit
PURSUE_BOOST = tuning.get("EXCH_PURSUE_BOOST", 1.25)
PURSUE_COST = tuning.get("EXCH_PURSUE_COST", 0.9)
PURSUE_MONTHS = tuning.get("EXCH_PURSUE_MONTHS", 12)
PURSUE_LOCK = tuning.get("EXCH_PURSUE_LOCK", 5)  # years a pursuit is held once chosen
# what a pursuit gives, by our place in its field at the yearly contest (outside the top three, third, second, first):
# the first modifier once for each step, the second at first place only; scaled by how far the pursuit has built up
PURSUE_FX = tuning.get("EXCH_PURSUE_FX", {
    # [grows with our place, first place only, *costs]. beta.12: each path themed to what it is won by; every path
    # carries a cost, and its costs grow with the place too (COST_SCALE), so leading a path stirs more resentment
    "floor": [["state_trade_capacity_mult", 0.03], ["building_trade_center_throughput_add", 0.1],
              ["interest_group_ig_landowners_approval_add", -1]],  # merchants over the land
    "sound": [["country_loan_interest_rate_mult", -0.015], ["interest_group_ig_petty_bourgeoisie_approval_add", 2],
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
    "lender": [["country_leverage_generation_mult", 0.05], ["country_loan_interest_rate_mult", -0.05],
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
TRUST_FX = tuning.get("CENTRE_TRUST_FX", [
    [["country_loan_interest_rate_mult", 0.1], ["interest_group_ig_industrialists_approval_add", -2]],
    [["country_loan_interest_rate_mult", 0.05]], [],
    [["country_loan_interest_rate_mult", -0.05], ["interest_group_ig_industrialists_approval_add", 2]]])
ICON = lambda k: icons.path(f"name_{k}")  # icons.py: our painting, else its vanilla stand-in
ROUND = "gfx/interface/backgrounds/round_button_bg.dds"  # vanilla's gold-rimmed disc (company_panel's charter badges): order numbers
LEAD_HOLD = tuning.get("EXCH_LEAD_HOLD", 3)  # months a challenger must stay ahead to become a field's leader


def _name_tail(hook):
    """A speciality's two hooks, the good and the bad alike, follow its strength (spec_pw_<key>): they build up over
    PURSUE_MONTHS once chosen and fade as slowly once dropped, as its modifiers do."""
    if not NAMES_ON:
        return ""
    return "".join(f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pw_{k} var:spec_pw_{k} > 0 }}\n"
                   f"\t\tmultiply = {{ value = var:spec_pw_{k} multiply = {round(NAME_FX[k][hook] - 1, 4):g} add = 1 }}\n\t}}\n"
                   for k, *_ in NAMES if hook in NAME_FX[k])


def _name_values():
    tail = lambda k: (f"\tif = {{\n\t\tlimit = {{ has_variable = spec_pw_sum }}\n"
                      f"\t\tmultiply = {{ value = var:spec_pw_{k} multiply = {PURSUE_BOOST - 1:g} add = 1 }}\n"
                      f"\t\tmultiply = {{ value = var:spec_pw_sum subtract = var:spec_pw_{k} multiply = {PURSUE_COST - 1:g} add = 1 }}\n\t}}\n")
    return "\n# what each name is won by (centres.py)\n" + "".join(
        f"spec_name_{k} = {{\n{NAME_BY[k]}{tail(k)}}}\n" for k, *_ in NAMES) + _pursue_values()


def _names_drop(t):
    """Take this country's places in the fields (its chosen specialities stay)."""
    if not NAMES_ON:
        return ""
    return "".join(f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_lead_{k} }}\n{t}\tremove_variable = spec_lead_{k}\n{t}}}\n"
                   for k, *_ in NAMES)


def _names(t="\t"):
    """In the ranking pass, once a year: the three leaders of each field among Exchanges of National Standing or
    better get var:spec_lead_<key> 1..3, which sets what a chosen speciality gives. ponytail: ties fall as
    ordered_country lists them."""
    if not NAMES_ON:
        return ""
    T = lambda n: t + "\t" * n
    lead = ""
    for k, _, ch in NAMES:
        lead += (f"{T(1)}set_global_variable = {{ name = spec_top_{k} value = 1 }}\n"
                 f"{T(1)}every_country = {{\n{T(2)}limit = {{ has_variable = spec_lead_{k} }}\n"
                 f"{T(2)}remove_variable = spec_lead_{k}\n{T(1)}}}\n"
                 + "".join(f"{T(1)}if = {{\n{T(2)}limit = {{ has_global_variable = spec_w_{k}{p} }}\n"
                           f"{T(2)}remove_global_variable = spec_w_{k}{p}\n{T(1)}}}\n" for p in (1, 2, 3)))
        slots = "".join(f"{T(2)}if = {{\n{T(3)}limit = {{ global_var:spec_name_next = {pos} }}\n"
                        f"{T(3)}set_global_variable = {{ name = spec_w_{k}{pos} value = this }}\n"
                        + (f"{T(3)}set_global_variable = {{ name = spec_top_{k} value = {{ value = spec_name_{k} min = 1 }} }}\n"
                           if pos == 1 else "") + f"{T(2)}}}\n" for pos in (1, 2, 3))
        lead += (f"{T(1)}set_global_variable = {{ name = spec_name_next value = 1 }}\n"
                 f"{T(1)}ordered_country = {{\n{T(2)}limit = {{\n{_eligible(k, ch, T(3))}{T(2)}}}\n"
                 f"{T(2)}order_by = spec_name_{k}\n{T(2)}max = 3\n{T(2)}check_range_bounds = no\n"
                 f"{T(2)}set_variable = {{ name = spec_lead_{k} value = global_var:spec_name_next }}\n"
                 f"{slots}{T(2)}change_global_variable = {{ name = spec_name_next add = 1 }}\n{T(1)}}}\n"
                 f"{T(1)}remove_global_variable = spec_name_next\n")
    return _leaders(t) + (f"{t}# each field's three leaders, once a year (centres.py); the AI chooses its specialities then\n"
            f"{t}if = {{\n{T(1)}limit = {{\n{T(2)}NOT = {{ has_global_variable = spec_names_year }}\n"
            f"{T(2)}any_country = {{\n{T(3)}has_variable = spec_exch_stand\n{T(3)}var:spec_exch_stand >= 1\n{T(2)}}}\n{T(1)}}}\n"
            f"{T(1)}set_global_variable = {{ name = spec_names_year days = 365 }}\n{_charter_balance(T(1))}{lead}"
            f"{T(1)}every_country = {{\n{T(2)}limit = {{ has_variable = spec_exch_stand }}\n"
            + _pursue_ai(T(2)) + f"{T(1)}}}\n{t}}}\n")


CHARTER_ROOM = 3  # places each charter path hands out: the AI spreads its charters to fill them


def _charter_balance(t):
    """Yearly, before the leaders: an AI Exchange of National Standing or better with no charter, or one whose path it
    cannot place on (a tally of 0), or one of more than CHARTER_ROOM holders while another charter has room, takes the
    charter with the fewest holders among those whose path it can place on (a tie: the first listed). The counts
    (spec_chn_<n>, holders that can place) move as it goes, so the AI fills every charter path's three places."""
    path = {c: k for k, _, c in NAMES if c}
    can = lambda n: (f"{SHARES} " if n == 3 else "") + f"spec_name_{path[n]} > 0"
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


def _eligible(k, ch, t):
    """An Exchange in the running for name k: National Standing or better, the charter if the name needs one."""
    return (f"{t}is_country_alive = yes\n{t}has_variable = spec_exch_stand\n{t}var:spec_exch_stand >= 1\n"
            + (f"{t}var:spec_exch_known ?= {ch}\n" if ch else "") + f"{t}spec_name_{k} > 0\n")


def _leaders(t):
    """Monthly, in the ranking pass: each field's leader (global spec_ld_<key>) and its tally (spec_ldv_<key>).
    The top tally this month only takes the lead once it has stayed on top LEAD_HOLD months running
    (spec_ch_<key>, spec_chm_<key>); a leader that drops out of the running loses it at once."""
    out = f"{t}# each field's leader (centres.py): a challenger must stay on top {LEAD_HOLD} months to take it\n"
    for k, _, ch in NAMES:
        now, u, w = f"scope:spec_now_{k}", t + "\t", t + "\t\t"
        clear = (f"{w}if = {{\n{w}\tlimit = {{ has_global_variable = spec_ch_{k} }}\n"
                 f"{w}\tremove_global_variable = spec_ch_{k}\n{w}\tremove_global_variable = spec_chm_{k}\n{w}}}\n")
        take = f"{w}set_global_variable = {{ name = spec_ld_{k} value = {now} }}\n{clear}"
        out += (f"{t}ordered_country = {{\n{u}limit = {{\n{_eligible(k, ch, w)}{u}}}\n{u}order_by = spec_name_{k}\n"
                f"{u}position = 0\n{u}check_range_bounds = no\n"  # without a position it walks them all: the last, lowest, stuck
                f"{u}save_temporary_scope_as = spec_now_{k}\n{t}}}\n"
                f"{t}if = {{\n{u}limit = {{ exists = {now} }}\n"
                # Trigger OR blocks still evaluate missing scope links. Handle absent or annexed leaders before
                # any dereference; a surviving leader that lost its eligibility is handled in the next branch.
                f"{u}if = {{\n{w}limit = {{ NOT = {{ exists = global_var:spec_ld_{k} }} }}\n{take}{u}}}\n"
                f"{u}else_if = {{\n{w}limit = {{\n{w}\tNOT = {{\n{w}\t\tglobal_var:spec_ld_{k} = {{\n"
                f"{_eligible(k, ch, w + chr(9) * 3)}{w}\t\t}}\n{w}\t}}\n{w}}}\n{take}{u}}}\n"
                f"{u}else_if = {{\n{w}limit = {{ global_var:spec_ld_{k} = {now} }}\n{clear}{u}}}\n"
                f"{u}else = {{\n{w}if = {{\n{w}\tlimit = {{\n{w}\t\thas_global_variable = spec_ch_{k}\n"
                f"{w}\t\tglobal_var:spec_ch_{k} = {now}\n{w}\t}}\n"
                f"{w}\tchange_global_variable = {{ name = spec_chm_{k} add = 1 }}\n{w}}}\n"
                f"{w}else = {{\n{w}\tset_global_variable = {{ name = spec_ch_{k} value = {now} }}\n"
                f"{w}\tset_global_variable = {{ name = spec_chm_{k} value = 1 }}\n{w}}}\n"
                f"{w}if = {{\n{w}\tlimit = {{ global_var:spec_chm_{k} >= {LEAD_HOLD} }}\n"
                f"{w}\tset_global_variable = {{ name = spec_ld_{k} value = {now} }}\n"
                f"{w}\tremove_global_variable = spec_ch_{k}\n{w}\tremove_global_variable = spec_chm_{k}\n{w}}}\n{u}}}\n"
                f"{u}global_var:spec_ld_{k} = {{\n"
                f"{w}set_global_variable = {{ name = spec_ldv_{k} value = {{ value = spec_name_{k} min = 0.01 }} }}\n{u}}}\n"
                + "".join(f"{u}set_global_variable = {{ name = spec_t{p}_{k} value = 0 }}\n" for p in (2, 3))
                + f"{u}ordered_country = {{\n{w}limit = {{\n{_eligible(k, ch, w + chr(9))}"
                f"{w}\tNOT = {{ this = global_var:spec_ld_{k} }}\n{w}}}\n{w}order_by = spec_name_{k}\n{w}max = 2\n{w}check_range_bounds = no\n"
                f"{w}if = {{\n{w}\tlimit = {{ global_var:spec_t2_{k} = 0 }}\n"
                f"{w}\tset_global_variable = {{ name = spec_t2_{k} value = {{ value = spec_name_{k} max = global_var:spec_ldv_{k} }} }}\n{w}}}\n"
                f"{w}else = {{\n{w}\tset_global_variable = {{ name = spec_t3_{k} value = {{ value = spec_name_{k} max = global_var:spec_t2_{k} }} }}\n{w}}}\n"
                f"{u}}}\n{t}}}\n"
                # nobody is in the running: no leader, nothing to measure against
                f"{t}else_if = {{\n{u}limit = {{ has_global_variable = spec_ld_{k} }}\n"
                f"{u}remove_global_variable = spec_ld_{k}\n{u}remove_global_variable = spec_ldv_{k}\n"
                f"{u}if = {{\n{w}limit = {{ has_global_variable = spec_ch_{k} }}\n"
                f"{w}remove_global_variable = spec_ch_{k}\n{w}remove_global_variable = spec_chm_{k}\n{u}}}\n{t}}}\n")
    return out


def _shares(t):
    """Monthly, for the player and every Exchange of National Standing or better: our tally as a share of each
    field's leader (spec_sh_<key>, up to 1.5) and last month's (spec_shl_<key>), for the contest bars."""
    if not NAMES_ON:
        return ""
    u, w = t + "\t", t + "\t\t"
    each = "".join(f"{u}if = {{\n{w}limit = {{ has_global_variable = spec_ldv_{k} }}\n"
                   f"{w}if = {{\n{w}\tlimit = {{ has_variable = spec_sh_{k} }}\n"
                   f"{w}\tset_variable = {{ name = spec_shl_{k} value = var:spec_sh_{k} }}\n{w}}}\n"
                   f"{w}set_variable = {{ name = spec_sh_{k} value = {{ value = spec_name_{k} divide = global_var:spec_ldv_{k} max = 1.5 }} }}\n"
                   f"{u}}}\n{u}else_if = {{\n{w}limit = {{ has_variable = spec_sh_{k} }}\n"
                   f"{w}remove_variable = spec_sh_{k}\n{w}remove_variable = spec_shl_{k}\n{u}}}\n" for k, *_ in NAMES)
    return (f"{t}if = {{\n{u}limit = {{\n{w}has_variable = spec_exch_stand\n"
            f"{w}OR = {{\n{w}\tis_player = yes\n{w}\tvar:spec_exch_stand >= 1\n{w}}}\n{u}}}\n{each}{t}}}\n")


def _charter_effects():
    """The state grants a charter: free the first time, then at a cost in trust (cut directly, not through the losses
    multiplier); the specialities only the old charter allowed are stopped (_charter_stop, also on the AI's yearly
    change of charter)."""
    return "".join(f"spec_charter_to_{n} = {{\n\tif = {{\n\t\tlimit = {{\n\t\t\thas_variable = spec_exch_known\n"
                   f"\t\t\thas_variable = spec_centre_trust\n\t\t}}\n"
                   f"\t\tset_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_trust "
                   f"multiply = {1 - CHARTER_COST:g} }} }}\n"
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
    return ("spec_pursue_slots = {\n\tvalue = 1\n\tif = {\n\t\tlimit = { has_variable = spec_exch_stand }\n"
            "\t\tadd = var:spec_exch_stand\n\t}\n}\n")


def _pursue_fx(k, lv):
    """The modifiers a pursuit of `k` gives at level lv (0 outside the top three .. 3 first)."""
    (m, base), extra, *costs = PURSUE_FX[k]
    return [(m, round(base * (lv + 1), 4))] + [_cost(c, x, lv) for c, x in costs] + ([tuple(extra)] if lv == 3 else [])


COST_SCALE = tuning.get("EXCH_COST_SCALE", [1, 1.25, 1.5, 2])  # a path's costs by place: unranked, 3rd, 2nd, 1st
APPROVAL_COST = [1, 1, 1, 2]  # approval in whole points: -1, -1, -1, -2 for a -1 cost


def _cost(m, x, lv):
    if m.endswith("approval_add"):
        return (m, x * APPROVAL_COST[lv])
    pts = int(abs(x) * COST_SCALE[lv] * 100 + 0.5)  # whole percent, halves up
    return (m, (pts if x > 0 else -pts) / 100)


def _mod_words(fx, sep=", "):
    """Vanilla's modifier names with our values: green when good for the state, red when bad."""
    out = []
    for m, x in fx:
        good = x < 0 if m == "country_loan_interest_rate_mult" or m.endswith("mortality_mult") else x > 0
        val = f"{x:+g}" if m.endswith(("legitimacy_base_add", "max_companies_add", "approval_add")) else f"{x:+.1%}".replace(".0%", "%")
        out.append(f"#{'P' if good else 'N'} {val}#! ${m}$")
    return sep.join(out)


def _pursue_lv(k):
    """Pursue tooltip: what the pursuit gives at each place, ours in bold and the rest grey (vanilla's current-line style)."""
    now = lambda lv: (f"Not({P}.Var('spec_lead_{k}').IsSet)" if lv == 0
                      else f"EqualTo_CFixedPoint({v(f'spec_lead_{k}')}, {fx(4 - lv)})")
    return (chr(92) + "n").join(
        f"[SelectLocalization({now(lv)}, 'SPEC_PURSUE_LV_{k}_{lv}_ON', 'SPEC_PURSUE_LV_{k}_{lv}')]" for lv in (3, 2, 1, 0))


def _pursue_lv_keys(k):
    """The place lines _pursue_lv picks between."""
    return "".join(f' SPEC_PURSUE_LV_{k}_{lv}_ON: "#b {PLACE_SHORT[lv]}: {_mod_words(_pursue_fx(k, lv))}#!"\n'
                   f' SPEC_PURSUE_LV_{k}_{lv}: "#grey {PLACE_SHORT[lv]}:#! {_mod_words(_pursue_fx(k, lv))}"\n' for lv in range(4))


def _trust_words(i):
    return f"\\n$TOOLTIP_DELIMITER$\\n{_mod_words(TRUST_FX[i], chr(92) + 'n')}" if TRUST_FX[i] else ""


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
    for i, f in enumerate(TRUST_FX):
        if not f:
            continue
        lim = ([f"var:spec_centre_trust >= {CALM * i / 4:g}"] if i else []) + ([f"var:spec_centre_trust < {CALM * (i + 1) / 4:g}"] if i < 3 else [])
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
    return "".join(f"spec_pursue_to_{k} = {{\n{init}\tchange_variable = {{ name = spec_pursue_n add = 1 }}\n"
                   f"\tset_variable = {{ name = spec_pu_{k} value = var:spec_pursue_n }}\n\tset_variable = spec_has_{k}\n"
                   f"\tset_variable = {{ name = spec_pu_lock_{k} value = {PURSUE_LOCK * 12} }}\n}}\n\n"  # months, counted down in _pursue_month
                   f"spec_pursue_stop_{k} = {{\n{left(k)}"
                   f"\tremove_variable = spec_pu_{k}\n\tremove_variable = spec_has_{k}\n\tif = {{\n\t\tlimit = {{ has_variable = spec_pu_lock_{k} }}\n"
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
    PURSUE_MONTHS and fades as slowly once stopped; what it gives follows its strength and our place in its field."""
    if not NAMES_ON:
        return ""
    step = round(1 / PURSUE_MONTHS + 0.0005, 3)
    u = t + "\t"
    each = "".join(f"{u}if = {{\n{u}\tlimit = {{ has_variable = spec_pu_{k} }}\n"
                   f"{u}\tchange_variable = {{ name = spec_pw_{k} add = {step:g} }}\n{u}}}\n"
                   f"{u}else = {{\n{u}\tchange_variable = {{ name = spec_pw_{k} add = -{step:g} }}\n{u}}}\n"
                   f"{u}clamp_variable = {{ name = spec_pw_{k} min = 0 max = 1 }}\n"
                   # the months a speciality must still be kept, as the Credit Policy's cooldown counts down
                   f"{u}if = {{\n{u}\tlimit = {{ has_variable = spec_pu_lock_{k} }}\n"
                   f"{u}\tchange_variable = {{ name = spec_pu_lock_{k} add = -1 }}\n"
                   f"{u}\tif = {{\n{u}\t\tlimit = {{ var:spec_pu_lock_{k} <= 0 }}\n{u}\t\tremove_variable = spec_pu_lock_{k}\n{u}\t}}\n{u}}}\n"
                   for k, *_ in NAMES)
    total = " ".join(f"add = var:spec_pw_{k}" for k, *_ in NAMES)
    drop = _pursue_drop(u)
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


def _pursue_ai(t):
    """Once a year an AI Exchange fills its free specialities, one a pass, each time the path it is closest to leading
    (its tally's share of the leader's, spec_sh_<key>; none counts 0; a tie goes to the first listed).
    ponytail: it never drops one."""
    u, w = t + "\t\t", t + "\t\t\t"
    sh = lambda k: f"local_var:spec_ai_sh_{k}"
    best = "".join(f"{u}set_local_variable = {{ name = spec_ai_sh_{k} value = -1 }}\n"
                   f"{u}if = {{\n{w}limit = {{ spec_can_pursue_{k} = yes }}\n"
                   f"{w}set_local_variable = {{ name = spec_ai_sh_{k} value = 0 }}\n"
                   f"{w}if = {{\n{w}\tlimit = {{ has_variable = spec_sh_{k} }}\n"
                   f"{w}\tset_local_variable = {{ name = spec_ai_sh_{k} value = var:spec_sh_{k} }}\n{w}}}\n"
                   f"{w}if = {{\n{w}\tlimit = {{ {sh(k)} > local_var:spec_ai_best }}\n"
                   f"{w}\tset_local_variable = {{ name = spec_ai_best value = {sh(k)} }}\n{w}}}\n{u}}}\n" for k, *_ in NAMES)
    take = "".join(f"{u}{'if' if i == 0 else 'else_if'} = {{\n{w}limit = {{ {sh(k)} >= 0 {sh(k)} = local_var:spec_ai_best }}\n"
                   f"{w}spec_pursue_to_{k} = yes\n{u}}}\n" for i, (k, *_) in enumerate(NAMES))
    room = "OR = { NOT = { has_variable = spec_pursue_n } spec_pursue_slots > var:spec_pursue_n }"
    passes = "".join(f"{t}\tif = {{\n{u}limit = {{ {room} }}\n{u}set_local_variable = {{ name = spec_ai_best value = -1 }}\n"
                     f"{best}{take}{t}\t}}\n" for _ in range(4))  # at most 4 specialities
    return f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tis_player = no\n{t}\t\thas_variable = spec_exch_stand\n{t}\t}}\n{passes}{t}}}\n"


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
                            pic(ICON(k), 8, 44) + name(f"SPEC_NAME_H_{k}", 50, 34) + badge(i) + foot(k)) for k, *_ in NAMES)
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
			alwaystransparent = yes  # the place's tooltip, not the country's
		}}
	}}
}}
"""

    def row(k, ch):
        has = f"{P}.Var('spec_has_{k}').IsSet"
        pu = f"{P}.Var('spec_pu_{k}').IsSet"
        open_ = f"EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(ch)})" if ch else ""
        shut = (f"""icon = {{
	visible = "[Not({open_})]"
	size = {{ 100% 100% }}
	texture = "{FLAT}"
	color = {{ 0 0 0 0.35 }}
	alwaystransparent = yes
}}
""" if ch else "")
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
        div = lambda x: f"""progressbar = {{
	visible = "[{gt(x, 0.02)}]"
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
	value = "[{at(sh)}]"
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
        dim = f"""icon = {{
	visible = "[And({picking}, {f'And(Not({ok}), {open_})' if ch else f'Not({ok})'})]"
	size = {{ 100% 100% }}
	texture = "{FLAT}"
	color = {{ 0 0 0 0.35 }}
	alwaystransparent = yes
}}
"""
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
	textbox = {{
		position = {{ {NX + 3} {BAR_Y + BAR_H + 3} }}
		size = {{ {NW - 6} 18 }}
		align = left|nobaseline
		elide = right
		using = fontsize_small
		text = "SPEC_NAME_TALLY_{k}"
		tooltip = "SPEC_NAME_BAR_TT_{k}"
	}}
{ind(flag(k, 1) + flag(k, 2) + flag(k, 3), 1)}	textbox = {{
		position = {{ {GX} 0 }}
		size = {{ {GW} {rh} }}
		multiline = yes
		align = left|nobaseline
		using = fontsize_small
		text = "SPEC_NAME_STATUS_{k}"
	}}
{ind(shut + dim + pick, 1)}}}
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
            "press": ("Our rival Press Campaigns", 1), "raid": ("Our rival Bear Raids", 1),
            "lure": ("Our rival Lure Investors", 1), "shore": ("Our Shore Up lasts", 1),
            "crash": ("Confidence lost in busts", -1), "panic": ("[concept_spec_financial_panic] length", -1),
            "rescue": ("Rescue cost", -1), "tie_inv": ("Investment ties to other markets", 0),
            "tie_trade": ("Trade ties to other markets", 0), "blue": ("[concept_spec_blue_chip] climb", 1),
            "burst": ("Bubble Bursts", -1), "bad": ("[concept_spec_bad_debts] a panic leaves", -1),
            "ceiling": ("Credit ceiling", 1)}
NAMES_ABOUT = ("You grant your Exchange one charter: #v Commodity Exchange#!, #v Money Market#! or #v Share Market#!. "
               f"It holds #v 1#! to #v 4#! specialities from the #v {len(NAMES)}#! Paths to Renown, more as its "
               f"Standing rises, and keeps each for at least #v {PURSUE_LOCK}#! years.")
FX_COLUMN = {h: (FX_SHORT[h], g) for h, (_, g) in FX_WORDS.items()}


def _fx_words(k, sep, words=FX_WORDS):
    def one(hook, x):
        what, good = words[hook]
        col = "v" if not good else "P" if (x > 1) == (good > 0) else "N"
        return f"{what}: #{col} {x - 1:+.0%}#!"
    return sep.join(one(h, x) for h, x in NAME_FX[k].items())


def _names_loc(ui, known):
    """The charter cards' and the names' words; replaces the earned cards' (same keys)."""
    tc = "[GetBuildingType('building_trade_center').GetName]"
    by = {"price": ("the value of the goods our market deals in", "D"), "harbour": ("the trust our Exchange holds", "0"),
          "companies": ("[concept_spec_company_strength]: the [concept_prosperity] of our companies, and "
                        f"#v {companies.BLUE_BONUS:g}#! for each [concept_spec_blue_chip]. "
                        f"@spec_blue_chip! [Concept('concept_spec_blue_chip','$concept_spec_blue_chips$')] held: "
                        f"#v [{P}.ScriptValue('spec_log_kbc')|0]#!", "1"), "floor": (f"{tc} levels", "0"),
          "sound": ("quiet months of sound lending", "0"),
          "pockets": ("money entering the [concept_investment_pool] each month", "D"),
          "door": ("treaties with other countries", "0"),
          "futures": ("the states our market reaches", "0"),
          "lender": ("countries granting us [concept_foreign_investment] rights", "0"),
          "railway": ("[GetBuildingType('building_railway').GetName] and [GetBuildingType('building_port').GetName] levels", "0")}
    about = {"price": "The world looks to our floor for the price of goods.",
             "harbour": "Frightened money from abroad comes to our banks.",
             "companies": "The greatest companies raise their money here.",
             "floor": "More trade passes through our market than through any other.",
             "sound": "Our banks lend with care.",
             "pockets": "No market has more money seeking a use.",
             "door": "Our market deals freely with the world.",
             "futures": "Harvests yet unsown are bought and sold on our floor.",
             "lender": "Foreign governments come to us for their money.",
             "railway": "Every new line is floated on our market, and every fortune with it."}
    drop = (" SPEC_EXCH_CARD_N_", " SPEC_EXCH_CARD_TT_", " SPEC_H_KNOWN_TT", " SPEC_EXCH_CARD_NOTE", " SPEC_EXCH_CARD_HELD")
    out = "".join(line for line in ui.splitlines(True) if not line.startswith(drop))
    short = [f"Investor Reaction: #v {KNOWN_HYPE - 1:+.0%}#!", f"Trust losses: #P {KNOWN_LOSS - 1:+.0%}#!",
             f"Credit lent: up to #P {KNOWN_CREDIT - 1:+.0%}#!"]
    only = {}
    for _, title, ch in NAMES:
        if ch:
            only[ch] = f"{only[ch]}#! or #v {title}" if ch in only else title
    held = lambda n: f"EqualTo_CFixedPoint({v('spec_exch_known')}, {fx(n)})"
    for n in (1, 2, 3):
        key = f"charter_{n}"
        out += (f' SPEC_EXCH_CARD_N_{n}: "{short[n - 1]}"\n'
                f' SPEC_EXCH_CARD_TT_{n}: "#header {known[n]}#!\\n{short[n - 1]}\\nOpens #v {only[n]}#! as a speciality'
                f"[AddLocalizationIf(Not(GetScriptedGui('spec_sgui_{key}').IsValid(GuiScope.SetRoot({P}).End)), "
                f"'SPEC_CHARTER_WHY_{n}')]\"\n"
                f' SPEC_CHARTER_WHY_{n}: "\\n\\n{sg(key, "BuildTooltip")}"\n'
                f" SPEC_CHARTER_BTN_{n}: \"[SelectLocalization({held(n)}, 'SPEC_CHARTER_HELD', 'SPEC_CHARTER_GRANT')]\"\n"
                f' SPEC_NAME_NEED_{n}: "{known[n]} only"\n'
                f' SPEC_NAME_NEEDS_{n}: "\\n\\n#N Needs the {known[n]} charter#!"\n')
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
        pct = f"Multiply_CFixedPoint({pw}, {fx(round(PURSUE_BOOST - 1, 4))})"
        third = f"GetGlobalVariable('spec_w_{k}3')"
        third_v = f"{third}.GetCountry.MakeScope.ScriptValue('spec_name_{k}')"
        ld, ch_ = f"GetGlobalVariable('spec_ld_{k}')", f"GetGlobalVariable('spec_ch_{k}')"
        ldv = f"GetGlobalVariable('spec_ldv_{k}').GetValue"
        sh = v(f"spec_sh_{k}")
        shl = f"{P}.Var('spec_shl_{k}').GetValueWithDefault({sh})"
        ours_v = f"{P}.ScriptValue('spec_name_{k}')"
        tval = lambda p: ldv if p == 1 else f"GetGlobalVariable('spec_t{p}_{k}').GetValue"
        need = lambda p: f"Subtract_CFixedPoint({tval(p)}, {ours_v})"
        stat = f"[SelectLocalization({has}, 'SPEC_NAME_FX_{k}', 'SPEC_NAME_FXDIM_{k}')]"  # the build-up is in the row's tooltip
        flight = f"\\n#grey [concept_spec_capital_flight] received {FLIGHT_IF}#!" if "flight" in NAME_FX[k] else ""
        out += (f' SPEC_NAME_H_{k}: "#b {title}#!"\n'
                f' SPEC_NAME_FX_{k}: "{_fx_words(k, chr(92) + "n", FX_COLUMN)}"\n'
                f' SPEC_NAME_FXDIM_{k}: "$SPEC_NAME_FX_{k}$"\n'  # coloured as held: good green, bad red, neutral white
                # the effects always show, chartered or not (the user wants to see what a locked path gives);
                # the charter it needs is in the icon's tooltip
                + f' SPEC_NAME_STATUS_{k}: "{stat}"\n'
                + f' SPEC_NAME_PW_TT_{k}: "\\n$TOOLTIP_DELIMITER$\\nTally bonus: #v +[{pct}|%0]#! of #v {PURSUE_BOOST - 1:+.0%}#!'
                f"[SelectLocalization({pu}, 'SPEC_NAME_PW_UP', 'SPEC_NAME_PW_DOWN')]\"\n"
                f" SPEC_NAME_QTY_{k}: \"#b {cur}[{P}.ScriptValue('spec_name_{k}')|{f}]#!\"\n"
                f' SPEC_NAME_TALLY_{k}: "$SPEC_NAME_QTY_{k}$ #grey {unit[k]}#!"\n'
                f' SPEC_NAME_BAR_TT_{k}: "#header {title}#!\\nRanked by {by[k][0]}\\n$TOOLTIP_DELIMITER$\\n'
                f"[SelectLocalization({ld}.GetCountry.IsValid, 'SPEC_NAME_PLACES_{k}', 'SPEC_NAME_NOLEAD')]"
                + f"[AddLocalizationIf({ch_}.GetCountry.IsValid, 'SPEC_NAME_CH_{k}')]"
                + f"[SelectLocalization({gt(f'Subtract_CFixedPoint({sh}, {shl})', 0.001)}, 'SPEC_NAME_UP', "
                f"SelectLocalization({gt(f'Subtract_CFixedPoint({shl}, {sh})', 0.001)}, 'SPEC_NAME_DOWN', 'SPEC_NAME_FLAT'))]"
                f'"\n'
                # the flags' three, each with its tally now: "1st France: 212"
                f" SPEC_NAME_PLACES_{k}: \"" + "".join(
                    f"[AddLocalizationIf(GetGlobalVariable('spec_w_{k}{p}').GetCountry.IsValid, 'SPEC_NAME_P{p}_{k}')]" for p in (1, 2, 3))
                + f"\\n#b Ours: {cur}[{ours_v}|{f}]#! #grey {unit[k]}#!\"\n"
                + "".join(f" SPEC_NAME_FLAG_TT_{k}{p}: \"#header {('1st', '2nd', '3rd')[p - 1]} on {title}#!\\n"
                          f"[SelectLocalization(GetGlobalVariable('spec_w_{k}{p}').GetCountry.IsValid, 'SPEC_NAME_FW_{k}{p}', 'SPEC_NAME_NOONE')]"
                          f"\\n$TOOLTIP_DELIMITER$\\nAs our speciality, this place gives:\\n{_mod_words(_pursue_fx(k, 4 - p), chr(92) + 'n')}\"\n"
                          f" SPEC_NAME_FW_{k}{p}: \"#v [GetGlobalVariable('spec_w_{k}{p}').GetCountry.GetNameNoFormatting]#!: "
                          f"#v {cur}[GetGlobalVariable('spec_w_{k}{p}').GetCountry.MakeScope.ScriptValue('spec_name_{k}')|{f}]#! #grey {unit[k]}#!\"\n"
                          for p in (1, 2, 3))
                + f' SPEC_NAME_CH_{k}: "\\n#v [{ch_}.GetCountry.GetNameNoFormatting]#! takes the lead after #v {LEAD_HOLD}#! months ahead '
                f'(#v [GetGlobalVariable(\'spec_chm_{k}\').GetValue|0]#! so far)"\n'
                + f" SPEC_NAME_P1_{k}: \"1st [GetGlobalVariable('spec_w_{k}1').GetCountry.GetNameNoFormatting]: #v {cur}[GetGlobalVariable('spec_w_{k}1').GetCountry.MakeScope.ScriptValue('spec_name_{k}')|{f}]#! #grey {unit[k]}#!\"\n"
                + f" SPEC_NAME_P2_{k}: \"\\n2nd [GetGlobalVariable('spec_w_{k}2').GetCountry.GetNameNoFormatting]: #v {cur}[GetGlobalVariable('spec_w_{k}2').GetCountry.MakeScope.ScriptValue('spec_name_{k}')|{f}]#! #grey {unit[k]}#!\"\n"
                + f" SPEC_NAME_P3_{k}: \"\\n3rd [GetGlobalVariable('spec_w_{k}3').GetCountry.GetNameNoFormatting]: #v {cur}[GetGlobalVariable('spec_w_{k}3').GetCountry.MakeScope.ScriptValue('spec_name_{k}')|{f}]#! #grey {unit[k]}#!\"\n"
                + f' SPEC_NAME_THIRD_{k}: "\\nThird place: #v {cur}[{third_v}|{f}]#! #grey {unit[k]}#!"\n'
                f' SPEC_NAME_ICON_TT_{k}: "$SPEC_NAME_TT_{k}$"\n'
                f' SPEC_PURSUE_STOP_TT_{k}: "#header Drop {title}#!\\nFrees its slot at once; its effects fade over #v {PURSUE_MONTHS}#! months.'
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
                f' SPEC_NAME_TT_{k}: "#header {title}#!\\n#italic {about[k]}#!\\n$TOOLTIP_DELIMITER$\\n'
                f'#b As a speciality#!\\n{_fx_words(k, chr(92) + "n")}{flight}\\n\\n'
                f'#b By our place each year#!\\n$SPEC_PURSUE_LV_{k}$'
                + (f"[AddLocalizationIf(Not({held(ch)}), 'SPEC_NAME_NEEDS_{ch}')]" if ch else "")
                + f"[AddLocalizationIf({live}, 'SPEC_NAME_PW_TT_{k}')]" + '"\n')
    for ch in (1, 2, 3):
        out += f' spec_pursue_charter_tt_{ch}: "Our [concept_spec_exchange] is chartered as a #v {known[ch]}#!"\n'
    rule = (f"Specialities: #v 1#! at Provincial, up to #v 4#! as a World Centre\\n"
            f"Each is kept at least #v {PURSUE_LOCK}#! years once chosen\\n"
            f"Builds up over #v {PURSUE_MONTHS}#! months, and fades as slowly once dropped\\n"
            f"At full strength: our tally #P {PURSUE_BOOST - 1:+.0%}#! on its path, #N {PURSUE_COST - 1:+.0%}#! on every other path\\n"
            "If the Standing falls, the last chosen are dropped first")
    slots = f"{P}.ScriptValue('spec_pursue_slots')"
    out += (f' SPEC_PURSUE_RULE: "{rule}"\n SPEC_PURSUE_STOP: "Drop"\n'
            ' SPEC_NAME_PW_UP: ", #P building#!"\n SPEC_NAME_PW_DOWN: ", #N fading#!"\n'
            ' SPEC_NAME_UP: "\\n#P Gaining on the leader this month#!"\n'
            ' SPEC_NAME_DOWN: "\\n#N Falling behind the leader this month#!"\n SPEC_NAME_FLAT: ""\n'
            f' SPEC_NAME_BAR_RULE: "Our tally against the leader\'s, updated each month. The marks show where 3rd, 2nd and 1st '
            f'place stand. The bar is gold while we gain on the leader and red while we fall behind. A market takes the lead once '
            f'it has stayed ahead for #v {LEAD_HOLD}#! months in a row."\n'
            ' SPEC_NAME_NOLEAD: "No Exchange leads on this path yet"\n'
            ' SPEC_NAME_NOONE: "#grey No Exchange holds this place yet#!"\n'
            f' SPEC_H_NAMES_RIGHT: "#v [{v("spec_pursue_n")}|0]#! of #v [{slots}|0]#!"\n'
            ' SPEC_H_CONTEST: "Paths to Renown"\n'
            ' SPEC_H_CONTEST_TT: "#header Paths to Renown#!\\n$SPEC_CONTEST_NOTE$\\n\\n$SPEC_NAME_RULE$\\n\\n$SPEC_NAME_BAR_RULE$\\n$TOOLTIP_DELIMITER$\\n$SPEC_PURSUE_RULE$"\n'
            ' SPEC_CONTEST_PLACE_1: "#grey 1st#!"\n SPEC_CONTEST_PLACE_2: "#grey 2nd#!"\n SPEC_CONTEST_PLACE_3: "#grey 3rd#!"\n'
            ' SPEC_CONTEST_NOTE: "The flags show last year\'s three leaders on each path, and each bar our tally against '
            'the leader\'s. Choosing a path as a speciality helps us climb on it, at some cost to the rest."\n'
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
            ' spec_pursue_room_tt: "We have a free speciality"\n'
            f' spec_pursue_locked_tt: "Kept at least #v {PURSUE_LOCK}#! years"\n'
            ' SPEC_SLOT_PICK: "Choose"\n SPEC_SLOT_PICK_CANCEL: "Cancel"\n'
            ' SPEC_ROW_CLICK: "#instruction Click to choose#!"\n SPEC_ROW_CANNOT: "#N Cannot be chosen#!"\n'
            ' SPEC_SLOT_PICK_TT: "#header Choose a Speciality#!\\n#instruction Click one of the lit Paths to Renown in the list below#!"\n'
            ' SPEC_SLOT_PICK_CANCEL_TT: "#header Cancel#!\\n#instruction Click to stop choosing a path for this slot#!"\n'
            ' SPEC_SLOT_LATER_TT: "#header Open Speciality#!\\nFilled after the slots before it.\\n\\n$SPEC_PURSUE_RULE$"\n'
            ' spec_pursue_first_tt: "Already first"\n spec_pursue_last_tt: "Already last"\n'
            ' SPEC_PURSUE_ORDER: "If our [concept_spec_exchange]\'s Standing falls, specialities are lost from the last slot first. '
            'Moving one earlier keeps it longer."\n'
            ' SPEC_PURSUE_SLOT_TT: "#header Order Chosen#!\\nIf our [concept_spec_exchange]\'s Standing falls, the last chosen specialities are dropped first."\n'
            + "".join(f' spec_pursue_{k}_{lv}: "{title}"\n spec_pursue_{k}_{lv}_desc: "The [concept_country]\'s [concept_spec_exchange] '
                      f'has made this its speciality, and stands {PLACE_WORDS[lv].lower()} on its path."\n' for k, title, _ in NAMES for lv in range(4))
            # the Standing-down toast (notify.py) names the specialities the fall cost (_pursue_fall)
            + ' SPEC_EXCH_DOWN_LOST: "' + "".join(f"[AddLocalizationIf(GetPlayer.MakeScope.Var('spec_pu_lost_{k}').IsSet, "
                                                  f"'SPEC_EXCH_LOST_{k}')]" for k, *_ in NAMES) + '"\n'
            + "".join(f' SPEC_EXCH_LOST_{k}: "\\n#v {title}#! is no longer one of its specialities."\n' for k, title, _ in NAMES))
    return out + (
        ' SPEC_NAME_RULE: "Once a year the world\'s Exchanges of National Standing or higher are compared on each Path to Renown. '
        'Our place on a path chosen as a speciality sets what it gives."\n'
        ' SPEC_CHARTER_HELD: "Chartered"\n SPEC_CHARTER_GRANT: "Grant Charter"\n'
        f' SPEC_CHARTER_RULE: "The first charter is free\\nA new one later: #N -{CHARTER_COST:.0%}#! '
        "of the [concept_spec_exchange]'s trust, and any speciality only the old charter allowed\\nEach charter stands for "
        f'#v {CHARTER_LOCK}#! years"\n'
        ' spec_charter_current_tt: "Our [concept_spec_exchange] does not already hold this charter"\n'
        f' spec_charter_locked_tt: "No charter has been granted in the last #v {CHARTER_LOCK}#! years"\n'
        ' SPEC_H_CHARTER: "Exchange Charter"\n'
        ' SPEC_H_CHARTER_TT: "#header Exchange Charter#!\\n$SPEC_EXCH_CARD_NOTE$\\n\\n$SPEC_CHARTER_RULE$"\n'
        ' SPEC_EXCH_CARD_NOTE: "The state grants its [concept_spec_exchange] one charter\\nEach brings its own advantage and opens '
        'Paths to Renown no other charter can choose"\n'
        ' SPEC_H_KNOWN_TT: "#header Specialities#!\\nThe Paths to Renown the state has chosen for our [concept_spec_exchange].\\n\\n$SPEC_PURSUE_RULE$"\n')


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


def _pledge_month(t):
    """The pledge each month: a default breaks it; notice runs out; the AI makes it or gives notice."""
    if not PLEDGE_ON:
        return ""
    return f"""{t}if = {{
{t}	limit = {{
{t}		has_variable = spec_pledge
{t}		in_default = yes
{t}	}}
{t}	set_variable = {{ name = spec_centre_trust value = 0 }}
{t}	spec_cool_conf = {{ AMOUNT = {PLEDGE_BREAK["conf"]} }}
{t}	add_modifier = {{ name = spec_pledge_broken months = 60 }}
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
    # Strict, Cautious or Sound +1, Lax nothing, Reckless -1; no gain while Bad Debts drain it (_crunch)
    calm = "NOT = { has_variable = spec_crunch } " if CRUNCH else ""
    month = (f"{t}\tif = {{\n{u}limit = {{ has_variable = spec_lax var:spec_lax >= {cycle.LAX_CUTS[3]:g} }}\n{_lose(1, u)}{t}\t}}\n"
             f"{t}\telse_if = {{\n{u}limit = {{ {calm}OR = {{ NOT = {{ has_variable = spec_lax }} var:spec_lax < {cycle.LAX_CUTS[2]:g} }} }}\n"
             f"{_gain(1, u)}{SOUND(u)}{t}\t}}\n"
             if cycle.ON else f"{t}\tif = {{\n{u}limit = {{ {calm}always = yes }}\n{_gain(1, u)}{SOUND(u)}{t}\t}}\n")
    # a new Exchange starts Respected (half of CALM), or from its quiet months if more
    return (f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_centre_trust }} }}\n"
            f"{t}\tset_variable = {{ name = spec_centre_trust value = {{ value = var:spec_centre_calm min = {CALM / 2:g} max = {CALM} }} }}\n{t}}}\n"
            f"{t}if = {{\n{t}\tlimit = {{ NOT = {{ has_variable = spec_panic }} }}\n{month}{t}}}\n"
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
    return (f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_crunch }}\n{_lose(LINK_CRUNCH, t + chr(9))}"
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
            + (["spec_exch_best"] if not EARN else [])  # current builds never set the legacy standing-choice variable
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
{_regions() if ON else ''}{_standing()}{_names()}{__import__("rivals").pass_() if RIVAL_ON else ""}{COUNTS}{shown}	# ponytail: a market hovering between the last place and the next gets a toast each time it crosses; hold a place
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
	country_loan_interest_rate_mult = {-STEP:g}
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
HEADS = ([(0, 40, "", "center", False), (40, 176, "SPEC_CENTRE_COL_NAME", "left", False),  # the place numbers' own head
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
    """A tiered row's Standing colour: a faint wash fading right."""
    if t is None:
        return ""
    return f"""		background = {{
			using = fade_right_colored
			color = {{ {TIER_COL[t]} 1 }}
			alpha = 0.18
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
	widget = {{
		size = {{ {W} {ROW_H} }}
		{f'datacontext = "[{SLOT(n)}.GetCountry]"' if n else ""}
		{f'visible = "[{STAND_IS(t)}]"' if t is not None else ""}
		tooltip = "SPEC_CENTRE_TT_{n if placed else 'OWN'}"
		background = {{
			visible = "[Country.IsLocalPlayer]"
			using = paper_bg
		}}
{tint(t)}		divider_clean = {{
			parentanchor = bottom
			position = {{ 0 2 }}
		}}
{ind(text(0, 40, f"SPEC_CENTRE_N_{n or 'NONE'}", "center"), 2)}		tiny_flag = {{
			position = {{ 44 0 }}
			parentanchor = vcenter
		}}
		button = {{
			position = {{ 78 0 }}
			size = {{ 134 30 }}
			parentanchor = vcenter
			using = clean_button
			onclick = "[InformationPanelBar.OpenCountryPanel(Country.Self)]"
			tooltipwidget = {{
				FancyTooltip_Country = {{}}
			}}
			textbox = {{
				size = {{ 100% 100% }}
				margin_left = 12
				align = nobaseline
				parentanchor = vcenter
				elide = right
				alwaystransparent = yes
				text = "[Country.GetNameNoFormatting]"
			}}
		}}
{ind(text(226, 60, "SPEC_CENTRE_SCORE", "right") + text(476, 54, f"SPEC_CENTRE_{THIRD}", "right"), 2)}{rival_button() if RIVAL_ON else ""}{name_icons()}	}}
}}
"""


# each Standing's colour in the World tab, after its badge: gold, silver, bronze, stone
TIER_COL = {3: "0.86 0.69 0.32", 2: "0.72 0.77 0.84", 1: "0.76 0.47 0.26", 0: "0.5 0.5 0.5"}


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
{"".join(row(n, t) for n in range(1, {3: 2, 0: 1}.get(t, SHOWN + 1))) + row(None, t)}textbox = {{
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
	default_progressbar_horizontal = {{
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


def score_levels():
    """The score as the Standings' levels, under the four cards, each segment how far through that Standing:
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
    return f"""widget = {{
	size = {{ {W} 32 }}
	parentanchor = hcenter
	textbox = {{
		position = {{ 0 4 }}
		size = {{ {W} 26 }}
		align = center|nobaseline
		tooltip = "SPEC_EXCH_CALC_TT"
		text = "SPEC_EXCH_SCORE_LINE"
	}}
}}
{levels_bar(segs, BAR_W)}"""


def trust_levels():
    """Trust as vanilla shows legitimacy (politics_panel_overview.gui:543): its level and value, then the levels bar."""
    share = f"Divide_CFixedPoint({v('spec_centre_trust')}, {fx(CALM)})"
    segs = [(f"Multiply_CFixedPoint(Subtract_CFixedPoint({share}, {fx(i / 4)}), {fx(4)})",
             f"And(Not(LessThan_CFixedPoint({share}, {fx(i / 4)})), LessThan_CFixedPoint({share}, {fx((i + 1) / 4 if i < 3 else 2)}))",
             f"SPEC_EXCH_TRUST_LV_TT_{i}") for i in range(4)]
    return f"""widget = {{
	size = {{ {W} 32 }}
	parentanchor = hcenter
	textbox = {{
		position = {{ 0 4 }}
		size = {{ {W} 26 }}
		align = center|nobaseline
		tooltip = "SPEC_EXCH_G_TRUST_TT"
		text = "SPEC_EXCH_TRUST_HEAD"
	}}
}}
{levels_bar(segs, BAR_W, "SPEC_EXCH_G_TRUST_TT")}"""


def _parts_loc():
    """The score's calculator in vanilla's breakdown form (as market_tab.why_lines): the base value from the capital the
    Exchange draws on, then each multiplier "from" its cause, those at x1 left out, the parts with more to them in
    nested tooltips; then where that places us, against the world's top three and our region's leader."""
    p = lambda name, f="0": f"[{v(name)}|{f}]"
    nest = lambda key, text: f"#tooltippable #tooltip:[Country.GetTooltipTag],{key} {text}#!#!"
    money = lambda name: f"@money![Multiply_CFixedPoint({v(name)}, {fx(CAP_PER)})|D]"
    x = lambda name: f"#§ x{p(name, '2')}#!"  # §: the colour, P above x1 and N below (SPEC_XS_ROW_<k> and _N)
    mults = {"WEALTH": ("spec_xs_wealth_v", f"{nest('SPEC_XS_WEALTH_TT', x('spec_xs_wealth_v'))} from Wealth per Head"),
             "FD": ("spec_xs_fdm_v", f"{x('spec_xs_fdm_v')} from [GetBuildingType('building_financial_district').GetName] "
                                     f"(#v {p('spec_xs_fd_v')}#! levels)"),
             "CO": ("spec_xs_com_v", f"{x('spec_xs_com_v')} from Companies (#v {p('spec_xs_co_v')}#! headquartered here)"),
             "TECH": ("spec_xs_tech_v", f"{nest('SPEC_XS_TECH_TT', x('spec_xs_tech_v'))} from Finance Technologies "
                                        f"(#v {p('spec_xs_ntech_v')}#! of #v {len(TECHS)}#!)"),
             "RANK": ("spec_xs_rank_v", f"{x('spec_xs_rank_v')} from [concept_rank]"),
             "ECON": ("spec_xs_econ_v", f"{nest('SPEC_XS_ECON_TT', x('spec_xs_econ_v'))} from Economic System"),
             "TRUST": ("spec_xs_trust_v", f"{x('spec_xs_trust_v')} from Trust")}
    issue = (f"[AddLocalizationIf({P}.Var('spec_issue').IsSet, 'SPEC_XS_ROW_ISSUE')]" if levers.ISSUE_ON else "")
    regs = "".join(f"[AddLocalizationIf(EqualTo_CFixedPoint({v('spec_xs_reg')}, {fx(i)}), 'SPEC_XS_REGLINE_{i}')]"
                   for i in range(1, len(REGIONS) + 1))
    calc = (f"#header [Concept('concept_spec_financial_centre','$concept_spec_exchange$')] score: #v {p('spec_centre_score')}#!#!\\n$TOOLTIP_DELIMITER$\\n"
            f"{nest('SPEC_XS_CAP_TT', '#v ' + p('spec_xs_size_v') + '#!')} from Capital "
            f"(#v {money('spec_xs_own_v')}#! our own, #v {money('spec_xs_reach_v')}#! from our ties)"
            + "".join(f"[AddLocalizationIf(GreaterThan_CFixedPoint({v(n)}, {fx(1)}), 'SPEC_XS_ROW_{k}')]"
                      f"[AddLocalizationIf(LessThan_CFixedPoint({v(n)}, {fx(1)}), 'SPEC_XS_ROW_{k}_N')]" for k, (n, _) in mults.items())
            + issue + f"\\n$TOOLTIP_DELIMITER$\\nTotal #v {p('spec_xs_raw')}#!, scored against the world's top three, whose average is #v 100#!{regs}")
    techs = "".join(f"\\n${t}$: #P +{b:.0%}#!" for t, b in TECHS.items())
    econ = "".join(f"\\n$law_{k}$: #{'v' if m == 1 else 'P' if m > 1 else 'N'} x{m:g}#!" for k, m in ECON.items())
    tech = lambda k: f"[GetTechnology('{k}').GetName]"
    reach = (f"a quarter of the capital of each smaller [concept_country] in our [concept_market], our [Concept('concept_subject','$concept_subjects$')], "
             f"our [concept_power_bloc], or granting us [concept_foreign_investment] rights; at most as much as our own")
    return (f' SPEC_EXCH_CALC_TT: "{calc}"\n'
            + "".join(f' SPEC_XS_ROW_{k}: "\\n{line.replace("§", "P")}"\n SPEC_XS_ROW_{k}_N: "\\n{line.replace("§", "N")}"\n'
                      for k, (_, line) in mults.items())
            + f' SPEC_XS_ROW_ISSUE: "\\n#P x{levers.ISSUE_SCORE:g}#! from a Great Issue"\n'
            + "".join(f' SPEC_XS_REGLINE_{i}: "\\nAgainst the leader in {name}, '
                      f"[GetGlobalVariable('spec_xs_rlead_{i}').GetCountry.GetName]: #v {p('spec_xs_regshare')}%#!\"\n"
                      for i, (_, name) in enumerate(REGIONS, 1))
            + f' SPEC_XS_CAP_TT: "#header Capital#!\\n$TOOLTIP_DELIMITER$\\nThe score grows with the {'fourth' if SIZE_ROOT == 4 else 'square'} root of the capital our '
            f"[concept_spec_exchange] draws on: "
            f"{'sixteen' if SIZE_ROOT == 4 else 'four'} times the capital doubles it\\n\\nOur own: #v {money('spec_xs_own_v')}#!, six months of [concept_investment_pool] income, yearly "
            f"average\\nFrom our ties: #v {money('spec_xs_reach_v')}#!, {reach}\"\n"
            f' SPEC_XS_WEALTH_TT: "#header Wealth per Head#!\\n$TOOLTIP_DELIMITER$\\n[concept_investment_pool] income per '
            f"person: #v {p('spec_xs_ratio_v', '2')}#! times the world's\\nThe score takes its square "
            f'root, from #v x{WEALTH[0]:g}#! to #v x{WEALTH[1]:g}#!"\n'
            f' SPEC_XS_TECH_TT: "#header Finance Technologies#!\\n$TOOLTIP_DELIMITER$\\nEach one researched{techs}'
            f"\\n\\n{tech('stock_exchange')} is needed to stand #v International#!, "
            f"{tech('central_banking')} to stand #v World Centre#!\"\n"
            f' SPEC_XS_ECON_TT: "#header Economic System#!\\n$TOOLTIP_DELIMITER$\\nBy economic system{econ}"\n')


def standing_block():
    """Exchange tab, first: the four Standings as a ladder with ours lit, then the score and the trust that move it."""
    def rung(t):
        reached = f"Not(LessThan_CFixedPoint({v('spec_exch_stand')}, {fx(t)}))"
        badge = lambda shown, extra: f"""	icon = {{
		size = {{ 64 64 }}
		position = {{ 0 8 }}
		parentanchor = top|hcenter
		visible = "[{shown}]"
		texture = "{icons.path(f'exch_tier_{t}')}"
{extra}	}}
"""
        return f"""widget = {{
	size = {{ {(W - 30) // 4} 106 }}
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
		position = {{ 0 -8 }}
		size = {{ 100% 22 }}
		parentanchor = bottom|hcenter
		align = center|nobaseline
		elide = right
		text = "SPEC_EXCH_W_{t}"
	}}
}}
"""
    return f"""flowcontainer = {{
	parentanchor = hcenter
	spacing = 10
{ind("".join(rung(t) for t in range(4)), 1)}}}
{score_levels()}widget = {{
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
    about = (f"Every [concept_spec_financial_panic] rescued at once, #P {1 - PLEDGE_SHARE:.0%}#! cheaper, while the "
             "[concept_treasury] can pay from reserves and we are not in [concept_default]\\n"
             f"[concept_spec_exchange] trust lost to a panic: #P {PLEDGE_PANIC - 1:+.0%}#!\\n"
             f"[concept_spec_capital_flight] received: #P {PLEDGE_FLIGHT - 1:+.0%}#!"
             + ("\\nEach rescue loosens Lending Standards" if cycle.ON else "") + "\\n$TOOLTIP_DELIMITER$\\n"
             f"Broken by [concept_default]: all trust lost, [concept_spec_market_confidence] "
             f"#N -{PLEDGE_BREAK['conf']}#!, [concept_legitimacy] #N -{PLEDGE_BREAK['legit']}#! for #v 5#! years\\n"
             f"Withdrawing the Pledge takes #v {PLEDGE_NOTICE}#! months' notice")
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
           f' SPEC_PLEDGE_MAKE_TT: "#header Pledge to Rescue the Banks#!\\n$TOOLTIP_DELIMITER$\\n{about}{why("pledge")}"\n'
           f' SPEC_PLEDGE_OUT_TT: "#header $SPEC_PLEDGE_OUT$#!\\n$TOOLTIP_DELIMITER$\\n{about}{why("pledge_leave")}"\n'
           ' spec_pledge_stand_tt: "Our [concept_spec_exchange] stands #v National#! or higher"\n'
           f' spec_pledge_debt_tt: "Our debt is no more than #v {PLEDGE_DEBT:.0%}#! of our [concept_credit]"\n'
           ' spec_pledge_panic_tt: "There is no [concept_spec_financial_panic]"\n'
           ' spec_pledge_made_tt: "We have not already made the Pledge"\n'
           ' spec_pledge_none_tt: "We have made the Pledge"\n'
           ' spec_pledge_leaving_tt: "We are not already withdrawing it"\n'
           ' SPEC_PLEDGE_UNMET: "\\n\\n#N The [concept_treasury] cannot honor the Pledge#!, so the [concept_spec_financial_panic] runs its course"\n'
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
    out = (' SPEC_H_CENTRES: "Leading Exchanges"\n'
           ' SPEC_H_CENTRES_TT: "#header $concept_spec_financial_centres$#!\\n$concept_spec_financial_centre_desc$"\n'
           ' concept_spec_financial_centre: "Leading Exchange"\n'
           ' concept_spec_financial_centres: "Leading Exchanges"\n'
           f' concept_spec_financial_centre_desc: "The $concept_spec_financial_centres$ are the #v {PLACES}#! '
           + ("[Concept('concept_country','$concept_countries$')] with the highest "
              "[Concept('concept_spec_financial_centre','$concept_spec_exchange$')] score, ranked each month. The score rests on "
              "the [concept_investment_pool] income your [concept_spec_exchange] draws on, and rises with its trust, your wealth per "
              "head, Financial Districts, companies, finance technologies, [concept_rank] and economic system. The average of the "
              "top three is shown as #v 100#!.\\n\\n" if ON else
              "[Concept('concept_country','$concept_countries$')] whose Exchanges lead the world, ranked each month.\\n\\n"
              f"Your Exchange's score is #v {MONTHS:g}#! months of [concept_investment_pool] income plus its "
              "[concept_spec_outstanding_credit]. A [concept_spec_financial_panic] cuts this to #v half#!; it then grows "
              f"month by month, to #v one and a half times#! after #v {CALM // 12}#! years without another. The leader's "
              "score is shown as #v 100#!.\\n\\n")
           + f"First place: #P +{pct(1)}#! [concept_prestige], #P -{pct(1)}#! [concept_loans] interest rate"
           + (f", #P +{lim(1)}#! months of Lending Limit" if BRAKE else "")
           + f"\\nLast place (#v {PLACES}#!): #P +{pct(PLACES)}#!, #P -{pct(PLACES)}#!"
           + (f", #P +{lim(PLACES)}#! month{'s' * (lim(PLACES) != '1')}\\nThe Lending Limit bonus needs "
              "[GetTechnology('central_banking').GetName] and Lending Standards #v Sound#! or stricter" if BRAKE else "") + '"\n'
           f' SPEC_CENTRE_PLACE: "#v ##{rank}#!"\n'
           f' SPEC_CENTRE_PLACE_TT: "We rank #v ##{rank}#! among the world\'s {centres}"\n'
           ' SPEC_CENTRE_EMPTY: "No $concept_spec_financial_centres$"\n'
           ' SPEC_CENTRE_COL_NAME: "$concept_country$"\n'
           ' SPEC_CENTRE_COL_SCORE: "Score"\n'
           ' SPEC_CENTRE_COL_SCORE_TT: "The [concept_spec_exchange]\'s capital, with diminishing returns, times its depth: '
           'wealth per head, Financial Districts, companies, finance technologies and trust\\n'
           + ("#v 100#! is the average of the world\'s top three" if ON else "#v 100#! is the leader\'s") + '"\n'
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
                f'$TOOLTIP_DELIMITER$\\n{stats}\\n\\n[concept_prestige]: #P +{pct(n)}#!\\n'
                f'[concept_loans] interest rate: #P -{pct(n)}#!'
                + (f"\\nLending Limit: #P +{lim(n)}#! month{'s' * (lim(n) != '1')} (with [GetTechnology('central_banking').GetName], "
                   "Lending Standards #v Sound#! or stricter)" if BRAKE else "") + '"\n')
    if not ON:
        return out
    limit = f"{P}.ScriptValue('spec_exch_limit')"
    brake = (f" SPEC_EXCH_LIMIT: \"[SelectLocalization({gt(limit)}, 'SPEC_EXCH_LIMIT_ON', 'SPEC_EXCH_LIMIT_OFF')]\"\n"
             f' SPEC_EXCH_LIMIT_ON: "\\nLending Limit from our place among the {centres}: #P +[{limit}|0]#! months, up to #v {leverage.RUIN}#! in all"\n'
             f' SPEC_EXCH_LIMIT_OFF: "\\nLending Limit from our place among the {centres}: #N none#! before [GetTechnology(\'central_banking\').GetName], or while Lending Standards are #v Lax#! or #v Reckless#!"\n')
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
    # what _panic_cut, PANIC and PANIC_OVER do: a share by leverage at the start, half that if caught or pledged, then
    # halved again if the panic ran its full course unrescued
    cut = (f"#N -{PANIC_CUT[0]:.0%}#! to #N -{sum(PANIC_CUT):.0%}#! of trust as it starts, more with higher "
           "[concept_spec_leverage]" if leverage.ON else f"#N -{0.5:.0%}#! of trust as it starts")
    trust_how = (("Each month: #P rises#! with no [concept_spec_financial_panic] while Lending Standards are #v Sound#! or "
                  "stricter\\nHolds while #v Lax#!, #N falls#! while #v Reckless#!\\n" if cycle.ON else
                  "Each month: #P rises#! with no [concept_spec_financial_panic]\\n")
                 + "Boom ending in a main good: [concept_spec_correction] #P a little#!, [concept_spec_bust] or "
                 "[concept_spec_collapse] #N a lot#!\\n"
                 f"[concept_spec_financial_panic]: {cut}\\nHalved if set off by a [concept_spec_foreign_panic]"
                 + (" or under the Pledge" if PLEDGE_ON else "")
                 + ", and again if it runs its course with no Bank Rescue"
                 + ("\\n[concept_spec_bad_debts]: #N falls#! each month, and the Standing cannot rise" if CRUNCH else "")
                 + f"\\nA new Exchange starts at #v {0.5:.0%}#!")
    # Phase 5's links, in the Exchange row's tooltip
    links = ((f"\\n[concept_spec_market_mood] swings, by trust: #v x[{P}.ScriptValue('spec_exch_mood')|2]#!" if MOOD_REF else "")
             + (f"\\n[concept_spec_market_confidence] recovers, by trust: #v x[{P}.ScriptValue('spec_exch_recover')|2]#!" if RECOVER_REF else "")
             + (f"[AddLocalizationIf({P}.Var('spec_crunch').IsSet, 'SPEC_EXCH_FX_CRUNCH')]" if CRUNCH else "")
             + (f"[AddLocalizationIf({is_stand('GreaterThan', 0.5)}, 'SPEC_EXCH_FX_LEAN')]" if LEAN else "")
             + (f"[AddLocalizationIf({is_stand('GreaterThan', 0.5)}, 'SPEC_EXCH_FX_IND')]" if LINKS and LINK_IND else ""))
    links_loc = ((f' SPEC_EXCH_FX_CRUNCH: "\\n[concept_spec_bad_debts]: the Standing cannot rise, and trust falls #N {LINK_CRUNCH / CALM:.1%}#! per month"\n'
                  if CRUNCH else "")
                 + (f' SPEC_EXCH_FX_LEAN: "\\n[concept_spec_market_mood] from companies with high [concept_prosperity]: '
                    f"#v [{P}.ScriptValue('spec_exch_lean')|+=2]#! per month\"\n" if LEAN else "")
                 + (f' SPEC_EXCH_FX_IND: "\\nIndustrialists\' political strength: #P +[Multiply_CFixedPoint({stand(P)}, {fx(LINK_IND)})|%0]#!"\n'
                    ' spec_exch_industry: "Exchange Standing"\n'
                    ' spec_exch_industry_desc: "The Industrialists gain strength from the [concept_country]\'s [concept_spec_exchange]."\n'
                    if LINKS and LINK_IND else ""))
    nxt = [f"To stand #v National#!: #v {NATIONAL:g}%#! of the top three's score, #v {REG_NATIONAL:g}%#! of our region's leader's, "
           f"or a place among the {centres}",
           f"To stand #v International#!: a place among the #v {PLACES}#! {centres} or the lead in our region, with {stock}",
           f"To stand #v World Centre#!: a top #v {WORLD_PLACES}#! place among the {centres}, with {bank}",
           f"#v World Centre#! is the highest Standing. It is kept while we hold a top #v {WORLD_PLACES}#! place"]
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
            "The one furthest past its mark wins; until one is reached, the Exchange keeps its name.\\n") if EARN and not NAMES_ON else ""
    tier_fx = lambda t: ("Every market begins here" if t == 0 else f"Investor Reaction: #v {up(HYPE[t])}#!"
                         + f"\\n[concept_prestige]: #P +{PRESTIGE:.0%}#! when not among the {centres}"
                         + (f"\\nReceives [concept_spec_capital_flight]: #P x{FLIGHT[t]:g}#!" if t >= 2 else "")
                         + (f"\\n[concept_spec_foreign_panic] losses: #P {WORLD_SHELTER - 1:+.0%}#!\\n{_mod_words(WORLD_FX, chr(92) + 'n')}"
                            "\\nOne rival free of upkeep" if t == 3 else ""))
    card_fx = [f"Investor Reaction: #v {up(KNOWN_HYPE)}#!", f"Trust losses: #P {KNOWN_LOSS - 1:+.0%}#!",
               f"Up to #P {up(KNOWN_CREDIT)}#! credit lent into the [concept_investment_pool] each month"]
    card_by = [(f"{tc} levels", sv("spec_log_ktc"), EARN_TC),
               ("Years of sound lending", f"#v [Divide_CFixedPoint({P}.ScriptValue('spec_log_ksnd'), {fx(12)})|1]#!", EARN_SOUND / 12),
               ("Prosperous companies", sv("spec_log_kco"), EARN_CO)]
    ui = ("".join(f' SPEC_EXCH_TIER_TT_{t}: "#header {words[t]}#!\\n{tier_fx(t)}'
                  + (f"\\n$TOOLTIP_DELIMITER$\\n{nxt[t - 1]}" if t else "") + '"\n'
                  + f" SPEC_EXCH_TIER_N_{t}: \"Markets: #v [GetGlobalVariable('spec_exch_n_{t}').GetValue|0]#!\"\n" for t in range(4))
          + "".join(f' SPEC_EXCH_CARD_H_{n}: "#b $SPEC_EXCH_KNOWN_{n}$#!"\n' for n in (1, 2, 3))
          + "".join(f' SPEC_EXCH_CARD_N_{n}: "{what}\\n{now} of #v {mark:g}#!"\n'
                    f' SPEC_EXCH_CARD_TT_{n}: "#header {known[n]}#!\\n{card_fx[n - 1]}\\n$TOOLTIP_DELIMITER$\\n'
                    f'Earned from: {what}, {now} of #v {mark:g}#!"\n' for n, (what, now, mark) in enumerate(card_by, 1))
          + ' SPEC_EXCH_TIER_EMPTY: "No market holds this Standing"\n'
          ' SPEC_CENTRE_COL_TRUST: "Trust"\n'
          ' SPEC_CENTRE_COL_RIVAL: "Rival"\n'
          ' SPEC_CENTRE_COL_RIVAL_TT: "Whether our [concept_spec_exchange] rivals theirs"\n'
          ' SPEC_CENTRE_COL_KNOWN: "Specialities"\n'
          ' SPEC_CENTRE_COL_KNOWN_TT: "The Paths to Renown the [concept_country]\'s [concept_spec_exchange] has chosen"\n'
          ' SPEC_CENTRE_COL_TRUST_TT: "How far the [concept_country]\'s [concept_spec_exchange] is trusted"\n'
          ' SPEC_CENTRE_TRUST: "#v $SPEC_EXCH_TRUST$#!"\n'
          + f' SPEC_EXCH_SCORE_LINE: "[Concept(\'concept_spec_financial_centre\',\'$concept_spec_exchange$\')] score #v [{v("spec_centre_score")}|0]#!"\n'
          + _parts_loc()
          + "".join(f' SPEC_EXCH_TRUST_LV_{i}: "#{TRUST_COL[i]} {w}#!"\n' for i, w in enumerate(TRUST_LV))
          + "".join(f' SPEC_EXCH_TRUST_LV_TT_{i}: "#header {w}#!\\nTrust from #v {i * 25}%#! to #v {i * 25 + 25}%#!{_trust_words(i)}"\n'
                    for i, w in enumerate(TRUST_LV))
          + f' SPEC_EXCH_TRUST_HEAD: "#grey Trust:#! #b {TRUST_PICK()}#!"\n'  # the label and the coloured level; its % is in the tooltip
          f' SPEC_EXCH_G_TRUST_TT: "#header Trust: {TRUST_PICK()} $SPEC_CENTRE_TRUST$#!\\n$TOOLTIP_DELIMITER$\\n{trust_how}"\n'
          ' SPEC_H_KNOWN: "Specialities"\n'
          ' SPEC_H_KNOWN_TT: "#header Known For#!\\n$SPEC_EXCH_CARD_NOTE$"\n'
          f' SPEC_H_KNOWN_RIGHT: "#v {_pick(v("spec_exch_known"), "SPEC_EXCH_KNOWN", 3)}#!"\n'
          ' SPEC_EXCH_CARD_HELD: "#P Known for this#!"\n'
          ' SPEC_EXCH_CARD_NOTE: "An Exchange becomes known for what its country builds. Once a year, the one furthest past '
          'its mark gives the Exchange its name; until one is reached, it keeps the name it has."\n')
    if NAMES_ON:
        ui = _names_loc(ui, known)
    if RIVAL_ON:
        ui += __import__("rivals").loc()
    return (ui + "".join(f' SPEC_EXCH_W_{i}: "{w}"\n' for i, w in enumerate(words))
            + "".join(f' SPEC_EXCH_NEXT_{i}: "{w}"\n' for i, w in enumerate(nxt))
            + "".join(f' SPEC_EXCH_KNOWN_{i}: "{w}"\n' for i, w in enumerate(known))
            + f' SPEC_CENTRE_STAND: "#v {_pick(stand(P), "SPEC_EXCH_W", 3)}#!"\n'
            f' SPEC_EXCH_STAND_ME: "{_pick(stand("GetPlayer.MakeScope"), "SPEC_EXCH_W", 3)}"\n'
            f' SPEC_EXCH_TRUST: "[Divide_CFixedPoint({v("spec_centre_trust")}, {fx(CALM)})|%0]"\n'
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
            f' SPEC_EFFECT_EXCH_TT: "#header $SPEC_EFFECT_EXCH$#!\\n[concept_spec_exchange] Standing: $SPEC_EFFECT_EXCH_VALUE$\\n'
            f'$TOOLTIP_DELIMITER$\\n[Concept(\'concept_spec_financial_centre\',\'$concept_spec_exchange$\')] score: #v {score}#!\\nTrust: #v $SPEC_EXCH_TRUST$#!\\n'
            f"{'Exchange Charter' if NAMES_ON else 'Known for'}: #v {_pick(v('spec_exch_known'), 'SPEC_EXCH_KNOWN', 3)}#!\\n{earn}$TOOLTIP_DELIMITER$\\n"
            f'Investor Reaction: {pct("spec_exch_hype")}\\n'
            f"[SelectLocalization({is_stand('GreaterThan', 1.5)}, 'SPEC_EXCH_FX_FLIGHT', 'SPEC_EXCH_FX_FLIGHT_GP')]"
            f"[AddLocalizationIf(And({is_stand('GreaterThan', 0.5)}, Not({P}.Var('spec_centre_rank').IsSet)), 'SPEC_EXCH_FX_PRESTIGE')]"
            f"[AddLocalizationIf({moved('loss') if NAMES_ON else f"LessThan_CFixedPoint({P}.ScriptValue('spec_exch_loss'), {fx(1)})"}, 'SPEC_EXCH_FX_LOSS')]"
            f"[AddLocalizationIf({moved('credit') if NAMES_ON else gt(credit, 1)}, 'SPEC_EXCH_FX_CREDIT')]{links}"
            f"\\n$TOOLTIP_DELIMITER$\\n{_pick(stand(P), 'SPEC_EXCH_NEXT', 3)}\"\n"
            f' SPEC_EXCH_FX_FLIGHT: "Receives [concept_spec_capital_flight]: #v x[{P}.ScriptValue(\'spec_exch_flight\')|{1 if NAMES_ON else 0}]#!"\n'
            ' SPEC_EXCH_FX_FLIGHT_GP: "Receives [concept_spec_capital_flight]: only as a [concept_great_power]"\n'
            f' SPEC_EXCH_FX_PRESTIGE: "\\n[concept_prestige]: #P +{PRESTIGE:.0%}#!"\n'
            + (f' SPEC_EXCH_FX_LOSS: "\\nTrust losses: {pct("spec_exch_loss")}"\n' if NAMES_ON else
             f' SPEC_EXCH_FX_LOSS: "\\nTrust losses: #P {KNOWN_LOSS - 1:+.0%}#!"\n')
            +
            (f' SPEC_EXCH_FX_CREDIT: "\\nCredit lent: up to {pct("spec_exch_credit")}"\n' if NAMES_ON else
               f' SPEC_EXCH_FX_CREDIT: "\\nCredit lent: up to #P {up(KNOWN_CREDIT)}#!"\n')
            +
            # the concept
            ' concept_spec_exchange: "Exchange"\n'
            ' concept_spec_exchange_desc: "A [concept_country]\'s $concept_spec_exchange$ is where its shares, bonds and credit change hands. Its Standing '
            "follows its [Concept('concept_spec_financial_centre','$concept_spec_exchange$')] score: #v Provincial#!, #v National#!, "
            f"#v International#! (needs {stock}) or #v World Centre#! (needs {bank}). The higher your Exchange's Standing, the more "
            "strongly investors react to rising prices, and from #v International#! it also receives [concept_spec_capital_flight].\\n\\n"
            + (NAMES_ABOUT if NAMES_ON else
               f"An Exchange becomes known for what its country builds, checked once a year: a #v Commodity Exchange#! for "
               f"higher Investor Reaction, from {tc} levels; a #v Money Market#! for smaller Trust losses, from years of sound "
               "lending; or a #v Share Market#! for more credit, from prosperous companies. "
               "The one furthest past its mark wins; until one is reached, the Exchange keeps its name."
               if EARN else
               "Each time an Exchange first reaches a higher Standing, it chooses what it is to be known for: a "
               "#v Commodity Exchange#! for higher Investor Reaction, a #v Money Market#! for smaller Trust losses, or a "
               "#v Share Market#! for more credit.")
            + "\\n\\nTrust rises in calm years" + (" under sound lending" if cycle.ON else "")
            + ", and falls with [Concept('concept_spec_financial_panic','$concept_spec_financial_panics$')]"
            + (", [concept_spec_bad_debts]" if CRUNCH else "")
            + ' and a [concept_spec_bust] or [concept_spec_collapse] in a main good. Low trust raises the interest rate on your [concept_loans] and high trust lowers it."\n'
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
        assert all(f"remove_modifier = spec_trust_{i}" in script for i, f in enumerate(TRUST_FX) if f)
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
        assert f"multiply = {levers.ISSUE_SCORE:g}" in values() and "spec_log_issue" in values() + LOG
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
        assert script.count("NOT = { has_variable = spec_crunch } ") == 1 and f"{LINK_CRUNCH / CALM:.1%}" in words
    if NAMES_ON:
        # the AI picks its free speciality by its share of each leader, the first listed on a tie; a charter change
        # (the player's or the AI's) stops what the new charter forbids; the charter's cost is a straight cut
        assert ai_pick({"floor": 0.4, "sound": 0.9, "door": None}) == "sound" and ai_pick({"floor": 0.5, "sound": 0.5}) == "floor"
        assert ai_pick({"price": None}) is None and script.count("spec_ai_best value = -1") == 4
        # the AI's charter: none or a dead path takes the fewest it can place on; a crowded one moves only to room
        y = {1: True, 2: True, 3: True}
        assert charter_pick({1: 5, 2: 1, 3: 1}, 0, y) == 2 and charter_pick({1: 5, 2: 1, 3: 0}, 1, {**y, 3: False}) == 2
        assert charter_pick({1: 4, 2: 3, 3: 3}, 1, y) == 1 and charter_pick({1: 2, 2: 0, 3: 0}, 1, {**y, 1: False}) == 2
        assert charter_pick({1: 0, 2: 0, 3: 0}, 0, {1: False, 2: False, 3: False}) == 0
        # charters 2 and 3, player and AI; the monthly Standing-fall passes and the player's at the fall itself
        assert script.count("spec_pursue_stop_price = yes") == 2 * 3 + 3 + 3  # + the AI's charter balance
        assert f"multiply = {1 - CHARTER_COST:g} }}" in script and "spec_exch_known_new" not in script
        assert "has_technology_researched = stock_exchange" in rules[0] and script.count(SHARES) > 2  # International's gate and the AI's charters
        # a field's leader is cleared once nobody qualifies; the bar's tooltip says so
        assert script.count("remove_global_variable = spec_ldv_") == len(NAMES) and "SPEC_NAME_NOLEAD" in words
        # a speciality's hooks follow its strength, the drawback as much as the benefit
        assert "has_variable = spec_has_" not in values() and values().count("multiply = { value = var:spec_pw_") == 4 * len(NAMES)  # 2 hooks and the 2 tally lines
        assert words.count("[concept_spec_capital_flight] received at International") == 2 * sum("flight" in NAME_FX[k] for k, *_ in NAMES)
    if NAMES_ON:
        # the hand-out: first places before seconds before thirds, no more than the Standing allows; every name
        # helps one hook and hurts another; the player's charter is a button, the AI's is still earned
        assert all(2 <= len(NAME_FX[k]) <= 3 and set(NAME_FX[k]) <= set(FX_WORDS) for k, *_ in NAMES)
        assert set(FX_WORDS) == {"hype", "flight", "loss", "credit", *NX_HOOKS}
        assert script.count("order_by = spec_name_") == 3 * len(NAMES) and "name = spec_t3_door value = {" in script  # monthly leader, runner-ups and annual top three
        assert script.count("set_variable = spec_has_") == len(NAMES) and "is_player = no OR = { NOT = { has_variable = spec_exch_stand }" in script
        assert all(f"spec_sgui_charter_{n} = " in rules[1] and f"spec_can_charter_{n} = " in rules[0] for n in (1, 2, 3))
        assert all(f" SPEC_NAME_TT_{k}:" in words and f"\nspec_name_{k} = " in values() for k, *_ in NAMES)
        assert words.count(" SPEC_EXCH_CARD_NOTE:") == 1 and words.count(" SPEC_EXCH_CARD_TT_1:") == 1
        # the podium and the pursuit: three leaders a field by country, one tally up and the rest down
        assert script.count("set_global_variable = { name = spec_w_") == 3 * len(NAMES)
        assert all(f"spec_sgui_pursue_{k} = " in rules[1] and f" SPEC_NAME_STATUS_{k}:" in words for k, *_ in NAMES)
        assert all(f"multiply = {{ value = var:spec_pw_{k} multiply = {PURSUE_BOOST - 1:g} add = 1 }}" in values()
                   and f"spec_sgui_pursue_stop_{k} = " in rules[1] for k, *_ in NAMES)
        assert "spec_pursue_slots = {" in values() and script.count("spec_pursue_to_") >= 3 * len(NAMES)
        # slots by Standing, dropped last-chosen first; each pursuit's bonus by place; trust's effects by level
        assert script.count("var:spec_pursue_n > spec_pursue_slots") == 6 * len(NAMES) and "spec_pu_lock_door" in script
        # the fall's toast names what it cost; the 5-year keep counts down in months and the Drop tooltip shows it
        assert script.count("set_variable = spec_pu_lost_") == 3 * len(NAMES) and "spec_pu_lost_door" in words + script
        assert script.index("set_variable = spec_pu_lost_door") < script.index("post_notification = spec_exch_down")
        assert f"name = spec_pu_lock_door value = {PURSUE_LOCK * 12}" in script and "name = spec_pu_lock_door add = -1" in script
        assert "days = " not in script.split("spec_pursue_to_door = {")[1].split("}\n\n")[0] and " SPEC_PURSUE_LEFT_door:" in words
        # while a slot is filled the rows that can be chosen are lit and say so; the row shows what each place gives
        assert gui.count("[And(GetVariableSystem.Exists('spec_pick_slot'), And(Country.IsLocalPlayer") == 2 * len(NAMES)  # click, light
        assert all(f"$SPEC_PURSUE_LV_{k}$[AddLocalizationIf" in words for k, *_ in NAMES) and " SPEC_ROW_CLICK:" in words
        assert _pursue_fx("railway", 3) == [("building_railway_throughput_add", 0.12), ("building_group_bg_construction_laborers_mortality_mult", 0.08), ("state_infrastructure_mult", 0.1)]
        assert _pursue_fx("floor", 0) == [("state_trade_capacity_mult", 0.03)] and "spec_pursue_harbour_3 = {" in MODIFIER
        assert _mod_words(TRUST_FX[0]).startswith("#N +10%#! $country_loan_interest_rate_mult$")
        assert _mod_words(TRUST_FX[3]) == "#P -5%#! $country_loan_interest_rate_mult$, #P +2#! $interest_group_ig_industrialists_approval_add$"
        assert script.count("add_modifier = { name = spec_trust_") == sum(1 for f in TRUST_FX if f)
        assert "clamp_variable = { name = spec_pw_door min = 0 max = 1 }" in script
        assert script.count("save_temporary_scope_as = spec_now_") == len(NAMES) and f"spec_chm_door >= {LEAD_HOLD}" in script
        assert "is_country_alive = yes" in _eligible("price", 1, "")  # annexed leaders may retain their Exchange fields
        assert all(f"name = spec_sh_{k} value" in script and f" SPEC_NAME_QTY_{k}:" in words for k, *_ in NAMES)
        assert round(1 / PURSUE_MONTHS + 0.0005, 3) * PURSUE_MONTHS >= 1  # a pursuit reaches full strength
    if RIVAL_ON:
        assert "rivalry.dds" in gui and " SPEC_RV_RAID_TT:" in words and "spec_rival_contest = yes" in script
        assert "spec_sgui_rival" not in gui + script + "".join(rules) and "spec_rival_pick" not in script
    if LINKS:
        # the links at the defaults: mood x1.5 to x0.5 and recovery x0.75 to x1.5 over no trust to full; the lean
        # stays within 0.3 either way; Bad Debts cap the Standing at last month's
        if (LINK_MOOD, LINK_RECOVER, LINK_PROSPER) == (1, 1, 0.2):
            assert links(0, 1) == (1.5, 0.75, 0) and links(CALM, 1) == (0.5, 1.5, 0) and links(CALM / 2, 2)[:2] == (1, 1.125)
        assert links(0, 99)[2] == 0.3 >= links(0, 1.5)[2] and links(0, 0)[2] >= -0.3
        assert all(f"\n{k} = {{" in values() for k in ("spec_exch_mood", "spec_exch_recover")) and bool(LEAN) == ("SPEC_EXCH_FX_LEAN" in words) == ("spec_exch_lean" in values())
        assert not CRUNCH or ("value = local_var:spec_exch_was" in script and "SPEC_EXCH_FX_CRUNCH" in words)
        assert ("spec_exch_industry" in MODIFIER + script + words) == bool(LINK_IND)
    assert script.count("ordered_country") == 1 + SHOWN * ON + (1 + len(REGIONS) if ON else 1) + 3 * len(NAMES) * bool(NAMES_ON)
    assert f"max = {PLACES}\n\t\t\tcheck_range_bounds = no" in script and "name = spec_centre_new value = global_var:spec_centre_next" in script
    if ON:
        assert TOP.count("ordered_country") == 1 and "max = 3" in TOP and "position =" not in TOP
        assert _leaders("\t").count("max = 2\n\t\t\tcheck_range_bounds = no") == len(NAMES)
    assert "+10%" in words and "-2%" in words  # the first and the last place at the default step
    keys = {line.split(":")[0].strip() for line in words.splitlines()}
    used = {k.strip('"') for k in __import__("re").findall(r'"SPEC_[A-Z0-9_]+"', gui)}
    assert used <= keys, used - keys
    print("ok")
