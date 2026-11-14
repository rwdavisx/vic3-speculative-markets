import re
from pathlib import Path
# static checks on a built mod (braces, loc keys, concepts): reads SPEC_MOD_OUT, else mod/ (read only)
import os; MOD = Path(os.environ.get("SPEC_MOD_OUT") or Path(__file__).resolve().parent.parent / "mod").resolve(); GAME = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game")
def braces(s):
    d = 0; i = 0
    while i < len(s):
        c = s[i]
        if c == "#": i = s.find("\n", i); i = len(s) if i < 0 else i
        elif c == '"':
            i += 1
            while i < len(s):
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == '"':
                    break
                i += 1
            if i >= len(s):
                return -1  # fail malformed input instead of starting over forever
        elif c == "{": d += 1
        elif c == "}":
            d -= 1
            if d < 0: return d
        i += 1
    return d
bad = [p for p in list(MOD.rglob("*.txt")) + list(MOD.rglob("*.gui")) if braces(p.read_text(encoding="utf-8-sig"))]
print("files checked:", len(list(MOD.rglob("*.txt")) + list(MOD.rglob("*.gui"))), "unbalanced:", bad)
keyre = re.compile(r'^ ([A-Za-z0-9_.\-]+):\d* "(.*)"\s*$')
def keys(path):
    out = {}
    for l in path.read_text(encoding="utf-8-sig").splitlines():
        m = keyre.match(l)
        if m: out[m.group(1)] = m.group(2)
    return out
mod = keys(MOD / "localization/english/spec_markets_l_english.yml")
raw = (MOD / "localization/english/spec_markets_l_english.yml").read_text(encoding="utf-8-sig").splitlines()
badlines = [l[:60] for l in raw[1:] if l.strip() and not keyre.match(l)]
print("mod loc keys:", len(mod), "malformed lines:", badlines)
dup = [k for k in mod if sum(1 for l in raw if l.startswith(f" {k}:")) > 1]
print("duplicate keys:", dup)
brk = [k for k, v in mod.items() if v.count("[") != v.count("]") or v.count("#") and False]
print("unbalanced [] in values:", brk)
van = {}
for p in (GAME / "localization/english").rglob("*.yml"): van.update(keys(p))
defs = set(re.findall(r"^(concept_\w+) =", "\n".join(p.read_text(encoding="utf-8-sig") for p in (GAME / "common/game_concepts").glob("*.txt")), re.M))
mdefs = set(re.findall(r"^(concept_\w+) =", (MOD / "common/game_concepts/spec_concepts.txt").read_text(encoding="utf-8-sig"), re.M))
print("mod concept definitions:", sorted(mdefs), "clash with vanilla:", mdefs & defs)
text = "\n".join(mod.values()) + "\n" + "\n".join(p.read_text(encoding="utf-8-sig") for p in MOD.rglob("*.gui"))
linked = set(re.findall(r"\[(concept_\w+)\]", text)) | set(re.findall(r"Concept\('(concept_\w+)'", text))
print("concepts linked:", len(linked), "without definition:", sorted(linked - defs - mdefs))
dollar = set(re.findall(r"\$(concept_\w+|[A-Z_]+_GC_LINK)\$", text))
print("$keys$ used:", len(dollar), "missing loc:", sorted(k for k in dollar if k not in mod and k not in van))
print("mod concepts missing name/desc loc:", [c for c in mdefs if c not in mod or c + "_desc" not in mod])
spec = set(re.findall(r"\b(SPEC_[A-Z0-9_]+|spec_[a-z0-9_.]+(?:_tt|_desc|\.[tdfab]))\b", text)) | set(re.findall(r'"(SPEC_[A-Z0-9_]+)"', text))
spec_upper = {k for k in re.findall(r"\b(SPEC_[A-Z0-9_]+)\b", text)}
print("SPEC_ keys referenced:", len(spec_upper), "missing:", sorted(k for k in spec_upper if k not in mod))
print("unused mod concepts:", sorted(mdefs - linked))
# anything in this list fails the check (exit 1), so a build script or a person cannot miss it
problems = {"unbalanced braces": bad, "malformed loc lines": badlines, "duplicate keys": dup, "unbalanced [] in values": brk,
            "concepts clashing with vanilla": sorted(mdefs & defs), "concepts without definition": sorted(linked - defs - mdefs),
            "$keys$ without loc": sorted(k for k in dollar if k not in mod and k not in van),
            "concepts missing name/desc": [c for c in mdefs if c not in mod or c + "_desc" not in mod],
            "SPEC_ keys missing": sorted(k for k in spec_upper if k not in mod)}
