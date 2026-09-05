// Полный порт текстов из src/quixote_bot/messages.py (Python-версии).

export const CATEGORIES = [
    "готовое ТЗ",
    "потенциальный заказ",
    "вопрос по услуге",
    "уточнение по текущему заказу",
    "спам",
    "непонятное",
] as const;

export const LANG_OPTIONS: Record<string, string> = {
    ru: "Выберите язык общения:\n\nChoose your language:",
    en: "Choose your language:\n\nВыберите язык общения:",
};

export const LANG_BUTTONS: Record<string, string> = { ru: "Русский", en: "English" };

// Первые слова (без учёта регистра и пунктуации), отправляющие заявку
// владельцу напрямую, минуя ИИ и вопросы.
export const FAST_TRACK_WORDS = new Set(["заказ", "order"]);

export const PORTFOLIO_URL = "https://t.me/quixoted";

export const SHORT_DESCRIPTIONS: Record<string, string> = {
    ru: "Quixote.Dev — сайты, боты, автоматизация с ИИ. Портфолио: t.me/quixoted. Заявка: слово ЗАКАЗ.",
    en: "Quixote.Dev — websites, bots, AI automation. Portfolio: t.me/quixoted. Fast application: word ORDER.",
};

export const QUALIFICATION_QUESTIONS: Record<string, Record<string, string>> = {
    budget: {
        ru: "Какой бюджет проекта? Укажите примерную сумму или диапазон.",
        en: "What is the project budget? Please specify an approximate amount or range.",
    },
    deadline: {
        ru: "Какие сроки реализации? Когда нужно сдать проект?",
        en: "What is the implementation timeline? When do you need the project delivered?",
    },
    scope: {
        ru: "Опишите задачу подробнее: какие функции, страницы или компоненты нужны?",
        en: "Describe the task in more detail: what functions, pages, or components do you need?",
    },
    technologies: {
        ru: "Есть ли предпочтения по технологиям или платформе? (например, React, Telegram Bot, сайт)",
        en: "Do you have technology or platform preferences? (e.g., React, Telegram Bot, website)",
    },
    materials: {
        ru: "Если есть макеты, документы или примеры — отправьте их мне в личку при личном обсуждении.",
        en: "If you have mockups, documents or examples — send them to me in a personal chat during our discussion.",
    },
};

export const QUESTION_ORDER = ["scope", "budget", "deadline", "technologies", "materials"];

// Telegram отклоняет сообщения длиннее 4096 символов; оставляем запас.
export const MAX_MESSAGE_LENGTH = 3900;

export function renderWelcome(language: string): string {
    if (language === "en") {
        return (
            "Welcome to Quixote.Dev!\n\n" +
            "I do full-stack development and AI-powered automation.\n" +
            "Minimum order — $10, working hours 14:00–20:00 MSK, urgent projects accepted.\n\n" +
            "To get a faster answer, include in your first message:\n" +
            "1. What needs to be done: task, features, pages\n" +
            "2. Approximate budget\n" +
            "3. Timeline\n" +
            "4. Technology or platform preferences\n" +
            "5. Materials, if any (mockups, documents, examples)\n\n" +
            "Fast track: start your message with ORDER (or send /apply <text>) — " +
            "it goes straight to me, with no questions and no AI wait.\n\n" +
            "Important:\n" +
            "- Only TEXT messages are accepted.\n" +
            "- Files, photos, voice messages and other media — later in personal chat.\n\n" +
            `Portfolio and case studies: ${PORTFOLIO_URL}\n\n` +
            "Send your project description:"
        );
    }
    return (
        "Добро пожаловать в Quixote.Dev!\n\n" +
        "Помогаю с фуллстек-разработкой и автоматизациями с участием ИИ.\n" +
        "Минимальный заказ — $10, работаю 14:00–20:00 по мск, срочные проекты — можно.\n\n" +
        "Чтобы получить ответ быстрее, сразу включите в сообщение:\n" +
        "1. Что нужно сделать: задача, функции, страницы\n" +
        "2. Примерный бюджет\n" +
        "3. Сроки\n" +
        "4. Предпочтения по технологиям или платформе\n" +
        "5. Материалы, если есть (макеты, документы, примеры)\n\n" +
        "Быстрая заявка: начните сообщение со слова ЗАКАЗ (или отправьте /apply <текст>) — " +
        "она уйдёт напрямую, без вопросов и ожидания ИИ.\n\n" +
        "Важно:\n" +
        "- Принимаются только ТЕКСТОВЫЕ сообщения.\n" +
        "- Файлы, фото, голосовые и другие медиа — позже, в личной переписке.\n\n" +
        `Портфолио и примеры работ: ${PORTFOLIO_URL}\n\n` +
        "Отправьте описание проекта:"
    );
}

