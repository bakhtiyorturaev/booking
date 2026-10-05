import datetime
import logging
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.barbers.models import Barber
from apps.bookings.models import Booking, BookingHold
from apps.clubs.models import Branch, Club

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def get_barber_available_slots(barber: Barber, target_date: datetime.date):
    """
    Sartaroshning ko'rsatilgan sanadagi 1 soatlik bo'sh vaqt slotlarini hisoblaydi.
    """
    from apps.payments.venue_billing import branch_accepts_bookings
    from apps.payments.barber_billing import barber_accepts_bookings
    club = barber.branch.club if barber.branch_id else barber.club
    if not barber.is_active or not barber_accepts_bookings(barber) or (club is not None and (club.status != Club.Status.ACTIVE)) or (barber.branch_id and (barber.branch.status != Branch.Status.ACTIVE or not branch_accepts_bookings(barber.branch))) or (club is not None and barber.affiliation_status != Barber.AffiliationStatus.APPROVED):
        return {
            "barber_id": str(barber.id), "target_date": target_date.isoformat(),
            "is_available": False, "status": barber.status,
            "reason": "Muassasa hozir yangi bron qabul qilmayapti.", "slots": [],
        }
    local_timezone = ZoneInfo(barber.branch.timezone) if barber.branch_id else TASHKENT_TZ
    now_local = timezone.localtime(timezone.now(), local_timezone)
    is_today = (target_date == now_local.date())

    # 1. Agar sartarosh bugun ishlamasa yoki dam olish kuni bo'lsa
    if is_today and barber.status == Barber.Status.DAY_OFF:
        return {
            "barber_id": str(barber.id),
            "target_date": target_date.isoformat(),
            "is_available": False,
            "status": barber.status,
            "reason": "Sartarosh bugun dam olish kunida.",
            "slots": [],
        }

    if is_today and barber.status == Barber.Status.NOT_AT_WORK:
        return {
            "barber_id": str(barber.id),
            "target_date": target_date.isoformat(),
            "is_available": False,
            "status": barber.status,
            "reason": "Sartarosh hozircha ishga chiqmagan.",
            "slots": [],
        }

    # 2. Haftaning ish kuni tekshiruvi (1 = Dushanba ... 7 = Yakshanba)
    weekday = target_date.isoweekday()
    working_days = barber.working_days or [1, 2, 3, 4, 5, 6]
    if weekday not in working_days:
        return {
            "barber_id": str(barber.id),
            "target_date": target_date.isoformat(),
            "is_available": False,
            "status": Barber.Status.DAY_OFF,
            "reason": "Sartaroshning haftalik dam olish kuni.",
            "slots": [],
        }

    opens_at = timezone.make_aware(datetime.datetime.combine(target_date, barber.work_start_time), local_timezone)
    closes_at = timezone.make_aware(datetime.datetime.combine(target_date, barber.work_end_time), local_timezone)
    if closes_at <= opens_at:
        closes_at += datetime.timedelta(days=1)
    if barber.branch_id:
        from apps.bookings.services import _schedule_window
        window = _schedule_window(barber.branch, target_date)
        if window is None:
            return {"barber_id": str(barber.id), "target_date": target_date.isoformat(), "is_available": False, "status": barber.status, "reason": "Filial bu kuni yopiq.", "slots": []}
        opens_at = max(opens_at, window[0])
        closes_at = min(closes_at, window[1])
        if target_date > now_local.date() + datetime.timedelta(days=barber.branch.advance_booking_days):
            return {"barber_id": str(barber.id), "target_date": target_date.isoformat(), "is_available": False, "status": barber.status, "reason": "Bron sanasi ruxsat etilgan muddatdan tashqarida.", "slots": []}

    # Band qilingan bronlar va holdlar
    day_start = timezone.make_aware(
        datetime.datetime.combine(target_date, datetime.time.min),
        local_timezone,
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(target_date + datetime.timedelta(days=1), datetime.time.max),
        local_timezone,
    )

    active_bookings = Booking.objects.filter(
        barber=barber,
        status__in=[
            Booking.Status.CONFIRMED,
            Booking.Status.CHECKED_IN,
            Booking.Status.PENDING_CONFIRMATION,
        ],
        starts_at__lt=day_end,
        ends_at__gt=day_start,
    ).values("starts_at", "ends_at")

    active_holds = BookingHold.objects.filter(
        barber=barber,
        status=BookingHold.Status.HELD,
        expires_at__gt=timezone.now(),
        starts_at__lt=day_end,
        ends_at__gt=day_start,
    ).values("starts_at", "ends_at")

    occupied_intervals = list(active_bookings) + list(active_holds)

    slots = []
    slot_start_dt = opens_at
    while slot_start_dt + datetime.timedelta(hours=1) <= closes_at:
        slot_end_dt = slot_start_dt + datetime.timedelta(hours=1)
        hour = slot_start_dt.hour
        # O'tgan vaqt tekshiruvi
        is_past = slot_start_dt < now_local

        # Bandlik tekshiruvi
        is_occupied = False
        for interval in occupied_intervals:
            if slot_start_dt < interval["ends_at"] and slot_end_dt > interval["starts_at"]:
                is_occupied = True
                break

        is_slot_available = not is_past and not is_occupied

        slots.append({
            "starts_at": slot_start_dt.isoformat(),
            "ends_at": slot_end_dt.isoformat(),
            "time_label": f"{slot_start_dt:%H:%M} - {slot_end_dt:%H:%M}",
            "hour": hour,
            "is_available": is_slot_available,
            "is_past": is_past,
            "is_occupied": is_occupied,
        })
        slot_start_dt = slot_end_dt

    return {
        "barber_id": str(barber.id),
        "target_date": target_date.isoformat(),
        "is_available": True,
        "status": barber.status,
        "reason": "",
        "slots": slots,
    }


