CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    language TEXT DEFAULT 'ru',
    is_blacklisted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    category TEXT,
    read INTEGER DEFAULT 0,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS conversations (
    user_id INTEGER PRIMARY KEY,
    step TEXT DEFAULT 'idle',
    questions_asked INTEGER DEFAULT 0,
    started_at REAL,
    context TEXT
);

CREATE TABLE IF NOT EXISTS blacklist_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reason TEXT,
    created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_messages_user_read ON messages (user_id, read);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at);
