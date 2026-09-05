# Деплой на Serv00 (бесплатно, без карты)

Serv00 — бесплатный shared-хостинг (FreeBSD) с SSH, постоянным диском и cron.
Регистрация по email: [serv00.com](https://www.serv00.com/) — карту не спрашивают.
Бот живёт 24/7 независимо от вашего ПК; надзор за процессом делает cron.

## 1. Регистрация

1. [serv00.com](https://www.serv00.com/) → Registration: ник, email, сервер (любой
   свободный, например s1–sN). Пароль приходит письмом.
2. Дождитесь активации (обычно мгновенно, иногда очередь).
3. Логин для SSH = ваш ник, хост = `s<N>.serv00.com`, порт 22.

## 2. Деплой

Выполняется с машины, у которой есть SSH-доступ (логин/пароль от панели):

```bash
ssh <ник>@s<N>.serv00.com
# на сервере:
git clone https://github.com/AeternaGate/quixote-dev-bot.git ~/quixote-dev-bot
cd ~/quixote-dev-bot
python3 -m venv ~/.venvs/quixote
~/.venvs/quixote/bin/pip install -e .
cp .env.example .env   # затем заполнить реальными ключами (nano .env)
```

## 3. Запуск и надзор

Скрипт `scripts/serv00_watchdog.sh` проверяет процесс и поднимает его, если
умер (после перезагрузки сервера в том числе). Добавить в cron:

```bash
crontab -e
```

```
*/5 * * * * /home/<ник>/quixote-dev-bot/scripts/serv00_watchdog.sh
```

Первый запуск — вручную: `./scripts/serv00_watchdog.sh`, затем проверить:

```bash
tail -f ~/quixote-dev-bot/bot.log   # ждём "Run polling for bot @quixotedevbot"
```

**Важно:** локальный экземпляр бота должен быть остановлен до первого запуска
на сервере — Telegram не отдаст апдейты двум поллерам (409 Conflict).

## 4. Обновление

```bash
cd ~/quixote-dev-bot
git pull
~/.venvs/quixote/bin/pip install -e .   # если менялись зависимости
kill $(cat bot.pid)                      # watchdog поднимет новую версию за 5 минут
```

## 5. Диагностика

```bash
tail -50 ~/quixote-dev-bot/bot.log
ps aux | grep quixote
```

## Нюансы Serv00

- Shared-хостинг: мягкие лимиты CPU. Профиль бота (почти всё время — ожидание
  сети) туда влезает; не запускайте на нём ничего тяжёлого.
- Панель может сбросить процессы при обслуживании — cron-надзор поднимает бота
  в течение 5 минут.
- Логи и база лежат в `~/quixote-dev-bot/`; диск постоянный.
