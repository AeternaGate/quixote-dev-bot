// Порт src/quixote_bot/handlers.py на grammY: вся логика бота.

import { Bot, Context, InlineKeyboard } from "grammy";

import * as db from "./db";
import {
    FAST_TRACK_WORDS,
    LANG_BUTTONS,
    LANG_OPTIONS,
    buildUnreadChunks,
    renderAiUnavailable,
    renderBlacklistList,
    renderBlacklistResult,
    renderBroadcastConfirm,
    renderCategories,
    renderConfirmation,
    renderError,
    renderFastTrackNotification,
    renderFastTrackUsage,
    renderMaxQuestions,
    renderMediaInstruction,
    renderOwnerNotification,
    renderOwnerOnly,
    renderPortfolio,
    renderProcessing,
    renderRateLimit,
    renderUnauthorized,
    renderUnreadHeader,
    renderUnreadItem,
    renderWelcome,
} from "./messages";
import { OpenRouterError, chat } from "./openrouter";
import {
    CONVERSATION_TTL_SECONDS,
    SYSTEM_PROMPT,
    analyzeWithRetry,
    buildUserContext,
    fallbackAnalysis,
    getNextQuestion,
    parseContext,
    serializeContext,
    shouldAskQuestion,
} from "./qualification";
import type { Env } from "./types";

const RATE_LIMIT = 10;
const RATE_WINDOW = 300;

// Порядок команд в grammY важен: команды зарегистрированы до message:text,
// как в aiogram-версии.

function isOwner(ctx: Context, ownerId: number): boolean {
    return ctx.from?.id === ownerId;
}

