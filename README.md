# Club Booking Platform

Zamonaviy klublar, zallar, PlayStation/kompyuter klublari va barberlar uchun to‘liq funksional bron qilish (booking), to‘lovlar va boshqaruv platformasi.

---

## Arxitektura (Tech Stack)

- **Backend:** Django 6 REST Framework (DRF), SimpleJWT, DRF Spectacular (Swagger/OpenAPI), Postgres / SQLite, Redis, Cryptography
- **Frontend:** Nuxt 4 (Vue 3 + TypeScript), Vite, Tailwind / Vanilla CSS, FontAwesome
- **Integratsiyalar:** Telegram Bot & Mini App (TMA), SMS OTP, To‘lov tizimlari (Click/Payme/Manual), Cloudflare Turnstile
- **DevOps:** Docker, Docker Compose, Gunicorn, Multi-stage builds

---

## Tezkor Boshlash (Local Development)

Loyihani istalgan yangi kompyuterda yoki muhitda 2 xil usulda ishga tushirish mumkin:
1. **Standart (Manual) usul** (Python & Node.js)
2. **Docker Compose usul** (Barcha xizmatlar 1 ta buyruq bilan)

---

### 1-usul: Standart Ishga Tushirish (Manual Setup)

#### A. Backend (Django)

1. **Virtual muhit yaratish va faollashtirish:**
   ```powershell
   # Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Kutubxonalarni o‘rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfiguratsiya faylini yaratish:**
   ```bash
   # .env.example faylidan nusxa oling:
   cp .env.example .env
   ```
   *(Standart holatda `.env` local SQLite va test qiymatlari bilan darhol ishlashga sozlangan).*

4. **Migratsiyalarni qo‘llash va ma'lumotlarni to‘ldirish (Seed):**
   ```bash
   python manage.py migrate
   python manage.py seed_app_translations
   python manage.py seed_system_messages
   python manage.py seed_demo_clubs
   python manage.py seed_barbers
   ```

5. **Superadmin foydalanuvchi yaratish:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Serverni ishga tushirish:**
   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```
   - **Swagger API Docs:** `http://127.0.0.1:8000/api/docs/`
   - **Django Admin:** `http://127.0.0.1:8000/admin/`

---

#### B. Frontend (Nuxt 4)

1. **Frontend papkasiga o‘tish va bog‘liqliklarni o‘rnatish:**
   ```bash
   cd frontend
   npm install
   ```

2. **Ishlab chiqish rejimida ishga tushirish:**
   ```bash
   npm run dev
   ```
   - **Mijoz Web Ilovasi:** `http://localhost:3000`

3. **Frontend tekshiruvlari (Lint & Typecheck):**
   ```bash
   npm run typecheck
   npm run lint
   npm run build
   ```

---

#### C. Telegram Bot (Ixtiyoriy)

Agar Telegram Mini App yoki bot orqali bron qilish xususiyatlarini sinab ko‘rmoqchi bo‘lsangiz:
1. `.env` faylida `TELEGRAM_BOT_TOKEN` va `TELEGRAM_BOT_USERNAME` ni kiriting.
2. Botni ishga tushiring:
   ```bash
   python manage.py run_telegram_bot
   ```

---

### 2-usul: Docker & Docker Compose orqali Ishga Tushirish

Agar kompyuteringizda yoki serverda Docker o‘rnatilgan bo‘lsa, barcha xizmatlar (PostgreSQL, Redis, Django API, Nuxt Frontend) avtomatik tarzda ko‘tariladi:

```bash
# 1. Konfiguratsiya faylini tayyorlang
cp .env.example .env

# 2. Barcha xizmatlarni bir vaqtda ishga tushiring
docker compose up --build -d

# 3. Loglarni kuzatish
docker compose logs -f
```

- **Frontend:** `http://localhost:3000`
- **Backend API & Swagger:** `http://localhost:8000/api/docs/`

---

## Muhit O‘zgaruvchilari (Environment Variables)

Asosiy sozlamalar `.env` orqali dinamik boshqariladi:

| O‘zgaruvchi | Tavsif | Local Default | Production Misol |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Django xavfsizlik kaliti | *(dev fallback)* | *Uzoq tasodifiy satr* |
| `DJANGO_DEBUG` | Debug rejimi | `true` | `false` |
| `DJANGO_ALLOWED_HOSTS` | Ruxsat etilgan hostlar | `127.0.0.1,localhost` | `api.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSRF ishonchli domenlar | `http://localhost:3000` | `https://example.com` |
| `CORS_ALLOWED_ORIGINS` | CORS ruxsat etilgan URLlar | `http://localhost:3000` | `https://example.com` |
| `DB_ENGINE` | Ma'lumotlar bazasi drayveri | *(bosh - SQLite)* | `postgresql` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL parametrlari | - | `club_db, db_user, ...` |
| `DB_HOST`, `DB_PORT` | PostgreSQL host & port | `127.0.0.1:5432` | `postgres:5432` |
| `REDIS_URL` | Redis kesh manzili | *(bosh - DB cache)* | `redis://redis:6379/1` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot tokeni | `""` | `123456:ABC-DEF...` |
| `NUXT_PUBLIC_API_BASE_URL` | Frontend API manzili | `http://127.0.0.1:8000/api/v1` | `https://api.example.com/api/v1` |

---

## Testlarni Ishga Tushirish

Backend va Frontend uchun to‘liq testlar:

```powershell
# Django testlari (76 ta test):
python manage.py test

# Frontend TypeScript va Linter tekshiruvi:
cd frontend
npm run typecheck
npm run lint
```

---

## Production Deployment Tavsiyalari

1. `.env` faylida `DJANGO_DEBUG=false` qilib belgilang.
2. `DJANGO_SECRET_KEY` uchun kuchli maxfiy kalit o‘rnating.
3. `DJANGO_SECURE_SSL_REDIRECT=true`, `DJANGO_SESSION_COOKIE_SECURE=true`, `DJANGO_CSRF_COOKIE_SECURE=true` qilib xavfsizlikni kuchaytiring.
4. Statik fayllarni yig‘ish: `python manage.py collectstatic --noinput`.
5. Nginx reverse proxy va SSL sertifikati (Certbot/Let's Encrypt) orqali `8000` (Backend) va `3000` (Frontend) portlarini yo‘naltiring.
