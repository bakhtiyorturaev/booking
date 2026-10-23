from django.core.exceptions import ValidationError as DjangoValidationError
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
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        error_messages={"max_length": "auth.invalid_phone_format"},
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

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            return ""
        try:
            phone_validator(phone)
        except DjangoValidationError as error:
            raise serializers.ValidationError("auth.invalid_phone_format", code="auth.invalid_phone_format") from error
        user = self.context["request"].user
        if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("auth.phone_already_registered", code="auth.phone_already_registered")
        return phone

    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("auth.invalid_birth_date", code="auth.invalid_birth_date")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        phone = validated_data.pop("phone", None)
        if phone:
            user = self.context["request"].user
            if user.phone != phone:
                user.phone = phone
                # Foydalanuvchi o'zi kiritgan raqam TASDIQLANMAGAN hisoblanadi —
                # Telegram "Raqamni yuborish" tugmasi orqali qayta tasdiqlanishi
                # kerak. Aks holda eski `telegram_verified_at` saqlanib qolib,
                # `is_phone_verified` har qanday raqam uchun True bo'lib qolardi.
                user.phone_verified_at = None
                user.save(update_fields=["phone", "phone_verified_at", "updated_at"])
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def create(self, validated_data):
        raise NotImplementedError


def cabinet_sections(user):
    from django.db.models import Q
    sections = []
    if user.owned_clubs.exists():
        sections.extend(["clubs", "branches"])
    if hasattr(user, "barber_profile") or user.owned_clubs.filter(
        Q(category="BARBERSHOP") | Q(service_type__code="BARBER") | Q(available_services__code__in=["BARBERSHOP", "BARBER"])
    ).exists():
        sections.append("barbers")
    return sections


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_phone_verified = serializers.BooleanField(read_only=True)

    cabinet_sections = serializers.SerializerMethodField()

    def get_cabinet_sections(self, obj):
        return cabinet_sections(obj)

    has_owned_clubs = serializers.SerializerMethodField()

    def get_has_owned_clubs(self, obj):
        return obj.owned_clubs.exists()

    has_barber_profile = serializers.SerializerMethodField()

    def get_has_barber_profile(self, obj):
        return hasattr(obj, "barber_profile")

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "phone",
            "telegram_user_id",
            "role",
            "status",
            "is_staff",
            "is_superuser",
            "has_barber_profile",
            "has_owned_clubs",
            "cabinet_sections",
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
    password_expired = serializers.BooleanField(
        source="is_password_expired",
        read_only=True,
    )

    cabinet_sections = serializers.SerializerMethodField()

    def get_cabinet_sections(self, obj):
        return cabinet_sections(obj)

    has_owned_clubs = serializers.SerializerMethodField()

    def get_has_owned_clubs(self, obj):
        return obj.owned_clubs.exists()

    has_barber_profile = serializers.SerializerMethodField()

    def get_has_barber_profile(self, obj):
        return hasattr(obj, "barber_profile")

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
            "is_staff",
            "is_superuser",
            "has_barber_profile",
            "has_owned_clubs",
            "cabinet_sections",
            "preferred_language",
            "is_phone_verified",
            "is_profile_completed",
            "password_expired",
        )
        read_only_fields = fields


class StaffPasswordLoginSerializer(serializers.Serializer):
    login_type = serializers.ChoiceField(choices=["", "staff", "client"], required=False, default="")
    login = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "auth.login_required",
            "blank": "auth.login_required",
        },
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "auth.password_required",
            "blank": "auth.password_required",
        },
    )
    device_name = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        default="",
    )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "auth.old_password_required",
            "blank": "auth.old_password_required",
        },
    )
    new_password = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=6,
        write_only=True,
        error_messages={
            "required": "auth.new_password_required",
            "blank": "auth.new_password_required",
            "min_length": "auth.password_too_short",
        },
    )
    confirm_password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "auth.confirm_password_required",
            "blank": "auth.confirm_password_required",
        },
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "auth.password_mismatch"},
                code="auth.password_mismatch",
            )
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "auth.password_same_as_old"},
                code="auth.password_same_as_old",
            )
        return attrs


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


class TelegramCodeVerifySerializer(serializers.Serializer):
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=10,
        trim_whitespace=True,
        error_messages={
            "required": "auth.code_required",
            "blank": "auth.code_required",
        },
    )
    session_id = serializers.CharField(
        max_length=64,
        required=True,
        allow_blank=False,
    )
    device_name = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        default="",
    )
