from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.utils import timezone

from apps.bookings.models import Booking, BookingHold, Cancellation
from apps.clubs.models import (
    Branch,
    Club,
    OperatingHour,
    ResourceBlock,
    SpecialSchedule,
    Zone,
)
from apps.payments.services import require_paid_access


BLOCKING_BOOKING_STATUSES = (
    Booking.Status.PENDING_CONFIRMATION,
    Booking.Status.CONFIRMED,
    Booking.Status.CHECKED_IN,
)


def invalidate_branch_availability(branch_id):
    if not branch_id:
        return
    version_key = f"branch_avail_ver:{branch_id}"
    try:
        if cache.get(version_key) is None:
            cache.set(version_key, 1, timeout=86400)
        else:
            cache.incr(version_key)
    except Exception:
        cache.set(version_key, str(timezone.now().timestamp()), timeout=86400)


def _schedule_window(branch, target_date):
    schedule = SpecialSchedule.objects.filter(branch=branch, date=target_date).first()
    if schedule:
        if schedule.is_closed:
            return None
        opens_at, closes_at = schedule.opens_at, schedule.closes_at
    elif branch.is_24_hours:
        opens_at = closes_at = time.min
    else:
        schedule = OperatingHour.objects.filter(
            branch=branch,
            weekday=target_date.weekday(),
        ).first()
        if not schedule or schedule.is_closed:
            return None
        opens_at, closes_at = schedule.opens_at, schedule.closes_at

    local_timezone = ZoneInfo(branch.timezone)
    starts_at = timezone.make_aware(datetime.combine(target_date, opens_at), local_timezone)
    ends_at = timezone.make_aware(datetime.combine(target_date, closes_at), local_timezone)
    if ends_at <= starts_at:
        ends_at += timedelta(days=1)
    return starts_at, ends_at


def _overlaps(item, starts_at, ends_at):
    return item.starts_at < ends_at and item.ends_at > starts_at


def get_branch_availability(branch, target_date, duration_minutes=None):
    version_key = f"branch_avail_ver:{branch.id}"
    version = cache.get(version_key)
    if version is None:
        version = 1
        cache.set(version_key, version, timeout=86400)

    cache_key = f"branch_avail:{branch.id}:{target_date}:{duration_minutes}:{version}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    window = _schedule_window(branch, target_date)
    duration_minutes = duration_minutes or branch.minimum_booking_minutes
    if not window:
        return []

    opens_at, closes_at = window
    now = timezone.now()
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=branch.slot_interval_minutes)
    zones = branch.zones.filter(status=Zone.Status.ACTIVE).prefetch_related(
        Prefetch(
            "bookinghold_set",
            queryset=BookingHold.objects.filter(
                status=BookingHold.Status.HELD,
                expires_at__gt=now,
                starts_at__lt=closes_at,
                ends_at__gt=opens_at,
            ),
            to_attr="active_holds",
        ),
        Prefetch(
            "booking_set",
            queryset=Booking.objects.filter(
                status__in=BLOCKING_BOOKING_STATUSES,
                starts_at__lt=closes_at,
                ends_at__gt=opens_at,
            ),
            to_attr="active_bookings",
        ),
        Prefetch(
            "resource_blocks",
            queryset=ResourceBlock.objects.filter(
                is_active=True,
                starts_at__lt=closes_at,
                ends_at__gt=opens_at,
            ),
            to_attr="active_blocks",
        ),
    )
    result = []

    for zone in zones:
        holds = zone.active_holds
        bookings = zone.active_bookings
        blocks = zone.active_blocks
        slots = []
        starts_at = opens_at
        while starts_at + duration <= closes_at:
            ends_at = starts_at + duration
            if starts_at <= now:
                starts_at += step
                continue
            blocked = any(_overlaps(item, starts_at, ends_at) for item in blocks)
            reserved = sum(
                item.quantity
                for item in (*holds, *bookings)
                if _overlaps(item, starts_at, ends_at)
            )
            slots.append(
                {
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "available": 0 if blocked else max(zone.booking_capacity - reserved, 0),
                }
            )
            starts_at += step

        result.append({"zone": zone, "slots": slots})

    cache.set(cache_key, result, timeout=30)
    return result


