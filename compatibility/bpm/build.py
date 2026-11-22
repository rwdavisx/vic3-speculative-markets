"""Build the Speculative Markets / Better Politics Mod patch as a delta against a generated SM parent.

Generates the parent twice, without and with SPEC_BPM. The BPM build adds goods pools for BPM's political interest
groups (ig_stances.BPM_POOLS) and BPM's interest group panel with our Goods section (gui/BPM_interest_group_panel.gui:
it loads before our gui/interest_group_panel.gui, and the first definition of a GUI type wins). The patch holds the
files that differ, so it matches only the parent it was built against: rebuild for each parent release and for each
BPM update of its panel. Load it after BPM and after that Speculative Markets channel.
    py -3 -B compatibility/bpm/build.py --out runs/bpm/<new folder> [--parent beta/mod] [--bpm PATH] [--version X.Y.Z]
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from morgenroete_build import delta, hashes, verify_parent  # noqa: E402

DEFAULT_BPM = Path("G:/SteamLibrary/steamapps/workshop/content/529340/2932134122")
SKIP = ("gui/interest_group_panel.gui",)  # changes with the pools, but BPM's panel type wins over it


def build(parent, bpm, out, version):
    parent, bpm, out = (p.resolve() for p in (parent, bpm, out))
    if out.exists() or not out.is_relative_to(ROOT / "runs"):
        raise ValueError("Use a new output folder beneath runs/; previous candidates are immutable")
    original = hashes(parent)
    out.mkdir(parents=True)
    for name, with_bpm in (("baseline", False), ("extended", True)):
        env = {k: v for k, v in os.environ.items() if k not in ("SPEC_MOD_OUT", "SPEC_BPM", "SPEC_MORGENROETE", "SPEC_TECHRES")}
        env["SPEC_MOD_OUT"] = str(out / name)
        if with_bpm:
            env["SPEC_BPM"] = str(bpm)
        subprocess.run([sys.executable, "-B", str(ROOT / "tools/generate.py")], env=env, cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    base, extended = hashes(out / "baseline"), hashes(out / "extended")
    verify_parent(base, original)
    changes = [n for n in delta(base, extended) if not n.startswith(".metadata/") and n not in SKIP]
    patch = out / "mod"
    for n in changes:
        (patch / n).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out / "extended" / n, patch / n)
    meta = json.loads((parent / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))
    bpm_meta = json.loads((bpm / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))
    (patch / ".metadata").mkdir(parents=True)
    (patch / ".metadata/metadata.json").write_text(json.dumps({
        "name": "Speculative Markets - Better Politics Mod Compatibility", "id": "speculative_markets_bpm_compat",
        "version": version, "supported_game_version": "1.15.*",
        "short_description": f"Requires Better Politics Mod and Speculative Markets {meta['version']}. Load this patch last.",
        "tags": ["Utilities"], "relationships": [{"rel_type": "dependency", "id": "2932134122",
                                                  "display_name": "Better Politics Mod", "resource_type": "mod", "version": "*"}],
        "game_custom_data": {"multiplayer_synchronized": True}}, indent=2) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "status": "UNVERIFIED CANDIDATE - NOT PUBLISHED", "parent_id": meta["id"], "parent_version": meta["version"],
        "parent": str(parent), "bpm_version": bpm_meta["version"],
        "bpm_panel": hashes(bpm, ("gui/BPM_interest_group_panel.gui",)),
        "parent_hashes": original, "patch_hashes": hashes(patch)}, indent=2) + "\n", encoding="utf-8")
    print(f"Candidate: {patch}; {len(changes)} files. Parent {meta['id']} {meta['version']}, BPM {bpm_meta['version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=ROOT / "beta/mod")
    parser.add_argument("--bpm", type=Path, default=DEFAULT_BPM)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()
    build(args.parent, args.bpm, args.out, args.version)
