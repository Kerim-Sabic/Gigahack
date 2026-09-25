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


Attempt 5, run `1790363037052101900`: **13/16 development variations pass**. D06 retains
correct approved date but calls the work a decision; D07 retains the date but calls the
report deadline information; D14 abstains on a clearly affirmed quantity with a negated
alternative. No invented prescribing action. EN/RO/RU/mixed corrections, later reference,
owner-only date preservation, ambiguous date, currencies and separate scopes pass their
exact checks. Gold labels are unchanged. Broader acceptance remains open.

Implementation `69e2684e4de0f49976aaae412e027d0d17bf4ca8` pushed; remote main hash
matched. CI run `36177502914` was in progress when checked, not yet claimed passing.
Next focused attempt clarifies work deadlines versus calendar decisions and explicit
negation versus genuine quantity ambiguity; all prior attempts remain retained.


- Attempt 6 `1790363248994481700`: D06/D07 pass after clarifying nominal work and work
  deadlines; D14 still abstains despite a negation instruction (2/3 pass).
- Attempts 7 `1790363318955170000` and 8 `1790363342973575600`: D14 still fails.
  Explicit descriptive-value wording and withholding the category hint alone do not fix it.
- Attempt 9 `1790363374787812600`: D14 passes after supplying all literal unit-bearing
  numeric spans as untrusted options, including both affirmed and negated alternatives.
  Interpretation remains model-proposed; exact source checks remain mandatory. The quantity
  structurer was then adjusted to preserve an already selected literal unit, rather than
  treating every other cited unit as ambiguity. Bare-number ambiguity still abstains.
- CI run `36177502914` **passed** for pushed `69e2684`. Later development changes are not
  covered by that CI result. Full original and development reruns are next.


Attempt 10 `1790363438326637700`: **22/25 text pass**, with regressions T10 (superseded
quantity lost), T18 (separate fact quantity lost), T19 (condition lost); five outside text.
Attempt 11 `1790363654347857600`: **13/16 development pass**, D11/D12/D16 category/state
failures. These full runs disprove the adequacy of the expanded initial/field prompts.
Those ineffective additions and category-hint removal are rolled back; only nominal-work
classification clarification and literal numeric option enumeration remain for the next attempt.

Quantity rendering replay (Windows, captured passing T10 output from attempt 4):
`quantity-replay-1aca3cc464424e9f88e3a743b4cd45cb`. Real API/browser review, field evidence,
immutable JSON/HTML and actual PDF pass. Inspected the rendered one-page PDF and UI screenshot;
PDF extracted text contains 25 beds, Ward A and historical 20 beds. This is explicitly replay,
not new inference or audio accuracy. First harness attempts exposed an exact-label mismatch
and a UI-loading race; fixed the harness. Native Chromium and current frontend build used.
The short PDF is legible, but final branding, pagination, multilingual/long templates,
approval labeling and refined output remain required. No standalone final PDF delivered yet.


Attempt 12 `1790363871245723300`: 2/3 original focused checks pass.
Attempt 13 `1790363899080255700`: 3/6 development checks pass.
Attempt 14 `1790364043409999500`: 5/7 original focused checks pass.
Attempt 15 `1790364112042751000`: 2/6 development checks pass.
All local artifacts are preserved. A concrete comparison bug was
found: initial bare amount and a later literal amount+unit were treated as disagreement.
Enrich the initial literal quantity before comparing passes, and always rebuild stale
quantity metadata. This fixes quantity comparison without semantic unit inference.

