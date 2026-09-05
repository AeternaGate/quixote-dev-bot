import { describe, expect, it } from "vitest";

import { matchFastTrack } from "../src/handlers";
import {
    buildUnreadChunks,
    renderFastTrackNotification,
    renderWelcome,
    SHORT_DESCRIPTIONS,
} from "../src/messages";
import {
    buildUserContext,
    fallbackAnalysis,
    getNextQuestion,
    parseAnalysis,
    parseContext,
    serializeContext,
    shouldAskQuestion,
} from "../src/qualification";

function validJson(changes: Record<string, unknown> = {}): string {
    return JSON.stringify({
        category: "готовое ТЗ",
        ready: true,
        question: null,
        summary: "Сайт",
        urgency: "обычная",
        budget: "$500",
        timeline: "2 недели",
        risks: [],
        recommended_reply: "Изучу задачу.",
        client_reply: null,
        ...changes,
    });
}

describe("matchFastTrack", () => {
    it("matches word with punctuation and returns body", () => {
        expect(matchFastTrack("Заказ! Одностраничный сайт-визитка")).toBe("Одностраничный сайт-визитка");
        expect(matchFastTrack("заказ: лендинг для кофейни")).toBe("лендинг для кофейни");
        expect(matchFastTrack("ORDER website for cafe")).toBe("website for cafe");
    });

    it("returns empty body when the word is alone", () => {
        expect(matchFastTrack("Заказ")).toBe("");
        expect(matchFastTrack("ЗАКАЗ.")).toBe("");
    });

    it("does not match word inside a longer word or mid-text", () => {
        expect(matchFastTrack("заказать лендинг")).toBeNull();
        expect(matchFastTrack("Хочу разместить заказ на лендинг")).toBeNull();
    });
});

describe("parseAnalysis", () => {
    it("parses a valid response", () => {
        const a = parseAnalysis(validJson());
        expect(a.category).toBe("готовое ТЗ");
        expect(a.ready).toBe(true);
        expect(a.clientReply).toBeNull();
    });

    it("tolerates markdown fences and chatter", () => {
        const fenced = "```json\n" + validJson() + "\n```";
        expect(parseAnalysis(fenced).category).toBe("готовое ТЗ");
        const chatty = "Вот анализ:\n" + validJson() + "\nГотово.";
        expect(parseAnalysis(chatty).summary).toBe("Сайт");
    });

    it("coerces null text fields and drops bad risks", () => {
        const a = parseAnalysis(
            JSON.stringify({
                category: "потенциальный заказ",
                ready: false,
                question: null,
                summary: null,
                urgency: null,
                budget: null,
                timeline: null,
                risks: null,
                recommended_reply: null,
                client_reply: null,
            }),
        );
        expect(a.budget).toBe("не определен");
        expect(a.risks).toEqual([]);
        expect(a.question).toBeNull();
    });

    it("rejects unknown category and non-boolean ready", () => {
        expect(() => parseAnalysis(validJson({ category: "other" }))).toThrow();
        expect(() => parseAnalysis(validJson({ ready: "yes" }))).toThrow();
    });
});

describe("qualification helpers", () => {
    it("fallback is a valid ready analysis", () => {
        const f = fallbackAnalysis();
        expect(f.category).toBe("непонятное");
        expect(f.ready).toBe(true);
    });

    it("questions follow the order and stop at 5", () => {
        expect(getNextQuestion(0, "ru")).toContain("Опишите задачу");
        expect(getNextQuestion(4, "en")).toContain("mockups");
        expect(getNextQuestion(5, "ru")).toBeNull();
    });

    it("asks questions only for incomplete briefs", () => {
        expect(shouldAskQuestion({ ready: false } as never, 0)).toBe(true);
        expect(shouldAskQuestion({ ready: true } as never, 0)).toBe(false);
        expect(shouldAskQuestion({ ready: false } as never, 5)).toBe(false);
    });

    it("context roundtrips and survives garbage", () => {
        const raw = serializeContext(["бриф", "ответ 1"]);
        expect(parseContext(raw)).toEqual(["бриф", "ответ 1"]);
        expect(parseContext("garbage")).toEqual([]);
        expect(parseContext(null)).toEqual([]);
    });

    it("numbers user messages in context", () => {
        const ctx = buildUserContext(["Hello", "World"]);
        expect(ctx).toContain("Сообщение клиента 1");
        expect(ctx).toContain("Сообщение клиента 2");
        expect(ctx).toContain("World");
    });
});

describe("messages", () => {
    it("welcome mentions fast track, portfolio and MSK in both languages", () => {
        const ru = renderWelcome("ru");
        expect(ru).toContain("ЗАКАЗ");
        expect(ru).toContain("/apply");
        expect(ru).toContain("t.me/quixoted");
        expect(ru).toContain("мск");
        const en = renderWelcome("en");
        expect(en).toContain("ORDER");
        expect(en).toContain("MSK");
    });

    it("short descriptions fit the 120-char limit", () => {
        for (const text of Object.values(SHORT_DESCRIPTIONS)) {
            expect(text.length).toBeLessThanOrEqual(120);
        }
    });

    it("fast-track notification truncates long text", () => {
        const text = renderFastTrackNotification(42, null, "x".repeat(4000));
        expect(text.length).toBeLessThan(3200);
        expect(text.endsWith("…")).toBe(true);
    });
});

describe("buildUnreadChunks", () => {
    const item = (userId: number, len: number) => ({ userId, rendered: "x".repeat(len) });

    it("keeps everything in one chunk when it fits", () => {
        const chunks = buildUnreadChunks("Header:", [item(1, 100), item(2, 100)]);
        expect(chunks).toHaveLength(1);
        expect(chunks[0]!.userIds).toEqual([1, 2]);
    });

    it("splits when over the Telegram limit", () => {
        // В проде renderUnreadItem обрезает превью до 200 символов, поэтому
        // элементы заведомо меньше лимита — как и здесь.
        const chunks = buildUnreadChunks("Header:", [item(1, 1900), item(2, 1900), item(3, 1900)]);
        expect(chunks).toHaveLength(2);
        expect(chunks[0]!.userIds).toEqual([1, 2]);
        expect(chunks[1]!.userIds).toEqual([3]);
        for (const c of chunks) expect(c.text.length).toBeLessThanOrEqual(3900);
    });
});
