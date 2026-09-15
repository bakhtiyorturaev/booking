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


def _after_commit(title, message, category):
    transaction.on_commit(
        lambda: notify_developer_async(
            title,
            message,
            category=category,
        )
    )


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
            "Yangi foydalanuvchi",
            f"User ID: {instance.pk}",
            "notify_user_events",
        )


@receiver(post_save, sender=Booking, dispatch_uid="developer_bot_booking_saved")
def notify_booking_saved(sender, instance, created, **kwargs):
    event = "Yangi bron" if created else "Bron holati o‘zgardi"
    _after_commit(
        event,
        (
            f"Booking ID: {instance.pk}; "
            f"raqam: {instance.booking_number}; "
            f"status: {instance.status}; user ID: {instance.user_id}"
        ),
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
            (
                f"Booking ID: {instance.booking_id}; "
                f"user ID: {instance.requested_by_id}"
            ),
            "notify_booking_events",
        )
