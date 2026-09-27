# 026 — Focused action review, bounded context and local meeting folders

The action workspace now presents a queue beside one selected item. Pending,
reviewed and all-item views, owner/text search, source fields, surrounding turns,
and topic history keep normal reading quiet. Accept/exclude advances only after
successful persistence. Reviewer corrections remain selected even when their
review state changes. Original evidence, revision history, membership checks,
transcript invalidation and separate approval/delivery remain authoritative.
The global Actions register lists reviewed projections with owner filtering,
deadline order and direct links to meeting review.

The local model already extracted a chronological event ledger. Reconciliation
now retrieves up to six preceding conversation turns, configurable through
`llm.conversation_context_turns` in `config/inference.toml` (0–32). The existing
reconciliation token budget trims optional context and never discards required
evidence. It does not add later turns to reinterpret earlier decisions. The UI
can separately show subsequent turns for human review. No model migration or new
dependency was introduced. Unknown fields and uncertain interpretations still
require review; this change does not promise perfect understanding.

Meeting-folder publishing is explicitly enabled through a membership-checked,
writer-only endpoint. The UI enables it after saving an upload or recording;
existing meetings expose Save meeting folder under Meeting options. Windows
uses `C:/notavra/transcriptions`, configurable through `MOM_TRANSCRIPT_EXPORT_DIR`;
other systems default inside the runtime data directory. Names are sanitized
and suffixed with a meeting ID to prevent collisions. A database migration tracks
status. A background task publishes only enabled meetings, streams immutable audio
copies with SHA-256 verification, and atomically writes UTF-8 text/JSON. A clearly
labeled template exists only until saved transcript text is available. Imported
provenance and unapproved status remain visible in metadata. App edits refresh
these generated files; editing an exported copy does not edit the app. Exports
survive meeting deletion and need their own retention management. These are local
filesystem copies, governed by host folder permissions rather than browser roles.

Validation: automated tests cover membership/read-only guards, unsafe folder
ownership, template-to-transcript updates, Unicode and revision persistence,
context bounds/no future turns, failed review saves and correction selection.
A real local model run on three synthetic imported turns retained October 16 as
the confirmed deadline and October 20 as a later proposal (25.7 seconds observed).
No ASR or delivery ran. Browser verification at desktop/mobile covered search,
accept-and-next, edit/history persistence, source navigation and minutes. Medpark
was checked read-only apart from enabling its requested folder; the copied audio
hash and supplied transcript text were verified. No Medpark inference was run.
Private proof artifacts remain ignored in `.runtime/action-review-proof`.

Final automated results: 242 backend passed / 2 platform skips; 27 frontend
passed; production TypeScript/build, Ruff and diff checks passed.
