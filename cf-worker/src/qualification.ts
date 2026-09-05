// Порт src/quixote_bot/qualification.py — промпт, валидация ответа ИИ, fallback.

import { CATEGORIES, QUALIFICATION_QUESTIONS, QUESTION_ORDER } from "./messages";

// Диалог старше этого времени считается устаревшим.
export const CONVERSATION_TTL_SECONDS = 30 * 60;

export const SYSTEM_PROMPT = `Ты — ассистент фрилансера Quixote.Dev.
Твоя задача: классифицировать сообщение клиента, определить готовность проекта и кратко ответить клиенту.

Услуги фрилансера:
- Фуллстек-разработка (сайты, боты, приложения)
- Автоматизация с участием ИИ
- Минимальная стоимость: $10 за легкие правки
- Рабочие часы: 14:00-20:00 по мск
- Срочные проекты принимаются
- Сомнительные и незаконные заказы не принимаются

Категории: "готовое ТЗ", "потенциальный заказ", "вопрос по услуге", "уточнение по текущему заказу", "спам", "непонятное"

Отвечай ТОЛЬКО валидным JSON без markdown:
{
  "category": "одна из категорий выше",
  "ready": true/false,
  "question": null или "один короткий вопрос" если ready=false,
  "summary": "краткое резюме на русском",
  "urgency": "срочно/обычная/не горит",
  "budget": "предварительная оценка или null",
  "timeline": "предполагаемые сроки или null",
  "risks": ["список рисков"],
  "recommended_reply": "рекомендуемый ответ владельцу на русском",
  "client_reply": "короткий ответ клиенту на языке сообщения или null"
}

Примеры классификации (сообщение → ключевые поля ответа):
1. "Хочу заказать лендинг" → category "потенциальный заказ", ready false,
   question "Расскажите подробнее: что за проект, какие страницы и функции нужны?",
   budget "не определен", client_reply "Спасибо за обращение! Уточните детали задачи."
2. "Одностраничный сайт с описанием кафе, меню с ценами и отзывами" →
   category "потенциальный заказ", ready false, question "Какой бюджет и сроки?",
   client_reply "Принял! Уточните бюджет и сроки."
3. "Нужен бот для записи клиентов, с базой и напоминаниями, бюджет $300" →
   category "готовое ТЗ", ready true, question null,
   client_reply "Спасибо, заявка принята! Скоро свяжусь."
4. "Привет" / "тест" → category "непонятное", ready true, question null, client_reply null
5. "Купите дешевые подписки, пишите в лс" → category "спам", ready true, question null, client_reply null

Любое описание конкретной работы (даже короткое) — это "потенциальный заказ" или "готовое ТЗ", но не "непонятное".

Правила для client_reply:
- "готовое ТЗ" → краткое подтверждение получения + что свяжутся soon
- "потенциальный заказ" → благодарность + что изучат задачу
- "вопрос по услуге" → краткий ответ на вопрос по услугам
- "уточнение по текущему заказу" → подтверждение получения
- "спам" → null (не отвечать)
- "непонятное" → null (без ответа)
- Если ready=false — client_reply может быть null, ответ придет после уточнений
- Отвечай на том же языке, что и сообщение клиента
- Максимум 2-3 предложения, деловой тон
- Не называй цену окончательно, только предварительно`;

export interface Analysis {
    category: string;
    ready: boolean;
    question: string | null;
    summary: string;
    urgency: string;
    budget: string;
    timeline: string;
    risks: string[];
    recommendedReply: string;
    clientReply: string | null;
}

// Модели оборачивают JSON в ```json-ограждения или болтовню — вытаскиваем объект.
function loadJsonObject(raw: string): Record<string, unknown> {
    let data: unknown;
    try {
        data = JSON.parse(raw.trim());
    } catch {
        const start = raw.indexOf("{");
        const end = raw.lastIndexOf("}");
        if (start === -1 || end <= start) throw new Error("no json object found");
        data = JSON.parse(raw.slice(start, end + 1));
    }
    if (data === null || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("AI result must be an object");
    }
    return data as Record<string, unknown>;
}

export function parseAnalysis(raw: string): Analysis {
    const data = loadJsonObject(raw);
    const category = data.category;
    if (typeof category !== "string" || !(CATEGORIES as readonly string[]).includes(category)) {
        throw new Error("unknown category");
    }
    const ready = data.ready;
    if (typeof ready !== "boolean") throw new Error("ready must be boolean");
    // Вопрос от ИИ информационный: при ready=false задаём свои канонические вопросы.
    let question = typeof data.question === "string" ? data.question : null;
    if (ready) question = null;
    const defaults: Record<string, string> = {
        summary: "Без резюме",
        urgency: "обычная",
        budget: "не определен",
        timeline: "не определены",
        recommended_reply: "Изучу задачу и вернусь с ответом.",
    };
    const pick = (key: string): string => {
        const value = data[key];
        if (typeof value === "string") return value;
        return value === null || value === undefined ? defaults[key]! : String(value);
    };
    const risks =
        Array.isArray(data.risks) && data.risks.every((r) => typeof r === "string")
            ? (data.risks as string[])
            : [];
    const clientReply = typeof data.client_reply === "string" ? data.client_reply : null;
    return {
        category,
        ready,
        question,
        summary: pick("summary"),
        urgency: pick("urgency"),
        budget: pick("budget"),
        timeline: pick("timeline"),
        risks,
        recommendedReply: pick("recommended_reply"),
        clientReply,
    };
}

export function fallbackAnalysis(): Analysis {
    return {
        category: "непонятное",
        ready: true,
        question: null,
        summary: "ИИ не смог разобрать заявку.",
        urgency: "обычная",
        budget: "не определен",
        timeline: "не определены",
        risks: ["Требуется ручная проверка."],
        recommendedReply: "Спасибо, я изучу задачу и вернусь с ответом.",
        clientReply: null,
    };
}

export async function analyzeWithRetry(call: () => Promise<string>): Promise<Analysis> {
    for (let attempt = 0; attempt < 2; attempt++) {
        try {
            return parseAnalysis(await call());
        } catch {
            if (attempt === 1) return fallbackAnalysis();
        }
    }
    throw new Error("unreachable");
}

export function getNextQuestion(questionNumber: number, language = "ru"): string | null {
    if (questionNumber >= QUESTION_ORDER.length) return null;
    const key = QUESTION_ORDER[questionNumber]!;
    return QUALIFICATION_QUESTIONS[key]![language] ?? null;
}

export function shouldAskQuestion(analysis: Analysis, questionCount: number): boolean {
    return !analysis.ready && questionCount < 5;
}

export function buildUserContext(messages: string[]): string {
    return messages.map((msg, i) => `Сообщение клиента ${i + 1}:\n${msg}`).join("\n\n");
}

export function serializeContext(messages: string[]): string {
    return JSON.stringify(messages);
}

export function parseContext(raw: string | null): string[] {
    if (!raw) return [];
    try {
        const data: unknown = JSON.parse(raw);
        if (Array.isArray(data) && data.every((m) => typeof m === "string")) {
            return data as string[];
        }
    } catch {
        // повреждённый контекст трактуем как пустой
    }
    return [];
}
