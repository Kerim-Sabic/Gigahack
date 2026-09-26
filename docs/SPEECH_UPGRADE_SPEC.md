You are responsible for upgrading the existing Secure MOM / Gigahack speech pipeline into the **highest-accuracy fully local Romanian + Russian medical transcription system we can realistically build on this workstation**.

Repository:

`Kerim-Sabic/Gigahack`

Hardware:

* Windows 11 host
* Ryzen 9 7950X
* 128 GB system RAM
* 2 × NVIDIA RTX 5080
* approximately 16 GB VRAM per GPU
* WSL2/Linux/Docker is allowed and preferred if required for reliable CUDA/NeMo/vLLM operation

DO NOT merely write an architecture proposal.

Inspect the repository, implement the system, install and pin dependencies, download models locally, modify the backend/frontend where required, run real inference, benchmark it, debug failures, test mixed-language audio, and leave the project operational.

The highest priority is **TRANSCRIPTION ACCURACY**.

Latency is important, but if there is a tradeoff:

**final transcript accuracy > live latency**

The live transcript may be provisional.

The final transcript must use every reasonable local technique available to maximize accuracy.

---

# NON-NEGOTIABLE LANGUAGE REQUIREMENT

The system is primarily intended for Moldova.

It must handle:

* Romanian
* Russian
* English when it appears
* Moldovan Romanian accents
* Russian spoken by Moldovan speakers
* Romanian speakers using Russian expressions
* Russian speakers using Romanian expressions
* medical terminology
* medication names
* clinician names
* acronyms
* numbers
* dosages
* dates
* measurements

Most importantly:

## TRUE INTRA-SENTENCE CODE SWITCHING

Do NOT design this as:

```text
detect language of recording
→ choose Romanian ASR

OR

detect language of recording
→ choose Russian ASR
```

That architecture is unacceptable.

A speaker might say something approximately like:

```text
Pacientul a venit dimineață și a spus что ему стало хуже după administrarea medicamentului.
```

or:

```text
Am verificat давление și după aceea am făcut ECG-ul.
```

or speak:

```text
90% Romanian
10% Russian
```

where the Russian portion may be:

* one word
* two words
* one short phrase
* an interruption
* a medical term
* a colloquial expression

The transcription system must attempt to preserve that switch correctly.

Expected output should preserve appropriate orthography:

```text
Romanian → Latin script + Romanian diacritics
Russian → Cyrillic
```

Do NOT transliterate Russian into Latin simply because most of the sentence is Romanian.

Do NOT translate Russian into Romanian.

This is TRANSCRIPTION.

Preserve what was spoken.

---

# CORE ASR STRATEGY

Do not rely on a single ASR model.

Implement a multi-engine architecture optimized specifically for Romanian/Russian code-switching.

Primary candidates must include:

## Engine A — Qwen3-ASR-1.7B

Use the latest official local checkpoint from Qwen.

This should be treated as the primary high-accuracy multilingual/code-switch candidate.

Verify current official:

* model ID
* Transformers support
* qwen-asr package
* vLLM support
* streaming implementation
* language configuration
* context/hotword prompting
* output scores/confidence availability
* timestamp capabilities
* licensing

Use BF16 where supported.

Use FlashAttention or equivalent optimized attention where supported and stable on RTX 5080.

Use the 1.7B model, not 0.6B, unless benchmarking demonstrates a compelling reason otherwise.

Required capabilities:

* Romanian
* Russian
* automatic language handling
* mixed-language transcription
* long audio
* streaming
* contextual vocabulary biasing

Do NOT blindly force the language of an entire utterance to Romanian or Russian.

---

# Engine B — Whisper large-v3

Integrate full:

**Whisper large-v3**

as a second high-accuracy multilingual transcription engine.

For final-pass accuracy, prefer full `large-v3` over a smaller/faster Whisper variant unless measured results show otherwise.

Whisper should run locally.

Use an optimized implementation such as:

