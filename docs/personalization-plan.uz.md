# Shaxs, uslub va vaqt bo'yicha boshqariladigan Telegram yordamchi

Sana: 2026-10-25. Holat: birinchi bosqich va chatni vaqtli qo'lda boshqarish amalga oshirildi; quyidagi to'liq rejaning qolgan qismlari hali reja.
Akkaunt egasi: Bahodir. Boshqaruvchi Telegram ID: 518662608.
Vaqt mintaqasi: Asia/Tashkent.

Amaldagi birinchi bosqich: `/people` orqali shaxs kartasi, toifa (ichki belgi),
alohida uslub va Siz/Sen tanlovi, AI/tayyor matn/qo'lda rejimlari, `/template`,
`/preview` va kiruvchi xabarga mos avtomatik til. Egasi Business chatga o'zi
yozsa, AI aynan o'sha chatda 24 soat jim turadi; `/resume TELEGRAM_ID` yoki
tugma uni muddatidan oldin qayta yoqadi. Tugma tanlovi darhol saqlanadi;
versiya tarixi va alohida tasdiqlash oynasi hali yo'q. Hozirgi toifalar guruhli
shablonlar emas. Qo'ng'iroq/shoshilinch xabar uchun bildirishnoma, haqiqiy yuborish
holatiga mos tasdiq va `/alerts` qo'shildi. AI oddiy qisqa suhbatni davom
ettirmaydi va API xatosida takroriy tayyor javob yubormaydi. Jadval, Business
chatiga bot ichidan admin javobi, tasdiqlash rejimi va haqoratlar jurnali hali
amalga oshirilmagan.
Til haqidagi keyingi talab sabab tayyor matn ham AI orqali tarjima qilinishi mumkin;
quyidagi dastlabki "model chaqirilmaydi" talabi shu jihatdan o'zgardi.

## 1. Maqsad va chegaralar

Bahodir bot ichidan kimga, qanday ohangda, qaysi mavzularda, qaysi kun va soatlarda
qanday javob berilishini boshqaradi. Bir odamga alohida profil yoki bir nechta
odamga umumiy toifa qo'llanadi. Bot rasmiy rahbar, do'st, mijoz va boshqa rollarni
ism yoki yozishmadan o'zi taxmin qilib tayinlamaydi: rolni Bahodir belgilaydi.

Bu hujjat avvalgi muhim xabarlar, botdan javob yuborish, AI'ni to'xtatish va
haqoratlar jurnali rejasini kengaytiradi. Ishlayotgan botni ushbu hujjatning
o'zi o'zgartirmaydi. Sana qoidalari kiruvchi xabarga javobni boshqaradi;
odamlarga o'z-o'zidan tabrik yoki rejalashtirilgan xabar yubormaydi.

## 2. Hozirgi fakt

2026-10-25 kuni config.py, bot.py, ai.py va storage.py tekshirildi.

| Qism | Hozir mavjud | Qo'shiladigan qism |
|---|---|---|
| AI | Gemini; qisqa/noaniq xabarda jim, mazmunli savolga reja asosida javob | Har bir chat uchun tekshirilgan profil |
| Rejim | Umumiy BUSINESS_REPLY_MODE va kontakt uchun AI/tayyor matn/qo'lda | Tasdiqlash rejimi |
| Tanishtirish | Tilga mos salom, tanishtirish va ixtiyoriy stiker | Profilga mos tanishtirish tanlovi |
| Kontakt | Xabardan sender.id olinadi | Doimiy kontakt kartasi va toifa |
| Tarix | Ulanish/chat uchun oxirgi 20 xabar | Barqaror egasi/kontakt identifikatori |
| Kun va sana | Mavjud emas | Hafta kunlari, soatlar, sana oralig'i, istisnolar |
| Boshqaruv | Faqat egaga ochiq menyu, `/people`, `/alerts`, `/resume` | Jadval va tasdiqlash menyusi |
| Admin javobi | Egasi shaxsiy Telegram chatidan bevosita yozadi; bu AI'ni 24 soat to'xtatadi | Bot ichidan Business suhbatga xavfsiz yo'naltirish |
| Audit | Xabar muallifi/vaqti to'liq saqlanmaydi | Xabar, qaror, sozlama va yuborish jurnali |

