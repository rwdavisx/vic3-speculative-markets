# English localization style

The mod's text should read like a Paradox expansion, not a mod. These rules come from vanilla's own files
(`game/localization/english`). When unsure, find the vanilla string closest in purpose and copy its shape.

## Voice by surface

| Surface | Vanilla shape | Example (vanilla) |
|---|---|---|
| Concept `_desc` | Encyclopedia entry. First sentence says what it is. Then what drives it, then what it affects. The player is "you/your". | `concept_authority_desc`: "Authority is a [concept_capacity] used to effect internal change to your [concept_country]..." |
| Journal entry `_reason` / status text | Narrative, "we/our", present tense. Situation first, mechanics after. | `je_acw_countdown_reason`: "Slaveholders and abolitionists are engaged in increasingly rancorous debate..." |
| Alert `_desc` | Plain statement of the problem, "we/our". | "We are currently not actively focusing our research on any [concept_technology]." |
| Alert `_hint` | Advice addressed to the player: "You can ..." and where to do it. | "You can establish a new [concept_company] in the Companies Panel" |
| Alert `_action` | The destination's name. | "Budget Panel" |
| Notification `_name` | Short newspaper headline, sentence case, usually with a verb. | "[country] protests expulsions", "[formation] has returned from exile" |
| Notification `_desc` | One or two sentences of news, past or present perfect. At most one consequence. | "[country] has backed down from their expansion in [state], giving us a [concept_claim] on their colony." |
| Event `.t` | Evocative Title Case title. | "The Other Side of the Fence", "Unhappy Mine Owners" |
| Event `.d` | Two to four sentences of third-person narrative. No percentages or month counts unless the scene needs them; numbers belong in option tooltips. | "Several mine owners from [state] are requesting an exemption from the mining regulations." |
| Event `.f` | A vignette or a period quotation in `"..."`. | |
| Event options | Short, in a voice (a minister, the government), ending with a period. | "Light shall be mandatory.", "Too costly.", "One small exception couldn't hurt." |
| Decision / button name | Imperative, Title Case. | "Hold a Grand Exhibition" |
| Decision / button `_desc` | One in-world sentence of what is done and why, then briefly what it achieves. | "Hold a Grand Exhibition to show all the world your wonders. The more technologies you have to show, the more successful the exhibition will be." |
| Modifier name | Title Case noun phrase. | |
| Modifier `_desc` | One flavor sentence about the situation. The game lists the effects, so never repeat numbers. | |
| Condition tooltip (`_tt` used in triggers) | A fact in the present tense that is true when the condition passes. | "Has not lost the Opium Wars", "You own #bold all#! of your cultural homelands" |
| Breakdown lines | Vanilla's calculator: `value from cause`, `xN from cause`. | |
| Labels, tabs, column heads | Title Case, one to three words. | |
| UI instructions | `#instruction Click to ...#!` on its own line, at the end. | "#instruction Right-click to dismiss#!" |

## Rules

- **Link a concept once.** The first mention in a string is `[concept_x]`; later mentions in the same string use
  `$concept_x$` (plain name), as vanilla does. Keep the links that a player would actually want to open.
- **Concept icons are automatic.** `generate.with_icons` sets `@spec_<concept>!` before a mod concept that opens a
  line or a `#header`, and at the start of the concept's own description, as vanilla's "@aut! Authority". Don't type
  them by hand. A new concept needs an entry in `icons.CONCEPT_ICON` (a painted slot, `art/paint.sh <slot>`).
- **Vanilla's words.** Investment Pool, Throughput, Credit, Default, Treasury, Construction, Radicals, Loyalists,
  Interest Group, Market, Goods, Price: never a synonym.
- **American spelling,** as vanilla: favor, labor, center, harbor. The mod's term "Leading Exchange" and key names stay.
- **No designer's notes.** "Inspired by...", "This mod...", "Hover a group to see..." are out-of-world. History goes
  in-world: "#lore The Bank of England lent freely in the crises of 1847, 1857 and 1866.#!" on its own paragraph, or
  is dropped. Hover hints become vanilla's `#instruction`.
- **Concepts are not rulebooks.** Keep the thresholds a player plans around (Panic below 25, Mania at 80). Drop
  tuning numbers the tooltips already show (decay rates, per-month chances), or move them to the tooltip that shows
  the live value.
- **Sentences, not fragments,** in descriptions. Fragments are fine in labels and breakdown lines.
- **Plain period diction.** Formal, concrete, a little dry. No modern finance jargon the 1800s did not use, no jokes
  in UI text (event flavor may be wry). No dashes as sentence punctuation.
- **Format codes as vanilla:** values in `#v`, good/bad in `#P`/`#N`, named states in `#b`, section heads `#header`
  or `#title`. Do not add color to prose.
- **Keep the mod's named terms** exactly: concept names, the interest levels (Fleeing, Doubtful, Calm, Keen, Eager,
  Feverish), confidence tiers (Shaken/Panic, Wary, Steady, Buoyant, Mania), boom endings (Correction, Bust,
  Collapse), button names players have learned (Lend to the Banks, Buy Up Bad Loans, Restrain Speculation,
  Encourage Investment, Suspend the Bank Act, Relief Works). Renaming them is a design change, not a style fix.

## Process

Edit the strings in their generator under `tools/`, never the built files. Keep every key, every `[...]`
expression, `$...$` reference and `@icon!`; change only words and the concept-link form. Build to a side directory
and check:

```powershell
$env:SPEC_MOD_OUT = "<scratch dir>"; py -3 -B tools/generate.py; py -3 -B tools/check.py
```

A changed English string keeps its old translation while that translation's codes and placeholders still fit
(`outdated` in the build log), else it shows in English. Retranslate with `tools/i18n/BRIEF.md` afterwards.