def _validate_window(zone, starts_at, ends_at, quantity):
    branch = zone.branch
    local_timezone = ZoneInfo(branch.timezone)
    duration_minutes = (ends_at - starts_at).total_seconds() / 60
    target_date = timezone.localtime(starts_at, local_timezone).date()
    today = timezone.localtime(timezone.now(), local_timezone).date()
    window = _schedule_window(branch, target_date)

    if starts_at <= timezone.now() or ends_at <= starts_at:
        raise ValidationError("bookings.invalid_time_range", code="bookings.invalid_time_range")
    if target_date > today + timedelta(days=branch.advance_booking_days):
        raise ValidationError("bookings.date_outside_advance_limit", code="bookings.date_outside_advance_limit")
    if not window or starts_at < window[0] or ends_at > window[1]:
        raise ValidationError("bookings.outside_working_hours", code="bookings.outside_working_hours")
    if not branch.minimum_booking_minutes <= duration_minutes <= branch.maximum_booking_minutes:
        raise ValidationError("bookings.duration_out_of_range", code="bookings.duration_out_of_range")
    if duration_minutes % branch.slot_interval_minutes:
        raise ValidationError("bookings.duration_not_slot_aligned", code="bookings.duration_not_slot_aligned")
    if (starts_at - window[0]).total_seconds() % (branch.slot_interval_minutes * 60):
        raise ValidationError("bookings.start_not_slot_aligned", code="bookings.start_not_slot_aligned")
    if quantity < 1 or quantity > zone.booking_capacity:
        raise ValidationError("bookings.invalid_quantity", code="bookings.invalid_quantity")


