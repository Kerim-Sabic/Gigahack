# 022 — Evaluate VibeVoice without replacing the working recognizer

The user approved testing a larger local recognizer for Romanian/Russian switches
on the dual RTX 5080 (16 GB each), 128 GB RAM, Ryzen 9 7950X workstation.

## Reuse and preparation

Use Microsoft's native Transformers checkpoint `microsoft/VibeVoice-ASR-HF` at
`f22241c2062b3b25272bf117397e03d73381037a`. Its index records 8,330,325,888
parameters and 16,660,651,776 weight bytes. This is the publisher's converted
checkpoint; do not confuse it with the original custom-code model repository.
All 16 selected local files are SHA-256 recorded in the speech model manifest.
Weights remain ignored and private recording files never leave the machine.

The model is MIT licensed. The full Microsoft notice and source revision are
retained under `manifests/speech-runtime/licenses/VibeVoice-MIT-LICENSE` and its
provenance JSON. Runtime distribution notices are retained separately.
No model-provided Python is executed: loading uses native Transformers,
`trust_remote_code=False`, local files only, safetensors and pinned hashes.

The isolated Python 3.12 runtime has 96 exact package versions. It reuses the
already reviewed Transformers source commit
`27166ea03f12c940f23176a904ab1d2ff1a3dcbb`, Torch 2.14.0 and focused audio
dependencies, with Accelerate 1.15.0 for device dispatch. Existing core, Qwen and
Nemotron environments are unchanged. Ordinary copies were used when preparing it.
`uv pip check` passed. The recorded OSV query returned no known advisories for
these version queries; development-commit coverage is incomplete and this is not
a security certification. Exact runtime registration includes package versions,
direct source URLs, lock and inventory fingerprints.

## Integration and hardware policy

This is a benchmark-only adapter. The existing supervisor host lock and child
model lock reserve both GPUs for one owned process; no other application inference
stage is admitted concurrently. The worker sees devices 0 and 1 and dispatches
whole decoder layers explicitly. Audio encoders stay on device 0. Each device
must have at least 11 GiB free at admission. No assumption of automatic pooled
VRAM or concurrent LLM residency is made.

Windows/WSL GPU totals include other allocations; report this worker's actual
Torch peak allocated/reserved counters separately. Initial tests limit input to
60 seconds and batch size one. They do not qualify an hour of context, live
streaming, indefinite files, or production dual-GPU scheduling.

The adapter resamples canonical 16 kHz audio to the model's native 24 kHz input,
retaining the original sample interval. It preserves native script and returns
no invented word timestamps, language spans or confidence. Generated JSON is
validated; malformed, truncated and out-of-source timestamps produce explicit
failure artifacts. Speaker IDs are anonymous and local to each window.
Upstream acoustic latent sampling remains enabled with a recorded fixed seed.

The first load exposed that the audio tokenizer does not accept SDPA. The adapter
now selects SDPA only for the text decoder and eager execution for the audio
encoders. This configuration is separate from any future numerical/precision
comparison; failure logs are retained.

## Evaluation scope

1. Replay the same six preselected FLEURS Romanian/Russian validation clips used
   for Whisper, Parakeet and Qwen; references are never model prompts.
2. Construct two separately labelled probes inserting three foreign-language
   words in each direction. Source words are from publisher references whose
   full baseline transcript matches, but cut times come from Whisper. Joins,
   voice changes and unnatural sentences prevent claims about natural switching.
   Report minority-word recall separately, with human boundary review unavailable.
3. Diagnose three preselected Medpark windows: 0–60, 300–360 and 640–700 seconds.
   There is no reference transcript; an empty scoring reference is explicitly
   unannotated, not silence. No WER or speaker-accuracy claim is permitted.

All actual inference uses enforced network namespaces, private benchmark meetings,
the production supervisor, source hashes and no accepted events or outgoing mail.
Normal transcription defaults remain unchanged. Test results must justify any
later model promotion; a larger parameter count does not establish superiority.

Sources: [Microsoft checkpoint](https://huggingface.co/microsoft/VibeVoice-ASR-HF),
[native integration](https://huggingface.co/docs/transformers/main/model_doc/vibevoice_asr),
[Microsoft source](https://github.com/microsoft/VibeVoice).

## Initial measured results and excluded fixtures

The first functioning BF16 run produced a hallucinated year sequence on FLEURS
`ro_ro-1655` and reached 2,048 tokens. The full comparison repeated that failure
with an explicit 1,024-token budget. Five of six reference clips yielded valid
outputs: 24 errors / 92 words (26.09%) on that completed subset. The sixth is a
failed output, not an excluded difficult example for claiming overall accuracy.
The existing Whisper run completed all six with 7 errors / 110 words (6.36%).
These small samples do not qualify overall Romanian/Russian or Moldovan accuracy.

Two initial constructed probes were invalidated: reading normalized floating WAV
data directly into integer PCM through libsndfile yielded effectively silent
audio. Their silence outputs are not ASR failures. The corrected preparation
decodes to float32, explicitly scales to PCM16, checks source amplitude and is
covered by a numerical regression test. Original fixtures and the exclusion
sidecar remain available for audit; corrected clips use a separate directory.

Initial comparison: `.runtime/speech-benchmarks/vibevoice-1790432441688703344`.
It includes all six public clips, two invalidated fixtures, and the three private
Medpark windows. Do not use its unfiltered failed-case total as a model score.
Both before/after network probes were blocked. One Medpark output was truncated;
another contained a valid environmental-sound annotation without a speaker ID,
which exposed an overly strict parser rule requiring a follow-up correction.
No transcript was accepted, approved or sent.

The corrected two-clip VibeVoice run completed successfully as an experiment:
`.runtime/speech-benchmarks/vibevoice-1790432947326414433/report.json`.
It preserved 0/3 inserted Russian words and 0/3 inserted Romanian words. Whisper
and Parakeet repeated on the same corrected inputs also preserved 0/3 in both
directions. These constructed probes are explicitly not natural code-switch gold.
Both inserted portions have nonzero measured energy; original cut times still
require human review. This failure must not be hidden by aggregate WER.

The parser now allows exact `[Silence]` and `[Environmental Sounds]` annotations
without a speaker ID, retains them in raw segment evidence, and excludes those
annotations from spoken text. Missing speakers on ordinary speech still fail.
Replaying the saved complete Medpark 640–700 s output with this rule succeeds;
the recovered diagnostic is `.runtime/provided-audio/vibevoice-reparsed-medpark640.json`.
The 300–360 s output remains truncated and is not recovered or published.

Local checks after these corrections: 230 backend tests passed, two Linux-only
tests skipped on Windows, Ruff passed, 12 frontend tests passed and the strict
frontend build passed. No runtime, model or benchmark identity file was changed
during a live inference run.

Qwen's publisher runtime also preserved 0/3 minority words in both corrected
probes (`qwen_asr-1790433515218147445`). A final isolated-word control replay
with Whisper (`whisper-1790433640964426572`) recognized all three Russian words
plus one extra word; the Romanian control was misrecognized as English with
zero exact reference words preserved. Thus the Russian control shows a context
effect, while the Romanian case also has short-clip language ambiguity. These
results must not be generalized to natural speech or attributed solely to switching.
The canonical PCM passed to the model was checked byte-identical to both prepared
mixed probes. There was no hidden upload conversion or deletion of the insertions.

Final decision: retain VibeVoice as an explicitly selected experimental benchmark
adapter, not a default production recognizer. Preserve the working architecture.
Further qualification needs human-annotated natural speech, including minority
words and language-boundary ambiguity, before any model promotion or fine-tuning.
