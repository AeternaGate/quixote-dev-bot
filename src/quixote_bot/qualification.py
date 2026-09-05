import json
from collections.abc import Callable
from dataclasses import dataclass

from .messages import CATEGORIES, QUALIFICATION_QUESTIONS, QUESTION_ORDER

# A conversation older than this is stale: the next message starts a new one.
CONVERSATION_TTL_SECONDS = 30 * 60

SYSTEM_PROMPT = """Ты — ассистент фрилансера Quixote.Dev.
Твоя задача: классифицировать сообщение клиента, определить готовность проекта и кратко ответить клиенту.

Услуги фрилансера:
- Фуллстек-разработка (сайты, боты, приложения)
- Автоматизация с участием ИИ
- Минимальная стоимость: $10 за легкие правки
- Рабочие часы: 14:00-20:00 по мск
- Срочные проекты принимаются
- Сомнительные и незаконные заказы не принимаются

Категории: "готовое ТЗ", "потенциальный заказ", "вопрос по услуге", "уточнение по текущему заказу", "спам", "непонятное"

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

Примеры классификации (сообщение → ключевые поля ответа):
1. "Хочу заказать лендинг" → category "потенциальный заказ", ready false,
   question "Расскажите подробнее: что за проект, какие страницы и функции нужны?",
   budget "не определен", client_reply "Спасибо за обращение! Уточните детали задачи."
2. "Одностраничный сайт с описанием кафе, меню с ценами и отзывами" →
   category "потенциальный заказ", ready false, question "Какой бюджет и сроки?",
   client_reply "Принял! Уточните бюджет и сроки."
3. "Нужен бот для записи клиентов, с базой и напоминаниями, бюджет $300" →
   category "готовое ТЗ", ready true, question null,
   client_reply "Спасибо, заявка принята! Скоро свяжусь."
4. "Привет" / "тест" → category "непонятное", ready true, question null, client_reply null
5. "Купите дешевые подписки, пишите в лс" → category "спам", ready true, question null, client_reply null

Любое описание конкретной работы (даже короткое) — это "потенциальный заказ" или "готовое ТЗ", но не "непонятное".

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


def _load_json_object(raw: str) -> dict:
    """Parse the AI reply, tolerating markdown fences or chatter around the JSON."""
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(raw[start:end + 1])
    return data


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
        data = _load_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError("AI result must be an object")
        if data.get("category") not in CATEGORIES:
            raise ValueError("unknown category")
        ready = data.get("ready")
        if not isinstance(ready, bool):
            raise ValueError("ready must be boolean")
        question = data.get("question")
        if not isinstance(question, str):
            # The AI-proposed question is informational only: the flow asks its
            # own canned questions, so a missing one must not sink the analysis.
            question = None
        if ready:
            question = None
        defaults = {
            "summary": "Без резюме",
            "urgency": "обычная",
            "budget": "не определен",
            "timeline": "не определены",
            "recommended_reply": "Изучу задачу и вернусь с ответом.",
        }
        fields = {}
        for key, default in defaults.items():
            value = data.get(key)
            fields[key] = value if isinstance(value, str) else (default if value is None else str(value))
        risks = data.get("risks")
        if not isinstance(risks, list) or not all(isinstance(item, str) for item in risks):
            risks = []
        client_reply = data.get("client_reply")
        if client_reply is not None and not isinstance(client_reply, str):
            client_reply = None
        return cls(
            category=data["category"], ready=ready, question=question,
            summary=fields["summary"], urgency=fields["urgency"],
            budget=fields["budget"], timeline=fields["timeline"],
            risks=risks, recommended_reply=fields["recommended_reply"],
            client_reply=client_reply,
        )


def fallback_analysis() -> Analysis:
    return Analysis(
        category="непонятное", ready=True, question=None,
        summary="ИИ не смог разобрать заявку.", urgency="обычная",
        budget="не определен", timeline="не определены",
        risks=["Требуется ручная проверка."],
        recommended_reply="Спасибо, я изучу задачу и вернусь с ответом.",
        client_reply=None,
    )


def analyze_with_retry(call: Callable[[], str]) -> Analysis:
    for attempt in range(2):
        try:
            return Analysis.from_json(call())
        except (ValueError, TypeError, json.JSONDecodeError):
            if attempt == 1:
                return fallback_analysis()
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


def serialize_context(messages: list[str]) -> str:
    return json.dumps(messages, ensure_ascii=False)


def parse_context(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        return []
    return data
