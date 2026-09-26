# Current implementation status

Complete mission remains active. The last verified remote checkpoint is
352acc47c5107480054263ee4281b63abb64800f (CI 36236901925 PASS). It contains multilingual
transcription, frozen developer settings, current-step ETA and bounded ASR checkpoints.
It also includes atomic recording/stage recovery and kernel-backed model-process ownership.
Exact bounded audio clips and optional-model excerpt results are included. Full-recording
experimental results and the separate license inventory are recorded. The verified isolated optional runtime is connected to the API and supervisor. Current changes
include source-linked audio coverage observations, frozen warning counts in exported minutes,
resource-aware long uploads and RF64 source playback. Source-first speech-act review now passes
the known H03 regression, eight new development contrasts and all 25 original text cases.

## Current evidence

- Fresh complete provided-recording browser/API/actual-model run passes offline in 1,287.96s:
  198 segments, 262 diarized turns/five clusters, 198 comparison and 57 recovery hypotheses,
  35 unreviewed candidates, 74 audio flags. Source playback passes; no browser errors, approvals
  or deliveries. See PROVIDED_AUDIO_ACCEPTANCE for timings, RAM and accuracy limitations.
- Notavra display identity and source-bracket mark now integrate UI, metadata, frozen snapshots
  and email without an internal rename. Nine synthetic multilingual document-layout cases pass;
  overflow fixed, repeated headers/page numbers and explicit empty sections added. Updated
  synthetic browser/PDF/Mailpit flow passes. See Decision 018.


- 170 backend tests pass locally with two Linux-only checks skipped; those ownership/RF64
  checks pass in Linux. Current frontend checkpoint: 12 tests and strict build pass.
- Reviewed gap insertion now has idempotent receipts, overlap/revision/authorization guards
  and mandatory transcript reanalysis. Transcript-only jobs preserve audio checks and bypass
  speech models. Actual synthetic Qwen reanalysis passes in 43.47s; the browser correction,
  reanalysis, re-review and export/Mailpit flow passes. See Decision 017 for scope and limits.
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
  The current source-first fix passes that known regression, eight EN/RO/RU/mixed-language
  contrasts and the original 25 text cases. This is not new held-out or acoustic accuracy.
  The prior 16-case development result remains historical; see Decision 015.

## Optional models

Current gap recovery independently processes diarizer-positive intervals outside the existing
transcript when both options are enabled. Bounded/checkpointed hypotheses are shown with source
context, without automatic transcript fusion. Actual app run persisted 56 hypotheses (52 nonempty
context outputs, four empty), including 115 word midpoints inside 35 flagged gaps. These are not
human-verified recovered words. Reviewed insertion is now implemented and tested; full accuracy qualification remains open;
see Decision 016. The real optional run took 144.57s; the synthetic browser workflow passes.

Pinned Parakeet and Community-1 assets downloaded; user accepted Community-1 access terms.
Model cards, CC-BY-4.0 attribution/license and checksums are recorded separately. Weights and
private recording data remain ignored. The first experimental NeMo/pyannote stack imported
successfully offline, but a 208-package OSV scan identified advisories. A patched 232-package
candidate installed with no current OSV matches and pip check passes. Two focused compatibility
patches are retained with hashes/licenses under manifests/optional-runtime-experiment.
Both models now executed successfully on a private 45-second excerpt with external networking
unavailable: Community-1 10 turns / two clusters, Parakeet one timestamped hypothesis.
Cold stage times were 194.61s and 216.95s in WSL on the NTFS workspace. This is not a latency
qualification or an accuracy score. Full-recording experiments also completed: 194 Whisper-derived comparison clips, a separate
24-window entire-timeline Parakeet pass and 262 diarized turns / five clusters. The independent
pass returned no text in three windows with substantial model-detected speech; 92 word
hypotheses fall outside Whisper clips. These are review signals, not gold accuracy results.
Actual production supervisor/adapter integration passed offline using prior real Whisper
segments: all 194 alternatives and speaker labels persisted. Availability now requires verified
Linux/WSL runtime registration. Fresh provided-recording UI processing now passes; human accuracy and target fit remain unqualified. The optional inventory now contains 233 components including pinned pip 26.2.1;
all 233 have no current OSV matches. Supplied/upstream notices are retained; release linkage
and remaining distribution-notice review are still open.
A fresh 182-package candidate plus pip removes 50 unused packages. Worker startup verifies exact
installed versions, reviewed patch hashes and pinned model files. The metadata-only API check
imports no model frameworks. Clean-runtime whole-recording diarization reproduced the same
262 turns/five clusters. See DECISIONS/010-optional-model-preparation.md.

## Audio coverage review

Optional adapters now persist possible speech gaps and empty second-recognizer observations.
The latest analysis has paginated, member-authorized playback in the UI. Minutes snapshots
freeze the warning count. A diagnostic replay of the saved private outputs found 56 possible
gaps / 102.322875 seconds and 24 empty alternatives; these are not human-confirmed omissions.
Schema 3 preserves accounts and existing records; retention cascades observations with jobs.
See DECISIONS/013-audio-coverage-review.md. Independent gap recovery remains open.

## Long audio

See DECISIONS/014-long-audio-storage-and-playback.md for exact ingestion, sparse RF64, source
playback and real silent-ASR scope. The complete mission still requires long-speech accuracy,
aggregate-memory and crash recovery work; finite hardware cannot promise failure-free operation.

## Remaining acceptance

Default byte/duration caps are removed; RF64, paged recording assembly, storage checks and
sectioned source playback are implemented. Actual 1.728 GB / 2.5-hour silence upload and all
30 real Whisper chunks passed. This does not qualify long speech or optional diarization.
Extraction checkpoints and bounded transcript state remain open.
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
