# Requirements matrix

Environment: Windows development host; target RTX 3070 Ti qualification not run.

| ID | Requirement | Status | Implementation | Evidence / prerequisite |
|---|---|---|---|---|
| R01 | Clean clone → documented preparation → app starts through one implemented command | NOT STARTED | — | Not run |
| R02 | Actual GPU/RAM/disk/dependency/model doctor with actionable failures | NOT STARTED | — | Not run |
| R03 | Reproducible model preparation, immutable revisions/checksums, license manifest; offline startup | NOT STARTED | — | Not run |
| R04 | Local first-run account; authentication, logout, role and per-meeting authorization | NOT STARTED | — | Not run |
| R05 | Persisted meeting metadata, participants, classification, timezone and output language | NOT STARTED | — | Not run |
| R06 | Supported-file upload with bounded decoding, type/duration/size checks and durable original | NOT STARTED | — | Not run |
| R07 | Real microphone recording, acknowledged chunks, pause/stop, visible gaps and recovery | NOT STARTED | — | Not run |
| R08 | Durable job queue, leases, restart recovery, cancellation and idempotent retry | NOT STARTED | — | Not run |
| R09 | Single GPU admission, subprocess cleanup, bounded memory and truthful fallback behavior | NOT STARTED | — | Not run |
| R10 | Real local multilingual ASR with source-relative times and preserved raw output | NOT STARTED | — | Not run |
| R11 | Transcript search, word/segment playback, pagination and revision history | NOT STARTED | — | Not run |
| R12 | Speaker labeling/manual roster mapping; real optional diarization with capability status | NOT STARTED | — | Not run |
| R13 | Real optional second-ASR adapter; disagreement evidence; no silent transcript fusion | NOT STARTED | — | Not run |
| R14 | Real 4B local LLM extraction with token budgets, JSON constraints and parse validation | NOT STARTED | — | Not run |
| R15 | Decision/action separation; proposal, confirmation, amendment, rejection, cancellation/reopening | NOT STARTED | — | Not run |
| R16 | Field-level source references with meeting/revision/quote/offset integrity | NOT STARTED | — | Not run |
| R17 | Unknown owner/date, ambiguous numbers, conditional actions and overlap remain explicit | NOT STARTED | — | Not run |
| R18 | Subject reconciliation and semantic duplicate handling across overlapping windows | NOT STARTED | — | Not run |
| R19 | Review queue with accept/correct/exclude, human provenance and conflict detection | NOT STARTED | — | Not run |
| R20 | Transcript edits invalidate dependencies and stale approvals without erasing history | NOT STARTED | — | Not run |
| R21 | Complete review workspace with field-specific evidence and amendment timeline | NOT STARTED | — | Not run |
| R22 | Deterministic professional minutes, real PDF and structured JSON exports | NOT STARTED | — | Not run |
| R23 | Immutable snapshots; atomic approval revision check; no automatic publication | NOT STARTED | — | Not run |
| R24 | Explicit allowed recipients; separate send command; transactional outbox and honest SMTP state | NOT STARTED | — | Not run |
| R25 | Real local Mailpit receipt through the UI flow; configurable internal SMTP adapter | NOT STARTED | — | Not run |
| R26 | English/Romanian/Russian UI localization, source-language preservation and font coverage | NOT STARTED | — | Not run |
| R27 | Meeting/action views, templates/settings, useful empty/loading/error states | NOT STARTED | — | Not run |
| R28 | Keyboard, focus, zoom and responsive-layout verification on target sizes | NOT STARTED | — | Not run |
| R29 | Authorized media/SSE/export/search, CSRF/Origin defenses, safe uploads and rendering | NOT STARTED | — | Not run |
| R30 | Runtime external calls prevented by scoped policy; offline evidence status truthful | NOT STARTED | — | Not run |
| R31 | Prepared offline package, disconnected startup/run, scoped networking test/runbook | NOT STARTED | — | Not run |
| R32 | Consistent backup and demonstrated restore; documented retention/deletion behavior | NOT STARTED | — | Not run |
| R33 | Fast CI plus separate real-inference and target-hardware qualification commands | NOT STARTED | — | Not run |
| R34 | Thirty adversarial cases encoded with exact expected results; outcomes not fabricated | NOT STARTED | — | Not run |
| R35 | Fault tests: disk/mic loss, worker crash, malformed model output, stale edit, SMTP timeout | NOT STARTED | — | Not run |
| R36 | Synthetic demo with real processing and evidence; no hidden canned results | NOT STARTED | — | Not run |
| R37 | Honest stage timing, peak-memory and accuracy reports tied to exact model/config/input | NOT STARTED | — | Not run |
| R38 | Repository notes, lockfiles, setup/recovery/operator docs match the actual implementation | NOT STARTED | — | Not run |
| R39 | Coherent commits and verified remote push; otherwise exact local commit and access blocker | NOT STARTED | — | Not run |
