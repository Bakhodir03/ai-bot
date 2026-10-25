"""Private, owner-only contact settings. No messages are sent to contacts here."""
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
from telegram.error import BadRequest
from datetime import datetime, timedelta, timezone
import time

from ai import generate_reply
from config import ADMIN_TELEGRAM_ID, AUTO_REPLY_TEXT, BUSINESS_REPLY_MODE
from localization import business_texts
from storage import (
    PROFILE_OPTIONS, get_contact, human_control_active, list_contacts, remember_contact,
    recent_alerts, resume_ai, update_contact,
)

FIELDS = {
    "category": "Toifa", "tone": "Uslub", "address": "Murojaat",
    "reply_length": "Javob uzunligi", "humor": "Hazil darajasi",
    "conflict_mode": "Keskin xabardagi amal", "reply_mode": "Rejim",
}


def excerpt(value: str, limit: int) -> str:
    value = (value or "").replace("\n", " ").strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


def is_owner(update) -> bool:
    return bool(ADMIN_TELEGRAM_ID and update.effective_user
                and update.effective_user.id == ADMIN_TELEGRAM_ID
                and update.effective_chat and update.effective_chat.id == ADMIN_TELEGRAM_ID
                and update.effective_chat.type == "private")


def owner_menu():
    return Keyboard([[Button("Shaxslar", callback_data="people:list:0")],
                     [Button("Bildirishnomalar", callback_data="alerts:list")]])


async def alerts_command(update, context):
    if not is_owner(update):
        if update.callback_query:
            await update.callback_query.answer("Faqat akkaunt egasi uchun.", show_alert=True)
        else:
            await update.message.reply_text("Bu bo'lim faqat akkaunt egasi uchun.")
        return
    statuses = {"sent": "Telegram'ga yuborilgan", "failed": "Yuborilmagan",
                "unknown": "Yetkazilishi tasdiqlanmagan", "pending": "Yetkazilishi tasdiqlanmagan"}
    lines = ["Oxirgi 10 ta bildirishnoma:"]
    for item in recent_alerts(ADMIN_TELEGRAM_ID):
        moment = datetime.fromisoformat(item["created_at"]).replace(tzinfo=timezone.utc)
        local = moment.astimezone(timezone(timedelta(hours=5))).strftime("%d.%m %H:%M")
        lines.append(f"{local} — ID {item['user_id']} — {statuses[item['status']]}")
    if len(lines) == 1:
        lines.append("Hozircha bildirishnoma yo'q.")
    lines.append("\nVaqt: Toshkent. Yuborilgan holati xabar o'qilganini anglatmaydi.")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text("\n".join(lines))


def contacts_page(offset: int = 0):
    contacts = list_contacts(ADMIN_TELEGRAM_ID, offset, 9)
    rows = [[Button(f"{p['name'] or p['user_id']} · {p['user_id']}"[:60],
                    callback_data=f"people:show:{p['user_id']}")] for p in contacts[:8]]
    nav = []
    if offset:
        nav.append(Button("← Oldingi", callback_data=f"people:list:{max(0, offset - 8)}"))
    if len(contacts) > 8:
        nav.append(Button("Keyingi →", callback_data=f"people:list:{offset + 8}"))
    if nav:
        rows.append(nav)
    return ("Shaxslar. Sozlash uchun odamni tanlang.\n"
            "Yangi yozganlar shu yerda paydo bo'ladi. ID orqali qo'shish: /people TELEGRAM_ID."
            if contacts else "Hozircha shaxslar yo'q. Shaxsiy akkauntingizga yangi xabar kelganda "
            "ro'yxatga qo'shiladi. Oldindan qo'shish: /people TELEGRAM_ID."), Keyboard(rows)


