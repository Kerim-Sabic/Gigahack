# 021 — Measure speech candidates before changing the final transcript

The current contract is `docs/SPEECH_UPGRADE_SPEC.md`. Its primary workstation
is Windows/WSL, Ryzen 7950X, 128 GB RAM and two separate RTX 5080 16 GB devices.
The earlier 3070 Ti laptop remains an unqualified secondary target. The user
clarified that Medpark is probably mostly Romanian, with Russian also expected.
That is a useful language prior, not a word-level reference transcript.

## Integration

Preserve the FastAPI/React/SQLite application, canonical sample clock, supervisor
ownership, existing Whisper/Parakeet/Community-1 paths and review/approval rules.
Add a lightweight `ASREngine` contract and explicit source-window adapters for
Qwen, Whisper and Parakeet. No framework imports enter the API. Missing Qwen word
times and uncalibrated confidence remain null. A window-level language tag never
labels all of its words. Native script and accents are retained in raw outputs.

Qwen's native Transformers 5.17 integration fits the existing optional environment.
The publisher implementation additionally requires `qwen-asr==0.0.6`,
`transformers==4.57.6`, and `accelerate==1.12.0`. Those incompatible pins therefore
live in a separate environment; the working 182-package optional runtime is not
modified. The publisher package pulls in unused demo dependencies such as Gradio;
no demo service is launched. This is an experimental comparison environment,
not yet the approved application default. Exact packages, wheel hashes, retained
notices and security findings are under `manifests/speech-runtime/`.

Nemotron-3 requires newer Transformers than stable 5.17. A separate runtime pins
source commit `27166ea03f12c940f23176a904ab1d2ff1a3dcbb`. Its adapter uses bounded
PCM reads and carries the speaker cache between chunks. The offline-context mode
uses the checkpoint's chunk/right-context/FIFO/cache-update settings. Frame
probabilities and canonical source intervals are retained. Speaker IDs are anonymous
arrival-order channels, at most eight; no person identity is inferred. Cache
recovery and human DER remain separate acceptance gates.

All three new checkpoints and their original file hashes are recorded in
`manifests/speech-models.lock.json`. Qwen is Apache-2.0; Nemotron is OpenMDW-1.1.
These licenses do not establish accuracy or security. All weights remain outside Git.

## Actual findings

- A native Qwen 45-second attempt exhausted 512 output tokens. It failed rather
  than publishing an incomplete transcript. Later capped responses are retained
  as diagnostic artifacts, not accepted transcripts.
- On Medpark 0–20 s, native BF16/SDPA returned nine characters with a Czech label.
  Float32/eager and the publisher implementation also selected Czech, although
  their outputs differed. Extending the publisher pass to 60 seconds did not fix
  its language choice. This is a failed recognition outcome, not a successful
  accuracy result merely because the process completed.
- Additional Romanian and Russian hints produce separate, explicitly forced
  alternatives. They are not language detection, gold, or automatic corrections.
  The Romanian alternative still contains word errors. Raw hypotheses remain
  private and none has been accepted, approved or emailed.
- Six FLEURS validation clips were selected before inference: first three rows of
  each pinned Romanian/Russian validation parquet. Both Qwen and Whisper detect
  the expected language on all six, but neither is error-free. This small
  monolingual development check does not measure medical, Moldovan-accent,
  intra-sentence switching, minority-word recall, or speaker accuracy.

## Security review

The OSV query for the publisher runtime reports advisories for its old Transformers
and Accelerate pins. The raw identifiers and query timestamp are retained. The
reviewed issues involve attacker-controlled checkpoint indexes/configurations,
remote attention kernels, Trainer checkpoint loading, LightGlue loading, and
`save_pretrained` path handling. We use pinned, hash-checked local Qwen safetensors,
an explicit attention implementation and network-isolated qualification workers;
we do not invoke training, LightGlue or model saving. These constraints reduce
exposure for these tests but do not turn vulnerable dependency versions into
patched packages. Production promotion requires a documented remediation decision.

