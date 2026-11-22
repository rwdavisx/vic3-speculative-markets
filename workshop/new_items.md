# Staged 1.2.0 release

Stable **1.2.0** was uploaded and Steam-verified public on November 22, 2026, 08:14 UTC ([receipt](upload_receipts/20261122T081438.810029Z_stable_update_verified_e82f4e42.json)). CMF 1.0.4, Morgenroete 1.2.0 and Tech & Res 1.1.0 were uploaded and Steam-verified public on November 22, 2026, 14:35 UTC (receipts `20261122T1435*_{cmf,morgenroete,techres}_update_verified_*.json`). Beta 1.2.0-beta.36 was uploaded and Steam-verified public at 14:36 UTC (`20261122T143643.380579Z_beta_update_verified_c90c7584.json`). The 1.2 gallery cards were put on the stable listing through the Steam client API on November 22, 2026: the old speculation.jpg was removed, and the new speculation.jpg, stances.jpg and monetary.jpg were added (now 14 images; Steam re-query confirmed). The stable listing's cover picture was replaced at 18:07 UTC with a preview-only update (`steam_upload.py update stable --execute --public --preview mod/thumbnail.png --note workshop/note_cover_1.2.0.txt`; receipt `20261122T180733.300445Z_stable_update_verified_5daa845e.json`): Steam reports a 999,022-byte preview, public, with the same content size and update time as the 1.2.0 upload. `mod/thumbnail.png` now holds the new cover and differs from the 1.2.0 archive until the next release; the beta and patch covers are unchanged. Run `py -3 -B tools/steam_upload.py plan <channel>` to review, then `update <channel> --execute --public` for each.

| Channel | Version | Archive sha256 |
| --- | --- | --- |
| stable | 1.2.0 | `d277d7ab230d41ee99745643be9771df4a22a8d2a7d81159b8b7af369d8a8828` |
| beta | 1.2.0-beta.36 (gameplay bytes match stable) | `34dbc864c157902b74e1dc937ea7d2bfee19205b2ab19b49030e9934641f45a4` |
| cmf | 1.0.4 | `64e1a36f870db50ec71801a3a99137157494f8f8f85082041b196be371f093f1` |
| morgenroete | 1.2.0 (Morgenroete 2.9.1c) | `8892f7f5752ec6bd6a9352969e9454da9b0d9ce3d9eed3a035d983f4c85188ba` |
| techres | 1.1.0 | `68bb2933733b6b44d7d6678cf0328550366be9f36b9f878779c497f7ef95a566` |

Checks run: `quick_test.py` generated-mod contracts PASS, CMF PASS; `i18n.py check` 0 missing and 0 broken in all 10 languages; CMF patch unit tests (11) OK; Morgenroete and Tech & Res builders' parent checks passed against 1.2.0. Python contract tests had 16 stale failures (tests/test_ui_hotfix.py expects the pre-rework sector filters and a one-expression filter caption; its evaluator lacks LessThan_CFixedPoint; tests/test_tuner_parity.py expects the old trust numbers). Not run: `quick_test.py --engine` (the dev game was open) and in-game checks of the patches. Balance is beta/feedback_120/tuning.json, copied to tools/tuning.json.

# Latest stable update

Steam verified public release **1.1.6** on November 18, 2026 (US Eastern). The release includes the Finance fixes and quality-of-life updates tested in **1.1.5-beta.4** and preserves the original 1.1 feature notes. See the [stable listing](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383), [release evidence](../tests/mechanics/verification_finance_116.json), and [Steam receipt](upload_receipts/20261118T055713.793707Z_stable_update_verified_2f27ea76.json).

# Latest beta update

Steam verified the public [Speculative Markets - Beta](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) update to **1.2.0-beta.1** on November 19, 2026, 15:19 UTC: archive `beta/releases/Speculative_Markets_Beta_1.2.0-beta.1.zip` (sha256 `55b475a6b93cb5e7693923c4b6ef9d7a526d6bba4c3f63a6394ec33a34e1a99b`), [Steam receipt](upload_receipts/20261119T151915.789623Z_beta_update_verified_bd8e33ff.json). Validation: generator and packaging checks passed, and the dev game loaded the build on Victoria 3 1.15.2 with no mod entries in the error log. `quick_test.py --engine` was not run, and the 1.2 features have not been checked in game. The Morgenroete and Tech & Res patches still match stable 1.1.6, and the listing warns against using them with this beta.

