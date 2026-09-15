import uuid

import apps.payments.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0003_alter_user_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSubscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=10,
                        choices=[
                            ("ACTIVE", "Active"),
                            ("EXPIRED", "Expired"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="ACTIVE",
                    ),
                ),
                ("starts_at", models.DateTimeField(default=timezone.now)),
                (
                    "expires_at",
                    models.DateTimeField(
                        default=apps.payments.models.subscription_expires_at
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_subscriptions",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="usersubscription",
            constraint=models.CheckConstraint(
                condition=Q(expires_at__gt=F("starts_at")),
                name="subscription_expires_after_start",
            ),
        ),
    ]
