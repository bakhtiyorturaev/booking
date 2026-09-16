import html
import logging
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

logger = logging.getLogger(__name__)


def get_safe_webapp_url():
    url = getattr(settings, "TELEGRAM_MINIAPP_URL", "") or getattr(settings, "FRONTEND_URL", "") or "https://rezervuz.uz"
    url = url.strip()
    if not url.startswith("https://"):
        if url.startswith("http://"):
            url = "https://" + url[7:]
        else:
            url = "https://" + url
    return url


def get_safe_frontend_url():
    url = getattr(settings, "FRONTEND_URL", "") or "https://rezervuz.uz"
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")


def build_user_keyboard(language="uz", site_url=None):
    miniapp_url = get_safe_webapp_url()
    buttons = []
    if site_url:
        site_text = "🌐 Saytga o‘tish" if language == "uz" else ("🌐 Перейти на сайт" if language == "ru" else "🌐 Open Website")
        buttons.append([{"text": site_text, "url": site_url}])

    miniapp_text = "🎮 RezervUZ ilovasini ochish" if language == "uz" else ("🎮 Открыть приложение" if language == "ru" else "🎮 Open Mini App")
    if miniapp_url.startswith("https://"):
        buttons.append([{"text": miniapp_text, "web_app": {"url": miniapp_url}}])
    else:
        buttons.append([{"text": miniapp_text, "url": miniapp_url}])

    return {"inline_keyboard": buttons}


def safe_send_message(client, chat_id, text, reply_markup=None):
    if not chat_id:
        return
    try:
        client.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as err:
        logger.warning("Telegram HTML sendMessage failed for chat_id=%s: %s", chat_id, err)
        try:
            # Fallback without markup
            client.send_message(chat_id, text, reply_markup=None, parse_mode="HTML")
        except Exception as html_err:
            logger.warning("Telegram fallback HTML failed: %s", html_err)
            try:
                # Fallback plain text without parse_mode
                plain_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                client.send_message(chat_id, plain_text, reply_markup=None, parse_mode=None)
            except Exception as final_err:
                logger.exception("Failed to send telegram message to chat_id=%s: %s", chat_id, final_err)


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

    default_keyboard = build_user_keyboard(language)

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
                "✅ <b>Telefon raqamingiz muvaffaqiyatli saqlandi!</b>\n\n"
                "Endi bemalol o‘yin klublari va sartaroshxonalarni bron qilishingiz mumkin 👇"
                if language == "uz"
                else (
                    "✅ <b>Ваш номер телефона успешно сохранен!</b>\n\n"
                    "Теперь вы можете бронировать места в клубах и барбершопах 👇"
                    if language == "ru"
                    else "✅ <b>Your phone number has been saved!</b>\n\n"
                    "You can now proceed with your bookings 👇"
                )
            )
            safe_send_message(client, chat_id, success_text, default_keyboard)
            return

    # 2. Agar web login deep-link bo'lsa: /start login_<token>
    if text.startswith("/start") and "login_" in text:
        parts = text.split()
        token = ""
        for p in parts:
            if "login_" in p:
                token = p.split("login_", 1)[1].strip()
                break

        confirmed = False
        if token:
            confirmed = confirm_web_login_from_bot(token, user)

        raw_user_name = user.get("first_name", "").strip() or "Foydalanuvchi"
        safe_user_name = html.escape(raw_user_name)

        if confirmed:
            frontend_url = get_safe_frontend_url()
            site_return_url = f"{frontend_url}?tg_login={token}" if token else frontend_url

            login_success_text = (
                f"✅ <b>Assalomu alaykum, {safe_user_name}!</b>\n\n"
                f"RezervUZ tizimiga muvaffaqiyatli kirdingiz.\n"
                f"Brauzeringizdagi sahifaga qayting yoki quyidagi tugma orqali to‘g‘ridan-to‘g‘ri saytga o‘ting 👇"
                if language == "uz"
                else (
                    f"✅ <b>Здравствуйте, {safe_user_name}!</b>\n\n"
                    f"Вы успешно вошли в систему RezervUZ.\n"
                    f"Вернитесь на страницу в браузере или перейдите по кнопке ниже 👇"
                    if language == "ru"
                    else (
                        f"✅ <b>Welcome, {safe_user_name}!</b>\n\n"
                        f"Successfully logged into RezervUZ.\n"
                        f"Return to your browser or click below to open the website 👇"
                    )
                )
            )
            login_keyboard = build_user_keyboard(language, site_url=site_return_url)
        else:
            login_success_text = (
                "⚠️ Kirish havolasi eskirgan yoki noto‘g‘ri. Iltimos, saytdan qayta urinib ko‘ring."
                if language == "uz"
                else "⚠️ Ссылка для входа устарела. Попробуйте снова на сайте."
            )
            login_keyboard = default_keyboard

        safe_send_message(client, chat_id, login_success_text, login_keyboard)
        return

    # 3. /start yoki har qanday xabar uchun doimiy javob
    raw_user_name = user.get("first_name", "").strip() or "Foydalanuvchi"
    safe_user_name = html.escape(raw_user_name)
    if language == "ru":
        greeting = (
            f"👋 <b>Здравствуйте, {safe_user_name}!</b>\n\n"
            f"<b>RezervUZ</b> — платформа онлайн-бронирования игровых клубов (PlayStation, PC) и барбершопов.\n\n"
            f"Нажмите кнопку ниже, чтобы открыть приложение и забронировать удобное время! 👇"
        )
    elif language == "en":
        greeting = (
            f"👋 <b>Hello, {safe_user_name}!</b>\n\n"
            f"Welcome to <b>RezervUZ</b> — online booking platform for gaming clubs (PlayStation, PC) and barbershops.\n\n"
            f"Tap the button below to open the app and reserve your spot! 👇"
        )
    else:
        greeting = (
            f"👋 <b>Assalomu alaykum, {safe_user_name}!</b>\n\n"
            f"<b>RezervUZ</b> — o‘yin klublari (PlayStation, PC) hamda sartaroshxonalarni onlayn bron qilish platformasiga xush kelibsiz.\n\n"
            f"Quyidagi tugma orqali platformani ochib, filiallarni ko‘rishingiz va o‘zingizga qulay vaqtni band qilishingiz mumkin! 👇"
        )

    safe_send_message(client, chat_id, greeting, default_keyboard)
