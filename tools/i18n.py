"""The other languages, built from the English localization after generate.py writes it. Each string is masked, its
expressions, numbers and names becoming {1}, {2}, so a translation survives changes to them, and stored under a hash of
the masked English in tools/i18n/<language>/*.json. A string with no translation stays English until it has one.

Usage: py -3 tools/i18n.py source          writes tools/i18n/source/<n>.txt, the strings to translate
       py -3 tools/i18n.py check [language]  every translation against its English: what is missing, stale or broken
       py -3 tools/i18n.py prune [language]  drops the stale ones (copy tools/i18n first)
       py -3 tools/i18n.py terms <language> <English>...  vanilla's wording of a term, for matching it"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
STORE = HERE / "i18n"
MOD = Path(os.environ.get("SPEC_MOD_OUT") or HERE.parent / "mod")  # SPEC_MOD_OUT: the side build, as in generate.py
GAME = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game")
LANGUAGES = ["braz_por", "french", "german", "japanese", "korean", "polish", "russian", "simp_chinese", "spanish", "turkish"]
ENTRY = re.compile(r'^\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$')
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![A-Za-z\d])")
LITERAL = re.compile(r"\[concept_\w+\]|\$\w+\$|#!|#\w+(?::\w+)? |\\n|@\w+!")  # what a translation must keep as it is
KEPT_VARIABLE = re.compile(r"\$(SPEC_|TOOLTIP_DELIMITER|concept_)")


def bracket_end(s, i):
    depth = 0
    for j in range(i, len(s)):
        depth += (s[j] == "[") - (s[j] == "]")
        if not depth:
            return j + 1
    return len(s)


def mask(value):
    """(the string with its expressions, names and numbers as {1}, {2}, ..., the text of each)."""
    out, tokens, i = [], [], 0

    def hide(text):
        tokens.append(text)
        out.append(f"{{{len(tokens)}}}")

    while i < len(value):
        c = value[i]
        tip = re.compile(r"#tooltippable #tooltip:\[[^\]]*\],\w+ ").match(value, i)
        if tip:
            hide(tip.group())
            i = tip.end()
        elif c == "[" and not re.compile(r"\[concept_\w+\]").match(value, i):
            j = bracket_end(value, i)
            hide(value[i:j])
            i = j
        elif c == "$" and (m := re.compile(r"\$[\w|=+\-%.]+\$").match(value, i)) and not KEPT_VARIABLE.match(m.group()):
            hide(m.group())
            i = m.end()
        elif (lit := LITERAL.match(value, i)):
            out.append(lit.group())
            i = lit.end()
        elif (num := NUMBER.match(value, i)) and not (i and (value[i - 1].isalnum() or value[i - 1] == ".")):
            hide(num.group())
            i = num.end()
        else:
            out.append(c)
            i += 1
    return "".join(out), tokens


def unmask(text, tokens):
    return re.sub(r"\{(\d+)\}", lambda m: tokens[int(m.group(1)) - 1], text)


def has_words(masked):
    return bool(re.search(r"[^\W\d_]{2,}", LITERAL.sub(" ", re.sub(r"\{\d+\}", " ", masked))))


def string_id(masked):
    return hashlib.md5(masked.encode("utf-8")).hexdigest()[:10]


def english():
    """[(file relative to localization/english, [(key, value)])], blank lines and comments dropped."""
    files = []
    root = MOD / "localization/english"
    for p in sorted(root.rglob("*.yml")):
        pairs = [m.groups() for m in map(ENTRY.match, p.read_text(encoding="utf-8-sig").splitlines()) if m]
        files.append((p.relative_to(root).as_posix(), pairs))
    return files


def load(language):
    table = {}
    for p in sorted((STORE / language).glob("*.json")):
        table.update(json.loads(p.read_text(encoding="utf-8-sig")))
    return table


def problems(en, text):
    """What is wrong with a translation (both masked), [] if nothing."""
    bad = []
    need, got = re.findall(r"\{\d+\}", en), re.findall(r"\{\d+\}", text)
    if sorted(need) != sorted(got):
        bad.append(f"placeholders {sorted(need)} became {sorted(got)}")
    a, b = sorted(LITERAL.findall(en)), sorted(LITERAL.findall(text))
    if a != b:
        lost = [t for t in set(a) if a.count(t) > b.count(t)]
        added = [t for t in set(b) if b.count(t) > a.count(t)]
        bad.append(f"codes lost {lost} added {added}")
    if '"' in text and '"' not in en:
        bad.append('has a " the English does not')
    if re.search(r"\[(?!concept_)|\](?<!\w\])", text):
        bad.append("has a [ or ] that is not a [concept_...] link")
    depth = 0
    for m in re.finditer(r"#!|#\w+(?::\w+)? |\{(\d+)\}", text):
        if m.group() == "#!":
            depth -= 1
        elif m.group(1) is None:
            depth += 1
        else:
            depth += OPENS.get((en, m.group(1)), 0)
        if depth < 0:
            bad.append("a #! comes before what it closes")
            break
    return bad


OPENS = {}  # (masked English, placeholder number): text styles a placeholder opens, as a tooltip link opens two


def strings():
    """{masked: (first key, tokens)} for every string with words to translate."""
    found = {}
    for _, pairs in english():
        for key, value in pairs:
            masked, tokens = mask(value)
            assert unmask(masked, tokens) == value, key
            if has_words(masked):
                found.setdefault(masked, (key, tokens))
                for n, t in enumerate(tokens, 1):
                    if t.startswith("#tooltippable"):
                        OPENS[masked, str(n)] = 2
    return found


def hint(token):
    if NUMBER.fullmatch(token):
        return None
    if token.startswith("#tooltippable"):
        return "opens a hover link, closed by #!#!"
    if token.startswith("$"):
        return "a game name"
    if re.search(r"SelectLocalization|AddLocalizationIf", token):
        return "text the game picks, may be empty"
    if "GetName" in token or "GetCustomName" in token or "GetAdjective" in token:
        return "a name"
    if "Concept(" in token:
        return "a linked term: " + re.search(r"Concept\('concept_(\w+)", token).group(1)
    return "a value"


def source(per_file=160):
    out = STORE / "source"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.txt"):
        old.unlink()
    items = sorted(strings().items(), key=lambda kv: kv[1][0])
    for part in range((len(items) + per_file - 1) // per_file):
        lines = []
        for masked, (key, tokens) in items[part * per_file:(part + 1) * per_file]:
            hints = [f"{{{n}}}={h}" for n, t in enumerate(tokens, 1) if (h := hint(t))]
            lines.append(f"{string_id(masked)}\t{key}\t{masked}" + ("\t" + "; ".join(hints) if hints else ""))
        (out / f"{part + 1}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(items)} strings, {sum(len(re.findall(r'[^\W\d_]+', m)) for m in strings())} words, {part + 1} files")


def check(languages):
    found = strings()
    ids = {string_id(m): m for m in found}
    failed = 0
    for language in languages:
        table = load(language)
        broken = {i: problems(ids[i], t) for i, t in table.items() if i in ids}
        broken = {i: b for i, b in broken.items() if b}
        missing = [i for i in ids if i not in table]
        same = [i for i, t in table.items() if i in ids and t == ids[i] and len(ids[i].split()) > 2]
        print(f"{language}: {len(table)} stored, {len(missing)} missing, {len(broken)} broken, {len(same)} left in English, "
              f"{sum(i not in ids for i in table)} stale")
        for i, b in list(broken.items())[:40]:
            print(f"  {i} {found[ids[i]][0]}: {'; '.join(b)}")
        failed += len(broken)
    return failed


HISTORY = STORE / "keys.json"  # key -> the ids its English has had, oldest first, so an edit keeps the old translation


def history():
    """{key: [ids]}: keys.json, plus what the source export had for each key (the ids translators worked from)."""
    try:
        out = json.loads(HISTORY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        out = {}
    for p in sorted((STORE / "source").glob("*.txt")):
        for line in p.read_text(encoding="utf-8").splitlines():
            i, key, *_ = line.split("\t") + [""]
            if key and i not in out.setdefault(key, []):
                out[key].insert(0, i)
    return out


def pick(table, key, masked, past):
    """(translation, how): this English's own, else the newest one from an earlier English of the key whose
    placeholders and codes still fit ('outdated'), else (None, 'missing')."""
    if (text := table.get(string_id(masked))) is not None:
        return text, "own"
    for i in reversed(past.get(key, [])):
        if (text := table.get(i)) is not None and not problems(masked, text):
            return text, "outdated"
    return None, "missing"


def build(write):
    """Every language's files beside the English. The keys are all there, so a string with no translation reads English
    rather than as its key. A key whose English changed keeps its last translation until it is translated again, and
    each language's missing and outdated counts are printed, so neither goes unnoticed."""
    files = english()
    found = strings()  # also fills OPENS, without which problems() rejects every string with a hover link
    past = history()
    for _, pairs in files:
        for key, value in pairs:
            masked, _ = mask(value)
            if has_words(masked) and string_id(masked) not in past.setdefault(key, []):
                past[key].append(string_id(masked))
    exported = {line.split("\t")[0] for p in (STORE / "source").glob("*.txt") for line in p.read_text(encoding="utf-8").splitlines()}
    if exported != {string_id(m) for m in found}:
        print("i18n: tools/i18n/source is out of date with the English; run py -3 tools/i18n.py source before sending it out")
    for language in LANGUAGES:
        table = load(language)
        count = {"own": 0, "outdated": 0, "missing": 0}
        for rel, pairs in files:
            lines = [f"l_{language}:"]
            for key, value in pairs:
                masked, tokens = mask(value)
                text, how = pick(table, key, masked, past) if has_words(masked) else (None, "")
                if how:
                    count[how] += 1
                if text and (bad := problems(masked, text)):
                    print(f"{language} {key} stays English: {'; '.join(bad)}")
                    count[how] -= 1
                    count["missing"] += 1
                elif text:
                    value = unmask(text, tokens)
                lines.append(f' {key}: "{value}"')
            write(f"localization/{language}/{rel.replace('l_english', f'l_{language}')}", "\n".join(lines) + "\n")
        print(f"i18n {language}: {count['own']} translated, {count['outdated']} kept from an earlier English, {count['missing']} still English")
    if not os.environ.get("SPEC_MOD_OUT"):  # side builds (sweeps) run side by side: only the live build records
        HISTORY.write_text(json.dumps(past, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")


def terms(language, wanted):
    """Vanilla's strings whose English is exactly one of these, in the language."""
    def table(lang):
        out = {}
        for p in (GAME / "localization" / lang).rglob("*.yml"):
            for m in map(ENTRY.match, p.read_text(encoding="utf-8-sig", errors="ignore").splitlines()):
                if m:
                    out[m.group(1)] = m.group(2)
        return out
    en, other = table("english"), table(language)
    want = {w.lower() for w in wanted}
    seen = set()
    for key, value in en.items():
        if value.lower() in want and key in other and (value, other[key]) not in seen:
            seen.add((value, other[key]))
            print(f"{value} = {other[key]}   ({key})")


def prune(languages):
    """Drops stored translations whose English text is gone (the 'stale' count in check). Copy tools/i18n first."""
    ids = {string_id(m) for m in strings()}
    for language in languages:
        cut = 0
        for p in sorted((STORE / language).glob("*.json")):
            table = json.loads(p.read_text(encoding="utf-8-sig"))
            keep = {i: t for i, t in table.items() if i in ids}
            cut += len(table) - len(keep)
            if len(keep) < len(table):
                p.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
        print(f"{language}: {cut} cut")


if __name__ == "__main__":
    command, args = (sys.argv + [""])[1], sys.argv[2:]
    if command == "source":
        source()
    elif command == "check":
        sys.exit(1 if check(args or LANGUAGES) else 0)
    elif command == "prune":
        prune(args or LANGUAGES)
    elif command == "terms":
        terms(args[0], args[1:])
    else:
        # the mask gives back what it took, and a broken translation is caught
        s = "#v [Country.GetName]#! fell #N -5.1#!\\n[concept_good]: $wine$ x2 #tooltippable #tooltip:[A.B],KEY_1 here#!#!"
        m, t = mask(s)
        assert unmask(m, t) == s and "[concept_good]" in m and "Country" not in m and "5.1" not in m, m
        OPENS[m, "4"] = 2
        assert not problems(m, m), problems(m, m)
        assert problems(m, m.replace("{1}", "")) and problems(m, m.replace("#!", "", 1)) and problems(m, m + '"')
        # an edited English keeps the key's last translation while it still fits, and says so
        old, new = mask("Banks lend #v [X]#!")[0], mask("Banks lend now #v [X]#!")[0]
        table, past = {string_id(old): "Bancos #v {1}#!"}, {"K": [string_id(old)]}
        assert pick(table, "K", new, past) == ("Bancos #v {1}#!", "outdated") and pick(table, "K", old, past)[1] == "own"
        assert pick(table, "K", mask("Banks #v [X]#! and #v [Y]#!")[0], past) == (None, "missing")  # a placeholder more
        print("i18n ok")
