from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.clubs.models import Branch, Club
from apps.clubs.permissions import is_platform_admin
from apps.payments.models import Payment
from apps.reviews.models import Review
from apps.core.responses import error_response


class AdminDashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="Admin panel umumiy statistikasi (KPIs)",
    )
    def get(self, request):
        if not is_platform_admin(request.user):
            return error_response("clubs.permission_denied", request, status_code=403)

        now = timezone.now()
        today = now.date()

        total_clubs = Club.objects.count()
        active_clubs = Club.objects.filter(status=Club.Status.ACTIVE).count()
        pending_clubs = Club.objects.filter(status=Club.Status.PENDING).count()

        total_branches = Branch.objects.count()
        active_branches = Branch.objects.filter(status=Branch.Status.ACTIVE).count()

        total_bookings_today = Booking.objects.filter(starts_at__date=today).count()
        active_bookings_now = Booking.objects.filter(
            status__in=[Booking.Status.CONFIRMED, Booking.Status.CHECKED_IN],
            starts_at__lte=now,
            ends_at__gte=now,
        ).count()
        pending_bookings = Booking.objects.filter(
            status=Booking.Status.PENDING_CONFIRMATION
        ).count()
        completed_bookings = Booking.objects.filter(
            status=Booking.Status.COMPLETED
        ).count()
        cancelled_bookings = Booking.objects.filter(
            status=Booking.Status.CANCELLED
        ).count()

        total_users = User.objects.count()
        active_users = User.objects.filter(status=User.Status.ACTIVE).count()
        staff_users = User.objects.filter(
            role__in=[User.Role.ADMIN, User.Role.MODERATOR]
        ).count()

        total_revenue = (
            Payment.objects.filter(status=Payment.Status.PAID).aggregate(
                total=Sum("amount_tiyin")
            )["total"]
            or 0
        )
        today_revenue = (
            Payment.objects.filter(
                status=Payment.Status.PAID, paid_at__date=today
            ).aggregate(total=Sum("amount_tiyin"))["total"]
            or 0
        )

        recent_bookings_qs = (
            Booking.objects.select_related("user__profile", "zone__branch__club")
            .order_by("-created_at")[:6]
        )
        recent_bookings = [
            {
                "id": str(b.id),
                "user_name": b.user.profile.full_name or b.user.username,
                "user_phone": b.user.phone or "",
                "club_name": b.zone.branch.club.name,
                "branch_name": b.zone.branch.name,
                "zone_name": b.zone.name,
                "starts_at": b.starts_at.isoformat(),
                "ends_at": b.ends_at.isoformat(),
                "status": b.status,
                "total_price_tiyin": b.total_price_tiyin,
            }
            for b in recent_bookings_qs
        ]

        recent_reviews_qs = (
            Review.objects.select_related("user__profile", "club")
            .order_by("-created_at")[:6]
        )
        recent_reviews = [
            {
                "id": str(r.id),
                "user_name": r.user.profile.full_name or r.user.username,
                "club_name": r.club.name,
                "rating": r.rating,
                "comment": r.comment,
                "is_visible": r.is_visible,
                "created_at": r.created_at.isoformat(),
            }
            for r in recent_reviews_qs
        ]

        return Response(
            {
                "clubs": {
                    "total": total_clubs,
                    "active": active_clubs,
                    "pending": pending_clubs,
                },
                "branches": {
                    "total": total_branches,
                    "active": active_branches,
                },
                "bookings": {
                    "today": total_bookings_today,
                    "active_now": active_bookings_now,
                    "pending": pending_bookings,
                    "completed": completed_bookings,
                    "cancelled": cancelled_bookings,
                },
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "staff": staff_users,
                },
                "revenue": {
                    "total_tiyin": total_revenue,
                    "today_tiyin": today_revenue,
                },
                "recent_bookings": recent_bookings,
                "recent_reviews": recent_reviews,
            }
        )
