"""Deliver owner alerts before acknowledging them. No AI-generated delivery claims."""
import logging
import re
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden, NetworkError, TelegramError

from localization import business_texts, offline_language
from storage import finish_alert, reserve_alert

logger = logging.getLogger(__name__)
KINDS = {
    "call": "Qo'ng'iroq so'rovi",
    "urgent": "Shoshilinch xabar",
    "notify": "Xabar yetkazish so'rovi",
    "money": "Moliyaviy so'rov",
}
CONVERSATION_STARTERS = {
    "salom", "assalom", "assalomu alaykum", "hi", "hello", "hey",
    "qandaysan", "qandaysiz", "nima gap", "nima gap o'zi", "nima gap ozi",
    "zerikishlar yomi", "zerikishlar yoqmi", "sizchi", "whats up", "how are you",
    "hows it going", "как дела", "чем занимаешься", "ты как",
}
STATUS_TEXT = {
    "uz": {
        "sent": "Xabaringiz haqida Bahodirga bot orqali bildirishnoma yuborildi. Bu uning xabarni o'qiganini yoki telefon qilish vaqtini tasdiqlamaydi.",
        "failed": "Bahodirga bot orqali bildirishnoma yuborilmadi. Xabaringiz shu shaxsiy chatda qoladi. Shoshilinch bo'lsa, unga bevosita qo'ng'iroq qiling.",
        "unknown": "Bildirishnoma yetkazilganini tasdiqlay olmadim. Shoshilinch bo'lsa, Bahodirga bevosita qo'ng'iroq qiling.",
        "none": "Hozircha Bahodirga bot orqali bildirishnoma yuborilmagan. Xabaringiz shu shaxsiy chatda turibdi.",
    },
    "ru": {
        "sent": "Баходиру отправлено уведомление через бота. Это не означает, что он уже прочитал сообщение или подтвердил время звонка.",
        "failed": "Не удалось отправить Баходиру уведомление через бота. Ваше сообщение остаётся в этом чате. Если дело срочное, позвоните ему напрямую.",
        "unknown": "Не удалось подтвердить доставку уведомления. Если дело срочное, позвоните Баходиру напрямую.",
        "none": "Уведомление Баходиру через бота пока не отправлено. Ваше сообщение находится в этом личном чате.",
    },
    "en": {
        "sent": "A notification has been sent to Bahodir through the bot. This does not confirm that he has read it or when he will call.",
        "failed": "The bot could not send Bahodir a notification. Your message remains in this chat. If it is urgent, please call him directly.",
        "unknown": "I could not confirm delivery of the notification. If it is urgent, please call Bahodir directly.",
        "none": "No notification has been sent to Bahodir through the bot yet. Your message is in this personal chat.",
    },
}


def normalize(text: str) -> str:
    return re.sub(r"['‘’ʻ`ʼ]", "", text.casefold())


def attention_kind(text: str) -> str | None:
    """Fast common requests work even when the AI service is unavailable."""
    text = normalize(text)
    if re.search(r"(?:ogohlantir|xabardor|yetkaz|yubor|ayt)\w*(?:dingmi|dizmi|dimi|ganmi|ildimi)|"
                 r"(?:did you|have you) (?:notify|tell|inform|alert|notified|told|informed)|"
                 r"(?:ты|вы) (?:уже )?(?:уведомил|сообщил|передал)", text):
        return "status"
    # A negative instruction is not an alert request; leave other intent to the model.
    if re.search(r"(?:telefon|qongiroq)\s+qilma|ogohlantirma|xabardor qilma|"
                 r"shoshilinch emas|dont (?:call|notify)|do not (?:call|notify)|"
                 r"не (?:звони|уведомляй|сообщай)", text):
        return None
    # Do not promise, negotiate or collect financial details automatically. Let the
    # owner see a request for a loan, money or an explicit amount instead.
    if re.search(r"\b(?:qarz|pul\s+(?:kerak|ber|so'r)|karta(?:ga)?\s+(?:pul|tashla)|"
                 r"loan|borrow(?:\s+money)?|send\s+money|money\s+(?:needed|need)|"
                 r"долг|занять|деньги\s+(?:нужны|нужно)|одолжи)\b|"
                 r"\b\d+(?:[\s.,]*\d+)?\s*(?:ming|minga|mln|million|so['‘’ʻ`ʼ]?m|сум|руб|dollar|usd)\b",
                 text):
        return "money"
    if re.search(r"\b(?:telefon|tel|qongiroq)\s+(?:qil(?:gin|ing|inglar)?|qivor|qib yubor)\b|"
                 r"\b(?:позвони(?:те)?|перезвони(?:те)?|звоните|қўнғироқ қил(?:инг|гин)?|телефон қил(?:инг|гин)?)\b|"
                 r"\b(?:call me|call back|give me a call|phone me)\b", text):
        return "call"
    if re.search(r"\b(?:shoshilinch|zudlik|tezda boglan|tezroq boglan|urgent|asap|срочно|срочный|шошилинч)\b", text):
        return "urgent"
    if re.search(r"\b(?:ogohlantir|xabardor qil|xabar ber|yetkazib qoy|aytib qoy)|"
                 r"\b(?:notify|alert|inform) (?:him|bahodir)|"
                 r"\b(?:сообщи|уведоми|передай)\b", text):
        return "notify"
    return None


