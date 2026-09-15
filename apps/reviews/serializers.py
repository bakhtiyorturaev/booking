from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions, serializers

from apps.reviews.models import Review
from apps.reviews.services import create_review, update_review


def _raise_service_error(error):
    if isinstance(error, ObjectDoesNotExist):
        raise exceptions.NotFound("reviews.not_found", code="reviews.not_found") from error
    raise serializers.ValidationError(error.messages, code=error.code) from error


class ReviewSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(
        error_messages={"required": "reviews.booking_immutable", "invalid": "reviews.booking_immutable"},
    )

    class Meta:
        model = Review
        fields = (
            "id",
            "booking_id",
            "club_id",
            "barber_id",
            "rating",
            "barber_rating",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "club_id", "barber_id", "created_at", "updated_at")
        extra_kwargs = {
            "rating": {
                "error_messages": {
                    "required": "reviews.rating_invalid",
                    "invalid": "reviews.rating_invalid",
                    "min_value": "reviews.rating_invalid",
                    "max_value": "reviews.rating_invalid",
                }
            },
            "barber_rating": {
                "required": False,
                "allow_null": True,
            },
            "comment": {"error_messages": {"max_length": "reviews.comment_too_long"}},
        }

    def validate_booking_id(self, value):
        if self.instance and value != self.instance.booking_id:
            raise serializers.ValidationError("reviews.booking_immutable", code="reviews.booking_immutable")
        return value

    def create(self, validated_data):
        try:
            return create_review(
                user=self.context["request"].user,
                **validated_data,
            )
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _raise_service_error(error)

    def update(self, instance, validated_data):
        validated_data.pop("booking_id", None)
        try:
            return update_review(
                self.context["request"].user,
                instance,
                **validated_data,
            )
        except DjangoValidationError as error:
            _raise_service_error(error)


class PublicReviewSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "author", "rating", "comment", "created_at")

    def get_author(self, obj) -> str:
        profile = getattr(obj.user, "profile", None)
        return profile.full_name if profile and profile.full_name else obj.user.username
