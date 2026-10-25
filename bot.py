"""Telegram Business helper controlled from the owner's private bot chat."""
import logging
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Conflict, TelegramError
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

from ai import plan_business_reply
from config import (
    ADMIN_TELEGRAM_ID, BUSINESS_REPLY_MODE, DATA_RETENTION_DAYS, MAX_AUTO_REPLY_AGE_SECONDS,
    TELEGRAM_BOT_TOKEN, ROOT, WELCOME_STICKER_ID, validate_config,
)
from instance_lock import AlreadyRunningError, single_instance
from localization import business_texts
from notifications import (
    attention_kind, claims_delivery, delivery_reply, is_conversation_starter,
    has_hostile_language, has_profile_alert_keyword, notify_owner, should_stay_silent,
)
from profiles import (
    alerts_command, instruction_command, owner_menu, people_command, preview_command,
    profile_button, template_command, instruction_input,
)
from storage import (
    activate_human_control, get_business_history, human_control_active, initialize,
    purge_expired_data, resume_ai, save_business_message,
    record_service_failure, record_service_success,
    has_daily_greeting, mark_daily_greeting,
    remember_contact, get_contact,
    latest_alert,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# HTTP request URLs contain the Telegram token. Do not log them.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
_requests = defaultdict(deque)
HUMAN_TAKEOVER_SECONDS = 24 * 60 * 60


async def report_ai_failure_if_needed(context: ContextTypes.DEFAULT_TYPE):
    if not record_service_failure("ai", int(time.time())):
        return
    try:
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=("⚠ AI xizmati ketma-ket bir necha marta javob bermadi. "
                  "Hozir avtomatik AI javoblari yuborilmaydi. Internet va Gemini limitini tekshiring."),
        )
    except TelegramError as error:
        logger.warning("Could not report AI health issue: %s", type(error).__name__)


def tashkent_day() -> str:
    return datetime.now(timezone(timedelta(hours=5))).date().isoformat()


def is_stale_business_message(message) -> bool:
    """Never revive an ordinary personal conversation from a delayed update queue."""
    sent_at = getattr(message, "date", None)
    if not isinstance(sent_at, datetime):
        return False
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - sent_at.astimezone(timezone.utc)).total_seconds() > MAX_AUTO_REPLY_AGE_SECONDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_TELEGRAM_ID:
        await update.message.reply_text(
            "Admin panel.\n/people — shaxslar, uslub va avtojavob rejimi\n"
            "/alerts — bildirishnomalar holati\n"
            "/resume TELEGRAM_ID — shu shaxs uchun AI ni darhol qayta yoqish\n"
            "/myid — ID",
            reply_markup=owner_menu(),
        )
        return
    await update.message.reply_text(
        "Bu bot Bahodirning shaxsiy Telegram akkauntidagi yordamchini boshqarish uchun ishlatiladi."
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Sizning Telegram ID raqamingiz: {update.effective_user.id}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


def allowed_by_rate_limit(chat_id: int | tuple) -> bool:
    now = time.monotonic()
    q = _requests[chat_id]
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= 6:
        return False
    q.append(now)
    return True


async def handle_owner_business_message(message, context: ContextTypes.DEFAULT_TYPE):
    """Pause AI when the owner personally writes in a Business chat."""
    target_user_id = message.chat_id
    if target_user_id == ADMIN_TELEGRAM_ID:
        return
    text = (message.text or getattr(message, "caption", "") or "").strip()
    save_business_message(message.business_connection_id, target_user_id, "assistant", text)
    started = activate_human_control(
        ADMIN_TELEGRAM_ID,
        target_user_id,
        message.message_id,
        int(time.time()) + HUMAN_TAKEOVER_SECONDS,
    )
    if not started:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("AI ni qayta yoqish", callback_data=f"control:resume:{target_user_id}"),
    ]])
    try:
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=("Siz bu chatga o'zingiz yozdingiz. AI 24 soat javob bermaydi. "
                  "Muhim xabarlar haqida bildirishnoma kelishda davom etadi."),
            reply_markup=keyboard,
        )
    except TelegramError as error:
        logger.warning("Could not confirm human control: %s", type(error).__name__)


