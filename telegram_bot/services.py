import html
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, Cancellation
from apps.core.services.messages import get_system_message
from telegram_bot.client import TelegramClient
from telegram_bot.models import (
    BranchTelegramBinding,
    TelegramBotSettings,
    TelegramBookingMessage,
    TelegramCancellationReason,
    TelegramMessageTemplate,
)

logger = logging.getLogger(__name__)


def _booking_values(booking):
    branch_tz = "Asia/Tashkent"
    if booking.zone and booking.zone.branch and booking.zone.branch.timezone:
        branch_tz = booking.zone.branch.timezone
    elif booking.barber and booking.barber.branch and booking.barber.branch.timezone:
        branch_tz = booking.barber.branch.timezone

    try:
        local_timezone = ZoneInfo(branch_tz)
    except Exception:
        local_timezone = ZoneInfo("Asia/Tashkent")

    starts_at = timezone.localtime(booking.starts_at, local_timezone)
    ends_at = timezone.localtime(booking.ends_at, local_timezone)
    cancellation = getattr(booking, "cancellation", None)

    branch_name = "-"
    zone_name = "-"
    if booking.zone:
        branch_name = booking.zone.branch.name if booking.zone.branch else "-"
        zone_name = booking.zone.name
    elif booking.barber:
        branch_name = booking.barber.branch.name if booking.barber.branch else (booking.barber.club.name if booking.barber.club else "-")
        zone_name = f"Sartarosh: {booking.barber.full_name}"

    return {
        "booking_number": booking.booking_number,
        "branch": branch_name,
        "zone": zone_name,
        "date": starts_at.strftime("%d.%m.%Y"),
        "time": starts_at.strftime("%H:%M"),
        "end_time": ends_at.strftime("%H:%M"),
        "quantity": booking.quantity,
        "customer": getattr(getattr(booking.user, "profile", None), "full_name", "")
        or booking.user.username,
        "phone": booking.user.phone or "-",
        "reason": cancellation.reason if cancellation else "-",
    }


def translated_message(code, language="uz"):
    return get_system_message(code, language)["message"]


def render_booking_message(booking, language="uz"):
    event = {
        Booking.Status.PENDING_CONFIRMATION: TelegramMessageTemplate.Event.PENDING,
        Booking.Status.CONFIRMED: TelegramMessageTemplate.Event.CONFIRMED,
        Booking.Status.CANCELLED: TelegramMessageTemplate.Event.CANCELLED,
    }.get(booking.status, TelegramMessageTemplate.Event.PENDING)
    template = TelegramMessageTemplate.objects.get(event=event, is_active=True)
    return template.get_text(language).format(**_booking_values(booking))


def booking_keyboard(booking, language="uz"):
    if booking.status != Booking.Status.PENDING_CONFIRMATION:
        return {"inline_keyboard": []}
    return {
        "inline_keyboard": [[
            {
                "text": translated_message("telegram.btn_confirm", language),
                "callback_data": f"confirm:{booking.id}",
            },
            {
                "text": translated_message("telegram.btn_cancel", language),
                "callback_data": f"cancel:{booking.id}",
            },
        ]]
    }


def cancellation_keyboard(booking_id, language="uz"):
    return {
        "inline_keyboard": [
            [{
                "text": reason.get_title(language),
                "callback_data": f"reason:{reason.code}:{booking_id}",
            }]
            for reason in TelegramCancellationReason.objects.filter(is_active=True)
        ]
    }


def queue_booking_message(booking):
    if not booking.zone:
        return None
    binding = BranchTelegramBinding.objects.select_related("group").filter(
        branch=booking.zone.branch,
        is_active=True,
        group__is_active=True,
    ).first()
    if not binding:
        raise ValidationError("telegram.group_not_configured", code="telegram.group_not_configured")
    message, created = TelegramBookingMessage.objects.get_or_create(
        booking=booking,
        defaults={"group": binding.group},
    )
    message.status = TelegramBookingMessage.Status.PENDING
    message.operation = (
        TelegramBookingMessage.Operation.SEND
        if created or not message.message_id
        else TelegramBookingMessage.Operation.EDIT
    )
    message.last_error = ""
    message.save(update_fields=("status", "operation", "last_error", "updated_at"))
    return message


