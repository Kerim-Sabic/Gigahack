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
