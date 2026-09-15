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


def _booking_values(booking):
    local_timezone = ZoneInfo(booking.zone.branch.timezone)
    starts_at = timezone.localtime(booking.starts_at, local_timezone)
    ends_at = timezone.localtime(booking.ends_at, local_timezone)
    cancellation = getattr(booking, "cancellation", None)
    return {
        "booking_number": booking.booking_number,
        "branch": booking.zone.branch.name,
        "zone": booking.zone.name,
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


def send_customer_booking_notification(booking, event_type, client=None):
    """Mijozning shaxsiy Telegram botiga bron holati haqida xabar jo'natadi."""
    profile = getattr(booking.user, "profile", None)
    if not profile or not profile.telegram_chat_id or not profile.telegram_notifications_enabled:
        return

    client = client or TelegramClient()
    language = profile.preferred_language or "uz"
    local_tz = ZoneInfo(booking.zone.branch.timezone)
    starts = timezone.localtime(booking.starts_at, local_tz)
    ends = timezone.localtime(booking.ends_at, local_tz)

    club_name = booking.zone.branch.club.name
    branch_name = booking.zone.branch.name
    zone_name = booking.zone.name
    date_str = starts.strftime("%d.%m.%Y")
    time_str = f"{starts.strftime('%H:%M')} – {ends.strftime('%H:%M')}"

    if event_type == Booking.Status.CONFIRMED:
        if language == "ru":
            text = (
                f"✅ <b>Ваша бронь подтверждена!</b>\n\n"
                f"🎮 <b>Клуб:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Зона:</b> {zone_name}\n"
                f"📅 <b>Дата:</b> {date_str}\n"
                f"⏰ <b>Время:</b> {time_str}\n"
                f"🔢 <b>Номер брони:</b> <code>{booking.booking_number}</code>\n\n"
                f"Ждем вас в клубе!"
            )
        elif language == "en":
            text = (
                f"✅ <b>Your booking is confirmed!</b>\n\n"
                f"🎮 <b>Club:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Zone:</b> {zone_name}\n"
                f"📅 <b>Date:</b> {date_str}\n"
                f"⏰ <b>Time:</b> {time_str}\n"
                f"🔢 <b>Booking Number:</b> <code>{booking.booking_number}</code>\n\n"
                f"We look forward to your visit!"
            )
        else:
            text = (
                f"✅ <b>Sizning broningiz tasdiqlandi!</b>\n\n"
                f"🎮 <b>Klub:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Zona:</b> {zone_name}\n"
                f"📅 <b>Sana:</b> {date_str}\n"
                f"⏰ <b>Vaqt:</b> {time_str}\n"
                f"🔢 <b>Bron raqami:</b> <code>{booking.booking_number}</code>\n\n"
                f"Sizni klubimizda kutamiz!"
            )
    elif event_type == Booking.Status.CANCELLED:
        cancellation = getattr(booking, "cancellation", None)
        reason = cancellation.reason if cancellation else "-"
        if language == "ru":
            text = (
                f"❌ <b>Бронь #{booking.booking_number} отменена</b>\n\n"
                f"🎮 <b>Клуб:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Зона:</b> {zone_name}\n"
                f"📅 <b>Дата:</b> {date_str} {time_str}\n"
                f"ℹ️ <b>Причина:</b> {reason}"
            )
        elif language == "en":
            text = (
                f"❌ <b>Booking #{booking.booking_number} has been cancelled</b>\n\n"
                f"🎮 <b>Club:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Zone:</b> {zone_name}\n"
                f"📅 <b>Date:</b> {date_str} {time_str}\n"
                f"ℹ️ <b>Reason:</b> {reason}"
            )
        else:
            text = (
                f"❌ <b>Bron #{booking.booking_number} bekor qilindi</b>\n\n"
                f"🎮 <b>Klub:</b> {club_name} ({branch_name})\n"
                f"📍 <b>Zona:</b> {zone_name}\n"
                f"📅 <b>Sana:</b> {date_str} {time_str}\n"
                f"ℹ️ <b>Sabab:</b> {reason}"
            )
    else:
        return

    try:
        client.send_message(profile.telegram_chat_id, text)
    except Exception:
        pass


@transaction.atomic
def confirm_booking(booking_id, actor_id, actor_name=""):
    booking = Booking.objects.select_for_update().select_related("user__profile", "zone__branch__club").get(pk=booking_id)
    booking.transition_to(Booking.Status.CONFIRMED)
    _record_action(booking, actor_id, actor_name)
    queue_booking_message(booking)
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
    booking = Booking.objects.select_for_update().select_related("user__profile", "zone__branch__club").get(pk=booking_id)
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
    queue_booking_message(booking)
    send_customer_booking_notification(booking, Booking.Status.CANCELLED)
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
