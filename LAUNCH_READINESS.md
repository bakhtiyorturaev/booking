# Ishga tushirish

## Loginlar

- `/site/superuser/admin/`: Django superuser; o‘z session va CSRF cookie’si, faqat admin yo‘liga yuboriladi.
- `/site/staff/login`: xodim, alohida access/refresh cookie.
- `/site/client/login`: xizmat egasi yoki sartarosh, alohida access/refresh cookie.
- `/login`: oddiy foydalanuvchi, alohida Telegram sessiyasi.

Bitta brauzerda bu loginlar birga ishlashi mumkin; bittasidan chiqish qolganini o‘chirmaydi. Oldingi umumiy cookie’lar yangi login uchun ishlatilmaydi; foydalanuvchilar qayta kiradi.

Saytda Telegram orqali kirish botga maxsus havola beradi. Bot shaxsiy chatdagi `/start auth_...` orqali 5 raqamli kod beradi. Kod berilgan paytdan 60 soniya ishlaydi, sayt sessiyasiga bog‘langan, faqat bir marta ishlatiladi va 5 noto‘g‘ri urinishdan keyin yaroqsiz bo‘ladi. Botdagi Mini App Telegram imzolagan `initData` orqali kiradi.

## Jonli server sozlamalari

1. PostgreSQL, Redis va haqiqiy HTTPS domenini tayyorlang. SQLite parallel bronlarda kerakli qator qulflarini bermaydi.
2. `DJANGO_DEBUG=false`, kuchli `DJANGO_SECRET_KEY` va superuser paroli, `DJANGO_SECURE_SSL_REDIRECT=true`; HTTPS xavfsizlik sozlamalarini haqiqiy reverse proxy bilan tekshiring.
3. `FRONTEND_URL`, `TELEGRAM_MINIAPP_URL` ni haqiqiy HTTPS domeniga sozlang. `TELEGRAM_BOT_USERNAME` va tokenni sozlang; token Django admin → Telegram bot settings yoki muhit orqali beriladi.
4. Reverse proxy foydalanuvchi yuborgan `X-Forwarded-For` va `X-Forwarded-Proto` ni almashtirsin. Faqat shu ishonchli proxy ortida `NUXT_TRUST_PROXY_HEADERS=true` va `DJANGO_USE_X_FORWARDED_PROTO=true` yoqing. Backendni ommaga to‘g‘ridan-to‘g‘ri ochmang. Bu HTTPS va foydalanuvchi IP bo‘yicha limitlar uchun kerak.
5. `manage.py migrate`, `seed_system_messages`, `collectstatic --noinput` bajaring. Bot jarayonini ham ishga tushiring (`run_telegram_bot` yoki Docker bot servisi).
6. `.venv/bin/python manage.py check_launch_readiness` va `manage.py check --deploy` bajaring; `.env` va tokenlarni repozitoriyga qo‘shmang.
7. Haqiqiy Telegram akkauntida kod bilan kirish va Mini App’ni, ikki foydalanuvchi bilan bir vaqtga bron urinishini, bekor qilish va kelganini tasdiqlashni tekshiring.

To‘lov integratsiyasi talab qilinmaydi. Har bir filial/sartarosh uchun bepul/pullik rejim va alohida muassasa/sartarosh hisoblari [MANUAL_BILLING.md](MANUAL_BILLING.md) da.

Lokal avtomatik sinovlar haqiqiy bot tokeni, domen sertifikati yoki jonli PostgreSQL serverini tekshirish o‘rnini bosmaydi.

## Lokal tekshiruv natijasi

- 149 ta Django test o‘tdi; `check` xatosiz, yangi migratsiya talab qilinmaydi.
- Nuxt typecheck va production build o‘tdi. ESLint: 0 xato, 162 ogohlantirish.
- Playwright: bitta brauzerda staff/client/customer/Django admin sessiyalari, SSR sahifa yangilanishi, alohida logout, filial/sartarosh uchun alohida bepul checkboxlar, sartarosh jadvalini saqlash va begona Origin’dan yozishni rad etish tekshirildi. 1440, 390 va 320 px ekranlarda tekshirilgan sahifalar sig‘di.
- Telegram kodi serverda sinov ma’lumotlari bilan yaratilgan va haqiqiy verify endpoint orqali kiritilgan; haqiqiy Telegram tarmog‘i/tokeni tekshirilmagan.
- Vaqtinchalik browser akkauntlari va kodlari olib tashlandi. Lokal frontend `localhost:3000` da tayyor build bilan ishlamoqda.
- Jonli konfiguratsiya tekshiruvi hali bot tokeni/username, HTTPS URL’lar, DEBUG/SECRET_KEY/SSL/cookie sozlamalari, PostgreSQL va kuchli superuser paroli talab qilmoqda.
