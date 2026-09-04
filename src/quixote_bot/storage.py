import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UserRow:
    user_id: int
    username: str | None
    language: str
    is_blacklisted: int


@dataclass
class MessageRow:
    id: int | None
    user_id: int
    text: str
    category: str | None
    read: int
    created_at: float


@dataclass
class ConversationState:
    user_id: int
    step: str
    questions_asked: int
    started_at: float


class Storage:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript("""
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
                created_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS conversations (
                user_id INTEGER PRIMARY KEY,
                step TEXT DEFAULT 'idle',
                questions_asked INTEGER DEFAULT 0,
                started_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS blacklist_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                created_at REAL
            );
        """)
        self._conn.commit()

    def ensure_user(self, user_id: int, username: str | None) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        self._conn.commit()

    def get_user(self, user_id: int) -> UserRow | None:
        row = self._conn.execute(
            "SELECT user_id, username, language, is_blacklisted FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return UserRow(
            user_id=row["user_id"], username=row["username"],
            language=row["language"], is_blacklisted=row["is_blacklisted"],
        )

    def set_language(self, user_id: int, language: str) -> None:
        self._conn.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (language, user_id),
        )
        self._conn.commit()

    def is_blacklisted(self, user_id: int) -> bool:
        row = self._conn.execute(
            "SELECT is_blacklisted FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return bool(row and row["is_blacklisted"])

    def set_blacklisted(self, user_id: int, reason: str = "") -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO users (user_id, is_blacklisted) VALUES (?, 1)",
            (user_id,),
        )
        self._conn.execute(
            "INSERT INTO blacklist_log (user_id, reason, created_at) VALUES (?, ?, ?)",
            (user_id, reason, time.time()),
        )
        self._conn.commit()

    def remove_blacklisted(self, user_id: int) -> bool:
        cur = self._conn.execute(
            "UPDATE users SET is_blacklisted = 0 WHERE user_id = ? AND is_blacklisted = 1",
            (user_id,),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def blacklist_add(self, user_id: int, reason: str = "") -> bool:
        user = self.get_user(user_id)
        if not user:
            self.ensure_user(user_id, None)
        if self.is_blacklisted(user_id):
            return False
        self.set_blacklisted(user_id, reason)
        return True

    def blacklist_remove(self, user_id: int) -> bool:
        return self.remove_blacklisted(user_id)

    def get_conversation(self, user_id: int) -> ConversationState | None:
        row = self._conn.execute(
            "SELECT user_id, step, questions_asked, started_at FROM conversations WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return ConversationState(
            user_id=row["user_id"], step=row["step"],
            questions_asked=row["questions_asked"], started_at=row["started_at"],
        )

    def upsert_conversation(self, user_id: int, step: str, questions_asked: int) -> None:
        now = time.time()
        existing = self.get_conversation(user_id)
        if existing:
            self._conn.execute(
                "UPDATE conversations SET step = ?, questions_asked = ? WHERE user_id = ?",
                (step, questions_asked, user_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO conversations (user_id, step, questions_asked, started_at) VALUES (?, ?, ?, ?)",
                (user_id, step, questions_asked, now),
            )
        self._conn.commit()

    def clear_conversation(self, user_id: int) -> None:
        self._conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def save_message(self, user_id: int, text: str, category: str | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO messages (user_id, text, category, created_at) VALUES (?, ?, ?, ?)",
            (user_id, text, category, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def mark_read(self, user_id: int) -> int:
        cur = self._conn.execute(
            "UPDATE messages SET read = 1 WHERE user_id = ? AND read = 0",
            (user_id,),
        )
        self._conn.commit()
        return cur.rowcount

    def get_unread(self) -> list[MessageRow]:
        rows = self._conn.execute(
            "SELECT id, user_id, text, category, read, created_at FROM messages WHERE read = 0 ORDER BY created_at",
        ).fetchall()
        return [
            MessageRow(
                id=r["id"], user_id=r["user_id"], text=r["text"],
                category=r["category"], read=r["read"], created_at=r["created_at"],
            )
            for r in rows
        ]

    def get_category_counts(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT category, COUNT(*) as cnt FROM messages WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC",
        ).fetchall()
        return {r["category"]: r["cnt"] for r in rows}

    def check_rate_limit(self, user_id: int, limit: int, window: int) -> bool:
        cutoff = time.time() - window
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE user_id = ? AND created_at > ?",
            (user_id, cutoff),
        ).fetchone()
        return row["cnt"] < limit  # type: ignore[union-attr]

    def close(self) -> None:
        self._conn.close()
