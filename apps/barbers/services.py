import datetime
import logging
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.barbers.models import Barber
from apps.bookings.models import Booking, BookingHold

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def get_barber_available_slots(barber: Barber, target_date: datetime.date):
    """
    Sartaroshning ko'rsatilgan sanadagi 1 soatlik bo'sh vaqt slotlarini hisoblaydi.
    """
    now_local = timezone.localtime(timezone.now(), TASHKENT_TZ)
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

    # 3. Ish vaqti oralig'ida 1 soatlik slotlar generatsiyasi
    start_hour = barber.work_start_time.hour
    end_hour = barber.work_end_time.hour
    if barber.work_end_time.minute > 0:
        end_hour += 1

    # Band qilingan bronlar va holdlar
    day_start = timezone.make_aware(
        datetime.datetime.combine(target_date, datetime.time.min),
        TASHKENT_TZ,
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(target_date, datetime.time.max),
        TASHKENT_TZ,
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
    for hour in range(start_hour, end_hour):
        slot_start_dt = timezone.make_aware(
            datetime.datetime.combine(target_date, datetime.time(hour=hour, minute=0)),
            TASHKENT_TZ,
        )
        slot_end_dt = slot_start_dt + datetime.timedelta(hours=1)

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
            "time_label": f"{hour:02d}:00 - {hour+1:02d}:00",
            "hour": hour,
            "is_available": is_slot_available,
            "is_past": is_past,
            "is_occupied": is_occupied,
        })

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
