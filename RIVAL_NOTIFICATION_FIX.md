# Repeated rival notifications — November 14, 2026

The reported repeated rival-surpassed popup has a standalone reproduction. A player can name one rival while several AI exchanges name that player. Each distinct pair used to post the same generic notification. Reciprocal pairs already avoided double rewards; multiple incoming rivals were the missing notification case.

`tools/centres.py` now collects each player's win/loss flags during annual scoring and posts at most one notification of each kind after all pairs finish. It clears both flags in that pass. Every pair still changes trust as before. Mixed results can legitimately produce one win notice and one loss notice. The next annual pass can notify again; ties produce no notice. No balance constants changed.

## Test method

`tools/rival_notification_testbed.py` extracts the annual scoring body from a frozen beta package. Only the extracted test helper substitutes GBR for the player guard in observer mode and adds counters beside the retained production `post_notification` calls. This measures dispatch calls in the actual game engine, not rendered popup instances. The helper boundaries and hashes are recorded in each run manifest. Test fixtures are excluded from release content.

The original 1.0.5-beta.1 fails four of seven assertions: multiple wins, multiple losses, repeated annual scoring and mixed outcomes. Its trust and tie checks pass. The candidate passes all seven. The fixture uses GBR with FRA, PRU and AUS, not the reporter's United Netherlands save or full playset. No CMF or other gameplay mod is enabled.

All **32 engine assertions** pass: seven new notification checks plus 25 regressions covering annual rivalry scoring, reciprocal/incoming networks, trust bounds and rival cleanup. All four cumulative error-log gates pass with zero blocking errors. Machine-readable results and classifications are in `tests/mechanics/verification_rival_notifications_105.json`. Known base-game diagnostics and 16 mod variable-load warnings are reported separately; a passing gate does not mean an empty log. No live popup UI check was performed for this change.

## Local package

Candidate **1.0.5-beta.3** is under `beta/rival_notifications/`. Archive SHA-256: `114b94c2d61fdb0b9e0b9ef47dfbcee8a0bdee08a78b638486dbf43163953f80`.

Compared with local beta.2, only channel version metadata and `common/scripted_effects/spec_centre_effects.txt` differ. It retains the previously tested AI rescue correction from beta.2. The package contains 155 verified files. Generator syntax/localization checks and all 46 Python tests pass.

Stable `mod/` and published `beta/mod/` are unchanged. This candidate has not been uploaded to Workshop or promoted to stable.
