import asyncio
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram import Dispatcher
from aiogram.filters import CommandObject

from src.quixote_bot.config import Settings
from src.quixote_bot.handlers import setup_handlers
from src.quixote_bot.messages import render_ai_unavailable, render_rate_limit, render_unauthorized
from src.quixote_bot.openrouter import OpenRouterError
from src.quixote_bot.storage import Storage


def valid_json(**changes):
    value = {
        "category": "готовое ТЗ", "ready": True, "question": None,
        "summary": "Сайт", "urgency": "обычная", "budget": "$500",
        "timeline": "2 недели", "risks": [], "recommended_reply": "Изучу задачу.",
        "client_reply": None,
    }
    value.update(changes)
    return json.dumps(value)


class FakeAIClient:
    """Sync stand-in for OpenRouterClient that records prompts and replays results."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def chat(self, system, user):
        self.calls.append(user)
        if not self._results:
            raise AssertionError("unexpected extra AI call")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FailingAIClient:
    def chat(self, system, user):
        raise OpenRouterError("connection failed")


def make_settings(db_path, owner_id=999, rate_limit=100):
    return Settings(
        bot_token="test-token",
        openrouter_api_key="test-key",
        owner_id=owner_id,
        db_path=db_path,
        openrouter_model="test-model",
        rate_limit=rate_limit,
        rate_window=300,
    )


def make_message(user_id, text, username="alice"):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id, username=username),
        text=text,
        content_type="text",
        answer=AsyncMock(),
        bot=SimpleNamespace(send_message=AsyncMock()),
    )


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.storage = Storage(self.db)
        self.settings = make_settings(self.db)
        self.storage.ensure_user(self.settings.owner_id, "owner")

    def tearDown(self):
        self.storage.close()
        os.unlink(self.db)

    def wire(self, ai_client):
        dp = Dispatcher()
        setup_handlers(dp, self.settings, self.storage, ai_client)
        return dp

    def get_handler(self, dp, name):
        router = dp.sub_routers[0]
        for handler in router.message.handlers:
            if handler.callback.__name__ == name:
                return handler.callback
        raise KeyError(name)

    def answers(self, message):
        return [call.args[0] for call in message.answer.call_args_list]

    def test_message_saved_once_and_delivered(self):
        ai = FakeAIClient([valid_json()])
        dp = self.wire(ai)
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "Нужен сайт-визитка")
        asyncio.run(on_text(msg))

        self.assertEqual(self.storage.get_category_counts(), {"готовое ТЗ": 1})
        self.assertEqual(self.storage.get_unread(), [])
        msg.bot.send_message.assert_called_once()
        self.assertIn("Нужен сайт-визитка", msg.bot.send_message.call_args.args[1])
        self.assertEqual(
            self.answers(msg)[-1],
            "Спасибо! Ваше сообщение получено и переслано на рассмотрение. С вами свяжутся в ближайшее время.",
        )

    def test_rate_limit_replies_with_dedicated_text(self):
        self.settings = make_settings(self.db, rate_limit=1)
        dp = self.wire(FakeAIClient([valid_json()]))
        on_text = self.get_handler(dp, "on_text")

        first = make_message(1, "первая заявка")
        asyncio.run(on_text(first))
        second = make_message(1, "вторая заявка")
        asyncio.run(on_text(second))

        self.assertIn(render_rate_limit("ru"), self.answers(second))
        self.assertNotIn(render_rate_limit("ru"), self.answers(first))

    def test_conversation_context_accumulates(self):
        ai = FakeAIClient([
            valid_json(category="потенциальный заказ", ready=False, question="Какой бюджет?"),
            valid_json(),
        ])
        dp = self.wire(ai)
        on_text = self.get_handler(dp, "on_text")

        first = make_message(1, "Нужен бот для магазина")
        asyncio.run(on_text(first))
        conv = self.storage.get_conversation(1)
        self.assertIsNotNone(conv)
        self.assertEqual(conv.questions_asked, 1)
        first.bot.send_message.assert_not_called()

        second = make_message(1, "Бюджет $500, срок месяц")
        asyncio.run(on_text(second))

        self.assertEqual(len(ai.calls), 2)
        self.assertIn("Нужен бот для магазина", ai.calls[1])
        self.assertIn("Бюджет $500, срок месяц", ai.calls[1])
        self.assertIsNone(self.storage.get_conversation(1))
        second.bot.send_message.assert_called_once()
        notification = second.bot.send_message.call_args.args[1]
        self.assertIn("Бюджет $500, срок месяц", notification)

    def test_spam_auto_blacklist_and_no_delivery(self):
        dp = self.wire(FakeAIClient([valid_json(category="спам", ready=True)]))
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "КУПИТЕ ДИПЛОМ ДЕШЕВО")
        asyncio.run(on_text(msg))

        self.assertTrue(self.storage.is_blacklisted(1))
        msg.bot.send_message.assert_not_called()

        follow_up = make_message(1, "ну хоть что-нибудь")
        asyncio.run(on_text(follow_up))
        self.assertIn(render_unauthorized(), self.answers(follow_up))

    def test_ai_failure_still_notifies_owner(self):
        dp = self.wire(FailingAIClient())
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "текст при упавшем ИИ")
        asyncio.run(on_text(msg))

        self.assertEqual(self.storage.get_category_counts().get("непонятное"), 1)
        self.assertIn(render_ai_unavailable("ru"), self.answers(msg))
        msg.bot.send_message.assert_called_once()
        self.assertEqual(self.storage.get_unread(), [])

    def test_owner_text_is_ignored(self):
        dp = self.wire(FakeAIClient([]))
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(self.settings.owner_id, "заметка для себя")
        asyncio.run(on_text(msg))

        msg.answer.assert_not_called()
        self.assertEqual(self.storage.get_category_counts(), {})

    def test_cmd_new_delivers_and_marks_read(self):
        dp = self.wire(FakeAIClient([]))
        self.storage.ensure_user(1, "alice")
        self.storage.save_message(1, "текст заявки", "готовое ТЗ")
        cmd_new = self.get_handler(dp, "cmd_new")

        msg = make_message(self.settings.owner_id, "/new")
        asyncio.run(cmd_new(msg))

        output = "\n".join(self.answers(msg))
        self.assertIn("текст заявки", output)
        self.assertIn("@alice", output)
        self.assertEqual(self.storage.get_unread(), [])

    def test_cmd_new_empty(self):
        dp = self.wire(FakeAIClient([]))
        cmd_new = self.get_handler(dp, "cmd_new")

        msg = make_message(self.settings.owner_id, "/new")
        asyncio.run(cmd_new(msg))

        self.assertIn("Нет непрочитанных", self.answers(msg)[0])

    def test_blacklist_add_keeps_reason(self):
        dp = self.wire(FakeAIClient([]))
        cmd_blacklist = self.get_handler(dp, "cmd_blacklist")

        msg = make_message(self.settings.owner_id, "/blacklist add 777 спам и реклама")
        asyncio.run(cmd_blacklist(msg))

        self.assertEqual(self.storage.get_blacklist(), [(777, None, "спам и реклама")])
        self.assertIn("777", self.answers(msg)[0])

    def test_blacklist_requires_owner(self):
        dp = self.wire(FakeAIClient([]))
        cmd_blacklist = self.get_handler(dp, "cmd_blacklist")

        msg = make_message(1, "/blacklist list")
        asyncio.run(cmd_blacklist(msg))

        self.assertIn("владельцу", self.answers(msg)[0])

    def test_fast_track_phrase_skips_ai(self):
        dp = self.wire(FakeAIClient([]))  # any AI call would raise here
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "Заказ! Одностраничный сайт-визитка для кафе")
        asyncio.run(on_text(msg))

        self.assertEqual(self.storage.get_category_counts(), {"готовое ТЗ": 1})
        self.assertEqual(self.storage.get_unread(), [])
        msg.bot.send_message.assert_called_once()
        self.assertIn("Одностраничный сайт-визитка", msg.bot.send_message.call_args.args[1])
        self.assertIn("#готовое ТЗ", msg.bot.send_message.call_args.args[1])
        self.assertIn("получено", self.answers(msg)[-1])
        self.assertIsNone(self.storage.get_conversation(1))

    def test_fast_track_with_punctuated_word(self):
        dp = self.wire(FakeAIClient([]))
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "заказ: лендинг для кофейни")
        asyncio.run(on_text(msg))

        self.assertEqual(self.storage.get_category_counts(), {"готовое ТЗ": 1})

    def test_normal_message_with_word_inside_is_classified(self):
        ai = FakeAIClient([valid_json()])
        dp = self.wire(ai)
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "Хочу разместить заказ на лендинг")
        asyncio.run(on_text(msg))

        self.assertEqual(len(ai.calls), 1)
        self.assertEqual(self.storage.get_category_counts(), {"готовое ТЗ": 1})

    def test_fast_track_word_without_body_asks_for_description(self):
        dp = self.wire(FakeAIClient([]))
        on_text = self.get_handler(dp, "on_text")

        msg = make_message(1, "Заказ")
        asyncio.run(on_text(msg))

        self.assertEqual(self.storage.get_category_counts(), {})
        msg.bot.send_message.assert_not_called()
        self.assertIn("ЗАКАЗ", self.answers(msg)[0])

    def test_apply_command_delivers_directly(self):
        dp = self.wire(FakeAIClient([]))
        cmd_apply = self.get_handler(dp, "cmd_apply")

        msg = make_message(1, "/apply Нужен бот для записи клиентов")
        command = CommandObject(prefix="/", command="apply", args="Нужен бот для записи клиентов")
        asyncio.run(cmd_apply(msg, command))

        self.assertEqual(self.storage.get_category_counts(), {"готовое ТЗ": 1})
        msg.bot.send_message.assert_called_once()

    def test_apply_without_text_shows_usage(self):
        dp = self.wire(FakeAIClient([]))
        cmd_apply = self.get_handler(dp, "cmd_apply")

        msg = make_message(1, "/apply")
        command = CommandObject(prefix="/", command="apply", args=None)
        asyncio.run(cmd_apply(msg, command))

        self.assertEqual(self.storage.get_category_counts(), {})
        msg.bot.send_message.assert_not_called()
        self.assertIn("/apply", self.answers(msg)[0])

    def test_portfolio_command_shows_link(self):
        dp = self.wire(FakeAIClient([]))
        cmd_portfolio = self.get_handler(dp, "cmd_portfolio")

        msg = make_message(1, "/portfolio")
        asyncio.run(cmd_portfolio(msg))

        self.assertIn("t.me/quixoted", self.answers(msg)[0])


if __name__ == "__main__":
    unittest.main()
