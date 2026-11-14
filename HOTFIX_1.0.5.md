# Stable 1.0.5 and Morgenroete compatibility 1.0.0

Published November 14, 2026. Stable now contains the tested beta gameplay and UI; beta is aligned as 1.0.5-beta.1. Balance constants are unchanged.

- Tied Exchange contests no longer retain an old win/loss result.
- Bank tooltips use current loan balances.
- Confidence-loss accounting respects the zero floor.
- Surrender applies the missing confidence penalty.
- Individual goods no longer have Open Finance. Sidebar and journal navigation remain.

The new Morgenroete bridge integrates instruments, uranium and publications while retaining the current Finance window and electricity. It defines the missing instrument-workshop throughput modifier type. It replaces the obsolete third-party bridge.

## Validation

45 Python tests and 9 CMF source tests pass. Stable gameplay/UI bytes match tested beta6; CMF rebuild is byte-identical to published 1.0.1. The Morgenroete release changes metadata only relative to the tested candidate's generated patch files.

The bridge inherits 24 added-goods and 52 collapse/recovery engine assertions. Nine new migration assertions pass on a CMF+Morgenroete save created without SM; a test fixture supplied existing industries. Migration completed with zero blocking SM/test diagnostics. This does not establish migration from the obsolete bridge or the reporter's full modlist.

Final live UI used CMF, Morgenroete 2.9.0e, stable 1.0.5, this patch, and CMF compatibility 1.0.1. All three goods rendered their icons, names, interest/risk controls and native panels without the removed button. Finance/native transitions and the instrument restraint eligibility tooltip passed. Journal Speculation selection is retained from byte-identical beta6 runtime evidence. Final UI logs: zero blocking errors, 253 engine/upstream messages and 16 variable-load warnings.

An initial unpatched MR+SM seed attempt crashed on January 2 with an unsymbolized access violation. Its cause is unresolved; this release does not claim to fix it. The clean MR-only seed, patched migration, and production UI completed. Long campaigns and the full reported modlist remain untested.

Machine-readable evidence and upload receipts: `tests/mechanics/verification_release_105.json`. Raw logs/screenshots remain under `runs/morgenroete/`; older evidence and archives are immutable.

## Published packages

| Package | SHA-256 |
| --- | --- |
| Stable 1.0.5 | `fea557a88a69f8f95520265a92d6621da76ddf5d6171bfd7aa781fa5d53c321f` |
| Beta 1.0.5-beta.1 | `4150e11eb99cb017a5772443639d12edab7b7f4300360f3a1e9e1d61c98eb58a` |
| Morgenroete compatibility 1.0.0 | `b95c23566b90fd9871948d7e95497cd5407ede69060d081266e39c0b8a43cb22` |

Steam verified public visibility, nonzero content and previews, and exact description hashes for all three uploads. The CMF listing received a description-only update. Stable, beta and CMF descriptions link new item **3839705018**. Its required Workshop item is Morgenroete **2889925770**; the description specifies the remaining load order without forcing both SM channels.

Load CMF → Morgenroete → one SM channel → our Morgenroete compatibility → our CMF compatibility. Disable the old third-party Speculative Markets+Morgenroete patch.
