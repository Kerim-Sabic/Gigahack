# Recovery

Source audio is retained after failed/cancelled processing. Retry uses stage artifact input hashes;
changing source revisions invalidates extraction inputs. Worker leases older than 30 seconds are requeued
on startup. Never manually reset an outbox row marked uncertain: inspect Mailpit/internal SMTP first.
Message-ID and outbox deduplication reduce duplicates; they do not provide exactly-once SMTP delivery.

Stop with `python -m scripts.mom stop`. Backup to a new folder with `backup --path`.
SQLite backup API plus a stopped copy of audio/jobs/exports gives a consistent boundary.
Restore to a new empty MOM_DATA folder; original data is not overwritten. Paths are relocated in SQLite.
The automated test validates account and acknowledged-audio survival. Encrypt and restrict backups.

A browser refresh loses unacknowledged microphone memory. Acknowledged PCM chunks remain on disk.
The UI offers Seal acknowledged audio for interrupted recordings, and marks the unknown missing wall
interval explicitly. Unacknowledged browser memory is never represented as saved audio.
Physical microphone disconnection and sustained target-device capture require further fault rehearsal.

The admin-and-member-only meeting deletion endpoint requires the expected revision and exact title.
It rejects active jobs, quarantines audio, removes meeting content/exports and retains a minimal audit
tombstone. Backups are separate retention copies and are not erased by meeting deletion. Failed file
cleanup is reported as pending. Automatic retention scheduling and forensic SSD erasure are not provided.


The minutes panel offers **Retry this failed delivery** only when the attempt failed before
entering the SMTP send operation. The server rejects uncertain, sending and accepted attempts.
Retry preserves the frozen recipients, snapshot, Message-ID and attempt count; a stale approved
version still needs an explicit older-version choice. The displayed delivery recipients are the
frozen envelope, independent of the currently selected group.

Internal SMTP configuration is read from the mail worker environment:
`MOM_SMTP_HOST`, `MOM_SMTP_PORT`, `MOM_SMTP_FROM`, `MOM_SMTP_TLS` (`starttls` or `ssl`),
`MOM_SMTP_USER`, `MOM_SMTP_PASSWORD`, and optional `MOM_SMTP_CA_FILE` for an internal CA.
Non-loopback hosts default to STARTTLS/587; implicit TLS defaults to 465. Certificate and hostname
verification remain enabled. Plain transport is allowed only for loopback Mailpit, without credentials.
Keep credentials outside Git and restart the mail worker after configuration changes. An internal
SMTP deployment needs its own connectivity/certificate rehearsal; automated tests cover transport
ordering and failures, while the actual local Mailpit flow covers delivery integration.
