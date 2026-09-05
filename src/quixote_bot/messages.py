CATEGORIES = {
    "готовое ТЗ",
    "потенциальный заказ",
    "вопрос по услуге",
    "уточнение по текущему заказу",
    "спам",
    "непонятное",
}

LANG_OPTIONS = {
    "ru": "Выберите язык общения:\n\nChoose your language:",
    "en": "Choose your language:\n\nВыберите язык общения:",
}

LANG_BUTTONS = {"ru": "Русский", "en": "English"}

# First words (case-insensitive, punctuation ignored) that send the rest of the
# message straight to the owner as a ready application, skipping AI and questions.
FAST_TRACK_WORDS = {"заказ", "order"}

PORTFOLIO_URL = "https://t.me/quixoted"

SHORT_DESCRIPTIONS = {
    "ru": (
        "Quixote.Dev — сайты, боты, автоматизация с ИИ. "
        "Портфолио: t.me/quixoted. Заявка: слово ЗАКАЗ."
    ),
    "en": (
        "Quixote.Dev — websites, bots, AI automation. "
        "Portfolio: t.me/quixoted. Fast application: word ORDER."
    ),
}

QUALIFICATION_QUESTIONS = {
    "budget": {
        "ru": "Какой бюджет проекта? Укажите примерную сумму или диапазон.",
        "en": "What is the project budget? Please specify an approximate amount or range.",
    },
    "deadline": {
        "ru": "Какие сроки реализации? Когда нужно сдать проект?",
        "en": "What is the implementation timeline? When do you need the project delivered?",
    },
    "scope": {
        "ru": "Опишите задачу подробнее: какие функции, страницы или компоненты нужны?",
        "en": "Describe the task in more detail: what functions, pages, or components do you need?",
    },
    "technologies": {
        "ru": "Есть ли предпочтения по технологиям или платформе? (например, React, Telegram Bot, сайт)",
        "en": "Do you have technology or platform preferences? (e.g., React, Telegram Bot, website)",
    },
    "materials": {
        "ru": "Если есть макеты, документы или примеры — отправьте их мне в личку при личном обсуждении.",
        "en": "If you have mockups, documents or examples — send them to me in a personal chat during our discussion.",
    },
}

QUESTION_ORDER = ["scope", "budget", "deadline", "technologies", "materials"]


def render_welcome(language: str) -> str:
    if language == "en":
        return (
            "Welcome to Quixote.Dev!\n\n"
            "I do full-stack development and AI-powered automation.\n"
            "Minimum order — $10, working hours 14:00–20:00 MSK, urgent projects accepted.\n\n"
            "To get a faster answer, include in your first message:\n"
            "1. What needs to be done: task, features, pages\n"
            "2. Approximate budget\n"
            "3. Timeline\n"
            "4. Technology or platform preferences\n"
            "5. Materials, if any (mockups, documents, examples)\n\n"
            "Fast track: start your message with ORDER (or send /apply <text>) — "
            "it goes straight to me, with no questions and no AI wait.\n\n"
            "Important:\n"
            "- Only TEXT messages are accepted.\n"
            "- Files, photos, voice messages and other media — later in personal chat.\n\n"
            f"Portfolio and case studies: {PORTFOLIO_URL}\n\n"
            "Send your project description:"
        )
    return (
        "Добро пожаловать в Quixote.Dev!\n\n"
        "Помогаю с фуллстек-разработкой и автоматизациями с участием ИИ.\n"
        "Минимальный заказ — $10, работаю 14:00–20:00 по мск, срочные проекты — можно.\n\n"
        "Чтобы получить ответ быстрее, сразу включите в сообщение:\n"
        "1. Что нужно сделать: задача, функции, страницы\n"
        "2. Примерный бюджет\n"
        "3. Сроки\n"
        "4. Предпочтения по технологиям или платформе\n"
        "5. Материалы, если есть (макеты, документы, примеры)\n\n"
        "Быстрая заявка: начните сообщение со слова ЗАКАЗ (или отправьте /apply <текст>) — "
        "она уйдёт напрямую, без вопросов и ожидания ИИ.\n\n"
        "Важно:\n"
        "- Принимаются только ТЕКСТОВЫЕ сообщения.\n"
        "- Файлы, фото, голосовые и другие медиа — позже, в личной переписке.\n\n"
        f"Портфолио и примеры работ: {PORTFOLIO_URL}\n\n"
        "Отправьте описание проекта:"
    )


def render_media_instruction(language: str) -> str:
    if language == "en":
        return (
            "I accept only text messages. "
            "Please send files, photos, voice messages and other media "
            "directly in personal chat during our discussion."
        )
    return (
        "Я принимаю только текстовые сообщения. "
        "Файлы, фото, голосовые и другие медиа "
        "отправляйте в личку при личном обсуждении."
    )


def render_portfolio(language: str) -> str:
    if language == "en":
        return f"Quixote.Dev portfolio and case studies:\n{PORTFOLIO_URL}"
    return f"Портфолио и примеры работ Quixote.Dev:\n{PORTFOLIO_URL}"