async def handle_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply through an authorized personal-account connection, never as the standalone bot."""
    message = update.business_message
    if not message or not message.business_connection_id or not ADMIN_TELEGRAM_ID:
        return
    sender = message.from_user
    if (not sender or sender.is_bot or message.sender_business_bot
            or message.chat.type != "private"):
        return
    connection_id = message.business_connection_id
    connection = await context.bot.get_business_connection(connection_id)
    rights = getattr(connection, "rights", None)
    can_reply = rights.can_reply if rights else getattr(connection, "can_reply", False)
    if (connection.user.id != ADMIN_TELEGRAM_ID
            or not connection.is_enabled or not can_reply):
        return
    if sender.id == ADMIN_TELEGRAM_ID:
        await handle_owner_business_message(message, context)
        return

    history = get_business_history(connection_id, message.chat_id)
    text = (message.text or getattr(message, "caption", "") or "").strip()
    save_business_message(connection_id, message.chat_id, "user", text)
    remember_contact(ADMIN_TELEGRAM_ID, sender.id,
                     getattr(sender, "full_name", "") or "", getattr(sender, "username", "") or "")
    profile = get_contact(ADMIN_TELEGRAM_ID, sender.id)
    if is_stale_business_message(message):
        logger.info("Skipped stale business update: chat=%s", message.chat_id)
        return
    mode = profile["reply_mode"] if profile["reply_mode"] != "default" else BUSINESS_REPLY_MODE
    intent = attention_kind(text)
    hostile = has_hostile_language(text)
    if not intent and has_profile_alert_keyword(text, profile):
        intent = "notify"
    if not intent and hostile and profile.get("conflict_mode") == "notify":
        intent = "notify"
    delivery_status = None
    if intent in {"call", "urgent", "notify", "money"}:
        # Owner alerts are independent of automatic replies and their rate limit.
        # Send before waiting for any AI or translation service.
        delivery_status = await notify_owner(context.bot, ADMIN_TELEGRAM_ID, message, profile, intent)
    elif intent == "status":
        previous = latest_alert(ADMIN_TELEGRAM_ID, sender.id)
        delivery_status = previous["status"] if previous else "none"
    # Manual mode and human takeover still keep important owner alerts above,
    # but never send anything back into that personal conversation.
    if mode == "manual" or human_control_active(ADMIN_TELEGRAM_ID, sender.id, int(time.time())):
        return
    # This contact policy intentionally alerts only the owner; replying could
    # escalate a hostile exchange or reveal the alert.
    if hostile and profile.get("conflict_mode") == "notify":
        return
    if hostile and profile.get("conflict_mode") == "silent":
        return
    if not allowed_by_rate_limit((connection_id, message.chat_id)):
        return

    hint = getattr(sender, "language_code", "") or ""
    if delivery_status is not None:
        answer = await delivery_reply(text, history, profile, delivery_status, hint)
        await context.bot.send_message(chat_id=message.chat_id, text=answer,
                                       business_connection_id=connection_id)
        save_business_message(connection_id, message.chat_id, "assistant", answer)
        return
    texts = None
    day = tashkent_day()
    starts_conversation = is_conversation_starter(text)
    if not has_daily_greeting(connection_id, message.chat_id, day) or starts_conversation:
        texts = await business_texts(text, history, profile, hint)
        destination = {"chat_id": message.chat_id, "business_connection_id": connection_id}
        await context.bot.send_message(**destination, text=texts["greeting"])
        if WELCOME_STICKER_ID:
            try:
                await context.bot.send_sticker(**destination, sticker=WELCOME_STICKER_ID)
            except TelegramError as error:
                logger.warning("Welcome sticker unavailable: %s", type(error).__name__)
        if texts["intro"]:
            await context.bot.send_message(**destination, text=texts["intro"])
        if text and texts["intro"]:
            save_business_message(connection_id, message.chat_id, "assistant",
                                  texts["greeting"] + "\n" + texts["intro"])
        if texts["intro"]:
            mark_daily_greeting(connection_id, message.chat_id, day)
        if mode == "ai" and (not text or starts_conversation):
            return
        # A first message can already contain a question: answer it after the welcome.
    if mode == "ai" and should_stay_silent(text, profile):
        logger.info("Business reply suppressed as low-signal: chat=%s", message.chat_id)
        return
    if mode == "ai" and len(text) > 2000:
        # Long text is retained in the owner's Telegram chat, but it must not
        # trigger the old generic waiting response.
        return
    answer = None
    if mode == "ai" and text and len(text) <= 2000:
        try:
            plan = await plan_business_reply(text, history, profile=profile)
            record_service_success("ai")
            logger.info("Business reply decision: chat=%s attention=%s action=%s",
                        message.chat_id, plan.attention, plan.action)
            if plan.attention in {"call", "urgent", "notify", "money"}:
                state = await notify_owner(context.bot, ADMIN_TELEGRAM_ID, message, profile, plan.attention)
                answer = await delivery_reply(text, history, profile, state, hint)
            elif plan.attention == "status":
                previous = latest_alert(ADMIN_TELEGRAM_ID, sender.id)
                answer = await delivery_reply(text, history, profile,
                                              previous["status"] if previous else "none", hint)
            elif plan.action == "silent":
                return
            elif claims_delivery(plan.reply):
                # An ordinary draft must never masquerade as a completed action.
                answer = await delivery_reply(text, history, profile, "none", hint)
            else:
                answer = plan.reply
        except Exception as error:
            # A generic fallback after a quota/network failure is misleading and
            # creates a repetitive chat companion. The owner can still see the message.
            logger.warning("Business AI unavailable; no automatic reply: %s", type(error).__name__)
            await report_ai_failure_if_needed(context)
            return
    if human_control_active(ADMIN_TELEGRAM_ID, sender.id, int(time.time())):
        # The owner may have written while the AI request was being generated.
        return
    if answer is None:
        texts = texts or await business_texts(text, history, profile, hint)
        answer = texts["fallback"]
    for i in range(0, len(answer), 4000):
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=answer[i:i + 4000],
            business_connection_id=connection_id,
        )
    save_business_message(connection_id, message.chat_id, "assistant", answer)
    logger.info("Business reply sent: chat=%s", message.chat_id)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.error(
            "Telegram Conflict: shu token bilan boshqa bot nusxasi ishlayapti. "
            "Bu nusxa to'xtatiladi. Boshqa terminal yoki serverdagi nusxani tekshiring."
        )
        context.application.stop_running()
        return
    # Raw exception text can contain credentials, URLs or private message content.
    logger.error("Update processing failed: %s", type(context.error).__name__)


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow only the owner to end a temporary human takeover early."""
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        return
    # CommandHandler normally fills context.args. Reading the message as a fallback
    # also accepts commands forwarded or formatted by Telegram clients differently.
    raw = " ".join(context.args or [])
    match = re.search(r"(?<!\d)(\d{1,19})(?!\d)", raw or (update.message.text or ""))
    if not match or not 0 < int(match.group(1)) < 2**63:
        await update.message.reply_text("Foydalanish: /resume 1074409531")
        return
    user_id = int(match.group(1))
    resume_ai(ADMIN_TELEGRAM_ID, user_id)
    await update.message.reply_text("AI bu chat uchun qayta yoqildi.")


