from django.conf import settings
import requests

from telegram_bot.models import TelegramBotSettings


class TelegramClient:
    def __init__(self, token=None, request_timeout=None):
        self.token_override = token
        self.request_timeout_override = request_timeout

    def _connection(self):
        configuration = TelegramBotSettings.objects.filter(pk=1).first()
        token = (
            self.token_override
            or (configuration.bot_token if configuration and configuration.bot_token else "")
            or getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
        )
        if not token:
            raise RuntimeError(
                "Telegram bot sozlamalarini Django admin orqali kiriting yoki TELEGRAM_BOT_TOKEN ni .env da ko‘rsating."
            )
        timeout = self.request_timeout_override or (
            configuration.request_timeout_seconds if configuration else 20
        )
        return token, timeout, configuration

    def request(self, method, request_timeout=None, **payload):
        token, default_timeout, _ = self._connection()
        response = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload,
            timeout=request_timeout or default_timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram API error"))
        return data["result"]

    def get_updates(self, offset=None, timeout=None):
        _, _, configuration = self._connection()
        timeout = timeout or (
            configuration.polling_timeout_seconds if configuration else 25
        )
        payload = {"timeout": timeout, "allowed_updates": ["callback_query", "message"]}
        if offset is not None:
            payload["offset"] = offset
        return self.request("getUpdates", request_timeout=timeout + 5, **payload)

    def send_message(self, chat_id, text, reply_markup=None, parse_mode="HTML"):
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self.request("sendMessage", **payload)

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        return self.request(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )

    def edit_markup(self, chat_id, message_id, reply_markup):
        return self.request(
            "editMessageReplyMarkup",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )

    def answer_callback(self, callback_id, text=""):
        return self.request("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def is_group_admin(self, chat_id, user_id):
        member = self.request("getChatMember", chat_id=chat_id, user_id=user_id)
        return member["status"] in ("administrator", "creator")
