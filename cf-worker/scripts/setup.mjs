// Регистрация вебхука и метаданных бота (меню команд, описание).
// Использование: node scripts/setup.mjs https://<имя>.<account>.workers.dev
// Секреты берутся из process.env или файла .dev.vars.

import { readFileSync } from "node:fs";

function loadVars() {
    const vars = { ...process.env };
    try {
        const raw = readFileSync(new URL("../.dev.vars", import.meta.url), "utf8");
        for (const line of raw.split(/\r?\n/)) {
            const m = line.match(/^([A-Z_]+)=(.*)$/);
            if (m && !vars[m[1]]) vars[m[1]] = m[2].trim();
        }
    } catch {
        // .dev.vars не обязателен
    }
    return vars;
}

const env = loadVars();
const baseUrl = process.argv[2]?.replace(/\/+$/, "");
if (!baseUrl) {
    console.error("Usage: node scripts/setup.mjs <base-url>");
    process.exit(1);
}
for (const key of ["BOT_TOKEN", "WEBHOOK_SECRET", "OWNER_ID"]) {
    if (!env[key]) {
        console.error(`Missing ${key} (set it in .dev.vars or environment)`);
        process.exit(1);
    }
}

async function api(method, body) {
    const res = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const ok = res.ok;
    const detail = await res.json().catch(() => null);
    return { ok, detail };
}

const url = `${baseUrl}/webhook/${env.WEBHOOK_SECRET}`;

let res = await api("setWebhook", {
    url,
    secret_token: env.WEBHOOK_SECRET,
    allowed_updates: ["message", "callback_query"],
});
console.log("setWebhook:", res.ok ? "OK" : JSON.stringify(res.detail));

const commands = [
    { command: "start", description: "Начать работу / Start" },
    { command: "portfolio", description: "Портфолио / Portfolio" },
    { command: "apply", description: "Быстрая заявка без вопросов" },
];
res = await api("setMyCommands", { commands });
console.log("setMyCommands:", res.ok ? "OK" : JSON.stringify(res.detail));

res = await api("setMyCommands", {
    commands: [
        ...commands,
        { command: "new", description: "Непрочитанные заявки" },
        { command: "categories", description: "Статистика по категориям" },
        { command: "broadcast", description: "Рассылка всем пользователям" },
        { command: "blacklist", description: "Чёрный список: add/remove/list" },
    ],
    scope: { type: "chat", chat_id: Number(env.OWNER_ID) },
});
console.log("setMyCommands(owner):", res.ok ? "OK" : JSON.stringify(res.detail));

res = await api("setMyShortDescription", {
    short_description:
        "Quixote.Dev — сайты, боты, автоматизация с ИИ. Портфолио: t.me/quixoted. Заявка: слово ЗАКАЗ.",
});
console.log("setMyShortDescription(ru):", res.ok ? "OK" : JSON.stringify(res.detail));

res = await api("setMyShortDescription", {
    short_description:
        "Quixote.Dev — websites, bots, AI automation. Portfolio: t.me/quixoted. Fast application: word ORDER.",
    language_code: "en",
});
console.log("setMyShortDescription(en):", res.ok ? "OK" : JSON.stringify(res.detail));
