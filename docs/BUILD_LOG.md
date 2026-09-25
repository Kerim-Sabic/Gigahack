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
- Latest verification: 38 backend tests, 5 frontend tests, lint, generated API types and production build pass.
- Real text extraction retains semantic failures; no full accuracy or target-hardware acceptance claim.
- Five-minute synthetic browser microphone rehearsal passed: 307.648 seconds saved; pause/resume,
  stop/flush, abrupt browser close and sealing acknowledged audio; zero page errors.
- Latest model run exposed an uncited owner; strict validation rejected it. Added conservative optional-field
  withholding, retained strict quote validation, and tested the behavior. Fresh offline-kit environment then
  completed the real browser workflow in 25.168 s. Network isolation was not enabled for this run.
- Published hardening commit 4a7e607b86289ba54758c6d59140f4bd1113e3f9 and verified remote equality.
- Qualification now explicitly fails if hardware differs or mandatory accuracy, egress or sustained thermal
  measurements remain unknown, even when a smoke workflow and memory samples pass.
- GitHub clean Ubuntu CI passed at ef1242cfa52973709a6aabd146000099b6b2f407 after fixing test-directory setup.
- Added explicitly test-only fixture browser harness; local browser/API/queue/PDF/Mailpit test passed in
  9.079 s. Production worker has no fixture switch. CI extension pending execution.
- Prepared pinned Linux CUDA llama.cpp/Mailpit and Linux Python environment without changing the host driver.
- Scoped production Linux worker passed real Whisper/Qwen processing in 51.038 s with external IPv4/IPv6
  blocked. First run on a shared NTFS SQLite database failed during a Windows-side inspection; rerun used
  native Linux database storage. Do not read a live database concurrently across OS boundaries.
- WSL peak total GPU memory exceeded target budget (9769 MiB); recorded as failure to qualify, not hidden.
- GitHub fixture browser CI passed at fb9edb004e794998f893245ab55d5ab3fdb08b1c.
- Localized operational states/errors and minutes captions; real RO/RU browser checks preserve quotations
  and persist preferences. Added recipient group selection, explicit older-version send, manual quantity/condition
  correction and reviewer issue resolution with retained provenance. 38 backend and 5 frontend tests pass.
- Browser regression now creates a second recipient group, selects it and verifies its exact address in
  Mailpit. Latest fixture workflow: 9.256 s plus successful RO/RU checks; zero page errors.

- GitHub full Ubuntu CI passed at ec3d049b9a8e45e14a55a9b8ebfcf51b037638e3 (run 36163082294).
- Added operator metadata/access/delete controls and retained candidate amendment history. Fixed date
  cache identity and stale relative-deadline acceptance; excluded history is not resurrected by edits.
- Added admin-only safe account directory, explicit failed-mail retry and verified SMTP TLS/authentication.
  No new external dependency/model. 44 backend tests, 5 frontend tests, lint and strict build pass.
- Expanded browser assertions exposed accessible-label ambiguity in the role selector and amendment
  textarea; explicit labels were added. Test tab selector corrected to the actual displayed label.
- Expanded fixture browser flow passed in 12.175 s, with metadata edit, account creation/access grant,
  retained amendment reason, actual PDF and Mailpit receipt. RO/RU persistence/source checks also pass.
- Final operator browser regression after checkbox/selection fixes passed in 9.889 s, zero page errors.
