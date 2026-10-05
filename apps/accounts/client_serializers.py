from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.accounts.managers import normalize_phone, normalize_username
from apps.accounts.models import User, UserProfile
from apps.accounts.validators import phone_validator, username_validator


class ClientCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=30)
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128, trim_whitespace=False, error_messages={"min_length": "auth.client_weak_password", "max_length": "auth.client_weak_password"})

    def validate_username(self, value):
        value = normalize_username(value)
        try:
            username_validator(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError("auth.invalid_username_format") from error
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("auth.username_unavailable")
        return value

    def validate_phone(self, value):
        value = normalize_phone(value)
        try:
            phone_validator(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError("auth.invalid_phone_format") from error
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("auth.phone_already_registered")
        return value

    def validate(self, attrs):
        forbidden = {"role", "is_staff", "is_superuser", "status"} & self.initial_data.keys()
        if forbidden:
            raise serializers.ValidationError("auth.client_creation_forbidden")
        try:
            validate_password(attrs["password"], User(username=attrs["username"], phone=attrs["phone"]))
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": "auth.client_weak_password"}) from error
        return attrs

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        try:
            with transaction.atomic():
                user = User.objects.create_user(**validated_data, role=User.Role.CLIENT)
                UserProfile.objects.update_or_create(user=user, defaults={"full_name": full_name})
                return user
        except IntegrityError as error:
            raise serializers.ValidationError("auth.username_unavailable") from error
