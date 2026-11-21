"""Build the separate Speculative Markets / Community Mod Framework GUI patch.

The parent mods are read only. Run from any working directory:
    py -3 -B compatibility/cmf/build.py [--spec PATH] [--cmf PATH] [--out PATH]

This patch must load after both parents. It replaces their two sidebar files with
one merged definition, so duplicate-type precedence is not part of the contract.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "mod"
DEFAULT_CMF = Path("G:/SteamLibrary/steamapps/workshop/content/529340/3385002128")
DEFAULT_OUT = Path(__file__).resolve().parent / "mod"
VERSION = "1.0.4"
SPEC_ALERT = "gui/topfrontend.gui"
CMF_ALERT = "gui/00_com_topfrontend.gui"
SPEC_JOURNAL = "gui/journal_entry.gui"
CMF_JOURNAL = "gui/com_gui_journal_entry.gui"
VANILLA_ALERT = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game") / SPEC_ALERT
SPEC_ID = "speculative_markets"
CMF_ID = "com.github.Victoria-3-Modding-Co-op.Community-Mod-Framework"
SPEC_GUI = "gui/information_panel_bar.gui"
CMF_GUI = "gui/com_gui_sidebar.gui"
METADATA = ".metadata/metadata.json"


def _block_end(text, start):
    """Find a GUI block's closing brace, respecting comments and quoted strings."""
    if start >= len(text) or text[start] != "{":
        raise ValueError("Expected an opening brace")
    depth, quote, comment = 0, False, False
    i = start
    while i < len(text):
        char = text[i]
        if comment:
            comment = char != "\n"
        elif quote:
            if char == "\\":
                i += 1
            elif char == '"':
                quote = False
        elif char == "#":
            comment = True
        elif char == '"':
            quote = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("Unclosed GUI block or quoted string")


def _type(text, name, base):
    pattern = rf"(?m)^[ \t]*type\s+{re.escape(name)}\s*=\s*{re.escape(base)}\s*\{{"
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} = {base} type; found {len(matches)}")
    match = matches[0]
    return text[match.start():_block_end(text, match.end() - 1) + 1]


def _replace(text, pattern, replacement, expected, label):
    text, count = re.subn(pattern, replacement, text, flags=re.M)
    if count != expected:
        raise ValueError(f"Unsupported parent layout: {label}: expected {expected}, found {count}")
    return text


def _validate_gui(text):
    """Check all top-level blocks before any output files are touched."""
    i = 0
    while i < len(text):
        if text[i] == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end + 1
        elif text[i] == "{":
            i = _block_end(text, i) + 1
        elif text[i] == "}":
            raise ValueError("Unmatched closing GUI brace")
        else:
            i += 1


