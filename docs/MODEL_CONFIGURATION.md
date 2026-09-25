# Developer model configuration

Edit `config/inference.toml`. This is the single configuration for prepared LLM selection,
context and source windows, output/reasoning budgets, temperature, GPU layers, batching,
timeouts and recursive splitting; ASR model/beam/window/compute choices; and optional-stage
budgets. `services/worker/settings.py` validates names, ranges and compatible budgets before
inference. Unknown keys fail rather than being silently ignored. API code does not import
heavy inference libraries.

New jobs store the complete effective configuration under `config.inference`. Changes create
a different job/cache identity. Source/configuration hashes also fence stale queued workers;
after editing the configuration, cancel/requeue old work rather than expecting it to silently
pick up new values. Receipts retain the input configuration. A running process uses its frozen
profile. Developer edits never mutate an earlier approved snapshot.

For a larger context, change `llm.context_tokens`, then choose `source_window_tokens` and
`reconciliation_tokens` leaving room for system instructions and output. Static validation
rejects obviously incompatible budgets; every actual rendered prompt is checked as well.
Larger context is not automatically qualified for the 8 GB laptop. Measure loading/inference
VRAM, latency and unchanged semantic checks before selecting a new release default.

For a different model or quantization, explicitly prepare the licensed local files, add their
immutable revision/checksums/attribution to the model manifest, and change `model_directory`
and `model_file`. Unpinned/missing LLM files fail locally. No configuration option enables a
cloud fallback or downloads at runtime. The initial default is still the existing Qwen 4B
Q4_K_M file, 4096 context, 768 extraction output, temperature zero and one generation slot.

`reasoning_tokens` applies only to independent interpretation passes; zero disables thinking.
The non-thinking initial extractor is unchanged. The current 768-token reasoning choice has
a measured latency cost and an open held-out semantic failure; see DECISIONS/007-bounded-interpretation.md.
Single GPU admission and one generation slot are enforced invariants. They are deliberately
not exposed as unqualified parallelism knobs. Prompt text and evidence validation remain
reviewable code in `services/worker/stage.py` and the domain modules.

Run `python -m scripts.mom test`, `python -m ruff check .`, original/development text evaluation,
real audio checks and target qualification after consequential changes. A model card's accuracy
or hardware claim is not proof for this application or the supplied recording.

Multilingual ASR defaults to per-window language detection and transcription (no translation).
The initial detected language is only a recording summary. It must not be presented as a
language annotation for every word. The optional Parakeet check now defaults to all transcript
segments, including speech without numbers/negation; this costs additional processing time.
Reducing `parakeet_audio_fraction` reduces coverage and may miss short code switches.

ASR `checkpoint_seconds` bounds each PCM read (default 300 seconds), with two seconds
of context on each side. Word midpoint ownership avoids publishing the same overlap window
twice, and crossing hypotheses retain their complete raw text and a boundary-review flag.
Checkpoints are atomic/fsynced and keyed to the actual audio hash, settings, device/retry
profile and implementation identity. Corrupt or mismatching checkpoints are recomputed.
This bounds waveform memory; total transcript/LLM state is still proportional to meeting size.
Fixed default upload/duration caps are removed and canonical storage supports RF64. Full-pipeline
long-speech qualification and bounded aggregate state remain open. See DECISIONS/014-long-audio-storage-and-playback.md.

`worker.no_activity_timeout_seconds` controls the inactivity watchdog (default 1800 seconds).
A long stage is not stopped merely because two hours elapsed. Advancing work or observed CPU
computation in its process tree keeps it alive; timestamp-only updates do not. This cannot
identify every logical busy loop. Cancellation and bounded model-request timeouts remain.


Optional models use a separate pinned Linux x86_64 Python 3.12 environment. The API stays in
its core environment. After preparing the candidate packages and exact reviewed patches,
register it locally with `python -m scripts.mom verify-optional --path /absolute/environment`.
This checks the complete installed package/version set, patched source hashes and every pinned
model file hash without downloading or importing inference frameworks. It writes a readiness
record inside that environment. Run the Linux/WSL app with `MOM_OPTIONAL_RUNTIME` set to the
same absolute prefix, or set `optional.runtime_prefix` in the TOML. The environment override
is resolved when a job is queued and is frozen with that job's configuration.

The API checks this record and asset presence; actual optional workers repeat package, patch
and model hash verification before loading. Missing/stale registration disables the optional
controls. Native Windows does not dispatch work across an implicit WSL boundary. Both the API
and supervisor must run in Linux/WSL to use this optional setup. Prepared status establishes
local prerequisites, not linguistic accuracy or compatibility with the target laptop.

The candidate lock records 182 package artifacts; pip 26.2.1 is separate bootstrap tooling.
The complete reproducible installer/offline distribution is still pending. Do not point the
application at the historical merged experimental environment, which contains extra packages.


Ingestion resource policy is separate from inference budgets. `MOM_MAX_UPLOAD_BYTES` and
`MOM_MAX_AUDIO_SECONDS` default to zero (no operator-imposed cap). `MOM_MIN_FREE_BYTES`
defaults to 5 GiB and cannot be lowered below that reserve. `MOM_DECODE_IDLE_SECONDS`
defaults to 300 and measures lack of CPU/output activity, not total decoding time. These
process-start settings live in services/api/config.py; restart the API after changing them.
They do not certify unlimited storage or bounded whole-pipeline memory. Storage errors preserve
already acknowledged audio; unacknowledged incoming bytes may need to be sent again.