## 3. Kimga qanday javob: boshlang'ich shablonlar

Bular tavsiya etiladigan shablonlar; mavjud kontaktlarga avtomatik tayinlanmaydi.

| Toifa | Ohang va murojaat | Tavsiya rejim | Bildirishnoma | Chegara |
|---|---|---|---|---|
| Rahbar | Rasmiy, hurmatli, Siz; qisqa | Tasdiqlash | Har yangi masala | Muddat va va'dani o'zi bermaydi |
| Hamkasb | Ishchan, sodda, Siz | AI | Muhim/shoshilinch | Tasdiqlanmagan ish holatini aytmaydi |
| Mijoz | Xushmuomala, tushunarli, Siz | AI | Buyurtma, shikoyat, to'lov masalasi | Narx va kafolat faqat tasdiqlangan manbadan |
| Do'st | Samimiy, qisqa; Sen faqat siz tanlasangiz | AI | Siz belgilagan mavzular | Bahodir bo'lib gapirmaydi |
| Oila/yaqinlar | Iliq va hurmatli | Qo'lda | Xabar kelganda | Shaxsiy munosabatni AI o'zi yuritmaydi |
| VIP | Alohida tanlangan uslub | Tasdiqlash | Yuqori ustuvorlik | Maxsus ko'rsatma shaxsiy profilda |
| Yangi kontakt | Neytral, Siz | Hozirgi AI rejimi | Odam bilan gaplashish talabi/muhim masala | Niyatni aniqlashtiradi |
| Javob berilmasin | Tashqariga javob yo'q | Qo'lda | Siz tanlagan daraja | Telegram bloklash bilan bir xil emas |

Bir odamga bitta asosiy toifa beriladi; qidirish uchun bir nechta yorliq bo'lishi
mumkin. Kontaktning shaxsiy sozlamasi toifa shablonidagi aynan shu maydonni
almashtiradi. Bir xil ismli odamlar Telegram ID orqali ajratiladi.

Bir xil "Bahodir bilan bugun gaplashsam bo'ladimi?" savoliga namunalar:
- Rahbar uchun sizga ko'rsatiladigan loyiha: "Assalomu alaykum. Men Bahodirning
  shaxsiy AI yordamchisiman. Qaysi masala va vaqt yuzasidan bog'lanmoqchisiz?"
- Do'st uchun: "Salom! Men Bahodirning AI yordamchisiman. Nima gap edi? Qaysi
  vaqtda gaplashmoqchisan?" Sen murojaati faqat shu profilda yoqilgan bo'lsa.
- Mijoz uchun: "Assalomu alaykum! Men Bahodirning AI yordamchisiman. Qaysi
  xizmat yoki masala bo'yicha bog'lanmoqchisiz?"
- Qo'lda boshqariladigan oila profili: tashqariga avtomatik javob yo'q;
  Bahodirning bot chatiga kiruvchi xabar haqida bildirishnoma keladi.

Bu birinchi tanishtirish namunalari; keyingi xabarlarda tanishtirish takrorlanmaydi.
Aniq vaqt tasdiqlanmaguncha "Bahodir bugun albatta gaplashadi" deyilmaydi.

## 4. Kontakt kartasi

Kartada ism, username bo'lsa username, Telegram ID, toifa, faol profil,
javob rejimi, bugungi jadval va bildirishnoma tanlovi ko'rinadi. Telefon raqami
talab qilinmaydi. Username o'zgarsa ID o'sha kontaktni saqlab qoladi.

