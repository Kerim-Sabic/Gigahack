# Durable stage artifacts and nonblocking recording finalization

Stage cache reuse now checks both the frozen input hash and actual output checksum. Missing,
partial, corrupt, wrong-input or non-object output/receipt pairs are recomputed. Stage input,
output and receipts publish through fsync and atomic replacement. The worker includes the
actual canonical-audio hash in the stage input, preventing stale cached output after changed
normalized audio. Completed stage progress still does not authorize database publication.

Remove the two-hour total stage timeout. The developer profile now sets an inactivity timeout
(default 1800 seconds). The worker observes changed work counters or CPU work in its owned
process tree using a monotonic clock. Timestamp-only display heartbeats do not count as work;
unavailable progress display does not stop observed active computation. Cancellation remains
available. This is not detection of every logical busy loop or a guarantee of eventual success.

Recording finalization previously held SQLite's writer transaction while assembling and
decoding the audio. It now claims finalizing in a short transaction under an OS-backed recording
lock, then processes audio outside the database lock and rechecks authorization before
publishing. Audio chunks are checksum-checked; assembled and normalized files are flushed
and atomically replaced. Decode/fsync failure leaves saved chunks and previously completed
artifacts intact. Retry after process loss can claim finalizing once its OS lock is released.
An identical repeated finish returns the already published asset, avoiding duplicate assets.

Tests cover corrupt stage cache pairs; three hours of synthetic observed progress without a
fixed timeout; a genuinely inactive timer; CPU activity with missing progress; interrupted
recording state; a separate database writer during decode; duplicate finish; concurrent finish;
decode failure retaining chunks; and failed file publication preserving a completed target.
Full backend after adapter checks: 140 PASS. Frontend: 10 PASS; strict build and Python lint pass. Actual CUDA
silence through the changed worker passes with zero segments/candidates/deliveries (6.19s).
These checks do not prove multi-hour linguistic quality or whole-app crash recovery.

Still open: upload size/duration limits, large canonical containers, long recording counts,
extraction checkpoints and bounded transcript state, complete application crash/fencing,
full-job ETA, target hardware, optional models and final offline/package qualification.

The optional diarization adapter now applies the frozen segmentation/embedding batch setting
and exposes pyannote hook progress. Optional stages use the same single OOM retry path as
core stages; diarization reduces both batches to one. A deterministic adapter contract test
passes; this is not actual optional-model inference qualification.