* faster-whisper / CTranslate2
* or another current implementation proven to preserve accuracy

if it materially improves speed without degrading transcription quality.

Whisper is important because its errors will often differ from Qwen's errors.

We want independent hypotheses.

---

# Engine C — NVIDIA Parakeet TDT 0.6B v3

Keep:

**Parakeet TDT 0.6B v3**

because it is fast and strong for individual supported languages.

However:

DO NOT assume Parakeet alone solves Romanian/Russian code-switching.

Use it as:

* fast live hypothesis
* third independent ASR hypothesis
* timestamp source where useful
* confidence evidence
* fallback
* consensus input

Benchmark it specifically on code-switching.

---

# OPTIONAL MODELS

Only after the above three are operational, evaluate other current open/local ASR models that:

1. support BOTH Romanian and Russian;
2. can run locally;
3. fit our hardware;
4. have credible evidence of strong ASR performance;
5. improve our measured test set.

Do not add models because they are large or fashionable.

Add them only if they improve measured accuracy.

---

# ASR ABSTRACTION

Implement a unified interface.

Something conceptually like:

```python
class ASREngine:
    def transcribe(...)
    def transcribe_stream(...)
    def get_word_timestamps(...)
    def get_confidence(...)
    def supports_language(...)
    def supports_streaming(...)
    def health_check(...)
```

Implement adapters:

```text
QwenASREngine
WhisperASREngine
ParakeetASREngine
```

Every engine should return a normalized internal schema.

Example:

```json
{
  "text": "...",
  "segments": [],
  "words": [],
  "language": null,
  "language_spans": [],
  "confidence": null,
  "model": "...",
  "model_version": "...",
  "latency_ms": 0
}
```

Do not force every model to fake fields it cannot reliably produce.

Mark unavailable information explicitly.

---

# CRITICAL: DO NOT USE RECORDING-LEVEL LANGUAGE ROUTING

A recording might be:

```text
95% Romanian
5% Russian
```

or:

```text
70% Russian
30% Romanian
```

or alternate repeatedly.

Therefore:

DO NOT implement:

```python
lang = detect_language(audio)

if lang == "ro":
    romanian_model(audio)
else:
    russian_model(audio)
```

That fails our central use case.

Language identification must be treated as:

* segment-level
* span-level
* possibly token-level

and as supporting evidence rather than an irreversible router.

---

# MULTI-HYPOTHESIS DECODING

For each meaningful speech region, generate multiple independent hypotheses where computationally appropriate.

For FINAL mode, at minimum consider:

```text
Qwen3-ASR-1.7B auto/multilingual
Whisper large-v3 multilingual
Parakeet v3 multilingual
```

For difficult or low-confidence spans, optionally produce additional targeted hypotheses such as:

```text
Qwen Romanian-biased
Qwen Russian-biased

Whisper Romanian-conditioned
Whisper Russian-conditioned
```

BUT:

Do not replace the whole sentence simply because a forced-language version scores well.

Use these alternative decodes only as evidence for uncertain spans.

This is especially important for single-word language switches.

---

# CODE-SWITCH RECOVERY SYSTEM

Implement a specific component:

```text
CodeSwitchResolver
```

Its job is to identify and repair likely language-switch spans.

Example:

Primary decode:

```text
Pacientul spune că "davlenie" este mare.
```

Another hypothesis:

```text
Pacientul spune că давление este mare.
```

The second may contain the actual spoken Russian word.

The resolver should use:

* acoustic confidence
* model confidence/log probabilities where available
* agreement between independent ASR engines
* phonetic compatibility
* language/script evidence
* temporal alignment
* local context
* medical vocabulary
* validated engine-specific reliability

Do NOT select words merely because they make the sentence semantically nicer.

Audio evidence must dominate.

---

# LANGUAGE-SPAN REPRESENTATION

Represent language switching explicitly.

For example:

