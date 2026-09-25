# Actual architecture

Compiled React assets are served by one FastAPI process. Cookie sessions and meeting membership protect
the API. SQLite WAL and short write transactions persist accounts, audio manifests, jobs, source revisions,
candidates/evidence, accepted event history, snapshots, approval and delivery outbox.

The worker owns a host-level lock. Each Whisper/LLM stage runs in a separate subprocess, with bounded
job files, leases and cancellation. Subprocess trees are terminated before subsequent stages. Raw model
outputs and input/output hashes remain local. API startup never imports speech frameworks.

Whisper runs the local large-v3 CT2 checkpoint with VAD and word times at derived 16 kHz sample offsets.
Original uploaded bytes/native metadata remain separate. The exact source-to-derived relation is a rate
conversion; recordings preserve explicit pause gap records. Browser PCM chunks are durable before ack.

Qwen emits typed events. Quote identity/revision/offsets and required field citations are checked before
persisting candidates. Conservative deterministic date validation can withhold model dates. Human review
accepts meaning; mechanically valid evidence is not semantic proof. Reducer replays by speech order,
preserves amendments and prevents proposed/cancelled items becoming active without support.

Approval checks review revision atomically and retains immutable snapshots. Explicit delivery checks
approved snapshot plus recipient group version and inserts an idempotent outbox entry. SMTP timeout after
transmission is uncertain and never automatically resent. PDFs and JSON use the same snapshot data.

Known architecture gaps are in STATUS and REQUIREMENTS_MATRIX: schema upgrades, complete recording
recovery UX, tokenizer/template budgeting/reconciliation for long meetings, optional stages, process OS
sandbox and complete multilingual UI are not implied by the successful short synthetic path.
