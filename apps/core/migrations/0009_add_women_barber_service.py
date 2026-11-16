from django.db import migrations


def add_women_barber(apps, schema_editor):
    ServiceType = apps.get_model("core", "ServiceType")
    parent = ServiceType.objects.filter(code="BARBERSHOP").first()
    men = ServiceType.objects.filter(code="BARBER").first()
    if men and men.name == "Sartarosh":
        # Faqat standart nom bo'lsa — kabinetda qo'lda o'zgartirilgan nomga tegmaymiz.
        men.name, men.name_ru, men.name_en = "Erkak sartarosh", "Мужской парикмахер", "Men's barber"
        men.save(update_fields=("name", "name_ru", "name_en"))
    ServiceType.objects.get_or_create(
        code="WOMEN_BARBER",
        defaults={
            "name": "Ayol sartarosh",
            "name_ru": "Женский парикмахер",
            "name_en": "Women's hairdresser",
            "parent": parent,
            "sort_order": (men.sort_order + 1) if men else 0,
        },
    )


def remove_women_barber(apps, schema_editor):
    ServiceType = apps.get_model("core", "ServiceType")
    ServiceType.objects.filter(code="WOMEN_BARBER").delete()
    ServiceType.objects.filter(code="BARBER", name="Erkak sartarosh").update(
        name="Sartarosh", name_ru="Парикмахер", name_en="Barber",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_seed_toshkent_districts"),
    ]

    operations = [
        migrations.RunPython(add_women_barber, remove_women_barber),
    ]