Prompt wording changes remain brittle on nominal work, language and negation. Next bounded
experiment restores the successful checkpoint's prompts and tests 384 local reasoning tokens
only for interpretation passes, with increased total completion budget and rendered-context
validation. Same pinned model/runtime; no new dependency or cloud call.
References inspected: [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-4B) and
[pinned llama.cpp b11146 server documentation](https://github.com/ggml-org/llama.cpp/blob/b11146/tools/server/README.md).
This experiment is not adopted or claimed passing before measured checks.


- Attempt 16 `1790364244145312600`: T06/T10/T19 all pass with bounded 384-token
  reasoning for independent interpretation. Initial extraction remains non-thinking.
- Attempt 17 `1790364296142684600`: 4/6 focused development checks pass; D07 and D12
  fail. Several reasoning passes reach their cap. No gold changes.
- Attempt 18 `1790364480137348400`: D07 and D12 both pass with a 768-token reasoning
  cap and general clarification of work deadlines versus resource/budget revisions.
- Attempt 19 `1790364630444995500`: full unchanged original corpus **25 PASS, 0 FAIL,
  5 NOT RUN**. Stage SHA-256 `cfcd371eb24220289e33f099c74f304ed14afe11993bc29a88801cf729a4e662`.
  This is actual local Qwen inference on development hardware, not target qualification.
- Attempt 20 `1790365368826297600`: full development variations running. Held-out set
  remains unrun until development selection freezes.
- Template checkpoint `750944e65bd28407188a9a4ead8f2f623fdb9662`: remote verified;
  GitHub CI **36181262970 passed**. Current semantic experiments are not in that commit.
- Configured-template T10 replay `quantity-replay-46be174d1fee4652b32fe98b1867778c`
  passes actual browser review and frozen JSON/PDF response with saved heading/introduction.
  Full local Mailpit fixture rerun waits for GPU admission; its earlier failed attempt is
  retained (worker lock conflict and missing select accessible name, subsequently fixed).


Attempt 20 `1790365368826297600`: **16/16 development variations PASS**, 0 FAIL.
Total case execution 708.46 seconds on the development host. Strict annotated commitments:
actions TP 10 / FP 0 / FN 0; decisions TP 4 / FP 0 / FN 0. Annotated fields:
owner 1/1, due 10/10, exact value 3/3, unit 4/4, scope 2/2, status 14/14,
quantity substring 2/2, pending alternative 1/1. These tiny synthetic denominators are not
population accuracy or clinical review. Unsupported meaning/human correction time remain unmeasured.
The supplementary `metrics-expanded.json` scores quantity-substring and pending annotations
that the initial metric omitted; raw results and original summary remain unchanged.

Freeze stage hash `cfcd371eb24220289e33f099c74f304ed14afe11993bc29a88801cf729a4e662`
for the first six-case held-out run (attempt 21). No held-out prompt tuning is authorized by
a failed result; preserve and report failures. Original and variation gold remain unchanged.

Configured-template replay PDF has now been rendered and visually inspected: saved heading,
introduction, 25 beds / Ward A and historical 20 beds are legible, with no one-page clipping.
Final PDF layout/approval/page-number/multilingual acceptance remains open.
Audio recording materials (8 development / 4 held-out scripts) and critical-span/WER scoring
are now authored. Five scorer tests pass; these are not recordings or observed audio accuracy.
Full backend suite at this point: 108 passed, one existing deprecation warning; lint passed.


Attempt 21 `1790366119505605300`: first held-out run **5 PASS / 1 FAIL**. H03 replaces
the confirmed 9 June 2027 lift inspection with a tentative 11 June Russian suggestion;
the latter is misclassified as amend. Literal evidence is valid in all six cases, showing
why citation validity is not semantic correctness. Strict annotated action precision/recall
are both 2/3 (TP 2, FP 1, FN 1); decision TP 2 / FP 0 / FN 0. Held-out corpus hash:
`213d3b5d5b40ccb207df9384e3734d3830b4dc62ec044a971b09c9905d8fd1e8`.
No prompts, gold or runtime files changed during this run. Semantic acceptance remains open.
Future work informed by this failure must treat it as a known regression, not reuse the same
case as untouched held-out evidence. This checkpoint does not claim broad Russian accuracy.

Current Windows backend suite: **109 passed**, one existing warning; lint passes.
Native browser fixture rerun passes in 12.513 seconds, no page errors: template configuration,
frozen template metadata, suggested recipient, review, snapshot, approval, SMTP acceptance and
actual Mailpit receipt. This run uses explicitly test-only ASR/extraction; it is integration
verification, not fresh speech/model accuracy. RO/RU UI, keyboard and DOM/layout zoom checks
also pass; headless zoom screenshots remain unqualified as documented by the harness.

Real generated instrumental audio run `music-1790366407304190100`: **PASS**, 20 seconds
through production CUDA ASR/worker, zero observed segments/candidates/deliveries in 5.594 seconds.
The waveform is an original local procedural tune; it uses no downloaded composition or voice.
This closes that synthetic T26 music branch alongside separate silence evidence, not all music
or difficult speech. Models and dependencies remain unchanged. Raw waveforms are ignored.
