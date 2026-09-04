import json
from dataclasses import dataclass
from typing import Callable

from .messages import CATEGORIES, QUESTION_ORDER, QUALIFICATION_QUESTIONS


SYSTEM_PROMPT = """Ты — ассистент фрилансера Quixote.Dev. Твоя задача: классифицировать сообщение клиента, определить готовность проекта и кратко ответить клиенту.

Услуги фрилансера:
- Фуллстек-разработка (сайты, боты, приложения)
- Автоматизация с участием ИИ
- Минимальная стоимость: $10 за легкие правки
- Рабочие часы: 14:00-20:00 по Тбилиси
- Срочные проекты принимаются
- Сомнительные и незаконные заказы не принимаются

КATEGORIES: "готовое ТЗ", "потенциальный заказ", "вопрос по услуге", "уточнение по текущему заказу", "спам", "непонятное"

Отвечай ТОЛЬКО валидным JSON без markdown:
{
  "category": "одна из категорий выше",
  "ready": true/false,
  "question": null или "один короткий вопрос" если ready=false,
  "summary": "краткое резюме на русском",
  "urgency": "срочно/обычная/не горит",
  "budget": "предварительная оценка или null",
  "timeline": "предполагаемые сроки или null",
  "risks": ["список рисков"],
  "recommended_reply": "рекомендуемый ответ владельцу на русском",
  "client_reply": "короткий ответ клиенту на языке сообщения или null"
}

Правила для client_reply:
- "готовое ТЗ" → краткое подтверждение получения + что свяжутся soon
- "потенциальный заказ" → благодарность + что изучат задачу
- "вопрос по услуге" → краткий ответ на вопрос по услугам
- "уточнение по текущему заказу" → подтверждение получения
- "спам" → null (не отвечать)
- "непонятное" → null (без ответа)
- Если ready=false — client_reply может быть null, ответ придет после уточнений
- Отвечай на том же языке, что и сообщение клиента
- Максимум 2-3 предложения, деловой тон
- Не называй цену окончательно, только предварительно"""


@dataclass(frozen=True)
class Analysis:
    category: str
    ready: bool
    question: str | None
    summary: str
    urgency: str
    budget: str
    timeline: str
    risks: list[str]
    recommended_reply: str
    client_reply: str | None

    @classmethod
    def from_json(cls, raw: str) -> "Analysis":
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("AI result must be an object")
        if data.get("category") not in CATEGORIES:
            raise ValueError("unknown category")
        ready = data.get("ready")
        question = data.get("question")
        if not isinstance(ready, bool):
            raise ValueError("ready must be boolean")
        if not ready and not isinstance(question, str):
            raise ValueError("incomplete brief needs a question")
        if ready:
            question = None
        if not all(isinstance(data.get(key), str) for key in (
            "summary", "urgency", "budget", "timeline", "recommended_reply"
        )):
            raise ValueError("analysis text fields are required")
        if not isinstance(data.get("risks"), list) or not all(
            isinstance(item, str) for item in data["risks"]
        ):
            raise ValueError("risks must be a list of strings")
        client_reply = data.get("client_reply")
        if client_reply is not None and not isinstance(client_reply, str):
            client_reply = None
        return cls(
            category=data["category"], ready=ready, question=question,
            summary=data["summary"], urgency=data["urgency"],
            budget=data["budget"], timeline=data["timeline"],
            risks=data["risks"], recommended_reply=data["recommended_reply"],
            client_reply=client_reply,
        )


def analyze_with_retry(call: Callable[[], str]) -> Analysis:
    for attempt in range(2):
        try:
            return Analysis.from_json(call())
        except (ValueError, TypeError, json.JSONDecodeError):
            if attempt == 1:
                return Analysis(
                    category="непонятное", ready=True, question=None,
                    summary="ИИ не смог разобрать заявку.", urgency="обычная",
                    budget="не определен", timeline="не определены",
                    risks=["Требуется ручная проверка."],
                    recommended_reply="Спасибо, я изучу задачу и вернусь с ответом.",
                    client_reply=None,
                )
    raise AssertionError("unreachable")


def get_next_question(question_number: int, language: str = "ru") -> str | None:
    if question_number >= len(QUESTION_ORDER):
        return None
    key = QUESTION_ORDER[question_number]
    return QUALIFICATION_QUESTIONS[key][language]


def should_ask_question(analysis: Analysis, question_count: int) -> bool:
    return not analysis.ready and question_count < 5


def build_user_context(messages: list[str]) -> str:
    return "\n\n".join(f"Сообщение клиента {i+1}:\n{msg}" for i, msg in enumerate(messages))