def contact_card(user_id: int):
    p = get_contact(ADMIN_TELEGRAM_ID, user_id)
    if not p:
        raise ValueError("Unknown contact")
    lines = [p["name"] or "Shaxs", f"Telegram ID: {user_id}"]
    if p["username"]:
        lines.append("@" + p["username"])
    for field, label in FIELDS.items():
        lines.append(f"{label}: {PROFILE_OPTIONS[field][p[field]]}")
    if p["reply_mode"] == "default":
        lines.append(f"Amaldagi rejim: {PROFILE_OPTIONS['reply_mode'][BUSINESS_REPLY_MODE]}")
    paused = human_control_active(ADMIN_TELEGRAM_ID, user_id, int(time.time()))
    keywords = excerpt(p["alert_keywords"].replace("\n", ", "), 240) or "yo'q"
    lines += ["Til: har bir kiruvchi xabarga mos (avtomatik)",
              "Tayyor javob: " + excerpt(p["template"] or AUTO_REPLY_TEXT, 600),
              "Shaxsiy AI qoidasi: " + (excerpt(p["custom_instruction"], 600) or "yo'q"),
              "Muhim kalit so'zlar: " + keywords,
              "AI holati: vaqtincha to'xtatilgan" if paused else "AI holati: yoqilgan",
              "", "Tugma bilan tanlangan sozlama darhol saqlanadi.",
              "AI qoidasi 2.0: toifa, uslub, hazil, keskin xabardagi amal va shaxsiy qoidani birga ishlatadi.",
              f"Tayyor matn: /template {user_id} matn",
              f"Matnni tiklash: /template {user_id} -",
              "Shaxsiy qoida: pastdagi ✍ AI qoidasini yozish tugmasini bosing.",
              f"Faqat sizga sinov javobi: /preview {user_id} Hello!"]
    rows = [[Button(label, callback_data=f"people:field:{user_id}:{field}")]
            for field, label in FIELDS.items()]
    rows.append([Button("▶ AI ni qayta yoqish" if paused else "✓ AI yoqilgan",
                        callback_data=f"people:resume:{user_id}")])
    rows.append([Button("✍ AI qoidasini yozish", callback_data=f"people:instruction:{user_id}")])
    rows.append([Button("📄 AI qoidasini to'liq ko'rish", callback_data=f"people:ruletext:{user_id}")])
    rows.append([Button("🔔 Muhim so'zlarni yozish", callback_data=f"people:keywords:{user_id}")])
    rows.append([Button("← Shaxslar", callback_data="people:list:0")])
    return "\n".join(lines), Keyboard(rows)


async def people_command(update, context):
    if not is_owner(update):
        await update.message.reply_text("Bu bo'lim faqat akkaunt egasi uchun.")
        return
    if context.args:
        if len(context.args) != 1 or not context.args[0].isdigit() or not 0 < int(context.args[0]) < 2**63:
            await update.message.reply_text("Foydalanish: /people yoki /people TELEGRAM_ID")
            return
        target = int(context.args[0])
        if not get_contact(ADMIN_TELEGRAM_ID, target):
            remember_contact(ADMIN_TELEGRAM_ID, target)
        text, keyboard = contact_card(target)
    else:
        text, keyboard = contacts_page()
    await update.message.reply_text(text, reply_markup=keyboard)


