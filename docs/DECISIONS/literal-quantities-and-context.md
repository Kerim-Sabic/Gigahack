# Literal quantities and contextual classification

Date: 2026-09-25. Scope: continuation semantic fixes; no new dependency.

The T01 date normalizer was correct. An independent classification pass demoted a source
correction to information, which could not replace the prior commitment. Supply prior
candidate dates/owners/values and speech acts as context, while withholding the current
candidate's disputed classification from the independent check. Model linkage is a review
proposal, never authority. Literal source validation and mandatory review remain unchanged.

T10 lost the unit in initial candidate fields even though it was in the same cited turn.
Add an optional structured quantity, derived mechanically from literal revision-valid
citations adjacent to the existing extracted amount. Preserve lexical decimals/thousands,
raw span, unit, subject and evidence; do not convert units or create work from a number.
A bounded multilingual unit vocabulary is deliberately conservative. Missing/unknown or
ambiguous units remain explicit, including alternatives outside the vocabulary.

Retain the existing string value for compatibility and presentation. Owner-only changes
retain quantity evidence; reviewer replacement clears machine structure and retains human
provenance. Approved/older snapshot data is immutable. Include the new helper in runtime
hashes. Additive fields need no destructive migration. Minutes template version becomes 3.

Tradeoffs: this does not understand arbitrary quantities, establish source meaning, or
resolve medical ambiguities. Current source association can still be wrong semantically;
review and separate held-out/long/audio evaluation remain necessary. Full fixed text suite
passes 25/25 after the change; this is a regression result, not general accuracy.