def dispatch_pending_messages(client=None, limit=100):
    client = client or TelegramClient()
    messages = TelegramBookingMessage.objects.filter(
        status__in=(
            TelegramBookingMessage.Status.PENDING,
            TelegramBookingMessage.Status.FAILED,
        )
    ).select_related("booking__user", "booking__zone__branch", "group")[:limit]
    for message in messages:
        try:
            text = render_booking_message(message.booking, message.group.language)
            keyboard = booking_keyboard(message.booking, message.group.language)
            if message.operation == TelegramBookingMessage.Operation.EDIT:
                client.edit_message(
                    message.group.chat_id,
                    message.message_id,
                    text,
                    keyboard,
                )
            else:
                result = client.send_message(message.group.chat_id, text, keyboard)
                message.message_id = result["message_id"]
            message.status = TelegramBookingMessage.Status.SENT
            message.last_error = ""
        except Exception as error:
            message.status = TelegramBookingMessage.Status.FAILED
            message.last_error = str(error)[:2000]
        message.attempts += 1
        message.save()


def _format_currency(amount_tiyin, language="uz"):
    if not amount_tiyin or amount_tiyin <= 0:
        if language == "ru":
            return "0 сум (Бесплатно)"
        elif language == "en":
            return "0 UZS (Free)"
        return "0 so‘m (Tekin)"
    amount_som = amount_tiyin // 100
    formatted_sum = f"{amount_som:,}".replace(",", " ")
    if language == "ru":
        return f"{formatted_sum} сум"
    elif language == "en":
        return f"{formatted_sum} UZS"
    return f"{formatted_sum} so‘m"


