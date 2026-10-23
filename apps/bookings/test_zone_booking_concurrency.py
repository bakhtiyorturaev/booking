"""Concurrency regression test for zone-based double booking.

create_hold() (apps/bookings/services.py) takes select_for_update() on the
Zone row before checking remaining capacity, which should serialize two
concurrent holds for the same zone+slot on a real database (PostgreSQL in
production). This fires two near-simultaneous create_hold() calls for a
single-seat zone and asserts at most one HELD hold ever exists for that
slot. See apps/bookings/test_concurrency.py for the equivalent barber-side
test and its notes on SQLite's shared-cache locking quirks in this test
runner (select_for_update() is a no-op on SQLite).
"""

import threading
import time as time_module
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import OperationalError, connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import BookingHold
from apps.bookings.services import create_hold
from apps.clubs.models import Branch, City, Club, Zone


def _retry_on_sqlite_table_locked(fn, max_attempts=25, base_delay=0.01):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            last_error = error
            time_module.sleep(base_delay * (attempt + 1))
    raise last_error


class CreateHoldConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.city = City.objects.create(name="QA Zone City", slug="qa-zone-city")
        self.owner = User.objects.create_user(
            username="qa_zone_owner", phone="+998901240001", role=User.Role.CLIENT,
        )
        self.club = Club.objects.create(
            name="QA Zone Club", slug="qa-zone-club",
            category=Club.Category.GAMING_CLUB, owner=self.owner, status=Club.Status.ACTIVE,
        )
        self.branch = Branch.objects.create(
            club=self.club, name="Main", city=self.city, address="Test address",
            latitude="41.0", longitude="69.0", status=Branch.Status.ACTIVE, is_24_hours=True,
        )
        # Single-seat zone: at most one of the two racing customers may win.
        self.zone = Zone.objects.create(
            branch=self.branch, name="Single PC", capacity=1,
            booking_type=Zone.BookingType.PER_SEAT, unit_count=1,
            price_per_hour_tiyin=10_000,
        )
        self.customer_a = User.objects.create_user(username="qa_zone_cust_a", phone="+998901240002")
        self.customer_b = User.objects.create_user(username="qa_zone_cust_b", phone="+998901240003")

        tomorrow = timezone.localdate() + timedelta(days=1)
        self.starts_at = timezone.make_aware(datetime.combine(tomorrow, time(10, 0)))
        self.ends_at = self.starts_at + timedelta(hours=1)

    def test_concurrent_create_hold_does_not_oversell_single_seat_zone(self):
        results = {}
        barrier = threading.Barrier(2, timeout=10)

        def attempt(label, user):
            try:
                barrier.wait()
                hold = _retry_on_sqlite_table_locked(
                    lambda: create_hold(user, self.zone.id, self.starts_at, self.ends_at, quantity=1)
                )
                results[label] = ("ok", str(hold.id))
            except ValidationError as error:
                results[label] = ("rejected", f"{error.code}: {error}")
            except Exception as error:  # noqa: BLE001
                results[label] = ("error", f"{type(error).__name__}: {error}")
            finally:
                connection.close()

        t1 = threading.Thread(target=attempt, args=("a", self.customer_a))
        t2 = threading.Thread(target=attempt, args=("b", self.customer_b))
        t1.start()
        t2.start()
        t1.join(timeout=20)
        t2.join(timeout=20)

        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())

        held_count = BookingHold.objects.filter(
            zone=self.zone,
            status=BookingHold.Status.HELD,
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        ).count()
        self.assertLessEqual(
            held_count, 1,
            f"Expected at most one HELD hold for a 1-seat zone, found {held_count}. "
            f"Thread results: {results}",
        )

        statuses = {label: value[0] for label, value in results.items()}
        self.assertNotIn("error", statuses.values(), results)
        self.assertEqual(sorted(statuses.values()), ["ok", "rejected"], results)
