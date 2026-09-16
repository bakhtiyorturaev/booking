import re
import requests


class DeveloperTelegramClient:
    def __init__(self, token, chat_id, timeout=5):
        if not token:
            raise RuntimeError("DEVELOPER_BOT_TOKEN is not configured")
        if not chat_id:
            raise RuntimeError("DEVELOPER_BOT_CHAT_ID is not configured")

        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method, **payload):
        response = requests.post(
            f"{self.base_url}/{method}",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram API error"))
        return data["result"]

    def get_me(self):
        return self.request("getMe")

    def get_chat(self):
        return self.request("getChat", chat_id=self.chat_id)

    def send_message(self, text):
        try:
            return self.request(
                "sendMessage",
                chat_id=self.chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            clean_text = re.sub(r"<[^>]+>", "", text)
            return self.request(
                "sendMessage",
                chat_id=self.chat_id,
                text=clean_text[:4096],
                disable_web_page_preview=True,
            )

