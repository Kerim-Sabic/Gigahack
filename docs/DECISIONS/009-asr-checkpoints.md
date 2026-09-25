# Bounded ASR waveform reads and recoverable chunks

Whole-file Whisper decoding grew waveform memory with recording duration and repeated all
transcription after a process failure. The worker now reads at most checkpoint_seconds plus
left/right context from the canonical PCM file. Defaults: 300 seconds plus two seconds per
side. Existing multilingual per-decoding-window detection, source-language text and word
sample offsets remain in use. No new model, runtime package or remote call is introduced.

Each chunk is saved with fsync and atomic replacement before publication, keyed to the actual
canonical audio SHA-256, effective ASR settings, device/retry profile and implementation
identity. Completed chunks survive an interrupted stage; corrupt/hash-mismatched chunks are
recomputed. Settings/audio/source changes create a different checkpoint namespace. The
existing same-job Retry action can reuse compatible checkpoints; no partial chunk becomes a
successful transcript. Original recordings and private hypotheses remain outside Git.

Adjacent chunks have overlapping context. Source word midpoints select publication ownership;
raw full hypotheses are retained. Crossing segments are flagged in the transcript for audio
review. This policy does not prove linguistic correctness at boundaries. Per-chunk initial
language metadata is not a word-level language annotation. Restored work is excluded from ETA
throughput, so loading checkpoints cannot manufacture an unrealistically short estimate.

Tests cover an interrupted second chunk, exact source offsets and no repeated synthetic words,
maximum PCM array length, a corrupt checkpoint, changed settings/audio, mixed-language boundary
text, and ETA after resumption. These deterministic fixtures test mechanics, not ASR accuracy.

Actual supplied recording run 1790368675990215900 completed three chunks in 166.71 seconds
(model stage; supervisor receipt 167.09 seconds), 194 segments, 52 with Latin-script text.
Chunk initial languages were ru/ro/ro. Process-tree peak RSS was 3,174,469,632 bytes versus
3,253,755,904 bytes for the earlier full-waveform multilingual pass. This short recording and
shared development host are not target-laptop or long-recording memory qualification.

Still open: whole-app crash/stale-worker fencing qualification; extraction checkpoints;
streamed transcript state; duration/size/container/decode limits; full-job ETA; long-recording
accuracy and target resources. Do not describe this partial implementation as arbitrary-length
support or a guarantee against crashes. Existing two-hour upload and stage limits remain.

Actual recovery run 1790368911190021900: the owned real Whisper subprocess was terminated
after its first durable chunk. Same-job stage retry reused one chunk and finished all three
(702.549 seconds, 195 segments). Interrupted log/resource artifacts were retained separately.
This verifies ASR-child interruption and stage retry; it does not assert a full application
restart or linguistically identical model generations. No public transcript is included.

The transcript displays boundary notices, and candidates citing those segments receive an
explicit wording-review uncertainty. API tests cover its presence and absence through the
same evidence/quantity pipeline. Original uncertainty/approval requirements remain in force.

Validation: full backend suite passed 131 tests; the added boundary/no-boundary API
parameterization then passed both cases (132 total cases). Frontend 10 tests/build and
lint pass. Synthetic fixture browser/PDF/Mailpit rerun also verifies the boundary notice.
