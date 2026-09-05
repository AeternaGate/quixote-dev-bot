import json
import urllib.error
import urllib.request
from typing import Any


class OpenRouterClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._key = api_key
        self._model = model
        self._url = "https://openrouter.ai/api/v1/chat/completions"

    def chat(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
            "max_tokens": 1500,
        }).encode()

        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
                "HTTP-Referer": "https://quixotedevbot.local",
                "X-Title": "Quixote.Dev Bot",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data: Any = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as e:
            raise OpenRouterError(str(e)) from e


class OpenRouterError(Exception):
    pass