async def profile_button(update, context):
    query = update.callback_query
    if not is_owner(update):
        await query.answer("Bu bo'lim faqat akkaunt egasi uchun.", show_alert=True)
        return
    parts = query.data.split(":")
    session = getattr(context, "user_data", None)
    # A person selection starts a focused one-message input. Moving anywhere
    # else in the panel must not leave that input active by accident.
    starts_text_input = len(parts) == 3 and parts[1] in {"instruction", "keywords"}
    if isinstance(session, dict) and not starts_text_input:
        session.pop("profile_text_input", None)
    try:
        if len(parts) < 3 or not parts[2].isdigit() or not 0 <= int(parts[2]) < 2**63:
            raise ValueError("Invalid selection")
        action, target = parts[1], int(parts[2])
        if action == "list" and len(parts) == 3:
            text, keyboard = contacts_page(target)
        elif action == "show" and len(parts) == 3:
            text, keyboard = contact_card(target)
        elif action == "resume" and len(parts) == 3:
            if not get_contact(ADMIN_TELEGRAM_ID, target):
                raise ValueError("Unknown contact")
            was_paused = human_control_active(ADMIN_TELEGRAM_ID, target, int(time.time()))
            resume_ai(ADMIN_TELEGRAM_ID, target)
            text, keyboard = contact_card(target)
            text = ("AI shu chat uchun qayta yoqildi.\n\n" if was_paused
                    else "AI bu chatda allaqachon yoqilgan.\n\n") + text
        elif action == "instruction" and len(parts) == 3:
            if not get_contact(ADMIN_TELEGRAM_ID, target):
                raise ValueError("Unknown contact")
            if isinstance(session, dict):
                session["profile_text_input"] = {"target": target, "field": "custom_instruction"}
            text = ("AI uchun shaxsiy qoida yozishga tayyor.\n\n"
                    "Endi keyingi oddiy xabaringizga qoidani yozing — u shu shaxs uchun saqlanadi.\n"
                    "Masalan: Hazilni tabiiy qabul qil, ammo haqorat bilan javob qaytarma.\n\n"
                    "Qoidani o'chirish uchun faqat - belgisini yuboring.")
            keyboard = Keyboard([[Button("Bekor qilish", callback_data=f"people:show:{target}")]])
        elif action == "keywords" and len(parts) == 3:
            if not get_contact(ADMIN_TELEGRAM_ID, target):
                raise ValueError("Unknown contact")
            if isinstance(session, dict):
                session["profile_text_input"] = {"target": target, "field": "alert_keywords"}
            text = ("Muhim kalit so'zlarni yozishga tayyor.\n\n"
                    "Keyingi oddiy xabaringizga vergul bilan ajratib yozing. Shu so'zlar kelgan xabarda "
                    "uchrasa, sizga bildirishnoma yuboriladi.\n\n"
                    "Masalan: hisobot, uchrashuv, to'lov\n"
                    "O'chirish uchun faqat - belgisini yuboring.")
            keyboard = Keyboard([[Button("Bekor qilish", callback_data=f"people:show:{target}")]])
        elif action == "ruletext" and len(parts) == 3:
            profile = get_contact(ADMIN_TELEGRAM_ID, target)
            if not profile:
                raise ValueError("Unknown contact")
            text = "Shaxsiy AI qoidasi:\n\n" + (profile["custom_instruction"] or "Hozircha qoida yozilmagan.")
            keyboard = Keyboard([[Button("← Orqaga", callback_data=f"people:show:{target}")]])
        elif action == "field" and len(parts) == 4 and parts[3] in FIELDS:
            if not get_contact(ADMIN_TELEGRAM_ID, target):
                raise ValueError("Unknown contact")
            field = parts[3]
            text = f"{FIELDS[field]} tanlang. Tanlov darhol saqlanadi."
            rows = [[Button(label, callback_data=f"people:set:{target}:{field}:{value}")]
                    for value, label in PROFILE_OPTIONS[field].items()]
            rows.append([Button("← Orqaga", callback_data=f"people:show:{target}")])
            keyboard = Keyboard(rows)
        elif action == "set" and len(parts) == 5:
            update_contact(ADMIN_TELEGRAM_ID, target, parts[3], parts[4])
            text, keyboard = contact_card(target)
        else:
            raise ValueError("Invalid selection")
    except ValueError:
        await query.answer("Tanlov eskirgan yoki noto'g'ri. /people orqali qayta oching.", show_alert=True)
        return
    await query.answer()
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest as error:
        if "Message is not modified" not in str(error):
            raise


async def template_command(update, context):
    if not is_owner(update):
        await update.message.reply_text("Bu buyruq faqat akkaunt egasi uchun.")
        return
    # Split the original message so line breaks in the saved template survive.
    parts = update.message.text.split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit() or not 0 < int(parts[1]) < 2**63:
        await update.message.reply_text("Foydalanish: /template TELEGRAM_ID matn (1–2000 belgi)")
        return
    target, value = int(parts[1]), parts[2].strip()
    try:
        update_contact(ADMIN_TELEGRAM_ID, target, "template", "" if value == "-" else value)
    except ValueError:
        await update.message.reply_text("Shaxs topilmadi yoki matn 2000 belgidan uzun. /people orqali tekshiring.")
        return
    text, keyboard = contact_card(target)
    await update.message.reply_text("Tayyor javob saqlandi.\n\n" + text, reply_markup=keyboard)


