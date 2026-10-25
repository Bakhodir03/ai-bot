# Oracle Cloud Always Free: Ubuntu serverga o‘rnatish

Bu loyiha Telegram polling bot. U web-server emas, shuning uchun Render yoki Koyeb
free web rejimlariga qo‘yilmaydi: ular uxlaydi va lokal SQLite faylini saqlamaydi.
Oracle Cloud Always Free Ubuntu VM’da `systemd` botni qayta ishga tushirib turadi.

## 1. VM yaratish

Oracle Cloud Console ichida Ubuntu 24.04 yoki yangiroq image tanlang. `Always Free`
belgili VM.Standard.A1.Flex (Arm) yoki VM.Standard.E2.1.Micro (AMD) tanlang.
Bu bot uchun 1 OCPU va 1–2 GB RAM yetarli. SSH private key faylini faqat o‘zingizda saqlang.

Bot faqat Telegram va Gemini API’ga tashqariga chiqadi. Polling ishlagani uchun HTTP port
ochish shart emas; 22-portni faqat o‘z IP manzilingiz uchun SSH maqsadida oching.

## 2. Serverga ulanish va tayyorlash

```bash
ssh ubuntu@SERVER_PUBLIC_IP
sudo apt update
sudo apt install -y git python3 python3-venv
sudo useradd --system --create-home --shell /usr/sbin/nologin telegrambot
sudo mkdir -p /opt/telegram-ai-bot
sudo chown telegrambot:telegrambot /opt/telegram-ai-bot
sudo -u telegrambot git clone GIT_REPOSITORY_URL /opt/telegram-ai-bot
sudo -u telegrambot python3 -m venv /opt/telegram-ai-bot/.venv
sudo -u telegrambot /opt/telegram-ai-bot/.venv/bin/pip install -r /opt/telegram-ai-bot/requirements.txt
```

`GIT_REPOSITORY_URL` o‘rniga GitHub’dagi SSH yoki HTTPS manzilini yozing. Private
repository uchun serverda read-only deploy key ishlating; shaxsiy GitHub parolini yozmang.

## 3. Sirlarni serverga kiritish

`/etc/telegram-ai-bot.env` faylini yarating:

```bash
sudo nano /etc/telegram-ai-bot.env
sudo chmod 600 /etc/telegram-ai-bot.env
```

Ichiga lokal `.env` dagi qiymatlarni qo‘ying. Bu fayl Git’ga yuklanmaydi:

```env
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_ID=...
AI_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
BUSINESS_REPLY_MODE=ai
MAX_AUTO_REPLY_AGE_SECONDS=900
DATA_RETENTION_DAYS=60
```

## 4. Doimiy xizmatni yoqish

```bash
sudo cp /opt/telegram-ai-bot/deploy/telegram-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-ai
sudo systemctl status telegram-ai --no-pager
```

Jurnalni ko‘rish:

```bash
sudo journalctl -u telegram-ai -f
```

## 5. Keyingi yangilash

```bash
sudo -u telegrambot git -C /opt/telegram-ai-bot pull --ff-only
sudo -u telegrambot /opt/telegram-ai-bot/.venv/bin/pip install -r /opt/telegram-ai-bot/requirements.txt
sudo systemctl restart telegram-ai
sudo systemctl status telegram-ai --no-pager
```

`Conflict` xatosi chiqsa, eski lokal yoki boshqa serverdagi bot nusxasi ishlayotgan bo‘ladi.
Bir vaqtning o‘zida faqat bitta nusxa polling qilsin.
