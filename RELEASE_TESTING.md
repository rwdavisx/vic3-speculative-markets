# Release testing

## Fast checks

Run `py -3 -B tools/quick_test.py` for the Python contracts, generated stable files and CMF tests. The three checks run in parallel. Pass `--source PATH` to check a separately generated stable layout.

Run `py -3 -B tools/quick_test.py --engine beta/mod` to add a single headless Victoria 3 process. Point `--engine` at the beta being tested. The runner copies it once, loads the selected fixture events together, and calls them on the same initialized world. Each assertion carries its suite name. A missing or repeated assertion, a failed assertion, an incomplete suite, a crash or a blocking error-log entry fails the batch. The report and raw evidence go under `runs/`.

Use `--cases bank_display renown_reach` to narrow the batch. The default group has been exercised together. Other single-event cases listed by `--help` can be run individually. An arbitrary combination can change another case's starting balance, laws, or rivalries. Check a new grouping both ways before adding it to the default.

## Release evidence

Record the candidate version, archive hash, and fast-check results with the release notes. For changes to navigation, verify the buttons, selected tabs, and panel transitions in the game. For war behavior that requires a native peace or capitulation action, keep the corresponding live-game evidence.

Stage the verified archive for the intended Workshop channel. The uploader checks the staged files against their manifest. Previous release reports and receipts are historical records.
