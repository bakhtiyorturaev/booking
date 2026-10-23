from django.db import migrations, transaction
from django.db.models import ProtectedError


TOSHKENT_CITY_SLUG = "toshkent-shahri"

TOSHKENT_DISTRICTS = (
    ("Bektemir", "bektemir", 10),
    ("Chilonzor", "chilonzor", 20),
    ("Mirobod", "mirobod", 30),
    ("Mirzo Ulugʻbek", "mirzo-ulugbek", 40),
    ("Olmazor", "olmazor", 50),
    ("Sergeli", "sergeli", 60),
    ("Shayxontohur", "shayxontohur", 70),
    ("Uchtepa", "uchtepa", 80),
    ("Yakkasaroy", "yakkasaroy", 90),
    ("Yashnobod", "yashnobod", 100),
    ("Yunusobod", "yunusobod", 110),
    ("Yangihayot", "yangihayot", 120),
)


def seed_toshkent_districts(apps, schema_editor):
    City = apps.get_model("core", "City")
    District = apps.get_model("core", "District")

    city = City.objects.filter(slug=TOSHKENT_CITY_SLUG).first()
    if city is None:
        city = City.objects.filter(name__iexact="Toshkent shahri").first()
    if city is None:
        return

    for name, slug, sort_order in TOSHKENT_DISTRICTS:
        district = District.objects.filter(city=city, slug=slug).first()
        if district is None:
            district = District.objects.filter(city=city, name__iexact=name).first()

        if district is None:
            District.objects.create(
                city=city,
                name=name,
                slug=slug,
                sort_order=sort_order,
                is_active=True,
            )
            continue

        district.name = name
        district.slug = slug
        district.sort_order = sort_order
        district.is_active = True
        district.save(
            update_fields=("name", "slug", "sort_order", "is_active", "updated_at")
        )


def unseed_toshkent_districts(apps, schema_editor):
    City = apps.get_model("core", "City")
    District = apps.get_model("core", "District")

    city = City.objects.filter(slug=TOSHKENT_CITY_SLUG).first()
    if city is None:
        return

    seeded_slugs = [slug for _, slug, _ in TOSHKENT_DISTRICTS]
    districts = District.objects.filter(city=city, slug__in=seeded_slugs)
    for district in districts:
        # Filial, klub, sartarosh va tarif qoidalari District'ni PROTECT bilan
        # ushlab turadi — ishlatilgan tumanni o'chirmasdan tashlab ketamiz.
        try:
            with transaction.atomic():
                district.delete()
        except ProtectedError:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_add_service_type_hierarchy"),
        ("clubs", "0026_alter_branch_city_alter_club_billing_city_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_toshkent_districts,
            reverse_code=unseed_toshkent_districts,
        ),
    ]