Tahrirlanadigan maydonlar:
- Ohang: rasmiy, ishchan, samimiy yoki shaxsiy ko'rsatma.
- Murojaat: Siz/Sen va faqat egasi tasdiqlagan murojaat nomi.
- Til: suhbat tiliga mos, o'zbekcha, ruscha yoki egasi tanlagan til.
- Javob uzunligi: qisqa/o'rtacha; emoji va stiker: yoqilgan/o'chirilgan.
- Rejim: AI/tayyor matn/tasdiqlash/qo'lda.
- Salomlashuv matni, birinchi tanishtirish, maxsus tayyor javob.
- Javob berish mumkin bo'lgan mavzular va tasdiqlangan faktlar.
- Sizga topshiriladigan mavzular: uchrashuv tasdig'i, pul, kelishuv, shikoyat kabi.
- Bildirishnoma darajasi va jadvali; javob jadvalidan alohida.
- Egasi yozgan 2-3 ta uslub namunasi (ixtiyoriy), umumiy chatlardan ko'chirilmaydi.

AI doim yordamchi sifatida qoladi. Uslubni o'xshatish Bahodirning o'zi yozayotgani
haqida yolg'on aytish yoki uning nomidan kelishuv tasdiqlashni anglatmaydi.
Shaxsiy izohlar (masalan, "bu rahbarim") ichki belgi; suhbatdoshga chiqarilmaydi.

## 5. Bot ichidagi boshqaruv oqimi

Asosiy menyu: Shaxslar / Toifalar / Jadval / Muhim xabarlar / Javob loyihalari /
Haqoratlar jurnali / Sozlamalar.

Yangi odam uchun:
1. Telegram botga ruxsat berilgan shaxsiy chatdan yangi xabar keladi.
2. Sizning bot chattingizda xabar kartasi va "Profilni sozlash" tugmasi ko'rinadi.
3. Toifani tanlaysiz yoki "Shaxsiy profil" ochasiz.
4. Ohang, rejim, tanishtirish, kerakli ko'rsatma va jadvalni tanlaysiz.
5. "Sinab ko'rish" orqali namunaviy xabar kiritasiz. Javob faqat sizga ko'rsatiladi.
6. "Saqlash va qo'llash" yangi versiyani faollashtiradi. "Bekor qilish" eski
   sozlamani saqlaydi; "Oldingi versiya" orqali qaytarish mumkin.

Sinov ekranida: tanlangan odam, mahalliy sana/vaqt, ishlagan qoida, yakuniy
rejim va javob namunasini ko'rsatish kerak. Sinov suhbatdoshga xabar yubormaydi,
real suhbat tarixiga yoki tanishtirish holatiga yozilmaydi.

Bot barcha kontaktlar ro'yxatini avtomatik o'qiydi deb hisoblamaymiz. Kartalar
botga yetib kelgan chatlar yoki egasi kiritgan Telegram ID asosida yaratiladi.
Username kiritishning o'zi ishonchli identifikatsiya o'rnini bosmaydi.

