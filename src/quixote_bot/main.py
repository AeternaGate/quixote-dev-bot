import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeChat
from dotenv import load_dotenv

from .config import Settings
from .handlers import setup_handlers
from .messages import SHORT_DESCRIPTIONS
from .openrouter import OpenRouterClient
from .storage import Storage


async def setup_bot_metadata(bot: Bot, settings: Settings) -> None:
    """Short pre-start description and the / command menu; failures are non-fatal."""
    try:
        await bot.set_my_short_description(SHORT_DESCRIPTIONS["ru"])
        await bot.set_my_short_description(SHORT_DESCRIPTIONS["en"], language_code="en")
    except Exception:
        logging.warning("Failed to set bot short description")

    commands = [
        BotCommand(command="start", description="Начать работу / Start"),
        BotCommand(command="portfolio", description="Портфолио / Portfolio"),
        BotCommand(command="apply", description="Быстрая заявка без вопросов"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception:
        logging.warning("Failed to set default command menu")

    owner_commands = commands + [
        BotCommand(command="new", description="Непрочитанные заявки"),
        BotCommand(command="categories", description="Статистика по категориям"),
        BotCommand(command="broadcast", description="Рассылка всем пользователям"),
        BotCommand(command="blacklist", description="Чёрный список: add/remove/list"),
    ]
    try:
        await bot.set_my_commands(
            owner_commands, scope=BotCommandScopeChat(chat_id=settings.owner_id)
        )
    except Exception:
        logging.warning("Failed to set owner command menu (owner may not have started the bot yet)")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    load_dotenv()

    try:
        settings = Settings.from_env()
    except ValueError as e:
        logging.error("%s", e)
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

    await setup_bot_metadata(bot, settings)

    logging.info("Quixote.Dev bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        storage.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
