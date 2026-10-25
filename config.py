"""Load non-secret configuration; credentials live in a local .env file."""
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
WELCOME_STICKER_ID = os.getenv("WELCOME_STICKER_ID", "").strip()

_admin = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
if _admin and (not _admin.isdigit() or int(_admin) <= 0):
    raise ValueError("ADMIN_TELEGRAM_ID must be a positive Telegram numeric ID")
ADMIN_TELEGRAM_ID = int(_admin) if _admin else None

BUSINESS_REPLY_MODE = os.getenv("BUSINESS_REPLY_MODE", "ai").strip().lower()
if BUSINESS_REPLY_MODE not in {"ai", "static"}:
    raise ValueError("BUSINESS_REPLY_MODE must be ai or static")
AUTO_REPLY_TEXT = os.getenv(
    "AUTO_REPLY_TEXT",
    "Assalomu alaykum! Bu avtomatik javob. Xabaringiz qabul qilindi. "
    "Iltimos, javobni kuting.",
).strip()
if not AUTO_REPLY_TEXT or len(AUTO_REPLY_TEXT) > 2000:
    raise ValueError("AUTO_REPLY_TEXT must contain 1 to 2000 characters")

MAX_AUTO_REPLY_AGE_SECONDS = int(os.getenv("MAX_AUTO_REPLY_AGE_SECONDS", "900"))
if not 60 <= MAX_AUTO_REPLY_AGE_SECONDS <= 86400:
    raise ValueError("MAX_AUTO_REPLY_AGE_SECONDS must be between 60 and 86400")

DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "60"))
if not 7 <= DATA_RETENTION_DAYS <= 3650:
    raise ValueError("DATA_RETENTION_DAYS must be between 7 and 3650")

DATABASE_PATH = ROOT / "data" / "bot.sqlite3"
KNOWLEDGE_PATH = ROOT / "knowledge" / "company.txt"


def validate_config() -> None:
    if AI_PROVIDER not in {"openai", "gemini"}:
        raise RuntimeError("AI_PROVIDER must be openai or gemini")
    key_name, api_key = (
        ("GEMINI_API_KEY", GEMINI_API_KEY) if AI_PROVIDER == "gemini"
        else ("OPENAI_API_KEY", OPENAI_API_KEY)
    )
    missing = [
        key for key, val in [
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            (key_name, api_key),
        ] if not val
    ]
    if missing:
        raise RuntimeError(
            "Missing configuration: " + ", ".join(missing)
            + ". Create a .env file using .env.example."
        )
