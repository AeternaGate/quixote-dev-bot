export interface Env {
  DB: D1Database;
  BOT_TOKEN: string;
  OPENROUTER_API_KEY: string;
  OWNER_ID: string;
  WEBHOOK_SECRET: string;
  OPENROUTER_MODEL?: string;
}

export interface UserRow {
  userId: number;
  username: string | null;
  language: string;
  isBlacklisted: number;
}

export interface UnreadRow {
  id: number;
  userId: number;
  text: string;
  category: string | null;
}

export interface ConversationRow {
  step: string;
  questionsAsked: number;
  startedAt: number;
  context: string | null;
}

export interface BlacklistEntry {
  userId: number;
  username: string | null;
  reason: string;
}