```json
{
  "text": "Pacientul spune că давление este mare.",
  "language_spans": [
    {
      "language": "ro",
      "start_char": 0,
      "end_char": 18
    },
    {
      "language": "ru",
      "start_char": 18,
      "end_char": 27
    },
    {
      "language": "ro",
      "start_char": 27,
      "end_char": 37
    }
  ]
}
```

If token/word timestamps are available, language spans should also contain time ranges.

Do NOT require an entire ASR segment to contain a single language.

---

# NATIVE SCRIPT PRESERVATION

Default behavior:

### Romanian

Preserve:

```text
ă
â
î
ș
ț
```

Use proper Romanian diacritics.

### Russian

Preserve Cyrillic:

```text
А Б В Г Д ...
```

Do not output phonetic Latin transliteration unless explicitly requested.

### Medical international vocabulary

Preserve clinically conventional spelling when the acoustic evidence supports it.

Examples include:

```text
ECG
CT
MRI
COVID-19
HbA1c
SpO2
metoprolol
atorvastatin
```

Do not convert recognized international terms into awkward phonetic spellings unnecessarily.

---

# QWEN CONTEXT / HOTWORD BIASING

Use Qwen3-ASR contextual prompting carefully.

Construct a session-specific vocabulary prompt containing high-value vocabulary such as:

### Known participants

```text
Dr. Popescu
Dr. Ivanov
Ana Munteanu
```

### Hospital terminology

Romanian medical terminology.

Russian medical terminology.

### Departments

```text
cardiologie
terapie intensivă
neurologie
кардиология
реанимация
неврология
```

### Medications

Known medication vocabulary relevant to the hospital.

### Procedures

Known procedure names.

### Abbreviations

Hospital-specific abbreviations.

### Device / product terminology

if relevant.

Do not create a giant random dictionary.

Context biasing should contain likely vocabulary for the session.

Implement:

```text
ContextBuilder
```

that can assemble context from:

* meeting type
* department
* participant names
* known medical terminology
* optional user-provided terms
* previous verified vocabulary

Do NOT include patient diagnoses not already known.

Do NOT bias the model into hallucinating clinical facts.

---

# MEDICAL LEXICON

Create a structured bilingual terminology system.

Example:

```text
resources/medical/
    ro_terms.*
    ru_terms.*
    medications.*
    abbreviations.*
    names.*
```

Do not simply use these terms for blind autocorrection.

Use them as evidence during:

* contextual prompting
* candidate ranking
* spelling validation
* terminology confidence assessment

Every correction must remain grounded in acoustic/ASR evidence.

---

# NUMBERS ARE HIGH PRIORITY

Medical transcription can become dangerous when numbers are wrong.

Create dedicated validation for:

* medication doses
* blood pressure
* heart rate
* oxygen saturation
* temperature
* laboratory values
* percentages
* dates
* time
* age
* frequencies
* units

Examples:

```text
5 mg
50 mg
15 mg

120/80
180/80

SpO2 92%
SpO2 99%

37.2°C
39°C
```

Treat number disagreements between models as high-risk.

Do NOT silently choose one.

If final confidence remains low, flag the value.

Example:

```json
{
  "text": "metoprolol 50 mg",
  "confidence": 0.61,
  "requires_review": true,
  "alternatives": [
    "15 mg",
    "50 mg"
  ]
}
```

The frontend may visually highlight low-confidence medical numbers.

---

# MEDICAL TERM ERROR DETECTION

Create a higher-sensitivity review mechanism for:

* medications
* diagnoses
* procedures
* anatomy
* measurements
* named devices

If ASR engines disagree significantly on one of these entities, flag it.

Do not hide disagreement.

---

# AUDIO CHUNKING

Naive 30-second hard slicing is unacceptable.

Use overlapping contextual windows.

Investigate and benchmark configurations such as:

```text
live:
short incremental chunks
+
rolling context

final:
20–60 second contextual windows
+
2–5 second overlap
```

Choose values through measurement.

At every boundary:

