"""Regression for the reproduced 1.15.1 boom-toast access violation."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import notify
import exposure
import cycle


class NotificationScopeTests(unittest.TestCase):
    def test_toast_details_use_event_values_not_country_argument_scope(self):
        text = exposure.loc() + cycle.loc()
        self.assertNotIn("SCOPE.sGoods('spec_note_good').GetKey", text)
        for name in ('bank', 'over', 'ppl'):
            self.assertIn(f"SCOPE.GetValue('spec_note_{name}')", text)

    def test_each_good_resets_all_captured_values_before_optional_overrides(self):
        # A second good without a modifier must not inherit the first one's detail.
        for good in ('grain', 'steel'):
            text = notify.boom_note_scopes(good)
            for name, default in (('bank', 1), ('over', 1), ('ppl', 0)):
                reset = f'name = spec_note_{name} value = {default}'
                override = f'name = spec_note_{name} value = var:spec_note_{name}_{good}'
                self.assertLess(text.index(reset), text.index(override))
                self.assertIn(f'has_variable = spec_note_{name}_{good}', text)
            self.assertNotIn(f'var:spec_note_bank_{"steel" if good == "grain" else "grain"}', text)

    def test_every_generated_boom_post_has_capture_for_its_good(self):
        # Check the built beta, including all 49 goods and all three severities.
        text = (ROOT/'beta/mod/common/on_actions/spec_on_actions.txt').read_text(encoding='utf-8-sig')
        posts = list(re.finditer(r'post_notification = spec_boom_end_[123]_(?:bank_over|bank|over|plain)\b', text))
        self.assertEqual(len(posts), 49 * 3 * 4)
        for post in posts:
            before = text[:post.start()]
            saved = list(re.finditer(r'g:(\w+) = \{ save_scope_as = spec_note_good \}', before))[-1]
            normalize = lambda value: '\n'.join(line.strip() for line in value.splitlines()).strip()
            self.assertIn(normalize(notify.boom_note_scopes(saved.group(1))), normalize(before[saved.start():]))

    def test_numeric_details_never_pass_through_select_localization(self):
        text = exposure.loc() + cycle.loc()
        for key in ('SPEC_NOTE_BANKS_ON', 'SPEC_NOTE_OVER_ON'):
            self.assertNotRegex(text, rf"SelectLocalization\([^\n]*'{key}'")
        for severity in (1, 2, 3):
            for suffix in ('plain', 'bank', 'over', 'bank_over'):
                key = f'spec_boom_end_{severity}_{suffix}'
                desc = notify.NOTES[key][-1]
                self.assertEqual('$SPEC_NOTE_BANKS_ON$' in desc, 'bank' in suffix)
                self.assertEqual('$SPEC_NOTE_OVER_ON$' in desc, 'over' in suffix and cycle.ON)
                self.assertIn(f'post_notification = {key}', notify.boom_post(severity))


if __name__ == '__main__':
    unittest.main()
