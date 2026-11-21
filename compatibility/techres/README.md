# Speculative Markets - Tech & Res Compatibility

The local 1.2.0-beta.16 candidate uses the current beta as its parent and covers 85 goods. It includes the same category trends, Authority cap and domestic bulletin as the parent. The [candidate manifest](../../beta/feedback_120/releases/compatibility.manifest.json) identifies the 39-file candidate used in the joint engine smoke test.

**Published 1.0.0** (2026-11-18), Workshop [3841713072](https://steamcommunity.com/sharedfiles/filedetails/?id=3841713072), built against Speculative Markets 1.1.4, Tech & Res 1.7 (Workshop 3472248460), Victoria 3 1.15.1.
**Published 1.0.1** (2026-11-18 UTC, public, receipt `20261118T023337.975103Z_techres_update_verified_ee8d5d6e.json`):
`runs/techres/v1_0_1_meta/mod`, archive `releases/Speculative_Markets_TechRes_Compatibility_1.0.1.zip`, the 1.0.0 files with only the metadata changed.
Checked in a test copy of the Paradox Launcher: 1.0.0 shows "missing dependencies", 1.0.1 shows none (`launcher_check_1.0.1.png`). The
dependency now names Tech & Res by its metadata id `tech.res`; 1.0.0 used its Workshop number, which the mod manager
can't match (it matches `metadata_relationships.relationshipId` to `mods.metadataId`), so players saw a red warning.
Archive `releases/Speculative_Markets_TechRes_Compatibility_1.0.0.zip` (sha256 c83c0f8a…ef21), built with `--out runs/techres/v1_0_0 --version 1.0.0`.

The two mods run together without this patch: they share no files, their INJECTs on the same 43 vanilla buildings and on
Mutual Funds set different fields, and both monthly pulse hooks are lists that merge. This patch adds Tech & Res's goods
to our price trends, booms and busts, bank exposure, interventions, investment, companies and Finance window.

## Scope

36 Tech & Res goods, tied to 34 of its buildings (some of which also count vanilla goods: electricity, automobiles,
aeroplanes, tanks, rubber). The building ->
good registry is `TR_SELLS` / `TR_UPGRADES` in `tools/mod_sources.py`.

- Tech & Res replaces the vanilla synthetics plant to make cosmetics, so under this patch it counts cosmetics, not dye or silk.
- Secondary goods are counted from the start (no tech gate).
- Excluded: `androids` (no building makes it) and `elgar_music` (a service, as in the Morgenroete patch).
- Tech & Res redefines Morgenroete's uranium, instruments and prints itself, so this patch covers them. Don't combine it with
  the Morgenroete patch: both replace the same generated files. Morgenroete + Tech & Res players use this patch.
- Four buildings have no throughput modifier type upstream (fusion, geothermal and hydroelectric plants, instrument
  workshops); the patch defines them.

## Load order

Tech & Res requires the Community Mod Framework, so CMF and our CMF patch are always part of this set.

1. Community Mod Framework
2. Tech & Res
3. Speculative Markets
4. This patch
5. Speculative Markets - Community Mod Framework Compatibility

## Build

```powershell
py -3 -B tools/techres_build.py --out runs/techres/<new folder> --version 0.1.0-test
```

The builder generates a normal build and a Tech & Res-aware build from the same generators, fails unless the normal build
matches `mod/` byte for byte, and keeps only the files that differ (25) plus the missing modifier types.

## Validation

candidate1: parent check against 1.1.4 passed; `check.py` passed on both builds; every icon path the patch uses exists in
Tech & Res or the game. Not yet loaded in the game.
