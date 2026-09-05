# Деплой на Cloudflare Workers (бесплатно, без карты, 24/7)

TypeScript-версия бота живёт в каталоге [cf-worker/](../cf-worker/): grammY + D1.
На бесплатном тарифе нет сна и нет CPU-квот, вебхук — нативный сценарий Workers.
Нужен Node.js 18+.

## 1. Подготовка

1. Аккаунт Cloudflare: [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) — только email.
2. Локально:

```bash
cd cf-worker
npm install
npm test          # юнит-тесты логики
```

3. `.dev.vars` для локальной разработки (в git не попадает) — по образцу
   `.dev.vars.example`, значения те же, что в `.env`.

## 2. Вход и создание базы

```bash
npx wrangler login        # откроется браузер — нажмите Allow
npx wrangler d1 create quixote-bot
```

После `d1 create` скопируйте `database_id` из вывода в `wrangler.toml`
(замените `SET_AFTER_D1_CREATE`). Затем:

```bash
npx wrangler d1 migrations apply quixote-bot --remote
```

## 3. Секреты и деплой

```bash
npx wrangler secret put BOT_TOKEN           # вставить токен из .env
npx wrangler secret put OPENROUTER_API_KEY  # ключ OpenRouter
npx wrangler secret put OWNER_ID            # ваш Telegram user_id
npx wrangler secret put WEBHOOK_SECRET      # случайная строка (token_hex(32))
npx wrangler deploy
```

`wrangler deploy` напечатает URL вида `https://quixote-dev-bot.<account>.workers.dev`.

## 4. Вебхук и метаданные

```bash
npm run setup -- https://quixote-dev-bot.<account>.workers.dev
```

Скрипт вызовет `setWebhook` (с секретом), зарегистрирует меню команд
(`/start`, `/portfolio`, `/apply` + админские у владельца) и короткое
описание бота. **Перед этим остановите polling-версию бота** — polling и
вебхук взаимоисключающие.

## 5. Обновление

```bash
git pull && npm install && npm test
npx wrangler deploy
```

## 6. Диагностика

```bash
npx wrangler tail        # живые логи
```

Ошибки также видны в дашборде Cloudflare: Workers & Pages → quixote-dev-bot → Logs.

## Отличия от Python-версии

- Логика перенесена 1:1 (fast-track «ЗАКАЗ», диалог с TTL, автобан за спам,
  rate limit, чанки /new); база стартует пустой.
- Логи — в `wrangler tail`/дашборде вместо файлов.
- Локальный Python-бот остаётся в репо для разработки.