async def instruction_command(update, context):
    if not is_owner(update):
        await update.message.reply_text("Bu buyruq faqat akkaunt egasi uchun.")
        return
    parts = update.message.text.split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit() or not 0 < int(parts[1]) < 2**63:
        await update.message.reply_text("Foydalanish: /instruction TELEGRAM_ID qoida (1–2000 belgi)")
        return
    target, value = int(parts[1]), parts[2].strip()
    try:
        update_contact(ADMIN_TELEGRAM_ID, target, "custom_instruction", "" if value == "-" else value)
    except ValueError:
        await update.message.reply_text("Shaxs topilmadi yoki qoida 2000 belgidan uzun. /people orqali tekshiring.")
        return
    text, keyboard = contact_card(target)
    await update.message.reply_text("AI qoidasi saqlandi.\n\n" + text, reply_markup=keyboard)


async def instruction_input(update, context):
    """Save the next owner message after the personal-rule button is pressed."""
    if not is_owner(update):
        return
    session = getattr(context, "user_data", None)
    pending = session.get("profile_text_input") if isinstance(session, dict) else None
    if not isinstance(pending, dict):
        return
    target, field = pending.get("target"), pending.get("field")
    if (not isinstance(target, int) or field not in {"custom_instruction", "alert_keywords"}
            or not get_contact(ADMIN_TELEGRAM_ID, target)):
        if isinstance(session, dict):
            session.pop("profile_text_input", None)
        return
    value = (update.message.text or "").strip()
    if not value:
        await update.message.reply_text("Matn bo'sh. Matn yozing yoki Bekor qilish tugmasini bosing.")
        return
    limit = 500 if field == "alert_keywords" else 2000
    if len(value) > limit:
        await update.message.reply_text(f"Matn {limit} belgidan oshmasin. Qisqartirib qayta yuboring.")
        return
    try:
        update_contact(ADMIN_TELEGRAM_ID, target, field, "" if value == "-" else value)
    except ValueError:
        await update.message.reply_text("Shaxs topilmadi. /people orqali qayta oching.")
        return
    session.pop("profile_text_input", None)
    text, keyboard = contact_card(target)
    saved = "Muhim kalit so'zlar saqlandi." if field == "alert_keywords" else "AI qoidasi saqlandi."
    await update.message.reply_text(saved + "\n\n" + text, reply_markup=keyboard)


async def preview_command(update, context):
    if not is_owner(update):
        await update.message.reply_text("Bu buyruq faqat akkaunt egasi uchun.")
        return
    parts = update.message.text.split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit() or not 0 < int(parts[1]) < 2**63 or len(parts[2]) > 2000:
        await update.message.reply_text("Foydalanish: /preview TELEGRAM_ID namunaviy xabar (2000 belgigacha)")
        return
    p = get_contact(ADMIN_TELEGRAM_ID, int(parts[1]))
    if not p:
        await update.message.reply_text("Shaxs topilmadi. /people orqali qo'shing.")
        return
    mode = BUSINESS_REPLY_MODE if p["reply_mode"] == "default" else p["reply_mode"]
    if mode == "manual":
        answer = "Qo'lda rejim: avtomatik javob ham, stiker ham yuborilmaydi."
    else:
        try:
            texts = await business_texts(parts[2], [], p)
            answer = texts["greeting"] + "\n👋\n" + texts["intro"]
            if mode == "static":
                answer += "\n\n" + texts["fallback"]
            elif not texts["greeting_only"]:
                answer += "\n\n" + await generate_reply(parts[2], [], business=True, profile=p)
        except Exception:
            await update.message.reply_text("Sinovda AI xizmatiga ulanish imkoni bo'lmadi. Keyinroq urinib ko'ring.")
            return
    await update.message.reply_text("Sinov — faqat sizga. Suhbatdoshga yuborilmadi:\n" + answer[:3800])
