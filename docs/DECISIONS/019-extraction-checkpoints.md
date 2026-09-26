# Durable extraction work units

The complete supplied-recording run spent 900.59 seconds in extraction. Previously a
worker interruption discarded completed extraction/reconciliation work and repeated it.
Keep the existing model, prompts and reducer; checkpoint validated source groups and final
reviewed model events inside the private job directory.

The namespace includes source text/revisions, date/timezone, frozen configuration, resolved
LLM settings, implementation identity, actual model and executable hashes, and canonical
audio identity. Each event key also chains the preceding validated events: changing earlier
context invalidates later work. Volatile meeting/job status is deliberately excluded so lease
recovery can resume the same inputs. Cached units are checksum-checked, schema-validated and
checked against current literal source evidence before reuse. They never authorize acceptance,
approval or delivery. Checksums detect corruption, not a malicious writer who controls both
data and checksums.

Publication uses existing reserve-aware atomic/fsynced writes. Units larger than 32 MiB are
recomputed instead of being truncated; oversize cache files are not loaded. Raw replies stay
in attempt journals and completed checkpoints. The stage output references its raw journal
instead of duplicating all replies into another aggregate array. Full transcript, event and
reconciliation state still grow with meeting length; this is not bounded whole-pipeline RAM.

Five focused tests cover restart, changed sources/settings/prior context, corrupt or invalid
evidence, atomic-write failure, and model cleanup when the raw journal cannot be created.
The latter exposed a cleanup gap; journal creation now executes inside model cleanup scope.
The backend suite passes 175 tests, with two Linux-only checks skipped on Windows.

Actual Linux/WSL operator rehearsal `python -m scripts.mom qualify-recovery` passes in
142.16 seconds (run `app-crash-1790422794049692413`). It kills API and supervisor after one
completed event, observes three owned descendants exit while an unrelated sentinel survives,
restarts both services, recovers the same job on attempt two and reuses one group and one
event. The browser returns to awaiting review with two candidates and no accepted events,
snapshots or deliveries. External IPv4/IPv6 are blocked before and after the run.

This uses actual Qwen with explicitly seeded synthetic Russian text over silence, including
the known tentative-date regression. It does not establish ASR accuracy, physical power-loss
durability, arbitrary-length completion or the unavailable 8 GB laptop's resource budget.
No dependency, model, prompt, expectation or private-recording approval was added or changed.
