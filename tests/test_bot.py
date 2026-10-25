import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from telegram.error import Conflict

import bot
import storage
from ai import ReplyPlan
from localization import pack


class BusinessReplyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db_patch = patch.object(storage, "DATABASE_PATH", Path(temp.name) / "bot.sqlite3")
        db_patch.start()
        self.addCleanup(db_patch.stop)
        storage.initialize()
        bot._requests.clear()
        self.texts = patch.object(bot, "business_texts", new=AsyncMock(return_value=pack("uz", False)))
        self.texts.start()
        self.addCleanup(self.texts.stop)
        self.welcome = patch.object(bot, "has_daily_greeting", return_value=True)
        self.welcome.start()
        self.addCleanup(self.welcome.stop)
        self.context = SimpleNamespace(bot=SimpleNamespace(
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=900)),
            send_sticker=AsyncMock(),
            get_business_connection=AsyncMock(return_value=SimpleNamespace(
                user=SimpleNamespace(id=999), is_enabled=True,
                rights=SimpleNamespace(can_reply=True),
            )),
        ))

    @staticmethod
    def business_update(*, sender=123, chat_id=123, text="Ish vaqti qachon?", sender_bot=None, date=None):
        return SimpleNamespace(business_message=SimpleNamespace(
            business_connection_id="connection-a", chat_id=chat_id, message_id=10,
            chat=SimpleNamespace(type="private"), text=text, caption=None,
            date=date,
            from_user=SimpleNamespace(id=sender, is_bot=False, full_name="Test person",
                                      username="testperson", language_code="uz"),
            sender_business_bot=sender_bot,
        ))

    async def test_substantive_message_gets_planned_reply(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock(
                    return_value=ReplyPlan("none", "reply", "Ish vaqti 9:00 dan 18:00 gacha."))) as plan:
            await bot.handle_business_message(self.business_update(), self.context)
        plan.assert_awaited_once()
        self.context.bot.send_message.assert_awaited_once_with(
            chat_id=123, text="Ish vaqti 9:00 dan 18:00 gacha.",
            business_connection_id="connection-a",
        )

    async def test_first_message_of_day_gets_greeting_and_ai_identity_before_answer(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "has_daily_greeting", return_value=False), \
                patch.object(bot, "mark_daily_greeting") as mark, \
                patch.object(bot, "plan_business_reply", new=AsyncMock(
                    return_value=ReplyPlan("none", "reply", "Savolingizga javob."))):
            await bot.handle_business_message(self.business_update(), self.context)
        self.assertEqual([call.kwargs["text"] for call in self.context.bot.send_message.call_args_list], [
            pack("uz")["greeting"], pack("uz")["intro"], "Savolingizga javob.",
        ])
        mark.assert_called_once_with("connection-a", 123, bot.tashkent_day())

    async def test_greeting_reintroduces_ai_without_an_extra_ai_reply(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="Salom"), self.context)
        self.assertEqual([call.kwargs["text"] for call in self.context.bot.send_message.call_args_list], [
            pack("uz")["greeting"], pack("uz")["intro"],
        ])
        plan.assert_not_awaited()

    async def test_casual_and_long_messages_do_not_reply(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="haa"), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()

    async def test_stale_update_never_restarts_an_old_conversation(self):
        old = datetime.now(timezone.utc) - timedelta(seconds=bot.MAX_AUTO_REPLY_AGE_SECONDS + 1)
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(date=old), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()

    async def test_conflict_notify_alerts_owner_without_replying_to_sender(self):
        storage.remember_contact(999, 123, "Test")
        storage.update_contact(999, 123, "conflict_mode", "notify")
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="Sen ahmoqsan"), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_awaited_once()
        self.assertEqual(self.context.bot.send_message.call_args.kwargs["chat_id"], 999)

        self.context.bot.send_message.reset_mock()
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="x" * 2001), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()

    async def test_owner_message_pauses_ai_and_second_message_extends_without_duplicate_notice(self):
        owner_update = self.business_update(sender=999, chat_id=123, text="O'zim javob beraman")
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999):
            await bot.handle_business_message(owner_update, self.context)
            await bot.handle_business_message(owner_update, self.context)
        self.assertEqual(self.context.bot.send_message.await_count, 1)
        self.assertEqual(self.context.bot.send_message.call_args.kwargs["chat_id"], 999)
        self.assertTrue(storage.human_control_active(999, 123, 1))
        self.context.bot.send_message.reset_mock()
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="Yana bir savolim bor"), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()

    async def test_resume_command_restores_ai_reply(self):
        storage.activate_human_control(999, 123, 10, 2_000_000_000)
        command_message = SimpleNamespace(reply_text=AsyncMock(), text="/resume 123")
        update = SimpleNamespace(effective_user=SimpleNamespace(id=999), message=command_message)
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999):
            await bot.resume_command(update, SimpleNamespace(args=[]))
        self.assertFalse(storage.human_control_active(999, 123, 1))
        command_message.reply_text.assert_awaited_once()
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock(
                    return_value=ReplyPlan("none", "reply", "AI yana ishlayapti."))):
            await bot.handle_business_message(self.business_update(), self.context)
        self.context.bot.send_message.assert_awaited_once()

    async def test_important_message_alerts_owner_during_human_control_but_never_replies_to_sender(self):
        storage.activate_human_control(999, 123, 10, 2_000_000_000)
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="Menga 500ming qarz kerak"), self.context)
        plan.assert_not_awaited()
        self.context.bot.send_message.assert_awaited_once()
        self.assertEqual(self.context.bot.send_message.call_args.kwargs["chat_id"], 999)
        self.assertNotIn("business_connection_id", self.context.bot.send_message.call_args.kwargs)

    async def test_call_request_alerts_then_reports_real_delivery_result(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock()) as plan:
            await bot.handle_business_message(self.business_update(text="Tezroq telefon qilgin"), self.context)
        plan.assert_not_awaited()
        calls = self.context.bot.send_message.call_args_list
        self.assertEqual([call.kwargs["chat_id"] for call in calls], [999, 123])
        self.assertIn("yuborildi", calls[-1].kwargs["text"])
        self.assertEqual(storage.latest_alert(999, 123)["status"], "sent")

    async def test_model_detected_notification_is_real_and_unbacked_claim_is_blocked(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock(
                    return_value=ReplyPlan("notify", "silent", ""))), \
                patch.object(bot, "delivery_reply", new=AsyncMock(return_value="Bildirishnoma yuborildi.")):
            await bot.handle_business_message(self.business_update(text="Loyiha haqida aytib qo'ying"), self.context)
        self.assertEqual(self.context.bot.send_message.await_count, 2)

        self.context.bot.send_message.reset_mock()
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999), \
                patch.object(bot, "plan_business_reply", new=AsyncMock(
                    return_value=ReplyPlan("none", "reply", "Uni ogohlantirib qo'ydim"))), \
                patch.object(bot, "delivery_reply", new=AsyncMock(return_value="Xabar yuborilmagan.")):
            await bot.handle_business_message(self.business_update(text="Oddiy ma'lumot"), self.context)
        self.assertIn("yuborilmagan", self.context.bot.send_message.call_args.kwargs["text"])

    async def test_owner_bot_and_unauthorized_connections_do_not_change_state(self):
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999):
            await bot.handle_business_message(self.business_update(sender=999, sender_bot=object()), self.context)
        self.context.bot.get_business_connection.assert_not_awaited()
        self.assertFalse(storage.human_control_active(999, 123, 1))

        self.context.bot.get_business_connection.reset_mock()
        self.context.bot.get_business_connection.return_value = SimpleNamespace(
            user=SimpleNamespace(id=888), is_enabled=True, rights=SimpleNamespace(can_reply=True),
        )
        with patch.object(bot, "ADMIN_TELEGRAM_ID", 999):
            await bot.handle_business_message(self.business_update(), self.context)
        self.context.bot.send_message.assert_not_awaited()


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_application_allows_parallel_updates(self):
        with patch.object(bot, "TELEGRAM_BOT_TOKEN", "123:test"):
            app = bot.build_application()
        self.assertEqual(app.update_processor.max_concurrent_updates, 4)

    async def test_conflict_stops_polling(self):
        application = SimpleNamespace(stop_running=Mock())
        await bot.handle_error(None, SimpleNamespace(error=Conflict("test"), application=application))
        application.stop_running.assert_called_once_with()

    async def test_control_button_is_owner_only(self):
        query = SimpleNamespace(from_user=SimpleNamespace(id=123), data="control:resume:123",
                                answer=AsyncMock(), edit_message_text=AsyncMock())
        await bot.control_button(SimpleNamespace(callback_query=query), SimpleNamespace())
        query.answer.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
