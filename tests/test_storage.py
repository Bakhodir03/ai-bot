import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "bot.sqlite3"
        self.patcher = patch.object(storage, "DATABASE_PATH", self.path)
        self.patcher.start()
        storage.initialize()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_business_history_is_scoped_and_bounded(self):
        storage.save_business_message("a", 123, "user", "personal question")
        storage.save_business_message("a", 123, "assistant", "personal answer")
        storage.save_business_message("b", 123, "user", "other connection")
        self.assertEqual(storage.get_business_history("a", 123)[0]["content"], "personal question")
        self.assertEqual(storage.get_business_history("b", 123)[0]["content"], "other connection")
        self.assertEqual(storage.get_business_history("a", 456), [])

        for i in range(20):
            storage.save_business_message("a", 123, "user", f"Q{i}")
        history = storage.get_business_history("a", 123)
        self.assertEqual(len(history), 8)
        self.assertEqual(history[0]["content"], "Q12")
        with self.assertRaises(ValueError):
            storage.save_business_message("a", 123, "owner", "bad role")

    def test_human_control_can_be_extended_resumed_and_survives_restart(self):
        self.assertTrue(storage.activate_human_control(999, 123, 10, 2_000))
        self.assertTrue(storage.human_control_active(999, 123, 1_999))
        self.assertFalse(storage.activate_human_control(999, 123, 11, 2_100))
        storage.initialize()
        self.assertTrue(storage.human_control_active(999, 123, 2_099))
        storage.resume_ai(999, 123)
        self.assertFalse(storage.human_control_active(999, 123, 1))

    def test_daily_greeting_and_profiles_are_owner_scoped(self):
        storage.mark_daily_greeting("a", 123, "2026-10-25")
        self.assertTrue(storage.has_daily_greeting("a", 123, "2026-10-25"))
        self.assertFalse(storage.has_daily_greeting("a", 123, "2026-10-26"))
        self.assertFalse(storage.has_daily_greeting("b", 123, "2026-10-25"))

        storage.remember_contact(999, 123, "Old name", "old_username")
        storage.remember_contact(888, 123, "Other owner")
        storage.update_contact(999, 123, "tone", "formal")
        storage.update_contact(999, 123, "reply_mode", "manual")
        storage.remember_contact(999, 123, "New name", "")
        profile = storage.get_contact(999, 123)
        self.assertEqual((profile["tone"], profile["reply_mode"], profile["name"]),
                         ("formal", "manual", "New name"))
        self.assertEqual(storage.get_contact(888, 123)["tone"], "polite")

    def test_profile_rejects_unknown_values(self):
        storage.remember_contact(999, 123)
        for field, value in [("name", "malicious"), ("tone", "invented"),
                             ("template", "x" * 2001), ("tone=?; DROP TABLE x;--", "x")]:
            with self.assertRaises(ValueError):
                storage.update_contact(999, 123, field, value)
        storage.update_contact(999, 123, "template", "First line\nSecond line")
        self.assertEqual(storage.get_contact(999, 123)["template"], "First line\nSecond line")

    def test_retention_removes_old_content_but_keeps_contact_profile(self):
        storage.remember_contact(999, 123, "Saved contact")
        storage.save_business_message("connection", 123, "user", "Old message")
        row, _ = storage.reserve_alert(999, "connection", 123, 44, 123, "urgent")
        storage.finish_alert(row["id"], "sent", 55)
        storage.mark_daily_greeting("connection", 123, "2020-01-01")
        with storage.connect() as db:
            db.execute("UPDATE business_messages SET created_at=datetime('now', '-61 days')")
            db.execute("UPDATE owner_alerts SET created_at=datetime('now', '-61 days')")
        storage.purge_expired_data(60)
        self.assertEqual(storage.get_business_history("connection", 123), [])
        self.assertEqual(storage.recent_alerts(999), [])
        self.assertIsNotNone(storage.get_contact(999, 123))

    def test_service_health_notifies_after_three_failures_then_resets_on_success(self):
        self.assertFalse(storage.record_service_failure("ai", 1_000))
        self.assertFalse(storage.record_service_failure("ai", 1_001))
        self.assertTrue(storage.record_service_failure("ai", 1_002))
        self.assertFalse(storage.record_service_failure("ai", 1_003))
        storage.record_service_success("ai")
        self.assertFalse(storage.record_service_failure("ai", 2_000))


if __name__ == "__main__":
    unittest.main()
