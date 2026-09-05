# Деплой на PythonAnywhere (бесплатно, без карты)

Бот работает через вебхуки: Telegram сам присылает обновления на HTTPS-адрес,
постоянно висящий процесс не нужен. SQLite остаётся — диск на PA постоянный.
Оба нужных домена (`api.telegram.org`, `openrouter.ai`) уже в whitelist
бесплатного тарифа ([список](https://www.pythonanywhere.com/whitelist/)).

## Ограничения бесплатного тарифа

- ~100 CPU-секунд в день: ожидание ответов сети не расходует CPU, классификация
  тратит миллисекунды — для личного потока заявок запас большой.
- Один воркер: ИИ-вызов (до ~60 с) задерживает обработку следующего апдейта.
- Один веб-домен: `https://<логин>.pythonanywhere.com`.
- Исходящие запросы идут через прокси PA — настраивается ниже.

## 1. Регистрация и код

1. Регистрация на [pythonanywhere.com](https://www.pythonanywhere.com/) —
   достаточно email, карта не нужна.
2. Consoles → Bash:

```bash
git clone https://github.com/AeternaGate/quixote-dev-bot.git
cd quixote-dev-bot
mkvirtualenv venv --python=python3.13
pip install -e .
```

## 2. Файл .env

Создайте `.env` в корне проекта (Files → New File, или `nano .env` в консоли) с теми же
переменными, что и локально, плюс две новые:

```
BOT_TOKEN=...
OPENROUTER_API_KEY=...
OWNER_ID=...
TELEGRAM_WEBHOOK_SECRET=<случайная строка>
PROXY_URL=http://<логин-PA>:<API-токен-PA>@proxy.pythonanywhere.com:3128
```

`TELEGRAM_WEBHOOK_SECRET` — сгенерируйте: `python -c "import secrets; print(secrets.token_hex(32))"`.
`PROXY_URL` — прокси PA Free: логин и API-токен из вкладки Account (см.
[справку PA о прокси](https://help.pythonanywhere.com/pages/proxy/)).

## 3. Веб-приложение

1. Web → Add a new web app → Manual configuration → Python 3.13.
2. В секции Virtualenv укажите путь: `/home/<логин>/.virtualenvs/venv`.
3. Source code / Working directory: `/home/<логин>/quixote-dev-bot`.
4. WSGI configuration file — замените содержимое на:

```python
import os
import sys

sys.path.insert(0, "/home/<логин>/quixote-dev-bot")
os.environ["PROXY_URL"] = "http://<логин-PA>:<API-токен-PA>@proxy.pythonanywhere.com:3128"

from src.quixote_bot.webapp import create_app

application = create_app()
```

5. Нажмите зелёную **Reload**.

Проверка: откройте `https://<логин>.pythonanywhere.com/` — должно ответить
«quixote-dev-bot webhook endpoint».

## 4. Включить вебхук

Polling и вебхук взаимоисключающие: **сначала остановите локального бота**,
затем в Bash-консоли PA:

```bash
cd ~/quixote-dev-bot
export PROXY_URL="http://<логин-PA>:<API-токен-PA>@proxy.pythonanywhere.com:3128"
python -m src.quixote_bot.webhook_setup https://<логин>.pythonanywhere.com
```

Скрипт зарегистрирует вебхук (с секретом) и метаданные (меню команд, описание).
После этого напишите боту в Telegram — всё должно работать.

Если позже решите вернуться к polling, вебхук нужно снять (`bot.delete_webhook()` —
попросите, и я добавлю эту операцию флагом в `webhook_setup`).

## 5. Обновление кода

```bash
cd ~/quixote-dev-bot
git pull
pip install -e .   # если менялись зависимости
```

Затем Web → **Reload**.

## 6. Диагностика и бэкапы

- Ошибки: Web → Error log (там же видны логи exception'ов хендлеров).
- База: `~/quixote-dev-bot/data/bot.db` — периодически скачивайте копию через Files.
- База с перепиской клиентов наружу выкладываться не должна.