Previous: Steam verified the public update to **1.1.5-beta.2** on November 17, 2026 (US Eastern). The listing retains the 1.1 feature notes. See the [release evidence](../tests/mechanics/verification_finance_readability_115b2.json) and [Steam receipt](upload_receipts/20261118T043256.184905Z_beta_update_verified_013779c5.json).

# November 14, 2026 releases

Published and API-verified public November 14, 2026. Stable **1.0.6** and beta **1.0.6-beta.1** include the rivalry notification and AI rescue fixes. CMF **1.0.1** and Morgenroete **1.0.0** retain byte-identical patch content; their descriptions now identify the matching parent versions.

| Item | Version | Verification receipt |
| --- | --- | --- |
| [stable](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383) | 1.0.6 | `workshop\upload_receipts\20261114T201625.340346Z_stable_update_verified_0d9479cf.json` |
| [beta](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) | 1.0.6-beta.1 | `workshop\upload_receipts\20261114T201612.828807Z_beta_update_verified_1a59152d.json` |
| [cmf](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275348) | 1.0.1 | `workshop\upload_receipts\20261114T201626.541512Z_cmf_update_verified_36bc8034.json` |
| [morgenroete](https://steamcommunity.com/sharedfiles/filedetails/?id=3839705018) | 1.0.0 | `workshop\upload_receipts\20261114T201627.789819Z_morgenroete_update_verified_9d0cfd0f.json` |

See `HOTFIX_1.0.6.md` and `tests/mechanics/verification_release_106.json`. Historical records below are retained for reference.

# Historical release records and separate Workshop items

Stable 1.0.4 and Beta 1.0.4-beta.5 were uploaded successfully and verified **public** on November 14, 2026 at 06:11 and 15:34 UTC respectively. CMF remains 1.0.1. The rejected CMF 1.0.0 and Beta 1.0.2-beta.1 archives are for audit only. The compatibility item's sole Workshop Required Item, Community Mod Framework, was saved and verified at 19:33 EST; [API receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T003313.752779Z_cmf_query_f5aa4cb9.json).

| Public Workshop item | Version | Successful upload verification |
| --- | --- | --- |
| [Speculative Markets](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383) | 1.0.4 | [Stable receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T061128.512707Z_stable_update_verified_15683ca1.json) |
| [Speculative Markets - Beta](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) | 1.0.4-beta.5 | [Beta receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T153405.356081Z_beta_update_verified_08697ab8.json) |
| [Speculative Markets - CMF Compatibility](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275348) | 1.0.1 | [CMF patch receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002808.860527Z_cmf_update_verified_f8b6379e.json) |

The Steam API receipts confirm public visibility, nonzero content, the selected preview sizes, and description text matching the canonical local drafts. Each description links the other relevant releases; none asks players to enable stable and beta together.

## Accepted packages

| Package | Verified archive | Integrity record |
| --- | --- | --- |
| Stable 1.0.4 | [Speculative Markets 1.0.4](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.4.zip) | [Manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.4.manifest.json) |
| CMF patch 1.0.1 | [CMF Compatibility 1.0.1](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.zip) | [Manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.manifest.json) |
| Beta 1.0.4-beta.5 | [Speculative Markets Beta](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.4-beta.5.zip) | [Manifest](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.4-beta.5.manifest.json) |

All three archives pass integrity and output-byte checks. The corrected beta/CMF metadata and Finance transitions passed a fresh game run and final log review on Victoria 3 1.15.1; known existing engine warnings remain. See the [release review](G:/GameDev/speculative-markets/HOTFIX_1.0.2.md) for the exact validation scope. Do not select an older candidate merely because its ZIP is still present in a release directory.

## Item identities and future updates

| Field | Beta item | Compatibility item |
| --- | --- | --- |
| Title | **Speculative Markets - Beta** | **Speculative Markets - CMF Compatibility** |
| Local mod folder | [beta/mod](G:/GameDev/speculative-markets/beta/mod) | [compatibility/cmf/mod](G:/GameDev/speculative-markets/compatibility/cmf/mod) |
| Current version | 1.0.4-beta.5 | 1.0.1 |
| Metadata ID | `speculative_markets_beta` | `speculative_markets_cmf_compat` |
| Listing description | [Beta BBCode](G:/GameDev/speculative-markets/beta/workshop_description.bbcode) | [CMF patch BBCode](G:/GameDev/speculative-markets/compatibility/cmf/workshop_description.bbcode) |
| Preview | [Beta PNG](G:/GameDev/speculative-markets/workshop/new_items/beta_preview.png) / [SVG source](G:/GameDev/speculative-markets/workshop/new_items/beta_preview.svg) | [CMF patch PNG](G:/GameDev/speculative-markets/workshop/new_items/cmf_preview.png) / [SVG source](G:/GameDev/speculative-markets/workshop/new_items/cmf_preview.svg) |
| Suggested tags | Economy And Buildings; Events; Journal Entries | Utilities |
| Steam Required Items | **None.** Do not require stable or CMF. | Verified: **Community Mod Framework only**, item `3385002128`. Do not require stable and beta together. |
| Workshop item ID | `3839275304` | `3839275348` |

The beta and patch now have separate Workshop listings. Use their recorded IDs for later updates; never select stable item `3831434383` as the target for either package. Metadata IDs above are not Steam Workshop item numbers.

Use the preview PNGs as listing artwork; they are original text/vector designs and live outside the frozen mod packages. The beta package's inherited thumbnail still shows the older Market tab, so use the new Beta preview on its new listing. The compatibility package intentionally has only its two GUI files and metadata. If the upload workflow requires artwork inside a content folder, prepare a separate upload staging folder; do not alter the verified archives or silently overwrite their manifests.

The Beta and patch descriptions link each other, and the stable description links both new items. The patch description explains manual order: CMF, **one** Speculative Markets channel, patch last. Only CMF should be its Workshop Required Item; the stable-or-beta choice stays in the description because the game cannot express that alternative as a dependency.

For future uploads, confirm the item ID, content folder, version, description, preview, and Required Items. Keep successful upload receipts alongside the immutable release manifests. The [release review](G:/GameDev/speculative-markets/HOTFIX_1.0.2.md) contains the final runtime status and artifact hashes.

## Update the existing listings

The Beta and CMF listings were created through the official Steam API. Their IDs are bound in [beta.binding.json](G:/GameDev/speculative-markets/workshop/upload_receipts/beta.binding.json) and [cmf.binding.json](G:/GameDev/speculative-markets/workshop/upload_receipts/cmf.binding.json); [steam_upload.py](G:/GameDev/speculative-markets/tools/steam_upload.py) reads those bindings for updates. The launcher's database does **not** have their `remoteSteamId` association. Do not run `create` again, delete the binding/creation-intent receipts, or publish them blindly from the launcher: that could create duplicate listings. Stable remains bound to item `3831434383` in the uploader.

For a future release, first build and validate a new immutable archive and manifest. Stage that accepted release under `workshop/upload_staging/<channel>/`, with the chosen preview and a reviewed `workshop/upload_staging/manifest.json` containing its source archive hash, version, and every staged-file hash. Preserve the prior release archives and upload receipts. The uploader verifies the staged files against this manifest; it does not generate or validate new gameplay changes for you.

From the repository root, run the intended update without `--execute` first. This example plans a public update of the **existing Beta item**:

```powershell
py -3 -B tools/steam_upload.py update beta --public
```

For stable and beta content updates, run the fast checks against the intended beta and record their results as described in `RELEASE_TESTING.md`. Verify relevant UI changes in-game.

Check that the plan names item `3839275304`, the intended version, source archive hash, description hash, and public visibility. When the upload is authorized and that exact plan has been reviewed, execute the same update:

```powershell
py -3 -B tools/steam_upload.py update beta --public --execute
```

Use channel `cmf` for item `3839275348`, or `stable` for item `3831434383`, with the same plan-then-execute sequence. Keep `--public` on updates to these public listings; without it, the helper defaults to private visibility for Beta and CMF. Afterward, inspect the new `update_verified` receipt and live page, including description links and Required Items. If an upload is ambiguous or fails, reconcile its existing receipts and item state before retrying; never create a replacement listing as a shortcut.

## Follow-up Beta 1.0.4-beta.4

Published and verified public at 14:23:52 UTC, November 14, item 3839275304.
Receipt: `workshop/upload_receipts/20261114T142352.503370Z_beta_update_verified_48d4f209.json`.
Archive SHA256: `b0c66b01bbcb99f60e65a8d8246de86a126335014c516a85ffb9d8e10a4d2f82`.
Fixes burst losses overstated in the confidence breakdown when confidence hits zero.
The resulting confidence and balance are unchanged. Red/green accounting tests and
37 related regression assertions pass full log gates. Description lists the latest
version and concise change bullets. Stable and CMF are unchanged. Detailed evidence:
`tests/mechanics/verification_accounting_2026-11-14.json`; open checks remain in the audit.
