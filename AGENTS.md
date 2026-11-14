# Release workflow

The user requested a separate beta distribution on November 13, 2026 to reduce disruption to stable subscribers.

- Keep `mod/` as the stable release output. Generate experiments into a separate `SPEC_MOD_OUT` directory and package them with `beta/build.py`.
- Test changes in the beta distribution before promoting them to stable. A focused, verified stable hotfix is appropriate for a reported broken feature.
- Stable uses `speculative_markets`; beta uses `speculative_markets_beta`. Enable exactly one. Never upload beta content to the stable Workshop item.
- The optional Community Mod Framework compatibility mod is separate under `compatibility/cmf/`. It loads after CMF and whichever Speculative Markets channel is enabled. Rebuild and retest it when either parent's GUI changes.
- Edit generators under `tools/`, then regenerate; do not maintain divergent handwritten copies of generated gameplay files.
- For Finance navigation changes, verify the journal and goods-panel Open Finance shortcuts in-game, including the selected tab, and exercise native/CMF panel transitions as applicable. Static handler checks alone are insufficient.
- Keep versioned release archives immutable, with hashes and precise validation notes. Do not describe a package as published unless a successful Workshop upload was observed.

See `beta/README.md`, `compatibility/cmf/README.md`, and `HOTFIX_1.0.2.md` for build commands and release details.
