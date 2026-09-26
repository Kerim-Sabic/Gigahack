# Bounded recovery hypotheses for speech gaps

Previously the app compared only Whisper-derived segments with Parakeet. Diarization could
flag possible speech outside those segments, but those intervals never reached a recognizer.
When both optional stages are selected, diarization now runs first. Suspected speech gaps
are split into review rows no longer than the configured recovery window. Parakeet processes
these intervals independently of the existing transcript comparison fraction.

Defaults are 20 seconds of primary audio plus two seconds of context on either side,
at most 24 seconds total. A longer empty primary result receives one 10-second subdivision
pass. Short empty clips are not repeatedly retried unchanged. Configuration rejects a retry
window that is not shorter and total context exceeding 25 seconds. All work stays in the
existing verified optional runtime, with batch one and the same supervisor/GPU admission.
No dependency, model revision, license or framework changed.

Each result, including empty output, is atomically checkpointed with an audio/settings/runtime
identity and payload checksum. Corrupt checkpoints are recomputed. Derived WAVs are bounded,
checked against the storage reserve, and removed after each attempt. Raw text and timestamp
output are retained. Aggregate transcript/result state is still proportional to recording size;
this does not establish unlimited-file or target-laptop qualification.

Schema 4 adds recovery hypotheses to existing job-bound audio observations. The authorized,
paginated endpoint exposes them with exact source and primary intervals. Each production row
contains at most one initial and two retry hypotheses. The review UI plays either the flagged
interval or the full context, distinguishes initial/retry output, and warns about repeated
nearby words. It never substitutes these hypotheses into transcript, extraction or approval.
Existing warning counts remain frozen in minutes. A dedicated reviewed gap-insertion workflow
is still pending; users must not mistake surfaced hypotheses for completed corrections.

## Actual verification

- 167 backend tests pass on Windows, with two Linux-only skips; 11 frontend tests, lint and
  strict build pass. Tests cover exact source samples, bounded intervals/retries, checkpoint
  reuse/corruption, persistence, membership and separate context playback.
- Actual optional adapter run `app-optional-1790417657788376240` used the supplied recording
  and replayed earlier real Whisper segments. Both real optional models ran in an isolated
  network namespace; 194 alternatives and speaker labels persisted. This is not a fresh full
  ASR/LLM workflow. No candidate, approval or delivery was created.
- Total 144.57s; stage receipts: diarization 45.22s and Parakeet 95.93s. Peak process-tree RSS
  2,467,479,552 and 3,794,857,984 bytes respectively. Per-process VRAM remains unmeasured;
  device totals include unrelated workloads and do not qualify the 8 GB target.
- All 56 detected gaps have persisted hypotheses: 52 nonempty context outputs and four empty.
  There are 451 context-word hypotheses, of which 115 midpoints fall inside 35 flagged gaps.
  These are model outputs/timestamps, not human-confirmed recovered words. Longest actual
  context clip was 13.0684s; this gap set did not exercise the shorter-retry branch.
- Separate actual run `recovery-stress-1790417989021120246` used preselected 90–150s and
  660–690s source intervals, not the production gap set. Five initial windows included three
  empty results; six shorter retries produced one nonempty and five empty outputs. All 11
  hypotheses and checkpoints are retained. This verifies actual retry execution, not improved
  accuracy or complete recovery. The production detector was not changed to fit these cases.
- Browser fixture `fixture-bb137a3145874f0ba5a1e3866866226c` passes real UI/audio/API/PDF/Mailpit,
  RO/RU persistence and zoom DOM checks. Its recovery text is explicitly synthetic, not model
  accuracy. The normal-scale review image was inspected. Two earlier browser attempts exited
  because the live inference run held supervisor admission; logs are retained. They did not
  bypass the single-worker lock. Headless zoom images remain unqualified.

Empty hypotheses, uncertain language switches, speaker accuracy, reviewed insertion,
full long-speech behavior and human/target qualification remain open.

Follow-up: Decision 017 implements and verifies reviewed insertion and transcript-only
reanalysis. The acoustic and hardware qualification limits above remain open.
