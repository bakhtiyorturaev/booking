"""Regression tests for venue/barber billing-gate bypass.

branch_accepts_bookings() / barber_accepts_bookings() (apps/payments/
venue_billing.py, apps/payments/barber_billing.py) are the single gate that
decides whether a club/branch/barber may keep accepting paid bookings once
billing_required is relevant. These tests confirm:

1. A non-free branch/barber with no active billing record is correctly
   locked out of new bookings (no silent bypass).
2. Only platform staff -- never the club/barber owner themselves -- can
   flip the `is_free` switch that exempts a branch/barber from billing
   (apps/payments/venue_views.py::FreeModeMixin.free_mode).
"""

from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.clubs.models import Branch, City, Club
from apps.payments.barber_billing import barber_accepts_bookings, require_barber_access
from apps.payments.models import BarberBilling, VenueBilling
from apps.payments.venue_billing import branch_accepts_bookings, require_branch_access
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


class VenueBillingBypassTests(APITestCase):
    def setUp(self):
        self.city = City.objects.create(name="QA Billing City", slug="qa-billing-city")
        self.owner = User.objects.create_user(
            username="qa_bill_owner", phone="+998901250001", role=User.Role.CLIENT,
        )
        self.club = Club.objects.create(
            name="QA Billing Club", slug="qa-billing-club",
            category=Club.Category.GAMING_CLUB, owner=self.owner, status=Club.Status.ACTIVE,
        )
        self.paid_branch = Branch.objects.create(
            club=self.club, name="Paid Branch", city=self.city, address="Addr",
            latitude="41.0", longitude="69.0", status=Branch.Status.ACTIVE,
            is_24_hours=True, is_free=False,
        )

    def test_branch_without_billing_record_is_locked_out(self):
        self.assertFalse(branch_accepts_bookings(self.paid_branch))
        with self.assertRaises(DRFValidationError):
            require_branch_access(self.paid_branch)

    def test_branch_with_expired_billing_is_locked_out(self):
        from django.utils import timezone
        from datetime import timedelta

        VenueBilling.objects.create(
            club=self.club, monthly_price_tiyin=100_000, created_by=self.owner,
            paid_until=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(branch_accepts_bookings(self.paid_branch))

    def test_branch_with_active_billing_accepts_bookings(self):
        from django.utils import timezone
        from datetime import timedelta

        VenueBilling.objects.create(
            club=self.club, monthly_price_tiyin=100_000, created_by=self.owner,
            paid_until=timezone.now() + timedelta(days=5),
        )
        self.assertTrue(branch_accepts_bookings(self.paid_branch))

    def test_owner_cannot_self_grant_free_mode(self):
        """Only platform staff may call the free-mode action; the owning
        club's own user must be rejected even though they manage the branch."""
        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.post(
            f"/api/v1/cabinet/branch-billing/{self.paid_branch.id}/free-mode/",
            {"is_free": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.paid_branch.refresh_from_db()
        self.assertFalse(self.paid_branch.is_free)

    def test_platform_admin_can_grant_free_mode(self):
        admin = User.objects.create_user(
            username="qa_bill_admin", phone="+998901250002",
            role=User.Role.ADMIN, is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/v1/cabinet/branch-billing/{self.paid_branch.id}/free-mode/",
            {"is_free": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.paid_branch.refresh_from_db()
        self.assertTrue(self.paid_branch.is_free)
        self.assertTrue(branch_accepts_bookings(self.paid_branch))


class BarberBillingBypassTests(APITestCase):
    def setUp(self):
        self.city = City.objects.create(name="QA Barber Billing City", slug="qa-barber-billing-city")
        self.owner = User.objects.create_user(
            username="qa_barber_bill_owner", phone="+998901250003", role=User.Role.CLIENT,
        )
        self.club = Club.objects.create(
            name="QA Barber Billing Club", slug="qa-barber-billing-club",
            category=Club.Category.BARBERSHOP, owner=self.owner, status=Club.Status.ACTIVE,
        )
        self.barber_user = User.objects.create_user(username="qa_bb_barber", phone="+998901250004")
        self.barber = Barber.objects.create(
            user=self.barber_user, full_name="QA Barber", club=self.club,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
            status=Barber.Status.AVAILABLE, is_active=True, is_free=False,
        )

    def test_unpaid_barber_is_locked_out(self):
        self.assertFalse(barber_accepts_bookings(self.barber))
        with self.assertRaises(DRFValidationError):
            require_barber_access(self.barber)

    def test_paid_barber_accepts_bookings(self):
        from django.utils import timezone
        from datetime import timedelta

        BarberBilling.objects.create(
            barber=self.barber, monthly_price_tiyin=50_000, created_by=self.owner,
            paid_until=timezone.now() + timedelta(days=10),
        )
        self.assertTrue(barber_accepts_bookings(self.barber))

    def test_barber_cannot_self_grant_free_mode(self):
        client = APIClient()
        client.force_authenticate(user=self.barber_user)
        response = client.post(
            f"/api/v1/cabinet/barber-billing/{self.barber.id}/free-mode/",
            {"is_free": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.barber.refresh_from_db()
        self.assertFalse(self.barber.is_free)
