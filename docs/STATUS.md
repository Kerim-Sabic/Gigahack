# Status

Current stage: real local workflow implemented; acceptance gates remain open.

Windows development host: two RTX 5080 16 GB GPUs, 128 GiB RAM, Python 3.12.10.
Target RTX 3070 Ti 8 GB / 24 GB laptop is not connected and has NOT RUN.

- 44 backend/domain/recovery/fault tests pass; 5 frontend tests pass; strict build and lint pass.
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
- Real Whisper/Qwen processing completed under a WSL namespace with IPv4/IPv6 blocked (51.038 s).
  API/PDF/SMTP and Windows-host isolation remain outside that scoped proof.
- Latest memory gate failed honestly on the shared development host: total RAM peaked at 31.27 GB
  including unrelated processes; peak total GPU 0 memory was 4880 MiB. Target hardware remains unqualified.

Services: API/UI 8765, Mailpit UI 8025, SMTP 1025; model server 8081 only during extraction.
Hardening milestone 4a7e607b86289ba54758c6d59140f4bd1113e3f9 pushed; exact remote hash verified.
A follow-up tightens qualification failure reporting and records the final checks.

Next release gates: multilingual semantic accuracy and long-window reconciliation; native review of translations;
physical microphone failure/long recording; optional model assets and qualification; complete offline
runtime rehearsal; target-laptop sustained performance. See REQUIREMENTS_MATRIX.md for all 39 requirements.

UI language persistence and recipient errors passed real Romanian/Russian browser checks; evidence
quotes remain unchanged. Conditions/values and explicit issue resolution now support human amendments.

Operator metadata/access/delete controls and retained amendment timeline are implemented.
Date edits invalidate job context; stale relative deadlines cannot be accepted unchanged.
Explicit safe failed-mail retry and verified internal SMTP TLS/authentication have regression tests.
