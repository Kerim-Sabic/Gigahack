# Developer model configuration

Extraction work-unit checkpoints bind to the complete frozen configuration, resolved LLM
settings, model/executable bytes, source revisions and implementation identity. Changing
context, output budgets or another setting recomputes affected work; do not edit private
checkpoint files to apply settings. Raw replies remain in attempt journals. The stage output
contains `raw_artifact`, `checkpoint_identity` and `reused_units` alongside `events`, rather
than duplicating all raw responses in memory. Total transcript/event state still grows with
meeting length. See [Decision 019](DECISIONS/019-extraction-checkpoints.md).

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
a measured latency cost and open semantic acceptance; see DECISIONS/007-bounded-interpretation.md
and DECISIONS/015-source-first-speech-act-review.md for the known tentative-date regression fix.
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

When Parakeet and diarization are both enabled, `recovery_window_seconds` (20),
`recovery_retry_seconds` (10) and `recovery_padding_seconds` (2) control separate suspected-gap
hypotheses. The retry must be shorter and the primary plus padding may not exceed 25 seconds.
An empty longer window gets one subdivision pass; shorter empty output stays visible.
Gap review is independent of the comparison fraction and never automatically changes the
transcript. See DECISIONS/016-gap-recovery-hypotheses.md for measured behavior and open gates.

After a reviewer adds missing words or edits the transcript, use **Reanalyze corrected transcript**.
This queues `transcript_only: true` with the frozen LLM profile and saved source revisions;
Whisper, Parakeet and diarization are not rerun. New minutes require successful analysis and
renewed review. Earlier audio checks and immutable minutes remain available. See Decision 017.

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

## Speech-upgrade qualification controls

`config/inference.toml` exposes Qwen ASR backend, isolated runtime path, output-token
cap, vocabulary-character budget, precision and attention implementation. These
are distinct from the existing `[llm]` context and generation budgets. Qwen remains
an explicit-window candidate stage, not the primary recognizer in normal jobs.
Output-token exhaustion fails explicitly and retains diagnostics; it never silently
publishes a truncated transcript. Vocabulary inputs are bounded lists of actual
session spellings, not generated clinical facts.

`optional.diarization_engine` selects `community1` (default) or `nemotron3`.
The latter requires the registered runtime in `[nemotron].runtime_prefix`;
`mode` and `threshold` control context and speaker activity. Runtime/model hashes
are checked before loading. These experimental settings do not enable dual-GPU
execution, live streaming, or automatic acceptance of model hypotheses.

Use the prepared Linux/WSL core Python to run a reference benchmark:

```sh
python -m scripts.benchmark_speech --cases /absolute/path/cases.json --engine whisper
```

Each JSON list entry provides `id`, `audio`, `sha256`, `reference_text`, and
`provenance.review_status`. Relative audio paths resolve against the manifest.
Provide 1–32 clips, each at most 60 seconds; split longer evaluation material with
recorded source offsets rather than truncating it. References are scored after
inference and never supplied as model prompts. Parakeet requires `--runtime-prefix`;
Qwen uses `--engine qwen_asr --qwen-backend official --runtime-prefix ...`.
The command enforces a separate network namespace, the supervisor's GPU lock,
private output storage and no accepted meeting events. See Decision 021 for the
publisher runtime's unresolved security advisories and accuracy limitations.

Expected Romanian/Russian session context must not become recording-wide forced
language routing. Explicit diagnostic language hints are separate alternatives,
not detected languages or corrected transcripts. Word-level language labels remain
unavailable until independently qualified.

VibeVoice is another explicitly selected benchmark engine:

```sh
python -m scripts.benchmark_speech --cases /absolute/path/cases.json --engine vibevoice --runtime-prefix /absolute/path/registered-runtime --max-new-tokens 1024
```

Its runtime is pinned in `manifests/speech-runtime/vibevoice.lock.txt`. The normal
job settings expose `[vibevoice]` output budget, session vocabulary budget and
seed; the benchmark may override the output cap explicitly. The native adapter
uses BF16 and one process spanning both GPUs under the existing exclusive lock.
It is not offered as an automatic replacement in the normal meeting workflow.
Malformed/capped results are saved as failed cases and the remaining benchmark
clips continue. The report counts failed cases and exits nonzero when any fail;
never rank a candidate using only its successful subset without reporting coverage.
Unannotated clips have `NOT_MEASURED_NO_REFERENCE`, not an assumed silent reference.

`scripts.prepare_codeswitch_probe` constructs two reproducible, three-word
Romanian/Russian splicing probes from the pinned FLEURS clips and the saved
Whisper timing report. This requires the prepared speech runtime's SoundFile.
It checks that the timing transcript matches the publisher reference. The output
records all cuts and source hashes, but still requires human boundary review;
different voices and artificial joins do not qualify natural code-switch accuracy.

To reproduce the isolated VibeVoice environment in WSL, create a new Python 3.12
virtual environment and install the exact lock with ordinary copies:

```sh
UV_LINK_MODE=copy uv venv --python /usr/bin/python3.12 /absolute/path/new-runtime
UV_LINK_MODE=copy uv pip install --python /absolute/path/new-runtime/bin/python -r manifests/speech-runtime/vibevoice.lock.txt
/absolute/path/new-runtime/bin/python -m scripts.register_speech_runtime --name vibevoice
```

Run these from the repository root. Registration verifies the exact inventory and
source revisions; it does not regenerate the pins to bless whatever is installed.
A failed check restores the previous marker. Model preparation uses the revision
and per-file hashes in `manifests/speech-models.lock.json`; inference never downloads
missing files. This is an online preparation recipe, not the final offline installer.
