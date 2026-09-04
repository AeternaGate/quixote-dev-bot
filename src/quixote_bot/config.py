import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    openrouter_api_key: str
    owner_id: int
    db_path: str
    openrouter_model: str
    rate_limit: int
    rate_window: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "")
        key = os.getenv("OPENROUTER_API_KEY", "")
        owner = os.getenv("OWNER_ID", "8278836846")
        db = os.getenv("DB_PATH", "data/bot.db")
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        limit = os.getenv("RATE_LIMIT", "10")
        window = os.getenv("RATE_WINDOW", "300")
        return cls(
            bot_token=token,
            openrouter_api_key=key,
            owner_id=int(owner),
            db_path=db,
            openrouter_model=model,
            rate_limit=int(limit),
            rate_window=int(window),
        )
