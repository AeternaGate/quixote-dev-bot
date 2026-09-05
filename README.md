# Quixote.Dev Bot

Telegram-бот для первичного сбора фриланс-заявок с ИИ-классификацией.

## Возможности

- Принимает текстовые описания проектов
- ИИ анализирует заявку, классифицирует по категориям
- Задает уточняющие вопросы (максимум 5) если ТЗ неполное
- Отправляет владельцу структурированное уведомление с `#категорией` и `@username`
- Управление черным списком и rate limiting
- Поддержка русского и английского языков

## Быстрый старт

```bash
# 1. Клонируйте и установите зависимости
pip install -e ".[dev]"

# 2. Создайте .env файл
cp .env.example .env
# Заполните BOT_TOKEN, OWNER_ID (ваш Telegram user_id) и OPENROUTER_API_KEY
# Файл .env загружается автоматически при запуске

# 3. Запустите
python -m src.quixote_bot.main
```

## Команды

### Клиентские
- `/start` — начало диалога, выбор языка
- `/apply <текст>` — быстрая заявка напрямую владельцу (без ИИ и вопросов)
- Слово **ЗАКАЗ** в начале сообщения — то же самое, что /apply

Приветствие после выбора языка содержит чек-лист из 5 пунктов (задача, бюджет, сроки,
технологии, материалы) — если клиент пришлёт ответы сразу, уточняющие вопросы ИИ не понадобятся.

### Админские (только владелец)
- `/new` — непрочитанные сообщения
- `/categories` — статистика по категориям
- `/broadcast <текст>` — рассылка всем пользователям
- `/blacklist add <id> [причина]` — добавить в черный список
- `/blacklist remove <id>` — удалить из черного списка
- `/blacklist list` — список заблокированных

## Тесты

```bash
python -m pytest tests/ -v
```

## Безопасность

- Секреты живут только в `.env` (git его игнорирует); шаблон — `.env.example`.
- Pre-commit хук блокирует коммит `.env`, локальной БД и строк, похожих на токены:

```bash
git config core.hooksPath .githooks
```

## Деплой (бесплатно)

- **PythonAnywhere** — без карты, 24/7, режим вебхуков:
  [docs/deploy-pythonanywhere.md](docs/deploy-pythonanywhere.md)
- **Oracle Cloud Always Free** — бесплатная VM, Docker Compose:
  [docs/deploy-oracle.md](docs/deploy-oracle.md)

## Линт

```bash
ruff check src tests
```

## Запуск в Docker

```bash
docker build -t quixote-dev-bot .
docker run -d --name quixote-dev-bot --env-file .env -v "$(pwd)/data:/app/data" quixote-dev-bot
```

## Архитектура

- `config.py` — настройки из переменных окружения
- `storage.py` — SQLite: пользователи, сообщения, диалоги, blacklist
- `openrouter.py` — клиент OpenRouter с retry
- `qualification.py` — промпт ИИ, классификация, fallback
- `messages.py` — все текстовые шаблоны
- `handlers.py` — aiogram обработчики
- `main.py` — точка входа
