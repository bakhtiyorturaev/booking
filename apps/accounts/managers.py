from django.contrib.auth.base_user import BaseUserManager

from apps.accounts.validators import (
    phone_validator,
    username_validator,
)


def normalize_phone(phone):
    if not phone:
        return ""

    phone = str(phone).strip()

    for character in (" ", "-", "(", ")"):
        phone = phone.replace(character, "")

    return phone


def normalize_username(username):
    if not username:
        return ""

    return str(username).strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(
        self,
        username,
        phone=None,
        password=None,
        **extra_fields,
    ):
        username = normalize_username(username)
        phone = normalize_phone(phone)

        if not username:
            raise ValueError("1006")

        telegram_user_id = extra_fields.get("telegram_user_id")
        if not phone and not telegram_user_id:
            raise ValueError("1002")

        username_validator(username)
        if phone:
            phone_validator(phone)

        user = self.model(
            username=username,
            phone=phone or None,
            **extra_fields,
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username,
        password=None,
        phone=None,
        **extra_fields,
    ):
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        extra_fields.setdefault("status", self.model.Status.ACTIVE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("1003")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("1004")

        return self.create_user(
            username=username,
            phone=phone or "+998900000000",
            password=password,
            **extra_fields,
        )
