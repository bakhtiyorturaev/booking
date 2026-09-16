import html
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.bookings.models import Booking, Cancellation
from apps.developer_bot.models import DeveloperBotSettings
from apps.developer_bot.services import (
    clear_developer_bot_settings_cache,
    notify_developer_async,
)


def _get_tashkent_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Tashkent")
    except Exception:
        from datetime import timezone, timedelta
        return timezone(timedelta(hours=5))


def _after_commit(title, message, category):
    transaction.on_commit(
        lambda: notify_developer_async(
            title,
            message,
            category=category,
        )
    )


def _format_booking_details(booking):
    try:
        user = booking.user
        full_name = getattr(getattr(user, "profile", None), "full_name", "") or "Ko‘rsatilmagan"
        phone = user.phone or "Ko‘rsatilmagan"
        tg_user = (
            f"@{user.username}"
            if user.username and not user.username.startswith("tg_")
            else (f"ID: {user.telegram_user_id}" if getattr(user, "telegram_user_id", None) else "-")
        )

        if booking.barber_id:
            barber = booking.barber
            target_label = "Sartarosh"
            target_name = barber.full_name if barber else "-"
            branch_name = barber.branch.name if barber and barber.branch else "-"
            club_name = barber.branch.club.name if barber and barber.branch and barber.branch.club else "-"
        elif booking.zone_id:
            zone = booking.zone
            target_label = "Zona / Joy"
            target_name = zone.name if zone else "-"
            branch_name = zone.branch.name if zone and zone.branch else "-"
            club_name = zone.branch.club.name if zone and zone.branch and zone.branch.club else "-"
        else:
            target_label = "Xizmat"
            target_name = "-"
            branch_name = "-"
            club_name = "-"

        tz = _get_tashkent_tz()
        start_local = booking.starts_at.astimezone(tz)
        end_local = booking.ends_at.astimezone(tz)
        date_str = start_local.strftime("%d.%m.%Y")
        time_str = f"{start_local.strftime('%H:%M')} – {end_local.strftime('%H:%M')}"

        if booking.total_price_tiyin and booking.total_price_tiyin > 0:
            price_str = f"{booking.total_price_tiyin // 100:,} so‘m".replace(",", " ")
        else:
            price_str = "Joyida kelishiladi (0 so‘m)"

        status_map = {
            Booking.Status.PENDING_CONFIRMATION: "⏳ Kutilmoqda (PENDING)",
            Booking.Status.CONFIRMED: "✅ Tasdiqlangan (CONFIRMED)",
            Booking.Status.CHECKED_IN: "🚪 Tashrif buyurdi (CHECKED_IN)",
            Booking.Status.COMPLETED: "🏁 Yakunlandi (COMPLETED)",
            Booking.Status.CANCELLED: "❌ Bekor qilindi (CANCELLED)",
            Booking.Status.NO_SHOW: "⚠️ Kelmadi (NO_SHOW)",
        }
        status_display = status_map.get(booking.status, booking.status)

        lines = [
            f"<b>Bron raqami:</b> <code>#{booking.booking_number}</code>",
            f"<b>Mijoz:</b> {html.escape(full_name)}",
            f"<b>Telefon:</b> <code>{html.escape(phone)}</code>",
            f"<b>Telegram:</b> {html.escape(tg_user)}",
            f"<b>{target_label}:</b> {html.escape(target_name)}",
            f"<b>Filial:</b> {html.escape(branch_name)} ({html.escape(club_name)})",
            f"<b>Sana:</b> {date_str}",
            f"<b>Vaqt:</b> {time_str} (Toshkent vaqti)",
            f"<b>Narx:</b> {price_str}",
            f"<b>Holat:</b> {status_display}",
        ]
        return "\n".join(lines)
    except Exception as err:
        return f"Booking #{getattr(booking, 'booking_number', booking.pk)}; Status: {booking.status}; Error: {err}"


def _format_user_details(user):
    try:
        full_name = getattr(getattr(user, "profile", None), "full_name", "") or "Ko‘rsatilmagan"
        phone = user.phone or "Kiritilmagan"
        tg_user = (
            f"@{user.username}"
            if user.username and not user.username.startswith("tg_")
            else (f"ID: {user.telegram_user_id}" if getattr(user, "telegram_user_id", None) else "-")
        )
        role = getattr(user, "role", "CUSTOMER")

        lines = [
            f"<b>Foydalanuvchi:</b> {html.escape(full_name)}",
            f"<b>Telefon:</b> <code>{html.escape(phone)}</code>",
            f"<b>Telegram:</b> {html.escape(tg_user)}",
            f"<b>Rol:</b> {html.escape(role)}",
            f"<b>User ID:</b> <code>{user.pk}</code>",
        ]
        return "\n".join(lines)
    except Exception:
        return f"User ID: {user.pk}"


def _format_cancellation_details(cancellation):
    try:
        booking = getattr(cancellation, "booking", None)
        user = getattr(cancellation, "requested_by", None)
        booking_num = booking.booking_number if booking else str(cancellation.booking_id)
        user_name = getattr(getattr(user, "profile", None), "full_name", "") or (user.username if user else "Noma'lum")
        reason = getattr(cancellation, "reason", "") or "Sabab ko‘rsatilmagan"

        lines = [
            f"<b>Bron raqami:</b> <code>#{booking_num}</code>",
            f"<b>Bekor qilgan:</b> {html.escape(user_name)}",
            f"<b>Sabab:</b> {html.escape(reason)}",
        ]
        return "\n".join(lines)
    except Exception:
        return f"Booking ID: {cancellation.booking_id}; user ID: {cancellation.requested_by_id}"


@receiver(
    post_save,
    sender=DeveloperBotSettings,
    dispatch_uid="developer_bot_settings_cache",
)
def clear_settings_cache(sender, **kwargs):
    clear_developer_bot_settings_cache()


@receiver(post_save, sender=User, dispatch_uid="developer_bot_user_created")
def notify_user_created(sender, instance, created, **kwargs):
    if created:
        _after_commit(
            "Yangi foydalanuvchi ro‘yxatdan o‘tdi",
            _format_user_details(instance),
            "notify_user_events",
        )


@receiver(post_save, sender=Booking, dispatch_uid="developer_bot_booking_saved")
def notify_booking_saved(sender, instance, created, **kwargs):
    event = "Yangi bron qabul qilindi" if created else f"Bron holati o‘zgardi (#{instance.booking_number})"
    _after_commit(
        event,
        _format_booking_details(instance),
        "notify_booking_events",
    )


@receiver(
    post_save,
    sender=Cancellation,
    dispatch_uid="developer_bot_booking_cancelled",
)
def notify_booking_cancelled(sender, instance, created, **kwargs):
    if created:
        _after_commit(
            "Bron bekor qilindi",
            _format_cancellation_details(instance),
            "notify_booking_events",
        )
