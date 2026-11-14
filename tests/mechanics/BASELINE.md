# Standalone baseline tests

Results and limits are in `verification_baseline_105.json` and `../../AUDIT_BASELINE.md`. Use a standalone beta build; do not enable stable or compatibility mods. All test outputs belong under a new `runs/` directory.

Prepare `ai_frequency`, `crisis_network`, `tag_persistence`, `depression_duration`, `building_groups`, `owner_groups` or `successors` with:

```powershell
py -3 tools/mechanics_testbed.py --source beta/audit_baseline/mod --out runs/example --suite successors
py -3 tools/sweep.py --name example --arm test=runs/example --until 1837.4.1 --jobs 1
py -3 tools/mechanics_testbed.py --out runs/example --report runs/sweep_example/test_01/assertions.log --error-log runs/sweep_example/test_01/error.log
```

Use an end date after August 1838 for modifier expiry. The other short fixtures finish within the first few months. `successors` forces real uprisings with test-only political modifiers and checks their state after normal monthly initialization. It tests initialization, not natural uprising frequency. AI rescue draws have probabilistic acceptance bands; a failing sample needs investigation and repeated seeds, not widened bands.

For the manual war case:

```powershell
py -3 tools/late_peace_testbed.py --source beta/audit_baseline/mod --out runs/manual_peace
```

Launch only that disposable mod as Britain. The first monthly pulse starts a war against France with Prussia backing it. Follow the `READY TO CAPITULATE` log markers: switch to Prussia and surrender through the native war panel; wait at least seven days for the next marker; switch to France and surrender; advance at least three days. Capture cumulative debug/error logs and use the normal report command. The wrapper counts calls and delegates to the unchanged production settlement body.

The recorded UI run used an older standalone February 1836 save, manual start rather than automatic monthly start, a no-op for an old pending test event, and temporary console buttons/readout. Those controls are not in the release package. Their final hashes and the one readout warning are recorded in the evidence JSON. Language screenshots cover the upper Speculation panel, not every translated tooltip. The 140% test used a 1920x1080 window; the game itself marks that scale as larger than recommended.
