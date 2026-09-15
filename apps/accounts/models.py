import hashlib
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from apps.accounts.managers import (
    UserManager,
    normalize_phone,
    normalize_username,
)
from apps.accounts.validators import (
    phone_validator,
    username_validator,
)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        MODERATOR = "MODERATOR", "Moderator"
        ADMIN = "ADMIN", "Administrator"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"
        DELETED = "DELETED", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=30, unique=True, validators=[username_validator])
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True, validators=[phone_validator])
    telegram_user_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_verified_at = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    last_login = models.DateTimeField(null=True, blank=True, db_column="last_login_at")
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["role", "status"], name="users_role_status_idx")]

    def __str__(self):
        return self.username

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_phone_verified(self):
        return bool(self.phone and self.telegram_verified_at)

    def save(self, *args, **kwargs):
        self.username = normalize_username(self.username)
        if self.phone:
            self.phone = normalize_phone(self.phone)
        else:
            self.phone = None
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    class Language(models.TextChoices):
        UZ = "uz", "O‘zbek"
        RU = "ru", "Русский"
        EN = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.UZ)
    city = models.CharField(max_length=120, blank=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True)
    telegram_notifications_enabled = models.BooleanField(default=True)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def is_completed(self):
        return self.profile_completed_at is not None

    def mark_as_completed(self):
        if self.profile_completed_at is None:
            self.profile_completed_at = models.functions.Now()
            self.save(update_fields=["profile_completed_at", "updated_at"])


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_hash = models.CharField(max_length=64, unique=True)
    device_name = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_sessions"
        indexes = [
            models.Index(fields=["user"], name="session_user_idx"),
            models.Index(fields=["expires_at"], name="session_expires_at_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.device_name or 'Unknown device'}"

    @staticmethod
    def hash_refresh_token(raw_token):
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def set_refresh_token(self, raw_token):
        self.refresh_token_hash = self.hash_refresh_token(raw_token)

    def check_refresh_token(self, raw_token):
        return self.hash_refresh_token(raw_token) == self.refresh_token_hash

    @property
    def is_active(self):
        from django.utils import timezone
        return self.revoked_at is None and timezone.now() < self.expires_at

    def revoke(self):
        from django.utils import timezone
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])
