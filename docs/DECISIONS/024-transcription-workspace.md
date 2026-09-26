# 024 — Warm transcription workspace, with Notavra identity

The user requested an extensive frontend redesign close to MAI Transcribe's warm,
quiet audio/transcript experience, then clarified that Notavra must remain visually
distinct. Inspected the public live MAI Playground shell and example interaction.
The supplied session itself was unavailable without account context; no MAI
transcript screenshots were attached to this request. Private Medpark content was
never uploaded to the reference service. Do not claim an exact screenshot match.

Retained Notavra identity and all local backend contracts. Added a warm ivory
palette, restrained peripheral navigation, a 1040px reading area and 124px top
audio surface. Notavra-specific details include the sage recording edge, visible
speaker key and links from source evidence to the relevant transcript passage.
No Microsoft name, logo, font, code or proprietary assets are included. Reused
the existing locally bundled Noto Sans and already installed Lucide icons; no
dependency/model addition or migration.

`MeetingAudio` uses the existing authenticated bounded clip API. Its absolute
playback position maps onto ten-minute source windows, with seamless forward
continuation. The activity canvas uses actual source intervals and stable speaker
colors; it is not an amplitude waveform or fresh diarization. Imported approximate
timestamps remain disclosed once, with full provenance available per passage.
Native range controls provide pointer/keyboard seeking. The mini-player appears
only when the top player is off-screen and audio has loaded.

`TranscriptExperience` renders at most 80 utterances per page. Full transcript data
is fetched through existing bounded pages for whole-recording activity/search;
text memory therefore grows with the source, while DOM and audio loading remain
bounded. No claim of unlimited-duration or constant-memory processing. Follow
mode changes pages and scrolls only when enabled. Edits retain the existing
revision API, errors keep the editor open, and history/provenance load on demand.
Romanian and Cyrillic text are retained; search is Unicode-aware in the client.

Actions use a quieter two-column list/detail layout, category filtering and search.
Minutes retain separate preview, approval and delivery, with technical metadata
behind a disclosure. Editing transcript content continues to invalidate dependent
reviews; that warning remains visible on action/minutes views. Existing Medpark
content and its review state were not altered during this redesign's tests.

Validation: iterative desktop captures at 1440×900, plus 820×1000 and 390×844.
Actual Medpark playback, pause, timeline mouse/keyboard seek, absolute positions
beyond 600s, automatic window continuation, active passage, follow mode, mini-player,
Romanian/Cyrillic search, action/minutes navigation, and overflow checks passed.
Separate synthetic meeting exercised edit/cancel, Ctrl+Enter, speaker change,
reload persistence and revision history; that fixture was removed through the
role-protected API using a scoped temporary test administrator, then the temporary
account was removed. No clinical source was edited for test purposes.
Unit/component tests cover a 2001-segment transcript with only 80 rendered rows,
search beyond the first page, overlap/timing, deterministic colors, viewer controls,
and failed save retention. Final checks and screenshots are recorded in STATUS.

Follow-up: at the user’s request, replaced the MAI-like ivory/beige theme with
Notavra’s soft stone (#F3F2F5), pale lilac (#E6E1EC), plum (#665274) and slate
palette. Speaker identity colors now use plum, slate, eucalyptus, rose, ochre and
indigo consistently across labels, dots and timeline. Layout and behavior unchanged.
Strict build passed; actual 1440×900 Medpark view visually inspected.
