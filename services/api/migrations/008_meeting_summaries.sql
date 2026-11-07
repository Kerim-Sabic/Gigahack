CREATE TABLE meeting_summaries (
 id TEXT PRIMARY KEY, meeting_id TEXT NOT NULL REFERENCES meetings(id),
 job_id TEXT NOT NULL REFERENCES jobs(id), source_hash TEXT NOT NULL,
 body TEXT NOT NULL, created REAL NOT NULL
);
CREATE INDEX meeting_summaries_latest ON meeting_summaries(meeting_id,created);
INSERT INTO schema_version VALUES(8);