export function renderMediaInstruction(language: string): string {
    if (language === "en") {
        return (
            "I accept only text messages. " +
            "Please send files, photos, voice messages and other media " +
            "directly in personal chat during our discussion."
        );
    }
    return (
        "Я принимаю только текстовые сообщения. " +
        "Файлы, фото, голосовые и другие медиа " +
        "отправляйте в личку при личном обсуждении."
    );
}

export function renderProcessing(language: string): string {
    return language === "en" ? "Processing your message..." : "Обрабатываю ваше сообщение...";
}

export function renderConfirmation(language: string): string {
    if (language === "en") {
        return (
            "Thank you! Your message has been received and forwarded for review. " +
            "You will be contacted shortly."
        );
    }
    return (
        "Спасибо! Ваше сообщение получено и переслано на рассмотрение. " +
        "С вами свяжутся в ближайшее время."
    );
}

export function renderMaxQuestions(language: string): string {
    if (language === "en") {
        return (
            "Thank you for the details. Your message has been forwarded for review. " +
            "You will be contacted shortly."
        );
    }
    return (
        "Спасибо за подробности. Ваше сообщение переслано на рассмотрение. " +
        "С вами свяжутся в ближайшее время."
    );
}

interface AnalysisLike {
    category: string;
    question: string | null;
    summary: string;
    urgency: string;
    budget: string;
    timeline: string;
    risks: string[];
    recommendedReply: string;
}

export function renderOwnerNotification(
    userId: number,
    username: string | null,
    source: string,
    analysis: AnalysisLike,
    questionsAsked: number,
): string {
    const client = username ? `@${username}` : String(userId);
    let brief = source;
    if (brief.length > 3000) brief = brief.slice(0, 3000) + "…";
    const risks = analysis.risks.length
        ? analysis.risks.map((r) => `  - ${r}`).join("\n")
        : "  нет";
    const questionsLine = questionsAsked ? `Задано вопросов: ${questionsAsked}` : "";

    const lines = [
        `Новая заявка от ${client} (ID: ${userId})`,
        `Категория: #${analysis.category}`,
        "",
        `Обращение клиента:\n${brief}`,
        "",
        `Резюме: ${analysis.summary}`,
        `Срочность: ${analysis.urgency}`,
        `Предварительный бюджет: ${analysis.budget}`,
        `Сроки: ${analysis.timeline}`,
        `Риски:\n${risks}`,
        `Рекомендуемый ответ:\n${analysis.recommendedReply}`,
    ];
    if (analysis.question) lines.push(`Вопрос от ИИ: ${analysis.question}`);
    if (questionsLine) {
        lines.push("");
        lines.push(questionsLine);
    }
    return lines.join("\n");
}

export function renderFastTrackNotification(userId: number, username: string | null, source: string): string {
    const client = username ? `@${username}` : String(userId);
    if (source.length > 3000) source = source.slice(0, 3000) + "…";
    return (
        `Быстрая заявка от ${client} (ID: ${userId})\n` +
        "Категория: #готовое ТЗ\n\n" +
        `Текст:\n${source}`
    );
}