// Возвращает тело быстрой заявки, "" если текста нет, null если не fast-track.
export function matchFastTrack(text: string): string | null {
    const idx = text.indexOf(" ");
    const first = (idx === -1 ? text : text.slice(0, idx))
        .replace(/^[.,:!?;"'()]+|[.,:!?;"'()]+$/g, "")
        .toLowerCase();
    if (!FAST_TRACK_WORDS.has(first)) return null;
    return idx === -1 ? "" : text.slice(idx + 1).trim();
}

// Аргументы команды: всё после первого токена ("/apply текст" → "текст").
function commandArgs(ctx: Context): string {
    const raw = ctx.message?.text ?? "";
    const parts = raw.trim().split(/\s+/);
    return parts.slice(1).join(" ").trim();
}

export function createBot(env: Env): Bot {
    const bot = new Bot(env.BOT_TOKEN);
    const dbi = env.DB;
    const ownerId = Number(env.OWNER_ID);

    async function getLang(userId: number): Promise<string> {
        const user = await db.getUser(dbi, userId);
        return user?.language ?? "ru";
    }

    async function deliverFastTrack(ctx: Context, lang: string, body: string): Promise<void> {
        const uid = ctx.from!.id;
        const user = await db.getUser(dbi, uid);
        await db.clearConversation(dbi, uid);
        await db.saveMessage(dbi, uid, body, "готовое ТЗ");
        let delivered = false;
        try {
            await ctx.api.sendMessage(
                ownerId,
                renderFastTrackNotification(uid, user?.username ?? null, body),
            );
            delivered = true;
        } catch (e) {
            console.error(`Failed to deliver fast-track application for user ${uid}:`, e);
        }
        // При ошибке доставки заявка остаётся непрочитанной и подхватится /new.
        if (delivered) await db.markRead(dbi, uid);
        await ctx.reply(renderConfirmation(lang));
    }

    bot.catch((err) => {
        console.error("Unhandled error while processing update:", err.error);
        const ctx = err.ctx;
        if (ctx) {
            getLang(ctx.from?.id ?? 0)
                .then((lang) => ctx.reply(renderError(lang)))
                .catch(() => console.warn("Failed to deliver error notice to the user"));
        }
    });

    bot.command("start", async (ctx) => {
        const uid = ctx.from!.id;
        await db.ensureUser(dbi, uid, ctx.from!.username ?? null);
        const lang = await getLang(uid);

        const keyboard = new InlineKeyboard();
        for (const [code, label] of Object.entries(LANG_BUTTONS)) {
            keyboard.text(label, `lang:${code}`).row();
        }
        await ctx.reply(LANG_OPTIONS[lang] ?? LANG_OPTIONS["ru"]!, { reply_markup: keyboard });
    });

    bot.callbackQuery(/^lang:(ru|en)$/, async (ctx) => {
        const lang = ctx.callbackQuery.data!.split(":")[1]!;
        const uid = ctx.from.id;
        await db.ensureUser(dbi, uid, ctx.from.username ?? null);
        await db.setLanguage(dbi, uid, lang);
        await ctx.editMessageText(renderWelcome(lang));
        await ctx.answerCallbackQuery();
    });

    // Некорректный callback-данные молча игнорируем (валидация языка выше).
    bot.callbackQuery(/^lang:/, (ctx) => ctx.answerCallbackQuery());

    bot.command("portfolio", async (ctx) => {
        if (!ctx.from) return;
        const lang = await getLang(ctx.from.id);
        await ctx.reply(renderPortfolio(lang));
    });

    bot.command("apply", async (ctx) => {
        if (!ctx.from) return;
        const uid = ctx.from.id;
        const text = commandArgs(ctx);

        await db.ensureUser(dbi, uid, ctx.from.username ?? null);
        const lang = await getLang(uid);

        if (isOwner(ctx, ownerId)) return;
        if (await db.isBlacklisted(dbi, uid)) {
            await ctx.reply(renderUnauthorized());
            return;
        }
        if (!text) {
            await ctx.reply(renderFastTrackUsage(lang));
            return;
        }
        if (!(await db.checkRateLimit(dbi, uid, RATE_LIMIT, RATE_WINDOW))) {
            await ctx.reply(renderRateLimit(lang));
            return;
        }
        await deliverFastTrack(ctx, lang, text);
    });

    bot.command("new", async (ctx) => {
        if (!isOwner(ctx, ownerId)) {
            await ctx.reply(renderOwnerOnly());
            return;
        }
        const unread = await db.getUnread(dbi);
        if (unread.length === 0) {
            await ctx.reply("Нет непрочитанных сообщений.");
            return;
        }
        const items = [];
        for (const msg of unread) {
            const user = await db.getUser(dbi, msg.userId);
            items.push({
                userId: msg.userId,
                rendered: renderUnreadItem(msg.id, msg.userId, user?.username ?? null, msg.text, msg.category),
            });
        }
        const chunks = buildUnreadChunks(renderUnreadHeader(unread.length), items);
        // Помечаем прочитанным только после фактической отправки чанка:
        // неудачная отправка оставляет сообщения на следующий /new.
        for (const chunk of chunks) {
            await ctx.reply(chunk.text);
            for (const uid of [...new Set(chunk.userIds)]) {
                await db.markRead(dbi, uid);
            }
        }
    });

    bot.command("categories", async (ctx) => {
        if (!isOwner(ctx, ownerId)) {
            await ctx.reply(renderOwnerOnly());
            return;
        }
        await ctx.reply(renderCategories(await db.getCategoryCounts(dbi)));
    });

    bot.command("broadcast", async (ctx) => {
        if (!isOwner(ctx, ownerId)) {
            await ctx.reply(renderOwnerOnly());
            return;
        }
        const text = commandArgs(ctx);
        if (!text) {
            await ctx.reply("Использование: /broadcast <сообщение>");
            return;
        }
        let count = 0;
        let failed = 0;
        for (const uid of await db.getBroadcastTargets(dbi)) {
            try {
                await ctx.api.sendMessage(uid, text);
                count++;
            } catch (e) {
                failed++;
                console.warn(`Broadcast to ${uid} failed:`, e);
            }
        }
        if (failed > 0) console.warn(`Broadcast finished: ${count} delivered, ${failed} failed`);
        await ctx.reply(renderBroadcastConfirm(count));
    });

    bot.command("blacklist", async (ctx) => {
        if (!isOwner(ctx, ownerId)) {
            await ctx.reply(renderOwnerOnly());
            return;
        }
        const parts = (ctx.message?.text ?? "").trim().split(/\s+/);
        if (parts.length < 2) {
            await ctx.reply(
                "Использование:\n/blacklist add <user_id> [причина]\n/blacklist remove <user_id>\n/blacklist list",
            );
            return;
        }
        const action = parts[1]!.toLowerCase();

        if (action === "list") {
            await ctx.reply(renderBlacklistList(await db.getBlacklist(dbi)));
            return;
        }
        if (parts.length < 3) {
            await ctx.reply("Укажите user_id.");
            return;
        }
        const targetId = Number(parts[2]);
        if (!Number.isInteger(targetId)) {
            await ctx.reply("user_id должен быть числом.");
            return;
        }
        const reason = parts.slice(3).join(" ");

        if (action === "add") {
            const success = await db.blacklistAdd(dbi, targetId, reason);
            await ctx.reply(renderBlacklistResult("add", String(targetId), success));
        } else if (action === "remove") {
            const success = await db.blacklistRemove(dbi, targetId);
            await ctx.reply(renderBlacklistResult("remove", String(targetId), success));
        } else {
            await ctx.reply("Неизвестная команда. Используйте add/remove/list.");
        }
    });

    bot.on(
        ["message:photo", "message:video", "message:document", "message:voice", "message:video_note", "message:sticker", "message:animation"],
        async (ctx) => {
            if (!ctx.from) return;
            const lang = await getLang(ctx.from.id);
            if (isOwner(ctx, ownerId)) return;
            if (await db.isBlacklisted(dbi, ctx.from.id)) return;
            await ctx.reply(renderMediaInstruction(lang));
        },
    );

    bot.on("message:text", async (ctx) => {
        if (!ctx.from) return;
        const uid = ctx.from.id;
        const text = ctx.message.text.trim();
        if (!text) return;

        await db.ensureUser(dbi, uid, ctx.from.username ?? null);
        const lang = await getLang(uid);

        if (isOwner(ctx, ownerId)) return;
        if (await db.isBlacklisted(dbi, uid)) {
            await ctx.reply(renderUnauthorized());
            return;
        }
        if (!(await db.checkRateLimit(dbi, uid, RATE_LIMIT, RATE_WINDOW))) {
            await ctx.reply(renderRateLimit(lang));
            return;
        }

        // Быстрая заявка: слово ЗАКАЗ/ORDER в начале — напрямую владельцу,
        // без ИИ и без вопросов.
        const fastBody = matchFastTrack(text);
        if (fastBody !== null) {
            if (!fastBody) {
                await ctx.reply(renderFastTrackUsage(lang));
                return;
            }
            await deliverFastTrack(ctx, lang, fastBody);
            return;
        }

        // Накапливаем бриф: ответы на уточняющие вопросы классифицируются
        // вместе с исходным сообщением.
        let conv = await db.getConversation(dbi, uid);
        if (conv && Date.now() / 1000 - conv.startedAt > CONVERSATION_TTL_SECONDS) {
            await db.clearConversation(dbi, uid);
            conv = null;
        }
        const contextMessages = parseContext(conv?.context ?? null);
        contextMessages.push(text);

        await ctx.reply(renderProcessing(lang));

        let analysis;
        try {
            analysis = await analyzeWithRetry(() =>
                chat(env, SYSTEM_PROMPT, buildUserContext(contextMessages)),
            );
        } catch (e) {
            if (!(e instanceof OpenRouterError)) throw e;
            console.warn(`AI analysis failed for user ${uid}: ${e.message}`);
            analysis = fallbackAnalysis();
            await ctx.reply(renderAiUnavailable(lang));
        }

        await db.saveMessage(dbi, uid, text, analysis.category);

        if (analysis.category === "спам") {
            console.info(`User ${uid} auto-blacklisted as spam`);
            await db.blacklistAdd(dbi, uid, "автоматический спам");
            return;
        }

        const questionsAsked = conv?.questionsAsked ?? 0;

        if (shouldAskQuestion(analysis, questionsAsked)) {
            const question = getNextQuestion(questionsAsked, lang);
            if (question) {
                await db.upsertConversation(
                    dbi,
                    uid,
                    "asking",
                    questionsAsked + 1,
                    serializeContext(contextMessages),
                );
                await ctx.reply(question);
                return;
            }
        }

        // Заявка готова — отправляем владельцу.
        await db.clearConversation(dbi, uid);
        const user = await db.getUser(dbi, uid);
        const brief = contextMessages.join("\n\n");
        const notification = renderOwnerNotification(uid, user?.username ?? null, brief, analysis, questionsAsked);

        let delivered = false;
        try {
            await ctx.api.sendMessage(ownerId, notification);
            delivered = true;
        } catch (e) {
            console.error(`Failed to deliver lead notification for user ${uid}:`, e);
        }
        // При ошибке доставки остаётся непрочитанным — подхватит /new.
        if (delivered) await db.markRead(dbi, uid);

        if (analysis.clientReply) {
            await ctx.reply(analysis.clientReply);
        } else {
            const fallback = questionsAsked ? renderMaxQuestions(lang) : renderConfirmation(lang);
            await ctx.reply(fallback);
        }
    });

    return bot;
}
