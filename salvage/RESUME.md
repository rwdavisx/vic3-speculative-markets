# Resume 1.3.1 tuning on another machine

This branch is `release-1.1` at 1.3.0 (`25020bb`) plus the lost session's uncommitted work, rebuilt from its transcript.
The rebuilt `tools/` match the desktop at 13:12 UTC on 2026-11-25: beta.4 values with `LEV_LADDER` [3,6,9,12].
Full context is in `HANDOFF_tuner_2026-11-25.md`.

## What was rebuilt

- Generators and tools: `tuning.json`, `generate.py` (VERSION 1.3.1), `credit_ai.py` (margin AI rule), `leverage.py` (RECORD_PAST, AI limits),
  `market_tab.py`, `concepts.py`, `values_table.py`, `tuner.py`, `fastsim.py`.
- Simulator: `tuner/engine.py` (Tight payoff, AI rule, run12/blind12 bots, calibration, construction clamp), `inputs.json`, `targets.json`, `lab.py`, `server.py`.
- Beta text: `beta/changelog_1.3.1-beta.{1..4}.bbcode`, `beta/workshop_description.bbcode` (names beta.4; beta.4 was never uploaded).
- Scan helpers, formerly in the Windows temp scratchpad: `tools/tuner/scans/` (`r12b.py`, `mania12.py`, `mania12_h.py`, ...), plus `g3.json`, the scan that was running when the session died.

## Not rebuilt

- Build outputs: `build_scratch/rc_1.3.1`, `beta/release_131` packages and zips, Workshop staging. Regenerate them.
- The tutorial artifact, infographic and `_claude_scratch` experiments.

## Checks made in the cloud

- Every replayed find-and-replace matched exactly once.
- Two output sizes match the desktop's tool results: `workshop_description.bbcode` was 7112 and then 7169 bytes.
- All changed Python compiles and all JSON parses.
- **Not run:** `generate.py`, `check.py` and the simulator. They read the Victoria 3 install (`GAME` in `tools/generate.py`, `G:/SteamLibrary/...`), and the cloud has none. On a machine with the game at another path, change `GAME` locally.

## Next steps

1. Sanity check (from the repo root):
   - `SPEC_MOD_OUT=build_scratch/rc_1.3.1 py -3 -B tools/generate.py`
   - `py -3 -B tools/check.py`
   - `py -3 -B tools/tuner/engine.py`
2. Rerun the in-flight scan, the four 3/6/9/12 candidates:
   - `for k in 1 2 3: py -3 -B tools/tuner/scans/r12b.py 1000 k tools/tuner/scans/g3.json`
   - and `py -3 -B tools/tuner/scans/mania12.py one 1000 k tools/tuner/scans/g3.json`
3. Pick values where:
   - run12 beats hold6
   - reckless is clearly below careful
   - run12 panics are at most about 5.5

   Confirm under High volatility: `HV=78,0.25,1 py -3 -B tools/tuner/scans/mania12_h.py one 600 1 tools/tuner/scans/l0.json`.
4. Write the values into `tools/tuning.json`, regenerate, and check the leverage bar's 6 and 9 steps in game.
5. Build as **1.3.1-beta.5**. The changelog lists old → new against **beta.3**, the live beta. Leave beta.4 unpublished. Ask before uploading.