* preserve preceding context
* preserve following context
* deduplicate overlapping text
* never lose short words at chunk boundaries

Implement robust overlap reconciliation.

---

# DO NOT CUT SHORT RUSSIAN INSERTIONS

VAD must be conservative.

A Russian insertion such as:

```text
да
нет
хорошо
потом
давление
```

may be extremely short.

Do not discard it as noise.

Use:

* pre-roll
* post-roll
* minimum speech preservation
* boundary padding

Tune VAD against short-word recall.

Accuracy matters more than saving a few milliseconds of compute.

---

# RAW AUDIO + ENHANCED AUDIO

Never permanently replace the original audio with denoised audio.

Maintain:

```text
original audio
```

and optionally:

```text
enhanced audio
```

If you implement denoising, evaluate BOTH.

Some enhancement models destroy consonants or quiet speech.

Therefore test:

```text
ASR(original)
ASR(enhanced)
```

and determine empirically whether enhancement improves accuracy.

Do not assume denoising is beneficial.

---

# MULTI-CHANNEL AUDIO

If microphone hardware exposes multiple channels:

KEEP THEM.

Do not immediately downmix to mono.

Where possible use:

* channel information
* microphone geometry
* beamforming
* channel selection

to improve speech intelligibility.

Still preserve the original recording.

---

# LIVE MODE

The live pipeline should optimize latency while maintaining context.

Suggested conceptual pipeline:

```text
microphone
   ↓
ring buffer
   ↓
conservative VAD
   ↓
Qwen3-ASR streaming
   +
Parakeet fast streaming/secondary decode
   ↓
Nemotron diarization
   ↓
partial alignment
   ↓
LIVE transcript
```

Do not finalize text too early.

Maintain transcript states:

```text
tentative
stable
final
```

Example:

```text
TENTATIVE:
Speaker 1: Pacientul spune...

STABLE:
Dr. Popescu: Pacientul spune că...

FINAL:
Dr. Popescu: Pacientul spune că давление este ridicat.
```

Allow recent text to be revised.

---

# FINAL MODE — MAXIMUM ACCURACY

When the meeting ends, prioritize accuracy heavily.

The final pass should:

1. use the original high-quality recording;
2. run high-context Qwen3-ASR-1.7B;
3. run Whisper large-v3;
4. run Parakeet where useful;
5. generate word/segment timing evidence;
6. run final Nemotron diarization;
7. align ASR hypotheses temporally;
8. identify disagreement regions;
9. rerun uncertain regions with additional context;
10. run Romanian/Russian alternative hypotheses where useful;
11. resolve code switches;
12. reconcile speaker labels;
13. validate numbers;
14. validate medical terminology;
15. generate confidence metadata;
16. preserve the raw ASR hypotheses;
17. produce the final transcript.

Do not simply select whichever complete transcript "looks better."

---

# ENSEMBLE / TRANSCRIPT FUSION

Implement an actual ASR fusion layer.

Research current robust approaches such as:

* ROVER-style hypothesis fusion
* confusion-network voting
* minimum Bayes risk decoding
* confidence-weighted consensus
* time-aligned token voting

Use whichever technique is technically appropriate for available outputs.

Do NOT implement naive:

```python
if qwen_text != whisper_text:
    ask_llm_which_looks_better()
```

That is unacceptable.

Fusion must incorporate the audio-derived evidence.

---

# MODEL-SPECIFIC CALIBRATION

Different models produce different confidence scales.

Therefore do not directly compare:

```text
Qwen confidence = .8

versus

Whisper confidence = .8
```

as if they mean the same thing.

Build a calibration layer from validation data.

Use techniques such as:

* reliability curves
* temperature scaling
* isotonic regression

where applicable.

Learn model/language-specific reliability.

Example:

```text
Qwen:
Romanian reliability = X
Russian reliability = Y
RO→RU switch reliability = Z

Whisper:
Romanian reliability = A
Russian reliability = B
RO→RU switch reliability = C
```

Use measured values.

