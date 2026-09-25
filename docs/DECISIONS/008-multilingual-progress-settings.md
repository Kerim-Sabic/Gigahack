# Source-language transcription and reproducible developer settings

The supplied recording exposed recording-level language anchoring: the original Whisper
pass returned only Cyrillic text. Enabling faster-whisper's existing per-window multilingual
option produced Romanian passages alongside Russian without changing models or adding a
cloud service. Use transcription, not translation. Initial detected language is not a
word-level language label. Short code switches and medical terms remain unqualified without
annotated reference audio; retain independent hypotheses and source evidence for review.

The optional Parakeet coverage default changes from number/negation-selected clips within
15 percent of audio to all transcript segments. This intentionally increases processing time
to avoid ignoring language switches without those lexical triggers. The independent model
is still optional and not verified until its isolated dependencies and actual inference pass.
No recognizer agreement is treated as proof of correctness. Existing model assets stay ignored.

Validated config/inference.toml centralizes context, output/reasoning budgets, model selection,
ASR decoding and batch controls. Freeze effective settings into queued jobs and cache identity.
Changed settings require a new job and fresh resource qualification; the target 8 GB laptop
has not been measured. Keep existing architecture and single-process GPU admission.

Progress is a content-free, atomic, best-effort display artifact. Database job state remains
authoritative. ETA needs observed work and covers only its current phase; unseen later stages
and human review cannot honestly be assigned that same estimate. Completed stage progress
never implies published job completion. Unknown meeting date/timezone remain unknown, so
relative dates cannot be resolved against invented metadata.

Validation: 127 backend tests, 10 frontend tests, strict frontend build and Python lint pass.
Actual multilingual Whisper run: 184.49 seconds / 176 segments / supplied 702.55-second decoded
recording, with observed progress. Synthetic fixture browser-to-PDF/Mailpit, RO/RU persistence
and 200-percent DOM zoom checks pass in a separate Linux network namespace. Fixture inference
validates workflow, not model accuracy. Whole-job ETA, long-file checkpoints, optional models,
word-level language annotation and native-language accuracy review remain open.
