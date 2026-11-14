"""Evidence gates matter: a broken test harness must never certify a release."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mechanics_testbed as testbed


class MechanicsHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "beta"
        for folder in (".metadata", "events", "common/on_actions", "common/script_values", "common/scripted_effects"):
            (self.source / folder).mkdir(parents=True)
        (self.source / ".metadata/metadata.json").write_text(json.dumps({"id": "speculative_markets_beta", "version": "test"}))
        self.original = self.source / "common/on_actions/production.txt"
        self.original.write_text("# begin\nset_variable = flag\n# end", encoding="utf-8-sig")
        fixture = self.root / "tests/mechanics"
        fixture.mkdir(parents=True)
        self.fixture = fixture / "sample.txt"
        self.fixture.write_text('debug_log = "HOTFIX PASS a"\ndebug_log = "HOTFIX FAIL a"\ndebug_log = "HOTFIX SUITE COMPLETE"')
        (fixture / "sample.helpers.json").write_text(json.dumps({"helper": {"path": "common/on_actions/production.txt", "start": "# begin", "end": "# end"}}))
        self.out = self.root / "runs/test"
        self.patcher = patch.object(testbed, "ROOT", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            testbed.prepare(self.source, self.out, "sample")

    def test_preserves_production_bytes_and_encodes_helpers(self):
        before = self.original.read_bytes()
        self.prepare()
        self.assertEqual(before, self.original.read_bytes())
        self.assertEqual(before, (self.out / "common/on_actions/production.txt").read_bytes())
        helper = (self.out / "common/scripted_effects/zz_spec_mechanics_helpers.txt").read_bytes()
        self.assertTrue(helper.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(helper.count(b"\xef\xbb\xbf"), 1)
        self.assertIn(b"set_variable = flag", helper)

    def test_refuses_stable_and_reused_evidence_directories(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.prepare()
        (self.source / ".metadata/metadata.json").write_text(json.dumps({"id": "speculative_markets", "version": "test"}))
        with self.assertRaisesRegex(ValueError, "beta distribution"):
            testbed.prepare(self.source, self.root / "runs/new", "sample")

    def test_refuses_malformed_assertion_even_alongside_valid_ones(self):
        with self.fixture.open("a") as target:
            target.write('\ndebug_log = "HOTFIX PASS_silently_missing"')
        with self.assertRaisesRegex(ValueError, "Malformed"):
            self.prepare()

    def test_report_fails_missing_failed_and_error_records(self):
        self.prepare()
        assertions = self.root / "assertions.log"
        errors = self.root / "error.log"
        errors.write_text("")
        cases = [('HOTFIX SUITE COMPLETE', 1),
                 ('HOTFIX PASS a', 1),
                 ('HOTFIX PASS a\nHOTFIX FAIL a\nHOTFIX SUITE COMPLETE', 1),
                 ('HOTFIX PASS a\nHOTFIX SUITE COMPLETE', 0)]
        for text, expected in cases:
            assertions.write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(testbed.report(self.out, [assertions], [errors]), expected)
        errors.write_text("[00:00:00][lexer.cpp:285]: File 'common/scripted_effects/zz_spec_mechanics_helpers.txt' should be in utf8-bom encoding")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(testbed.report(self.out, [assertions], [errors]), 1)

    def test_duplicate_mod_journal_is_a_blocking_error(self):
        error = self.root / "duplicate.log"
        error.write_text("[00:00:00][journal_entry_manager.cpp:372]: Great Britain already has a journal entry of type je_spec_markets")
        self.assertEqual(testbed.hotfix_testbed.check_error_logs([error])["blocking_error_count"], 1)


if __name__ == "__main__":
    unittest.main()
