# 023 — Supplied transcripts enter the normal review workflow

The user requested a local Medpark test meeting using supplied audio and a supplied
speaker/timestamp transcript, with current test date/time. Recognition is not run
for that import: the transcript-only job performs ordinary local text extraction.

The import endpoint enforces account membership, write role, current revision,
asset ownership, no active processing, and no replacement of existing transcripts.
Identical retries are idempotent. The UTF-8 source is retained beside its audio,
addressed by SHA-256. Each segment retains its source index, supplied labels,
original text and import provenance. Names are anonymous speaker labels; apparent
language headings are unverified metadata. End anchors are inferred from the next
distinct start; equal starts overlap. No word alignment or audio verification is
claimed. Out-of-order anchors sort chronologically without losing original order.

The UI provides transcript import, visible import provenance, optional meeting
time and draft notes. Schema migration 006 adds these optional fields; existing
data is preserved. Notes/time are included in versioned minutes and escaped as
plain text. Changing metadata invalidates the current snapshot revision. Older
metadata clients that omit the new fields retain their existing values.

No new dependency or model. Private source files, account credentials, runtime
state and clinical drafts remain outside Git. Approval and delivery remain separate.

Validation: actual Medpark source imported as 234 segments, original hash retained,
702.5493125-second audio attached, both transcript pages and playback exercised.
Backend checks after schema integration: 238 passed / 2 platform skips. Frontend:
12 tests passed and strict build passed. Initial integration failures in review
handling and positional test inserts were corrected before final verification.

The user then requested stopping processing and preparing the workflow directly
from the supplied transcript. The transcript-only model pass was cancelled before
publication. Source-based draft authoring validates every exact quotation and the
complete source revision map, requires no active job or existing candidate draft,
and creates unreviewed candidates with explicit audit provenance. It does not
approve or send minutes. The assistant checked 14 source-backed items for this
test, keeping uncertain fields empty, and created an unapproved revision 17 preview.
The original transcript has 234 entries; all source hashes and audio are retained.
Verification: no active jobs, approvals or deliveries for this meeting; browser
shows the minutes draft and disabled send button. The new local test account was
provisioned under the user’s explicit request for login details; credentials are
private output/runtime files, never repository content.
