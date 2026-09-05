// Клиент OpenRouter chat completions на fetch.

import type { Env } from "./types";

export class OpenRouterError extends Error {}

export async function chat(env: Env, system: string, user: string): Promise<string> {
    const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
            "HTTP-Referer": "https://quixotedevbot.local",
            "X-Title": "Quixote.Dev Bot",
        },
        body: JSON.stringify({
            model: env.OPENROUTER_MODEL ?? "nvidia/nemotron-3-super-120b-a12b:free",
            messages: [
                { role: "system", content: system },
                { role: "user", content: user },
            ],
            temperature: 0.3,
            max_tokens: 1500,
        }),
    });
    if (!res.ok) throw new OpenRouterError(`HTTP ${res.status}`);
    const data: unknown = await res.json();
    const content = (data as any)?.choices?.[0]?.message?.content;
    if (typeof content !== "string") throw new OpenRouterError("unexpected response shape");
    return content;
}
