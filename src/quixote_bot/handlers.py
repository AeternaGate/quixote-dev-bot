import asyncio
import logging
import time

from aiogram import Dispatcher, F, Router
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, ErrorEvent, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import Settings
from .messages import (
    FAST_TRACK_WORDS,
    LANG_BUTTONS,
    LANG_OPTIONS,
    render_ai_unavailable,
    render_blacklist_list,
    render_blacklist_result,
    render_broadcast_confirm,
    render_categories,
    render_confirmation,
    render_error,
    render_fast_track_notification,
    render_fast_track_usage,
    render_max_questions,
    render_media_instruction,
    render_owner_notification,
    render_owner_only,
    render_portfolio,
    render_processing,
    render_rate_limit,
    render_unauthorized,
    render_unread_header,
    render_unread_item,
    render_welcome,
)
from .openrouter import OpenRouterClient, OpenRouterError
from .qualification import (
    CONVERSATION_TTL_SECONDS,
    SYSTEM_PROMPT,
    analyze_with_retry,
    build_user_context,
    fallback_analysis,
    get_next_question,
    parse_context,
    serialize_context,
    should_ask_question,
)
from .storage import Storage

logger = logging.getLogger(__name__)

# Telegram rejects messages over 4096 characters; keep a safety margin.
MAX_MESSAGE_LENGTH = 3900


def is_owner(user_id: int, settings: Settings) -> bool:
    return user_id == settings.owner_id


