"""WSGI entrypoint for hosts without always-on processes (e.g. PythonAnywhere Free).

Each Telegram webhook request is processed in a fresh event loop with a
throwaway Bot session: WSGI workers give us no persistent loop to keep an
aiohttp session alive in. SQLite and all handlers are shared with the polling
entrypoint.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Update
from flask import Flask, Response, abort, request

from .config import Settings
from .handlers import setup_handlers
from .openrouter import OpenRouterClient
from .storage import Storage

logger = logging.getLogger(__name__)


def _apply_proxy(settings: Settings) -> None:
    if not settings.proxy_url:
        return
    # The OpenRouter client uses urllib, which honours env proxies out of the box.
    os.environ.setdefault("HTTPS_PROXY", settings.proxy_url)
    os.environ.setdefault("HTTP_PROXY", settings.proxy_url)


def _make_bot(settings: Settings) -> Bot:
    session = AiohttpSession(proxy=settings.proxy_url or None)
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=None),
    )


def create_app() -> Flask:
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv

    load_dotenv()
    settings = Settings.from_env()
    _apply_proxy(settings)

    storage = Storage(settings.db_path)
    ai_client = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model)
    dp = Dispatcher()
    setup_handlers(dp, settings, storage, ai_client)

    app = Flask(__name__)
    secret_path = f"/webhook/{settings.webhook_secret}" if settings.webhook_secret else "/webhook"

    @app.get("/")
    def health() -> str:
        return "quixote-dev-bot webhook endpoint"

    @app.post(secret_path)
    def webhook() -> Response:
        sent_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if settings.webhook_secret and sent_secret != settings.webhook_secret:
            abort(403)

        payload = request.get_json(force=True, silent=True)
        if not isinstance(payload, dict):
            abort(400)

        bot = _make_bot(settings)

        async def process() -> None:
            try:
                update = Update.model_validate(payload)
                await dp.feed_webhook_update(bot, update)
            finally:
                await bot.session.close()

        try:
            asyncio.run(process())
        except Exception:
            logger.exception("Webhook processing failed")
            return Response("error", status=500)
        return Response("ok", status=200)

    return app
