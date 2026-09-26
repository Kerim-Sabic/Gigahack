# Notavra identity

Selected product display name: **Notavra**. Repository and internal identifiers remain
Gigahack / Secure MOM. The latter names describe the implementation/challenge history.
This document records design judgments, not user research or trademark clearance.

## Name exploration, 2026-09-26

| Candidate | Assessment |
|---|---|
| Notavra | Selected: evokes notes and spoken words; three readable syllables, no accents, useful N silhouette. |
| Notivra | More difficult consonant transition; less natural to pronounce. |
| Rostiva | Attractive connection to speaking/order, but unrelated existing businesses make it less distinctive. |
| Decivra | Strong decision association, rejected for an existing decision-software product. |
| Veridra | Implies truth too strongly for machine-generated, unreviewed hypotheses. |
| Ordavia | Suggests organization, but weak connection to speech or records. |
| Acordis | Agreement association risks implying every discussion reaches consensus. |
| Convera | Conversational association is useful but generic and less memorable in this set. |
| Minuta | Direct minutes association, too descriptive and easy to confuse with the document type. |
| Actoria | Suggests actions, rejected for existing AI software and unrelated acting associations. |

Working pronunciation: no-TA-vra (Romanian/English), но-ТА-вра (Russian).
These are intended readings, not native-speaker validation. Do not translate the name.

Preliminary web searches used the exact candidate strings with software, meeting and app
terms, plus an exact-name Notavra query. Returned Notavra results were unrelated OCR/text
matches; no obvious same-name meeting application appeared in this limited check. This is
not a finding of legal availability, domain ownership or exhaustive conflict clearance.
Concrete exclusions: [Decivra](https://decivra.app/) describes industrial bid decision
software; [Actoria](https://actoria.ai/) describes AI video software. The
[Istanbul facility directory](https://sporenvanteri.ibb.istanbul/tesis/rostiva-timur-imrag-anadolu-meslek-lisesi)
also contains Rostiva as a name. Search coverage is limited and may change.

## Visual direction

Calm, precise records rather than surveillance or certification. Explore connected source
brackets, aligned record lines and a two-strand N. Ink #183438, restrained teal #287F78,
white/paper surfaces. Avoid shields, microphones, crosses, approval checkmarks in the logo,
gradients and implied clinical validation. Keep status colors separate from brand decoration.
Use the already locally bundled Noto Sans for multilingual interface/document text.

The built-in image-generation tool produced the original three-concept exploration in
`brand/notavra-concepts.png`; the exact prompt is `brand/generation-prompt.txt`. Concept 01
was selected: two source brackets leave an N-shaped opening. Concept 02 was too intricate
at small sizes; concept 03 was a more generic ribbon N. The generated image had subtle
texture despite the flat-color request, so the production symbol is a hand-simplified
vector with flat fills, not an embedded generated bitmap.
Generated concepts are design references, not runtime dependencies. A final deterministic
SVG must remain legible at 16/24/32 pixels and in one-color print. The symbol and one-color variant are true SVG paths. The SVG lockup embeds the existing
Noto Sans font rather than requiring a network font; its lettering remains text, not outlines.
The local font license is retained in `brand/Noto-Sans-OFL.txt`. Transparent PNG symbol,
lockup and favicon are rendered by `python -m scripts.render_brand` with the already pinned
Playwright/Chromium. No new dependency or model is introduced. `brand/size-proof.png` was
visually inspected at 16/24/32/64 pixels: both bracket shapes and the central opening remain
visible in color and one color. Physical print qualification is still pending.

## Integration status

Name, symbol, wordmark, transparent rasters and favicon are integrated. `config/brand.json`
feeds the UI/browser title and Python display identity; new snapshots freeze the name and
email uses that frozen name. No database IDs, CLI commands, environment variables, filesystem
layouts or existing snapshots change. Actual synthetic browser/PDF/Mailpit flow passes;
see Decision 018 for layout checks and remaining physical-print/native-review limits.
