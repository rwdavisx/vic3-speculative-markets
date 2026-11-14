"""Safety and false-positive checks for the actual engine-test harness."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hotfix_testbed as testbed


class TestbedTests(unittest.TestCase):
    def test_release_and_runs_root_never_reach_generator(self):
        for path in (ROOT / "mod", ROOT / "runs", ROOT / "runs/../mod", ROOT.parent / "outside"):
            with self.subTest(path=path), patch.object(testbed.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    testbed.prepare(path)
                run.assert_not_called()

    def test_unrecognized_existing_run_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="test_hotfix_") as directory:
            path = Path(directory)
            evidence = path / "existing.log"
            evidence.write_text("valuable run evidence", encoding="utf-8")
            with patch.object(testbed.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    testbed.prepare(path)
                run.assert_not_called()
            self.assertEqual(evidence.read_text(encoding="utf-8"), "valuable run evidence")

    def test_report_requires_every_assertion_and_completion(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="test_hotfix_") as directory:
            path = Path(directory)
            (path / testbed.MANIFEST).write_text(json.dumps({
                "kind": testbed.KIND, "expected_assertions": ["alpha", "beta"],
            }), encoding="utf-8")
            log = path / "debug.log"
            for text, expected_exit in [
                ("HOTFIX PASS alpha\nHOTFIX SUITE COMPLETE", 1),
                ("HOTFIX PASS alpha\nHOTFIX PASS beta", 1),
                ("HOTFIX PASS alpha\nHOTFIX PASS beta\nHOTFIX FAIL alpha\nHOTFIX SUITE COMPLETE", 1),
                ("HOTFIX PASS alpha\nHOTFIX PASS beta\nHOTFIX SUITE COMPLETE", 0),
            ]:
                with self.subTest(text=text):
                    log.write_text(text, encoding="utf-8")
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(testbed.report(path, [log]), expected_exit)

    def test_passing_assertions_do_not_mask_mod_or_fixture_runtime_errors(self):
        errors = [
            """[17:23:38][jomini_script_system.cpp:247]: Script system error!
  Error: has_variable trigger [ This scope doesn't support variables. Scope: 0.00 ]
  Script location: common/scripted_effects/spec_centre_effects.txt:2998
events/zz_hotfix_economy_events.txt:177
""",
            """[17:11:23][jomini_scriptlists.cpp:406]: Given position was bigger than the list, capping at list size at common/scripted_effects/spec_centre_effects.txt:2415
""",
            """[17:23:38][jomini_script_system.cpp:247]: Script system error!
  Error: has_variable trigger [ Wrong scope ]
  Script location: events/zz_hotfix_economy_events.txt:177
""",
        ]
        with tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="test_hotfix_") as directory:
            path = Path(directory)
            (path / testbed.MANIFEST).write_text(json.dumps({
                "kind": testbed.KIND, "expected_assertions": ["alpha"],
            }), encoding="utf-8")
            assertions, error_log = path / "assertions.log", path / "error.log"
            assertions.write_text("HOTFIX PASS alpha\nHOTFIX SUITE COMPLETE", encoding="utf-8")
            for error in errors:
                with self.subTest(error=error):
                    error_log.write_text(error, encoding="utf-8")
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(testbed.main([
                            "--out", str(path), "--report", str(assertions), "--error-log", str(error_log),
                        ]), 1)
                    result = json.loads(output.getvalue())
                    self.assertEqual(result["failed"], [])
                    self.assertEqual(result["blocking_error_count"], 1)

    def test_vanilla_errors_and_known_debug_warnings_do_not_fail_suite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs", prefix="test_hotfix_") as directory:
            path = Path(directory)
            (path / testbed.MANIFEST).write_text(json.dumps({
                "kind": testbed.KIND, "expected_assertions": ["alpha"],
            }), encoding="utf-8")
            assertions, error_log = path / "assertions.log", path / "error.log"
            assertions.write_text("HOTFIX PASS alpha\nHOTFIX SUITE COMPLETE", encoding="utf-8")
            error_log.write_text("""[17:23:43][jomini_script_system.cpp:247]: Script system error!
  Error: has_journal_entry trigger [ Wrong scope for trigger: state, expected country ]
  Script location: common/scripted_triggers/00_ai_triggers.txt:1304
events/paralegal_discrimination_events.txt:115
[17:22:48][jomini_effect.cpp:1140]: Variable 'spec_hotfix_done' is set but is never used.
[17:22:48][jomini_eventmanager.cpp:376]: Event spec_depression.90 is orphaned
""", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(testbed.report(path, [assertions], [error_log]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["blocking_error_count"], 0)
            self.assertEqual(result["error_categories"], {
                "basegame_script_errors": 1, "mod_variable_load_warnings": 1, "mod_orphaned_event_load_warnings": 1,
            })


if __name__ == "__main__":
    unittest.main()
