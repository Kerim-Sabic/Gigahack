# Resource-aware long audio (2026-09-26)

The fixed 1 GiB upload, two-hour decode, and 3,601-chunk recording limits contradicted the
requested long-recording workflow. Removing those numbers alone would leave WAV's 32-bit size
boundary, memory growth during assembly, browser compatibility, and disk exhaustion unresolved.

Uploads now default to no operator-imposed byte/duration cap. Optional MOM_MAX_UPLOAD_BYTES
and MOM_MAX_AUDIO_SECONDS restore an explicit deployment cap; zero disables that cap. The
5 GiB minimum free-space reserve remains. Admission checks both multipart temporary storage
and the data volume, conservatively budgeting the input copy. Membership is checked before an
upload body is parsed. Copying, recording chunks, assembly and decoding check free space.
These checks are not an atomic reservation against unrelated processes or concurrent writers;
filesystem failures return storage errors and never acknowledge an unsaved chunk. WSL operators
must also provision the host volume backing their Linux filesystem. No data is deleted to make room.

The decoder has an inactivity watchdog based on output growth and actual child CPU activity,
not a fixed five-minute wall limit. Its stderr buffer is bounded and the child is reaped on
failure. ffprobe requests only needed fields and retains a bounded 30-second metadata timeout.
Actual positive decoded samples govern the canonical timeline. Original input remains retained.
A busy logical loop is not guaranteed to be detected by an activity watchdog, and API-process
crash recovery during ingestion still needs full qualification.

FFmpeg normalization uses RF64 automatically when needed. A focused local reader supports
only the app's uncompressed PCM16 mono RIFF/RF64 output, validates 64-bit sizes and source extent,
and performs bounded sample reads. It is not a replacement upload decoder. Recording assembly
writes the known frame-count header, fetches metadata in 256-chunk pages, validates chunk hashes
and lengths, and publishes only after fsync. Sequence/count values retain JavaScript's exact
integer bound rather than a duration-based cap. No new dependency was introduced.

Browsers receive at most ten minutes of virtual standard WAV per request, streamed in 64 KiB
buffers with byte-range support. This avoids relying on browser RF64 support and creates no
extra audio files. Source sample offsets remain explicit. The player shows the original source
interval, has previous/next controls, and advances normal continuous playback to the next
section. Evidence playback ends at its contextual excerpt. The original authorized full-audio
endpoint remains available for export. Clip access requires meeting membership.

## Observed checks

- Windows: 165 backend tests passed, two Linux-specific checks skipped; 11 frontend tests and
  strict build passed. Linux RF64 checks: six passed, including real sparse-file reads and
  exact clip extraction beyond 4 GiB. RF64 interoperability uses an actual FFmpeg-generated file.
- Storage failure stops/reaps a real decoder child; stalled-child cleanup passes. Low storage
  rejects upload and does not acknowledge a chunk. Existing atomic-publication tests pass.
- Recording assembly passed with 3,602 acknowledged metadata entries and actual PCM reads,
  resampling and sample-count validation. This does not establish physical microphone endurance.
- Actual isolated HTTP upload: 1,728,000,044 bytes of locally generated 48 kHz stereo silence,
  9,000 seconds. Normalization preserved 144,000,000 canonical samples. Tail clip and byte-range
  checks passed. Elapsed 67.39 seconds; sampled API-plus-decoder peak RSS 105,623,552 bytes.
  This was development hardware, not the target laptop. Report: local run
  long-upload-1790377231446247152. No speech or LLM accuracy claim follows from silence.
- Actual CUDA Whisper processed that entire canonical recording in 30 bounded checkpoints,
  22.02 seconds overall, with zero segments/candidates/deliveries. Peak model-stage RSS was
  2,686,316,544 bytes. GPU process allocation remained unmeasured. Report: local run
  long-asr-1790377469871017200. Silence is much easier than a 2.5-hour speech meeting.
- New short CUDA silence check passed in 7.36 seconds. The isolated browser/API/PDF/Mailpit
  fixture passed, including source playback, localized UI persistence and 200-percent DOM
  checks. Inference in that browser fixture is explicitly synthetic; zoom-image limitations remain.

A separate actual browser run on the 9,000-second file passed next/previous 600-second
section navigation and a jump to source seconds 8988–9000, with the browser reporting the
correct 12-second excerpt duration. The transcript navigation marker was explicitly seeded
synthetic test content, not recognized speech. No page errors were observed. Earlier test-script
selector/API mistakes are retained in local logs and were corrected before this passing run.

Still open: bounded aggregate transcript/extraction state, extraction checkpoints, long speech
accuracy and late reconciliation, long optional-diarization memory/identity continuity, full
crash/restart ingestion, concurrent-storage pressure, and target laptop qualification. There is
no claim of infinite capacity, perfect transcripts, or an application that can never fail.

Primary format reference: [FFmpeg WAV muxer documentation](https://ffmpeg.org/ffmpeg-formats.html#wav).
The reader/header code is local implementation of the format, not copied third-party source.
