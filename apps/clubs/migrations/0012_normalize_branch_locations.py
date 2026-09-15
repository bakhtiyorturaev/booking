import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify


def _unique_slug(model, base, **scope):
    base = slugify(base) or "location"
    candidate = base
    number = 2
    while model.objects.filter(slug=candidate, **scope).exists():
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def normalize_branch_locations(apps, schema_editor):
    Branch = apps.get_model("clubs", "Branch")
    City = apps.get_model("clubs", "City")
    District = apps.get_model("clubs", "District")
    city_cache = {}
    district_cache = {}

    for branch in Branch.objects.all().iterator():
        city_name = (branch.city_name or "").strip() or "Noma’lum"
        city_key = city_name.casefold()
        city = city_cache.get(city_key)
        if city is None:
            city = City.objects.filter(name__iexact=city_name).first()
            if city is None:
                city = City.objects.create(
                    name=city_name,
                    slug=_unique_slug(City, city_name),
                )
            city_cache[city_key] = city

        district = None
        district_name = (branch.district_name or "").strip()
        if district_name:
            district_key = (city.pk, district_name.casefold())
            district = district_cache.get(district_key)
            if district is None:
                district = District.objects.filter(
                    city_id=city.pk,
                    name__iexact=district_name,
                ).first()
                if district is None:
                    district = District.objects.create(
                        city_id=city.pk,
                        name=district_name,
                        slug=_unique_slug(
                            District,
                            district_name,
                            city_id=city.pk,
                        ),
                    )
                district_cache[district_key] = district

        Branch.objects.filter(pk=branch.pk).update(
            city_id=city.pk,
            district_id=district.pk if district else None,
        )


def denormalize_branch_locations(apps, schema_editor):
    Branch = apps.get_model("clubs", "Branch")
    for branch in Branch.objects.select_related("city", "district").iterator():
        Branch.objects.filter(pk=branch.pk).update(
            city_name=branch.city.name,
            district_name=branch.district.name if branch.district_id else "",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0011_alter_club_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(help_text="Shahar nomi.", max_length=120)),
                (
                    "slug",
                    models.SlugField(
                        help_text="Shahar kodi.",
                        max_length=140,
                        unique=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Tanlash uchun faolmi.",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Ko‘rinish tartibi.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Shahar",
                "verbose_name_plural": "Shaharlar",
                "db_table": "cities",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="District",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(help_text="Tuman nomi.", max_length=120)),
                (
                    "slug",
                    models.SlugField(help_text="Tuman kodi.", max_length=140),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Tanlash uchun faolmi.",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Ko‘rinish tartibi.",
                    ),
                ),
                (
                    "city",
                    models.ForeignKey(
                        help_text="Tuman tegishli shahar.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="districts",
                        to="clubs.city",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tuman",
                "verbose_name_plural": "Tumanlar",
                "db_table": "districts",
                "ordering": (
                    "city__sort_order",
                    "city__name",
                    "sort_order",
                    "name",
                ),
                "indexes": [
                    models.Index(
                        fields=["city", "is_active", "sort_order"],
                        name="district_city_active_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("city", "slug"),
                        name="unique_district_slug_per_city",
                    ),
                    models.UniqueConstraint(
                        fields=("city", "name"),
                        name="unique_district_name_per_city",
                    ),
                ],
            },
        ),
        migrations.RemoveIndex(
            model_name="branch",
            name="branch_status_city_idx",
        ),
        migrations.RenameField(
            model_name="branch",
            old_name="city",
            new_name="city_name",
        ),
        migrations.RenameField(
            model_name="branch",
            old_name="district",
            new_name="district_name",
        ),
        migrations.AddField(
            model_name="branch",
            name="city",
            field=models.ForeignKey(
                help_text="Filial joylashgan shahar.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="branches",
                to="clubs.city",
            ),
        ),
        migrations.AddField(
            model_name="branch",
            name="district",
            field=models.ForeignKey(
                blank=True,
                help_text="Filial joylashgan tuman.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="branches",
                to="clubs.district",
            ),
        ),
        migrations.RunPython(
            normalize_branch_locations,
            reverse_code=denormalize_branch_locations,
        ),
        migrations.AlterField(
            model_name="branch",
            name="city",
            field=models.ForeignKey(
                help_text="Filial joylashgan shahar.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="branches",
                to="clubs.city",
            ),
        ),
        migrations.RemoveField(
            model_name="branch",
            name="city_name",
        ),
        migrations.RemoveField(
            model_name="branch",
            name="district_name",
        ),
        migrations.AlterField(
            model_name="branch",
            name="address",
            field=models.CharField(
                help_text="Ko‘cha, uy va bino manzili.",
                max_length=300,
            ),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(
                fields=["status", "city"],
                name="branch_status_city_idx",
            ),
        ),
    ]
