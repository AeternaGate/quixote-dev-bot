from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import Settings
from .messages import (
    LANG_BUTTONS,
    LANG_OPTIONS,
    render_ai_unavailable,
    render_blacklist_list,
    render_blacklist_result,
    render_broadcast_confirm,
    render_categories,
    render_confirmation,
    render_error,
    render_max_questions,
    render_media_instruction,
    render_owner_notification,
    render_owner_only,
    render_processing,
    render_unread_header,
    render_unread_item,
    render_unauthorized,
    render_welcome,
)
from .openrouter import OpenRouterClient, OpenRouterError
from .qualification import (
    SYSTEM_PROMPT,
    analyze_with_retry,
    build_user_context,
    get_next_question,
    should_ask_question,
)
from .storage import Storage


def is_owner(user_id: int, settings: Settings) -> bool:
    return user_id == settings.owner_id


def setup_handlers(dp: Dispatcher, settings: Settings, storage: Storage, ai_client: OpenRouterClient) -> None:
    router = Router()

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
    async def on_language选择(callback: CallbackQuery) -> None:
        lang = callback.data.split(":")[1]
        uid = callback.from_user.id
        uname = callback.from_user.username
        storage.ensure_user(uid, uname)
        storage.set_language(uid, lang)

        await callback.message.edit_text(render_welcome(lang))
        await callback.answer()

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
        parts = [header]
        for msg in unread:
            user = storage.get_user(msg.user_id)
            uname = user.username if user else None
            parts.append(render_unread_item(msg.id, msg.user_id, uname, msg.text, msg.category))
            storage.mark_read(msg.user_id)

        await message.answer("\n\n".join(parts))

    @router.message(Command("categories"))
    async def cmd_categories(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        stats = storage.get_category_counts()
        await message.answer(render_categories(stats))

    @router.message(Command("broadcast"))
    async def cmd_broadcast(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        text = message.text.replace("/broadcast", "").strip()
        if not text:
            await message.answer("Использование: /broadcast <сообщение>")
            return

        count = 0
        # Send to all non-blacklisted users who interacted
        rows = storage._conn.execute(
            "SELECT DISTINCT user_id FROM messages WHERE user_id NOT IN "
            "(SELECT user_id FROM users WHERE is_blacklisted = 1)"
        ).fetchall()
        for row in rows:
            try:
                await message.bot.send_message(row["user_id"], text)
                count += 1
            except Exception:
                pass

        await message.answer(render_broadcast_confirm(count))

    @router.message(Command("blacklist"))
    async def cmd_blacklist(message: Message) -> None:
        if not is_owner(message.from_user.id, settings):
            await message.answer(render_owner_only())
            return

        parts = message.text.split(maxsplit=2)
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
            rows = storage._conn.execute(
                "SELECT u.user_id, u.username, bl.reason FROM users u "
                "JOIN blacklist_log bl ON u.user_id = bl.user_id "
                "WHERE u.is_blacklisted = 1"
            ).fetchall()
            entries = [(r["user_id"], r["username"], r["reason"]) for r in rows]
            await message.answer(render_blacklist_list(entries))
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

    @router.message(F.content_type.in_({"photo", "video", "document", "voice", "video_note", "sticker", "animation"}))
    async def on_media(message: Message) -> None:
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
        uid = message.from_user.id
        uname = message.from_user.username
        text = message.text.strip()

        if not text:
            return

        storage.ensure_user(uid, uname)
        user = storage.get_user(uid)
        lang = user.language if user else "ru"

        if is_owner(uid, settings):
            return

        if storage.is_blacklisted(uid):
            await message.answer(render_unauthorized())
            return

        if not storage.check_rate_limit(uid, settings.rate_limit, settings.rate_window):
            await message.answer(render_error(lang))
            return

        conv = storage.get_conversation(uid)
        if conv and conv.step == "idle":
            storage.clear_conversation(uid)
            conv = None

        await message.answer(render_processing(lang))

        # Save user message
        storage.save_message(uid, text)

        # AI analysis
        try:
            context = build_user_context([text])
            analysis = analyze_with_retry(lambda: ai_client.chat(SYSTEM_PROMPT, context))
        except OpenRouterError:
            analysis = analyze_with_retry(lambda: "")  # triggers fallback
            await message.answer(render_ai_unavailable(lang))

        category = analysis.category
        storage.save_message(uid, text, category)

        if analysis.category == "спам":
            storage.blacklist_add(uid, "автоматический спам")
            return

        conv = storage.get_conversation(uid)
        questions_asked = conv.questions_asked if conv else 0

        if should_ask_question(analysis, questions_asked):
            question = get_next_question(questions_asked, lang)
            if question:
                storage.upsert_conversation(uid, "asking", questions_asked + 1)
                await message.answer(question)
                return

        # Completed — send to owner
        storage.clear_conversation(uid)
        storage.mark_read(uid)

        user = storage.get_user(uid)
        uname = user.username if user else None
        notification = render_owner_notification(uid, uname, text, analysis, questions_asked)

        try:
            await message.bot.send_message(settings.owner_id, notification)
        except Exception:
            pass

        client_reply = analysis.client_reply
        if client_reply:
            await message.answer(client_reply)
        else:
            fallback = render_max_questions(lang) if questions_asked else render_confirmation(lang)
            await message.answer(fallback)

    dp.include_router(router)
