# Status

Current stage: complete synthetic local workflow runs; acceptance gates remain open.
Development hardware: two RTX 5080 16 GB GPUs, 128 GiB RAM. Target RTX 3070 Ti Laptop
8 GB / 24 GB is not connected and has NOT RUN.

- 80 backend/domain/recovery/fault tests and 6 frontend tests pass; lint and strict build pass.
- Real Linux browser → upload → FFmpeg → Whisper → Qwen → review → immutable minutes → PDF
  → Mailpit passed in a loopback-only namespace. IPv4/IPv6 external probes return ENETUNREACH
  before and after; all four services share the namespace; verified cleanup leaves no owned services.
  Browser workflow 56.394 s; total rehearsal 84.589 s. Windows host is outside this boundary.
- Latest fixed-corpus text evaluation: 23 PASS, 2 FAIL (T01 date correction; T10 missing unit),
  5 NOT RUN (four audio cases and one stateful case). These are development checks, not held-out
  multilingual accuracy. Separate canonical overlap/replay and mail idempotency tests pass.
- Every generation pass checks its rendered token budget, persists raw responses before parsing,
  and constrains citations to literal source spans. Bounded preceding context supports topic proposals;
  manual topic linking/splitting retains original amendment history. Semantic review remains mandatory.
- Queue identities include implementation/configuration hashes; changed implementations cannot silently
  reuse or publish old queued work. Doctor checks real assets, packages, browser, GPU, space and ports.
- Prepared revisions/checksums/license notices are tracked. Re-preparation rejects changed pinned assets.
  No new dependency, model or framework was introduced in this milestone.
- Stable Linux process start ticks prevent clock changes from breaking owned-process cleanup. Windows
  retains creation-time identity. Unrelated occupied ports/processes are never terminated.
- Synthetic microphone: 305-second capture and browser-loss recovery passed previously; physical device
  not measured. Windows offline kit preparation/no-index install and real workflow passed previously;
  current source changes have not yet been repackaged into that kit.
- Latest Linux peak total GPU 0 memory 9769 MiB exceeds the requested 7 GiB gate. Shared desktop activity
  is included. This is not target-device resource qualification or isolated process VRAM attribution.

Services: API/UI 8765, Mailpit UI 8025, SMTP 1025; extraction server 8081 only while needed.
Latest pushed checkpoint before this milestone: 18256f3987e4adc6ec9ec03a392462b05d7acb4e;
Previous checkpoint GitHub CI passed; current milestone CI is being checked.

Next: long-window reconciliation and multilingual audio acceptance, clean kit refresh,
native translation review, optional model preparation,
physical microphone and sustained target-laptop measurements. See all 39 rows in REQUIREMENTS_MATRIX.md.

Fresh remote clone installation and real Windows workflow passed (25.257 s), using existing pinned
prepared assets with a new environment/account. Format validation, T22 replay/deduplication, actual
200% browser zoom/viewer controls and the real T26 silence branch now have executable passing checks.
Latest verified CI: 2d6c0ec, run 36171610910.
