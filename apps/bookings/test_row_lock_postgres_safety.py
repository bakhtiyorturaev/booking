"""PostgreSQL row-lock xavfsizligi: `select_for_update()` + nullable `select_related()`.

NEGA BU TEST KERAK
------------------
Django hujjatlarida aniq yozilgan: `select_for_update()` ni nullable
(null=True) bog'lanish bilan `select_related()` qilinganda ishlatish
PostgreSQL'da **ishlamaydi**:

    django.db.utils.NotSupportedError:
    FOR UPDATE cannot be applied to the nullable side of an outer join

SQLite'da `select_for_update()` jimgina e'tiborsiz qoldiriladi
(`connection.features.has_select_for_update is False`), shuning uchun bu xato
lokal test bazasida **hech qachon** ko'rinmaydi — faqat productionda
(DB_ENGINE=postgresql) chiqadi.

Shu sababli bu test SQL emas, **manba kodini** tekshiradi: har bir
`select_for_update(...)` chaqiruvi `select_related(...)` bilan zanjirlanganda
`of=(...)` argumenti ko'rsatilgan bo'lishi shart. `of=("self",)` faqat asosiy
jadval qatorini bloklaydi va outer join muammosini butunlay yo'q qiladi.

Hozircha buzilgan joylar (2026-10-23):
  * apps/bookings/services.py::create_booking      (BookingHold -> zone nullable)
  * apps/reviews/services.py::create_review        (Booking -> zone/barber nullable)
  * apps/payments/barber_billing.py::record_barber_payment (Barber -> branch nullable)
  * telegram_bot/services.py::confirm_booking / cancel_booking_from_telegram
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

PROJECT_ROOT = Path(settings.BASE_DIR)
SCANNED_PACKAGES = ("apps", "telegram_bot")

# `select_for_update(...)` dan keyin xuddi shu ifodada `select_related(` kelsa,
# Django FOR UPDATE ni butun JOIN ga qo'llaydi. Zanjir bir necha qatorga
# bo'linishi mumkin, shuning uchun butun fayl matni bo'yicha izlaymiz.
CHAINED_LOCK = re.compile(
    r"select_for_update\((?P<args>[^)]*)\)"
    r"(?P<between>(?:\s*\.\s*\w+\([^()]*\))*?)"
    r"\s*\.\s*select_related\(",
    re.DOTALL,
)


def _python_sources():
    for package in SCANNED_PACKAGES:
        for path in (PROJECT_ROOT / package).rglob("*.py"):
            parts = set(path.parts)
            if "migrations" in parts or path.name.startswith("test_"):
                continue
            yield path


class SelectForUpdateOuterJoinSafetyTests(SimpleTestCase):
    def test_every_locking_query_with_select_related_scopes_the_lock(self):
        offenders = []
        for path in _python_sources():
            source = path.read_text(encoding="utf-8")
            for match in CHAINED_LOCK.finditer(source):
                if "of=" in match.group("args"):
                    continue
                line_number = source.count("\n", 0, match.start()) + 1
                snippet = " ".join(match.group(0).split())[:120]
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{line_number}: {snippet}"
                )

        self.assertEqual(
            offenders,
            [],
            "select_for_update() + select_related() uchun `of=(...)` majburiy, aks holda "
            "PostgreSQL `FOR UPDATE cannot be applied to the nullable side of an outer join` "
            "xatosini beradi:\n  " + "\n  ".join(offenders),
        )


class LockedQuerysetShapeTests(SimpleTestCase):
    """`of=("self",)` bilan yozilgan so'rovlar hali ham faqat bitta jadvalni bloklaydi."""

    def test_booking_lock_with_of_self_is_outer_join_safe(self):
        from apps.bookings.models import Booking

        queryset = Booking.objects.select_for_update(of=("self",)).select_related(
            "zone__branch__club", "barber__club"
        )
        # of=("self",) => FOR UPDATE OF "bookings" — outer join qatorlari bloklanmaydi.
        self.assertEqual(queryset.query.select_for_update_of, ("self",))
