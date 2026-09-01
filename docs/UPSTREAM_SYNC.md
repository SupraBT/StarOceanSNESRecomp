# Upstream Sync Notes

This file records upstream work that was inspected and selectively lifted into
this PR branch. Keep it current when repeating that process.

## 2026-09-01

- Upstream project checked: `SupraBT/StarOceanSNESRecomp@3e8d831fdb1006d038872876267600569ba0857d`
- Upstream submodule pin inspected: `SupraBT/snesrecomp@c759806b73755b07f21e558f8b9d95a2a07a1542`
- Local snesrecomp branch updated: `mstan/snesrecomp@65769f967403d8a6911daa4991836596db6c2999`
- Local project branch updated: `mstan/StarOceanSNESRecomp@1f57f5c9eaf215776b5c0fa3fdeebef436fba223`

Lifted into `mstan/snesrecomp`:

- APU pacing snapshot/restore hooks for Star Ocean save-state determinism.
- Interpreter bridge quiescence-cache reset and LLE resume-PC setter used by
  `src/state_file.c`.
- Star Ocean battle `$00D9` wait-loop fast path.
- Star Ocean battle vblank-wait addresses and vIRQ-aware landing refinement.

Lifted into this project:

- `src/state_file.c` is now compiled into `StarOcean`.
- Save/load hotkeys and TCP save/load commands use the Star Ocean file-backed
  state path.

Intentionally not lifted wholesale:

- The upstream project's direct switch to `SupraBT/snesrecomp@c759806`. That
  commit is an unrelated one-shot import of the runtime tree. This PR keeps the
  reviewable `mstan/snesrecomp` branch and ports specific useful deltas.
- Local diagnostic `.gitignore` churn and generated/build scratch artifacts.