def build_customer_booking_message_and_keyboard(booking, event_type, language="uz"):
    from telegram_bot.handlers import build_user_keyboard

    is_barber = bool(getattr(booking, "barber", None))
    cancellation = getattr(booking, "cancellation", None)
    reason = (cancellation.reason if cancellation and cancellation.reason else "").strip()
    if not reason:
        reason = "Sabab ko‘rsatilmagan" if language == "uz" else ("Причина не указана" if language == "ru" else "No reason provided")

    if is_barber:
        barber = booking.barber
        club = barber.club if barber else None
        branch = barber.branch if barber else None
        branch_tz = (branch.timezone if branch and branch.timezone else None) or "Asia/Tashkent"
        club_name = club.name if club else "Sartaroshxona"
        branch_name = branch.name if branch else ""
        address = getattr(branch, "full_address", "") or getattr(branch, "address", "") or ""
        barber_name = barber.full_name if barber else "-"
        barber_phone = barber.phone or ""
    else:
        zone = getattr(booking, "zone", None)
        branch = zone.branch if zone else None
        club = branch.club if branch else None
        branch_tz = (branch.timezone if branch and branch.timezone else None) or "Asia/Tashkent"
        club_name = club.name if club else "RezervUZ Klubi"
        branch_name = branch.name if branch else ""
        address = getattr(branch, "full_address", "") or getattr(branch, "address", "") or ""
        zone_name = zone.name if zone else "Zona"
        quantity = booking.quantity or 1

    try:
        local_tz = ZoneInfo(branch_tz)
    except Exception:
        local_tz = ZoneInfo("Asia/Tashkent")

    starts = timezone.localtime(booking.starts_at, local_tz)
    ends = timezone.localtime(booking.ends_at, local_tz)
    date_str = starts.strftime("%d.%m.%Y")
    time_str = f"{starts.strftime('%H:%M')} – {ends.strftime('%H:%M')}"

    # Price string
    if is_barber:
        if booking.total_price_tiyin and booking.total_price_tiyin > 0:
            price_str = _format_currency(booking.total_price_tiyin, language)
        else:
            price_str = "Sartaroshxonada joyida kelishiladi" if language == "uz" else ("Оплата на месте в барбершопе" if language == "ru" else "Pay at location")
    else:
        price_str = _format_currency(booking.total_price_tiyin, language)

    # Construct messages based on type, status, and language
    if is_barber:
        if event_type == Booking.Status.CONFIRMED:
            if language == "ru":
                text = (
                    f"💈 <b>Ваша запись к мастеру подтверждена!</b>\n\n"
                    f"✂️ <b>Мастер:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Барбершоп:</b> {html.escape(club_name)}"
                    f"{f' ({html.escape(branch_name)})' if branch_name else ''}\n"
                    f"{f'📍 <b>Адрес:</b> {html.escape(address)}\n' if address else ''}"
                    f"{f'📞 <b>Контакты мастера:</b> <code>{html.escape(barber_phone)}</code>\n' if barber_phone else ''}"
                    f"📅 <b>Дата:</b> {date_str}\n"
                    f"⏰ <b>Время:</b> {time_str}\n"
                    f"💰 <b>Оплата:</b> {price_str}\n"
                    f"🔖 <b>Номер брони:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Пожалуйста, приходите вовремя к назначенному времени.</i>"
                )
            elif language == "en":
                text = (
                    f"💈 <b>Your barber appointment is confirmed!</b>\n\n"
                    f"✂️ <b>Barber:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Barbershop:</b> {html.escape(club_name)}"
                    f"{f' ({html.escape(branch_name)})' if branch_name else ''}\n"
                    f"{f'📍 <b>Address:</b> {html.escape(address)}\n' if address else ''}"
                    f"{f'📞 <b>Contact:</b> <code>{html.escape(barber_phone)}</code>\n' if barber_phone else ''}"
                    f"📅 <b>Date:</b> {date_str}\n"
                    f"⏰ <b>Time:</b> {time_str}\n"
                    f"💰 <b>Payment:</b> {price_str}\n"
                    f"🔖 <b>Booking ID:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Please arrive on time for your appointment.</i>"
                )
            else:
                text = (
                    f"💈 <b>Sartarosh qabuliga broningiz tasdiqlandi!</b>\n\n"
                    f"✂️ <b>Usta:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Sartaroshxona:</b> {html.escape(club_name)}"
                    f"{f' ({html.escape(branch_name)})' if branch_name else ''}\n"
                    f"{f'📍 <b>Manzil:</b> {html.escape(address)}\n' if address else ''}"
                    f"{f'📞 <b>Usta bilan aloqa:</b> <code>{html.escape(barber_phone)}</code>\n' if barber_phone else ''}"
                    f"📅 <b>Sana:</b> {date_str}\n"
                    f"⏰ <b>Vaqt:</b> {time_str}\n"
                    f"💰 <b>To‘lov:</b> {price_str}\n"
                    f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Iltimos, belgilangan vaqtda kechikmasdan tashrif buyuring.</i>"
                )
        elif event_type == Booking.Status.CANCELLED:
            if language == "ru":
                text = (
                    f"❌ <b>Запись к мастеру отменена</b>\n\n"
                    f"✂️ <b>Мастер:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Барбершоп:</b> {html.escape(club_name)}\n"
                    f"📅 <b>Дата и время:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Номер брони:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Причина:</b> {html.escape(reason)}"
                )
            elif language == "en":
                text = (
                    f"❌ <b>Barber appointment cancelled</b>\n\n"
                    f"✂️ <b>Barber:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Barbershop:</b> {html.escape(club_name)}\n"
                    f"📅 <b>Date & time:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Booking ID:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Reason:</b> {html.escape(reason)}"
                )
            else:
                text = (
                    f"❌ <b>Sartarosh qabuliga bron bekor qilindi</b>\n\n"
                    f"✂️ <b>Usta:</b> {html.escape(barber_name)}\n"
                    f"🏢 <b>Sartaroshxona:</b> {html.escape(club_name)}\n"
                    f"📅 <b>Sana va vaqt:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Sabab:</b> {html.escape(reason)}"
                )
        else:
            return None, None
    else:
        # Zone / Club Booking
        if event_type == Booking.Status.CONFIRMED:
            if language == "ru":
                text = (
                    f"✅ <b>Ваша бронь успешно подтверждена!</b>\n\n"
                    f"🎮 <b>Клуб:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Филиал:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Адрес:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Зона / Место:</b> {html.escape(zone_name)} ({quantity} мест)\n"
                    f"📅 <b>Дата:</b> {date_str}\n"
                    f"⏰ <b>Время:</b> {time_str}\n"
                    f"💰 <b>Итоговая сумма:</b> {price_str}\n"
                    f"🔖 <b>Номер брони:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Пожалуйста, приходите за 5-10 минут до начала бронирования. Ждем вас!</i>"
                )
            elif language == "en":
                text = (
                    f"✅ <b>Your booking has been confirmed!</b>\n\n"
                    f"🎮 <b>Club:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Branch:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Address:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Zone:</b> {html.escape(zone_name)} ({quantity} place(s))\n"
                    f"📅 <b>Date:</b> {date_str}\n"
                    f"⏰ <b>Time:</b> {time_str}\n"
                    f"💰 <b>Total price:</b> {price_str}\n"
                    f"🔖 <b>Booking ID:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Please arrive 5-10 minutes prior to your scheduled time. See you soon!</i>"
                )
            else:
                text = (
                    f"✅ <b>Broningiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                    f"🎮 <b>Klub:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Filial:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Manzil:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Zona / Joy:</b> {html.escape(zone_name)} ({quantity} ta joy)\n"
                    f"📅 <b>Sana:</b> {date_str}\n"
                    f"⏰ <b>Vaqt:</b> {time_str}\n"
                    f"💰 <b>Jami summa:</b> {price_str}\n"
                    f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"ℹ️ <i>Iltimos, belgilangan vaqtdan 5-10 daqiqa oldinroq tashrif buyurishingizni so‘raymiz. Sizni kutamiz!</i>"
                )
        elif event_type == Booking.Status.PENDING_CONFIRMATION:
            if language == "ru":
                text = (
                    f"⏳ <b>Ваша бронь принята в обработку!</b>\n"
                    f"<i>Администратор клуба скоро подтвердит её.</i>\n\n"
                    f"🎮 <b>Клуб:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Филиал:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Адрес:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Зона / Место:</b> {html.escape(zone_name)} ({quantity} мест)\n"
                    f"📅 <b>Дата:</b> {date_str}\n"
                    f"⏰ <b>Время:</b> {time_str}\n"
                    f"💰 <b>Итоговая сумма:</b> {price_str}\n"
                    f"🔖 <b>Номер брони:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"🔔 <i>Мы пришлем уведомление сразу после подтверждения.</i>"
                )
            elif language == "en":
                text = (
                    f"⏳ <b>Booking request received!</b>\n"
                    f"<i>The club administrator will confirm it shortly.</i>\n\n"
                    f"🎮 <b>Club:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Branch:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Address:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Zone:</b> {html.escape(zone_name)} ({quantity} place(s))\n"
                    f"📅 <b>Date:</b> {date_str}\n"
                    f"⏰ <b>Time:</b> {time_str}\n"
                    f"💰 <b>Total price:</b> {price_str}\n"
                    f"🔖 <b>Booking ID:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"🔔 <i>We will notify you once confirmed.</i>"
                )
            else:
                text = (
                    f"⏳ <b>Broningiz qabul qilindi!</b>\n"
                    f"<i>Klub administratori tez orada bronni tasdiqlaydi.</i>\n\n"
                    f"🎮 <b>Klub:</b> {html.escape(club_name)}\n"
                    f"🏢 <b>Filial:</b> {html.escape(branch_name)}\n"
                    f"{f'📍 <b>Manzil:</b> {html.escape(address)}\n' if address else ''}"
                    f"🕹 <b>Zona / Joy:</b> {html.escape(zone_name)} ({quantity} ta joy)\n"
                    f"📅 <b>Sana:</b> {date_str}\n"
                    f"⏰ <b>Vaqt:</b> {time_str}\n"
                    f"💰 <b>Jami summa:</b> {price_str}\n"
                    f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>\n\n"
                    f"🔔 <i>Bron tasdiqlanishi bilan sizga xabar yuboramiz.</i>"
                )
        elif event_type == Booking.Status.CANCELLED:
            if language == "ru":
                text = (
                    f"❌ <b>Ваша бронь отменена</b>\n\n"
                    f"🎮 <b>Клуб:</b> {html.escape(club_name)} ({html.escape(branch_name)})\n"
                    f"🕹 <b>Зона:</b> {html.escape(zone_name)}\n"
                    f"📅 <b>Дата и время:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Номер брони:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Причина:</b> {html.escape(reason)}"
                )
            elif language == "en":
                text = (
                    f"❌ <b>Your booking has been cancelled</b>\n\n"
                    f"🎮 <b>Club:</b> {html.escape(club_name)} ({html.escape(branch_name)})\n"
                    f"🕹 <b>Zone:</b> {html.escape(zone_name)}\n"
                    f"📅 <b>Date & time:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Booking ID:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Reason:</b> {html.escape(reason)}"
                )
            else:
                text = (
                    f"❌ <b>Broningiz bekor qilindi</b>\n\n"
                    f"🎮 <b>Klub:</b> {html.escape(club_name)} ({html.escape(branch_name)})\n"
                    f"🕹 <b>Zona:</b> {html.escape(zone_name)}\n"
                    f"📅 <b>Sana va vaqt:</b> {date_str} {time_str}\n"
                    f"🔖 <b>Bron raqami:</b> <code>#{booking.booking_number}</code>\n"
                    f"ℹ️ <b>Sabab:</b> {html.escape(reason)}"
                )
        else:
            return None, None

    reply_markup = build_user_keyboard(language)
    return text, reply_markup


