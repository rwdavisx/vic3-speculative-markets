# Live player takeover test

Build a disposable copy of a chosen beta:

```powershell
py -3 tests/manual/player_takeover.py --source beta/mod --out runs/unique_takeover_run/mod
py -3 tests/manual/launch.py --run runs/unique_takeover_run --settings-profile runs/previous_run/profile
```

The launcher uses the game's binaries directory and Steam app ID so owned DLC
is recognized, and records these settings with the process ID. Use a settings
profile with event pausing enabled, cloud saves disabled and autosaves off.

Launch that copy alone in a private debug profile. Start a fresh sandbox as
Britain. Accept `TEST: Play the revolution`; after its 35-day checks, inspect
Financial Markets and use Open Finance. Minimize the secession prompt while
checking the revolution's UI, then accept it and repeat the UI checks for the
secession country.

Keep cumulative debug and error logs. The original successor fixture finishes
400 days after setup; the eight takeover checks must also finish. Evaluate all
20 assertions with `tools/mechanics_testbed.py --report ... --error-log ...`.
Passing assertions alone is insufficient: the cumulative error gate must pass.
Capture the selected Finance tab and country in screenshots.

Continue through an actual revolutionary victory when testing journal
inheritance. A run where the parent wins or neither side wins does not verify
that transition. Inspect the victorious country's journal and Finance panel.
The 20 assertions do not assert the victory outcome, so record that separately.

Never package or upload the disposable fixture. Retain failed runs alongside
the successful repeat and record exact source and evidence hashes.

## AI winner after a player parent

`ai_victory_takeover.py --source beta/.../mod --out runs/unique_run/mod`
tests the other direction: start as Britain, accept the parent-country prompt,
and let its 35-day check return control to Britain. The parent must gain a
journal and its insertion guard. Wait for the AI revolution to defeat it,
then accept the victor prompt and wait 35 more days. Check the journal and
Open Finance in the winner. The 17 assertions include an actual dead-parent /
living-victor condition; a run without that outcome is incomplete.

## Campaign crash controls

`campaign_controls.py --out runs/unique_controls --candidate beta/.../mod --seeds 2`
creates native vanilla seed saves, then runs vanilla, published beta, and the
candidate from each identical saved world. Each run ends June 1841. The modded
arms include the repeated campaign contracts; vanilla is an exit/crash control.
The tool preserves exit codes, launch profiles, autosaves and crash dumps.
Evaluate the modded assertions and cumulative logs separately. Finishing a
control run alone is not a release certificate or proof of a crash fix.

## Depression buttons

`depression_buttons.py --source beta/.../mod --out runs/unique_run/mod`
creates 17 visible choice cases. Start Britain, then choose 1a, 1b, 2a, 2b,
3a, 3b, 4a, 4b, 4c, 5a, 5b, 6a, 6b, 7a, 7b, 8a, 8b. Each choice checks the
existing Great Power contract immediately and schedules the next case.
Preserve screenshots and evaluate all assertions plus the cumulative error log.
After the final choice, allow simulation to continue until completion is flushed
to disk before stopping the process.

Cases clone the original event under separate IDs to bypass repeat cooldowns.
The original option effects and text are retained; test setup restores baseline
values immediately before the selected effects. This verifies visible routing
and immediate effects, not natural event scheduling, cooldowns, or every locale.

## Rival win popup

`rival_popup.py --source beta/.../mod --out runs/unique_run/mod` retains only
the first annual pass of the existing rivalry notification fixture. Play Britain
and watch January 31 at low speed. Capture the win toast and subsequent queue;
evaluate both dispatch/reward contracts and the cumulative error log. This is
one three-rival win case, not the reporter's full playset or every outcome.
