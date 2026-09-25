# Current implementation status

Complete mission remains active. The last verified remote checkpoint is
0046c2711e17290c6ae15aac0b7c65b71e9f3bf3 (CI 36191562041 PASS). It contains multilingual
transcription, frozen developer settings, current-step ETA and bounded ASR checkpoints.
It also includes atomic recording/stage recovery and kernel-backed model-process ownership.
Exact bounded audio clips and optional-model excerpt results form the next checkpoint.

## Current evidence

- 143 backend tests pass locally with one Linux-only check skipped; that check and the actual
  child cleanup test pass in Linux. Last frontend checkpoint: 10 tests and strict build pass.
- Hard-killing a model stage now terminates its owned child through Windows Job Objects or
  Linux parent-death binding; the actual tests preserve an unrelated running process.
  New CUDA silence inference passes in 7.00s. Full application crash rehearsal remains open.
- Actual supplied private recording: original Whisper pass 152.94s / 205 segments; per-window
  multilingual pass 184.49s / 176 segments; chunked pass 166.71s / 194 segments. Romanian
  passages appear alongside Russian. No reference transcript, participant identities or
  date/timezone were supplied, so none are invented and accuracy is not scored as perfect.
- Actual ASR-child termination/retry reused one durable chunk and finished three chunks.
  This is not yet whole-app crash recovery or arbitrary-length qualification.
- New stage cache validation rejects corrupt output/receipt pairs. Inputs, outputs, receipts
  and normalized audio publish atomically after fsync. Recording finalization decodes outside
  the database writer transaction; same-request retry is idempotent and chunks survive failure.
- A monotonic inactivity watchdog replaces the fixed two-hour stage cutoff. It observes real
  work counters or owned-process CPU work; this does not detect every logical busy loop.
- Actual changed-worker CUDA silence check: 6.19s, zero segments/candidates/deliveries.
  Synthetic fixture browser-to-PDF/Mailpit, RO/RU persistence and 200-percent DOM checks pass.
  The fixture tests workflow and includes a boundary-review notice; inference is test-only.
- Full original semantic attempt 19: 25/25 text cases passed; development 16/16 passed.
  Held-out attempt 21: 5/6 passed; H03 incorrectly accepted a tentative Russian date change.
  These prior model results are not fresh inference of every later runtime change.

## Optional models

Pinned Parakeet and Community-1 assets downloaded; user accepted Community-1 access terms.
Model cards, CC-BY-4.0 attribution/license and checksums are recorded separately. Weights and
private recording data remain ignored. The first experimental NeMo/pyannote stack imported
successfully offline, but a 208-package OSV scan identified advisories. A patched 232-package
candidate installed with no current OSV matches and pip check passes. Two focused compatibility
patches are retained with hashes/licenses under manifests/optional-runtime-experiment.
Both models now executed successfully on a private 45-second excerpt with external networking
unavailable: Community-1 10 turns / two clusters, Parakeet one timestamped hypothesis.
Cold stage times were 194.61s and 216.95s in WSL on the NTFS workspace. This is not a latency
qualification or an accuracy score. Full-recording runs have started; complete API/UI integration
and target fit remain unqualified, and application availability remains disabled.
See DECISIONS/010-optional-model-preparation.md.

## Remaining acceptance

Arbitrary-length upload/recording support still needs size/duration/container limits replaced
with resource-aware handling; extraction checkpoints and bounded transcript state remain open.
Full-app crash/fencing, final corrected real-model evaluation, multilingual human assessment,
long-distance reconciliation, retention/settings, branding/UI/PDF finishing, final demo,
current-source packaging and final offline qualification remain required.

Development hardware is two RTX 5080 16 GB GPUs and 128 GiB RAM. The RTX 3070 Ti Laptop
8 GB / 24 GB is unavailable; fit, thermals and latency are not verified. Shared total GPU
readings are not application VRAM attribution. Physical microphone and native language review
remain separate gates. Do not repeat the rejected hardlinked-kit action or mutate the old kit.

Details: REQUIREMENTS_MATRIX.md, CONTINUATION_PLAN.md, CONTINUATION_RESULTS.md,
PROVIDED_AUDIO_ACCEPTANCE.md and DECISIONS/008 through 011. Earlier status snapshots are retained
in history/STATUS-through-68853d8.md; their counts/claims belong to those revisions.