def send_customer_booking_notification(booking, event_type, client=None):
    """Mijozning shaxsiy Telegram botiga bron holati haqida tartibli xabar jo'natadi."""
    try:
        if not isinstance(booking, Booking):
            booking = (
                Booking.objects.select_related(
                    "user__profile",
                    "zone__branch__club",
                    "barber__club",
                    "barber__branch",
                    "cancellation",
                )
                .filter(pk=booking)
                .first()
            )
            if not booking:
                return

        user = getattr(booking, "user", None)
        if not user:
            return

        profile = getattr(user, "profile", None)
        if profile and profile.telegram_notifications_enabled is False:
            return

        chat_id = None
        if profile and profile.telegram_chat_id and profile.telegram_chat_id.strip():
            chat_id = profile.telegram_chat_id.strip()
        elif getattr(user, "telegram_user_id", None):
            chat_id = str(user.telegram_user_id)

        if not chat_id:
            logger.info("Cannot send customer booking notification: User #%s has no telegram chat_id or telegram_user_id", user.id)
            return

        language = (profile.preferred_language if profile and profile.preferred_language else "uz")
        text, reply_markup = build_customer_booking_message_and_keyboard(booking, event_type, language)
        if not text:
            return

        client = client or TelegramClient()
        from telegram_bot.handlers import safe_send_message
        safe_send_message(client, chat_id, text, reply_markup=reply_markup)
        logger.info("Successfully sent customer booking notification (%s) to chat_id %s", event_type, chat_id)
    except Exception as err:
        logger.warning("send_customer_booking_notification failed for booking #%s: %s", getattr(booking, "id", "-"), err)


