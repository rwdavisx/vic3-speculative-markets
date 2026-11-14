# Speculative Markets - Morgenroete Compatibility

An independently generated compatibility patch maintained with Speculative Markets.
**Published 1.0.0**, Workshop [3839705018](https://steamcommunity.com/sharedfiles/filedetails/?id=3839705018), for stable **1.0.5** or matching **1.0.5-beta.1**, Morgenroete **2.9.0e Curie**, Victoria 3 **1.15.1**.

Release verification: `tests/mechanics/verification_release_105.json`. All 85 focused engine assertions passed (76 inherited, 9 new migration), and the release UI renders all three added goods. The historical candidate notes below retain their original scope; individual-goods navigation and existing-Morgenroete-save migration are now checked. Full reporter playset and long campaigns remain untested.

The patch adds musical instruments, uranium, and printed publications to our price
trends, bank exposure, boom/bust cycle, industry interventions, building investment
and throughput, company integration, and Finance interface. Morgenroete supplies
the goods, buildings, icons, production methods, and translated goods names.
Air travel and orchestral music remain outside this tradable-goods integration.
No base-game balance constants change.

Load in this order:

1. Community Mod Framework
2. Morgenroete - Dawn of Flavor (Workshop 2889925770)
3. Speculative Markets 1.0.5 OR Beta 1.0.5-beta.1 (exactly one)
4. This Morgenroete compatibility patch
5. Speculative Markets - Community Mod Framework Compatibility

Disable the unselected SM channel and the older third-party **Speculative Markets+Morgenroete**
(Workshop 3836657389). Our patch replaces that bridge; the two must not be combined.
The CMF patch remains separate because it merges the sidebar, while this patch adds
goods to Speculative Markets. Test existing saves on copies.

## Build and maintenance

From the repository root:

```powershell
py -3 -B tools/morgenroete_build.py --parent mod --out runs/morgenroete/next_candidate --version 1.0.0
py -3 -B -m unittest discover -s tests -p "test_*.py"
```

Choose a new candidate directory each time. The builder generates a normal SM build
and a Morgenroete-aware build from the same generators. It checks every generated
parent gameplay/UI file against the selected installed channel, then packages only
the differences. A parent mismatch stops the build. It does not modify either parent,
enable mods, subscribe to Workshop items, or publish anything.

`tools/mod_sources.py` contains the three-good registry. Game data provides current
categories, prices, building groups, AI base priorities, and company membership.
The patch defines the instrument workshop's missing throughput modifier type.
A separate company-map initialization key adds the new building/good mappings to
existing saves. Current Finance types and all current generator fixes are retained.

This still replaces some generated files, including the Finance window and monthly
action. It therefore **must be rebuilt and retested when the parent changes**. A
version check at build time cannot stop a subscriber from using an old patch later.
Only publish a package for a precisely identified, tested parent. Do not claim that
the beta-targeted patch supports the older stable output.

Before release, verify the three goods in the engine, old-save initialization,
Finance sidebar/journal shortcuts and selected tabs; verify the individual-goods shortcut remains absent, native/CMF panel
transitions, and full logs. Preserve candidate hashes and test evidence. The
reported player's entire modlist and long-term campaigns are separate coverage.

## Historical candidate validation — November 14, 2026

The beta5 candidate passed 24 focused engine assertions for the three added goods
and 52 collapse/recovery assertions covering the entire goods registry. Both runs
completed with zero blocking SM/test-script diagnostics. All 46 Python tests pass.
The default generator output remains byte-identical to beta5 gameplay/UI files.

Live checks with CMF, Morgenroete, beta5, this patch and our CMF patch passed:
Finance sidebar opening; journal and native goods shortcuts selecting Speculation;
Finance/native Market transitions; and Finance/Morgenroete Sports transitions.
The regenerated candidate_02 patch is byte-identical to the tested candidate_01.

Candidate_03 was subsequently rebuilt against local **1.0.4-beta.6** after the
user requested removal of individual goods' Open Finance buttons. Its patch files
are byte-identical to candidate_02: the bridge does not replace `goods_panel.gui`,
so it inherits that change from its parent. This rebuild is not a new Workshop
release or completion of the remaining integration checks below.

This is still an unpublished candidate, not a general save-compatibility claim.
The UI seed predates Morgenroete and produces missing Morgenroete variables in
its logs (including `elgar_music_tradition`). Our log classifier's historical
`basegame_script_errors` label includes upstream mod errors; it does not mean
these are vanilla defects. Those errors were not investigated or fixed here.
The new goods' individual UI rows, existing *Morgenroete* save migration, the
reporter's complete playset, and long-term integration remain release checks.
The two extra services are intentionally outside this patch's current scope.

Detailed evidence: `tests/mechanics/verification_morgenroete_beta104_5.json`.
The immutable local candidate archive and build manifest are in `releases/`.
Stable 1.0.4 needs a matching separately generated/tested patch, or promotion of
the tested parent first; do not use this beta5 package to overwrite stable logic.

## Attribution

Morgenroete is created and maintained by its own authors:
https://steamcommunity.com/sharedfiles/filedetails/?id=2889925770

The older third-party bridge was inspected to establish its integration scope and
the incompatibility. Its code, localization, images and assets are not bundled.
Our patch is generated from our maintained Speculative Markets source and reads
Morgenroete's installed definitions during the build.
