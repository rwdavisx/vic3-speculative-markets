# Speculative Markets / Better Politics Mod compatibility patch

Under Better Politics Mod (BPM, Workshop 2932134122), this patch:

- **Shows the Goods section of the interest group panel.** BPM defines the panel in `gui/BPM_interest_group_panel.gui`. That file loads before our `gui/interest_group_panel.gui`, and the first definition of a GUI type wins. The patch ships BPM's file with our Goods section inserted (`ig_stances.panel_patch`).
- **Gives BPM's 13 political interest groups goods stances** (`ig_stances.BPM_POOLS`), from `ig_liberals` to `ig_agrarian_populists`. These can't go in the main mod, because without BPM their types don't exist.

The Monetary Standard stances need no patch. The main mod's `TRY_INJECT` lines in `tools/monetary.py` cover BPM's economy ideologies.

## Build

```
py -3 -B compatibility/bpm/build.py --out runs/bpm/<new folder> [--parent beta/mod] [--bpm PATH] [--version X.Y.Z]
```

The builder generates the parent twice: once as usual, and once with `SPEC_BPM` set to BPM's folder. It stops if the plain build doesn't match `--parent` byte for byte. The patch (`<out>/mod`) holds only the files that differ: the interest group scripts, the Finance tab, BPM's panel and the localization. The manifest records the parent, BPM's version and all hashes.

Because the patch replaces parent files, it matches only the parent it was built against. Rebuild it for every Speculative Markets release, for each channel, and whenever BPM changes its panel.

## Load order

1. Better Politics Mod
2. The Speculative Markets channel the patch was built against (exactly one)
3. This patch, last

## Open points

- The patch hasn't been tested in-game.
- The Restrain, Encourage and Great Issue tooltips list the groups, so their text differs from the parent's. Their translations fall back to English until the release translation pass.
- Ask BPM's author before publishing, because the patch redistributes a modified copy of their panel file.
