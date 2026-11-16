"""Check the separate CMF patch against the actual installed parent GUIs.

Run: py -3 -B compatibility/cmf/test_build.py
Set CMF_MOD_ROOT to use a different CMF installation. Builds go only into a
temporary directory; both parents are hashed to detect accidental mutations.
These checks model GUI paths and handlers, not the game's rendering engine.
"""
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = ROOT / "mod"
CMF = Path(os.environ.get("CMF_MOD_ROOT",
    "G:/SteamLibrary/steamapps/workshop/content/529340/3385002128"))
SPEC_GUI = Path("gui/information_panel_bar.gui")
CMF_GUI = Path("gui/com_gui_sidebar.gui")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def type_block(text, name):
    """Extract a complete actual GUI type, respecting comments and strings."""
    matches = list(re.finditer(r"\btype\s+" + re.escape(name) + r"\s*=\s*\w+\s*\{", text))
    if len(matches) != 1:
        raise AssertionError(f"expected one {name} definition, found {len(matches)}")
    start = matches[0].start()
    opened = text.index("{", start)
    depth, quoted, comment, escaped = 0, False, False, False
    for index in range(opened, len(text)):
        char = text[index]
        if comment:
            comment = char != "\n"
        elif quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError(f"unclosed {name} definition")


def normalized(text):
    return "\n".join(line.strip() for line in text.strip().splitlines())


def handlers(text):
    """Consecutive onclick lines are one actual button's action sequence."""
    line = r'[ \t]*onclick\s*=\s*"\[([^\n]+)\]"[ \t]*'
    groups = re.finditer(r"(?m)^" + line + r"(?:\n" + line + r")*", text)
    return [re.findall(line, match[0]) for match in groups]


