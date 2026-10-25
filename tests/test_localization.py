import json
import unittest
from unittest.mock import AsyncMock, patch

import ai
import localization as loc


class LanguageTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_greetings_use_current_language_not_previous_history(self):
        history = [{"role": "user", "content": "Salom"}, {"role": "assistant", "content": "Salom!"}]
        with patch.object(loc, "complete_text", new_callable=AsyncMock) as complete:
            for text, language in [("Привет!", "ru"), ("Hello", "en"), ("Салом", "uz-Cyrl")]:
                result = await loc.business_texts(text, history, hint="uz")
                self.assertEqual(result, loc.pack(language, True))
        complete.assert_not_awaited()

    async def test_arbitrary_language_translates_template_without_answering_question(self):
        translated = dict(greeting="Merhaba!", intro="Ben Bahodir'in kişisel yapay zekâ asistanıyım.",
                          fallback="Mesajınız alındı.", greeting_only=False)
        with patch.object(loc, "complete_text", new=AsyncMock(return_value=json.dumps(translated))) as complete:
            result = await loc.business_texts("Bahodir ile görüşebilir miyim?", [],
                                            {"template": "Xabaringiz qabul qilindi.", "tone": "formal"})
        self.assertEqual(result, translated)
        instructions, conversation = complete.call_args.args
        payload = json.loads(conversation[0]["content"])
        self.assertEqual(payload["incoming_message"], "Bahodir ile görüşebilir miyim?")
        self.assertEqual(payload["source"]["fallback"], "Xabaringiz qabul qilindi.")
        self.assertIn("Do not answer", instructions)

    async def test_bad_translation_json_falls_back_safely(self):
        for raw in ["invalid json", "[]", '{"greeting_only": "yes"}',
                    '{"greeting_only": false, "greeting": 10}']:
            with patch.object(loc, "complete_text", new=AsyncMock(return_value=raw)):
                result = await loc.business_texts("Когда можно связаться?", [])
            self.assertEqual(result["fallback"], loc.pack("ru")["fallback"])

    async def test_offline_unknown_language_does_not_send_wrong_uzbek_text(self):
        with patch.object(loc, "complete_text", new_callable=AsyncMock) as complete:
            result = await loc.business_texts("こんにちは", [], offline=True)
        complete.assert_not_awaited()
        self.assertEqual(result["fallback"], "⏳")

    async def test_emoji_uses_previous_user_language_in_outage(self):
        history = [{"role": "user", "content": "Привет"}, {"role": "assistant", "content": "Salom"}]
        result = await loc.business_texts("👍", history, offline=True)
        self.assertEqual(result["fallback"], loc.pack("ru")["fallback"])

    async def test_latest_message_and_owner_style_reach_ai_without_profile_identity(self):
        with patch.object(ai, "complete_text", new=AsyncMock(return_value="Ответ")) as complete:
            result = await ai.generate_reply("Когда можно связаться?",
                                            [{"role": "user", "content": "Salom"}], business=True,
                                            profile={"tone": "formal", "address": "sen", "category": "boss",
                                                     "name": "Private internal label"})
        rules, conversation = complete.call_args.args
        self.assertEqual(result, "Ответ")
        self.assertIn("LATEST incoming user message", rules)
        self.assertIn("formal and respectful", rules)
        self.assertIn("informal singular", rules)
        self.assertIn("NO forwarding or notification capability", rules)
        self.assertNotIn("Private internal label", rules)
        self.assertNotIn("/operator", rules)
        self.assertEqual(conversation[-1]["content"], "Когда можно связаться?")
