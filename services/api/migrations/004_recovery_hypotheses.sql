ALTER TABLE audio_checks ADD COLUMN hypotheses TEXT NOT NULL DEFAULT '[]';
INSERT INTO schema_version VALUES(4);
