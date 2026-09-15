from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.managers import normalize_phone
from apps.accounts.models import User, UserProfile
from apps.accounts.validators import phone_validator


class UserProfileSerializer(serializers.ModelSerializer):
    is_profile_completed = serializers.BooleanField(
        source="is_completed",
        read_only=True,
    )

    class Meta:
        model = UserProfile
        fields = (
            "full_name",
            "avatar_url",
            "birth_date",
            "preferred_language",
            "city",
            "telegram_notifications_enabled",
            "is_profile_completed",
        )
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        error_messages={"max_length": "auth.name_too_long"},
    )
    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={"invalid": "auth.invalid_birth_date"},
    )
    city = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        error_messages={"max_length": "auth.city_too_long"},
    )
    preferred_language = serializers.ChoiceField(
        choices=UserProfile.Language.choices,
        required=False,
    )

    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("auth.invalid_birth_date", code="auth.invalid_birth_date")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def create(self, validated_data):
        raise NotImplementedError


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "phone",
            "telegram_user_id",
            "role",
            "is_phone_verified",
            "profile",
        )
        read_only_fields = fields


class AuthUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        source="profile.full_name",
        read_only=True,
    )
    avatar_url = serializers.URLField(
        source="profile.avatar_url",
        read_only=True,
    )
    preferred_language = serializers.CharField(
        source="profile.preferred_language",
        read_only=True,
    )
    is_profile_completed = serializers.BooleanField(
        source="profile.is_completed",
        read_only=True,
    )
    is_phone_verified = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "phone",
            "telegram_user_id",
            "full_name",
            "avatar_url",
            "role",
            "preferred_language",
            "is_phone_verified",
            "is_profile_completed",
        )
        read_only_fields = fields


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "auth.refresh_token_missing",
            "blank": "auth.refresh_token_missing",
        },
    )


class TelegramMiniAppLoginSerializer(serializers.Serializer):
    init_data = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "auth.telegram_phone_permission_required",
            "blank": "auth.telegram_phone_permission_required",
        },
    )
    device_name = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        default="",
    )


class TelegramContactSerializer(serializers.Serializer):
    phone = serializers.CharField(
        max_length=20,
        required=True,
        allow_blank=False,
        error_messages={
            "required": "auth.phone_required",
            "blank": "auth.phone_required",
            "max_length": "auth.invalid_phone_format",
        },
    )

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError("auth.phone_required", code="auth.phone_required")
        try:
            phone_validator(phone)
        except Exception as error:
            raise serializers.ValidationError("auth.invalid_phone_format", code="auth.invalid_phone_format") from error
        return phone


class TelegramCodeExchangeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, allow_blank=False, max_length=2048)
    code_verifier = serializers.CharField(required=True, allow_blank=False, max_length=256)
    redirect_uri = serializers.URLField(required=True, allow_blank=False)
    device_name = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
