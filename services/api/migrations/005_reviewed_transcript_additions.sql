CREATE TABLE transcript_additions(
 job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
 start INTEGER NOT NULL,
 end INTEGER NOT NULL,
 segment_id TEXT NOT NULL UNIQUE REFERENCES segments(id) ON DELETE CASCADE,
 request_hash TEXT NOT NULL,
 actor TEXT NOT NULL,
 created REAL NOT NULL,
 PRIMARY KEY(job_id,start,end)
);
CREATE TABLE transcript_analysis_state(
 asset_id TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
 meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE
);
INSERT INTO schema_version VALUES(5);
