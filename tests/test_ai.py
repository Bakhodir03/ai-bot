import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from openai import RateLimitError

import ai
import config


class GeminiTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_request_contains_history_and_business_instructions(self):
        with tempfile.TemporaryDirectory() as folder:
            knowledge = Path(folder) / "company.txt"
            knowledge.write_text("Verified business facts", encoding="utf-8")
            history = [{"role": "user", "content": "Previous question"},
                       {"role": "assistant", "content": "Previous answer"}]
            with patch.object(ai, "AI_PROVIDER", "gemini"), \
                    patch.object(ai, "KNOWLEDGE_PATH", knowledge), \
                    patch.object(ai, "gemini_complete", new_callable=AsyncMock,
                                 return_value="Salom!") as complete:
                answer = await ai.generate_reply("Salom", history, business=True)
        self.assertEqual(answer, "Salom!")
        messages = complete.call_args.args[0]
        self.assertEqual(messages[1:-1], history)
        self.assertEqual(messages[-1], {"role": "user", "content": "Salom"})
        self.assertIn("Verified business facts", messages[0]["content"])
        self.assertIn("automated AI assistant", messages[0]["content"])
        self.assertNotIn("/operator", messages[0]["content"])

    async def test_gemini_quota_error_has_provider_specific_notice(self):
        response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
        error = RateLimitError("secret details", response=response, body={"code": 429})
        with patch.object(ai, "AI_PROVIDER", "gemini"):
            notice = ai.error_notice(error)
        self.assertIn("Gemini", notice)
        self.assertNotIn("OpenAI", notice)
        self.assertNotIn("secret details", notice)

    async def test_empty_gemini_answer_raises_instead_of_saving_fake_answer(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"choices": []}),
        ))
        try:
            with patch.object(ai, "GEMINI_API_KEY", "fake-key"):
                with self.assertRaisesRegex(RuntimeError, "no text"):
                    await ai.gemini_complete([{"role": "user", "content": "Salom"}], client=client)
        finally:
            await client.aclose()

    async def test_gemini_rest_client_uses_google_endpoint_and_key(self):
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        try:
            with patch.object(ai, "GEMINI_API_KEY", "gemini-test-key"), \
                    patch.object(ai, "GEMINI_MODEL", "gemini-test"):
                answer = await ai.gemini_complete([{"role": "user", "content": "Hello"}], client=client)
        finally:
            await client.aclose()
        self.assertEqual(answer, "OK")
        self.assertEqual(str(requests[0].url), ai.GEMINI_CHAT_URL)
        self.assertEqual(requests[0].headers["Authorization"], "Bearer gemini-test-key")
        self.assertEqual(json.loads(requests[0].content)["model"], "gemini-test")

    async def test_gemini_uses_fallback_after_primary_is_overloaded(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            if len(requests) < 3:
                return httpx.Response(503, request=request, json={"error": "busy"})
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        try:
            with patch.object(ai, "GEMINI_API_KEY", "gemini-test-key"), \
                    patch.object(ai, "GEMINI_MODEL", "primary-model"), \
                    patch.object(ai, "GEMINI_FALLBACK_MODEL", "fallback-model"), \
                    patch("ai.asyncio.sleep", new_callable=AsyncMock):
                answer = await ai.gemini_complete([{"role": "user", "content": "Hello"}], client=client)
        finally:
            await client.aclose()
        self.assertEqual(answer, "OK")
        self.assertEqual([item["model"] for item in requests], [
            "primary-model", "primary-model", "fallback-model",
        ])

class ConfigTests(unittest.TestCase):
    def test_gemini_does_not_require_openai_key(self):
        with patch.multiple(config, AI_PROVIDER="gemini", GEMINI_API_KEY="fake-key",
                            OPENAI_API_KEY="", TELEGRAM_BOT_TOKEN="123:test"):
            config.validate_config()

    def test_missing_gemini_key_does_not_fall_back_to_openai(self):
        with patch.multiple(config, AI_PROVIDER="gemini", GEMINI_API_KEY="",
                            OPENAI_API_KEY="fake-key", TELEGRAM_BOT_TOKEN="123:test"):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                config.validate_config()

    def test_invalid_provider_is_rejected(self):
        with patch.object(config, "AI_PROVIDER", "typo"):
            with self.assertRaisesRegex(RuntimeError, "AI_PROVIDER"):
                config.validate_config()


class ProfileStyleTests(unittest.TestCase):
    def test_category_changes_ai_style_rules(self):
        self.assertIn("manager", ai.style_rules({"category": "boss"}))
        self.assertIn("work colleague", ai.style_rules({"category": "colleague"}))
        self.assertIn("friend", ai.style_rules({"category": "friend"}))
        self.assertIn("client", ai.style_rules({"category": "client"}))
        self.assertIn("family", ai.style_rules({"category": "family"}))
        self.assertIn("Do not discuss prices", ai.style_rules({
            "category": "client", "custom_instruction": "Do not discuss prices until Bahodir confirms.",
        }))
        self.assertIn("Asia/Tashkent", ai.style_rules({"category": "boss"}))
        self.assertIn("two to four short paragraphs", ai.style_rules({
            "category": "friend", "reply_length": "detailed",
        }))
        self.assertIn("Natural, light playful humor", ai.style_rules({"humor": "natural"}))
        self.assertIn("choose silent", ai.style_rules({"conflict_mode": "silent"}))
