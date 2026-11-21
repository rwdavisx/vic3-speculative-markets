# Speculative Markets — CMF Compatibility

The local 1.2.0-beta.16 candidate was rebuilt against CMF 1.68.0 and passed a joint engine smoke test with Tech & Res. Its six payload files match the beta.10 patch. The [candidate manifest](../../beta/feedback_120/releases/compatibility.manifest.json) identifies the tested archive.

Version **1.0.1** is an optional, separate compatibility mod for **Speculative Markets 1.0.2** and **Community Mod Framework 1.67.6**, built against Victoria 3 **1.15.1**. Players who do not use CMF do not need this patch.

Also verified with **Speculative Markets 1.0.3 / Beta 1.0.3-beta.2**: the notification hotfix changes no GUI files, both parent GUI hashes still match this build, and the beta with CMF and this patch completed the notification regression run. Patch 1.0.1 remains the current release; no rebuild is required for this hotfix.

Both parent mods define the `information_panel_bar` GUI type. Without a patch, CMF's definition can replace the sidebar that hosts Finance, removing both its button and window. This patch combines the two sidebars, preserves CMF's custom buttons, and coordinates opening and closing their windows.

Enable all three mods in this order, with the patch **below both parents**:

1. [Community Mod Framework](https://steamcommunity.com/sharedfiles/filedetails/?id=3385002128)
2. [Speculative Markets](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383)
3. **Speculative Markets — CMF Compatibility**

The patch does not include either parent mod. It changes only GUI files and has no economic scripts, balance changes, or save migration. It does not modify either parent's files. Other mods that replace these same sidebar files may require an additional merge.

Finance remains the large button below Power Bloc. CMF's registered buttons remain below the normal sidebar controls. Opening Finance closes other CMF windows; opening a CMF window closes Finance and cancels a pending speciality selection. Map, native panel, and ledger navigation also close Finance.

## Stable or beta

Enable **exactly one** Speculative Markets channel: stable (`speculative_markets`) or **Speculative Markets - Beta** (`speculative_markets_beta`). For the matching **1.0.2-beta.2** build, substitute Beta for the stable mod in step 2; keep CMF first and this patch last. The beta is a complete mod, not an add-on to stable. The corrected beta and patch metadata passed fresh engine validation.

**Set the load order manually.** Victoria 3 1.15.1 accepts dependency relationships only, although the launcher recognizes additional types. This patch therefore declares only CMF as required in metadata. It does not require both Speculative Markets channels. Players must enable exactly one channel and put this patch below it and CMF. On Workshop, only CMF should be a required item; the stable/beta choice belongs in the description.

## Build

From the repository root:

```powershell
py -3 -B compatibility/cmf/build.py
py -3 -B -m unittest discover -s compatibility/cmf -p "test_*.py"
```

The builder reads the generated stable Speculative Markets sidebar and the installed CMF sidebar. It writes only the separate patch directory. Parent versions and source hashes are recorded outside the installable mod. A changed upstream layout must be reviewed before rebuilding. A newer beta with different GUI files needs a new compatibility check.

## Validation

Source regression checks cover both parent load orders with the patch last, one effective sidebar definition, parent-file preservation, click transitions, navigation guards, and failure on missing source anchors.

With Speculative Markets 1.0.2 and CMF 1.67.6 on game 1.15.1, runtime checks confirmed Finance opens from the sidebar, Finance yields to CMF Organizations, and Organizations → Financial Markets Journal Entry → Open Finance opens the Speculation tab.

The earlier beta session also passed UI checks with Beta before CMF and the patch last: Finance opened, Finance and Organizations switched in both directions, the Journal shortcut selected Speculation, and the pause menu hid Finance. [Journal shortcut screenshot](G:/GameDev/speculative-markets/runs/cmf_compat/beta_reverse_102/je_fixed_finance.png).

Final log review rejected **CMF patch 1.0.0** and **Beta 1.0.2-beta.1** because the game could not parse their `load_after` / `incompatible_with` relationships. Those archives remain immutable audit artifacts and must not be installed or published. Patch **1.0.1** removes those entries without changing the GUI. Its nine source checks pass.

The final fresh run with **Beta 1.0.2-beta.2**, CMF, and patch **1.0.1 last** repeated Finance → Organizations → Journal Entry → Open Finance successfully, selected Speculation, and hid Finance when the pause menu opened. The completed log review found zero metadata/parser, script-system, or shipping-file runtime errors; existing engine/base diagnostics and variable warnings remain. [Final screenshot](G:/GameDev/speculative-markets/runs/cmf_compat/beta_metadata_final/je_fixed_finance.png) and [verification record](G:/GameDev/speculative-markets/runs/cmf_compat/verification.json). Future beta revisions still require their own compatibility check.

## Credits

The combined sidebar includes GUI code from [Community Mod Framework](https://github.com/Victoria-3-Modding-Co-op/Community-Mod-Framework), maintained by the Victoria 3 Modding Co-op, and from Speculative Markets. CMF's custom button registry and button implementation are preserved. This is an independently maintained compatibility patch, not a replacement for CMF.
