"""Small SQLite store: last messages per user and human handoff state."""
import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH


@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH, timeout=15)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_business_messages_chat
            ON business_messages(connection_id, chat_id, id)
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_daily_greetings (
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                greeted_on TEXT NOT NULL,
                PRIMARY KEY(connection_id, chat_id, greeted_on)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS contact_profiles (
                owner_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'unknown',
                tone TEXT NOT NULL DEFAULT 'polite',
                address TEXT NOT NULL DEFAULT 'siz',
                reply_mode TEXT NOT NULL DEFAULT 'default',
                reply_length TEXT NOT NULL DEFAULT 'short',
                humor TEXT NOT NULL DEFAULT 'gentle',
                conflict_mode TEXT NOT NULL DEFAULT 'calm',
                template TEXT NOT NULL DEFAULT '',
                custom_instruction TEXT NOT NULL DEFAULT '',
                alert_keywords TEXT NOT NULL DEFAULT '',
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(owner_id, user_id)
            )
        """)
        profile_columns = {row[1] for row in db.execute("PRAGMA table_info(contact_profiles)")}
        if "custom_instruction" not in profile_columns:
            db.execute("ALTER TABLE contact_profiles ADD COLUMN custom_instruction TEXT NOT NULL DEFAULT ''")
        if "reply_length" not in profile_columns:
            db.execute("ALTER TABLE contact_profiles ADD COLUMN reply_length TEXT NOT NULL DEFAULT 'short'")
        if "humor" not in profile_columns:
            db.execute("ALTER TABLE contact_profiles ADD COLUMN humor TEXT NOT NULL DEFAULT 'gentle'")
        if "conflict_mode" not in profile_columns:
            db.execute("ALTER TABLE contact_profiles ADD COLUMN conflict_mode TEXT NOT NULL DEFAULT 'calm'")
        if "alert_keywords" not in profile_columns:
            db.execute("ALTER TABLE contact_profiles ADD COLUMN alert_keywords TEXT NOT NULL DEFAULT ''")
        message_columns = {row[1] for row in db.execute("PRAGMA table_info(business_messages)")}
        if "created_at" not in message_columns:
            db.execute("ALTER TABLE business_messages ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
            db.execute("UPDATE business_messages SET created_at=CURRENT_TIMESTAMP WHERE created_at='' ")
        db.execute("""
            CREATE TABLE IF NOT EXISTS owner_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_message_id INTEGER,
                error_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_id, connection_id, chat_id, message_id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_controls (
                owner_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                human_until INTEGER NOT NULL DEFAULT 0,
                last_owner_message_id INTEGER,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(owner_id, user_id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS service_health (
                service TEXT PRIMARY KEY,
                failure_count INTEGER NOT NULL DEFAULT 0,
                window_started INTEGER NOT NULL DEFAULT 0,
                last_notified INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_business_history(connection_id: str, chat_id: int) -> list[dict]:
    with connect() as db:
        rows = db.execute("""
            SELECT role, content FROM business_messages
            WHERE connection_id = ? AND chat_id = ? ORDER BY id DESC LIMIT 8
        """, (connection_id, chat_id)).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def has_daily_greeting(connection_id: str, chat_id: int, greeted_on: str) -> bool:
    with connect() as db:
        return db.execute(
            """SELECT 1 FROM business_daily_greetings
            WHERE connection_id = ? AND chat_id = ? AND greeted_on = ?""",
            (connection_id, chat_id, greeted_on),
        ).fetchone() is not None


def mark_daily_greeting(connection_id: str, chat_id: int, greeted_on: str):
    with connect() as db:
        db.execute(
            """INSERT OR IGNORE INTO business_daily_greetings(connection_id, chat_id, greeted_on)
            VALUES(?, ?, ?)""",
            (connection_id, chat_id, greeted_on),
        )


def save_business_message(connection_id: str, chat_id: int, role: str, content: str):
    if role not in {"user", "assistant"}:
        raise ValueError("Invalid business message role")
    if not content:
        return
    with connect() as db:
        db.execute("""
            INSERT INTO business_messages(connection_id, chat_id, role, content)
            VALUES(?, ?, ?, ?)
        """, (connection_id, chat_id, role, content[:4000]))
        db.execute("""
            DELETE FROM business_messages WHERE connection_id=? AND chat_id=?
            AND id NOT IN (
                SELECT id FROM business_messages WHERE connection_id=? AND chat_id=?
                ORDER BY id DESC LIMIT 20
            )
        """, (connection_id, chat_id, connection_id, chat_id))


def purge_expired_data(retention_days: int):
    """Remove old local content while preserving active contact settings."""
    if retention_days < 7:
        raise ValueError("Retention must be at least 7 days")
    modifier = f"-{retention_days} days"
    with connect() as db:
        db.execute("DELETE FROM business_messages WHERE created_at < datetime('now', ?)", (modifier,))
        db.execute("DELETE FROM owner_alerts WHERE created_at < datetime('now', ?)", (modifier,))
        db.execute("DELETE FROM business_daily_greetings WHERE greeted_on < date('now', ?)", (modifier,))


def record_service_failure(service: str, now_epoch: int, *, threshold: int = 3,
                           window_seconds: int = 600, notify_cooldown: int = 1800) -> bool:
    """Return true only for a rate-limited owner health notification."""
    with connect() as db:
        row = db.execute("SELECT failure_count, window_started, last_notified FROM service_health WHERE service=?",
                         (service,)).fetchone()
        count, started, notified = row if row else (0, now_epoch, 0)
        if now_epoch - started > window_seconds:
            count, started = 0, now_epoch
        count += 1
        should_notify = count >= threshold and (not notified or now_epoch - notified >= notify_cooldown)
        if should_notify:
            notified = now_epoch
        db.execute("""
            INSERT INTO service_health(service, failure_count, window_started, last_notified)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(service) DO UPDATE SET
                failure_count=excluded.failure_count,
                window_started=excluded.window_started,
                last_notified=excluded.last_notified,
                updated_at=CURRENT_TIMESTAMP
        """, (service, count, started, notified))
    return should_notify


def record_service_success(service: str):
    with connect() as db:
        db.execute("""
            INSERT INTO service_health(service, failure_count, window_started, last_notified)
            VALUES (?, 0, 0, 0)
            ON CONFLICT(service) DO UPDATE SET
                failure_count=0,
                window_started=0,
                updated_at=CURRENT_TIMESTAMP
        """, (service,))


PROFILE_OPTIONS = {
    "category": {"unknown": "Yangi kontakt", "boss": "Rahbar", "colleague": "Hamkasb",
                 "friend": "Do'st", "client": "Mijoz", "family": "Oila", "vip": "VIP"},
    "tone": {"polite": "Xushmuomala", "formal": "Rasmiy", "friendly": "Samimiy"},
    "address": {"siz": "Siz", "sen": "Sen"},
    "reply_length": {"short": "Qisqa", "normal": "O'rtacha", "detailed": "Batafsil"},
    "humor": {"off": "Hazilsiz", "gentle": "Yengil hazil", "natural": "Tabiiy hazil"},
    "conflict_mode": {"calm": "Vazmin javob", "silent": "Javob bermaslik",
                      "notify": "Menga bildirishnoma"},
    "reply_mode": {"default": "Umumiy sozlama", "ai": "AI", "static": "Tayyor matn",
                   "manual": "Faqat muhim xabarlar (avtojavob o'chiq)"},
}


def remember_contact(owner_id: int, user_id: int, name: str = "", username: str = ""):
    if owner_id <= 0 or user_id <= 0:
        raise ValueError("Invalid contact ID")
    with connect() as db:
        db.execute("""
            INSERT INTO contact_profiles(owner_id, user_id, name, username) VALUES(?, ?, ?, ?)
            ON CONFLICT(owner_id, user_id) DO UPDATE SET
                name=CASE WHEN excluded.name != '' THEN excluded.name ELSE contact_profiles.name END,
                username=excluded.username, last_seen=CURRENT_TIMESTAMP
        """, (owner_id, user_id, name[:150], username[:64]))


def get_contact(owner_id: int, user_id: int) -> dict | None:
    with connect() as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM contact_profiles WHERE owner_id=? AND user_id=?",
                         (owner_id, user_id)).fetchone()
    return dict(row) if row else None


def list_contacts(owner_id: int, offset: int = 0, limit: int = 9) -> list[dict]:
    with connect() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("""
            SELECT * FROM contact_profiles WHERE owner_id=?
            ORDER BY last_seen DESC, user_id LIMIT ? OFFSET ?
        """, (owner_id, limit, max(0, offset))).fetchall()
    return [dict(row) for row in rows]


def update_contact(owner_id: int, user_id: int, field: str, value: str):
    if field in {"template", "custom_instruction", "alert_keywords"}:
        maximum = 500 if field == "alert_keywords" else 2000
        if len(value) > maximum:
            raise ValueError("Profile text too long")
    elif field not in PROFILE_OPTIONS or value not in PROFILE_OPTIONS[field]:
        raise ValueError("Invalid profile setting")
    with connect() as db:
        # Column names are restricted to the allowlist above; values remain parameters.
        result = db.execute(f"UPDATE contact_profiles SET {field}=? WHERE owner_id=? AND user_id=?",
                            (value, owner_id, user_id))
        if not result.rowcount:
            raise ValueError("Unknown contact")


def reserve_alert(owner_id: int, connection_id: str, chat_id: int, message_id: int,
                  user_id: int, kind: str) -> tuple[dict, bool]:
    """Reserve a source message before sending; duplicates never send twice."""
    with connect() as db:
        db.row_factory = sqlite3.Row
        inserted = db.execute("""
            INSERT OR IGNORE INTO owner_alerts(owner_id, connection_id, chat_id, message_id, user_id, kind)
            VALUES(?, ?, ?, ?, ?, ?)
        """, (owner_id, connection_id, chat_id, message_id, user_id, kind)).rowcount == 1
        row = db.execute("""
            SELECT * FROM owner_alerts WHERE owner_id=? AND connection_id=? AND chat_id=? AND message_id=?
        """, (owner_id, connection_id, chat_id, message_id)).fetchone()
    return dict(row), inserted


def finish_alert(alert_id: int, status: str, admin_message_id: int | None = None,
                 error_type: str | None = None):
    if status not in {"sent", "failed", "unknown"}:
        raise ValueError("Invalid delivery status")
    with connect() as db:
        db.execute("UPDATE owner_alerts SET status=?, admin_message_id=?, error_type=? WHERE id=?",
                   (status, admin_message_id, error_type, alert_id))


def latest_alert(owner_id: int, user_id: int) -> dict | None:
    with connect() as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM owner_alerts WHERE owner_id=? AND user_id=? ORDER BY id DESC LIMIT 1",
                         (owner_id, user_id)).fetchone()
    return dict(row) if row else None


def recent_alerts(owner_id: int) -> list[dict]:
    with connect() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM owner_alerts WHERE owner_id=? ORDER BY id DESC LIMIT 10",
                          (owner_id,)).fetchall()
    return [dict(row) for row in rows]


def activate_human_control(owner_id: int, user_id: int, message_id: int,
                           until_epoch: int) -> bool:
    """Record a human takeover. Return True only when it begins a new session."""
    with connect() as db:
        row = db.execute("""
            SELECT human_until FROM conversation_controls WHERE owner_id=? AND user_id=?
        """, (owner_id, user_id)).fetchone()
        was_active = bool(row and row[0] > until_epoch - 24 * 60 * 60)
        db.execute("""
            INSERT INTO conversation_controls(owner_id, user_id, human_until, last_owner_message_id)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(owner_id, user_id) DO UPDATE SET
                human_until=excluded.human_until,
                last_owner_message_id=excluded.last_owner_message_id,
                updated_at=CURRENT_TIMESTAMP
        """, (owner_id, user_id, until_epoch, message_id))
    return not was_active


def human_control_active(owner_id: int, user_id: int, now_epoch: int) -> bool:
    with connect() as db:
        row = db.execute("""
            SELECT human_until FROM conversation_controls WHERE owner_id=? AND user_id=?
        """, (owner_id, user_id)).fetchone()
    return bool(row and row[0] > now_epoch)


def resume_ai(owner_id: int, user_id: int):
    with connect() as db:
        db.execute("""
            INSERT INTO conversation_controls(owner_id, user_id, human_until)
            VALUES(?, ?, 0)
            ON CONFLICT(owner_id, user_id) DO UPDATE SET human_until=0, updated_at=CURRENT_TIMESTAMP
        """, (owner_id, user_id))
