# Operator changes, history and mail recovery

Continue the existing FastAPI/SQLite/React architecture. No new dependency or model is adopted.
Use Python standard-library SMTP and TLS with verified certificates for internal mail systems.
Only failures before the send operation may be explicitly retried. Ambiguous SMTP outcomes remain
uncertain and blocked from replay; exactly-once delivery is not claimed.

Meeting metadata is revision-checked and cannot change during queued/running processing. Date,
timezone, language and classification participate in the job input identity. Changing meeting dates
cannot silently approve an obsolete relative deadline: re-extraction or an explicit due-date
correction is required. Excluded historical candidates remain excluded during metadata invalidation.

Account listing is admin-only and returns no password hashes or session fields. Granting meeting
access still requires the admin to be an existing member. Metadata, grant and exact-title deletion
controls expose existing authorization rules. Amendment history reads retained candidates, including
excluded originals and human correction reasons, independently from the current accepted projection.

Tradeoff: full native translation review and internal-server TLS rehearsal remain qualification
steps. No cloud service is introduced; Mailpit stays the local default.
