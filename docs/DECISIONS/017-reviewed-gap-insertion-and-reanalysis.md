# Reviewed transcript additions and reanalysis

Recovery hypotheses were previously readable and playable but could not become a new source
passage through the app. A secretary/member can now enter words for a flagged speech gap after
explicitly checking the interval. The form starts empty: surrounding model context is never
copied automatically. Optional speaker text is a manual assertion, not inferred identity.

The new API uses the exact stored gap bounds, verifies the asset extent and rejects overlaps
with existing nonempty transcript spans. It enforces membership/write role, meeting revision,
terminal processing state, nonblank text/reason and explicit review. A schema-5 receipt binds
the job/interval, actor and request hash to the inserted segment. Repeated identical submissions
return the same segment, even after the meeting revision advances; conflicting submissions fail.
The raw record retains the reviewer, reason, source job, interval and original recovery outputs.
No per-word timing is fabricated. Subsequent wording changes use normal revision history.

Both transcript edits and additions mark the affected recording as needing analysis, invalidate
its nonexcluded source-linked candidates and advance the meeting revision. New snapshots and
acceptance are blocked until reanalysis finishes. Historical snapshots/approvals remain immutable
and stale; no new approval or delivery is performed automatically.

`transcript_only` jobs run extraction on saved transcript revisions and bypass speech/speaker
models. They preserve the earlier audio-review observations. Queue identity includes the mode
and source versions. Before publishing, the worker verifies the complete segment-ID/revision
set, including newly inserted or deleted segments. Failure leaves the pending-analysis marker.
An unchanged previously invalidated candidate returns to unreviewed state; a deliberately
excluded candidate is not reactivated. Reacceptance uses the latest accepted event for current
projection while retaining older accepted records for history.

Reviewed gap receipts remain visible in audio review. New minutes omit their resolved warning
counts; frozen earlier minutes retain their original warnings. Transcript-only jobs do not hide
unresolved flags from the latest actual audio analysis. The UI waits for analysis completion and
a review revision matching the meeting before enabling acceptance.

## Verification

- Windows backend: 170 pass, two Linux-only skips. After the acceptance-race fix all 48 API
  tests pass again. Coverage includes idempotency/conflict, overlap, active processing, viewer
  and nonmember denial, immutable snapshots, blocked stale approval, transcript-only execution,
  candidate re-review and concurrent segment insertion during extraction.
- Frontend: 12 tests, strict build and lint pass. A failed correction keeps typed wording;
  model text is not prefilled. No new dependencies or model changes.
- Browser fixture `fixture-e8c9cb98bf6f4aa7afabc6c5cd0e21a3` passes correction → transcript-only
  reanalysis → renewed review → snapshot/PDF/approval/Mailpit, plus RO/RU persistence and zoom
  DOM checks. Its text/audio inference is explicitly synthetic. Normal review image inspected;
  headless zoom images remain unqualified. The first browser attempt exposed a stale-review
  timing race; API/UI guards and an authoritative-state wait fixed it. Logs remain retained.
- Actual local Qwen run `reanalysis-1790419406579072000` completed in 43.47s through the
  production API insertion and worker. The synthetic Russian confirmed-date/tentative-change
  transcript kept June 9 confirmed and June 11 pending. Only an extraction receipt was created;
  no ASR stage, accepted event or delivery was created. This is a synthetic text test with a
  silent source, not real-recording acoustic accuracy or offline Windows qualification.

The private recording has not received fabricated human corrections. Native language/speaker
accuracy, complete fresh Medpark processing, long-speech limits, target hardware and the full
remaining acceptance matrix still require evidence.
