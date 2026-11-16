"""Toasts telling a player that a country tied to them (spec_every_tied's ties) has panicked or turned greedy."""

import centres  # its switches decide which Exchange toasts exist; it does not import this module
import leverage
import cycle
V = "gfx/interface/icons/notification_icons"
SRC = "[SCOPE.sC('spec_note_src').GetName]"
GOOD = "[SCOPE.sGoods('spec_note_good').GetName]"
# message key -> (message settings group, icon, color, toast title, toast text)
NOTES = {
    "spec_tied_panic": (
        "spec_foreign_panic_notification_group", "rank_down", "bad",
        f"Panic breaks out in {SRC}",
        f"A [concept_spec_financial_panic] has broken out in {SRC}, and our ties to them have carried a [concept_spec_foreign_panic] into our own markets."),
    "spec_tied_mania": (
        "spec_foreign_mania_notification_group", "company", "neutral",
        f"Speculative mania grips {SRC}",
        f"Investors in {SRC} have been seized by a [concept_spec_speculative_mania]. Should it end in a [concept_spec_financial_panic], "
        "our ties to them will drag down our own [concept_spec_market_confidence]."),
    # our own market: a warning while there is still time to act, and the news when a boom ends
    "spec_feverish": (
        "spec_warning_notification_group", "goods", "bad",
        f"Investors grow feverish over {GOOD}",
        f"[concept_spec_investor_interest] in {GOOD} has become #v Feverish#!. Should it fall back now, the boom will end in a "
        "[concept_spec_collapse] and [concept_spec_market_confidence] will fall sharply."),
    "spec_near_panic": (
        "spec_warning_notification_group", "rank_down", "bad",
        "Confidence nears panic",
        "[concept_spec_market_confidence] has fallen to #v [GetPlayer.Var('spec_conf').GetValue|0]#!. "
        "Below #v $SPEC_PANIC_AT$#!, a [concept_spec_financial_panic] will break out."),
    "spec_nearly_broke": (
        "spec_warning_notification_group", "rank_down", "bad",
        "Treasury runs low",
        "At our present deficit, we will face [concept_bankruptcy] in #v [GetPlayer.ScriptValue('spec_broke_weeks')|0]#! weeks. "
        "[concept_spec_market_confidence] will keep sliding until the budget recovers."),
    # the panic is over, and the bubble has burst: until now the tab was the only place that said so
    # the Financial Centres (centres.py)
    "spec_centre_gained": (
        "spec_warning_notification_group", "rank_up", "good",
        "Our exchange becomes a Financial Centre",
        "Our [concept_spec_exchange] now ranks among the world's [Concept('concept_spec_financial_centre','$concept_spec_financial_centres$')]. "
        "While it does, we gain [concept_prestige] and pay less interest on our [concept_loans]."),
    "spec_centre_lost": (
        "spec_warning_notification_group", "rank_down", "bad",
        "Our exchange is no longer a Financial Centre",
        "Our [concept_spec_exchange] no longer ranks among the world's [Concept('concept_spec_financial_centre','$concept_spec_financial_centres$')]. "
        "We have lost the [concept_prestige] and the lower interest on our [concept_loans] that came with it."),
    "spec_panic_over": (
        "spec_warning_notification_group", "rank_up", "good",
        "The panic subsides",
        "The [concept_spec_financial_panic] has run its course, and its effects have lifted."),
    "spec_bubble_burst": (
        "spec_warning_notification_group", "rank_down", "bad",
        "The bubble bursts",
        "[concept_spec_market_confidence] has fallen too low to sustain our [concept_spec_speculative_excess]. "
        "The bubble has burst, and $concept_spec_market_confidence$ has fallen further."),
} | ({"spec_lev_unsafe": (
        "spec_warning_notification_group", "rank_down", "bad",
        "Leverage passes the safe limit",
        f"[concept_spec_leverage] has risen above #v {leverage.SAFE}#! months, the most that is safe. From here, a "
        "[concept_spec_financial_panic] will begin at a higher [concept_spec_market_confidence] and leave [concept_spec_bad_debts] behind it."),
} if leverage.ON else {}) | {f"spec_boom_end_{sev}": (
        "spec_boom_end_notification_group", "goods", color,
        f"{GOOD} boom ends in a {name}",
        f"The boom in {GOOD} has ended in a [concept_spec_{key}]. [concept_spec_market_confidence] has fallen, and the industry "
        f"built up for prices that did not last is now #v Recovering#!, shunned by investors for about #v {months}#! months.$SPEC_NOTE_BANKS$")
    for sev, key, name, color, months in
    # months: generate.UNWINDS' glut lengths (generate imports this module)
    [(1, "correction", "Correction", "neutral", 3), (2, "bust", "Bust", "bad", 6), (3, "collapse", "Collapse", "bad", 12)]}
GROUPS = {"spec_foreign_panic_notification_group": "Foreign Panics",
          "spec_foreign_mania_notification_group": "Foreign Speculative Mania",
          "spec_warning_notification_group": "Speculation Warnings",
          "spec_boom_end_notification_group": "Boom Endings"}