def run_actions(actions, state):
    """Apply emitted handlers to a tiny UI state; reject unmodelled commands."""
    state = dict(state)
    for action in actions:
        clear = re.fullmatch(r"GetVariableSystem.Clear\('([^']+)'\)", action)
        toggle = re.fullmatch(r"GetVariableSystem.Toggle\('([^']+)'\)", action)
        if clear:
            state.pop(clear[1], None)
        elif toggle:
            if toggle[1] in state:
                state.pop(toggle[1])
            else:
                state[toggle[1]] = True
        elif action == "InformationPanelBar.ClosePanel":
            state["native"] = False
        elif action == "MapListPanelManager.CloseCurrentPanel":
            state["ledger"] = False
        elif action == "GetVariableSystem.Set('com_open_window', Scope.GetFlagName)":
            state["com_open_window"] = "selected_cmf_window"
        elif action == "ScriptedGui.Execute(GuiScope.SetRoot(Country.MakeScope).End)":
            state["at_execute"] = dict(state)
        else:
            raise AssertionError(f"unmodelled click action: {action}")
    return state


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for path in (SPEC / SPEC_GUI, CMF / CMF_GUI):
            if not path.is_file():
                raise unittest.SkipTest(f"parent GUI unavailable: {path}")
        module = importlib.util.spec_from_file_location("cmf_compat_builder", HERE / "build.py")
        cls.builder = importlib.util.module_from_spec(module)
        module.loader.exec_module(cls.builder)
        cls.spec = read(SPEC / SPEC_GUI)
        cls.cmf = read(CMF / CMF_GUI)
        cls.before = {"spec": hashes(SPEC), "cmf": hashes(CMF)}
        cls.temp = tempfile.TemporaryDirectory(prefix="spec-cmf-regression-")
        cls.out = Path(cls.temp.name) / "patch"
        cls.manifest = cls.builder.build(SPEC, CMF, cls.out)
        cls.merged = read(cls.out / CMF_GUI)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_both_parent_orders_have_exactly_one_sidebar_definition(self):
        for parents in ((SPEC, CMF), (CMF, SPEC)):
            with self.subTest(parents=tuple(str(p) for p in parents)):
                effective = {}
                for root in (*parents, self.out):
                    effective.update({path.relative_to(root).as_posix(): read(path)
                                      for path in (root / "gui").rglob("*.gui")})
                definitions = [(path, match.start()) for path, text in effective.items()
                               for match in re.finditer(r"\btype\s+information_panel_bar\s*=", text)]
                self.assertEqual([path for path, _ in definitions], [CMF_GUI.as_posix()])
                self.assertNotRegex(effective[SPEC_GUI.as_posix()], r"\btype\s+\w+\s*=")

    def test_preserves_parents_layout_and_extension_types(self):
        source_positions = re.findall(r"(?m)^@(\w+)\s*=\s*([^\n]+)", self.spec)
        merged_positions = re.findall(r"(?m)^@(\w+)\s*=\s*([^\n]+)", self.merged)
        self.assertEqual(merged_positions, source_positions)
        self.assertEqual(normalized(type_block(self.merged, "custom_sidebar")),
                         normalized(type_block(self.cmf, "custom_sidebar")))
        for name in re.findall(r"\btype\s+(\w+)\s*=", self.spec):
            if name != "information_panel_bar":
                with self.subTest(helper=name):
                    self.assertEqual(normalized(type_block(self.merged, name)),
                                     normalized(type_block(self.spec, name)))
        self.assertEqual(len(re.findall(r"(?m)^\s*custom_sidebar\s*=\s*\{\s*\}", self.merged)), 1)
        self.assertEqual(self.merged.count("spec_finance_window = {}"), 1)
        self.assertEqual(self.merged.count("spec_finance_navigation_guard = {}"), 1)
        original_button = normalized(type_block(self.cmf, "com_sidebar_button"))
        patched_button = type_block(self.merged, "com_sidebar_button")
        patched_button = re.sub(r"(?m)^[ \t]*onclick = \"\[GetVariableSystem.Clear\('(spec_finance|spec_pick_slot)'\)\]\"\n", "", patched_button)
        self.assertEqual(normalized(patched_button), original_button)

    def test_pure_merge_matches_written_sidebar(self):
        self.assertEqual(self.builder.merge_gui(self.spec, self.cmf), self.merged)

    def test_metadata_uses_game_supported_cmf_dependency_only(self):
        metadata = json.loads(read(self.out / ".metadata/metadata.json"))
        relationships = metadata["relationships"]
        cmf_id = "com.github.Victoria-3-Modding-Co-op.Community-Mod-Framework"
        required = [relation for relation in relationships if relation["rel_type"] == "dependency"]
        self.assertEqual([relation["id"] for relation in required], [cmf_id],
                         "stable and beta are alternatives, never simultaneous dependencies")
        self.assertEqual(relationships, required,
                         "the game rejects launcher-only load_after/incompatible_with relationships")
        self.assertEqual(required[0]["version"], "*", "any CMF version, so CMF bugfixes don't mark the patch outdated")
        self.assertTrue(all(relation["resource_type"] == "mod" for relation in relationships))

    def test_finance_buttons_close_cmf_and_ledger_then_toggle_finance(self):
        clicks = [actions for actions in handlers(type_block(self.merged, "information_panel_bar"))
                  if "GetVariableSystem.Toggle('spec_finance')" in actions]
        self.assertEqual(len(clicks), 2, "both icon and expanded label must work")
        for index, actions in enumerate(clicks):
            for already_open in (False, True):
                with self.subTest(button=index, already_open=already_open):
                    initial = {"com_open_window": "old_cmf_window", "spec_pick_slot": 2,
                               "native": True, "ledger": True}
                    if already_open:
                        initial["spec_finance"] = True
                    final = run_actions(actions, initial)
                    self.assertEqual("spec_finance" in final, not already_open)
                    self.assertNotIn("com_open_window", final)
                    self.assertNotIn("spec_pick_slot", final)
                    self.assertFalse(final["native"])
                    self.assertFalse(final["ledger"])
                    self.assertLess(actions.index("GetVariableSystem.Clear('com_open_window')"),
                                    actions.index("GetVariableSystem.Toggle('spec_finance')"))

    def test_cmf_buttons_yield_finance_before_executing_the_selected_window(self):
        clicks = handlers(type_block(self.merged, "com_sidebar_button"))
        self.assertEqual(len(clicks), 2)
        for index, actions in enumerate(clicks):
            with self.subTest(button=index):
                final = run_actions(actions, {"spec_finance": True, "spec_pick_slot": 2,
                                              "com_open_window": "old_cmf_window"})
                self.assertNotIn("spec_finance", final["at_execute"])
                self.assertNotIn("spec_pick_slot", final["at_execute"])
                self.assertEqual(final["at_execute"]["com_open_window"], "selected_cmf_window")
                self.assertEqual(final["com_open_window"], "selected_cmf_window")

    def test_navigation_watcher_yields_finance_without_closing_cmf(self):
        guard = type_block(self.merged, "spec_cmf_navigation_guard")
        expressions = re.findall(r'trigger_when\s*=\s*"\[([^\n]+)\]"', guard)
        self.assertEqual(len(expressions), 1)
        starts = re.findall(r'on_start\s*=\s*"\[([^\n]+)\]"', guard)
        self.assertNotIn("GetVariableSystem.Clear('com_open_window')", guard)
        self.assertNotRegex(guard, r"\bvisible\s*=")
        self.assertEqual(self.merged.count("spec_cmf_navigation_guard = {}"), 1)
        for finance, cmf, ledger in itertools.product((False, True), repeat=3):
            with self.subTest(finance=finance, cmf=cmf, ledger=ledger):
                state = {"spec_pick_slot": 2, "ledger": ledger}
                if finance:
                    state["spec_finance"] = True
                if cmf:
                    state["com_open_window"] = "selected_cmf_window"
                expression = re.sub(r"GetVariableSystem.Exists\('([^']+)'\)",
                                    lambda m: str(m[1] in state), expressions[0])
                expression = expression.replace("MapListPanelManager.IsVisible", str(ledger))
                active = eval(expression, {"__builtins__": {}},
                              {"And": lambda a, b: a and b, "Or": lambda a, b: a or b})
                self.assertEqual(active, finance and (cmf or ledger))
                final = run_actions(starts, state) if active else state
                if active:
                    self.assertNotIn("spec_finance", final)
                    self.assertNotIn("spec_pick_slot", final)
                else:
                    self.assertEqual(final, state)
                self.assertEqual(final.get("com_open_window"), state.get("com_open_window"))
                self.assertEqual(final["ledger"], ledger)

    def test_build_never_changes_either_parent(self):
        self.assertEqual(hashes(SPEC), self.before["spec"])
        self.assertEqual(hashes(CMF), self.before["cmf"])

    def test_missing_parent_anchors_fail_before_any_output(self):
        mutations = (
            ("spec", "spec_finance_window = {}", "spec_finance_window_removed = {}"),
            ("spec", "GetVariableSystem.Toggle('spec_finance')", "GetVariableSystem.Toggle('removed_finance')"),
            ("cmf", "type custom_sidebar =", "type missing_custom_sidebar ="),
            ("cmf", "type com_sidebar_button =", "type missing_com_sidebar_button ="),
            ("cmf", "GetVariableSystem.Set('com_open_window', Scope.GetFlagName)",
             "GetVariableSystem.Set('removed_window', Scope.GetFlagName)"),
        )
        for index, (parent, old, new) in enumerate(mutations):
            with self.subTest(anchor=old):
                base = Path(self.temp.name) / f"invalid-{index}"
                spec, cmf, out = base / "spec", base / "cmf", base / "patch"
                for directory, relative, text in ((spec, SPEC_GUI, self.spec), (cmf, CMF_GUI, self.cmf)):
                    target = directory / relative
                    target.parent.mkdir(parents=True)
                    if directory.name == parent:
                        self.assertIn(old, text)
                        text = text.replace(old, new, 1)
                    target.write_text(text, encoding="utf-8-sig")
                    metadata = directory / ".metadata/metadata.json"
                    metadata.parent.mkdir(parents=True)
                    metadata.write_bytes(((SPEC if directory == spec else CMF) /
                                          ".metadata/metadata.json").read_bytes())
                with self.assertRaises(ValueError):
                    self.builder.build(spec, cmf, out)
                self.assertFalse(out.exists(), "invalid parent created output before validation")
                self.assertFalse((base / "build_manifest.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
