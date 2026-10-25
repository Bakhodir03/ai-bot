import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import profiles
import storage


class ProfileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db_patch = patch.object(storage, "DATABASE_PATH", Path(temp.name) / "bot.sqlite3")
        db_patch.start()
        self.addCleanup(db_patch.stop)
        admin_patch = patch.object(profiles, "ADMIN_TELEGRAM_ID", 999)
        admin_patch.start()
        self.addCleanup(admin_patch.stop)
        storage.initialize()
        storage.remember_contact(999, 123, "Test")
        self.message = SimpleNamespace(text="/people", reply_text=AsyncMock())
        self.query = SimpleNamespace(data="people:set:123:reply_mode:manual",
                                     answer=AsyncMock(), edit_message_text=AsyncMock())
        self.update = SimpleNamespace(effective_user=SimpleNamespace(id=999),
                                      effective_chat=SimpleNamespace(id=999, type="private"),
                                      message=self.message, callback_query=self.query)
        self.context = SimpleNamespace(args=[], bot=SimpleNamespace(send_message=AsyncMock()), user_data={})

    async def test_non_owner_and_group_cannot_read_or_change_profiles(self):
        for user_id, chat_id, kind in [(321, 321, "private"), (999, -321, "group")]:
            self.update.effective_user.id = user_id
            self.update.effective_chat.id = chat_id
            self.update.effective_chat.type = kind
            await profiles.people_command(self.update, self.context)
            await profiles.profile_button(self.update, self.context)
            await profiles.alerts_command(self.update, self.context)
            self.assertEqual(storage.get_contact(999, 123)["reply_mode"], "default")
            self.query.edit_message_text.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()

    async def test_alerts_command_shows_only_owner_delivery_status(self):
        row, _ = storage.reserve_alert(999, "a", 123, 1, 123, "call")
        storage.finish_alert(row["id"], "sent", 55)
        storage.reserve_alert(888, "a", 444, 1, 444, "urgent")
        self.update.callback_query = None
        await profiles.alerts_command(self.update, self.context)
        text = self.message.reply_text.call_args.args[0]
        self.assertIn("ID 123", text)
        self.assertNotIn("ID 444", text)
        self.assertIn("Telegram'ga yuborilgan", text)

    async def test_owner_changes_mode_with_inline_button(self):
        await profiles.profile_button(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["reply_mode"], "manual")
        self.assertIn("avtojavob o'chiq", self.query.edit_message_text.call_args.args[0])

    async def test_owner_can_choose_response_length(self):
        self.query.data = "people:set:123:reply_length:detailed"
        await profiles.profile_button(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["reply_length"], "detailed")
        self.assertIn("Batafsil", self.query.edit_message_text.call_args.args[0])

    async def test_contact_card_has_ai_resume_button(self):
        storage.activate_human_control(999, 123, 10, 2_000_000_000)
        self.query.data = "people:resume:123"
        await profiles.profile_button(self.update, self.context)
        self.assertFalse(storage.human_control_active(999, 123, 1))
        text = self.query.edit_message_text.call_args.args[0]
        self.assertIn("qayta yoqildi", text)
        keyboard = self.query.edit_message_text.call_args.kwargs["reply_markup"]
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        self.assertIn("people:resume:123", [button.callback_data for button in buttons])

    async def test_tampered_callback_cannot_set_unapproved_field(self):
        self.query.data = "people:set:123:owner_id:321"
        await profiles.profile_button(self.update, self.context)
        self.assertIsNone(storage.get_contact(321, 123))
        self.query.edit_message_text.assert_not_awaited()

    async def test_manual_preview_sends_only_to_owner_and_does_not_change_history(self):
        storage.update_contact(999, 123, "reply_mode", "manual")
        self.message.text = "/preview 123 Hello"
        with patch.object(profiles, "generate_reply", new_callable=AsyncMock) as generate:
            await profiles.preview_command(self.update, self.context)
        generate.assert_not_awaited()
        self.context.bot.send_message.assert_not_awaited()
        self.assertIn("yuborilmaydi", self.message.reply_text.call_args.args[0])
        self.assertEqual(storage.get_business_history("connection-a", 123), [])

    async def test_template_preserves_lines_and_can_reset(self):
        self.message.text = "/template 123 One\nTwo"
        await profiles.template_command(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["template"], "One\nTwo")
        self.message.text = "/template 123 -"
        await profiles.template_command(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["template"], "")

    async def test_owner_can_save_and_clear_personal_ai_instruction(self):
        self.message.text = "/instruction 123 Rahbar bilan juda qisqa va rasmiy yoz."
        await profiles.instruction_command(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["custom_instruction"],
                         "Rahbar bilan juda qisqa va rasmiy yoz.")
        self.message.text = "/instruction 123 -"
        await profiles.instruction_command(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["custom_instruction"], "")

    async def test_instruction_button_saves_the_next_owner_message(self):
        self.query.data = "people:instruction:123"
        await profiles.profile_button(self.update, self.context)
        self.assertEqual(self.context.user_data["profile_text_input"],
                         {"target": 123, "field": "custom_instruction"})
        self.assertIn("keyingi oddiy xabaringiz", self.query.edit_message_text.call_args.args[0])

        self.message.text = "Hazilni tushun, lekin haqorat bilan javob qaytarma."
        await profiles.instruction_input(self.update, self.context)

        self.assertEqual(storage.get_contact(999, 123)["custom_instruction"], self.message.text)
        self.assertNotIn("profile_text_input", self.context.user_data)
        self.assertIn("AI qoidasi saqlandi", self.message.reply_text.call_args.args[0])

    async def test_keywords_are_saved_and_long_rule_is_safe_to_display(self):
        self.query.data = "people:keywords:123"
        await profiles.profile_button(self.update, self.context)
        self.message.text = "hisobot, uchrashuv, to'lov"
        await profiles.instruction_input(self.update, self.context)
        self.assertEqual(storage.get_contact(999, 123)["alert_keywords"], self.message.text)

        storage.update_contact(999, 123, "custom_instruction", "q" * 2000)
        storage.update_contact(999, 123, "template", "t" * 2000)
        text, keyboard = profiles.contact_card(123)
        self.assertLess(len(text), 3000)
        buttons = [button.callback_data for row in keyboard.inline_keyboard for button in row]
        self.assertIn("people:ruletext:123", buttons)

        self.query.data = "people:ruletext:123"
        await profiles.profile_button(self.update, self.context)
        self.assertIn("q" * 2000, self.query.edit_message_text.call_args.args[0])

    async def test_pagination_has_no_contact_leaks(self):
        for user_id in range(1000, 1010):
            storage.remember_contact(999, user_id)
        storage.remember_contact(777, 9999, "Other owner's contact")
        text, keyboard = profiles.contacts_page()
        buttons = [b for row in keyboard.inline_keyboard for b in row]
        self.assertIn("people:list:8", [b.callback_data for b in buttons])
        self.assertNotIn("people:show:9999", [b.callback_data for b in buttons])
        for button in buttons:
            self.assertLessEqual(len(button.callback_data.encode()), 64)
