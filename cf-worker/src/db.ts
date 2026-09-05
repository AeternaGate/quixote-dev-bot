// Порт src/quixote_bot/storage.py на D1. Схема — migrations/0001_init.sql.

import type { BlacklistEntry, ConversationRow, UnreadRow, UserRow } from "./types";

const now = () => Date.now() / 1000;

export async function ensureUser(db: D1Database, userId: number, username: string | null): Promise<void> {
    await db
        .prepare("INSERT INTO users (user_id, username) VALUES (?1, ?2) ON CONFLICT (user_id) DO NOTHING")
        .bind(userId, username ?? null)
        .run();
}

export async function getUser(db: D1Database, userId: number): Promise<UserRow | null> {
    const row = await db
        .prepare("SELECT user_id, username, language, is_blacklisted FROM users WHERE user_id = ?1")
        .bind(userId)
        .first<{ user_id: number; username: string | null; language: string; is_blacklisted: number }>();
    if (!row) return null;
    return { userId: row.user_id, username: row.username, language: row.language, isBlacklisted: row.is_blacklisted };
}

export async function setLanguage(db: D1Database, userId: number, language: string): Promise<void> {
    await db.prepare("UPDATE users SET language = ?1 WHERE user_id = ?2").bind(language, userId).run();
}

export async function isBlacklisted(db: D1Database, userId: number): Promise<boolean> {
    const row = await db
        .prepare("SELECT is_blacklisted FROM users WHERE user_id = ?1")
        .bind(userId)
        .first<{ is_blacklisted: number }>();
    return Boolean(row && row.is_blacklisted);
}

export async function setBlacklisted(db: D1Database, userId: number, reason: string): Promise<void> {
    // UPSERT вместо REPLACE: username и язык пользователя сохраняются.
    await db.batch([
        db
            .prepare(
                "INSERT INTO users (user_id, is_blacklisted) VALUES (?1, 1) " +
                    "ON CONFLICT (user_id) DO UPDATE SET is_blacklisted = 1",
            )
            .bind(userId),
        db.prepare("INSERT INTO blacklist_log (user_id, reason, created_at) VALUES (?1, ?2, ?3)").bind(userId, reason, now()),
    ]);
}

export async function blacklistAdd(db: D1Database, userId: number, reason: string): Promise<boolean> {
    if (await isBlacklisted(db, userId)) return false;
    await setBlacklisted(db, userId, reason);
    return true;
}

export async function blacklistRemove(db: D1Database, userId: number): Promise<boolean> {
    const res = await db
        .prepare("UPDATE users SET is_blacklisted = 0 WHERE user_id = ?1 AND is_blacklisted = 1")
        .bind(userId)
        .run();
    return (res.meta.changes ?? 0) > 0;
}

export async function getBlacklist(db: D1Database): Promise<BlacklistEntry[]> {
    const { results } = await db
        .prepare(
            "SELECT u.user_id, u.username, " +
                "(SELECT bl.reason FROM blacklist_log bl WHERE bl.user_id = u.user_id " +
                " ORDER BY bl.created_at DESC LIMIT 1) AS reason " +
                "FROM users u WHERE u.is_blacklisted = 1 ORDER BY u.user_id",
        )
        .all<{ user_id: number; username: string | null; reason: string | null }>();
    return results.map((r) => ({ userId: r.user_id, username: r.username, reason: r.reason ?? "" }));
}

export async function getBroadcastTargets(db: D1Database): Promise<number[]> {
    const { results } = await db
        .prepare(
            "SELECT DISTINCT user_id FROM messages WHERE user_id NOT IN " +
                "(SELECT user_id FROM users WHERE is_blacklisted = 1)",
        )
        .all<{ user_id: number }>();
    return results.map((r) => r.user_id);
}

export async function getConversation(db: D1Database, userId: number): Promise<ConversationRow | null> {
    const row = await db
        .prepare("SELECT step, questions_asked, started_at, context FROM conversations WHERE user_id = ?1")
        .bind(userId)
        .first<{ step: string; questions_asked: number; started_at: number; context: string | null }>();
    if (!row) return null;
    return { step: row.step, questionsAsked: row.questions_asked, startedAt: row.started_at, context: row.context };
}

export async function upsertConversation(
    db: D1Database,
    userId: number,
    step: string,
    questionsAsked: number,
    context: string | null,
): Promise<void> {
    await db
        .prepare(
            "INSERT INTO conversations (user_id, step, questions_asked, started_at, context) " +
                "VALUES (?1, ?2, ?3, ?4, ?5) ON CONFLICT (user_id) DO UPDATE SET " +
                "step = ?2, questions_asked = ?3, started_at = ?4, context = COALESCE(?5, context)",
        )
        .bind(userId, step, questionsAsked, now(), context)
        .run();
}

export async function clearConversation(db: D1Database, userId: number): Promise<void> {
    await db.prepare("DELETE FROM conversations WHERE user_id = ?1").bind(userId).run();
}

export async function saveMessage(db: D1Database, userId: number, text: string, category: string | null): Promise<number> {
    const res = await db
        .prepare("INSERT INTO messages (user_id, text, category, created_at) VALUES (?1, ?2, ?3, ?4)")
        .bind(userId, text, category, now())
        .run();
    return Number(res.meta.last_row_id ?? 0);
}

export async function markRead(db: D1Database, userId: number): Promise<void> {
    await db.prepare("UPDATE messages SET read = 1 WHERE user_id = ?1 AND read = 0").bind(userId).run();
}

export async function getUnread(db: D1Database): Promise<UnreadRow[]> {
    const { results } = await db
        .prepare("SELECT id, user_id, text, category, read, created_at FROM messages WHERE read = 0 ORDER BY created_at")
        .all<{ id: number; user_id: number; text: string; category: string | null }>();
    return results.map((r) => ({ id: r.id, userId: r.user_id, text: r.text, category: r.category }));
}

export async function getCategoryCounts(db: D1Database): Promise<Record<string, number>> {
    const { results } = await db
        .prepare(
            "SELECT category, COUNT(*) AS cnt FROM messages " +
                "WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC",
        )
        .all<{ category: string; cnt: number }>();
    return Object.fromEntries(results.map((r) => [r.category, r.cnt]));
}

export async function checkRateLimit(db: D1Database, userId: number, limit: number, window: number): Promise<boolean> {
    const row = await db
        .prepare("SELECT COUNT(*) AS cnt FROM messages WHERE user_id = ?1 AND created_at > ?2")
        .bind(userId, now() - window)
        .first<{ cnt: number }>();
    return (row?.cnt ?? 0) < limit;
}
