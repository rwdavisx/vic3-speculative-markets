# Speculative Markets - Beta

This is the separate testing distribution of Speculative Markets. Enable **either Speculative Markets or Speculative Markets - Beta, never both**. The two distributions intentionally use the same gameplay definitions. Beta is a complete mod, not an add-on to stable.

Steam verified **1.2.0-beta.1** on November 19, 2026 (interest group stances, Monetary Standard, Financial Integration; see `workshop/new_items.md` for its validation scope). Before that, Steam verified **1.1.5-beta.2** on November 17, 2026 (US Eastern). It adds Banking breakdowns, a risk sort for goods, recovery and Great Issue timers, and clearer explanations for panic recalls, failed pledges, charter changes, and Shore Up. The packaged beta passed 295 assertions across 23 scenarios in one game instance. See the [verification record](../tests/mechanics/verification_finance_readability_115b2.json).

Use a separate playset and save copies when trying beta revisions; returning a beta save to an older version is not guaranteed. Older versioned archives remain immutable and do not indicate the currently published version.

**Do not use 1.0.3-beta.1.** It failed runtime verification because notification multipliers were blank. Its archive remains immutable; only revision 2 was published.

Beta has its own launcher name, ID `speculative_markets_beta`, and version `<source version>-beta.<revision>`. The launcher supports conflict relationships, but Victoria 3 1.15.1's game-side metadata reader rejects them. Beta therefore uses no conflict relationship; **you must disable stable manually when enabling beta**. The builder accepts only dependency relationships supported by the game.

**Do not use 1.0.2-beta.1.** Its archived ZIP is retained unchanged for the audit, with a `.rejected.json` record. The game rejected its `incompatible_with` metadata field. Revision 2 removes that field; gameplay files are unchanged.

There is one source tree in `tools/`. Do not edit generated files under `beta/mod/`. The builder copies a checked generated build, changes only launcher metadata, and verifies that every other byte is unchanged. It never installs a mod, modifies a playset, publishes to Workshop, or edits the source build.

Build the beta after generating and checking the intended main release:

```powershell
py -3 -B beta/build.py --revision 2
```

Outputs:

- `beta/mod/`: standalone mod content, including its distinct `.metadata/metadata.json`.
- `beta/releases/Speculative_Markets_Beta_<version>.zip`: deterministic ZIP, directly containing the mod files.
- `beta/releases/Speculative_Markets_Beta_<version>.manifest.json`: source/output hashes and archive hash.
- `beta/build_manifest.json`: fingerprint used to protect manually changed beta output from accidental replacement.

Increment `--revision` when publishing different bytes based on the same stable version. The builder refuses to overwrite an existing versioned ZIP with different content. Rebuilding the same inputs produces the same ZIP. If a generated beta directory was edited manually, preserve those edits elsewhere and rebuild from the source; the builder deliberately refuses to erase them.

For a future experiment, generate into a separate folder so `mod/` remains the stable artifact. Run these commands from the repository root, keeping any intended `SPEC_TUNING` override consistent for generation and checking:

```powershell
$env:SPEC_MOD_OUT = Join-Path (Get-Location) 'build_scratch/beta_candidate'
try {
    py -3 -B tools/generate.py
    if ($LASTEXITCODE -ne 0) { throw 'Generation failed' }
    py -3 -B beta/build.py --source $env:SPEC_MOD_OUT --revision 3
    if ($LASTEXITCODE -ne 0) { throw 'Beta packaging failed' }
} finally {
    Remove-Item Env:\SPEC_MOD_OUT -ErrorAction SilentlyContinue
}
```

A freshly generated side build may need the original `mod/thumbnail.png` copied into it before packaging; thumbnails are not generated. Use a clean non-debug source folder. `--log` builds, probes and hotfix test fixtures are rejected. The packaging checks cover source syntax/localization and artifact identity; they do not replace engine or UI validation of experimental changes.

The optional Community Mod Framework compatibility patch remains a separate mod. With CMF, enable CMF, **one** Speculative Markets distribution, then the patch after both. Its compatibility must be rechecked when either parent's GUI changes. Beta itself does not depend on CMF.

This folder is packaging infrastructure, not a second manually maintained gameplay source. Its separate [Beta Workshop item](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304) is now published. Future updates must use that existing item; never update stable with this package or create another Beta listing. The [publication index and update procedure](G:/GameDev/speculative-markets/workshop/new_items.md) records the API binding, staging checks, and dry-run/update commands. The launcher's database does not have the Beta item's upload association.
