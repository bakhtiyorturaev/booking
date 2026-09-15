from django.core.validators import RegexValidator


username_validator = RegexValidator(
    regex=r"^[a-zA-Z0-9_]{1,30}$",
    message="auth.invalid_username_format",
    code="auth.invalid_username_format",
)


phone_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{7,14}$",
    message="auth.invalid_phone_format",
    code="auth.invalid_phone_format",
)