"""Regression checks for build failures found during the 1.0 hotfix audit.

Run: py -3 -B -m unittest discover -s tests -p "test_*.py"
Gameplay regressions run in the real engine via tools/hotfix_testbed.py.
"""
import ast
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate

# check.py is a command, so load only its real scanner without executing the CLI.
checker_tree = ast.parse((ROOT / "tools/check.py").read_text(encoding="utf-8"))
scanner = next(n for n in checker_tree.body if isinstance(n, ast.FunctionDef) and n.name == "braces")
namespace = {}
exec(compile(ast.Module(body=[scanner], type_ignores=[]), "tools/check.py", "exec"), namespace)
braces = namespace["braces"]


class ScriptScannerTests(unittest.TestCase):
    def test_comments_and_escaped_quotes_do_not_change_depth(self):
        source = 'value = { text = "a \\"quoted } string" # } ignored\n child = {} } trailing'
        self.assertEqual(braces(source), 0)
        self.assertEqual(generate.block_end(source, source.index("{")), source.index(" trailing") - 1)

    def test_unterminated_string_fails(self):
        self.assertNotEqual(braces('value = { text = "never closed'), 0)
        with self.assertRaisesRegex(ValueError, "unterminated"):
            generate.block_end('{ text = "never closed', 0)

    def test_unbalanced_braces_fail(self):
        for source in ("a = {", "}", "}{", "a = { # end"):
            with self.subTest(source=source):
                self.assertNotEqual(braces(source), 0)

    def test_debug_build_cannot_overwrite_release_through_path_alias(self):
        alias = ROOT / "mod" / ".." / "mod"
        with patch.object(generate, "MOD", alias), patch.dict(os.environ, {"SPEC_MOD_OUT": str(alias)}):
            # Fail before any mutation if the destination guard ever regresses.
            with patch.object(generate.icons, "build", side_effect=AssertionError("release mutation")) as writer:
                with self.assertRaisesRegex(SystemExit, "outside mod"):
                    generate.main(log=True)
                writer.assert_not_called()

    def test_stale_outputs_removed_even_with_future_timestamp(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target / "events").mkdir()
            stale = target / "events/old_debug_events.txt"
            stale.write_text("obsolete")
            os.utime(stale, (4102444800, 4102444800))
            metadata = target / "metadata.txt"
            metadata.write_text("outside generated folders")
            with patch.object(generate, "MOD", target), patch.object(generate, "WRITTEN", set()):
                generate.write("events/current.txt", "current = {}")
                self.assertEqual(generate.remove_stale(), [stale])
                self.assertTrue((target / "events/current.txt").exists())
                self.assertTrue(metadata.exists())


if __name__ == "__main__":
    unittest.main()