if centres.ON:  # its Standing toasts replace the Financial Centre ones
    EXCH = "$SPEC_EXCH_CITY_ME$ Exchange"
    NEWS = "spec_exchange_notification_group"  # the Exchange's own news, muted apart from the panic warnings
    GROUPS[NEWS] = "Exchange News"
    NOTES = {k: x for k, x in NOTES.items() if k not in ("spec_centre_gained", "spec_centre_lost")} | {
        "spec_exch_up": (
            NEWS, "rank_up", "good",
            "Our exchange rises in standing",
            f"The {EXCH} now stands #v $SPEC_EXCH_STAND_ME$#!, and its booms will run hotter and fall harder."),
        "spec_exch_down": (
            NEWS, "rank_down", "bad",
            "Our exchange loses standing",
            f"The {EXCH} has fallen to #v $SPEC_EXCH_STAND_ME$#!, and has lost what its higher [concept_spec_exchange] Standing brought.$SPEC_EXCH_DOWN_LOST$"),
    }
    # the yearly tally names the Exchange (centres._earn); with the charters (NAMES_ON) it names only the AI's, so no toast
    if centres.EARN and not centres.NAMES_ON:
        NOTES["spec_exch_known_new"] = (
            NEWS, "rank_up", "good",
            "Our exchange makes its name",
            f"The {EXCH} is now known abroad for its #v $SPEC_EXCH_KNOWN_ME$#!.")
    if centres.RIVAL_ON:  # a rivalry's contest settling (rivals.ROUND years)
        NOTES["spec_rival_won"] = (NEWS, "rank_up", "good", "Our Exchange wins a contest",
                                   f"The {EXCH} has come out ahead in its contest with a competing Exchange, and its trust has grown.")
        NOTES["spec_rival_lost"] = (NEWS, "rank_down", "bad", "Our Exchange loses a contest",
                                    f"The {EXCH} has come out behind in its contest with a competing Exchange, and its trust has fallen.")


# SelectLocalization evaluates selected strings without the notification SCOPE.
# Choose the numeric-detail variant in script instead, then expand its $keys$
# directly in the notification context. Keep the original message IDs for saves.
for severity in (1, 2, 3):
    base = f"spec_boom_end_{severity}"
    group, icon, color, title, desc = NOTES[base]
    for suffix, bank, over in (("plain", False, False), ("bank", True, False),
                               ("over", False, True), ("bank_over", True, True)):
        NOTES[f"{base}_{suffix}"] = (
            group, icon, color, f"$notification_{base}_name$",
            f"$notification_{base}_desc$" + ("$SPEC_NOTE_BANKS_ON$" if bank else "")
            + ("$SPEC_NOTE_OVER_ON$" if over and cycle.ON else "") + cycle.NOTE_REF)


def boom_note_scopes(g, t="\t\t\t\t\t"):
    """Snapshot optional toast details before posting; reset absent values for every good.

    Direct SCOPE.GetValue reads are safe only in the original notification
    context, not inside strings returned by SelectLocalization.
    """
    return "".join(
        f"{t}save_scope_value_as = {{ name = spec_note_{kind} value = {default} }}\n"
        f"{t}if = {{\n{t}\tlimit = {{ has_variable = spec_note_{kind}_{g} }}\n"
        f"{t}\tsave_scope_value_as = {{ name = spec_note_{kind} value = var:spec_note_{kind}_{g} }}\n{t}}}\n"
        for kind, default in (("bank", 1), ("over", 1), ("ppl", 0)))


def boom_post(severity, t="\t\t\t\t\t"):
    """Pick optional numeric sentences before localization loses their scope."""
    bank = "scope:spec_note_bank > 1.04"
    over = "scope:spec_note_over > 1.04"
    out = ""
    for keyword, condition, suffix in (("if", f"{bank} {over}", "bank_over"),
                                       ("else_if", bank, "bank"),
                                       ("else_if", over, "over"),
                                       ("else", None, "plain")):
        out += f"{t}{keyword} = {{\n"
        if condition:
            out += f"{t}\tlimit = {{ {condition} }}\n"
        out += f"{t}\tpost_notification = spec_boom_end_{severity}_{suffix}\n{t}}}\n"
    return out


def messages():
    return "\n".join(f"""{key} = {{
	type = country
	group = "{group}"

	texture = "{V}/{icon}.dds"

	notification_type = toast
	color = {color}
}}
""" for key, (group, icon, color, *_) in NOTES.items())


# On the country the news is about (root). spec_every_tied can reach a country by two ties, so collect first,
# then post once each; the list is emptied as it is read, as vanilla's tsunami effect does.
EFFECTS = """spec_notify_tied = {
	save_scope_as = spec_note_src
	spec_every_tied = { EFFECT = spec_note_tied }
	every_in_list = {
		list = spec_note_list
		remove_from_list = spec_note_list
		post_notification = $TYPE$
	}
}

# WEIGHT comes from spec_every_tied; the game rejects arguments an effect never reads, so it is kept as a local
spec_note_tied = {
	set_local_variable = { name = spec_note_w value = $WEIGHT$ }
	# read once so the game stops logging it as set but never used; a weight is never negative
	if = { limit = { local_var:spec_note_w < 0 } }
	if = {
		limit = {
			is_player = yes
			has_variable = spec_conf
			NOT = { this = root }
			NOT = { is_in_list = spec_note_list }
		}
		add_to_temporary_list = spec_note_list
	}
}
"""


def loc(panic_at):
    if leverage.ON:
        panic_at = "[GetPlayer.MakeScope.ScriptValue('spec_panic_at')|0]"
    out = f' SPEC_PANIC_AT: "{panic_at}"\n' + "".join(f' {g}: "{name}"\n' for g, name in GROUPS.items())
    for key, (*_, name, desc) in NOTES.items():
        n = f"notification_{key}"
        out += (f' {n}_name: "{name}"\n {n}_desc: "{desc}"\n'
                f' {n}_tooltip: "#header ${n}_name$#!\\n$TOOLTIP_DELIMITER$\\n${n}_desc$"\n')
    return out


def build(write):
    write("common/messages/spec_messages.txt", messages())
    write("common/scripted_effects/spec_notify_effects.txt", EFFECTS)
