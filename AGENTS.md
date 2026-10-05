# Repository Guidelines

## Project Purpose
**Club Booking Platform** — a full-stack SaaS for booking venues: PlayStation/computer clubs, gyms, barber shops, and halls. Supports subscriptions, payments, reviews, Telegram Mini App, and a management cabinet.

---

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Django 6, Django REST Framework, SimpleJWT, drf-spectacular |
| Database | PostgreSQL 16 (prod) / SQLite (dev) |
| Cache | Redis 7 |
| Frontend | Nuxt 4 (Vue 3 + TypeScript), Vite, FontAwesome |
| Auth | Telegram OAuth / Mini App login; JWT (access + refresh) |
| Payments | Click / Payme / Manual (pluggable via `PAYMENT_PROVIDER`) |
| Bot | python-telegram-bot (management command `run_telegram_bot`) |
| Static | WhiteNoise; Gunicorn (prod); multi-stage Docker |
| CAPTCHA | Cloudflare Turnstile |
| Docs | `/api/docs/` (Swagger) · `/api/redoc/` · `/api/schema/` |

---

## High-Level Architecture
```
Browser / Telegram Mini App
       │
       ▼
Nuxt 4 Frontend (port 3000)
       │  SSR + client-side calls to /api/v1/
       ▼
Django 6 REST API (port 8000)
       │
       ├── PostgreSQL (persistent data)
       ├── Redis (cache / sessions)
       └── Telegram Bot (separate process / Docker service)
```

---