def merge_gui(spec_text, cmf_text):
    """Merge known parent layouts or fail without producing a partial patch."""
    spec_text = spec_text.lstrip("\ufeff").replace("\r\n", "\n")
    cmf_text = cmf_text.lstrip("\ufeff").replace("\r\n", "\n")
    _validate_gui(spec_text)
    _validate_gui(cmf_text)
    _type(spec_text, "information_panel_bar", "widget")
    _type(spec_text, "power_bloc_icon_button_widget", "widget")
    _type(cmf_text, "information_panel_bar", "widget")
    custom = _type(cmf_text, "custom_sidebar", "flowcontainer")
    buttons = _type(cmf_text, "com_sidebar_button", "container")

    for pattern, expected, label in (
        (r"(?m)^\s*@spec_finance_position\s*=\s*300\s*$", 1, "Finance position"),
        (r"(?m)^\s*spec_finance_window\s*=\s*\{\s*\}", 1, "Finance host"),
        (r"(?m)^\s*custom_sidebar\s*=\s*\{\s*\}", 0, "unmerged sidebar"),
    ):
        if len(re.findall(pattern, spec_text)) != expected:
            raise ValueError(f"Unsupported Speculative Markets layout: {label}")

    # Keep SM's complete namespace and helpers, and its one set of shifted button
    # positions. CMF's extension inherits those same positions below the ledger.
    merged = _replace(
        spec_text,
        r'^(?P<indent>[ \t]*)name = "ingame_sidebar_buttons_container"[^\n]*\n',
        lambda m: m[0] + m["indent"] + "custom_sidebar = {}\n",
        1, "sidebar container",
    )
    # 1.1: the Finance button cycles its tabs (spec_finance_next) instead of toggling; CMF's closes go after
    # the native ClosePanel that starts both of its click paths, and the rest of SM's path stays as it is
    finance_click = (
        r"^(?P<indent>[ \t]*)onclick = \"\[InformationPanelBar\.ClosePanel\]\"\n"
        r"(?=(?P=indent)onclick = \"\[GetVariableSystem\.Clear\('spec_finance_next'\)\]\")"
    )

    def finance_actions(match):
        indent = match["indent"]
        actions = (
            "InformationPanelBar.ClosePanel",
            "MapListPanelManager.CloseCurrentPanel",
            "GetVariableSystem.Clear('com_open_window')",
        )
        return "".join(f'{indent}onclick = "[{action}]"\n' for action in actions)

    merged = _replace(merged, finance_click, finance_actions, 4, "Finance click paths")
    cmf_click = r"^(?P<indent>[ \t]*)onclick = \"\[GetVariableSystem\.Set\('com_open_window', Scope\.GetFlagName\)\]\""
    buttons = _replace(
        buttons, cmf_click,
        lambda m: (f'{m["indent"]}onclick = "[GetVariableSystem.Clear(\'spec_finance\')]"\n'
                   f'{m["indent"]}onclick = "[GetVariableSystem.Clear(\'spec_pick_slot\')]"\n' + m[0]),
        2, "CMF click paths",
    )
    # The shared background marker exists in both SM 1.0.0 and 1.0.1. Do not
    # depend on 1.0.1's separate native-panel watcher being present.
    merged = _replace(
        merged, r"^(?P<indent>[ \t]*)### BACKGROUND FOR LABEL BUTTONS\n",
        lambda m: f'{m["indent"]}spec_cmf_navigation_guard = {{}}\n' + m[0],
        1, "navigation guard host",
    )
    guard = """    type spec_cmf_navigation_guard = widget {
        name = "spec_cmf_navigation_guard"
        size = { 1 1 }
        alwaystransparent = yes
        state = {
            name = spec_cmf_yield_to_navigation
            trigger_when = "[And(GetVariableSystem.Exists('spec_finance'), Or(GetVariableSystem.Exists('com_open_window'), MapListPanelManager.IsVisible))]"
            on_start = "[GetVariableSystem.Clear('spec_finance')]"
            on_start = "[GetVariableSystem.Clear('spec_pick_slot')]"
            duration = 0
        }
    }
"""
    merged = (
        "# Speculative Markets + Community Mod Framework compatibility patch.\n"
        "# Sidebar base: Speculative Markets by the mod author.\n"
        "# custom_sidebar and com_sidebar_button: Victoria 3 Modding Co-op CMF.\n"
        "# https://github.com/Victoria-3-Modding-Co-op/Community-Mod-Framework\n"
        "# Preserve CMF behavior; only cross-window close actions are added.\n\n"
        + merged.rstrip() + "\n\ntypes spec_cmf_sidebar_extensions {\n"
        + custom + "\n\n" + buttons + "\n\n" + guard + "}\n"
    )
    _validate_gui(merged)
    for name in ("information_panel_bar", "power_bloc_icon_button_widget", "custom_sidebar",
                 "com_sidebar_button", "spec_cmf_navigation_guard"):
        if len(re.findall(rf"\btype\s+{name}\s*=", merged)) != 1:
            raise ValueError(f"Merged GUI does not uniquely define {name}")
    return merged


