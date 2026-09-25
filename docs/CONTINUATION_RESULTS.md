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
