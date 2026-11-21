"""The 1.1 journal shortcut opens Speculation over the journal entry panel."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import journal
import market_tab


def open_actions(gui):
    buttons = re.findall(r'text = "SPEC_OPEN_TAB"\s+tooltip = "SPEC_OPEN_TAB_TT"\s+(.*?)\n\s*}',
                         gui, flags=re.S)
    if len(buttons) != 1:
        raise AssertionError(f"expected one Open Finance button, found {len(buttons)}")
    return re.findall(r'onclick = "\[([^\n]+)\]"', buttons[0])


def click_until_panel_is_destroyed(actions, variables):
    """ClosePanel ends the callback list because it owns the clicked widget."""
    variables = dict(variables)
    for action in actions:
        if action == "InformationPanelBar.ClosePanel":
            return variables, True
        clear = re.fullmatch(r"GetVariableSystem.Clear\('([^']+)'\)", action)
        set_value = re.fullmatch(r"GetVariableSystem.Set\('([^']+)', '([^']+)'\)", action)
        if clear:
            variables.pop(clear[1], None)
        elif set_value:
            variables[set_value[1]] = set_value[2]
        else:
            raise AssertionError(f"unmodelled button action: {action}")
    return variables, False


class FinanceOpenTests(unittest.TestCase):
    def assert_opens_over_journal(self, gui):
        actions = open_actions(gui)
        for initial in ({}, {market_tab.FIN: "open", market_tab.FIN_TAB: "world",
                             market_tab.PICK: "2", "unrelated_ui_choice": "keep"}):
            with self.subTest(initial=initial):
                variables, closed = click_until_panel_is_destroyed(actions, initial)
                self.assertFalse(closed, "the journal panel hosts Finance in 1.1")
                self.assertEqual(variables.get(market_tab.FIN), "open")
                self.assertEqual(variables.get(market_tab.FIN_TAB), "booms")
                self.assertNotIn(market_tab.PICK, variables)
                self.assertEqual(variables.get("unrelated_ui_choice"), initial.get("unrelated_ui_choice"))

    def test_journal_entry_link_opens_speculation_over_journal(self):
        self.assert_opens_over_journal(journal.widgets())

if __name__ == "__main__":
    unittest.main(verbosity=2)