def merge_alert_gui(spec, cmf, vanilla):
    """Preserve the SM Finance branch and the upstream CMF action on regular alerts."""
    action = 'onclick = "[PopupManager.OpenAlert(Alert.AccessSelf)]"'
    dispatch = "onclick = \"[GetVariableSystem.Set('com_alert_action', Alert.GetAction)]\""
    hide = 'onrightclick = "[Alert.MarkAsHidden]"'
    tooltip = 'tooltip = "[Alert.GetToolTip]"'
    parent = _type(cmf, "topfrontend", "widget")
    additions = ((action, dispatch), (hide, tooltip))

    def after(text, anchor, line, count):
        return _replace(text, r"^(?P<t>[ \t]*)" + re.escape(anchor) + "$",
                        lambda m: m[0] + "\n" + m["t"] + line, count, anchor)

    expected = _type(vanilla, "topfrontend", "widget")
    for anchor, line in additions:
        expected = after(expected, anchor, line, 1)
    if parent != expected:
        raise ValueError("Upstream CMF alert type changed; review the merge")
    merged = after(after(spec, action, dispatch, 1), hide, tooltip, 2)
    close = 'onclick = "[InformationPanelBar.ClosePanel]"'
    merged = after(merged, close, '''onclick = "[GetVariableSystem.Clear('com_open_window')]"''', 1)
    merged = after(merged, close, 'onclick = "[MapListPanelManager.CloseCurrentPanel]"', 1)
    _validate_gui(merged)
    return merged, cmf.replace(parent, "# Merged topfrontend is supplied in topfrontend.gui.")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def merge_journal_guard(spec, cmf):
    marker = "name = spec_finance_yield_to_other_entry"
    if marker not in spec:
        return None
    anchor = 'datacontext = "[JournalEntryPanel.AccessJournalEntryType]"'
    match = re.search(r'\n\s*state = \{\s*' + re.escape(marker), spec)
    if not match or spec.count(marker) != 1 or cmf.count(anchor) != 1 or marker in cmf:
        raise ValueError("Journal panel guard or CMF journal context changed; review the merge")
    end = _block_end(spec, spec.index("{", match.start())) + 1
    merged = cmf.replace(anchor, anchor + spec[match.start():end])
    _validate_gui(merged)
    return merged