# release guard: no debug script, and one version number in the generator, the metadata and the Workshop description
import json, sys
ROOT = Path(__file__).resolve().parent.parent
if MOD == ROOT / "mod":
    debug = ["spec_log_values.txt"] if (MOD / "common/script_values/spec_log_values.txt").exists() else []
    debug += ["test events"] if "spec_markets.90 =" in(MOD / "events/spec_markets_events.txt").read_text(encoding="utf-8-sig") else []
    problems["debug script in mod/ (built with --log)"] = debug
    built = (ROOT / "built_against.txt").read_text(encoding="utf-8").strip() if (ROOT / "built_against.txt").exists() else "never recorded"
    game = re.search(r'"rawVersion":\s*"([^"]+)"', (GAME.parent / "launcher/launcher-settings.json").read_text(encoding="utf-8")).group(1)
    supported = json.loads((MOD / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))["supported_game_version"]
    print("game:", game, "built against:", built, "supported:", supported)
    problems["game changed since the build (run generate.py again)"] = [f"{built} -> {game}"] if built != game else []
    problems["game version outside supported_game_version"] = [] if re.fullmatch(supported.replace(".", r"\.").replace("*", ".*"), game) else [f"{game} vs {supported}"]
    # a stray debug_log in a release writes to every player's log
    problems["debug_log lines in mod/"] = sorted({p.name for p in MOD.rglob("*.txt") if "debug_log" in p.read_text(encoding="utf-8-sig")})
# the feature switches (tools/tuning.json or SPEC_TUNING, as generate.py reads them) against what the build holds: a
# rebuild must give back the mod as built, so each switch's feature is in the mod exactly when the switch is on.
# (module, switch, a definition the build has only with it on); a switch its module no longer has is skipped
FEATURES = [("centres", "BRAKE", r"^spec_exch_limit = \{"), ("centres", "PLEDGE_ON", r"^spec_pledge_cost = \{"),
            ("centres", "EARN", r"^spec_earn_tc = \{"), ("centres", "LINKS", r"^spec_exch_mood = \{"), ("centres", "NAMES_ON", r"^spec_pursue_\w+ = \{"),
            ("centres", "RIVAL_ON", r"\bspec_rival_lock\b"), ("diplomacy", "RIVAL", r"var:spec_rival = root"),
            ("levers", "ISSUE_ON", r"^spec_issue_float = \{")]
script = "\n".join(p.read_text(encoding="utf-8-sig") for d in ("common", "events") for p in (MOD / d).rglob("*.txt"))
sys.dont_write_bytecode = True  # importing the tool modules must not leave tools/__pycache__ behind
sys.path.insert(0, str(ROOT / "tools"))
mismatch = []
for module, switch, mark in FEATURES:
    try:
        on = getattr(__import__(module), switch, None)
    except Exception as e:  # a module that fails to load cannot vouch for the build
        mismatch.append(f"{module} failed to load: {e}")
        continue
    if on is not None and bool(on) != bool(re.search(mark, script, re.M)):
        mismatch.append(f"{module}.{switch} is {'on' if on else 'off'}, the build {'lacks' if on else 'has'} it")
print("feature switches against the build:", mismatch or "match")
problems["build does not match the feature switches (rebuild, or fix the switch defaults)"] = mismatch
# a notification type nothing posts (directly, or as a TYPE parameter of a posting effect) only adds settings and loc
messages = "\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD / "common/messages").glob("*.txt"))
posting = "\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD / "common").rglob("*.txt") if p.parent.name != "messages") + "\n" + \
    "\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD / "events").rglob("*.txt"))
problems["notifications never posted"] = [n for n in re.findall(r"^(\w+) = \{", messages, re.M)
                                          # Legacy IDs remain readable in saves; 1.0.3 posts explicit detail variants.
                                          if n not in {f"spec_boom_end_{s}" for s in (1, 2, 3)}
                                          and not re.search(rf"\b(post_notification|TYPE) = {n}\b", posting)]
versions = {"generate.py": re.search(r'^VERSION = "([^"]+)"', (ROOT / "tools/generate.py").read_text(encoding="utf-8"), re.M).group(1),
            "description.bbcode": re.search(r"^\[b\](\d+\.\d+\.\d+)\[/b\]", (ROOT / "workshop/description.bbcode").read_text(encoding="utf-8"), re.M).group(1)}
metadata = MOD / ".metadata/metadata.json"
if metadata.exists():
    versions["metadata.json"] = json.loads(metadata.read_text(encoding="utf-8-sig"))["version"]
elif MOD == ROOT / "mod":
    problems["release metadata missing"] = [str(metadata)]
problems["version mismatch"] = [versions] if len(set(versions.values())) > 1 else []
failed = {k: v for k, v in problems.items() if v}
print("versions:", versions)
print("FAILED: " + "; ".join(f"{k}: {v}" for k, v in failed.items()) if failed else "OK")
sys.exit(1 if failed else 0)
