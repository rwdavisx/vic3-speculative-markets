# Release workflow

The user requested a separate beta distribution on November 13, 2026 to reduce disruption to stable subscribers.

- Keep `mod/` as the stable release output. Generate experiments into a separate `SPEC_MOD_OUT` directory and package them with `beta/build.py`.
- Test changes in the beta distribution before promoting them to stable. A focused, verified stable hotfix is appropriate for a reported broken feature.
- Before every stable/beta content upload, run the complete automated inventory with `tools/release_gate.py` against the intended beta and provide its passing report to `tools/steam_upload.py --gate`. Subset runs do not satisfy this requirement. See `RELEASE_TESTING.md`; relevant live UI/war checks remain separate and must not be described as automated passes.
- Stable uses `speculative_markets`; beta uses `speculative_markets_beta`. Enable exactly one. Never upload beta content to the stable Workshop item.
- The optional Community Mod Framework compatibility mod is separate under `compatibility/cmf/`. It loads after CMF and whichever Speculative Markets channel is enabled. Rebuild and retest it when either parent's GUI changes.
- Edit generators under `tools/`, then regenerate; do not maintain divergent handwritten copies of generated gameplay files.
- For Finance navigation changes, verify the journal and goods-panel Open Finance shortcuts in-game, including the selected tab, and exercise native/CMF panel transitions as applicable. Static handler checks alone are insufficient.
- Keep versioned release archives immutable, with hashes and precise validation notes. Do not describe a package as published unless a successful Workshop upload was observed.

See `beta/README.md`, `compatibility/cmf/README.md`, and `HOTFIX_1.0.2.md` for build commands and release details.

# Mechanics correctness before balance

- The user requested isolated, test-driven checks of each mechanic before further balance changes. Keep balance frozen while the open checks in `MECHANICS_AUDIT.md` remain.
- Reproduce a reported failure against a frozen beta, fix the generator, and rerun the case plus relevant regressions. A clean launch or static check is not proof that a mechanic works.
- Record assertion results and full error-log gates separately from live UI checks. Test fixtures must never enter a release package.
- CMF is now a periodic compatibility maintenance task, not the focus of the mechanics audit. Rebuild when its parent GUI changes and record whether the resulting patch bytes differ.