def build(spec=DEFAULT_SPEC, cmf=DEFAULT_CMF, out=DEFAULT_OUT):
    spec, cmf, out = (Path(p).expanduser().resolve() for p in (spec, cmf, out))
    for parent in (spec, cmf):
        if out == parent or out.is_relative_to(parent) or parent.is_relative_to(out):
            raise ValueError(f"Output must not overlap a parent mod: {out}")
    source_files = {}
    parents = {}
    for name, folder, expected, gui in (("speculative_markets", spec, {SPEC_ID, "speculative_markets_beta"}, SPEC_GUI),
                                        ("community_mod_framework", cmf, {CMF_ID}, CMF_GUI)):
        metadata = json.loads((folder / METADATA).read_text(encoding="utf-8-sig"))
        if metadata.get("id") not in expected:
            raise ValueError(f"Wrong {name} mod id at {folder}: {metadata.get('id')!r}")
        data = (folder / gui).read_bytes()
        source_files[name] = data.decode("utf-8-sig")
        parents[name] = {"path": str(folder), "metadata": metadata,
                         "files": {gui: _sha(data), METADATA: _sha((folder / METADATA).read_bytes())}}
    merged = merge_gui(source_files["speculative_markets"], source_files["community_mod_framework"])
    spec_version = parents["speculative_markets"]["metadata"]["version"]
    cmf_version = parents["community_mod_framework"]["metadata"]["version"]
    metadata = {
        "name": "Speculative Markets - Community Mod Framework Compatibility",
        "id": "speculative_markets_cmf_compat",
        "version": VERSION,
        "supported_game_version": "1.15.*",
        "short_description": "Requires CMF and either Speculative Markets or its Beta. Enable only one SM channel; load this patch last.",
        "tags": ["Utilities"],
        "relationships": [
            {"rel_type": "dependency", "id": CMF_ID, "display_name": "Community Mod Framework",
             # any CMF version: pinning the exact one marked the patch outdated on every CMF bugfix
             "resource_type": "mod", "version": "*"},
            # The 1.15.1 game parser accepts dependency only, even though the
            # launcher supports more relationship types. Exactly one SM
            # channel and patch-last ordering are explicit player instructions.
        ],
        "game_custom_data": {"multiplayer_synchronized": True},
    }
    files = {
        CMF_GUI: merged.encode("utf-8-sig"),
        SPEC_GUI: ("# The complete merged sidebar is in com_gui_sidebar.gui.\n"
                   "# Mask the parent file so only one information_panel_bar type is loaded.\n").encode("utf-8-sig"),
        METADATA: (json.dumps(metadata, indent=2) + "\n").encode("utf-8"),
    }
    if (spec / SPEC_ALERT).exists():
        alerts = []
        for name, folder, rel in (("speculative_markets", spec, SPEC_ALERT),
                                  ("community_mod_framework", cmf, CMF_ALERT)):
            data = (folder / rel).read_bytes()
            parents[name]["files"][rel] = _sha(data)
            alerts.append(data.decode("utf-8-sig").replace("\r\n", "\n"))
        merged_alert, mask = merge_alert_gui(*alerts, VANILLA_ALERT.read_text(encoding="utf-8-sig"))
        files[SPEC_ALERT] = merged_alert.encode("utf-8-sig")
        files[CMF_ALERT] = mask.encode("utf-8-sig")
    # CMF supplies its own journal_entry_panel type. Preserve its extensions
    # when applying the Finance guard to that version of the native window.
    if (spec / SPEC_JOURNAL).exists():
        source = (spec / SPEC_JOURNAL).read_bytes()
        if b"name = spec_finance_yield_to_other_entry" in source:
            framework = (cmf / CMF_JOURNAL).read_bytes()
            merged_journal = merge_journal_guard(source.decode("utf-8-sig"), framework.decode("utf-8-sig").replace("\r\n", "\n"))
            parents["speculative_markets"]["files"][SPEC_JOURNAL] = _sha(source)
            parents["community_mod_framework"]["files"][CMF_JOURNAL] = _sha(framework)
            files[CMF_JOURNAL] = merged_journal.encode("utf-8-sig")
    # Validate every layout before touching the destination; never remove an
    # unexpected file or follow a redirected output path into a parent mod.
    for rel in files:
        resolved = (out / rel).resolve()
        if not resolved.is_relative_to(out):
            raise ValueError(f"Redirected output path: {resolved}")
    manifest = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(), "builder_version": VERSION,
        "output": str(out), "parents": parents,
        "output_files": {rel: _sha(data) for rel, data in files.items()},
        "load_order": [SPEC_ID, CMF_ID, metadata["id"]],
        "notes": ["The two parents may be swapped; this patch must follow both.",
                  f"Built from Speculative Markets {spec_version}; enable either stable or the matching beta, never both.",
                  "Only CMF is a mandatory metadata dependency; the required SM channel choice is documented for players.",
                  "Set load order manually: the 1.15.1 game rejects launcher-only load_after metadata.",
                  "No parent files are modified. Runtime compatibility is validated separately.",
                  "CMF sidebar attribution is preserved in the merged GUI."],
    }
    for rel, data in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
    (out.parent / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--cmf", type=Path, default=DEFAULT_CMF)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        manifest = build(args.spec, args.cmf, args.out)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Compatibility build failed: {error}\n")
    print(f"Built {len(manifest['output_files'])} compatibility files in {manifest['output']}")
    print(f"Parent versions: SM {manifest['parents']['speculative_markets']['metadata']['version']}, "
          f"CMF {manifest['parents']['community_mod_framework']['metadata']['version']}")


if __name__ == "__main__":
    main()