@transaction.atomic
def create_hold(user, zone_id, starts_at, ends_at, quantity=1):
    require_paid_access(user)
    get_user_model().objects.select_for_update().get(pk=user.pk)
    zone = Zone.objects.select_for_update().select_related("branch", "branch__club").get(
        pk=zone_id
    )
    if (
        zone.status != Zone.Status.ACTIVE
        or zone.branch.status != Branch.Status.ACTIVE
        or zone.branch.club.status != Club.Status.ACTIVE
    ):
        raise ValidationError("bookings.zone_not_available", code="bookings.zone_not_available")

    _validate_window(zone, starts_at, ends_at, quantity)
    now = timezone.now()
    BookingHold.objects.filter(
        user=user,
        status=BookingHold.Status.HELD,
        expires_at__lte=now,
    ).update(status=BookingHold.Status.EXPIRED, updated_at=now)
    if BookingHold.objects.filter(
        user=user,
        status=BookingHold.Status.HELD,
        expires_at__gt=now,
    ).exists() or Booking.objects.filter(
        user=user,
        status__in=BLOCKING_BOOKING_STATUSES,
        ends_at__gt=now,
    ).exists():
        raise ValidationError("bookings.active_booking_exists", code="bookings.active_booking_exists")

    if ResourceBlock.objects.filter(
        zone=zone,
        is_active=True,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).exists():
        raise ValidationError("bookings.zone_closed_at_time", code="bookings.zone_closed_at_time")

    hold_count = BookingHold.objects.filter(
        zone=zone,
        status=BookingHold.Status.HELD,
        expires_at__gt=now,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).aggregate(total=Sum("quantity"))["total"] or 0
    booking_count = Booking.objects.filter(
        zone=zone,
        status__in=BLOCKING_BOOKING_STATUSES,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).aggregate(total=Sum("quantity"))["total"] or 0
    if hold_count + booking_count + quantity > zone.booking_capacity:
        raise ValidationError("bookings.insufficient_seats", code="bookings.insufficient_seats")

    duration_minutes = int((ends_at - starts_at).total_seconds() // 60)
    total_price = (zone.price_per_hour_tiyin * duration_minutes * quantity + 59) // 60
    hold = BookingHold.objects.create(
        user=user,
        zone=zone,
        starts_at=starts_at,
        ends_at=ends_at,
        quantity=quantity,
        unit_price_tiyin=zone.price_per_hour_tiyin,
        total_price_tiyin=total_price,
        expires_at=now + timedelta(minutes=zone.branch.booking_hold_minutes),
    )
    invalidate_branch_availability(zone.branch_id)
    return hold


def create_booking(user, hold_id):
    expired = False
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        hold = BookingHold.objects.select_for_update().select_related("zone").get(
            pk=hold_id,
            user=user,
        )
        if hold.status == BookingHold.Status.HELD and hold.expires_at <= timezone.now():
            hold.status = BookingHold.Status.EXPIRED
            hold.save(update_fields=("status", "updated_at"))
            expired = True
        elif hold.status != BookingHold.Status.HELD:
            raise ValidationError("bookings.hold_expired_or_used", code="bookings.hold_expired_or_used")
        elif Booking.objects.filter(
            user=user,
            status__in=BLOCKING_BOOKING_STATUSES,
            ends_at__gt=timezone.now(),
        ).exists():
            raise ValidationError("bookings.active_booking_exists", code="bookings.active_booking_exists")
        else:
            booking = Booking.objects.create(
                hold=hold,
                user=user,
                zone=hold.zone,
                starts_at=hold.starts_at,
                ends_at=hold.ends_at,
                quantity=hold.quantity,
                unit_price_tiyin=hold.unit_price_tiyin,
                total_price_tiyin=hold.total_price_tiyin,
                status=Booking.Status.PENDING_CONFIRMATION,
            )
            hold.status = BookingHold.Status.CONVERTED
            hold.save(update_fields=("status", "updated_at"))
            invalidate_branch_availability(hold.zone.branch_id)
            from telegram_bot.services import queue_booking_message, send_customer_booking_notification

            try:
                queue_booking_message(booking)
            except Exception:
                pass
            send_customer_booking_notification(booking, booking.status)

    if expired:
        raise ValidationError("bookings.hold_expired_or_used", code="bookings.hold_expired_or_used")
    return booking


@transaction.atomic
def cancel_booking(user, booking_id, reason=""):
    booking = Booking.objects.select_for_update().select_related("zone__branch", "barber__branch").get(
        pk=booking_id,
        user=user,
    )
    if booking.status not in (
        Booking.Status.PENDING_CONFIRMATION,
        Booking.Status.CONFIRMED,
    ):
        raise ValidationError("bookings.only_confirmed_can_cancel", code="bookings.only_confirmed_can_cancel")

    if booking.status == Booking.Status.CONFIRMED and booking.zone and booking.zone.branch:
        cancel_until = booking.starts_at - timedelta(
            minutes=booking.zone.branch.free_cancellation_minutes
        )
        if timezone.now() > cancel_until:
            raise ValidationError("bookings.cancel_too_late", code="bookings.cancel_too_late")
    booking.transition_to(Booking.Status.CANCELLED)
    Cancellation.objects.create(
        booking=booking,
        requested_by=user,
        reason=reason,
    )
    if booking.zone:
        invalidate_branch_availability(booking.zone.branch_id)
    from telegram_bot.services import queue_booking_message, send_customer_booking_notification

    try:
        queue_booking_message(booking)
    except Exception:
        pass
    send_customer_booking_notification(booking, Booking.Status.CANCELLED)
    return booking


@transaction.atomic
def transition_booking_for_operator(user, booking_id, target_status):
    """Move a booking through the on-site lifecycle for an authorized club owner."""
    from apps.clubs.permissions import can_manage_club

    booking = (
        Booking.objects.select_for_update()
        .select_related("zone__branch__club", "barber__club", "barber__branch")
        .get(pk=booking_id)
    )
    club = (
        booking.zone.branch.club
        if (booking.zone and booking.zone.branch)
        else (booking.barber.club if booking.barber else None)
    )
    if not club or not can_manage_club(user, club):
        raise PermissionError("clubs.permission_denied")

    now = timezone.now()
    if target_status == Booking.Status.CHECKED_IN and now < booking.starts_at:
        raise ValidationError("bookings.checkin_before_start_time", code="bookings.checkin_before_start_time")
    if target_status == Booking.Status.NO_SHOW:
        grace_minutes = (
            booking.zone.branch.no_show_grace_minutes
            if (booking.zone and booking.zone.branch)
            else 15
        )
        no_show_after = booking.starts_at + timedelta(minutes=grace_minutes)
        if now < no_show_after:
            raise ValidationError("bookings.noshow_grace_period_not_passed", code="bookings.noshow_grace_period_not_passed")

    booking.transition_to(target_status)
    if booking.zone:
        invalidate_branch_availability(booking.zone.branch_id)
    if target_status in (Booking.Status.CONFIRMED, Booking.Status.CANCELLED):
        from telegram_bot.services import send_customer_booking_notification

        send_customer_booking_notification(booking, target_status)
    return booking


def process_booking_lifecycle(now=None):
    """Apply branch auto-confirm and no-show rules; safe to run repeatedly."""
    now = now or timezone.now()
    from telegram_bot.services import process_confirmation_timeouts

    confirmed = process_confirmation_timeouts(now=now)
    no_show_ids = Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        starts_at__lte=now,
        zone__isnull=False,
    ).values_list("id", flat=True)
    no_shows = 0
    for booking_id in no_show_ids.iterator():
        try:
            booking = Booking.objects.select_related("zone__branch").get(pk=booking_id)
            if not booking.zone or not booking.zone.branch:
                continue
            grace_deadline = booking.starts_at + timedelta(
                minutes=booking.zone.branch.no_show_grace_minutes
            )
            if now >= grace_deadline:
                with transaction.atomic():
                    locked = Booking.objects.select_for_update().get(pk=booking_id)
                    if locked.status == Booking.Status.CONFIRMED:
                        locked.transition_to(Booking.Status.NO_SHOW)
                        if locked.zone:
                            invalidate_branch_availability(locked.zone.branch_id)
                        no_shows += 1
        except Booking.DoesNotExist:
            continue
    return {"confirmed": confirmed, "no_shows": no_shows}
