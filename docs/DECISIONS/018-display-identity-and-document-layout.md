# 018 — Display identity and readable review documents

## Decision

Use Notavra as the product display name, retaining the Gigahack repository and all existing
operational identifiers. `config/brand.json` is the name source. The API reads it through
`services/api/brand.py`; the web app imports it, and Vite inserts the same name in browser
metadata. New snapshots freeze the product name in their body and use template version 6.
Existing stored snapshot HTML and approvals are not rewritten.

Ten candidate names, limited conflict screening and the selection rationale are in
`docs/BRAND.md`. This is preliminary screening, not trademark clearance. The built-in image
tool generated three original concept directions. Concept 01 was manually simplified into
flat, scalable source brackets. The logo is a display asset, not an inference dependency.
The exact prompt, concept image, SVG/PNG assets, checksums and existing Noto Sans OFL notice
are retained in the repository. The embedded wordmark font remains text, not vector outlines.
No new package, runtime model, external font request or framework migration is introduced.

The live recording screen exposed another problem: 20 expanded audio-warning rows pushed
the review tabs far below the fold. The count remains visible in a native keyboard-operable
summary; the passages, original hypotheses and correction controls expand on demand. Nothing
is silently removed, automatically corrected or accepted. Existing query paging remains.

## Document defect and fix

A synthetic 60-row multilingual document with an unbroken reference produced a DOM width
of 2,690–2,746 pixels in a 794-pixel viewport. This was a real overflow failure. Fixed column
widths and wrapping now contain it; table headers repeat, rows avoid ordinary page breaks,
and A4 pages have page numbers. Unknown metadata stays explicit. Empty participant, item,
unresolved and amendment sections now have localized explanatory text instead of empty lists.

`python -m scripts.qualify_document_layout` produces nine synthetic cases (EN/RO/RU ×
empty/one/60 items) with no external asset requests. Run `document-layout-1790421194688101700`
passed all row-count and horizontal-overflow checks. Romanian short and Russian continuation
pages were rendered with Poppler and inspected after the final width adjustment. Earlier
English empty and Russian final-page renders verified explicit empty sections, footer and
pagination. This is not physical printing, universal font qualification or a full document
accessibility audit. The six-column format still needs broader long-row/evidence/approval
presentation work before the complete export requirement is qualified.

## Validation boundaries

The existing 170 backend tests and 12 frontend tests passed during this change; after the
snapshot/layout edits the 51 API/minutes tests passed again. TypeScript and Ruff checks pass.
The strict production build and final 170-test backend suite pass. The isolated browser run
`fixture-ab229bb1f16049c3b151b3147be46b23` passes correction/reanalysis/re-review, PDF, approval
and Mailpit receipt (20.29s), plus RO/RU persistence and 200% DOM checks. Its inference is
explicitly synthetic. Stored Mailpit subject starts with Notavra, and snapshot product name
and template version 6 were verified. Normal-scale review image inspected; headless zoom
screenshots remain unqualified.
Brand small-size proof was inspected in color and one color at 16, 24, 32 and 64 pixels.
Transparent PNG exports have RGBA color type. Native pronunciation and physical print review
remain unperformed. The private recording is never an approval/email fixture.
