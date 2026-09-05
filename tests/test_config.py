import os
import unittest
from unittest.mock import patch

from src.quixote_bot.config import Settings


class ConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {"BOT_TOKEN": "tok", "OPENROUTER_API_KEY": "key", "OWNER_ID": "8278836846"})
    def test_from_env_success(self):
        s = Settings.from_env()
        self.assertEqual(s.bot_token, "tok")
        self.assertEqual(s.openrouter_api_key, "key")
        self.assertEqual(s.owner_id, 8278836846)
        self.assertEqual(s.rate_limit, 10)
        self.assertEqual(s.rate_window, 300)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_token_raises(self):
        with self.assertRaises(ValueError):
            Settings.from_env()

    @patch.dict(os.environ, {"BOT_TOKEN": "tok"}, clear=True)
    def test_missing_owner_raises(self):
        with self.assertRaises(ValueError):
            Settings.from_env()

    @patch.dict(os.environ, {"BOT_TOKEN": "tok", "OWNER_ID": "not-a-number"}, clear=True)
    def test_invalid_owner_raises(self):
        with self.assertRaises(ValueError):
            Settings.from_env()

    @patch.dict(os.environ, {"BOT_TOKEN": "tok", "OWNER_ID": "123"})
    def test_custom_owner(self):
        s = Settings.from_env()
        self.assertEqual(s.owner_id, 123)


if __name__ == "__main__":
    unittest.main()
