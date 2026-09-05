# Деплой на Oracle Cloud Always Free

Бот работает через long polling: ему не нужны входящие порты, но нужен процесс 24/7
и постоянный диск для SQLite. Бесплатной VM Oracle это хватает с запасом.

## 1. Регистрация

1. Зайдите на [cloud.oracle.com](https://cloud.oracle.com/) → «Start for free».
2. Понадобятся email и банковская карта (для подтверждения; на Always Free не списывается).
3. **Важно:** «Home region» выбирается один раз и потом не меняется.
4. Нюансы:
   - Карты некоторых банков (в т.ч. РФ) регистрацию не проходят — известная проблема.
     Запасные варианты: Google Cloud `e2-micro` (Always Free, US-регионы) или хостинг на своём ПК.
   - После регистрации аккаунт находится в 30-дневном триале — Always Free ресурсы
     (VM, диск) не выключаются после его окончания.

## 2. Создание VM

Compute → Instances → Create Instance:

- **Image:** Ubuntu 24.04 (Minimal — тоже подойдёт).
- **Shape:** `Ampere A1.Flex` → 1 OCPU, 6 GB RAM. Если увидите «Out of capacity» —
  возьмите `VM.Standard.E2.1.Micro` (AMD, всегда бесплатны, их даже 2 штуки можно).
- **SSH keys:** сгенерируйте пару и скачайте приватный ключ (или загрузите свой публичный).
- После создания запишите **Public IP address**.

## 3. Настройка сервера (однократно)

```bash
ssh -i <путь-к-ключу> ubuntu@<PUBLIC_IP>

sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades   # авто-обновления безопасности
sudo usermod -aG docker ubuntu                    # затем перелогиниться
```

Брандмауэр настраивать не нужно: боту хватает исходящих соединений (polling),
входящие порты не открываются вовсе.

## 4. Деплой

```bash
# на сервере
git clone https://github.com/AeternaGate/quixote-dev-bot.git
cd quixote-dev-bot
```

```bash
# с локальной машины — секреты передаются отдельно и в git не попадают
scp -i <путь-к-ключу> .env ubuntu@<PUBLIC_IP>:~/quixote-dev-bot/.env
```

```bash
# на сервере
docker compose up -d --build
docker compose logs -f    # ждём строку "Run polling for bot @quixotedevbot"
```

Если репозиторий приватный — при `git clone` используйте Personal Access Token
вместо пароля или добавьте на VM deploy key.

**Перед запуском убедитесь, что локальный экземпляр бота остановлен** — иначе
Telegram вернёт `409 Conflict` за опрос одного бота двумя процессами.

## 5. Обновление

```bash
cd ~/quixote-dev-bot
git pull
docker compose up -d --build
```

## 6. Бэкап базы

SQLite лежит в `./data/bot.db` (bind mount, переживает пересоздание контейнера).
Ежедневная копия через cron:

```bash
mkdir -p ~/backups
crontab -e
```

```
0 4 * * * cp ~/quixote-dev-bot/data/bot.db ~/backups/bot-$(date +\%F).db
```

В базе переписка с клиентами — выкладывать бэкапы наружу не стоит.

## 7. Диагностика

```bash
docker compose logs -f     # живые логи
docker compose restart     # перезапуск
docker compose ps          # статус
```

Политика `restart: unless-stopped` поднимает контейнер после падения и перезагрузки VM.