def render_processing(language: str) -> str:
    if language == "en":
        return "Processing your message..."
    return "Обрабатываю ваше сообщение..."


def render_rate_limit(language: str) -> str:
    if language == "en":
        return "You are sending messages too quickly. Please wait a moment and try again."
    return "Слишком много сообщений подряд. Подождите немного и попробуйте снова."


def render_confirmation(language: str) -> str:
    if language == "en":
        return (
            "Thank you! Your message has been received and forwarded for review. "
            "You will be contacted shortly."
        )
    return (
        "Спасибо! Ваше сообщение получено и переслано на рассмотрение. "
        "С вами свяжутся в ближайшее время."
    )


def render_max_questions(language: str) -> str:
    if language == "en":
        return (
            "Thank you for the details. Your message has been forwarded for review. "
            "You will be contacted shortly."
        )
    return (
        "Спасибо за подробности. Ваше сообщение переслано на рассмотрение. "
        "С вами свяжутся в ближайшее время."
    )


def render_owner_notification(
    user_id: int,
    username: str | None,
    source: str,
    analysis,
    questions_asked: int,
) -> str:
    client = f"@{username}" if username else str(user_id)
    category_tag = f"#{analysis.category}"
    if len(source) > 3000:
        source = source[:3000] + "…"
    risks = "\n".join(f"  - {r}" for r in analysis.risks) if analysis.risks else "  нет"
    questions_line = f"Задано вопросов: {questions_asked}" if questions_asked else ""

    lines = [
        f"Новая заявка от {client} (ID: {user_id})",
        f"Категория: {category_tag}",
        "",
        f"Обращение клиента:\n{source}",
        "",
        f"Резюме: {analysis.summary}",
        f"Срочность: {analysis.urgency}",
        f"Предварительный бюджет: {analysis.budget}",
        f"Сроки: {analysis.timeline}",
        f"Риски:\n{risks}",
        f"Рекомендуемый ответ:\n{analysis.recommended_reply}",
    ]
    if analysis.question:
        lines.append(f"Вопрос от ИИ: {analysis.question}")
    if questions_line:
        lines.append("")
        lines.append(questions_line)
    return "\n".join(lines)


def render_fast_track_notification(user_id: int, username: str | None, source: str) -> str:
    client = f"@{username}" if username else str(user_id)
    if len(source) > 3000:
        source = source[:3000] + "…"
    return (
        f"Быстрая заявка от {client} (ID: {user_id})\n"
        f"Категория: #готовое ТЗ\n\n"
        f"Текст:\n{source}"
    )


def render_fast_track_usage(language: str) -> str:
    if language == "en":
        return "Add your application text after ORDER (or use /apply <text>)."
    return "Добавьте описание заявки после слова ЗАКАЗ (или /apply <текст>)."


def render_unread_header(count: int) -> str:
    return f"Непрочитанные сообщения ({count}):"


def render_unread_item(msg_id: int, user_id: int, username: str | None, text: str, category: str | None) -> str:
    client = f"@{username}" if username else str(user_id)
    tag = f" #{category}" if category else ""
    preview = text[:200] + ("..." if len(text) > 200 else "")
    return f"[{msg_id}] {client}{tag}\n{preview}"


def render_categories(stats: dict[str, int]) -> str:
    if not stats:
        return "Пока нет сообщений."
    lines = ["Статистика по категориям:"]
    for cat, cnt in stats.items():
        lines.append(f"  #{cat}: {cnt}")
    return "\n".join(lines)


def render_broadcast_confirm(count: int) -> str:
    return f"Сообщение отправлено {count} пользователям."


def render_blacklist_result(action: str, target: str, success: bool) -> str:
    if action == "add":
        if success:
            return f"Пользователь {target} добавлен в черный список."
        return f"Пользователь {target} уже в черном списке."
    if action == "remove":
        if success:
            return f"Пользователь {target} удален из черного списка."
        return f"Пользователь {target} не найден в черном списке."
    return "Неизвестная команда."


def render_blacklist_list(entries: list[tuple[int, str, str]]) -> str:
    if not entries:
        return "Черный список пуст."
    lines = ["Черный список:"]
    for uid, uname, reason in entries:
        name = f"@{uname}" if uname else str(uid)
        lines.append(f"  {name} — {reason or 'без причины'}")
    return "\n".join(lines)


def render_owner_only() -> str:
    return "Эта команда доступна только владельцу бота."


def render_error(language: str) -> str:
    if language == "en":
        return "An error occurred while processing. Please try again later."
    return "Произошла ошибка при обработке. Попробуйте позже."


def render_unauthorized() -> str:
    return "Доступ запрещен. Вы находитесь в черном списке."


def render_ai_unavailable(language: str) -> str:
    if language == "en":
        return "Temporary technical issue. Your message has been forwarded for manual review."
    return "Временная техническая проблема. Ваше сообщение переслано на ручную проверку."
