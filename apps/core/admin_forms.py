from django import forms


class SecretSettingsForm(forms.ModelForm):
    bot_token = forms.CharField(
        label='Bot token',
        required=False,
        widget=forms.TextInput(attrs={'style': 'width: 100%; max-width: 650px;', 'placeholder': '123456789:AAHbDmzEL...'}),
        help_text='Telegram BotFather dan olingan bot tokeni (ochiq korinishda).',
    )
    login_client_secret = forms.CharField(
        label='Telegram Login client secret',
        required=False,
        widget=forms.TextInput(attrs={'style': 'width: 100%; max-width: 650px;', 'placeholder': 'Client secret'}),
        help_text='BotFather Login Widget secret.',
    )

    def clean_bot_token(self):
        return self.cleaned_data.get('bot_token', '').strip()

    def clean_login_client_secret(self):
        return self.cleaned_data.get('login_client_secret', '').strip()
