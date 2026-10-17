"""Private, owner-scoped barber booking decisions in Telegram."""
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.bookings.models import Booking
from apps.bookings.services import cancel_booking, transition_booking_for_operator


def _owned_booking(booking_id, telegram_id, chat_id):
    if not telegram_id or not chat_id or str(chat_id) != str(telegram_id):
        raise PermissionError
    return Booking.objects.select_related("barber__user").get(
        pk=booking_id, barber__user__telegram_user_id=telegram_id,
    )


def _state_key(telegram_id, chat_id):
    return f"barber-cancellation:{telegram_id}:{chat_id}"


def handle_barber_callback(client, callback):
    data = callback.get("data", "")
    if not data.startswith(("barber_accept:", "barber_cancel:")):
        return False
    callback_id = callback["id"]
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    telegram_id = callback.get("from", {}).get("id")
    try:
        action, booking_id = data.split(":", 1)
        booking = _owned_booking(booking_id, telegram_id, chat_id)
        if action == "barber_accept":
            transition_booking_for_operator(booking.barber.user, booking.pk, Booking.Status.CONFIRMED)
            client.answer_callback(callback_id, "Bron qabul qilindi.")
            client.edit_markup(chat_id, message["message_id"], {"inline_keyboard": []})
        else:
            if booking.status not in (Booking.Status.PENDING_CONFIRMATION, Booking.Status.CONFIRMED):
                raise ValidationError("Bu bronni bekor qilib bo‘lmaydi.")
            prompt = client.send_message(
                chat_id,
                f"#{booking.booking_number} bronini bekor qilish sababini yozing (500 belgigacha). Bekor qilmaslik uchun /cancel yozing.",
                reply_markup={"force_reply": True, "selective": True, "input_field_placeholder": "Bekor qilish sababi"},
            )
            cache.set(_state_key(telegram_id, chat_id), {
                "booking_id": str(booking.pk), "prompt_id": prompt["message_id"],
                "original_message_id": message["message_id"],
            }, timeout=900)
            client.answer_callback(callback_id, "Bekor qilish sababini yuboring.")
    except (PermissionError, ValueError, KeyError, ObjectDoesNotExist, ValidationError):
        client.answer_callback(callback_id, "Bu amalni bajarib bo‘lmaydi yoki bron sizga tegishli emas.")
    return True


def handle_barber_reason(client, message):
    telegram_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    state = cache.get(_state_key(telegram_id, chat_id))
    if not state or str(chat_id) != str(telegram_id):
        return False
    text = (message.get("text") or "").strip()
    if text == "/cancel":
        cache.delete(_state_key(telegram_id, chat_id))
        client.send_message(chat_id, "Bekor qilish to‘xtatildi. Bron saqlandi.")
        return True
    if message.get("reply_to_message", {}).get("message_id") != state["prompt_id"]:
        return False
    if not text or len(text) > 500 or text.startswith("/"):
        client.send_message(chat_id, "Sababni 1–500 belgi bilan, so‘ralgan xabarga javob sifatida yozing.")
        return True
    try:
        booking = _owned_booking(state["booking_id"], telegram_id, chat_id)
        cancel_booking(booking.barber.user, booking.pk, text, operator=True)
        cache.delete(_state_key(telegram_id, chat_id))
        client.send_message(chat_id, "Bron bekor qilindi. Sabab saqlandi va mijozga xabar yuborildi.")
        client.edit_markup(chat_id, state["original_message_id"], {"inline_keyboard": []})
    except (PermissionError, ObjectDoesNotExist, ValidationError):
        cache.delete(_state_key(telegram_id, chat_id))
        client.send_message(chat_id, "Bu bronni bekor qilib bo‘lmadi. Holatini tekshiring.")
    return True
