# Bahodirning shaxsiy Telegram AI yordamchisi

Bu loyiha Telegram Business orqali Bahodirning shaxsiy akkauntiga kelgan xabarlarni
boshqaradi. Oddiy bot chatida faqat egasi sozlamalarni boshqaradi; suhbatdosh bilan
yozishma Bahodirning shaxsiy akkaunti nomidan ketadi.

## Ishlash qoidasi

- Birinchi xabarda salom, ixtiyoriy stiker va tanishtirish yuboriladi.
- AI faqat mazmunli savol yoki aniq masalaga javob beradi. `ha`, `haa`, emoji,
  salomlashuv, oddiy hol-ahvol va noaniq qisqa xabarlarga javob bermaydi.
- Qo'ng'iroq, shoshilinch holat, Bahodirga xabar yetkazish va pul/qarz so'rovlarida
  bot egasiga bildirishnoma keladi. Yuborilganligi Telegram natijasi bilan aniqlanadi.
- Bahodir shu chatga o'zi yozsa, AI 24 soatga to'xtaydi. Shu davrda muhim xabarlar
  haqida bildirishnoma keladi, lekin suhbatdoshga avtomatik javob ketmaydi.
- Egasi botdagi **AI ni qayta yoqish** tugmasi yoki `/resume TELEGRAM_ID` orqali
  kutmasdan AI ni yana yoqishi mumkin.
- Gemini xato bersa yoki limiti tugasa, AI rejimida takrorlanadigan tayyor javob
  yuborilmaydi. Xabar shaxsiy Telegram chattingizda qoladi.
- Telegram navbatidan kechikib kelgan xabarlar odatda avtomatik javobsiz qoladi.
- AI ketma-ket bir necha marta ishlamasa, bot egasiga bitta sog'liq bildirishnomasi yuboradi.

Hozircha haqoratlar jurnali, kun/soat jadvali va bot ichidan Business chatga qo'lda
javob yuborish hali qo'shilmagan. Rivojlantirish rejasi: [personalization-plan.uz.md](docs/personalization-plan.uz.md).

## Egasi uchun boshqaruv

Botning o'z chatida `/start` yuboring.

- `/people` — yozgan odamlar, toifa, uslub, Siz/Sen va rejim.
- `/people TELEGRAM_ID` — shaxsni oldindan qo'shish.
- `/template TELEGRAM_ID matn` — tayyor matnni tanlash.
- `/preview TELEGRAM_ID xabar` — javobni faqat o'zingizga sinash.
- `/alerts` — oxirgi muhim xabarlar bildirishnomasi.
- `/resume TELEGRAM_ID` — shu odam bilan chatda AI ni darhol qayta yoqish.
- `/myid` — Telegram ID ni ko'rish.

Har bir kontakt uchun rejim tanlanadi:

- **AI** — yuqoridagi cheklovlar bilan AI javobi.
- **Tayyor matn** — tanishtirishdan keyin saqlangan matn.
- **Faqat muhim xabarlar** — suhbatdoshga hech narsa yuborilmaydi; muhim xabarlar
  egaga bildiriladi.

Kontakt kartasida qo'shimcha **Hazil darajasi**, **Keskin xabardagi amal** va
**Muhim so'zlar** sozlamalari bor. Keskin xabardagi `Menga bildirishnoma` holati
suhbatdoshga javob bermaydi; faqat egaga xabar yuboradi. Shaxsiy AI qoidasini
tugma orqali oddiy xabar qilib yozasiz. Qoida matni uzun bo'lsa, kartada qisqartirib
ko'rinadi; `AI qoidasini to'liq ko'rish` tugmasi uni to'liq ochadi.

## Telegram Business ulanishi

1. Bot chatida `/myid` yuboring va chiqqan raqamni `.env` ichidagi
   `ADMIN_TELEGRAM_ID=` qatoriga yozing.
2. BotFather orqali bot uchun Telegram Business funksiyasini yoqing.
3. Telegram ilovasida **Settings → Telegram Business → Chatbots/Bots** ga kiring.
4. `@bahodir_ai_assistant_bot` ni ulang, **Read Messages** va **Reply to Messages**
   ruxsatlarini yoqing, kerakli shaxsiy chatlarni tanlang.
5. Botni qayta ishga tushiring va boshqa akkauntdan Bahodirning shaxsiy akkauntiga
   xabar yuborib sinang.

Rasmiy Telegram yo'riqnomasi: [connected business bots](https://core.telegram.org/api/bots/connected-business-bots).

## `.env` sozlamasi

```env
TELEGRAM_BOT_TOKEN=YOUR_PRIVATE_BOT_TOKEN
ADMIN_TELEGRAM_ID=YOUR_TELEGRAM_ID
AI_PROVIDER=gemini
GEMINI_API_KEY=YOUR_PRIVATE_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.1-flash-lite
BUSINESS_REPLY_MODE=ai
WELCOME_STICKER_ID=
```

Kalit va tokenlarni chatga yubormang hamda `.env` faylini ulashmang. Gemini rejimida
OpenAI kaliti kerak emas. `AI_PROVIDER=openai` tanlansa, tegishli `OPENAI_API_KEY`
ham kerak bo'ladi.

## Windowsda ishga tushirish

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe bot.py
```

Terminal ochiq turishi kerak. `Conflict` xatosi chiqsa, ayni token bilan ishlayotgan
boshqa nusxani to'xtating; bitta token bir vaqtda faqat bitta polling nusxasida ishlaydi.

Kompyuterga kirilganda bot avtomatik boshlanishi va xatodan keyin qayta ochilishi uchun:

```powershell
.\tools\install-autostart.ps1
```

## Ma'lumot muddati va zaxira

`DATA_RETENTION_DAYS=60` standart holatda eski chat nusxalari, bildirishnomalar va
kunlik salomlashuv qaydlarini 60 kundan keyin o'chiradi. Kontakt sozlamalari o'chmaydi.
Muddatni `.env` ichida o'zgartirish mumkin. Bazaning izchil zaxira nusxasi uchun:

```powershell
.venv\Scripts\python.exe maintenance.py backup
```

Zaxira `backups/` ichida yaratiladi va Git'ga qo'shilmaydi.

## Git va serverga ko'chirish

`.env`, `data/`, `backups/` va jurnal fayllari Git'dan chiqarilgan. GitHub'ga faqat
kod hamda `.env.example` yuklanadi. 24/7 Telegram polling uchun bepul web-hosting emas,
doimiy diskli VM ishlating. Oracle Cloud Always Free Ubuntu VM uchun aniq yo'riqnoma:
[OCI_UBUNTU_UZ.md](deploy/OCI_UBUNTU_UZ.md).

## Test

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`data/bot.sqlite3` ichida kontakt profillari, oxirgi chat xabarlari va
bildirishnoma natijalari saqlanadi. Bu fayl shaxsiy ma'lumot bo'lishi mumkin;
kompyuteringiz va zaxira nusxalarini himoyalang.