def has_profile_alert_keyword(text: str, profile: dict | None) -> bool:
    """Match owner-entered comma/newline separated phrases without logging message text."""
    saved = str((profile or {}).get("alert_keywords") or "")
    message = normalize(text)
    for item in re.split(r"[,\n]", saved):
        phrase = normalize(item).strip()
        # Accept common Uzbek suffixes ("uchrashuvni") but reject unrelated
        # longer words that merely start with the saved phrase.
        suffix = r"(?:ni|ning|ga|da|dan|lar|lari|imiz|ingiz|im|ing|i)\b"
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?=$|[^\w]|" + suffix + r")"
        if len(phrase) >= 2 and re.search(pattern, message):
            return True
    return False


def has_hostile_language(text: str) -> bool:
    """Conservative local signal used only when the owner selected a conflict policy."""
    return bool(re.search(
        r"\b(?:ahmoq\w*|tentak\w*|iflos\w*|haromi\w*|idiot\w*|stupid\w*|dumb\w*|"
        r"fuck\w*|bitch\w*|asshole\w*|дурак\w*|идиот\w*|сука\w*|блять\w*)\b", normalize(text)
    ))


def should_stay_silent(text: str, profile: dict | None = None) -> bool:
    """Keep a personal account from behaving like an endless chat companion."""
    value = normalize(text).strip(" .,!?:;🙂😉😊😂👍👋")
    if not value:
        return True
    acknowledgements = {
        "ha", "haa", "xa", "xo'p", "xop", "ok", "okay", "mayli", "tushunarli",
        "rahmat", "thanks", "thank you", "yes", "yeah", "yep", "no", "нет", "да",
        "понятно", "ладно", "хорошо", "понял", "поняла", "ага",
    }
    if value in acknowledgements:
        return True
    # A greeting or brief check-in deserves one concise answer. Subsequent
    # acknowledgements are still suppressed by the check above.
    if value in CONVERSATION_STARTERS:
        return False
    if (profile or {}).get("category") == "friend" and re.search(
        r"\b(?:oyin|o'yn|oynay|ww\d|zerik|bored|game|игр|скучн)\w*\b", value
    ):
        return True
    return False


def is_conversation_starter(text: str) -> bool:
    return normalize(text).strip(" .,!?:;🙂😉😊😂👍👋") in CONVERSATION_STARTERS


def claims_delivery(text: str) -> bool:
    """Reject common ungrounded notification claims in otherwise ordinary AI drafts."""
    text = normalize(text)
    return bool(re.search(
        r"ogohlantir|xabardor|yozib qoy|yetkaz|bildirishnoma|xabar ber(?:dim|aman)|"
        r"aytib qoy|уведом|переда(?:л|м|но)|сообщил|оповест|"
        r"\b(?:notif\w*|alerted|forwarded|relayed)\b|(?:pass|forward|relay) (?:it|your|the message)", text))


async def notify_owner(bot, owner_id: int, message, profile: dict, kind: str) -> str:
    if kind not in KINDS:
        raise ValueError("Unsupported notification kind")
    row, inserted = reserve_alert(owner_id, message.business_connection_id, message.chat_id,
                                  message.message_id, message.from_user.id, kind)
    if not inserted:
        return "unknown" if row["status"] == "pending" else row["status"]
    moment = getattr(message, "date", None) or datetime.now(timezone.utc)
    local_time = moment.astimezone(timezone(timedelta(hours=5))).strftime("%d.%m.%Y %H:%M")
    name = profile.get("name") or str(message.from_user.id)
    username = "@" + profile["username"] if profile.get("username") else "Username yo'q"
    original = (message.text or getattr(message, "caption", "") or "").strip()
    text = (f"🔔 {KINDS[kind]}\nKimdan: {name}\n{username}\nTelegram ID: {message.from_user.id}"
            f"\nVaqt: {local_time} (Toshkent)\n\nAsl xabar:\n{original[:2800]}"
            "\n\nJavob berish yoki qo'ng'iroq qilish uchun shaxsiy Telegram chattingizni oching.")
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(
        "Shaxs sozlamalari", callback_data=f"people:show:{message.from_user.id}")]])
    try:
        delivered = await bot.send_message(chat_id=owner_id, text=text,
                                           reply_markup=markup, disable_notification=False)
    except (Forbidden, BadRequest) as error:
        finish_alert(row["id"], "failed", error_type=type(error).__name__)
        logger.warning("Owner alert rejected: %s", type(error).__name__)
        return "failed"
    except (NetworkError, TelegramError) as error:
        # A timeout can occur after Telegram accepted the message. Do not falsely
        # report success or retry and risk a duplicate notification.
        finish_alert(row["id"], "unknown", error_type=type(error).__name__)
        logger.warning("Owner alert delivery uncertain: %s", type(error).__name__)
        return "unknown"
    finish_alert(row["id"], "sent", admin_message_id=delivered.message_id)
    return "sent"


async def delivery_reply(text: str, history: list[dict], profile: dict, status: str,
                         hint: str = "") -> str:
    status = status if status in {"sent", "failed", "none"} else "unknown"
    language = offline_language(text, history, hint)
    # These fixed acknowledgments are chosen only from the actual Telegram result.
    if language in STATUS_TEXT:
        answer = STATUS_TEXT[language][status]
        if profile.get("address") == "sen" and language == "uz":
            answer = answer.replace("Xabaringiz", "Xabaring").replace("xabaringiz", "xabaring")
            answer = answer.replace("qiling", "qil")
        return answer
    translated = await business_texts(text, history, {**profile, "template": STATUS_TEXT["uz"][status]}, hint)
    return translated["fallback"]