def setup_handlers(dp: Dispatcher, settings: Settings, storage: Storage, ai_client: OpenRouterClient) -> None:
    router = Router()

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Unhandled exception while processing update: %s", event.exception)
        message = event.update.message
        if message is None or not hasattr(message, "answer"):
            return
        try:
            user = storage.get_user(message.from_user.id) if message.from_user else None
            lang = user.language if user else "ru"
            await message.answer(render_error(lang))
        except Exception:
            logger.warning("Failed to deliver error notice to the user")

    async def send_fast_track(message: Message, lang: str, body: str) -> None:
        uid = message.from_user.id
        user = storage.get_user(uid)
        uname = user.username if user else None
        storage.clear_conversation(uid)
        storage.save_message(uid, body, "готовое ТЗ")
        try:
            await message.bot.send_message(
                settings.owner_id, render_fast_track_notification(uid, uname, body)
            )
        except Exception:
            logger.exception("Failed to deliver fast-track application for user %s", uid)
        else:
            # Keep unread on delivery failure so /new can pick the lead up.
            storage.mark_read(uid)
        await message.answer(render_confirmation(lang))

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        uid = message.from_user.id
        uname = message.from_user.username
        storage.ensure_user(uid, uname)
        user = storage.get_user(uid)
        lang = user.language if user else "ru"

        builder = InlineKeyboardBuilder()
        for code, label in LANG_BUTTONS.items():
            builder.button(text=label, callback_data=f"lang:{code}")

        await message.answer(LANG_OPTIONS.get(lang, LANG_OPTIONS["ru"]), reply_markup=builder.as_markup())

    @router.callback_query(F.data.startswith("lang:"))
    async def on_language_selected(callback: CallbackQuery) -> None:
        lang = callback.data.split(":")[1]
        if lang not in LANG_BUTTONS:
            await callback.answer()
            return
        uid = callback.from_user.id
        uname = callback.from_user.username
        storage.ensure_user(uid, uname)
        storage.set_language(uid, lang)

        await callback.message.edit_text(render_welcome(lang))
        await callback.answer()

    @router.message(Command("portfolio"))
    async def cmd_portfolio(message: Message) -> None:
        if message.from_user is None:
            return
        user = storage.get_user(message.from_user.id)
        lang = user.language if user else "ru"
        await message.answer(render_portfolio(lang))

    @router.message(Command("new"))
    async def cmd_new(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        unread = storage.get_unread()
        if not unread:
            await message.answer("Нет непрочитанных сообщений.")
            return

        header = render_unread_header(len(unread))
        chunks: list[tuple[str, set[int]]] = []
        current_text = header
        current_users: set[int] = set()
        for msg in unread:
            user = storage.get_user(msg.user_id)
            uname = user.username if user else None
            item = render_unread_item(msg.id, msg.user_id, uname, msg.text, msg.category)
            if current_users and len(current_text) + len(item) + 2 > MAX_MESSAGE_LENGTH:
                chunks.append((current_text, current_users))
                current_text = ""
                current_users = set()
            current_text = f"{current_text}\n\n{item}" if current_text else item
            current_users.add(msg.user_id)
        if current_users:
            chunks.append((current_text, current_users))

        # Mark messages read only after their chunk was actually delivered,
        # so a failed send leaves them for the next /new call.
        for chunk_text, user_ids in chunks:
            await message.answer(chunk_text)
            for uid in user_ids:
                storage.mark_read(uid)

    @router.message(Command("categories"))
    async def cmd_categories(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        stats = storage.get_category_counts()
        await message.answer(render_categories(stats))

    @router.message(Command("broadcast"))
    async def cmd_broadcast(message: Message, command: CommandObject) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        text = (command.args or "").strip()
        if not text:
            await message.answer("Использование: /broadcast <сообщение>")
            return

        count = 0
        failed = 0
        for uid in storage.get_broadcast_targets():
            try:
                await message.bot.send_message(uid, text)
                count += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await message.bot.send_message(uid, text)
                    count += 1
                except Exception:
                    failed += 1
                    logger.warning("Broadcast to %s failed after retry", uid)
            except Exception:
                failed += 1
                logger.warning("Broadcast to %s failed", uid)
            await asyncio.sleep(0.05)

        if failed:
            logger.warning("Broadcast finished: %d delivered, %d failed", count, failed)
        await message.answer(render_broadcast_confirm(count))

    @router.message(Command("blacklist"))
    async def cmd_blacklist(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        parts = message.text.split(maxsplit=3)
        if len(parts) < 2:
            await message.answer(
                "Использование:\n"
                "/blacklist add <user_id> [причина]\n"
                "/blacklist remove <user_id>\n"
                "/blacklist list"
            )
            return

        action = parts[1].lower()

        if action == "list":
            await message.answer(render_blacklist_list(storage.get_blacklist()))
            return

        if len(parts) < 3:
            await message.answer("Укажите user_id.")
            return

        try:
            target_id = int(parts[2])
        except ValueError:
            await message.answer("user_id должен быть числом.")
            return

        reason = parts[3] if len(parts) > 3 else ""

        if action == "add":
            success = storage.blacklist_add(target_id, reason)
            await message.answer(render_blacklist_result("add", str(target_id), success))
        elif action == "remove":
            success = storage.blacklist_remove(target_id)
            await message.answer(render_blacklist_result("remove", str(target_id), success))
        else:
            await message.answer("Неизвестная команда. Используйте add/remove/list.")

    @router.message(Command("apply"))
    async def cmd_apply(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        uid = message.from_user.id
        text = (command.args or "").strip()

        storage.ensure_user(uid, message.from_user.username)
        user = storage.get_user(uid)
        lang = user.language if user else "ru"

        if is_owner(uid, settings):
            return

        if storage.is_blacklisted(uid):
            await message.answer(render_unauthorized())
            return

        if not text:
            await message.answer(render_fast_track_usage(lang))
            return

        if not storage.check_rate_limit(uid, settings.rate_limit, settings.rate_window):
            await message.answer(render_rate_limit(lang))
            return

        await send_fast_track(message, lang, text)

    @router.message(F.content_type.in_({"photo", "video", "document", "voice", "video_note", "sticker", "animation"}))
    async def on_media(message: Message) -> None:
        if message.from_user is None:
            return
        uid = message.from_user.id
        user = storage.get_user(uid)
        lang = user.language if user else "ru"

        if is_owner(uid, settings):
            return

        if storage.is_blacklisted(uid):
            return

        await message.answer(render_media_instruction(lang))

    @router.message(F.text)
    async def on_text(message: Message) -> None:
        if message.from_user is None:
            return
        uid = message.from_user.id
        text = message.text.strip()

        if not text:
            return

        storage.ensure_user(uid, message.from_user.username)
        user = storage.get_user(uid)
        lang = user.language if user else "ru"

        if is_owner(uid, settings):
            return

        if storage.is_blacklisted(uid):
            await message.answer(render_unauthorized())
            return

        if not storage.check_rate_limit(uid, settings.rate_limit, settings.rate_window):
            await message.answer(render_rate_limit(lang))
            return

        # Fast track: a message starting with the magic word goes straight to
        # the owner as a ready application, with no AI call and no questions.
        first_word, _, rest = text.partition(" ")
        if first_word.strip(".,:!?;\"'()").lower() in FAST_TRACK_WORDS:
            body = rest.strip()
            if not body:
                await message.answer(render_fast_track_usage(lang))
                return
            await send_fast_track(message, lang, body)
            return

        conv = storage.get_conversation(uid)
        if conv and time.time() - conv.started_at > CONVERSATION_TTL_SECONDS:
            storage.clear_conversation(uid)
            conv = None

        # Accumulate the brief: the original message plus answers to
        # clarifying questions are classified together.
        context_messages = parse_context(conv.context) if conv else []
        context_messages.append(text)

        await message.answer(render_processing(lang))

        # The OpenRouter client is blocking (up to 30 s per attempt), so run
        # classification in a worker thread to keep the event loop responsive.
        try:
            analysis = await asyncio.to_thread(
                analyze_with_retry,
                lambda: ai_client.chat(SYSTEM_PROMPT, build_user_context(context_messages)),
            )
        except OpenRouterError as e:
            logger.warning("AI analysis failed for user %s: %s", uid, e)
            analysis = fallback_analysis()
            await message.answer(render_ai_unavailable(lang))

        storage.save_message(uid, text, analysis.category)

        if analysis.category == "спам":
            logger.info("User %s auto-blacklisted as spam", uid)
            storage.blacklist_add(uid, "автоматический спам")
            return

        questions_asked = conv.questions_asked if conv else 0

        if should_ask_question(analysis, questions_asked):
            question = get_next_question(questions_asked, lang)
            if question:
                storage.upsert_conversation(
                    uid, "asking", questions_asked + 1, serialize_context(context_messages)
                )
                await message.answer(question)
                return

        # Completed — send to owner
        storage.clear_conversation(uid)

        uname = user.username if user else None
        brief = "\n\n".join(context_messages)
        notification = render_owner_notification(uid, uname, brief, analysis, questions_asked)

        try:
            await message.bot.send_message(settings.owner_id, notification)
        except Exception:
            logger.exception("Failed to deliver lead notification for user %s", uid)
        else:
            # Keep unread on delivery failure so /new can pick the lead up.
            storage.mark_read(uid)

        client_reply = analysis.client_reply
        if client_reply:
            await message.answer(client_reply)
        else:
            fallback = render_max_questions(lang) if questions_asked else render_confirmation(lang)
            await message.answer(fallback)

    dp.include_router(router)