@transaction.atomic
def confirm_booking(booking_id, actor_id, actor_name=""):
    booking = (
        Booking.objects.select_for_update()
        .select_related("user__profile", "zone__branch__club", "barber__club", "barber__branch")
        .get(pk=booking_id)
    )
    booking.transition_to(Booking.Status.CONFIRMED)
    _record_action(booking, actor_id, actor_name)
    try:
        queue_booking_message(booking)
    except Exception:
        pass
    send_customer_booking_notification(booking, Booking.Status.CONFIRMED)
    return booking


@transaction.atomic
def cancel_booking_from_telegram(
    booking_id,
    reason_code,
    actor_id,
    actor_name="",
    language="uz",
):
    booking = (
        Booking.objects.select_for_update()
        .select_related("user__profile", "zone__branch__club", "barber__club", "barber__branch")
        .get(pk=booking_id)
    )
    if booking.status not in (
        Booking.Status.PENDING_CONFIRMATION,
        Booking.Status.CONFIRMED,
    ):
        raise ValidationError("bookings.only_confirmed_can_cancel", code="bookings.only_confirmed_can_cancel")
    reason = TelegramCancellationReason.objects.filter(
        code=reason_code,
        is_active=True,
    ).first()
    if not reason:
        raise ValidationError("telegram.invalid_cancel_reason", code="telegram.invalid_cancel_reason")
    booking.transition_to(Booking.Status.CANCELLED)
    Cancellation.objects.create(
        booking=booking,
        source=Cancellation.Source.TELEGRAM,
        actor_name=actor_name,
        reason=reason.get_reason(language),
    )
    _record_action(booking, actor_id, actor_name)
    try:
        queue_booking_message(booking)
    except Exception:
        pass
    send_customer_booking_notification(booking, Booking.Status.CANCELLED)
    if booking.zone:
        from apps.bookings.services import invalidate_branch_availability
        invalidate_branch_availability(booking.zone.branch_id)
    return booking


def process_confirmation_timeouts(now=None):
    settings = TelegramBotSettings.objects.get_or_create(pk=1)[0]
    if not settings.auto_confirm_enabled:
        return 0
    now = now or timezone.now()
    threshold = now - timedelta(
        minutes=settings.confirmation_timeout_minutes
    )
    booking_ids = Booking.objects.filter(
        status=Booking.Status.PENDING_CONFIRMATION,
        created_at__lte=threshold,
        zone__branch__auto_confirm_booking=True,
    ).values_list("id", flat=True)
    confirmed = 0
    for booking_id in booking_ids:
        try:
            confirm_booking(booking_id, None, "AUTO_CONFIRM")
            confirmed += 1
        except ValidationError:
            continue
    return confirmed


def _record_action(booking, actor_id, actor_name):
    TelegramBookingMessage.objects.filter(booking=booking).update(
        acted_by_telegram_id=actor_id,
        acted_by_name=actor_name,
        acted_at=timezone.now(),
    )
