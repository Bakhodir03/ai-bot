"""Optional synthetic API smoke check: python -m tests.live_language_check.

Uses the configured AI API, but never contacts Telegram or writes chat history.
"""
import asyncio
import json
import logging

import ai
from localization import business_texts


async def main():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    history = [{"role": "user", "content": "Salom"},
               {"role": "assistant", "content": "Men Bahodirning AI yordamchisiman."}]
    profile = {"tone": "polite", "address": "siz"}
    examples = [
        ("uz", "Bahodir bilan ish yuzasidan gaplashmoqchiman."),
        ("ru", "Я хочу обсудить с Баходиром рабочий вопрос."),
        ("en", "I would like to discuss a project with Bahodir."),
        ("tr", "Bahodir ile bir proje hakkında konuşmak istiyorum."),
        ("ar", "أريد مناقشة مشروع مع بهادير."),
    ]
    try:
        for language, message in examples:
            answer = await ai.generate_reply(message, history, business=True, profile=profile)
            print(json.dumps({"language": language, "answer": answer}, ensure_ascii=True), flush=True)
            history = (history + [{"role": "user", "content": message},
                                  {"role": "assistant", "content": answer}])[-8:]
        for language, message in [("tr", "Merhaba"), ("ar", "مرحبا")]:
            texts = await business_texts(message, history, profile, hint="uz")
            print(json.dumps({"welcome_language": language, **texts}, ensure_ascii=True), flush=True)
            if not texts["intro"] or not texts["greeting_only"]:
                raise RuntimeError("Localization check failed")
    except Exception as error:
        print("Live check failed: " + type(error).__name__, flush=True)
        cause = error.__cause__
        for _ in range(4):
            if cause is None:
                break
            print(f"Cause: {type(cause).__name__}; errno={getattr(cause, 'errno', None)}; "
                  f"winerror={getattr(cause, 'winerror', None)}", flush=True)
            cause = cause.__cause__ or cause.__context__
        return 1
    finally:
        if ai._client:
            await ai._client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