async def control_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or query.from_user.id != ADMIN_TELEGRAM_ID:
        return
    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[:2] != ["control", "resume"] or not parts[2].isdigit():
        return
    resume_ai(ADMIN_TELEGRAM_ID, int(parts[2]))
    await query.answer("AI qayta yoqildi")
    await query.edit_message_text("AI bu chat uchun qayta yoqildi.")


async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Botni boshlash"),
        BotCommand("myid", "Telegram ID ni bilish"),
        BotCommand("people", "Shaxslar va avtojavob sozlamalari (egasi uchun)"),
        BotCommand("instruction", "Shaxs uchun AI qoidasini yozish (egasi uchun)"),
        BotCommand("alerts", "Bildirishnomalar holati (egasi uchun)"),
        BotCommand("resume", "Chatdagi AI ni qayta yoqish (egasi uchun)"),
        BotCommand("help", "Yordam"),
    ])


def build_application():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    ordinary = filters.UpdateType.MESSAGE & filters.ChatType.PRIVATE
    app.add_handler(MessageHandler(
        filters.UpdateType.BUSINESS_MESSAGE & filters.ChatType.PRIVATE
        & (filters.TEXT | filters.ATTACHMENT), handle_business_message,
    ))
    for command, handler in (
        ("start", start), ("help", help_command), ("myid", my_id),
        ("people", people_command), ("template", template_command), ("instruction", instruction_command),
        ("preview", preview_command),
        ("alerts", alerts_command), ("resume", resume_command),
    ):
        app.add_handler(CommandHandler(command, handler, filters=ordinary))
    app.add_handler(MessageHandler(ordinary & filters.TEXT & ~filters.COMMAND, instruction_input))
    app.add_handler(CallbackQueryHandler(control_button, pattern="^control:resume:"))
    app.add_handler(CallbackQueryHandler(profile_button, pattern="^people:"))
    app.add_handler(CallbackQueryHandler(alerts_command, pattern="^alerts:list$"))
    app.add_error_handler(handle_error)
    return app


def main():
    try:
        with single_instance(ROOT / "data" / "bot.lock"):
            run_bot()
    except AlreadyRunningError:
        logger.error(
            "Bot allaqachon shu loyihada ishlayapti. Ikkinchi nusxa ochilmadi. "
            "Mavjud botdan foydalaning; qayta ishga tushirishdan oldin uni to'xtating."
        )
        return 1
    return 0


def run_bot():
    validate_config()
    initialize()
    purge_expired_data(DATA_RETENTION_DAYS)
    app = build_application()
    if not ADMIN_TELEGRAM_ID:
        logger.warning("Personal-account auto replies disabled: set ADMIN_TELEGRAM_ID using /myid")
    logger.info("Bot is running. Open your Telegram bot and send /start")
    app.run_polling(
        drop_pending_updates=False,
        allowed_updates=["message", "callback_query", "business_message"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