export function renderFastTrackUsage(language: string): string {
    return language === "en"
        ? "Add your application text after ORDER (or use /apply <text>)."
        : "Добавьте описание заявки после слова ЗАКАЗ (или /apply <текст>).";
}

export function renderUnreadHeader(count: number): string {
    return `Непрочитанные сообщения (${count}):`;
}

export function renderUnreadItem(
    msgId: number,
    userId: number,
    username: string | null,
    text: string,
    category: string | null,
): string {
    const client = username ? `@${username}` : String(userId);
    const tag = category ? ` #${category}` : "";
    const preview = text.slice(0, 200) + (text.length > 200 ? "..." : "");
    return `[${msgId}] ${client}${tag}\n${preview}`;
}

export function renderCategories(stats: Record<string, number>): string {
    if (Object.keys(stats).length === 0) return "Пока нет сообщений.";
    const lines = ["Статистика по категориям:"];
    for (const [cat, cnt] of Object.entries(stats)) lines.push(`  #${cat}: ${cnt}`);
    return lines.join("\n");
}

export function renderBroadcastConfirm(count: number): string {
    return `Сообщение отправлено ${count} пользователям.`;
}

export function renderBlacklistResult(action: string, target: string, success: boolean): string {
    if (action === "add") {
        return success
            ? `Пользователь ${target} добавлен в черный список.`
            : `Пользователь ${target} уже в черном списке.`;
    }
    if (action === "remove") {
        return success
            ? `Пользователь ${target} удален из черного списка.`
            : `Пользователь ${target} не найден в черном списке.`;
    }
    return "Неизвестная команда.";
}

export function renderBlacklistList(entries: Array<{ userId: number; username: string | null; reason: string }>): string {
    if (entries.length === 0) return "Черный список пуст.";
    const lines = ["Черный список:"];
    for (const e of entries) {
        const name = e.username ? `@${e.username}` : String(e.userId);
        lines.push(`  ${name} — ${e.reason || "без причины"}`);
    }
    return lines.join("\n");
}

export function renderPortfolio(language: string): string {
    return language === "en"
        ? `Quixote.Dev portfolio and case studies:\n${PORTFOLIO_URL}`
        : `Портфолио и примеры работ Quixote.Dev:\n${PORTFOLIO_URL}`;
}

export function renderOwnerOnly(): string {
    return "Эта команда доступна только владельцу бота.";
}

export function renderRateLimit(language: string): string {
    return language === "en"
        ? "You are sending messages too quickly. Please wait a moment and try again."
        : "Слишком много сообщений подряд. Подождите немного и попробуйте снова.";
}

export function renderError(language: string): string {
    return language === "en"
        ? "An error occurred while processing. Please try again later."
        : "Произошла ошибка при обработке. Попробуйте позже.";
}

export function renderUnauthorized(): string {
    return "Доступ запрещен. Вы находитесь в черном списке.";
}

export function renderAiUnavailable(language: string): string {
    return language === "en"
        ? "Temporary technical issue. Your message has been forwarded for manual review."
        : "Временная техническая проблема. Ваше сообщение переслано на ручную проверку.";
}

export interface UnreadItemInput {
    userId: number;
    rendered: string;
}

// Разбивает список непрочитанных на чанки, влезающие в лимит Telegram.
export function buildUnreadChunks(
    header: string,
    items: UnreadItemInput[],
): Array<{ text: string; userIds: number[] }> {
    const chunks: Array<{ text: string; userIds: number[] }> = [];
    let current = header;
    let users: number[] = [];
    for (const item of items) {
        if (users.length > 0 && current.length + item.rendered.length + 2 > MAX_MESSAGE_LENGTH) {
            chunks.push({ text: current, userIds: users });
            current = "";
            users = [];
        }
        current = current ? `${current}\n\n${item.rendered}` : item.rendered;
        users.push(item.userId);
    }
    if (users.length > 0) chunks.push({ text: current, userIds: users });
    return chunks;
}
