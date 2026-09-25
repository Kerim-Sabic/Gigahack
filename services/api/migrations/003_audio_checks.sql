CREATE TABLE audio_checks(
 job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
 kind TEXT NOT NULL CHECK(kind IN ('speech_without_transcript','empty_second_recognizer')),
 start INTEGER NOT NULL CHECK(start >= 0),
 end INTEGER NOT NULL CHECK(end > start),
 PRIMARY KEY(job_id,kind,start,end)
);
INSERT INTO schema_version VALUES(3);
