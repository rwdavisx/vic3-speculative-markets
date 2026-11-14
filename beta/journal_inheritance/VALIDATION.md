# 1.0.6-beta.2 — local candidate, not published

Fix: prevent a victorious revolution from inheriting a second Financial Markets
journal entry. Each country creates the entry through its existing initialization.
The original beta reproduced a duplicate-entry engine error on victory; the
candidate passed both player-revolution and AI-victor takeover checks.

Archive SHA-256:
`6ce2c56583ca19af1e9e1fce898fdd827ed8177de314a359a08048a1503b4ce5`

The immutable archive contains no test fixtures. Compared with published beta.1,
only the journal entry and build metadata differ. Stable and published beta
outputs remain unchanged. No Workshop upload was performed.

## Release hold

The full gate's repeated campaign crashed on January 10, 1840 after 16 passing
samples. The access-violation dump and cumulative logs are preserved. A fresh
repeat passed, as did two matched saved-world groups containing vanilla,
published beta.1 and this candidate. That does not explain the original crash
or justify replacing its failed gate result with a passing repeat.

Evidence is under `tests/mechanics/verification_*_106.json`:

- `journal_inheritance` and `ai_victory`: takeover assertions and live Finance checks.
- `depression_buttons`: all 17 visible choices and immediate effect contracts.
- `rival_popup`: one observed win toast, one dispatch, three preserved rewards.
- `campaign_exit` and `campaign_controls`: original crash, repeat, matched controls.

The automated gate is under `runs/release_gate/journal_inheritance_106_r1/`.
All 64 suites finished: 63 passed (777 observations), and the campaign failed.
All 60 Python tests passed. Raw evidence, source bytes and test-input hashes
were rechecked after completion. The release verifier rejects the report.
The committed result is `tests/mechanics/verification_journal_gate_106.json`.
This candidate must not be promoted on the basis of the focused checks alone.