Never fabricate them.

---

# UNCERTAINTY-TRIGGERED REPROCESSING

Do not run expensive multi-pass decoding unnecessarily on every second of audio.

Identify uncertain spans.

Examples:

* ASR models disagree
* language transition suspected
* low acoustic confidence
* medication detected
* number detected
* short isolated word
* unusual vocabulary
* diarization overlap
* low volume

Then spend more compute.

Conceptually:

```text
easy region
→ one/two engines

uncertain region
→ all engines
→ alternative decode
→ larger context
→ candidate fusion
```

This gives us high accuracy without unreasonable latency.

---

# SINGLE-WORD CODE SWITCHES

This case MUST have dedicated tests.

Example Romanian sentence with one Russian word:

```text
Trebuie să verificăm давление înainte de procedură.
```

Do not permit:

```text
Trebuie să verificăm davlenie înainte de procedură.
```

unless the actual speaker deliberately used Latin/transliterated terminology and evidence justifies it.

Similarly test one Romanian word inside Russian speech.

Generate a dedicated regression suite containing:

* one switched word
* two switched words
* switched medical term
* switched number/unit context
* switched colloquial term
* switched proper noun
* switch immediately after a pause
* switch with no pause
* switch during fast speech

---

# MOLDOVAN / REGIONAL ACCENTS

Accuracy on generic Romanian and Russian benchmarks is not enough.

Build a Moldova-specific evaluation track.

At minimum separate results into:

```text
Romanian — standard
Romanian — Moldovan accent

Russian — standard
Russian — Moldova speakers

Romanian-dominant RO/RU code-switch
Russian-dominant RU/RO code-switch
```

Do not report one blended WER and hide the hard cases.

---

# EVALUATION DATA

Search for legitimate publicly usable evaluation/training data for:

### Romanian

* Common Voice
* FLEURS
* other reputable Romanian speech corpora
* Moldovan Romanian datasets where licensing permits

### Russian

* Common Voice
* FLEURS
* reputable Russian speech datasets
* Moldova-relevant Russian recordings where legally available

### Code switching

Search specifically for:

```text
Romanian Russian code-switch ASR
Moldovan Romanian Russian bilingual speech
Moldova code switching corpus
Romanian Russian mixed speech dataset
```

Respect dataset licenses.

Do not silently train on material whose license does not allow it.

---

# OUR OWN CODE-SWITCH TEST SET

If a suitable public RO/RU code-switch benchmark does not exist, create the infrastructure for our own.

Define categories:

### CS-01

90% Romanian / 10% Russian.

### CS-02

90% Russian / 10% Romanian.

### CS-03

single switched word.

### CS-04

two-word switched phrase.

### CS-05

full switched sentence.

### CS-06

rapid repeated switching.

### CS-07

Romanian + Russian + English.

### CS-08

medical terminology switching.

### CS-09

numbers/dosages during switching.

### CS-10

overlapping speakers using different languages.

Synthetic/TTS audio may be used for ENGINEERING REGRESSION TESTS.

However:

DO NOT claim real-world ASR accuracy using only synthetic TTS.

Clearly separate:

```text
synthetic regression
```

from:

```text
human-recorded accuracy benchmark
```

---

# REQUIRED METRICS

Measure:

## Standard transcription

```text
WER
CER
```

for Romanian and Russian separately.

## Code switching

Implement metrics for:

```text
mixed-language WER
Romanian-span WER
Russian-span WER
embedded-language word recall
embedded-language word precision
code-switch boundary detection
native-script accuracy
```

## Clinical metrics

Implement:

```text
medical-term error rate
medication-name accuracy
number accuracy
dosage accuracy
measurement accuracy
proper-name accuracy
```

## Combined system

Measure:

```text
speaker-attributed WER
```

where annotated data allows.

---

# CODE-SWITCH TERM RECALL

This metric is especially important.

For an utterance:

```text
90 Romanian words
10 Russian words
```

I need to know specifically:

