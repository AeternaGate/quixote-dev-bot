import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .config import Settings
from .handlers import setup_handlers
from .openrouter import OpenRouterClient
from .storage import Storage


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    settings = Settings.from_env()

    if not settings.bot_token:
        logging.error("BOT_TOKEN is required. Set it in .env or environment.")
        return

    if not settings.openrouter_api_key:
        logging.warning("OPENROUTER_API_KEY is not set. AI analysis will use fallback.")

    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    storage = Storage(settings.db_path)

    ai_client = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher()

    setup_handlers(dp, settings, storage, ai_client)

    logging.info("Quixote.Dev bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        storage.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
