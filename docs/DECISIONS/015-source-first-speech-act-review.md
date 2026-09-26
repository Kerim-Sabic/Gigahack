# Source-first speech-act review

The known Russian tentative-date failure H03 reproduced on the current worker in run
`1790415514152556100` (40.43 seconds). The first extraction paraphrased the tentative
question as a definite move and inferred `changed_fields: [due]`. The consistency pass
received both that paraphrase and the original evidence and still returned `amend`.
The source citation was literal, but the interpretation was wrong.

The classification context now supplies the candidate's subject and evidence without
its generated paraphrase or inferred field values/changes. Original source turns remain
available, along with bounded earlier-topic context for reference resolution. The prompt
distinguishes an asserted correction from a suggestion to change an existing agreement.
There is no language keyword list, fixture-specific date rule, model change or new dependency.

Actual Qwen run `1790415860675546400` passed H03 in 38.08 seconds: the June 9 agreement
remains confirmed and the June 11 alternative remains pending. This is a known regression,
not untouched held-out evidence. Original gold and failed artifacts remain unchanged.
The new `speech-act-development.json` contains eight synthetic EN/RO/RU/mixed-language
contrasts authored before their execution. They assess text interpretation, not acoustic
recognition, language labeling or human-adjudicated accuracy.

Run `1790415949896801800` passed all eight contrasts in 307.28 seconds on the development
GPU. Both tentative alternatives and definite amendments passed in each language condition.
Backend tests: 165 passed / two Linux-only skips on Windows. Lint and strict web build pass.
Original corpus run `1790416268868794800` passed all 25 text cases; five audio/stateful
cases were outside this run. The evaluator deliberately exits nonzero for incomplete
30-case coverage even when every executed text case passes. The prior 16-case development
corpus and the remaining held-out cases have not been rerun with this change.

This is still model interpretation. Removing one source of anchoring does not prove all
speech acts correct; human evidence review remains necessary. The separate category/field
passes and existing deterministic evidence/date/state validation remain in place.