**How many of those 10 Russian words were captured correctly?**

Do not let ordinary WER hide this.

A system could have excellent overall WER while missing every minority-language word.

Therefore report:

```text
Embedded Russian Recall
Embedded Russian Precision

Embedded Romanian Recall
Embedded Romanian Precision
```

for code-switched samples.

Treat these as first-class quality metrics.

---

# SCRIPT ACCURACY

Measure whether words appear in their expected writing system.

Example:

Correct:

```text
tensiunea este mare, давление este 150
```

Potential failure:

```text
tensiunea este mare, davlenie este 150
```

Measure this separately.

---

# TRANSCRIPT PROVENANCE

Every final segment should maintain enough metadata to explain where it came from.

Internally preserve something conceptually like:

```json
{
  "final_text": "Trebuie să verificăm давление.",
  "start": 12.2,
  "end": 14.7,

  "speaker": "spk_02",

  "hypotheses": {
    "qwen": "...",
    "whisper": "...",
    "parakeet": "..."
  },

  "languages": [
    "ro",
    "ru"
  ],

  "confidence": 0.93,

  "reconciled": true
}
```

Do not expose all of this clutter to clinicians by default.

But retain it for debugging/audit.

---

# NO HALLUCINATED MEDICAL CORRECTION

An LLM may optionally help with:

* formatting
* punctuation
* candidate ranking
* obvious orthographic normalization

ONLY AFTER the acoustic transcription has been produced.

It must NOT freely rewrite clinical content.

Keep:

```text
RAW AUDIO-ASR TRANSCRIPT
```

separate from:

```text
NORMALIZED TRANSCRIPT
```

Any normalized change should be traceable.

Never allow a language model to invent:

* diagnosis
* medication
* dose
* lab value
* measurement
* symptom
* participant statement

because it appears medically plausible.

---

# TIMESTAMPS

Obtain high-quality word timestamps.

Do not assume one forced aligner supports every language.

Verify current supported languages before implementation.

If a forced alignment model supports Russian but not Romanian, do NOT silently use it for Romanian.

Use the strongest verified alignment path for each language.

For mixed-language text:

* align individual words/spans
* preserve language switches
* combine timestamps consistently

Timestamp errors must not corrupt diarization.

---

# DIARIZATION

Keep the previously specified:

**Nemotron-3-Diarization**

as the primary diarization engine.

Use maximum-context final processing.

Maintain:

```text
speaker
+
word
+
timestamp
+
language
```

Example final representation:

```text
00:12.22 – 00:15.84
Dr. Popescu [ro]:
Pacientul a venit dimineață.

00:15.85 – 00:18.41
Dr. Popescu [ro→ru]:
După aceea a spus что ему стало хуже.

00:18.90 – 00:20.20
Patient [ru]:
Да.
```

Do not let diarization segmentation force language segmentation.

They are separate problems.

---

# OVERLAPPING SPEECH

Overlapping speech is difficult and must not simply be dropped.

If Nemotron reports overlapping speakers:

* retain the overlapping interval
* attempt ASR appropriately
* do not force all words onto one speaker

Create tests where:

```text
Doctor speaks Romanian
Patient interrupts in Russian
```

This is a high-value real-world code-switch scenario.

---

# GPU STRATEGY

Use both RTX 5080 GPUs.

Benchmark placement rather than assuming.

A reasonable starting point is:

```text
GPU 0:
Qwen3-ASR-1.7B
Qwen streaming

GPU 1:
Nemotron diarization
Parakeet
speaker embedding model
```

During finalization, schedule:

```text
Whisper large-v3
```

where VRAM permits.

Do not assume GPU memory is pooled.

Each RTX 5080 has its own VRAM.

Implement a resource scheduler so final-pass models can share GPUs intelligently.

Models should remain loaded if memory permits.

Avoid constant load/unload cycles.

---

# PERFORMANCE PROFILES

Implement at least:

## LIVE

Goal:

