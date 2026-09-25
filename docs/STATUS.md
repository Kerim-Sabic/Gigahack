# Current ASR recovery continuation

- Committed multilingual checkpoint 0b9a2a4b86b18a832b1597e467753adbaee22dff is remote-verified;
  GitHub CI 36186616751 passed.
- Bounded PCM reads and durable ASR checkpoints implemented. Actual supplied recording
  completed in three chunks, with boundary-review flags and retained source offsets.
- Actual ASR-child termination and same-job retry reused one saved chunk and completed.
  This does not yet qualify whole-app crash recovery or arbitrary-length recordings.
- Optional isolated environment installation and pip check completed; imports and real
  inference verification are next.
- See DECISIONS/009-asr-checkpoints.md for measurements, tests and remaining limits.

# Current multilingual continuation

- Supplied private recording processed by real Whisper twice. Per-window multilingual run
  preserves Romanian passages alongside Russian; no reference WER or speaker score available.
  See PROVIDED_AUDIO_ACCEPTANCE.md. No meeting date/timezone or identities were invented.
- Central frozen inference settings, source-language ASR, current-phase progress/ETA and
  optional complete-segment comparison coverage implemented. 127 backend / 10 frontend
  tests, strict build and lint pass. Synthetic fixture browser/PDF/Mailpit and RO/RU/zoom
  checks pass in an isolated Linux namespace; actual models are not used by that fixture.
- Parakeet and Community-1 model snapshots downloaded; gated access accepted. Optional
  isolated dependency installation still running. Their actual inference is NOT VERIFIED.
- Long-file bounded checkpoints, full-job ETA, H03, branding/UI/PDF finishing, packaging,
  disconnected optional inference and target-laptop qualification remain open.

# Current continuation checkpoint

Current stage: generalize and verify semantic corrections before target/deployment readiness.

- T01/T10 root causes fixed; full original actual model run `1790362810483903700`:
  25 text-model PASS, 0 FAIL, 5 outside text scope. Original gold assertions unchanged.
- Earlier semantic checkpoint 69e2684 passed 95 backend tests; current counts are below.
- Structured literal quantities preserve amount/unit/scope/raw/evidence. API review/snapshot
  and human replacement tests pass. Quantity now appears in the minutes template; real
  UI/PDF replay passed; final document polish remains pending.
- Extended semantic experiments are ongoing; later prompt attempts introduced regressions.
  Current 768-token bounded reasoning candidate passes full original attempt 19 (25/25 text)
  and development attempt 20 (16/16). The first held-out run is 5/6: H03 wrongly accepts a tentative Russian date change.
  Five original audio/stateful cases remain outside the text run.
- Working tree: 109 backend tests and 8 frontend tests pass; strict frontend build/lint pass.
- Resource attribution committed at 029f35de92f9cd0f06445cf82ae7e56fdbcd1895; remote verified,
  CI run 36180243770 passed. Real CUDA silence with sampled resource receipt passed.
  Windows per-process GPU memory remains unavailable; target laptop remains unobserved.
- Versioned template forms/API/snapshots and group suggestions are implemented and tested.
  Captured T10 replay passes real UI/JSON/PDF with a configured template; full Mailpit fixture
  rerun passes through actual Mailpit receipt (test-only inference). See TEMPLATES.md.
- Template checkpoint 750944e remote verified; GitHub CI 36181262970 passed.
- Complete mission remains active. See CONTINUATION_PLAN.md and CONTINUATION_RESULTS.md.
- No new dependencies/models adopted. No package deletion, links or kit mutation performed.
- No persistent app services currently started; completed evaluation/browser services cleaned up.

## Earlier first-build checkpoint (historical)


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
Latest implementation checkpoint: fc2cdd949c4071eb9a54d7760d1fb1c90c5a8a65;
remote hash verified and full GitHub CI passed (run 36173731710).

Next: long-window reconciliation and multilingual audio acceptance, clean kit refresh,
native translation review, optional model preparation,
physical microphone and sustained target-laptop measurements. See all 39 rows in REQUIREMENTS_MATRIX.md.

Fresh remote clone installation and real Windows workflow passed (25.257 s), using existing pinned
prepared assets with a new environment/account. Format validation, T22 replay/deduplication, actual
200% browser zoom/viewer controls and the real T26 silence branch now have executable passing checks.
Latest verified CI: 2d6c0ec, run 36171610910.

Current Windows deliverable-kit refresh remains incomplete. Automatic approval review rejected the
hardlinked-kit creation with only "blocked by policy". A separate copy needs 9.285 GB of assets;
11.0 GB was free, which would leave less than the required 5 GiB operating reserve. No replacement
kit or destructive cleanup was performed. Existing prepared assets and the tested source remain intact.
