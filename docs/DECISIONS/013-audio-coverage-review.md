# Audio coverage observations (2026-09-26)

The supplied recording exposed two different limitations: diarized speech outside Whisper's
transcript spans, and empty second-recognizer hypotheses. A successful processing job must not
make these observations disappear. They do not prove that speech was missed: diarization can
mistake noise for speech, and model timestamps can disagree.

The optional adapters now persist source-clock observations in SQLite schema 3. Speech intervals
are unioned across speakers before subtracting the union of nonempty transcript spans. Gaps
of at least 8,000 samples (0.5 seconds at 16 kHz) are flagged. Smaller timing edges are omitted;
this threshold is not proof that short code switches were recognized. The check does not score
words, identify languages, certify speakers, or insert invented transcript text. Empty Parakeet
outputs are separately flagged at their original transcript span. Optional checks still require
the corresponding models; absence of flags does not certify complete coverage.

A completed stage atomically replaces its observations, making retries idempotent. Observations
belong to a job and are removed with that job during authorized retention deletion. An authorized,
paginated endpoint supplies the original asset and exact source times. The React panel shows
20 observations per page for the newest analysis of each asset and offers contextual playback.
Controls remain usable by read-only meeting members. Failed requests display a retry action.
Job state changes refetch the checks; transcript edits do not recompute historical observations,
and the UI states that limitation. No new dependency or model is introduced.

Snapshots freeze counts by job/asset/kind and include a localized warning in unresolved matters,
so HTML/PDF/JSON retain the same limitation after later observations change. This does not alter
explicit approval or recipient authorization. Source intervals remain available in the authorized
workspace. It is a review aid, not a substitute for improving recognition or manual corrections.

Applying this diagnostic to the already saved actual outputs in private run
app-optional-1790375165684521014 found 56 possible speech gaps totaling 102.322875 seconds and
24 empty second-recognizer hypotheses. This was an output replay, not fresh inference or human
accuracy measurement. Overlap/subtraction/clamping/idempotence/pagination/membership and frozen
snapshot behavior are tested. Component tests verify paging and source playback arguments.
The browser fixture uses an explicitly synthetic flag to test actual audio playback and the
review-to-PDF/Mailpit flow; it is never presented as model evidence.

Open: independent transcription of gaps, bounded retries with retained competing hypotheses,
human assessment of false flags and short within-sentence language switches, and target hardware.


Actual local verification: 155 backend checks passed with one Linux-only skip; 11 frontend
checks and the strict build passed. The isolated synthetic-inference browser workflow passed
through actual UI playback, persisted snapshots, PDF and Mailpit. English/Romanian/Russian
UI persistence and 200-percent DOM/layout checks also passed, with existing headless zoom
screenshot limitations retained. The new warning was visually inspected in both the workspace
and a generated one-page PDF. Repeated identical source warnings discovered during inspection
are now deduplicated per candidate; distinct uncertainties remain intact. Native-language and
long/multilingual PDF qualification are still separate open requirements.
