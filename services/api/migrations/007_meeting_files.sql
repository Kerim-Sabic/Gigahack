CREATE TABLE meeting_file_exports (
    meeting_id TEXT PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
    folder TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL DEFAULT 'pending',
    fingerprint TEXT,
    error TEXT,
    updated REAL
);
INSERT INTO schema_version VALUES(7);
