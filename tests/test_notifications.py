import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import ai
import storage
from notifications import (
    attention_kind, claims_delivery, has_hostile_language, has_profile_alert_keyword,
    should_stay_silent,
)


class IntentTests(unittest.IsolatedAsyncioTestCase):
    def test_common_requests_and_typos(self):
        for text, kind in [("Terzoq telefon qilgin", "call"), ("qo‘ng‘iroq qiling", "call"),
                           ("Позвони мне срочно", "call"), ("Please call me", "call"),
                           ("Shoshilinch masala bor", "urgent"), ("Bahodirni ogohlantir", "notify"),
                           ("ogohlantirdingmi?", "status"), ("Have you notified him?", "status")]:
            with self.subTest(text=text):
                self.assertEqual(attention_kind(text), kind)
        for text in ["Telefon raqami nima?", "Telefon qilma", "Do not call me", "не звони", "Salom",
                     "Telefon qilish nima?", "Я уже позвонил ему", "Telefon qilsam bo'ladimi?"]:
            with self.subTest(text=text):
                self.assertIsNone(attention_kind(text))

    def test_old_false_claims_are_blocked(self):
        for text in ["Uni ogohlantirib qo'ydim", "Yozib qo‘yaman", "I have notified him",
                     "Я уже уведомил Баходира", "I will pass your message along"]:
            self.assertTrue(claims_delivery(text))
        self.assertFalse(claims_delivery("Qaysi loyiha haqida gaplashmoqchisiz?"))

    def test_greeting_and_check_in_are_not_suppressed_but_acknowledgements_are(self):
        for text in ["Salom", "Qandaysan", "Nima gap?", "Как дела", "Hello", "Savol"]:
            with self.subTest(text=text):
                self.assertFalse(should_stay_silent(text))
        for text in ["ha", "haa", "rahmat", "👍"]:
            with self.subTest(text=text):
                self.assertTrue(should_stay_silent(text))

    def test_personal_alert_words_and_conflict_signal_are_local_and_explicit(self):
        profile = {"alert_keywords": "hisobot, uchrashuv\nto'lov"}
        self.assertTrue(has_profile_alert_keyword("Hisobot tayyormi?", profile))
        self.assertTrue(has_profile_alert_keyword("Uchrashuvni ko'chiraylik", profile))
        self.assertFalse(has_profile_alert_keyword("Hisobotchilik mavzusi", profile))
        self.assertFalse(has_profile_alert_keyword("Oddiy hol so'rash", profile))
        self.assertTrue(has_hostile_language("Sen ahmoqsan"))
        self.assertFalse(has_hostile_language("Bu juda yomon vaziyat"))

    async def test_model_plan_validates_schema_and_preserves_current_user_text(self):
        with patch.object(ai, "complete_text", new=AsyncMock(return_value='{"attention":"call","action":"silent","reply":""}')) as complete:
            plan = await ai.plan_business_reply("Llámame pronto", [], profile={"address": "sen"})
        self.assertEqual(plan.attention, "call")
        self.assertEqual(complete.call_args.args[1][-1]["content"], "Llámame pronto")
        for result in [[], {"attention": "send_money", "action": "reply", "reply": "ok"},
                       {"attention": "none", "action": "reply", "reply": ""},
                       {"attention": "none", "action": "silent", "reply": ""},
                       {"attention": "none", "action": "reply", "reply": 123}]:
            with patch.object(ai, "complete_text", new=AsyncMock(return_value=json.dumps(result))):
                with self.assertRaises(ValueError):
                    await ai.plan_business_reply("Salom", [], profile={})


class AlertStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(storage, "DATABASE_PATH", Path(self.temp.name) / "bot.sqlite3")
        self.patch.start()
        storage.initialize()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_deduplication_survives_restart_and_is_scoped(self):
        row, created = storage.reserve_alert(999, "a", 123, 10, 123, "call")
        self.assertTrue(created)
        storage.finish_alert(row["id"], "sent", 55)
        storage.initialize()
        repeated, created = storage.reserve_alert(999, "a", 123, 10, 123, "call")
        self.assertFalse(created)
        self.assertEqual((repeated["status"], repeated["admin_message_id"]), ("sent", 55))
        self.assertTrue(storage.reserve_alert(999, "a", 123, 11, 123, "call")[1])
        self.assertTrue(storage.reserve_alert(888, "a", 123, 10, 123, "call")[1])
        self.assertEqual(len(storage.recent_alerts(999)), 2)
        self.assertEqual(len(storage.recent_alerts(888)), 1)
        self.assertIsNone(storage.latest_alert(999, 456))