Sources: [Qwen model](https://huggingface.co/Qwen/Qwen3-ASR-1.7B),
[native integration](https://huggingface.co/docs/transformers/main/model_doc/qwen3_asr),
[Nemotron](https://huggingface.co/nvidia/Nemotron-3-Diarization),
[Accelerate advisory](https://osv.dev/vulnerability/GHSA-4j2p-28q2-5m79),
[attention-kernel advisory](https://osv.dev/vulnerability/GHSA-29pf-2h5f-8g72),
[Trainer advisory](https://osv.dev/vulnerability/GHSA-69w3-r845-3855),
[LightGlue advisory](https://osv.dev/vulnerability/GHSA-fgcw-684q-jj6r),
[model-saving advisory](https://osv.dev/vulnerability/GHSA-xrqw-3rrv-vx5w).

## Limits and next acceptance gates

The user clarified that Medpark is likely predominantly Romanian, with Romanian
and Russian expected in the Moldovan setting. This is session context, not a gold
transcript or evidence that each Latin-script word is Romanian. Preserve English
medical terms and minority-language words. A contradictory whole-window language
tag is a review signal; do not translate, transliterate or discard the other
language to satisfy the expected majority. Earlier Whisper output is also a
hypothesis, not the reference against which Qwen can be declared correct.

On the six preselected FLEURS clips (110 reference words total), micro-average
WER was 13/110 (11.82%) for publisher Qwen, 7/110 (6.36%) for full Whisper v3,
and 8/110 (7.27%) for Parakeet v3. These are development results from the saved
isolated runs, not a sufficiently large ranking or a Medpark accuracy estimate.

Nemotron processed the full 11,240,789-sample Medpark recording in an isolated
production-supervisor stage: 26 bounded blocks, 70,254 complete 10 ms frames,
246 turns and five anonymous channels. Total helper time was 22.683 seconds;
model decoding took 4.372 seconds. Torch peak allocated/reserved memory was
452,495,872/471,859,200 bytes, excluding other processes and non-Torch allocations.
The final 149 samples (9.3125 ms) are explicitly unscored, not assigned invented
speaker labels. The initial ceil-frame coverage guard failed; it was corrected
to match the model's complete-frame output and the full run repeated successfully.
Raw report: `.runtime/provided-audio/nemotron3-1790430275275746517/report.json`.
Both network probes were blocked; no segments, approvals or messages were created.
DER, actual identities, whole-file/chunk numerical parity and persistent speaker
cache recovery remain unmeasured. Community-1 remains the normal default.

The existing supervisor still serializes GPU work. Dual-device admission/residency,
true live Qwen streaming, final-pass fusion, calibrated reliability, language-span
detection, medical disagreement resolution, persistent speaker-cache recovery,
all CS01–CS10 audio tests and the final offline distribution are not yet complete.
Do not advertise the new pipeline as finished or more accurate on Medpark.
Qwen's forced aligner excludes Romanian from its supported languages; no Romanian
word timestamps are manufactured with that aligner.

The new code-switch scorer requires explicit reference token-language labels.
It reports minority-word recall separately from overall WER, preserves scripts and
accents, and leaves precision/per-language insertion attribution/boundary scores
unmeasured without hypothesis labels. Unit fixtures are scorer checks only.

FLEURS provides a licensed monolingual baseline. Common Voice is another candidate.
MoRoVoc addresses Romanian geographical variation, but its dataset availability,
license and suitability for transcription still need verification. This limited
search did not establish a ready, licensed RO/RU medical code-switch gold corpus;
that is not a claim that none exists. Laya and additional optional experiments are
deferred while the requested speech workflow is completed.

Sources: [FLEURS](https://huggingface.co/datasets/google/fleurs),
[Common Voice Russian](https://mozilladatacollective.com/datasets/cmu5x45pn00dao107j4o9w2yv),
[MoRoVoc paper](https://arxiv.org/abs/2509.16781).
