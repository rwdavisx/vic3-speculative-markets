**Speculative Markets 1.0.2 — local release review, November 13, 2026**

This historical local review predates publication. The successful uploads are recorded in the publication update at the end.

The Journal Entry and goods-panel **Open Finance** buttons now open the Speculation tab correctly. Three separate artifacts are assembled locally; nothing in this release has been published to Workshop.

| Artifact | Use | Files / review manifest |
| --- | --- | --- |
| [Speculative Markets 1.0.2](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.2.zip) | Normal stable release; replaces the previous main mod | 155; [hash manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.2.manifest.json) |
| [CMF Compatibility 1.0.1](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.zip) | Optional patch when also using Community Mod Framework; corrected metadata | 3; [hash manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.manifest.json) |
| [Speculative Markets Beta 1.0.2-beta.2](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.2-beta.2.zip) | Separate testing channel; same gameplay as stable 1.0.2, corrected metadata | 155; [hash manifest](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.2-beta.2.manifest.json) |

Enable **stable or beta, never both**. Beta is a complete mod with its own launcher ID, `speculative_markets_beta`. Without CMF, the chosen Speculative Markets channel works on its own. With CMF, use this order:

1. Community Mod Framework 1.67.6.
2. Speculative Markets 1.0.2 **or** Beta 1.0.2-beta.2.
3. Speculative Markets — CMF Compatibility 1.0.1, below both.

Both parent orders are covered by the patch's source checks, provided the patch stays last. Set this order manually. The game accepts only dependency relationships, so the patch requires CMF in metadata and documents the stable-or-beta choice instead of requiring both. See the [compatibility instructions](G:/GameDev/speculative-markets/compatibility/cmf/README.md).

**Rejected candidates:** CMF Compatibility **1.0.0** and Beta **1.0.2-beta.1** are retained for audit only; do not install or publish them. Their UI tests passed, but final game-log review found that Victoria 3 1.15.1 rejects their `load_after` and `incompatible_with` metadata. The launcher accepting those fields was insufficient. Their replacements above remove the unsupported entries and passed a fresh engine run and completed log review.

The 1.0.2 source fix is in the shared [Open Finance handler](G:/GameDev/speculative-markets/tools/goods_panel.py:169), used by both the Journal Entry and goods panel. Previously it closed the source panel first; the later open-window and selected-tab actions did not run in the reproduced Journal transition. It now clears the pending selection, selects `booms`, opens Finance, and closes the source panel **last**. Runtime testing confirmed both entry points open the Speculation tab.

Compared with the archived 1.0.1 release, **exactly three main-mod files changed**: `.metadata/metadata.json`, `gui/goods_panel.gui`, and `gui/spec_journal_widgets.gui`. The two GUI changes reorder the shared click handler. All [1.0.1 fixes](G:/GameDev/speculative-markets/HOTFIX_1.0.1.md) remain; 1.0.2 changes no economic scripts or balance constants.

The separate CMF patch merges the conflicting sidebar definitions, retaining Finance and CMF's registered buttons. It coordinates window switching and masks the duplicate sidebar file. It includes no gameplay scripts and does not alter either parent. The initial beta differs from stable only in launcher metadata; all 154 other files are byte-identical. The [beta workflow](G:/GameDev/speculative-markets/beta/README.md) explains future isolated builds, revision numbering, and packaging from the shared source tree.

Validation against Victoria 3 **1.15.1**:

- Main/build unit checks pass **29/29**, including the Journal/goods handler regressions, six beta checks, and the packaging metadata check. The corrected CMF suite passes **9/9**, for **38 checks total**. Static checks pass for 75 script/GUI files and 2,992 localization keys; all ten translated languages have zero missing or broken strings.
- A fresh main-only 1.0.2 session passed Journal Entry → Open Finance and goods panel → Open Finance. The pause menu hid Finance correctly; the earlier overlay observed during live GUI reload did not reproduce, so no menu change was made.
- With CMF, Finance opened from the sidebar, yielded to Organizations, and reopened on Speculation through Organizations → Financial Markets Journal Entry → Open Finance.
- All three ZIPs pass integrity checks and match their generated output byte for byte. Stable/beta GUI fingerprints and the resulting CMF merge are identical.
- The final corrected session loaded **Beta 1.0.2-beta.2 before CMF**, with patch **1.0.1 last**. Finance opened from its icon; Finance → Organizations → Financial Markets Journal Entry → Open Finance selected Speculation; the pause menu hid Finance. The game exited through its UI. [Final Journal shortcut screenshot](G:/GameDev/speculative-markets/runs/cmf_compat/beta_metadata_final/je_fixed_finance.png). Disposable fixtures are excluded from release archives.
- The completed final log audit found **zero metadata/parser, script-system, or shipping-file runtime errors**. The conflicting sidebar definition is absent. The log is not empty: 16 known variable warnings and 217 engine/base records remain, including the existing Journal Entry and vanilla Barracks diagnostics.

The [compatibility verification record](G:/GameDev/speculative-markets/runs/cmf_compat/verification.json) records the main-file delta and GUI checks. Known vanilla and pre-existing load diagnostics remain; a passing UI check does not mean an empty engine log. The earlier 1.0.1 campaign and engine results are retained in its release report; they are not presented as new 1.0.2 campaign runs. Future beta GUI changes require a new compatibility check.

The [current-release and Workshop preparation index](G:/GameDev/speculative-markets/workshop/new_items.md) links the accepted packages, separate listing descriptions, original preview artwork, and per-item upload instructions. At the time of this local review, these were prepared artifacts awaiting upload; see the completed publication update below.

## Publication update — November 13, 2026

All three releases were uploaded and verified public at 19:28 EST (November 14, 00:28 UTC):

- [Speculative Markets 1.0.2](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383) — [verified upload receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002829.727698Z_stable_update_verified_4c2e86f9.json).
- [Speculative Markets - Beta 1.0.2-beta.2](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) — [verified upload receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002820.272346Z_beta_update_verified_670b6158.json).
- [Speculative Markets - CMF Compatibility 1.0.1](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275348) — [verified upload receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002808.860527Z_cmf_update_verified_f8b6379e.json).

The API verification confirmed public visibility, nonzero content, expected preview sizes, and description text matching the canonical local drafts. The descriptions now link the stable, beta, and compatibility items as appropriate, while instructing players to use exactly one Speculative Markets channel. The frozen release archives remain unchanged.

**Final publication check passed:** the compatibility item's sole Workshop Required Item is CMF (`3385002128`), confirmed on the live Steam page and by the [19:33 EST API query receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T003313.752779Z_cmf_query_f5aa4cb9.json). The query reports public visibility, exactly one child item, and an unchanged description hash. Beta has no required items and does not require stable.