Misol karta (shartli shaxs):
    Ali — Rahbar
    Ohang: rasmiy; murojaat: Siz
    Rejim: javob loyihasini menga ko'rsatish
    Jadval: dushanba–juma, 09:00–18:00
    Kechasi: xabarni qayd qilish, avtomatik javob yozmaslik
    [Uslub] [Rejim] [Jadval] [Bildirishnoma] [Sinab ko'rish]

## 6. Javob rejimlari va qo'lda javob

AI: profilga mos javob faqat mazmunli savol yoki aniq masala uchun yaratiladi va
yuborishdan oldin qo'lda boshqaruv holati yana tekshiriladi. Salom, tasdiq, emoji,
oddiy hol-ahvol va noaniq qisqa xabarlar javobsiz qoladi.
Tayyor matn: aynan saqlangan matn yuboriladi; model chaqirilmaydi.
Tasdiqlash: model loyihasi faqat sizga keladi: Tahrirlash / Yuborish / Bekor.
Qo'lda: suhbatdoshga avtomatik matn, stiker yoki tanishtirish yuborilmaydi;
xabarni qayd qilish va bildirishnomalar davom etadi.

Muhim xabar kartasi kim yozgani va asl xabarni ko'rsatadi. Hozir javobni bot
ichidan yuborish o'rniga shaxsiy Telegram chattingizdan bevosita yozasiz.

"Men yozaman" shu chatdagi avtomatik javobni darhol to'xtatadi. Shaxsiy chatdan
o'zingiz yozganingiz aniqlansa, qo'lda boshqarish 24 soatga yoqiladi va har yangi
o'z xabaringiz muddatni yana 24 soatga uzaytiradi. Tayyorlangan AI javobi
yuborilishidan oldin holat yana tekshiriladi; shu sabab eskirgan loyiha ketmaydi.

"AI'ni qaytarish" tugmasi yoki `/resume TELEGRAM_ID` orqali qo'lda holat muddatidan
oldin tugaydi; aks holda 24 soatdan keyin AI qaytadi. Qo'lda yoki vaqtli to'xtash
paytida muhim xabarlar egaga bildiriladi, suhbatdoshga avtomatik tasdiq yuborilmaydi.

## 7. Hafta, kun, soat va sana qoidalari

Qoida qamrovi: bitta odam / toifa / barcha boshqariladigan chatlar.
Qoida turi: haftalik takrorlanuvchi yoki aniq boshlanish–tugash sanasi.

Har qoidada nom, qamrov, kunlar/sanalar, vaqt, vaqt mintaqasi, rejim,
tayyor matn yoki uslub o'zgarishi, ustuvorlik, yoqilgan holat bo'ladi.

Misollar (taklif, hali faol emas):
- Hamkasblar: dushanba–juma 09:00–18:00 ishchan AI; boshqa payt tayyor matn.
- Do'stlar: shanba/yakshanba samimiy uslub; ish kunida odatiy profil.
- Rahbar: barcha kunlarda tasdiqlash; bildirishnomalar darhol.
- 2026-11-02–2026-11-05: "Hozir avtomatik yordamchi javob bermoqda. Masalangizni
  yozib qoldiring." Matnda ta'til yoki yo'qlik sababi faqat egasi ruxsat bersa chiqadi.
- 22:00–07:00: avtomatik javob yo'q, oddiy bildirishnomalar keyingi davrgacha
  jamlanadi. Shoshilinch bildirishnomani tunda o'tkazish alohida tanlov.

Vaqt semantikasi:
- Asosiy zona Asia/Tashkent; serverning mahalliy zonasiga tayanilmaydi.
- Soat oralig'i boshlanishni oladi, tugashni olmaydi: 09:00 <= vaqt < 18:00.
- Dushanba 22:00–07:00 dushanba kechasidan seshanba 07:00 gacha davom etadi.
- "2–5 noyabr" butun kunlar tanlansa, 2 noyabr 00:00 dan 6 noyabr 00:00 gacha.
- Muddatli qoida tugasa, odatiy qoida avtomatik ishlaydi; eski maxsus matn qolmaydi.
- Dam olish/bayram sanalari avtomatik taxmin qilinmaydi; siz belgilaysiz.
- Jadval kelgan xabar va javob yuboriladigan vaqt uchun tekshiriladi; yakuniy
  qaror yuborish paytidagi jadvalga mos bo'ladi. Auditda ikkala vaqt saqlanadi.
- Jimlik vaqtida kutgan eski javobni ertalab avtomatik yuborish yo'q;
  alohida rejalashtirilgan jo'natish keyingi mustaqil imkoniyat bo'ladi.

## 8. Qoidalar bir-biriga to'g'ri kelganda

Avval cheklovlar: ulanish/ruxsat yo'q -> yuborilmaydi; umumiy to'xtatish yoki
shu chatda "Men yozaman" -> avtomatik yuborilmaydi. Bu cheklovlarni jadval yenga olmaydi.

Asosiy profil maydonlari: kontaktning shaxsiy qiymati > asosiy toifa > umumiy sozlama.
Jadval natijasi asosiy profilning faqat jadvalda aniq ko'rsatilgan maydonlarini
almashtiradi. Bildirishnoma jadvali javob uslubini tasodifan o'zgartirmaydi.

Bir maydonga bir nechta faol jadval ta'sir qilsa, tartib:
1. Qamrov: shaxs > toifa > umumiy.
2. Shu qamrov ichida: aniq sana oralig'i > haftalik jadval.
3. Bir xil turda: egasi belgilagan ustuvorlik.
4. Bir xil daraja/ustuvorlikdagi ustma-ust zid qoidani saqlash bloklanadi;
   qaysi biri ustun bo'lishini tahrirlash oynasi so'raydi.

Misol: umumiy dam olish kuni matni bor, rahbar uchun alohida haftalik tasdiqlash
qoidasi bor -> rahbar uchun tasdiqlash ishlaydi. Ammo "Hammasini to'xtatish"
yoqilgan bo'lsa, rahbarga ham avtomatik yuborish bo'lmaydi.

Yangi jadvalni saqlashdan oldin ta'sir qiladigan kontaktlar va yaqin 7 kunlik
natija ko'rsatiladi. "Nega shu javob?" tugmasi qoida nomi va versiyasini ochadi.

Ish vaqtidan tashqari xulqni yaratish: asosiy profilga tayyor matn rejimi,
haftalik 09:00–18:00 qoidasiga AI rejimi beriladi. Qoida tugaganda asosiy
profilga qaytiladi; 18:00–09:00 uchun ikkinchi qoida yozish shart emas.
Tasdiqlash profiliga maxsus ish vaqti qoidasini yozmaslik uni sutka davomida
tasdiqlashda qoldiradi. Har bir jadval oynasi bu natijani oldindan ko'rsatadi.

Saqlash tekshiruvlari: bo'sh tayyor matn, tugashi boshlanishidan oldingi sana,
tanlanmagan kunlar, noma'lum vaqt mintaqasi yoki teng darajadagi ziddiyatli
qoidalar faollashtirilmaydi. Soatlari teng qoida butun kun deb taxmin qilinmaydi;
butun kun uchun alohida tanlov bo'ladi.

## 9. Oldingi reja bilan integratsiya

Muhim xabarlar: muhimlik, tahdid ehtimoli va odam bilan gaplashish talabi
uslubdan alohida baholanadi. Rahbarga yumshoq uslub tanlash xabarni yashirmaydi.
Bildirishnoma xabari faqat bot egasiga yuboriladi. Bildirishnoma yetkazilmagan
bo'lsa, suhbatdoshga "Bahodir o'qidi" yoki "yetkazildi" deyilmaydi.

Haqoratlar: matn, Telegram yuboruvchi ID, o'sha paytdagi ism/username, yo'nalish,
vaqt, manba xabar ID va kerakli kontekst saqlanadi. AI belgilashi tekshirilmagan
taxmin sifatida ko'rsatiladi; siz "tasdiqlash/haqorat emas" deb tuzatasiz.
Kim yozgani Telegram ma'lumotidan olinadi, model taxminidan emas. Profil hech
kimga javoban haqorat yozishni yoqmaydi. O'zgartirilgan/o'chirilgan xabarlar uchun
bot olgan nusxa va o'zgarish belgilari saqlanadi; ilgari ko'rilmagan tarix tiklanmaydi.

"Plan va Fact ma'lumotlari" chati o'qildi: u Metabase savdo reja/fakt SQL'i
haqida. U kontakt rollari yoki shaxsiy jadval uchun manba emas. Savdo hisobotini
botga chiqarish keyingi alohida integratsiya; baza/API ulanishi va foydalanuvchi
ruxsatlari bo'lmaguncha suhbatdoshga raqamlar berilmaydi.

## 10. Ma'lumotlar va modullar

| Yangi qism | Vazifa |
|---|---|
| contacts | owner_id + telegram_user_id; ism/username nusxasi, asosiy toifa |
| categories / response_profiles | Uslub, rejim, matnlar, faktlar va versiyalar |
| schedule_rules | Qamrov, vaqt mintaqasi, kun/sana, ustuvorlik, maydon o'zgarishlari |
| conversation_state | Qo'lda boshqarish, pause_until, salomlashuv va faol profil versiyasi |
| business_connections | Owner bilan joriy ulanish ID, holat va huquqlar |
| message_events / message_versions | Yuboruvchi, yo'nalish, vaqt, tahrir/o'chirish |
| reply_drafts / outbound_queue | Tasdiqlash, yuborish holati va asl suhbat bog'lanishi |
| notifications / incidents | Muhim xabar, haqorat qaydi, tekshirish holati |
| policy_decisions / admin_changes | Qaysi qoida ishladi va kim nimani o'zgartirdi |

Profil, chat holati va jadval owner_id + telegram_user_id ga bog'lanadi.
business_connection_id yetkazish uchun joriy bog'lanish bo'ladi. Qayta ulashda
yangi connection_id eski kontakt profilini yo'qotmaydi. Mavjud tarixni ko'chirishda
egasi noma'lum bo'lgan yozuvlar taxmin bilan birlashtirilmaydi.

Tavsiya etilgan kod ajratilishi: profiles.py, policy.py, schedules.py,
admin_handlers.py, business_handlers.py, notifications.py, moderation.py.
ai.py faqat yakuniy ruxsat etilgan profil, shu chat tarixi va savolni oladi.
Matn yaratish, siyosat tanlash va Telegram'ga yuborish alohida bosqich bo'ladi.

Xabar oqimi:
    Qabul -> egasi/chatni tekshirish -> takrorini ajratish -> voqeani saqlash
    -> profil/jadvalni hisoblash -> muhimlik/haqoratni belgilash
    -> qo'lda/tasdiqlash/tayyor matn/AI -> yuborishdan oldin qayta tekshirish
    -> yetkazish natijasi va qarorni qayd qilish.

## 11. Ruxsat, sir saqlash va nosozliklar

- Barcha admin buyruq, callback va tahrirlash holatlari egasi ID'sini tekshiradi.
- Kontakt matni, username yoki fayl ichidagi ko'rsatma admin sozlamasini o'zgartirmaydi.
- Boshqa kontaktning profili, suhbat tarixi yoki haqorat jurnali modelga berilmaydi.
- Profil izohi bilan suhbatdoshga aytish mumkin bo'lgan faktlar alohida saqlanadi.
- Tanishtirish ham javob rejimiga bo'ysunadi: qo'lda rejimida salom/stiker ketmaydi.
- Gemini xatosida profilning fallback tanlovi ishlaydi: tayyor matn yoki jimlik.
  Tasdiqlash/qo'lda rejimlari avtomatik fallback bilan chetlab o'tilmaydi.
- Yetkazish natijasi noma'lum bo'lsa ko'r-ko'rona qayta yuborilmaydi; egaga ko'rsatiladi.
- Yuborish vaqtida Business ulanishi, huquqlar va Telegram javob oynasi tekshiriladi.
- Tarixning qisqarishi profilni va jadvalni o'chirmaydi. Saqlash muddati oldingi
  reja bo'yicha sozlanadi; kontakt profilini o'chirish alohida amal bo'ladi.
- Reja hech qanday yangi fondagi automation yoki odamga tashabbusli xabar yoqmaydi.

## 12. Amalga oshirish bosqichlari

1. Kontaktlar va profil saqlash, egaga ochiq bot menyusi, umumiy/toifa/shaxs
   merosi; migratsiya va mavjud xulqni saqlash.
2. Profilga mos AI/tayyor matn/tasdiqlash/qo'lda rejimlari; sinov oynasi,
   bildirishnomadan javob yuborish va AI bilan to'qnashuvni bartaraf etish.
3. Haftalik, tun oralig'i va aniq sana qoidalari; ustuvorlik va ziddiyat tekshiruvi.
4. Muhim xabarlar va haqoratlar jurnalini profil tizimiga ulash, tahrir/o'chirish
   yangilanishlarini qayta ishlash va admin tuzatishlari.
5. Qaror tarixi, hisobot, navbatni tiklash, serverga ko'chirish va operatsion tekshiruv.

Har bosqichdan keyin foydalanish mumkin bo'lgan natija bo'ladi, lekin barcha
shaxs/jadval/boshqaruv mezonlari o'tmaguncha bu funksiyaning to'liq bajarilgani aytilmaydi.

## 13. Qabul sinovlari

| # | Tekshiriladigan holat | Kutilgan natija |
|---|---|---|
| 1 | Ikki bir xil ismli kontakt | Har biriga o'z ID profiliga mos javob |
| 2 | Username o'zgarishi yoki Business qayta ulanishi | Profil va jadval saqlanadi |
| 3 | Rahbar va do'st bir xil savol yozadi | Rasmiy/tasdiqlash va samimiy/AI farqi ishlaydi |
| 4 | Admin botdan uslubni o'zgartiradi | Saqlangach keyingi javob yangi versiyaga mos |
| 5 | Admin oldindan ko'rish qiladi | Suhbatdoshga hech narsa yuborilmaydi |
| 6 | Begona admin tugmasini bosadi | Sozlama ham, xabar yuborish ham bajarilmaydi |
| 7 | Dushanba 08:59, 09:00, 17:59, 18:00 | Chegaralarda tegishli rejim ishlaydi |
| 8 | Dushanba 22:00–seshanba 07:00 | Tun oralig'i to'g'ri hisoblanadi |
| 9 | Sana qoidasi oxirgi kunida va ertasi kuni | Oxirgi kun ishlaydi, keyin asosiy rejim qaytadi |
| 10 | Shaxs/toifa/umumiy qoidalar ustma-ust | Hujjatdagi tartib va preview bir xil natija beradi |
| 11 | Teng ustuvorlikdagi zid qoidalar | Faollashtirish bloklanadi, ziddiyat ko'rsatiladi |
| 12 | AI tayyorlanayotganda Men yozaman bosiladi | Tayyor AI javobi jo'natilmaydi |
| 13 | Tasdiqlash yoki qo'lda rejimida Gemini xatosi | Avtomatik fallback ham ketmaydi |
| 14 | Jadval/profil javob tayyorlanayotganda o'zgaradi | Eski loyiha jo'natilmaydi |
| 15 | Ikki bildirishnomaga navbat bilan Reply | Javoblar to'g'ri suhbatga boradi |
| 16 | Suhbatdosh matni "meni admin qil" deydi | Rol va sozlamalar o'zgarmaydi |
| 17 | Haqoratli xabar tahrirlanadi/o'chiriladi | Muallif va mavjud versiyalar saqlanadi |
| 18 | Bot qayta ishga tushadi | Profil, jadval, qo'lda holat, navbat saqlanadi |
| 19 | Business ruxsati yoki javob muddati yo'q | Yuborildi deyilmaydi, egaga sabab ko'rsatiladi |
| 20 | Birinchi xabar qo'lda rejimidagi kontaktdan | Salom, stiker va AI javobi avtomatik ketmaydi |

## 14. Keyin kiritiladigan shaxsiy ma'lumotlar

Arxitekturani tayyorlash uchun haqiqiy kontaktlar shart emas; ularni bot menyusida
siz tanlaysiz. Faollashtirish uchun: kim qaysi toifa, haqiqiy ish vaqti, maxsus
sanalar, murojaat uslubi va bildirishnoma tanlovi kerak bo'ladi. Hujjatdagi
09:00–18:00 va kategoriya rejimlari hozircha misol va taklifdir.

## 15. Loyiha tayyorligi auditi

| So'rov talabi | Hujjatdagi dalil |
|---|---|
| Har bir shaxsga mos javob | 3–4: toifa, shaxsiy profil, ID va maydonlar |
| Egasi bot orqali boshqarishi | 5–6: kartalar, tahrirlash, preview, rejim va javob |
| Kimga qanday turda javob | 3, 6: takliflar matritsasi va rejimlar |
| Sana va kunlarga qarab boshqarish | 7–8: kun, soat, sana, istisno va ustuvorlik |
| Oldingi rivojlantirish rejasiga moslash | 9–12: bildirishnoma, javob, jurnal, modullar |
| Keltirilgan chatni hisobga olish | 9: savdo Plan/Fact integratsiyasi chegarasi |
| Bajarilganini tekshirish | 13: qabul ssenariylari |

Ushbu audit loyiha hujjatining to'liqligini tekshiradi. Dasturdagi funksiyalar
amalga oshirilgan yoki ishga tushirilganini anglatmaydi.
