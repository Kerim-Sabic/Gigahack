# Continuation results

## Reproduced baseline — 0363960

Windows, Python 3.12.10, RTX 5080 development machine. Target laptop not observed.
No application-owned services were running; required local ports were free.
Prepared model and native hashes were reverified without downloads.

- Backend: 80 passed; one Starlette test-client deprecation warning.
- Frontend: 6 passed; strict build and Python lint passed.
- Explicit fixture browser, RO/RU checks and actual Chromium zoom/control checks passed.
- Actual GPU silence evaluation: zero segments/candidates/deliveries, 5.657 seconds.
- Actual complete text baseline run `1790361868551892300`: 23 pass, 2 fail, 5 outside text scope.
  Both T01 and T10 reproduced. All original specifications and assertions remain unchanged.
- Inputs, raw replies, parsed candidates, validation checks and projections are retained in the
  ignored evaluation directory; command logs are under `.runtime/continuation-baseline-0363960`.

Baseline stage SHA-256: `679709e7231462fbda787b5379bdb2e937d85644f575f4026360c4d56d9f027f`.
Model manifest SHA-256: `ac30294ee1b83ef28f337b21016ca467f550df50b145186b0bae41baecf2d2e7`.
Original corpus SHA-256: `c5ef9d1cbc90755f9e4f5eeb4ae699d6c1c17e5a808fdab20624bba4f85f68e0`.

## Root-cause evidence before changes

T01: the initial generation emits proposal (28 September), amendment (30 September), confirmation.
The consistency pass changes the proposal to confirm and the correction to inform. The category pass
then calls the correction information. The final confirmation supplies no date. The reducer correctly
refuses an information event to overwrite a confirmed commitment, so 28 September survives. This is
primarily contextual speech-act classification/confirmation failure, not date normalization.
The consistency payload omits the initial candidate kind/category and the prior candidates' dates.

T10: the original and final candidates carry bare values `20` and `25` despite their cited source
containing `20 beds` and `25 beds for Ward A`. The later field pass proposes mismatched value/source
support, which validation rejects. No structured amount/unit/scope is retained. The category and
final amount are correct, but the unit is already missing before reduction. The renderer also has
no quantity column; UI/JSON/PDF verification must cover the fix, not just parsing.

## Evaluation separation

Sixteen synthetic development variations and six held-out variations are versioned separately.
The held-out set is frozen before implementation and has not been run or used to select changes.
These AI-authored RO/RU/EN examples still need native linguistic review. They do not substitute for
human-recorded audio, WER/critical-error assessment or clinical validation.


## Development attempts (all retained)

- Attempt 1, run `1790362226457408500`: 3/4 focused cases pass. T01 fixed, but T06
  regresses to tentative classification. Prior and current candidate context were both expanded.
- Attempt 2, run `1790362458520799600`: 4/6 pass. T01, T09, T15, T30 pass;
  T06 remains tentative and T10's category regresses to action. T10 now retains literal
  `25 beds`, structured amount/unit/scope and source evidence. Explicit multilingual prompt
  wording alone did not fix the classification anchoring.
- Attempt 3, run `1790362697149107400`: all six focused cases pass, including T01/T06/T10.
  Current candidate kind/category hints were removed from the independent check; enriched prior
  event context remains. This avoids feeding the disputed classification back as a hint.
  Stage SHA-256 `48bd0a5a328fa10a99bf21b85db85dd8b1d456b43c6f7072f9dd3233f55dd13c`.
- After attempt 3, literal quantity ambiguity checks were strengthened for unrecognized units.
  Backend/domain/API suite: 93 passed, one existing Starlette deprecation warning. A direct pytest
  invocation hit an inaccessible host temporary directory; the documented `scripts.mom test`
  runner uses its project-local test directory and passed. No host permissions were altered.
- Attempt 4, run `1790362810483903700`: full original suite **25 text-model PASS, 0 FAIL,
  5 NOT RUN in this text run**. Stage hash matches attempt 3; quantity helper hash is
  `351ddfb788d483271f26c0e7e1df4fae96fd84ce66167abc484c4ddd697a33f0`.
  The original corpus and assertions are unchanged. T08/T11/T26/T29 require audio and T22
  requires stateful workflow. Earlier separate T22 and T26 silence evidence remains distinct.
- Latest backend suite: **95 passed**, lint passed. Variation evaluator checks reject omitted
  or extra commitments, wrong dates, missing structured units and wrong scope.
- Attempt 5: the separate 16-case development variation run is in progress; held-out cases remain
  unrun. A fixed-corpus pass does not establish general semantic or multilingual audio accuracy.

Quantity derivation uses only the event's own literal, revision-valid citations; it never converts
units, borrows another topic's unit or changes the speech act. Human value replacement clears stale
machine quantity structure. API tests verify immutable JSON/HTML snapshots after replacement.
The HTML/PDF template now includes the quantity column; actual UI/PDF visual verification is pending.
No external dependency, model or model revision was added.
