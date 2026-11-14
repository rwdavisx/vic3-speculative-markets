# 1.0.3: boom notification crash

## Cause and fix

Victoria 3 1.15.1 can lose the notification's saved scope while resolving a string chosen by `SelectLocalization`. The old banking/overbuilding sentences looked up a goods key through that missing scope inside a country-variable expression. An isolated run of the released 1.0.2 beta reproduced the exact `SCOPE.sGoods('spec_note_good').GetKey` error followed immediately by Windows access violation `C0000005`.

The fix snapshots the three numeric details in the event chain and selects the banking/overbuilding message variant in script before posting. Localization expands those sentences directly in the notification context. Every good resets all three values before optional overrides, so absent values or simultaneous goods cannot inherit another event's details. Original notification IDs remain defined for saved notifications; their unsafe detail lookup is removed. No economic calculations or balance values changed.

The first candidate (1.0.3-beta.1) avoided the crash but still rendered blank multipliers. It failed runtime verification and was never published. The corrected candidate is **1.0.3-beta.2**.

## Validation

- 33 root unit tests and 9 CMF builder tests passed; generated syntax/localization checks passed. All ten translated languages regenerated without missing translations.
- Isolated beta-only run `runs/notification_scope_repro/beta_103_r2`: Britain, January 1 to February 18, 1840, audio and notifications enabled. Observed correct grain correction (x2.00 / x1.50), coal collapse (x1.80 / x2.00), missing-value wood correction without extra sentences, and simultaneous grain bust (x2.25 / x1.25) and steel collapse (x1.75 / x2.50). All three severity paths survived; no notification-scope errors or crash.
- CMF run `runs/notification_scope_repro/beta_103_r2_cmf`: CMF, beta, regression fixture, compatibility patch last. Ran to June 25, 1840. Correct initial multipliers observed; additional scheduled cases cover bank-only, overbuilding-only, exact threshold, and feverish warning. No notification-scope errors or crash. Not every additional toast was individually photographed. Fixture debug markers were not emitted in these runs; the runtime conclusion relies on observed notifications, elapsed game dates, fixture sequence, and log review.
- Existing base/profile diagnostics remain, including a duplicate Financial Markets journal-entry warning in the old baseline save. These are not a claim of an entirely clean game log or proof against unrelated crashes.
- Stable's 154 non-metadata files match the tested beta byte for byte. The only shipping changes from 1.0.2 are message definitions, notification posting blocks, localization, and version metadata. Finance GUI files are unchanged.

## Artifacts

Successful public Workshop uploads were observed and verified in order: Beta 1.0.3-beta.2 at **2026-11-14 04:46:24 UTC**, then stable 1.0.3 at **04:48:40 UTC**. Valve returned success for both; title, description hash, and visibility were re-queried successfully. Local receipts are retained under `workshop/upload_receipts/`. CMF patch 1.0.1 remains unchanged; its parent GUI hashes still match.

- Beta `Speculative_Markets_Beta_1.0.3-beta.2.zip`: SHA-256 `48a45d78851fac64a7c43b68bccef3e5f293617aa434073bf85bc2eaacf0b185`.
- Stable `Speculative_Markets_1.0.3.zip`: SHA-256 `ef3f2e4bd700eacd45658f78c4bb90bb86aa5096e5bc424b8513c54a8e4503ed`.
- Original crash evidence is retained locally under `runs/notification_scope_repro/profile_scheduled/crashes/victoria3_01261013_232432/`. Previous archives were not overwritten.

## Reporter log triage

The [Steam report](https://steamcommunity.com/workshop/filedetails/discussion/3831434383/572679917415785486/) describes Japan in 1838 with CMF, Tech & Res, Beta, the CMF patch, TechnocracyRebalance, Dense UI, and Waifu Britannica. Its [full log](https://pastebin.com/raw/8HEmRYqU) ends with the same notification scope error. We reproduced that failure without CMF, establishing that CMF is not required to trigger it.

Other `spec_` warnings in that log are localization-only ranking/pledge variables (the engine explicitly excludes localization when checking usage) and removal of the optional debug-only `spec_expo_raw` variable. The `gui/market_panel.gui:960` error matches `not_yet_initialized` in the installed Dense UI & Others file; this mod and the CMF patch do not ship that file. Numerous WB/ztr script and texture errors belong to other mods. The log also records loading a save missing the stable channel ID, consistent with changing to Beta's distinct ID; do not enable both channels to silence that warning. No additional confirmed Speculative Markets failure was established from this report.