```text
low latency
high practical accuracy
revision allowed
```

Suggested engines:

```text
Qwen3-ASR-1.7B streaming
+
Parakeet
+
Nemotron
```

## FINAL MAX ACCURACY

Goal:

```text
maximum transcription quality
```

Use:

```text
Qwen3-ASR-1.7B
+
Whisper large-v3
+
Parakeet
+
Nemotron final pass
+
code-switch resolver
+
ASR fusion
+
uncertainty reprocessing
+
medical validation
```

The UI should automatically replace provisional text with final text when processing completes.

---

# FINE-TUNING PREPARATION

Once the baseline pipeline works and measurements exist, create a training/fine-tuning path.

DO NOT fine-tune before establishing baselines.

Prepare support for future adaptation using:

```text
Romanian medical speech
Russian medical speech
Moldovan accents
RO/RU code-switched speech
```

Prioritize genuine human speech.

Potential augmentation may include:

* room impulse responses
* hospital background noise
* microphone distance
* gain changes
* reverberation
* mild speed variation
* overlapping voices

Do not distort audio so heavily that labels become invalid.

---

# CODE-SWITCH TRAINING DATA

For future adaptation, make it possible to create examples containing:

```text
Romanian context
+
Russian insertion
```

and:

```text
Russian context
+
Romanian insertion
```

at different frequencies:

```text
1%
5%
10%
20%
50%
```

Include:

* phrase-boundary switches
* word-level switches
* rapid switches
* medical terminology
* common Moldovan bilingual expressions

Synthetic examples may supplement real recordings.

They must not replace real bilingual speech.

---

# DOMAIN ADAPTATION

Eventually we should be able to train/evaluate a domain-adapted model using verified hospital audio.

Prepare:

```text
training/
    prepare_data.py
    augment.py
    manifests.py
    evaluate.py
```

Do NOT start storing real patient audio in training datasets without an explicit data-governance path.

---

# BENCHMARK BEFORE AND AFTER EVERY OPTIMIZATION

Every change intended to improve accuracy must be measured.

Examples:

```text
Does denoising improve WER?

Does longer context improve code-switch recall?

Does Qwen context prompting improve medication names?

Does ROVER improve mixed-language WER?

Does forcing Russian on uncertain spans help?

Does Whisper improve Qwen failures?

Does Parakeet improve timestamp quality?
```

Do not keep complexity that does not measurably help.

---

# MODEL SELECTION MUST BE EMPIRICAL

At the end I want a table similar to:

```text
                           RO WER   RU WER   CS-WER   RU-in-RO Recall
Qwen3-ASR-1.7B
Whisper large-v3
Parakeet
Qwen + Whisper
Qwen + Whisper + Parakeet
Final Secure MOM pipeline
```

Populate it ONLY with measurements actually performed.

If no human-labelled dataset is available for one metric, say:

```text
NOT MEASURED
```

Do not invent values.

---

# SPECIAL REGRESSION TEST

This exact category is mandatory:

A sentence containing approximately:

```text
90% Romanian
10% Russian
```

where the Russian consists of only one or two words.

Create multiple examples.

The system must not:

* ignore the Russian word
* Romanianize it
* transliterate it arbitrarily
* translate it
* remove it
* hallucinate a different Russian term

Do the reverse:

```text
90% Russian
10% Romanian
```

as well.

---

# ACCEPTANCE PHILOSOPHY

Do NOT declare success merely because:

```text
Romanian works
Russian works
```

The task is successful only when we have separately tested:

```text
Romanian
Russian
Romanian→Russian switching
Russian→Romanian switching
single-word switches
medical switches
numbers during switches
rapid switches
overlapping bilingual speech
```

---

# OFFLINE REQUIREMENT

Everything necessary for normal runtime must be cacheable locally.

After model acquisition:

```text
DISCONNECT INTERNET
```

and verify:

* ASR works
* diarization works
* code-switch resolution works
* speaker identification works
* finalization works

