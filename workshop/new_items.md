# Current releases and separate Workshop items

All three current releases were uploaded successfully and verified **public** on November 13, 2026 at 19:28 EST (November 14, 00:28 UTC). The rejected CMF 1.0.0 and Beta 1.0.2-beta.1 archives are for audit only. The compatibility item's sole Workshop Required Item, Community Mod Framework, was saved and verified at 19:33 EST; [API receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T003313.752779Z_cmf_query_f5aa4cb9.json).

| Public Workshop item | Version | Successful upload verification |
| --- | --- | --- |
| [Speculative Markets](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383) | 1.0.2 | [Stable receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002829.727698Z_stable_update_verified_4c2e86f9.json) |
| [Speculative Markets - Beta](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) | 1.0.2-beta.2 | [Beta receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002820.272346Z_beta_update_verified_670b6158.json) |
| [Speculative Markets - CMF Compatibility](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275348) | 1.0.1 | [CMF patch receipt](G:/GameDev/speculative-markets/workshop/upload_receipts/20261114T002808.860527Z_cmf_update_verified_f8b6379e.json) |

The Steam API receipts confirm public visibility, nonzero content, the selected preview sizes, and description text matching the canonical local drafts. Each description links the other relevant releases; none asks players to enable stable and beta together.

## Accepted packages

| Package | Verified archive | Integrity record |
| --- | --- | --- |
| Stable 1.0.2 | [Speculative Markets 1.0.2](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.2.zip) | [Manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_1.0.2.manifest.json) |
| CMF patch 1.0.1 | [CMF Compatibility 1.0.1](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.zip) | [Manifest](G:/GameDev/speculative-markets/releases/Speculative_Markets_CMF_Compatibility_1.0.1.manifest.json) |
| Beta 1.0.2-beta.2 | [Speculative Markets Beta](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.2-beta.2.zip) | [Manifest](G:/GameDev/speculative-markets/beta/releases/Speculative_Markets_Beta_1.0.2-beta.2.manifest.json) |

All three archives pass integrity and output-byte checks. The corrected beta/CMF metadata and Finance transitions passed a fresh game run and final log review on Victoria 3 1.15.1; known existing engine warnings remain. See the [release review](G:/GameDev/speculative-markets/HOTFIX_1.0.2.md) for the exact validation scope. Do not select an older candidate merely because its ZIP is still present in a release directory.

## Item identities and future updates

| Field | Beta item | Compatibility item |
| --- | --- | --- |
| Title | **Speculative Markets - Beta** | **Speculative Markets - CMF Compatibility** |
| Local mod folder | [beta/mod](G:/GameDev/speculative-markets/beta/mod) | [compatibility/cmf/mod](G:/GameDev/speculative-markets/compatibility/cmf/mod) |
| Current version | 1.0.2-beta.2 | 1.0.1 |
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

Check that the plan names item `3839275304`, the intended version, source archive hash, description hash, and public visibility. When the upload is authorized and that exact plan has been reviewed, execute the same update:

```powershell
py -3 -B tools/steam_upload.py update beta --public --execute
```

Use channel `cmf` for item `3839275348`, or `stable` for item `3831434383`, with the same plan-then-execute sequence. Keep `--public` on updates to these public listings; without it, the helper defaults to private visibility for Beta and CMF. Afterward, inspect the new `update_verified` receipt and live page, including description links and Required Items. If an upload is ambiguous or fails, reconcile its existing receipts and item state before retrying; never create a replacement listing as a shortcut.
