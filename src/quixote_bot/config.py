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
    webhook_secret: str = ""
    proxy_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "")
        owner = os.getenv("OWNER_ID", "")
        if not token:
            raise ValueError(
                "BOT_TOKEN is required. Set it in .env or environment variables."
            )
        if not owner.isdigit():
            raise ValueError(
                "OWNER_ID is required and must be a numeric Telegram user id. "
                "Set it in .env or environment variables."
            )
        db = os.getenv("DB_PATH", "data/bot.db")
        model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
        limit = int(os.getenv("RATE_LIMIT", "10"))
        window = int(os.getenv("RATE_WINDOW", "300"))
        return cls(
            bot_token=token,
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            owner_id=int(owner),
            db_path=db,
            openrouter_model=model,
            rate_limit=limit,
            rate_window=window,
            webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
            proxy_url=os.getenv("PROXY_URL", ""),
        )
