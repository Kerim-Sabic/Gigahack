# Execution checklist

- [x] M0/M1 baseline: preparation, real model smoke, auth and persistence.
- [x] M2/M3 baseline: capture, acknowledged recovery, sequential jobs and cancellation.
- [ ] M4/M5 acceptance: multilingual semantics and long-topic reconciliation remain open.
- [x] M6 baseline: snapshots, exports and real local SMTP integration.
- [ ] CURRENT M7/M8: finish Linux/WSL preparation and run isolated real inference; then complete localization.
- [ ] M9 acceptance: fixture browser CI, sustained target qualification and remaining matrix checks.

Current next actions: qualify the pinned Linux CUDA binaries, run the production worker in the scoped
network namespace on a synthetic queued job, record actual results, and update the Linux runbook.
A completed baseline does not mark all associated requirements VERIFIED.
