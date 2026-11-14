# Translating Speculative Markets

Speculative Markets is a Victoria 3 mod about booms, manias and financial panics in the 1800s. You are translating its
text into one language so it reads like Victoria 3's own translation of that language.

## Files

- Read: `G:\GameDev\speculative-markets\tools\i18n\source\1.txt` to `5.txt`. One string per line, tab-separated:
  `id`, `key`, `English`, and sometimes hints saying what each `{n}` is.
- Write: `G:\GameDev\speculative-markets\tools\i18n\<language>\1.json` to `5.json`, one per source file, UTF-8, shaped
  `{"<id>": "<translation>", ...}`. Write one file at a time.
- Check: `py -3 tools/i18n.py check <language>`, run from `G:\GameDev\speculative-markets` in PowerShell (the Bash tool
  is broken here). You are done when it reports 0 missing and 0 broken. "stale" should be 0 too.
- Vanilla wording: `py -3 tools/i18n.py terms <language> "Market Price" Authority Throughput` prints how the game
  translates a term. Vanilla's own files are in `G:\SteamLibrary\steamapps\common\Victoria 3\game\localization\<language>`.
- Touch nothing else. Do not edit `tools/i18n.py`, `mod/` or another language's folder.

## Keep exactly

- `{1}`, `{2}`...: each exactly once. Move them to wherever your grammar needs.
- `[concept_...]` links, `$...$` references, `@...!` icons, and `#v `, `#N `, `#P `, `#header `, `#title `, `#instruction `,
  `#indent_newline:3 ` style tags with their `#!` closers. Each must appear as often as in the English, and a tag must still
  open before its `#!` closes. Text inside a tag stays inside it. Do not translate these codes.
- `\n` line breaks: same number. In JSON that is written `\\n`, and a `"` is written `\"`. Other quotation marks are fine.
- Strings with a literal `"` (event quotations) keep theirs, or use your language's quotation marks.

## How to write it

- **Terms first.** Before translating, settle one wording for the mod's own terms and use it everywhere. Read the
  `concept_spec_*` entries and these sets, and keep each set consistent and distinct:
  - Interest levels: Fleeing, Doubtful, Calm, Keen, Eager, Feverish
  - Confidence tiers: Panic, Wary, Steady, Buoyant, Mania
  - Boom endings: Correction, Bust, Collapse
  - Others: Market Confidence, Investor Interest, Booms at Risk, Restrain, Encourage, Credit Policy, Banking Reforms,
    Market Mood, Long Depression
- **Vanilla's words win.** Where the game already has a term (Throughput, Authority, Investment Pool, Market Price,
  Great Power, Credit, Default, Goods), use its exact wording. Check with `terms`.
- **Match the game's voice:** the same register, punctuation and number style as vanilla's text in your language. Addressing
  the player follows vanilla too. English "we/our" means the player's country.
- **Plain words,** no jargon the English does not have. No dashes as sentence punctuation.
- **Keep labels short.** Keys for tabs, column titles, chips, tier names and buttons sit in tight spaces. A one or two word
  English label needs one or two words.
- **Do not depend on inflecting `{n}` or `[concept_...]`.** They appear in their dictionary form, so in languages with cases
  or gender, word the sentence so that form is correct, for example "Country: {1}" rather than a declined name. English
  `[concept_x]s` is a plural made with an s. Drop the s and word it so the plural is not needed.
- **Fragments join up.** Hints marked "text the game picks" and `$SPEC_...$` references insert other strings, often a whole
  sentence or an empty string. Keep the spacing around them as in the English. Read neighbouring keys when a piece makes no
  sense alone.
- `x{1}` and `x2.5` mean "times": keep the x. The calculator lines read "value from cause", as in vanilla's
  `BASE_VALUE_FOR_CALCULATOR` line of `core_l_english.yml`. Use your language's version of that wording.
- Event text and quotations should read as period prose, and may be freer than the UI text. Keep the jokes working.

Finish with a short report: the terms you chose for the sets above, and any strings you could not make work and why.
