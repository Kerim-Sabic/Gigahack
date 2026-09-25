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
