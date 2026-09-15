from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.accounts.models import User
from apps.accounts.services.telegram_web_login import confirm_web_login_from_bot
from apps.accounts.services.telegram_miniapp import save_telegram_contact
from telegram_bot.models import TelegramBookingMessage, TelegramGroup
from telegram_bot.services import (
    cancel_booking_from_telegram,
    cancellation_keyboard,
    confirm_booking,
    dispatch_pending_messages,
    translated_message,
)


def handle_callback(client, callback):
    callback_id = callback["id"]
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user = callback["from"]
    group = TelegramGroup.objects.filter(chat_id=chat_id, is_active=True).first()
    language = group.language if group else "uz"
    if not chat_id or not client.is_group_admin(chat_id, user["id"]):
        client.answer_callback(callback_id, translated_message("telegram.group_admin_only", language))
        return

    data = callback.get("data", "")
    try:
        action, value = data.split(":", 1)
        booking_id = value.split(":")[-1]
        if not TelegramBookingMessage.objects.filter(
            booking_id=booking_id,
            group__chat_id=chat_id,
        ).exists():
            raise ObjectDoesNotExist
        if action == "cancel":
            client.edit_markup(
                chat_id,
                message["message_id"],
                cancellation_keyboard(value, language),
            )
            client.answer_callback(callback_id)
            return
        actor_name = user.get("username") or user.get("first_name", "")
        if action == "confirm":
            confirm_booking(value, user["id"], actor_name)
        elif action == "reason":
            reason_code, booking_id = value.split(":", 1)
            cancel_booking_from_telegram(
                booking_id,
                reason_code,
                user["id"],
                actor_name,
                language,
            )
        else:
            raise ValueError
        dispatch_pending_messages(client, limit=1)
        client.answer_callback(callback_id, translated_message("telegram.action_completed", language))
    except (ValueError, ObjectDoesNotExist, ValidationError):
        client.answer_callback(callback_id, translated_message("telegram.action_cannot_be_completed", language))


def handle_message(client, message):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    user = message.get("from", {})
    contact = message.get("contact")
    language_code = user.get("language_code", "uz")[:2]
    language = language_code if language_code in ("uz", "ru", "en") else "uz"

    miniapp_url = getattr(settings, "TELEGRAM_MINIAPP_URL", "")
    if not miniapp_url:
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        miniapp_url = frontend_url

    webapp_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🎮 Klublarni ko‘rish va bron qilish" if language == "uz" else ("🎮 Открыть приложение" if language == "ru" else "🎮 Open Mini App"),
                    "web_app": {"url": miniapp_url},
                }
            ]
        ]
    }

    # 1. Agar foydalanuvchi kontakt yuborgan bo'lsa
    if contact:
        phone_number = contact.get("phone_number", "")
        contact_user_id = contact.get("user_id")
        if phone_number and (contact_user_id == user.get("id") or not contact_user_id):
            tg_user = User.objects.filter(telegram_user_id=user.get("id")).first()
            if tg_user:
                try:
                    save_telegram_contact(tg_user, phone_number)
                except Exception:
                    pass
            success_text = (
                "✅ <b>Telefon raqamingiz muvaffaqiyatli saqlandi!</b>\n\nEndi bemalol klublarni bron qilishingiz mumkin 👇"
                if language == "uz"
                else (
                    "✅ <b>Ваш номер телефона успешно сохранен!</b>\n\nТеперь вы можете бронировать места в клубах 👇"
                    if language == "ru"
                    else "✅ <b>Your phone number has been saved!</b>\n\nYou can now proceed with your bookings 👇"
                )
            )
            try:
                client.send_message(chat_id, success_text, webapp_keyboard)
            except Exception:
                pass
            return

    # 2. Agar web login deep-link bo'lsa: /start login_<token>
    if text.startswith("/start login_"):
        token = text.replace("/start login_", "").strip()
        confirmed = confirm_web_login_from_bot(token, user)
        if confirmed:
            login_success_text = (
                "✅ <b>Veb-saytga muvaffaqiyatli kirdingiz!</b>\n\nBrauzeringizga qaytib bron qilishni davom ettirishingiz mumkin."
                if language == "uz"
                else (
                    "✅ <b>Вы успешно вошли на сайте!</b>\n\nМожете вернуться в браузер и продолжить бронирование."
                    if language == "ru"
                    else "✅ <b>Successfully logged in on web!</b>\n\nYou can return to your browser now."
                )
            )
        else:
            login_success_text = (
                "⚠️ Kirish havolasi eskirgan yoki noto‘g‘ri. Iltimos, saytdan qayta urinib ko‘ring."
                if language == "uz"
                else "⚠️ Ссылка для входа устарела. Попробуйте снова на сайте."
            )
        try:
            client.send_message(chat_id, login_success_text, webapp_keyboard)
        except Exception:
            pass
        return

    # 3. Oddiy /start xabari
    if text.startswith("/start"):
        if language == "ru":
            greeting = (
                f"👋 <b>Здравствуйте, {user.get('first_name', '')}!</b>\n\n"
                f"Добро пожаловать в сервис онлайн-бронирования компьютерных и PlayStation клубов.\n\n"
                f"Нажмите кнопку ниже, чтобы открыть приложение и выбрать клуб! 👇"
            )
        elif language == "en":
            greeting = (
                f"👋 <b>Hello, {user.get('first_name', '')}!</b>\n\n"
                f"Welcome to the computer & PlayStation club booking service.\n\n"
                f"Tap the button below to browse clubs and book your seat! 👇"
            )
        else:
            greeting = (
                f"👋 <b>Assalomu alaykum, {user.get('first_name', '')}!</b>\n\n"
                f"Kompyuter va PlayStation klublarini onlayn bron qilish tizimiga xush kelibsiz.\n\n"
                f"Klublarni ko‘rish va joy band qilish uchun quyidagi tugmani bosing! 👇"
            )

        try:
            client.send_message(chat_id, greeting, webapp_keyboard)
        except Exception:
            pass
