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
  the pinned local download subsequently succeeded; excerpt inference later passed (see below). Never bypass the access restriction or silently use cloud diarization.
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

## Optional excerpt inference and exact clip preparation

Private run optional-diarize-1790371548383828053 processed source seconds 300–345 inside
an isolated Linux network namespace: 10 speech turns, two clusters, stage 194.61s,
peak process-tree RSS 2,619,744,256 bytes. No reference speaker labels exist, so diarization
error rate is not measured. Cluster labels do not identify people.

Private run optional-parakeet-1790371786397743852 processed the same excerpt in a separate
sequential stage: one nonempty hypothesis with word/character/segment timestamps, stage
216.95s, peak process-tree RSS 3,951,644,672 bytes. No gold transcript exists; no WER or
medical accuracy claim follows. Both runs include cold library/model startup on the NTFS
workspace through WSL. Shared device totals include unrelated applications; process VRAM
was not measured. They do not qualify the 8 GB target laptop.

For full-recording comparison, excerpts now copy exact canonical source samples in buffers
of at most 1 MiB, publishing only complete WAVs. Repeated FFmpeg decoding is eliminated.
Tests verify byte-for-byte sample/timing preservation across buffer boundaries, invalid ranges,
truncated input rejection and coverage of speech without numbers. The full backend passes
143 tests with one Linux-only skip. Full-recording optional runs are in progress; approval,
email and human accuracy review have not occurred.

## Full-recording optional experiments (still not app qualification)

- Parakeet comparison run `optional-parakeet-full-1790372072987398325`: all 194 Whisper
  segments plus padding, 170 nonempty hypotheses / 24 empty, five mixed-script hypotheses,
  stage 231.71s, process-tree RSS peak 3,910,197,248 bytes. Clip union is 598.62s of 702.549s:
  this first comparison did not independently cover gaps between Whisper segments.
- Community-1 run `optional-diarize-full-1790372313130440559`: complete canonical recording,
  262 turns / five clusters, stage 216.54s, process-tree RSS peak 2,605,187,072 bytes.
  Cluster accuracy, overlap accuracy and person identities are not verified.
- Independent Parakeet run `optional-parakeet-timeline-1790372626350097280`: 24 contiguous
  30-second primary windows with 0.2s padding; stage 220.37s, process-tree RSS peak
  3,914,293,248 bytes. 1,085 word hypotheses remain after midpoint ownership removes padding
  duplicates; 92 word midpoints lie outside the first comparison's Whisper clips. These may
  be missed speech, recognition errors or timing errors; they are not automatically accepted.
  Windows 90–120s, 120–150s and 660–690s returned no text despite the independent diarizer
  assigning about 26.16s, 26.65s and 25.73s of speech. This is an unresolved coverage/accuracy
  signal, not a passing linguistic qualification. NeMo recommends roughly 5–25s input clips;
  window-length sensitivity and shorter retries need evaluation before selecting a production
  whole-timeline profile. Original empty hypotheses must remain available.

All three runs were sequential in isolated Linux network namespaces. Package compatibility
patches were active. Results, original inputs, timestamped hypotheses, progress and resource
reports remain private and ignored. The first timeline helper attempt failed before inference
with a missing helper import; its failure log remains retained. The corrected attempt above
completed. Current-step progress and ETA were observed during actual comparison (169/194
clips, about 2.42s remaining for that phase); this is not an estimate for later pipeline steps.

None of these experiments approved minutes, sent email, established native-language accuracy,
qualified target hardware or completed production API/UI integration. Import/model startup
accounts for most observed wall time in this environment and needs separate profiling.


## Actual isolated app integration, 2026-09-26

Run app-optional-1790375165684521014 used the production supervisor/retry dispatcher and optional
adapters with the registered clean Linux environment. External networking was unavailable.
The earlier real 194-segment Whisper output was replayed into a new private database; this is
not a fresh full-pipeline or browser run. Parakeet processed those clips and persisted 194
alternative records (including empty hypotheses); diarization processed the entire canonical
recording and persisted a cluster/unknown label for all 194 segments. No participant identity,
meeting date or timezone was invented. No approval or delivery was performed.

The integration took 130.67 seconds: supervisor receipts recorded 98.92 seconds for Parakeet
and 30.96 seconds for diarization. Peak process-tree RSS was 3,780,259,840 and 2,472,194,048 bytes.
GPU totals include unrelated services starting on the host and cannot establish application
VRAM or target-laptop fit. Source/config hashes, raw hypotheses, turns, progress and receipts
remain in the ignored private run directory. Earlier coverage/empty-window failures remain
unresolved; successful persistence is not an acoustic accuracy result.


## Coverage diagnostic replay

The new interval diagnostic, applied to the stored actual outputs of
app-optional-1790375165684521014, found 56 possible speech gaps totaling 102.322875 seconds,
plus 24 empty second-recognizer hypotheses. Speaker overlaps are unioned; nonempty transcript
spans are subtracted; gaps under 0.5 seconds are not flagged. This is a review signal from
imperfect model outputs, not 102 seconds of human-confirmed missing speech. Private source
intervals and count report remain ignored. No new acoustic inference occurred in this replay.
