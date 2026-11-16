"""
Additive QA probe for concurrency safety of create_barber_booking().

This file is purely additive -- it does not modify or weaken any existing
test, and it does not change any application logic. It exists to give the
"create_barber_booking double-booking under concurrency" finding an
executable regression test.

IMPORTANT CAVEAT -- READ BEFORE TRUSTING A GREEN RUN HERE:

apps/bookings/services.py::create_barber_booking (lines ~417-442) wraps its
work in @transaction.atomic and calls select_for_update() on both the User
row and the Barber row *before* checking availability and creating the
Booking. On PostgreSQL this correctly serializes two concurrent requests for
the same barber+slot: the second transaction blocks on the row lock until
the first commits, then re-reads availability and (correctly) rejects the
now-taken slot.

On SQLite -- which is what `manage.py test` runs against locally -- Django
documents select_for_update() as a *silent no-op*. This is literally what
apps/payments/management/commands/check_launch_readiness.py already checks
for via `connection.features.has_select_for_update` and raises a launch
blocker about. So select_for_update() itself is NOT providing any protection
in this test run; any serialization observed here comes from SQLite's own,
unrelated locking, not from the code under test.

QA INVESTIGATION LOG (2026-10-10): this test was run standalone 10 times to
check for flakiness. Result: 6/10 passed, 4/10 failed -- but EVERY failure
had the exact same signature: BOTH threads raised
`django.db.utils.OperationalError: database table is locked` (zero bookings
created in any failing run), never a double-booking. Root cause: Django's
test runner here uses an in-memory, SHARED-CACHE SQLite database
(`file:memorydb_default?mode=memory&cache=shared` -- visible in the test
runner's own "Creating test database..." log line). Under SQLite's
shared-cache mode, two separate connections writing to the same table can
raise SQLITE_LOCKED ("database table is locked") *immediately*, which is a
DIFFERENT error code from SQLITE_BUSY ("database is locked", no "table" in
the message) and is NOT retried by the normal busy_timeout/busy-handler
mechanism. This is a well-documented SQLite shared-cache quirk specific to
this in-memory test-DB mode -- it is not how a real on-disk SQLite file
behaves, and it has nothing to do with PostgreSQL in production. In 10/10
runs the actual business invariant this test cares about (at most one
CONFIRMED booking for the same barber+slot) held perfectly; the only
instability was this unrelated test-harness-level infra error occasionally
starving BOTH attempts before either could reach the business logic at all.
`_call_with_sqlite_shared_cache_lock_retry` below retries ONLY that specific
SQLITE_LOCKED error, at the test-harness level, so both threads reliably
reach a REAL outcome (a created booking, or a clean
`bookings.zone_not_available` rejection) instead of occasionally bailing out
on infrastructure noise. This retry wrapper does not touch, patch, or relax
any application code -- it only makes the test's own thread-orchestration
robust against a SQLite-only, shared-cache-only artifact.

See reports/01_backend_test_results.md for the full writeup, including
whether a Postgres re-run via docker-compose was also attempted for this
test.
"""

import threading
import time as time_module
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import OperationalError, connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.bookings.models import Booking
from apps.bookings.services import create_barber_booking
from apps.clubs.models import Branch, City, Club


def _call_with_sqlite_shared_cache_lock_retry(fn, max_attempts=25, base_delay=0.01):
    """Test-harness-only retry helper (NOT application code).

    Retries ONLY `OperationalError`s whose message contains "locked" --
    i.e. SQLite's SQLITE_LOCKED/SQLITE_BUSY family, which is an artifact of
    running two threads against Django's in-memory shared-cache SQLite test
    database (see module docstring). Any other exception (including the
    application's own `ValidationError` business-rule rejections) is
    re-raised immediately and is NOT retried, since those are real outcomes
    we want to observe, not infra noise.
    """
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


