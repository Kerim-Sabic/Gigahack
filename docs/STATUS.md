# Status

Current stage: real local workflow implemented; acceptance gates remain open.

Windows development host: two RTX 5080 16 GB GPUs, 128 GiB RAM, Python 3.12.10.
Target RTX 3070 Ti 8 GB / 24 GB laptop is not connected and has NOT RUN.

- 32 backend/domain/recovery/fault tests pass; 4 frontend tests pass; strict build and lint pass.
- Real synthetic audio runs through Whisper, Qwen, evidence review, immutable minutes, PDF and Mailpit.
- Model revisions/checksums, package lockfiles, copied license notices and provenance are tracked.
- Schema upgrade, disk-write failure, child cancellation, OOM retry mechanism, backup/restore,
  stale review and uncertain SMTP behavior have tests. Real GPU OOM is not induced.
- Actual 30-input text extraction run produced 28 structurally valid outputs and 2 validation failures.
  Structural validity is not semantic correctness. Known owner/date/category/reconciliation errors remain.
  Acoustic/context-only fixtures in that earlier run are not valid audio qualification.
- Synthetic Chromium microphone captured 305 seconds (307.648 seconds saved), pause/resume,
  stop/flush and abrupt browser-loss recovery passed with no page errors. Physical device not measured.
- Windows offline kit preparation and no-index wheel installation ran successfully. Fresh kit application workflow also passed (25.168 s). Complete disconnected
  processing, Windows egress enforcement and Linux deployment are not verified.
- Scoped WSL network namespace probe blocked IPv4/IPv6. This does not prove host-wide isolation.
- Latest memory gate failed honestly on the shared development host: total RAM peaked at 31.27 GB
  including unrelated processes; peak total GPU 0 memory was 4880 MiB. Target hardware remains unqualified.

Services: API/UI 8765, Mailpit UI 8025, SMTP 1025; model server 8081 only during extraction.
Initial milestone f1998b7 pushed and verified; follow-up hardening milestone is being prepared.

Next release gates: multilingual semantic accuracy and long-window reconciliation; complete localization;
physical microphone failure/long recording; optional model assets and qualification; complete offline
runtime rehearsal; target-laptop sustained performance. See REQUIREMENTS_MATRIX.md for all 39 requirements.