def send_barber_booking_notification(booking):
    """
    Sartaroshning Telegram botiga yangi mijoz yozilgani haqida bildirishnoma jo'natadi.
    """
    try:
        barber = getattr(booking, "barber", None)
        if not barber or not barber.user:
            return

        telegram_user_id = barber.user.telegram_user_id
        if not telegram_user_id:
            logger.info("Barber user #%s has no telegram_user_id", barber.user_id)
            return

        from telegram_bot.client import TelegramClient

        client = TelegramClient()
        starts_at_local = timezone.localtime(booking.starts_at, TASHKENT_TZ)
        ends_at_local = timezone.localtime(booking.ends_at, TASHKENT_TZ)

        customer_name = (
            getattr(getattr(booking.user, "profile", None), "full_name", "")
            or booking.user.username
        )
        customer_phone = booking.user.phone or "—"
        salon_name = barber.club.name if barber.club else "Sartaroshxona"
        branch_name = barber.branch.name if barber.branch else ""

        message_text = (
            f"💈 <b>Yangi mijoz yozildi!</b>\n\n"
            f"👤 <b>Mijoz:</b> {customer_name}\n"
            f"📞 <b>Telefon:</b> {customer_phone}\n"
            f"📅 <b>Sana:</b> {starts_at_local.strftime('%d.%m.%Y')}\n"
            f"⏰ <b>Vaqt:</b> {starts_at_local.strftime('%H:%M')} - {ends_at_local.strftime('%H:%M')}\n"
            f"📍 <b>Sartaroshxona:</b> {salon_name} {f'({branch_name})' if branch_name else ''}\n\n"
            f"💰 <b>To'lov:</b> Sartaroshxonada joyida kelishiladi\n"
            f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>"
        )

        client.send_message(chat_id=telegram_user_id, text=message_text, parse_mode="HTML")
        logger.info("Successfully sent booking notification to barber telegram %s", telegram_user_id)
    except Exception as e:
        logger.warning("Could not send barber telegram notification: %s", e)
