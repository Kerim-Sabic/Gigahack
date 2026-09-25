
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL,
 password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','secretary','viewer')), language TEXT DEFAULT 'en');
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL,csrf TEXT);
CREATE TABLE IF NOT EXISTS meetings(id TEXT PRIMARY KEY,title TEXT NOT NULL,date TEXT NOT NULL,
 timezone TEXT NOT NULL,language TEXT NOT NULL,classification TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'draft',created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS members(meeting_id TEXT REFERENCES meetings(id),user_id TEXT REFERENCES users(id),
 PRIMARY KEY(meeting_id,user_id));
CREATE TABLE IF NOT EXISTS participants(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),path TEXT NOT NULL,
 hash TEXT NOT NULL,sample_rate INTEGER NOT NULL,samples INTEGER NOT NULL,channels INTEGER NOT NULL,original TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recordings(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),rate INTEGER,
 state TEXT DEFAULT 'recording',gaps TEXT DEFAULT '[]');
CREATE TABLE IF NOT EXISTS chunks(recording_id TEXT REFERENCES recordings(id),sequence INTEGER,hash TEXT,
 samples INTEGER,path TEXT,PRIMARY KEY(recording_id,sequence));
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),asset_id TEXT REFERENCES assets(id),
 state TEXT,stage TEXT,lease REAL DEFAULT 0,cancel INTEGER DEFAULT 0,error TEXT,attempt INTEGER DEFAULT 0,
 config TEXT NOT NULL,created REAL NOT NULL, UNIQUE(meeting_id,asset_id,config));
CREATE TABLE IF NOT EXISTS segments(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),asset_id TEXT REFERENCES assets(id),
 revision INTEGER NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,text TEXT NOT NULL,raw TEXT NOT NULL,
 speaker TEXT,alternatives TEXT DEFAULT '[]',words TEXT DEFAULT '[]', UNIQUE(id,meeting_id));
CREATE TABLE IF NOT EXISTS segment_history(id TEXT PRIMARY KEY,segment_id TEXT REFERENCES segments(id),revision INTEGER,
 text TEXT,actor TEXT REFERENCES users(id),created REAL);
CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),subject TEXT,
 body TEXT NOT NULL,review TEXT DEFAULT 'unreviewed',source_order INTEGER,actor TEXT,created REAL, UNIQUE(id,meeting_id));
CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),candidate_id TEXT,
 segment_id TEXT,revision INTEGER,field TEXT,quote TEXT,start INTEGER,end INTEGER,
 FOREIGN KEY(candidate_id,meeting_id) REFERENCES candidates(id,meeting_id),
 FOREIGN KEY(segment_id,meeting_id) REFERENCES segments(id,meeting_id));
CREATE TABLE IF NOT EXISTS accepted_events(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),candidate_id TEXT,
 body TEXT NOT NULL,source_order INTEGER,actor TEXT,created REAL);
CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,meeting_id TEXT REFERENCES meetings(id),revision INTEGER,
 body TEXT NOT NULL,hash TEXT NOT NULL,html TEXT NOT NULL,created REAL);
CREATE TABLE IF NOT EXISTS approvals(snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(id),actor TEXT,created REAL);
CREATE TABLE IF NOT EXISTS recipient_groups(id TEXT PRIMARY KEY,name TEXT,version INTEGER,addresses TEXT);
CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,snapshot_id TEXT REFERENCES snapshots(id),group_id TEXT,
 group_version INTEGER,addresses TEXT,recipient_hash TEXT,state TEXT,attempt INTEGER DEFAULT 0,error TEXT,
 message_id TEXT,created REAL,UNIQUE(snapshot_id,recipient_hash));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,meeting_id TEXT,actor TEXT,kind TEXT,
 payload TEXT,created REAL);
CREATE TABLE IF NOT EXISTS idempotency(user_id TEXT,key TEXT,route TEXT,body_hash TEXT,response TEXT,
 PRIMARY KEY(user_id,key,route));
