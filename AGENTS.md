# Repository Guidelines

## Project Structure & Module Organization

This is a Django 6 REST API. Global configuration lives in `config/`; domain code is grouped under `apps/`:

- `accounts/`: users, JWT/session authentication, OTP, and Google sign-in
- `clubs/`: clubs, branches, zones, tariffs, permissions, and serializers
- `bookings/`, `payments/`, `reviews/`, and `audit/`: supporting business domains
- `core/`: shared endpoints, messages, translations, and management commands

Keep domain logic in its owning app. Put reusable operations in `services/`, API routing in `urls.py`, and schema changes in `migrations/`. Do not commit generated media, `__pycache__/`, `.venv/`, or local database changes.

## Build, Test, and Development Commands

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Use `python manage.py migrate` to apply migrations and `python manage.py runserver` to serve the API locally. Run `python manage.py check` before submitting changes. API documentation is available at `/api/docs/` and `/api/redoc/`. Seed translated system messages with `python manage.py seed_system_messages`.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation. Use `snake_case` for functions, variables, and modules; `PascalCase` for classes; and uppercase names for settings/constants. Prefer double quotes in new code where practical, matching the newer modules. Keep views thin, move external integrations and multi-step workflows into `services/`, and use explicit, descriptive migration names such as `0012_normalize_branch_locations.py`.

No formatter or linter is configured. Group imports as standard library, third-party, then local packages.

## Testing Guidelines

The project currently has no committed test suite or coverage threshold. Add Django tests beside each domain as `apps/<app>/tests.py` or `apps/<app>/tests/test_<feature>.py`. Name test methods `test_<expected_behavior>`. Cover authentication, permissions, validation, and model/service edge cases. Run all tests with `python manage.py test`, or target one app with `python manage.py test apps.clubs`.

## Commit & Pull Request Guidelines

Repository history is not available in this checkout, so no existing commit convention can be verified. Use short, imperative subjects (for example, `Add branch availability validation`) and keep each commit focused. Pull requests should explain the behavior change, list migrations and configuration changes, link the relevant issue, and include test results. Add screenshots or sample request/response payloads when API documentation or visible behavior changes.

## Security & Configuration

Never commit `.env`, credentials, OAuth secrets, production databases, or tokens. New secrets must come from environment variables and be documented with safe placeholder values. Treat `db.sqlite3` as local development data.
