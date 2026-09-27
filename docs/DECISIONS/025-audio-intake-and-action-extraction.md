# Audio intake and explicit transcript analysis

The meeting workspace now exposes audio intake outside advanced settings. A new
meeting starts with an open audio drop area. Selecting a file shows its name and
size; explicit upload saves it without starting speech recognition. Actual transfer
progress changes to an indeterminate preparation phase until decoding and durable
storage finish. The panel remains open after saving. Saved recordings show duration
and a separate transcription command. Supported formats match the server.

Upload metadata now retains a path-stripped display filename inside the existing
metadata JSON. Storage paths remain generated identifiers. Existing assets fall back
to a recording number. No schema change or new dependency is needed.

The visible **Extract actions with AI** button uses the existing durable
`transcript_only` job contract for the selected recording. It reads current saved
segment revisions, including imported/corrected text, without ASR or diarization.
The existing source evidence, revision validation, event deduplication, review,
approval and delivery rules remain authoritative. Unknown owners/deadlines stay
unresolved. Existing identical completed jobs are reused; stopped jobs can retry.
The button disables while processing, loading source text, or missing a transcript.
Viewers cannot invoke it. Stage progress remains visible outside meeting options.

## Verification — 27 September 2026

- 23 frontend tests passed, including invalid audio, failed-upload retry state,
  explicit save without automatic transcription, transcript-only queue payload,
  disabled states, completion feedback and cancelled-job reuse.
- 239 backend tests passed, two platform-specific skips. A fresh repository-local
  pytest temporary directory avoids this host's inaccessible default temp root.
- Strict frontend build and Ruff passed.
- Actual browser upload persisted `Synthetic meeting.wav` and created no job.
  Desktop 1440px and mobile 390px layouts checked without overflow or page errors.
- Actual local LLM job `59a2424f-6cc1-43c7-bf4e-1fd59e153d1b` completed from the new
  button, with synthetic imported text and silent source audio. Observed completion
  after 24.1 seconds of polling. It extracted Maria and 2026-10-16 correctly,
  preserved unapproved review state, and created no speech-stage output. This is
  a functional smoke test, not a transcription or clinical accuracy benchmark.
- The user's Medpark recording was not processed or changed.

No claim of perfect extraction, arbitrary-length qualification or automatic
approval is introduced. Existing optional model and hardware acceptance gaps remain.
