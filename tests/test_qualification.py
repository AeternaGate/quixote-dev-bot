import json
import unittest

from src.quixote_bot.messages import QUALIFICATION_QUESTIONS, QUESTION_ORDER
from src.quixote_bot.qualification import (
    SYSTEM_PROMPT,
    Analysis,
    analyze_with_retry,
    build_user_context,
    get_next_question,
    should_ask_question,
)


def make_result(**changes):
    value = {
        "category": "потенциальный заказ", "ready": False,
        "question": "Какой бюджет?", "summary": "Автоматизация",
        "urgency": "обычная", "budget": "предварительно не определен",
        "timeline": "не определены", "risks": [],
        "recommended_reply": "Уточню детали.",
        "client_reply": "Спасибо за обращение!",
    }
    value.update(changes)
    return json.dumps(value)


class QualificationTests(unittest.TestCase):
    def test_ready_brief_skips_questions(self):
        analysis = Analysis.from_json(make_result(ready=True, question=None))
        self.assertFalse(should_ask_question(analysis, 0))
        self.assertFalse(should_ask_question(analysis, 4))

    def test_incomplete_brief_asks_questions(self):
        analysis = Analysis.from_json(make_result())
        self.assertTrue(should_ask_question(analysis, 0))
        self.assertTrue(should_ask_question(analysis, 4))

    def test_incomplete_brief_stops_at_five(self):
        analysis = Analysis.from_json(make_result())
        self.assertFalse(should_ask_question(analysis, 5))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            Analysis.from_json(make_result(category="other"))

    def test_invalid_json_retries_once_then_fallback(self):
        calls = 0

        def broken():
            nonlocal calls
            calls += 1
            return "not json"

        analysis = analyze_with_retry(broken)
        self.assertEqual(calls, 2)
        self.assertEqual(analysis.category, "непонятное")

    def test_valid_json_with_wrong_category_retries(self):
        calls = 0

        def bad_category():
            nonlocal calls
            calls += 1
            if calls == 1:
                return make_result(category="wrong")
            return make_result(category="спам", ready=True, question=None)

        analysis = analyze_with_retry(bad_category)
        self.assertEqual(analysis.category, "спам")

    def test_get_next_question_returns_by_order(self):
        q0 = get_next_question(0, "ru")
        self.assertEqual(q0, QUALIFICATION_QUESTIONS[QUESTION_ORDER[0]]["ru"])
        q4 = get_next_question(4, "ru")
        self.assertEqual(q4, QUALIFICATION_QUESTIONS[QUESTION_ORDER[4]]["ru"])

    def test_get_next_question_returns_none_at_limit(self):
        q5 = get_next_question(5, "ru")
        self.assertIsNone(q5)

    def test_get_next_question_english(self):
        q = get_next_question(0, "en")
        self.assertIn("detail", q.lower())

    def test_build_user_context(self):
        ctx = build_user_context(["Hello", "World"])
        self.assertIn("Сообщение клиента 1", ctx)
        self.assertIn("Сообщение клиента 2", ctx)
        self.assertIn("Hello", ctx)
        self.assertIn("World", ctx)

    def test_system_prompt_contains_categories(self):
        for cat in ("готовое ТЗ", "потенциальный заказ", "спам"):
            self.assertIn(cat, SYSTEM_PROMPT)

    def test_system_prompt_contains_few_shot_examples(self):
        self.assertIn("Примеры классификации", SYSTEM_PROMPT)
        self.assertIn("Хочу заказать лендинг", SYSTEM_PROMPT)

    def test_from_json_tolerates_markdown_fence(self):
        analysis = Analysis.from_json("```json\n" + make_result() + "\n```")
        self.assertEqual(analysis.category, "потенциальный заказ")

    def test_from_json_tolerates_surrounding_text(self):
        analysis = Analysis.from_json("Вот анализ заявки:\n" + make_result() + "\nНадеюсь, помог.")
        self.assertEqual(analysis.category, "потенциальный заказ")

    def test_from_json_tolerates_null_fields(self):
        raw = json.dumps({
            "category": "потенциальный заказ", "ready": False, "question": None,
            "summary": None, "urgency": None, "budget": None, "timeline": None,
            "risks": None, "recommended_reply": None, "client_reply": None,
        })
        analysis = Analysis.from_json(raw)
        self.assertEqual(analysis.category, "потенциальный заказ")
        self.assertEqual(analysis.budget, "не определен")
        self.assertEqual(analysis.risks, [])

    def test_client_reply_parsed(self):
        analysis = Analysis.from_json(make_result(client_reply="Привет!"))
        self.assertEqual(analysis.client_reply, "Привет!")

    def test_client_reply_none(self):
        analysis = Analysis.from_json(make_result(client_reply=None))
        self.assertIsNone(analysis.client_reply)

    def test_client_reply_wrong_type_becomes_none(self):
        analysis = Analysis.from_json(make_result(client_reply=123))
        self.assertIsNone(analysis.client_reply)


if __name__ == "__main__":
    unittest.main()
