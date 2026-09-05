import unittest

from src.quixote_bot.messages import (
    SHORT_DESCRIPTIONS,
    render_blacklist_list,
    render_blacklist_result,
    render_broadcast_confirm,
    render_categories,
    render_confirmation,
    render_fast_track_notification,
    render_fast_track_usage,
    render_media_instruction,
    render_owner_notification,
    render_owner_only,
    render_portfolio,
    render_unauthorized,
    render_unread_item,
    render_welcome,
)
from src.quixote_bot.qualification import Analysis


class MessageTests(unittest.TestCase):
    def test_welcome_mentions_media_and_ai_ru(self):
        text = render_welcome("ru")
        self.assertIn("медиа", text)
        self.assertIn("ИИ", text)
        self.assertIn("ТЕКСТОВЫЕ", text)

    def test_welcome_mentions_media_and_ai_en(self):
        text = render_welcome("en")
        self.assertIn("media", text.lower())
        self.assertIn("AI", text)
        self.assertIn("TEXT", text)

    def test_media_instruction_ru(self):
        text = render_media_instruction("ru")
        self.assertIn("личку", text)

    def test_media_instruction_en(self):
        text = render_media_instruction("en")
        self.assertIn("personal chat", text.lower())

    def test_owner_notification_has_hashtag_and_username(self):
        analysis = Analysis(
            "готовое ТЗ", True, None, "Сайт", "срочно", "$500", "2 недели",
            ["нет макетов"], "Пришлите макеты.", "Спасибо!",
        )
        text = render_owner_notification(42, "client", "Нужен сайт", analysis, 0)
        self.assertIn("@client", text)
        self.assertIn("#готовое ТЗ", text)
        self.assertIn("Обращение клиента:", text)
        self.assertIn("Резюме:", text)
        self.assertIn("Срочность:", text)
        self.assertIn("Предварительный бюджет:", text)
        self.assertIn("Сроки:", text)
        self.assertIn("Риски:", text)
        self.assertIn("Рекомендуемый ответ:", text)

    def test_owner_notification_without_username(self):
        analysis = Analysis(
            "непонятное", True, None, "Резюме", "обычная", "null", "null",
            [], "Ответ", None,
        )
        text = render_owner_notification(99, None, "текст", analysis, 3)
        self.assertIn("99", text)
        self.assertIn("Задано вопросов: 3", text)

    def test_categories_stats(self):
        stats = {"спам": 5, "готовое ТЗ": 2}
        text = render_categories(stats)
        self.assertIn("#спам: 5", text)
        self.assertIn("#готовое ТЗ: 2", text)

    def test_categories_empty(self):
        text = render_categories({})
        self.assertIn("Пока нет", text)

    def test_unread_item_format(self):
        text = render_unread_item(1, 42, "alice", "Hello world", "потенциальный заказ")
        self.assertIn("[1]", text)
        self.assertIn("@alice", text)
        self.assertIn("#потенциальный заказ", text)
        self.assertIn("Hello world", text)

    def test_owner_only(self):
        text = render_owner_only()
        self.assertIn("владельцу", text)

    def test_unauthorized(self):
        text = render_unauthorized()
        self.assertIn("черном списке", text)

    def test_blacklist_add_success(self):
        text = render_blacklist_result("add", "123", True)
        self.assertIn("добавлен", text)

    def test_blacklist_remove_success(self):
        text = render_blacklist_result("remove", "123", True)
        self.assertIn("удален", text)

    def test_blacklist_list_empty(self):
        text = render_blacklist_list([])
        self.assertIn("пуст", text)

    def test_blacklist_list_with_entries(self):
        text = render_blacklist_list([(1, "spam1", "реклама")])
        self.assertIn("@spam1", text)
        self.assertIn("реклама", text)

    def test_broadcast_confirm(self):
        text = render_broadcast_confirm(10)
        self.assertIn("10", text)

    def test_confirmation_ru(self):
        text = render_confirmation("ru")
        self.assertIn("получено", text)

    def test_confirmation_en(self):
        text = render_confirmation("en")
        self.assertIn("received", text.lower())

    def test_welcome_ru_includes_checklist_and_fast_track(self):
        text = render_welcome("ru")
        self.assertIn("ЗАКАЗ", text)
        self.assertIn("/apply", text)
        self.assertIn("бюджет", text.lower())
        self.assertIn("Сроки", text)
        self.assertIn("технологиям", text.lower())
        self.assertIn("Материалы", text)
        self.assertIn("мск", text)

    def test_welcome_en_includes_checklist_and_fast_track(self):
        text = render_welcome("en")
        self.assertIn("ORDER", text)
        self.assertIn("/apply", text)
        self.assertIn("budget", text.lower())
        self.assertIn("Timeline", text)
        self.assertIn("MSK", text)

    def test_short_descriptions_fit_telegram_limit(self):
        for text in SHORT_DESCRIPTIONS.values():
            self.assertLessEqual(len(text), 120)

    def test_fast_track_notification_format(self):
        text = render_fast_track_notification(42, "client", "Нужен сайт-визитка")
        self.assertIn("@client", text)
        self.assertIn("#готовое ТЗ", text)
        self.assertIn("Нужен сайт-визитка", text)

    def test_fast_track_notification_truncates_long_text(self):
        text = render_fast_track_notification(42, None, "x" * 4000)
        self.assertLess(len(text), 3200)
        self.assertTrue(text.endswith("…"))

    def test_fast_track_usage(self):
        self.assertIn("ЗАКАЗ", render_fast_track_usage("ru"))
        self.assertIn("ORDER", render_fast_track_usage("en"))

    def test_portfolio_contains_link(self):
        for lang in ("ru", "en"):
            self.assertIn("t.me/quixoted", render_portfolio(lang))

    def test_welcome_mentions_portfolio(self):
        for lang in ("ru", "en"):
            self.assertIn("t.me/quixoted", render_welcome(lang))


if __name__ == "__main__":
    unittest.main()
