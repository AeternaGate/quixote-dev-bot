"""One-shot helper: register the Telegram webhook and bot metadata, then exit.

Usage:
    python -m src.quixote_bot.webhook_setup https://<username>.pythonanywhere.com

Stop the polling bot before registering the webhook: Telegram delivers updates
either via polling or via webhook, never both.
"""

import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from .config import Settings
from .main import setup_bot_metadata


async def run(base_url: str) -> None:
    settings = Settings.from_env()
    if not settings.webhook_secret:
        raise SystemExit(
            "TELEGRAM_WEBHOOK_SECRET is not set. "
            "Generate one, e.g.: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    session = AiohttpSession(proxy=settings.proxy_url or None)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=None),
    )
    try:
        url = f"{base_url.rstrip('/')}/webhook/{settings.webhook_secret}"
        await bot.set_webhook(
            url,
            secret_token=settings.webhook_secret,
            allowed_updates=["message", "callback_query"],
        )
        await setup_bot_metadata(bot, settings)
        print(f"Webhook registered: {url}")
    finally:
        await bot.session.close()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python -m {__name__} <base-url, e.g. https://user.pythonanywhere.com>")
    asyncio.run(run(sys.argv[1]))


if __name__ == "__main__":
    main()