class CreateBarberBookingConcurrencyTests(TransactionTestCase):
    """Fires two near-simultaneous create_barber_booking() calls, from two
    different customers, for the exact same barber+slot, each on its own DB
    connection (via a real OS thread). Asserts that at most one CONFIRMED
    booking exists for that barber+slot afterwards -- i.e. no double-booking,
    regardless of which thread "won"."""

    def setUp(self):
        self.city = City.objects.create(name="QA Concurrency City", slug="qa-concurrency-city")
        self.owner = User.objects.create_user(
            username="qa_conc_owner",
            phone="+998901230001",
            role=User.Role.ADMIN,
        )
        self.club = Club.objects.create(
            name="QA Concurrency Barbershop",
            slug="qa-concurrency-barbershop",
            category=Club.Category.BARBERSHOP,
            owner=self.owner,
            status=Club.Status.ACTIVE,
        )
        self.branch = Branch.objects.create(
            club=self.club,
            name="Main",
            city=self.city,
            address="Test address",
            latitude="41.0",
            longitude="69.0",
            status=Branch.Status.ACTIVE,
            is_24_hours=True,
        )
        self.barber_user = User.objects.create_user(
            username="qa_conc_barber",
            phone="+998901230002",
        )
        self.barber = Barber.objects.create(
            user=self.barber_user,
            full_name="QA Concurrency Barber",
            club=self.club,
            branch=self.branch,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
            status=Barber.Status.AVAILABLE,
            work_start_time=time(0, 0),
            work_end_time=time(23, 59),
            working_days=[1, 2, 3, 4, 5, 6, 7],
            is_active=True,
            is_free=True,
        )
        self.customer_a = User.objects.create_user(
            username="qa_conc_cust_a", phone="+998901230003"
        )
        self.customer_b = User.objects.create_user(
            username="qa_conc_cust_b", phone="+998901230004"
        )

        tomorrow = timezone.localdate() + timedelta(days=1)
        self.starts_at = timezone.make_aware(datetime.combine(tomorrow, time(10, 0)))
        self.ends_at = self.starts_at + timedelta(hours=1)

    def test_concurrent_create_barber_booking_does_not_double_book_same_slot(self):
        results = {}
        barrier = threading.Barrier(2, timeout=10)

        def attempt(label, user):
            try:
                barrier.wait()
                booking = _call_with_sqlite_shared_cache_lock_retry(
                    lambda: create_barber_booking(
                        user, self.barber.id, self.starts_at, self.ends_at
                    )
                )
                results[label] = ("ok", str(booking.id))
            except ValidationError as error:
                # A clean business-rule rejection (e.g. the slot was taken
                # by the other thread first) -- this is an expected, correct
                # outcome for the "losing" side of the race, not a failure.
                results[label] = ("rejected", f"{error.code}: {error}")
            except Exception as error:  # noqa: BLE001 - surface exactly what each thread raised
                results[label] = ("error", f"{type(error).__name__}: {error}")
            finally:
                connection.close()

        t1 = threading.Thread(target=attempt, args=("a", self.customer_a))
        t2 = threading.Thread(target=attempt, args=("b", self.customer_b))
        t1.start()
        t2.start()
        t1.join(timeout=20)
        t2.join(timeout=20)

        self.assertFalse(t1.is_alive(), "Thread A did not finish in time")
        self.assertFalse(t2.is_alive(), "Thread B did not finish in time")
        self.assertIn("a", results)
        self.assertIn("b", results)

        confirmed_count = Booking.objects.filter(
            barber=self.barber,
            status=Booking.Status.CONFIRMED,
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        ).count()

        # This is the core invariant under test: no double-booking,
        # regardless of which thread "won".
        self.assertLessEqual(
            confirmed_count,
            1,
            "Expected at most one CONFIRMED booking for the same barber+slot "
            f"after concurrent requests, found {confirmed_count}. "
            f"Thread results: {results}",
        )

        statuses = {label: value[0] for label, value in results.items()}

        # Any remaining "error" (as opposed to "ok" or the clean "rejected"
        # business outcome) means the SQLite shared-cache lock retry above
        # did not fully resolve a transient infra error -- that would be a
        # test-harness problem, not a signal about create_barber_booking()'s
        # own correctness, so we fail loudly and distinctly from the real
        # double-booking assertion above.
        self.assertNotIn(
            "error",
            statuses.values(),
            "Got an unresolved non-business-rule error (test-harness/SQLite "
            f"infra issue, not a double-booking signal): {results}",
        )

        # Exactly one side should succeed and the other should be cleanly
        # rejected -- that's the expected, desired outcome of the race.
        self.assertEqual(
            sorted(statuses.values()),
            ["ok", "rejected"],
            f"Expected exactly one booking to succeed and the other to be "
            f"cleanly rejected, got: {results}",
        )
