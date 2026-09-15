from django import forms


class SecretSettingsForm(forms.ModelForm):
    bot_token = forms.CharField(
        label="Bot token",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text=(
            "Token bazada shifrlangan holda saqlanadi. Mavjud tokenni "
            "o‘zgartirmaslik uchun maydonni bo‘sh qoldiring."
        ),
    )
    login_client_secret = forms.CharField(
        label="Telegram Login client secret",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="BotFather Login Widget secret. Mavjud qiymatni saqlash uchun bo‘sh qoldiring.",
    )

    def clean_bot_token(self):
        token = self.cleaned_data.get("bot_token", "").strip()
        if token:
            return token
        if self.instance and self.instance.pk:
            return self.instance.bot_token
        return ""

    def clean_login_client_secret(self):
        secret = self.cleaned_data.get("login_client_secret", "").strip()
        if secret:
            return secret
        if self.instance and self.instance.pk:
            return getattr(self.instance, "login_client_secret", "")
        return ""
