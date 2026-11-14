"""Release guards for a compatibility patch which replaces generated definitions."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from morgenroete_build import delta, verify_parent


class MorgenroeteBuildTests(unittest.TestCase):
    def test_rejects_stale_parent(self):
        with self.assertRaisesRegex(ValueError, 'does not match'):
            verify_parent({'gui/spec_market_tab.gui': 'new'}, {'gui/spec_market_tab.gui': 'old'})

    def test_only_metadata_may_differ_for_beta(self):
        verify_parent({'.metadata/metadata.json': 'stable', 'gui/a.gui': 'same'},
                      {'.metadata/metadata.json': 'beta', 'gui/a.gui': 'same'})
        with self.assertRaises(ValueError):
            verify_parent({'events/a.txt': 'same'}, {})

    def test_patch_contains_only_additions_and_changes(self):
        self.assertEqual(delta({'same': 'a', 'changed': 'b'},
                               {'same': 'a', 'changed': 'c', 'added': 'd'}),
                         {'changed': 'c', 'added': 'd'})

    def test_rejects_unrepresentable_removal(self):
        with self.assertRaisesRegex(ValueError, 'cannot remove'):
            delta({'old': 'a'}, {})
