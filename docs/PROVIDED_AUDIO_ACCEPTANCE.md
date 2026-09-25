# Supplied recording and reliability continuation

User steering after checkpoint bb8c7ce: exercise the supplied recording locally; finish
Parakeet and diarization; add visible progress and estimated completion time; centralize
developer controls for model/context/resource settings; support long files with recoverable
processing. Keep the existing architecture and the full original continuation mission.

The user has no meeting date/timezone, participant list or reference transcript. Do not
infer the date from a file timestamp or current date, invent identities, or claim measured
WER/speaker accuracy without a reference. Original recording and derived private content
remain outside Git and public demonstration material. Runtime artifacts keep source hashes.

Observed input container: ALAC in M4A, 48 kHz stereo, 702.635 seconds. Initial production
Whisper-only check completed: 205 segments in 152.94 seconds, initial language ru.
This is successful execution, not measured transcription accuracy. No approval or email
is requested for this recording. A separate per-window multilingual comparison completed in 184.49 seconds with 176
segments; 47 contain Latin-script text, including Romanian passages. The baseline had
zero Latin-script segments. This is an observable transcription difference, not a gold
accuracy score. Initial detected language remains ru in both runs.

Local private runs: baseline `1790366639800846300`; multilingual `1790368053176477000`.
The latter retained observed progress through 702.549 seconds of decoded audio.
127 backend tests and 10 frontend tests pass; strict frontend build passes. The first
backend invocation hit temporary-directory permissions; a fresh repository-local test
directory passed. No recordings/transcripts are tracked.

## Required implementation and verification

- Unknown meeting date must be expressible; relative dates remain unresolved until supplied.
- ASR, optional second recognizer and diarization run sequentially with pinned local assets.
  Unknown speakers and overlap stay explicit. A speaker cluster is not a person's identity.
- Model access, dependencies and actual successful inference must be checked independently.
  Community-1 initially returned GatedRepoError. The user accepted publisher terms and
  the pinned local download subsequently succeeded; actual inference remains pending. Never bypass the access restriction or silently use cloud diarization.
- Progress must report observed work units/stages. ETA is explicitly an estimate, based on
  measured throughput, and unavailable during startup or insufficient sampling. Do not
  fabricate a linear percentage or show completion before durable publication.
- Developers can change context, token budgets, batching, stage/window sizes and prepared
  model selections in one validated configuration. Freeze effective settings in each job,
  include them in cache identity, and document target-memory consequences.
- Long files need bounded memory, durable chunk checkpoints, cancellation, safe retry and
  graceful disk/resource errors. A fixed two-hour stop cannot satisfy this new requirement.
  No implementation can guarantee unlimited storage or no crashes; preserve completed work
  and explain recovery. Never omit windows, silently truncate content or resume stale output.
- Verify the actual supplied audio end to end and retain failures. Without gold, successful
  execution and consistency review are not perfect transcription or diarization accuracy.

The semantic H03 tentative-date failure from the first held-out text run remains an open
acceptance item. New recording work does not erase it or the mandatory identity/UI/PDF,
packaging, recovery, offline and target-laptop requirements.

## Code-switching acceptance

Preserve source speech in Russian, Romanian and English, including switches inside one
sentence. Whisper performs per-decoding-window language detection with transcription,
never translation. Its initial language result is not a language tag for every word.
Cyrillic/Latin script differences alone cannot establish Romanian versus English.
Compare independent hypotheses; retain disagreements and source audio for review.
Do not claim accurate word-level language identification without annotated recordings.
