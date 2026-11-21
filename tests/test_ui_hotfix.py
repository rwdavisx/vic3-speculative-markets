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
        "And3": lambda a, b, c: a and b and c, "And": lambda a, b: a and b, "Or": lambda a, b: a or b,
        "Not": lambda a: not a, "GreaterThan_CFixedPoint": lambda a, b: a > b,
        "EqualTo_CFixedPoint": lambda a, b: a == b, "no": False,
        "GreaterThanOrEqualTo_CFixedPoint": lambda a, b: a >= b,
        "SelectLocalization": lambda test, yes, no: yes if test else no,
        "Select_CFixedPoint": lambda test, yes, no: yes if test else no,
    })


class FinanceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.categories = {"grain": "food", "tools": "industry", "wine": "plantation", "small_arms": "defence"}
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
        state = {"spec_word_grain": word, f"spec_n_w{word}_food": int(word > 0)}
        state.update(extra)
        return state

    def test_first_month_empty_then_trade_appears(self):
        self.assertNotIn("spec_ui_r_", self.ordinary_empty)
        self.assertNotIn("spec_word_", self.ordinary_empty)
        self.assertTrue(evaluate(self.empty, {}, {}))
        self.assertFalse(evaluate(self.empty, self.country(), {}))

    def test_empty_category_and_tier_filters(self):
        for selection in ({mt.CAT: "defence"}, {il.TIER: "6"},
                          {mt.CAT: "food", il.TIER: "6"}):
            with self.subTest(selection=selection):
                self.assertTrue(evaluate(self.empty, self.country(), selection))
        self.assertFalse(evaluate(self.empty, self.country(), {mt.CAT: "food", il.TIER: "3"}))

    def test_great_issue_is_an_active_control(self):
        selected = {il.ACTIVE: "yes"}
        self.assertFalse(evaluate(self.row, self.country(), selected))
        for active in ("spec_ui_r_grain", "spec_ui_e_grain", "spec_issue_grain"):
            with self.subTest(active=active):
                value = 1 if active == "spec_issue_grain" else 2
                country = self.country(**{active: value})
                self.assertTrue(evaluate(self.row, country, selected))
                self.assertFalse(evaluate(self.empty, country, selected))
                self.assertTrue(evaluate(self.empty, country, selected | {mt.CAT: "defence"}))
                self.assertTrue(evaluate(self.empty, country, selected | {il.TIER: "6"}))

    def test_untraded_good_does_not_survive_a_stale_sorted_list(self):
        self.assertFalse(evaluate(self.row, self.country(word=0, spec_issue_grain=1), {}))

    def test_filter_caption_uses_finance_selection(self):
        expression = self.loc["SPEC_CURRENT_GOODS_FILTERS"][1:-1]
        self.assertNotIn("MarketPanel", expression)
        self.assertEqual(evaluate(expression, {}, {}), "ALL_GOODS")
        for category in mt.CATEGORIES:
            self.assertEqual(evaluate(expression, {}, {mt.CAT: category}), "SPEC_SECTOR_" + category.upper())

    def test_sector_filter_rings_and_icons_follow_selection(self):
        filters = mt.cat_filters()
        rings = re.findall(r'round_frame_dec.dds"\s+visible = "\[([^\n]+?)\]"', filters)
        self.assertEqual(len(rings), len(mt.CATEGORIES))
        for i, sector in enumerate(mt.CATEGORIES):
            self.assertEqual(filters.count(f"sector_{sector}.dds"), 2)
            self.assertTrue(evaluate(rings[i], {}, {}))
            for selected in mt.CATEGORIES:
                self.assertEqual(evaluate(rings[i], {}, {mt.CAT: selected}), sector == selected)
        self.assertEqual(filters.count("goods_filter_button = {"), 2 * len(rings))

    def test_sector_filters_fit_two_centered_rows(self):
        rows = mt.cat_filters().split("flowcontainer = { parentanchor = center spacing = 3")[1:]
        self.assertEqual([row.count("round_frame_dec.dds") for row in rows], [5, 4])
        for row in rows:
            count = row.count("round_frame_dec.dds")
            self.assertEqual(row.count("round_button_big_wood_map_interaction.dds"), count * 2)
            self.assertEqual(row.count("size = { 52 52 }"), count * 2)
            self.assertEqual(row.count("size = { 40 40 }"), count * 2)

    def test_sector_box_and_tooltips(self):
        import charts
        chart = charts.sector_chart()
        self.assertIn("treemapchart = {", chart)
        self.assertNotIn("piechart = {", chart)
        self.assertNotIn("GetVariableSystem.Exists('piecharts')", chart)
        for good, sector in self.constants["CATEGORY"].items():
            tip = self.loc["SPEC_SECTOR_" + sector.upper() + "_TT"]
            self.assertIn(f"GetGoods('{good}').GetName", tip)
            self.assertIn(f"spec_sector_share_{sector}", tip)

    def test_sector_remainder_starts_with_fifth_sector(self):
        import sectors
        self.assertIn("var:spec_sector_position <= 4 ", sectors.rank_chart())
        tooltip = self.loc["SPEC_SECTOR_OTHER_TT"]
        for sector in sectors.GROUPS:
            name = "SPEC_SECTOR_" + sector.upper()
            item = self.loc[name + "_ITEM"]
            self.assertIn(f"#tooltip:[Country.GetTooltipTag],{name}_TT ", item)
            self.assertIn(f"@spec_sector_{sector}!", item)
            self.assertIn(f"icon = spec_sector_{sector}\n", mt.icons.texticons())
            clauses = [part for part in tooltip.split("[AddLocalizationIf(")
                       if f"spec_sector_rank_{sector}'" in part]
            ranks = [int(re.search(r", '\(CFixedPoint\)(\d+)'\),", part)[1]) for part in clauses]
            self.assertEqual(ranks, [5, 6, 7, 8, 9])

    def test_ranked_goods_summary_uses_displayed_country_in_observer_mode(self):
        board = mt.goods_board({"CATEGORY": self.categories})
        charts_at = board.index('text = "CHARTS"')
        filters_at = board.index('text = "FILTERS"', charts_at)
        rows_at = board.index('tooltip = "SPEC_JE_FAVOURED_TT"', filters_at)
        header_at = board.index('sort_button = {', rows_at)
        summary = board[filters_at:header_at]
        self.assertNotIn("Goods.GetNameNoFormatting", summary)
        self.assertIn("Country.MakeScope.Var('spec_conf').IsSet", summary)
        self.assertNotIn("Country.IsLocalPlayer", summary)
        for key in ("fav1", "fav2", "fav3", "shun1", "shun2"):
            self.assertIn(f"Country.MakeScope.Var('spec_{key}').GetGoods", summary)
        self.assertEqual(summary.count('tooltip = "SPEC_JE_FAVOURED_GOOD_TT"'), 3)
        self.assertEqual(summary.count('tooltip = "SPEC_JE_SHUNNED_GOOD_TT"'), 2)

    def test_sector_chart_empty_scope_has_no_dynamic_script_value_lookup(self):
        import charts
        for field in ("SPEC_SECTOR_CHART_NAME", "SPEC_SECTOR_CHART_TT"):
            self.assertNotIn("ScriptValue(Concatenate", self.loc[field])
            self.assertIn("'SPEC_IB_EMPTY'", self.loc[field])
        self.assertNotIn("ScriptValue(Concatenate", charts.sector_chart())
        self.assertNotIn("spec_review_sector_", self.loc["SPEC_SECTOR_LINE"])

    def test_observer_shares_competition_rows_and_uses_the_viewed_pair(self):
        import rivals
        gui = rivals.block()
        self.assertEqual(gui.count('tooltip = "SPEC_RV_ROW_TT"'), 2)
        self.assertNotIn("spec_hide_obs_rv_", gui)
        for model in (rivals.OUTGOING, rivals.INCOMING):
            self.assertIn(f'datamodel = "[{model}]"', gui)
        self.assertIn("spec_rv_observed_in", rivals.INCOMING)
        for script in ("spec_rv_rope", "spec_rv_n_push_me", "spec_rv_n_push_it"):
            self.assertIn(f"GuiScope.SetRoot(Country.MakeScope).AddScope('spec_rival_me', "
                          f"GetMetaPlayer.GetPlayedOrObservedCountry.MakeScope).ScriptValue('{script}')", gui)
        strips = re.findall(r'using = set_level_bar_background.*?set_level_bar_item', gui, re.S)
        self.assertEqual(len(strips), 2)
        for strip in strips:
            self.assertIn('visible = "[Not(GetMetaPlayer.IsObserver)]"', strip)

    def test_sector_header_uses_vanilla_plate_without_unsupported_widget_margin(self):
        board = il.board({"CATEGORY": self.categories})
        headers = re.findall(r'widget = \{\s+size = \{ \d+ 38 \}\s+([^{}]*?)background = \{\s+texture = "gfx/interface/buttons/expand_button_bg.dds"', board, re.S)
        self.assertTrue(headers)
        for header in headers:
            self.assertNotIn("margin_top", header)

    def test_pressure_chip_uses_tenths_and_keeps_precision_on_hover(self):
        for total in (0, 0.01, -0.01, 0.049, -0.049, 0.05, -0.05, 0.09, -0.09, 1, -1):
            with self.subTest(total=total):
                country = {"spec_p4": total}
                key = evaluate(self.loc["SPEC_CHIP_4"][1:-1], country, {})
                if abs(total) < 0.05:
                    self.assertEqual(key, "SPEC_CHIP_ZERO")
                else:
                    self.assertIn("|+=1]", self.loc[key])
                self.assertIn("|+=2]", self.loc["SPEC_CHIP_4_TT"])

    def test_panic_explains_output_tax_and_relief(self):
        self.assertIn("SPEC_PANIC_ALL_EFFECTS", self.loc["SPEC_PANIC_TT"])
        self.assertIn("#N -10%#!", self.loc["SPEC_PANIC_ECONOMY"])
        self.assertIn("#N -15%#!", self.loc["SPEC_PANIC_ECONOMY"])
        self.assertIn("#N -5%#!", self.loc["SPEC_PANIC_ECONOMY_RESCUED"])
        self.assertIn("#N -7.5%#!", self.loc["SPEC_PANIC_ECONOMY_RESCUED"])
        self.assertEqual(self.loc["spec_panic_relief"], "Panic Relief")
        self.assertIn("$SPEC_RESCUE_EXCEPTIONS$", self.loc["SPEC_RESCUE_TT"])
        self.assertIn("Does not cut $spec_panic_relief$", self.loc["SPEC_RESCUE_EXCEPTIONS"])
        self.assertIn("SPEC_PANIC_RELIEF_NOTE", self.loc["SPEC_PANIC_TT_END"])

    def test_external_panel_navigation_closes_finance_and_disarms_slot(self):
        guard = mt.navigation_guard()
        trigger = re.search(r'trigger_when = "\[([^\n]+)\]"', guard)[1]
        # The native manager rejects the GUI widget name journal_entry_panel as a panel ID.
        self.assertNotIn("IsPanelOpen('journal_entry_panel')", trigger)
        for finance_mode in (None, "open", "journal_map"):
            for panel in (None, "market", "journal", "journal_entry"):
                panel_open = panel is not None
                with self.subTest(finance=finance_mode, panel=panel):
                    selected = {mt.FIN: finance_mode} if finance_mode else {}
                    expression = trigger.replace("InformationPanelBar.IsAnyPanelOpen", repr(panel_open))
                    expression = re.sub(r"InformationPanelBar.IsPanelOpen\('([^']+)'\)",
                                        lambda m: repr(m[1] == panel), expression)
                    keep_map = finance_mode == "journal_map" and panel == "journal_entry"
                    self.assertEqual(evaluate(expression, {}, selected), bool(finance_mode and panel and not keep_map))
        self.assertIn("Not(ObjectsEqual(JournalEntryPanel.GetJournalEntry.Self, GetPlayer.MakeScope.Var('spec_je').GetJournalEntry.Self))",
                      generate.journal_entry_gui())
        clears = re.findall(r'on_start = "\[GetVariableSystem.Clear\(\'([^\']+)\'\)\]"', guard)
        self.assertEqual(clears, [mt.FIN, mt.PICK])
        self.assertNotIn("InformationPanelBar.ClosePanel", guard)
        self.assertNotIn("visible =", guard)
        host = generate.information_panel_bar(self.constants)
        self.assertEqual(host.count("spec_finance_navigation_guard = {}"), 1)
        self.assertLess(host.index("spec_finance_navigation_guard = {}"), host.index("spec_finance_window = {}"))


if __name__ == "__main__":
    unittest.main()
