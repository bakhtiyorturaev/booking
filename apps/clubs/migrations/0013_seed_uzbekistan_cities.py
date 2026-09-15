from django.db import migrations


UZBEKISTAN_CITIES = (
    ("Andijon viloyati", "andijon-viloyati", 10),
    ("Buxoro viloyati", "buxoro-viloyati", 20),
    ("Jizzax viloyati", "jizzax-viloyati", 30),
    ("Qashqadaryo viloyati", "qashqadaryo-viloyati", 40),
    ("Navoiy viloyati", "navoiy-viloyati", 50),
    ("Namangan viloyati", "namangan-viloyati", 60),
    ("Samarqand viloyati", "samarqand-viloyati", 70),
    ("Sirdaryo viloyati", "sirdaryo-viloyati", 80),
    ("Surxondaryo viloyati", "surxondaryo-viloyati", 90),
    ("Toshkent viloyati", "toshkent-viloyati", 100),
    ("Fargʻona viloyati", "fargona-viloyati", 110),
    ("Xorazm viloyati", "xorazm-viloyati", 120),
    ("Qoraqalpogʻiston Respublikasi", "qoraqalpogiston-respublikasi", 130),
    ("Toshkent shahri", "toshkent-shahri", 140),
)


def seed_uzbekistan_cities(apps, schema_editor):
    City = apps.get_model("clubs", "City")

    for name, slug, sort_order in UZBEKISTAN_CITIES:
        city = City.objects.filter(slug=slug).first()
        if city is None:
            city = City.objects.filter(name__iexact=name).first()

        if city is None:
            City.objects.create(
                name=name,
                slug=slug,
                sort_order=sort_order,
                is_active=True,
            )
            continue

        city.name = name
        city.slug = slug
        city.sort_order = sort_order
        city.is_active = True
        city.save(
            update_fields=("name", "slug", "sort_order", "is_active", "updated_at")
        )


def unseed_uzbekistan_cities(apps, schema_editor):
    City = apps.get_model("clubs", "City")
    seeded_slugs = [slug for _, slug, _ in UZBEKISTAN_CITIES]
    City.objects.filter(
        slug__in=seeded_slugs,
        districts__isnull=True,
        branches__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0012_normalize_branch_locations"),
    ]

    operations = [
        migrations.RunPython(
            seed_uzbekistan_cities,
            reverse_code=unseed_uzbekistan_cities,
        ),
    ]
