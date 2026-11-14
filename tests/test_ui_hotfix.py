"""Behavioral checks for Finance filters and the 1.0 panic tooltips.

Evaluate the actual generated visibility expressions against small country/UI
states. These checks need no running game and never write to mod/.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import generate
import interest_list as il
import market_tab as mt
import i18n


def evaluate(expression, country, selected):
    expression = re.sub(
        r"Country\.MakeScope\.Var\('([^']+)'\)\.GetValueWithDefault\('\(CFixedPoint\)([^']+)'\)",
        lambda m: repr(country.get(m[1], float(m[2]))), expression)
    expression = re.sub(r"'\(CFixedPoint\)([^']+)'", r"\1", expression)
    expression = re.sub(r"GetVariableSystem\.Exists\('([^']+)'\)",
                        lambda m: repr(m[1] in selected), expression)
    expression = re.sub(r"GetVariableSystem\.HasValue\('([^']+)', '([^']+)'\)",
                        lambda m: repr(selected.get(m[1]) == m[2]), expression)
    return eval(expression, {"__builtins__": {}}, {
        "And": lambda a, b: a and b, "Or": lambda a, b: a or b,
        "Not": lambda a: not a, "GreaterThan_CFixedPoint": lambda a, b: a > b,
        "EqualTo_CFixedPoint": lambda a, b: a == b, "no": False,
        "SelectLocalization": lambda test, yes, no: yes if test else no,
        "Select_CFixedPoint": lambda test, yes, no: yes if test else no,
    })


class FinanceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.categories = {"grain": "staple", "tools": "industrial", "wine": "luxury", "small_arms": "military"}
        board = il.board({"CATEGORY": cls.categories})
        empty_states = []
        for match in re.finditer('text = "SPEC_IL_EMPTY_FILTERS"', board):
            empty_widget = board[board.rfind("flowcontainer = {", 0, match.start()):match.start()]
            mode, empty = re.findall(r'visible = "\[([^\n]+)\]"', empty_widget)
            empty_states.append(f"And({mode}, {empty})")
        cls.empty = mt.any_of(empty_states)
        cls.ordinary_empty = empty_states[0]
        cls.row = re.search(r'visible = "\[([^\n]+)\]"', il.row("grain"))[1]
        cls.constants = {name: value for name, value in vars(generate).items()
                         if name.isupper() and isinstance(value, (int, float, dict))}
        cls.constants.update(CATEGORY=generate.categories(), UNWINDS=generate.UNWINDS)
        cls.loc = dict(m.groups() for m in map(i18n.ENTRY.match, mt.loc(cls.constants).splitlines()) if m)

    def country(self, word=3, **extra):
        state = {"spec_word_grain": word, f"spec_n_w{word}_staple": int(word > 0)}
        state.update(extra)
        return state

    def test_first_month_empty_then_trade_appears(self):
        self.assertNotIn("spec_ui_r_", self.ordinary_empty)
        self.assertNotIn("spec_word_", self.ordinary_empty)
        self.assertTrue(evaluate(self.empty, {}, {}))
        self.assertFalse(evaluate(self.empty, self.country(), {}))

    def test_empty_category_and_tier_filters(self):
        for selection in ({mt.CAT: "military"}, {il.TIER: "6"},
                          {mt.CAT: "staple", il.TIER: "6"}):
            with self.subTest(selection=selection):
                self.assertTrue(evaluate(self.empty, self.country(), selection))
        self.assertFalse(evaluate(self.empty, self.country(), {mt.CAT: "staple", il.TIER: "3"}))

    def test_great_issue_is_an_active_control(self):
        selected = {il.ACTIVE: "yes"}
        self.assertFalse(evaluate(self.row, self.country(), selected))
        for active in ("spec_ui_r_grain", "spec_ui_e_grain", "spec_issue_grain"):
            with self.subTest(active=active):
                value = 1 if active == "spec_issue_grain" else 2
                country = self.country(**{active: value})
                self.assertTrue(evaluate(self.row, country, selected))
                self.assertFalse(evaluate(self.empty, country, selected))
                self.assertTrue(evaluate(self.empty, country, selected | {mt.CAT: "military"}))
                self.assertTrue(evaluate(self.empty, country, selected | {il.TIER: "6"}))

    def test_untraded_good_does_not_survive_a_stale_sorted_list(self):
        self.assertFalse(evaluate(self.row, self.country(word=0, spec_issue_grain=1), {}))

    def test_filter_caption_uses_finance_selection(self):
        expression = self.loc["SPEC_CURRENT_GOODS_FILTERS"][1:-1]
        self.assertNotIn("MarketPanel", expression)
        self.assertEqual(evaluate(expression, {}, {}), "ALL_GOODS")
        for category in mt.CATEGORIES:
            self.assertEqual(evaluate(expression, {}, {mt.CAT: category}), category.upper() + "_FILTER_NAME")

    def test_panic_explains_output_tax_and_relief(self):
        self.assertIn("SPEC_PANIC_ALL_EFFECTS", self.loc["SPEC_PANIC_TT"])
        self.assertIn("#N -10%#!", self.loc["SPEC_PANIC_ECONOMY"])
        self.assertIn("#N -15%#!", self.loc["SPEC_PANIC_ECONOMY"])
        self.assertIn("#N -5%#!", self.loc["SPEC_PANIC_ECONOMY_RESCUED"])
        self.assertIn("#N -7.5%#!", self.loc["SPEC_PANIC_ECONOMY_RESCUED"])
        self.assertEqual(self.loc["spec_panic_relief"], "Panic Relief")
        self.assertIn("SPEC_PANIC_RELIEF_NOTE", self.loc["SPEC_RESCUE_TT"])
        self.assertIn("SPEC_PANIC_RELIEF_NOTE", self.loc["SPEC_PANIC_TT_END"])

    def test_external_panel_navigation_closes_finance_and_disarms_slot(self):
        guard = mt.navigation_guard()
        trigger = re.search(r'trigger_when = "\[([^\n]+)\]"', guard)[1]
        for finance_open in (False, True):
            for panel_open in (False, True):
                with self.subTest(finance=finance_open, panel=panel_open):
                    selected = {mt.FIN: "open"} if finance_open else {}
                    expression = trigger.replace("InformationPanelBar.IsAnyPanelOpen", repr(panel_open))
                    self.assertEqual(evaluate(expression, {}, selected), finance_open and panel_open)
        clears = re.findall(r'on_start = "\[GetVariableSystem.Clear\(\'([^\']+)\'\)\]"', guard)
        self.assertEqual(clears, [mt.FIN, mt.PICK])
        self.assertNotIn("InformationPanelBar.ClosePanel", guard)
        self.assertNotIn("visible =", guard)
        host = generate.information_panel_bar()
        self.assertEqual(host.count("spec_finance_navigation_guard = {}"), 1)
        self.assertLess(host.index("spec_finance_navigation_guard = {}"), host.index("spec_finance_window = {}"))


if __name__ == "__main__":
    unittest.main()
