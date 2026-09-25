# Versioned plain-text template configuration

Date: 2026-09-25. No new dependency or model.

Use the existing settings table to configure each of the three meeting classifications.
Do not execute editable HTML or allow required evidence/history sections to be disabled.
Typed API contracts constrain lengths, classification, languages and recipient-group existence.
Admin writes use optimistic version checks. Configuration is copied into each immutable
snapshot, so changing a global template cannot rewrite a reviewed/approved artifact.

Recipient suggestions reference existing groups only and confer no authorization. Existing
explicit approve/send transactions continue to validate group version and freeze recipients.
No external recipient source or automatic delivery was added. Custom wording is plain text
and is never automatically translated.

The React form keeps its draft/version across server failures and concurrent query refreshes;
replacing unsaved edits is an explicit user action. Required labels and errors remain local.
See TEMPLATES.md for checks and remaining complete-flow verification.
