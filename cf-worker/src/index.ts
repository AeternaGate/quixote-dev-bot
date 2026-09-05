// Точка входа Cloudflare Worker.
// Telegram получает "ok" мгновенно, обработка апдейта (включая запрос к
// OpenRouter на десятки секунд) продолжается под ctx.waitUntil().

import { Bot } from "grammy";
import type { Update } from "grammy/types";

import { createBot } from "./handlers";
import type { Env } from "./types";

// Воркер-изолят переиспользуется между запросами — бот инициализируется один раз.
const botCache = new Map<string, { bot: Bot; init: Promise<void> }>();

function getBot(env: Env): { bot: Bot; init: Promise<void> } {
    let entry = botCache.get(env.BOT_TOKEN);
    if (!entry) {
        const bot = createBot(env);
        entry = { bot, init: bot.init() };
        botCache.set(env.BOT_TOKEN, entry);
    }
    return entry;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);
        if (request.method === "GET") {
            return new Response("quixote-dev-bot worker", { status: 200 });
        }
        if (request.method !== "POST") {
            return new Response("not found", { status: 404 });
        }
        if (!env.WEBHOOK_SECRET || url.pathname !== `/webhook/${env.WEBHOOK_SECRET}`) {
            return new Response("not found", { status: 404 });
        }
        const sentSecret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
        if (sentSecret !== env.WEBHOOK_SECRET) {
            return new Response("forbidden", { status: 403 });
        }

        let update: Update;
        try {
            update = (await request.json()) as Update;
        } catch {
            return new Response("bad request", { status: 400 });
        }

        const { bot, init } = getBot(env);
        const processing = init
            .then(() => bot.handleUpdate(update))
            .catch((e) => console.error("Update processing failed:", e));
        ctx.waitUntil(processing);
        return new Response("ok", { status: 200 });
    },
};
