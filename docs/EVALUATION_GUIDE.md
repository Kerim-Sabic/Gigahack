# Semantic evaluation and review protocol

Use synthetic, non-patient content. Preserve every attempt; do not edit gold to fit outputs.
The original 30 cases are in `tests/fixtures/adversarial.json`. Development and frozen
held-out variations are separate files. Native RO/RU validation has not been performed.

## Reproducible commands

- Original corpus: `python -m scripts.evaluate_text`
- Development: `python -m scripts.evaluate_text --corpus tests/fixtures/continuation-development.json`
- Held-out (only after development changes freeze): `python -m scripts.evaluate_text --corpus tests/fixtures/continuation-held-out.json`
- Nonspeech: `python -m scripts.evaluate_silence --condition silence` or `--condition music`; generated fixture scope only.
- Scope a debugging run with `--cases ID ...`; the summary records exactly which cases ran.
- Literal rendering replay of a passing captured T10 output:
  `python -m tests.quantity_rendering_replay .runtime/evaluations/RUN_ID`
  This uses a fresh test account/database and silence playback placeholder. It is **not a new
  inference/audio run** and cannot be used to claim new ASR or model accuracy.

The GPU evaluator takes the host lock. Do not overlap inference runs. Keep source stable
through each run. Outputs include original inputs, all raw generation attempts, parsed
candidates, literal validation, ordered projection, individual checks and configuration hashes.
Exit is nonzero for any failure or outside-scope original case; NOT RUN is never counted as pass.

## Scope of all 30 original specifications

| Cases | Required scope | Existing evidence and remaining gate |
|---|---|---|
| T01–T07, T09–T10, T12–T21, T23–T25, T27–T28, T30 | Text model and domain projection | Executable exact gold checks; latest attempted code must be rechecked independently of older passing revision |
| T22 | Stateful worker/replay/review/outbox | Separate executable `test_t22_overlapping_worker_results_and_replay_create_one_item_and_delivery`; text alone insufficient |
| T08 | Ambiguous acoustic numeric alternatives | Labeled ambiguous audio, preserved hypotheses and reviewer resolution still required |
| T11 | Actual overlapping speakers and uncertain owner | Labeled overlap audio plus diarization/manual handling still required |
| T26 | Silence **and** music | Separate real 20-second silence and generated instrumental music runs pass; arbitrary music remains unqualified |
| T29 | Clearly spoken noninterchangeable units and protocol context | Text variations are useful development checks; labeled clear audio remains required |

Human adjudication overlays all language/meaning cases. An exact match against AI-authored
synthetic gold is not native-language review or medical validation.

## Metrics and limits

The variation summary reports strict annotated final-commitment precision/recall separately
for actions and decisions. A correct match requires the expected category and every annotated
owner/date/value/unit/scope/status field. Omitted commitments count as false negatives;
additional commitments count as false positives. Unannotated semantic content cannot be
scored by this metric. An empty output never yields perfect recall. Undefined precision is
`null`, not 100%. Field checks include their denominators, exact case outcomes, valid-evidence
counts, candidate warning counts and missing owner/deadline counts for active actions.

Literal evidence validity proves a quote/revision relation, not that the claim follows from
that quote. Unsupported semantic statements, observed human corrections and review time
remain NOT MEASURED until an adjudicator supplies actual labels. Never relabel automated
failed checks as a measured number of human edits or minutes of work.

## Human and audio review worksheet

For each frozen input, retain the recording license/provenance, consent where applicable,
recording conditions, reference transcript, gold decisions/actions and source sample offsets.
Keep recordings/weights/datasets out of Git. A qualified language reviewer should annotate:

1. Words as heard, including unclear alternatives, negation, numbers, units and names.
2. Actual action/decision objects, category and source chronology, with owner/date/condition.
3. Every generated statement unsupported by the source, including harmless-looking additions.
4. Omitted commitments, wrong associations and incorrect supersession.
5. Each necessary UI correction, whether accepted/excluded/edited, and observed elapsed review time.

Compute WER on source-preserving text; report additional exact counts for names, numbers,
units, medical terminology and negation. Do not normalize away a consequential distinction.
Separate processing time from human review time and development from held-out recordings.
A second reviewer resolves disagreements. State reviewer qualifications and unreviewed
languages explicitly; never invent a clinician or native-speaker assessment.

## Versioned recording materials and executable scoring

`tests/fixtures/audio-development.json` contains eight synthetic EN/RO/RU/mixed recording
scripts; `audio-held-out.json` contains four separately frozen scripts. These files are
**materials, not recordings or measured transcripts**. Each carries unreviewed provenance,
recording status and critical token spans. Have a speaker read the script, then have a
reviewer transcribe what was actually heard. Any deviation belongs in that recording's
reference; do not score a TTS prompt or script as if it were verified acoustic ground truth.
Hold out recordings by speaker/session as well as script, and do not tune on the held-out set.

Record clean and quiet/distant variants separately (retain microphone, distance, gain,
room and sample-rate metadata). Record genuine two-speaker overlap on an additional clip:
two distinct speakers say “I will do it” concurrently after a task proposal. Annotate overlap
sample intervals and owner ambiguity; concatenated speech is not overlap. For ambiguous
0.5/5 mg, retain blinded listener alternatives instead of declaring one script reading
the true acoustic answer. Music and silence have empty references, separately sourced and
hashed; silence alone cannot pass the music requirement.

For a long-meeting recording, place a confirmed dated commitment near the beginning,
at least 30 minutes of unrelated synthetic discussion between it and a late amendment,
and a similarly named separate subject in the intervening discussion. Retain exact sample
positions, expected final item and superseded values. Separately exercise a long transcript
without claiming that it establishes long-audio ASR or sustained laptop performance.

To score a source-aligned clip, save one reference case (with verified `reference_text`,
`critical_spans` and `provenance`) and its actual worker ASR output, then run:

```sh
python -m scripts.score_audio --reference .runtime/eval/reference.json --observed .runtime/eval/whisper-output.json --output .runtime/eval/score-new.json
```

The command performs no inference. It records both input hashes and declared reference
provenance, and refuses to overwrite a report. Match the observed output to the audio and
model/runtime receipt yourself; current installed model files do not establish the provenance
of an earlier output. Scores retain decimals, date separators, accents, scripts and units.
An empty reference has undefined WER plus explicit insertion counts. Critical spans use
reference token positions, so another occurrence of a name cannot satisfy the annotated one.
Boundary insertions and meaning still require human review. Long recordings must be scored
in source-aligned clips; the scorer rejects an oversized alignment rather than truncating it.
Aggregate WER as total substitutions + deletions + insertions divided by total reference words,
not the unweighted mean of clip percentages. Report unannotated categories as unmeasured.

Current environment: installed local Windows speech voices are English only; no local
Romanian/Russian synthesizer was found. No multilingual audio accuracy, native review or
human correction rate is claimed from these materials or scorer tests.
