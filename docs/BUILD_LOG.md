# Build log

## 2026-09-25 — Windows development environment

- Verified GitHub repository had no refs; cloned, initialized main. No applicable pre-existing AGENTS.md.
- Found Python 3.12, Node 22, FFmpeg, WSL2; two RTX 5080 16 GB GPUs and 128 GiB host RAM.
  About 34 GB disk free before preparation. Target laptop not connected.
- Resolved project-local dependencies; prepared Whisper large-v3 CT2 and Qwen3.5-4B Q4_K_M
  at immutable revisions with file hashes. Downloaded pinned llama.cpp and Mailpit tools.
- Implemented SQLite schema, local account setup, membership, CSRF, upload/PCM chunks,
  jobs, subprocess inference, source citations, reducer, review, snapshots, PDF and SMTP outbox.
- `python -m pytest -q --basetemp .runtime/test-temp`: initially 10 passed; now 19 passed.
  Initial default temporary directory was inaccessible; scoped test directory fixes that environment issue.
- `npm run build --prefix apps/web`: passes after pinning TypeScript 5.9.3 to support openapi-typescript.
- `python -m ruff check services scripts tests`: passes after formatting/import fixes.
- Real Whisper synthetic 9.667-second English clip: 15.251-second cold stage.
- Initial extraction produced an incorrect date and missing field citations. Changed prompt and
  strict output fields, then added independent date validation. Preserved failures in local smoke artifacts.
- Browser test first exposed upload controls disappearing when details auto-collapsed; fixed.
  A later keyboard test assumption failed; corrected focus setup. Full browser workflow passed in 21.584 s:
  real models, review, approval, PDF, SMTP acceptance, Mailpit receipt, widths and focus.
- Initial commit f1998b75e1f88fa12404228da52cee49ea18bbc4 pushed; git ls-remote verified exact match.
  Git CLI credentials work despite gh CLI reporting unauthenticated.
- Running all 30 adversarial text inputs through actual local Qwen. Results remain separate from
  audio qualification and require semantic checks; no assumed passes.

## Follow-up hardening

- Added versioned SQL migrations and tested existing-account preservation.
- Added actual worker cancellation, lease recovery, disk-write failure and one-retry OOM mechanism tests.
- Split SMTP from GPU admission; added admin settings, glossary versioning, recipient allowlists,
  optional capability controls, manual corrections and confirmed meeting deletion.
- Fixed correction evidence links and preservation of unchanged field citations during source replay.
- Added capture queue backpressure/retries, flush acknowledgements and interrupted-recording recovery UI.
- Added scoped unprivileged Linux namespace launcher and executed IPv4/IPv6 isolation probe.
- Added Windows offline-kit preparation; actually installed all pinned wheels with --no-index.
- Latest verification: 32 backend tests, 4 frontend tests, lint, generated API types and production build pass.
- Real text extraction retains semantic failures; no full accuracy or target-hardware acceptance claim.
- Five-minute synthetic browser microphone rehearsal passed: 307.648 seconds saved; pause/resume,
  stop/flush, abrupt browser close and sealing acknowledged audio; zero page errors.
- Latest model run exposed an uncited owner; strict validation rejected it. Added conservative optional-field
  withholding, retained strict quote validation, and tested the behavior. Fresh offline-kit environment then
  completed the real browser workflow in 25.168 s. Network isolation was not enabled for this run.
