# Release testing

Every new gameplay/UI package must pass the full automated standalone inventory against its beta build before promotion. Relevant live UI and war checks remain separate requirements. A passing gate means the recorded contracts passed; it does not prove there are no bugs.

## Run the inventory

```powershell
py -3 tools/release_gate.py plan
py -3 tools/release_gate.py run --source beta/mod --name unique_release_label --jobs 2
py -3 tools/release_gate.py verify --report runs/release_gate/unique_release_label/report.json --source mod
```

Use a new label for every run. The runner freezes the beta, runs the Python checks, creates disposable test copies, and runs the 64 automated suites with at most two game processes. It keeps a report as each case completes. No stable/beta files or playsets are modified. It does not publish anything.

Four suites create a real annual save, end the first game process, and load that checkpoint in a second process. The campaign suite requires all eight checks exactly 21 times. Longer expiry tests run to their actual deadlines. The legacy hotfix and instrumented rivalry-notification suites use their dedicated preparers.

Any failed/missing assertion, incomplete sequence, short run, crash, timeout, missing error log, blocking mod/harness diagnostic, changed test definition or changed source invalidates the gate. Verification rechecks raw evidence and compares tested gameplay/UI hashes with the release target. Channel metadata and thumbnail artwork may differ. Known base-game diagnostics remain classified separately; a pass does not mean an empty error log.

Stable/beta content uploads through `tools/steam_upload.py` now require `--gate <report.json>`. The uploader revalidates it before contacting Steam. Description-only changes and unchanged compatibility packages do not need another standalone campaign run. This guard does not waive relevant manual validation.

`--only suite_name ...` is for testing the runner or diagnosing a failure. A subset is always marked incomplete for release purposes, even if every selected case passes. New fixture files require an explicit inventory entry; they cannot silently escape testing.

## Manual and excluded work

The report lists two manual engine fixtures (`war_campaign`, `late_peace`) and the explicitly excluded compatibility fixtures. Their presence in the inventory is not a pass. Use the existing live-war workflow and preserve its logs. For navigation/UI changes, follow AGENTS.md and verify the actual buttons, selected tabs and panel transitions. Existing UI evidence can only support unchanged relevant UI/handler bytes; static checks cannot substitute for a changed UI's live test.

Standalone automation does not cover the reporter's full modlist, every event button or translated tooltip, player takeover of a revolution/secession, every building/PM combination, or every possible random sequence. Compatibility testing remains outside the current audit scope unless its parent files change.

Do not relax assertions or classify an unexplained failure away to obtain a green release. Reproduce it, distinguish fixture errors from production defects, fix the correct source and record the rerun. Preserve rejected evidence and immutable release archives.

## First accepted full run

November 14, 2026, beta 1.0.6-beta.1: all 64 automated suites pass, with 945 observations and 60 Python tests. Four cases crossed actual save/reload boundaries. One inquiry fixture needed a numeric cooldown in place of a boolean; its original error-log failure is retained. The accepted collection uses that corrected rerun and the other 63 unchanged cases from the same frozen beta. Only the inquiry fixture changed, and every accepted fixture's hash was checked against its current source.

Accepted report: `tests/mechanics/verification_release_gate_106.json`. It verifies against both current stable and beta gameplay/UI bytes. The original full-run report remains failed; it was not overwritten or relabeled. The manual checks were not rerun in this automated pass. No new production fix or Workshop upload resulted.