## Directory Map
```
booking/
├── config/            # Django project config (settings, urls, wsgi, asgi)
├── apps/
│   ├── accounts/      # Custom User model, JWT auth, Telegram login
│   ├── clubs/         # Club, Branch, Zone, Tariff, OperatingHours, images
│   ├── barbers/       # Barber profiles, schedules, affiliate links
│   ├── bookings/      # Booking, BookingHold, availability logic
│   ├── payments/      # Payment, SubscriptionPlan, webhook, checkout
│   ├── reviews/       # Review CRUD (public + cabinet)
│   ├── audit/         # AuditLog model + AuditMiddleware (async-capable)
│   ├── core/          # Translations, system messages, dashboard stats
│   └── developer_bot/ # Internal developer/ops Telegram bot
├── telegram_bot/      # User-facing Telegram bot (handlers, services, models)
├── frontend/
│   ├── app/
│   │   ├── pages/     # Nuxt file-based routing
│   │   ├── api/       # TS API client modules (auth, clubs, bookings, …)
│   │   ├── components/
│   │   ├── composables/
│   │   ├── layouts/
│   │   ├── middleware/ # Route guards (auth, role checks)
│   │   ├── plugins/
│   │   └── types/
│   └── server/        # Nuxt server routes (SSR)
├── load_tests/        # Locust load test scenarios
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Backend App Responsibilities
| App | Key Models / Concepts |
|---|---|
| `accounts` | `User` (UUID PK, roles: CUSTOMER/MODERATOR/ADMIN), Telegram login flow, JWT tokens, cabinet user management |
| `clubs` | `Club`, `Branch`, `Zone`, `BranchImage`, `OperatingHour`, `SpecialSchedule`, `ResourceBlock`, `Favorite`, City/District |
| `barbers` | `Barber`, barber availability, affiliate links, status |
| `bookings` | `Booking`, `BookingHold` (temp slot reservation), branch availability API |
| `payments` | `Payment`, `SubscriptionPlan`, `Subscription`, checkout + webhook endpoints |
| `reviews` | `Review` (tied to Club); public listing + cabinet moderation |
| `audit` | `AuditLog` auto-populated via middleware on every mutating request; async optional (`AUDIT_ASYNC`) |
| `core` | `AppTranslation`, `SystemMessage`; management commands for seeding; dashboard stats |
| `developer_bot` | Internal ops bot for developer notifications |
| `telegram_bot` | User-facing bot: booking flow, club search, Mini App bridge |

---

## Frontend Structure
- **Pages** (`frontend/app/pages/`): `index.vue` (home), `bookings.vue`, `profile.vue`, `clubs/`, `branches/`, `admin/`, `login/`, `register/`, `forgot-password/`
- **API modules** (`frontend/app/api/`): `auth.ts`, `clubs.ts`, `branches.ts`, `bookings.ts`, `barbers.ts`, `reviews.ts`, `payments.ts`, `favorites.ts`, `subscription.ts`, `translations.ts`, `admin.ts`, `client.ts`
- **Composables** handle auth state, locale, and shared fetch wrappers
- **Middleware** enforces auth guards on protected pages
- API base: `NUXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000/api/v1`)

---

## API Structure (`/api/v1/`)
| Prefix | Description |
|---|---|
| `auth/telegram/`, `auth/telegram-miniapp/`, `auth/telegram-web/` | Telegram login variants |
| `auth/me/`, `auth/token/refresh/`, `auth/logout/` | Session management |
| `clubs/`, `branches/` | Public venue discovery |
| `locations/cities/`, `locations/districts/` | Location lookup |
| `favorites/` | User favourites |
| `barbers/` | Public barber profiles; `barbers/me/` for self-management |
| `branches/<uuid>/availability/` | Slot availability check |
| `booking-holds/`, `bookings/` | Booking flow |
| `reviews/`, `clubs/<uuid>/reviews/` | Reviews |
| `subscriptions/plans/`, `subscriptions/me/` | Subscription |
| `payments/`, `payments/checkout/`, `payments/webhook/` | Payments |
| `cabinet/*` | Owner/admin management (clubs, branches, zones, bookings, reviews, payments, users, barbers, stats) |

---

## Auth & Roles
- **Authentication**: Telegram-only login (no email/password). Issues `access` + `refresh` JWT tokens.
- **Roles** (`User.Role`): `CUSTOMER` (default), `MODERATOR`, `ADMIN`
- **Platform admin**: `is_staff`, `is_superuser`, or role `ADMIN`/`MODERATOR`
- **Club operators**: club `owner_id == user.id` or platform admin
- **Permission classes**: `IsClubOperator`, `IsOwnerOrPlatformAdmin` in `apps/clubs/permissions.py`
- Cabinet endpoints require club ownership or platform admin role

---

## Database & Cache
- **Dev**: SQLite (no `DB_ENGINE` set), no Redis needed (falls back to DB cache)
- **Prod**: PostgreSQL 16 + Redis 7
- All PKs are UUIDs. Migrations live in each app's `migrations/` directory.
- Use explicit, descriptive migration names (e.g., `0012_normalize_branch_locations.py`)

---

## Telegram Bot
- Entry: `telegram_bot/` — `handlers.py` (command/callback handlers), `services.py` (business logic), `client.py` (HTTP client to backend), `models.py` (bot-side state)
- Run locally: `python manage.py run_telegram_bot`
- Env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_MINIAPP_URL`
- Mini App login via `auth/telegram-miniapp/` endpoint

---

## Docker Services
| Service | Image / Build | Port | Purpose |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Cache |
| `backend` | Dockerfile (root) | 8000 | Django API (Gunicorn, 3 workers) |
| `telegram_bot` | Dockerfile (root) | — | `run_telegram_bot` management command |
| `frontend` | frontend/Dockerfile | 3000 | Nuxt SSR frontend |

---

## Development Commands

### Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_system_messages
python manage.py seed_app_translations
python manage.py seed_demo_clubs      # optional demo data
python manage.py seed_barbers         # optional demo barbers
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
python manage.py run_telegram_bot     # optional bot
```

### Frontend
```bash
cd frontend && npm install
npm run dev         # http://localhost:3000
npm run typecheck
npm run lint
npm run build
```

### Docker (all services)
```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f
```

### Tests & Checks
```bash
python manage.py test               # all Django tests (76 tests)
python manage.py test apps.clubs    # single app
python manage.py check              # Django system check
cd frontend && npm run typecheck && npm run lint
```

### Production
```bash
python manage.py collectstatic --noinput
# Set: DJANGO_DEBUG=false, DJANGO_SECRET_KEY, DJANGO_SECURE_SSL_REDIRECT=true
```

---

## Important Conventions
- **Style**: PEP 8, 4-space indent, `snake_case` functions/modules, `PascalCase` classes, prefer double quotes
- **Views**: Keep thin — move external integrations and multi-step logic into `services/`
- **Migrations**: Explicit descriptive names; always run `python manage.py check` before submitting
- **Secrets**: Never commit `.env`, credentials, or tokens; use environment variables
- **Translations**: DB-backed via `AppTranslation`; seed with `seed_system_messages` and `seed_app_translations`
- **Cabinet prefix**: All owner/admin management endpoints use the `cabinet/` URL prefix
- **Public vs cabinet serializers**: `clubs/` has both `serializers.py` (cabinet) and `public_serializers.py`
- **Tests**: `apps/<app>/tests.py` or `apps/<app>/tests/test_<feature>.py`; method names: `test_<expected_behavior>`

---

## Files / Areas Requiring Caution
- `config/settings.py` — central config; security flags auto-enable in prod (SSL redirect, secure cookies)
- `apps/audit/middleware.py` — fires on every mutating request; avoid adding heavy synchronous logic
- `apps/payments/` — webhook secret validation; don't break `PAYMENT_WEBHOOK_SECRET` checks
- `apps/clubs/models.py` (21 KB) — many inter-related models; always check migrations after edits
- `apps/clubs/views.py` (38 KB) — very large; use targeted search, not full read
- `telegram_bot/services.py` (26 KB) — core bot business logic; large file, search before reading
- `PAYMENT_PROVIDER` setting (`manual`/`http`) controls checkout flow

---

## AI Working Rules (Minimize Token Usage)
1. **Don't scan**: `migrations/`, `__pycache__/`, `media/`, `staticfiles/`, `node_modules/`, `.git/`
2. **Start targeted**: read `config/urls.py` to locate an app, then its `urls.py` → `views.py` → `models.py`
3. **Large files**: use `StartLine`/`EndLine` on `views.py` (38 KB) and `services.py` (26 KB); `grep_search` first
4. **API exploration**: check `frontend/app/api/` TS modules for quick endpoint reference without reading DRF views
5. **Models first**: read `models.py` before `serializers.py` or `views.py` to understand data shape
6. **Permissions**: role logic lives in `apps/clubs/permissions.py` and `apps/accounts/models.py` (Role enum)
7. **Settings**: all env-driven config is in `config/settings.py`; read once per session
8. **Cabinet access**: search for `cabinet/` prefix in `urls.py` to find all admin-only endpoints
