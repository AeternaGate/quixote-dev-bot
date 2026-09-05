import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.quixote_bot.webapp import create_app


class WebAppTests(unittest.TestCase):
    """Light checks that never touch the Telegram API."""

    def setUp(self):
        # The app keeps its SQLite connection open, so on Windows the DB file
        # cannot be deleted; use a temp dir and clean up best-effort.
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "test.db")
        env = {
            "BOT_TOKEN": "test-token",
            "OWNER_ID": "999",
            "DB_PATH": self.db,
            "TELEGRAM_WEBHOOK_SECRET": "s3cret",
        }
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.client = create_app().test_client()

    def test_health_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("webhook endpoint", response.get_data(as_text=True))

    def test_webhook_rejects_wrong_secret(self):
        response = self.client.post(
            "/webhook/s3cret",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )
        self.assertEqual(response.status_code, 403)

    def test_webhook_rejects_invalid_body(self):
        response = self.client.post(
            "/webhook/s3cret",
            data="not json",
            content_type="application/json",
            headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_unknown_path_404(self):
        response = self.client.post(
            "/webhook/other-secret",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
