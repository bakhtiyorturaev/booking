import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_add_user_subscription"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("price_tiyin", models.PositiveBigIntegerField()),
                ("duration_days", models.PositiveSmallIntegerField(default=30)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "subscription_plans",
                "ordering": ("price_tiyin", "duration_days"),
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.CheckConstraint(
                condition=Q(price_tiyin__gt=0),
                name="subscription_plan_positive_price",
            ),
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.CheckConstraint(
                condition=Q(duration_days__gt=0),
                name="subscription_plan_positive_duration",
            ),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("provider", models.CharField(max_length=30)),
                ("external_id", models.CharField(blank=True, db_index=True, max_length=150)),
                ("idempotency_key", models.CharField(max_length=100, unique=True)),
                ("amount_tiyin", models.PositiveBigIntegerField()),
                ("currency", models.CharField(default="UZS", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PAID", "Paid"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                            ("REFUNDED", "Refunded"),
                        ],
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                ("checkout_url", models.URLField(blank=True, max_length=1000)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="payments.subscriptionplan",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "payments",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["user", "status"], name="payment_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["provider", "external_id"],
                name="payment_external_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=Q(amount_tiyin__gt=0),
                name="payment_positive_amount",
            ),
        ),
    ]