No cloud ASR.

No cloud diarization.

No external LLM required.

No remote audio upload.

---

# TEST WITH REAL AUDIO

Do not stop after loading checkpoints.

Run actual WAV/audio samples through:

```text
Qwen
Whisper
Parakeet
Nemotron
fusion pipeline
```

Verify actual output.

If multilingual human test recordings exist in the repository, use them.

If not, create a simple recording utility so we can quickly record:

```text
Romanian
Russian
RO/RU mixed
```

samples and obtain immediate benchmark results after manually supplying ground truth.

---

# FRONTEND

Expose useful uncertainty without overwhelming the clinician.

Normal UI:

```text
Dr. Popescu
Pacientul spune că давление este ridicat.
```

Potentially uncertain medical information:

```text
Dr. Popescu
Administrați [50 mg ?]
```

Allow user to inspect alternative hypotheses for flagged spans.

Do not highlight ordinary low-value differences unnecessarily.

---

# SEARCH / VERIFY BEFORE FREEZING DEPENDENCIES

Before implementation, check current official documentation/repositories for:

* Qwen3-ASR
* Whisper
* NVIDIA Parakeet
* NVIDIA Nemotron
* NeMo
* CUDA / PyTorch RTX 5080 compatibility
* vLLM
* faster-whisper/CTranslate2

Use the latest stable compatible versions.

Do not use random forks when official implementations work.

Record exact commit/package/model versions in the project.

---

# DELIVERABLES

Implement all practical portions directly in the repository.

At completion provide:

## 1. Architecture actually implemented

Not aspirational architecture.

## 2. Models

Exact:

```text
model ID
revision
precision
device
runtime
```

## 3. Installation

Exact commands.

## 4. Model download

Exact commands.

## 5. Run

Exact commands.

## 6. Offline verification

Exact commands.

## 7. Accuracy measurements

Actual measurements only.

## 8. Code-switch measurements

Especially:

```text
Embedded Russian Recall in Romanian speech
Embedded Romanian Recall in Russian speech
```

## 9. Performance

Actual:

```text
live latency
RTF
GPU VRAM
RAM
finalization time
```

## 10. Failure cases

Show examples the system still gets wrong.

## 11. Files modified

List them.

## 12. Tests

Show commands and outcomes.

---

# DEFINITION OF DONE

Do not consider the ASR work complete until:

* Qwen3-ASR-1.7B runs locally
* Whisper large-v3 runs locally
* Parakeet runs locally
* Nemotron diarization runs locally
* Romanian transcription works
* Russian transcription works
* Romanian/Russian mixed transcription is explicitly tested
* one-word Russian switches inside Romanian are explicitly tested
* one-word Romanian switches inside Russian are explicitly tested
* native scripts are preserved
* Romanian diacritics are preserved
* medical terms are tested
* medications are tested
* numbers/doses are tested
* ASR disagreement detection works
* uncertainty-triggered reprocessing works
* final-pass multi-model reconciliation works
* speaker attribution works
* offline mode works
* benchmarks exist
* no fake accuracy claims exist
* no cloud transcription is required
* README explains everything

---

# MOST IMPORTANT PRINCIPLE

I do not want:

**"a multilingual transcription system."**

I want:

**the highest-accuracy Romanian/Russian bilingual medical transcription pipeline we can build locally on this hardware.**

If one model is excellent on Romanian but misses Russian insertions, that is not good enough.

If another model is excellent on Russian but destroys Romanian diacritics, that is not good enough.

If overall WER looks good because 90% of a sentence is Romanian while every Russian insertion is wrong, that is not good enough.

Optimize specifically for the minority-language words inside majority-language speech.

Use the available compute.

Generate competing hypotheses.

Use longer context.

Reprocess uncertainty.

Measure everything.

Keep changes audio-grounded.

Do not hallucinate medical information.

Do not stop at the first working solution.

Iterate until additional complexity stops producing measurable gains.

IMPLEMENT IT.
