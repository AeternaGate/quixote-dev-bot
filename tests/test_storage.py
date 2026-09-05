import os
import tempfile
import unittest

from src.quixote_bot.storage import Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.mktemp(suffix=".db")
        self.storage = Storage(self.db)

    def tearDown(self):
        self.storage.close()
        os.unlink(self.db)

    def test_ensure_user(self):
        self.storage.ensure_user(1, "alice")
        user = self.storage.get_user(1)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.language, "ru")

    def test_set_language(self):
        self.storage.ensure_user(1, "alice")
        self.storage.set_language(1, "en")
        user = self.storage.get_user(1)
        self.assertEqual(user.language, "en")

    def test_blacklist(self):
        self.storage.ensure_user(1, "spam1")
        self.assertFalse(self.storage.is_blacklisted(1))
        self.storage.set_blacklisted(1, "spam")
        self.assertTrue(self.storage.is_blacklisted(1))
        self.storage.remove_blacklisted(1)
        self.assertFalse(self.storage.is_blacklisted(1))

    def test_blacklist_add_remove(self):
        self.assertTrue(self.storage.blacklist_add(999, "test"))
        self.assertTrue(self.storage.is_blacklisted(999))
        self.assertFalse(self.storage.blacklist_add(999, "dup"))
        self.assertTrue(self.storage.blacklist_remove(999))
        self.assertFalse(self.storage.is_blacklisted(999))

    def test_conversation_lifecycle(self):
        self.storage.ensure_user(1, None)
        self.storage.upsert_conversation(1, "asking", 1)
        conv = self.storage.get_conversation(1)
        self.assertEqual(conv.step, "asking")
        self.assertEqual(conv.questions_asked, 1)
        self.storage.clear_conversation(1)
        self.assertIsNone(self.storage.get_conversation(1))

    def test_save_message_and_unread(self):
        self.storage.ensure_user(1, None)
        self.storage.save_message(1, "hello")
        unread = self.storage.get_unread()
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0].text, "hello")
        self.storage.mark_read(1)
        self.assertEqual(len(self.storage.get_unread()), 0)

    def test_category_counts(self):
        for uid in (1, 2, 3):
            self.storage.ensure_user(uid, None)
        self.storage.save_message(1, "msg1", "спам")
        self.storage.save_message(2, "msg2", "спам")
        self.storage.save_message(3, "msg3", "готовое ТЗ")
        counts = self.storage.get_category_counts()
        self.assertEqual(counts["спам"], 2)
        self.assertEqual(counts["готовое ТЗ"], 1)

    def test_rate_limit(self):
        self.storage.ensure_user(1, None)
        for _ in range(9):
            self.storage.save_message(1, "msg")
        self.assertTrue(self.storage.check_rate_limit(1, 10, 300))
        self.storage.save_message(1, "msg")
        self.assertFalse(self.storage.check_rate_limit(1, 10, 300))


if __name__ == "__main__":
    unittest.main()
