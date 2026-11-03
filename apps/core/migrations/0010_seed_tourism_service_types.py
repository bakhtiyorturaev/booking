from django.db import migrations
from django.db.models import ProtectedError


# (code, uz, ru, en, children[(code, uz, ru, en)])
TOURISM_SERVICES = (
    ("ACCOMMODATION", "Turar joy", "Жильё", "Accommodation", (
        ("HOTEL", "Mehmonxona", "Гостиница", "Hotel"),
        ("HOSTEL", "Hostel", "Хостел", "Hostel"),
        ("GUEST_HOUSE", "Mehmon uyi", "Гостевой дом", "Guest house"),
        ("APARTMENT", "Kvartira", "Квартира", "Apartment"),
    )),
    ("RESTAURANT", "Restoran va choyxonalar", "Рестораны и чайханы", "Restaurants and teahouses", (
        ("NATIONAL_CUISINE", "Milliy taomlar restorani", "Ресторан национальной кухни", "National cuisine restaurant"),
        ("PLOV_CENTER", "Osh markazi", "Центр плова", "Plov centre"),
        ("TERRACE_CAFE", "Terrasali kafe", "Кафе с террасой", "Terrace cafe"),
    )),
    ("ATTRACTION", "Diqqatga sazovor joylar", "Достопримечательности", "Attractions", (
        ("MUSEUM", "Muzeylar", "Музеи", "Museums"),
        ("HISTORICAL_SITE", "Tarixiy obidalar", "Исторические памятники", "Historical monuments"),
        ("MAUSOLEUM", "Maqbaralar", "Мавзолеи", "Mausoleums"),
    )),
    ("EXCURSION", "Ekskursiyalar", "Экскурсии", "Excursions", (
        ("CITY_GUIDED_TOUR", "Gid bilan shahar sayohati", "Экскурсия по городу с гидом", "Guided city tour"),
        ("WALKING_TOUR", "Piyoda turlar", "Пешеходные туры", "Walking tours"),
        ("AUDIO_GUIDE", "Audiogid", "Аудиогид", "Audio guide"),
    )),
    ("TRANSPORT", "Transport", "Транспорт", "Transport", (
        ("AIRPORT_TRANSFER", "Aeroport transferi", "Трансфер из аэропорта", "Airport transfer"),
        ("CAR_WITH_DRIVER", "Haydovchili avtomobil", "Автомобиль с водителем", "Car with driver"),
        ("INTERCITY_TRAIN", "Shaharlararo poyezd", "Междугородний поезд", "Intercity train"),
        ("INTERCITY_BUS", "Shaharlararo avtobus", "Междугородний автобус", "Intercity bus"),
    )),
)
FIRST_SORT_ORDER = 11
OTHER_SORT_ORDER = 99


def seed_tourism_services(apps, schema_editor):
    ServiceType = apps.get_model("core", "ServiceType")
    for index, (code, name, name_ru, name_en, children) in enumerate(TOURISM_SERVICES):
        parent, _ = ServiceType.objects.get_or_create(code=code, defaults={
            "name": name, "name_ru": name_ru, "name_en": name_en,
            "sort_order": FIRST_SORT_ORDER + index, "is_active": True,
        })
        for child_index, (child_code, child_name, child_ru, child_en) in enumerate(children):
            ServiceType.objects.get_or_create(code=child_code, defaults={
                "name": child_name, "name_ru": child_ru, "name_en": child_en,
                "parent": parent, "sort_order": child_index, "is_active": True,
            })
    # Keep "Boshqa xizmat" at the end of the catalog.
    ServiceType.objects.filter(code="OTHER").update(sort_order=OTHER_SORT_ORDER)


def remove_tourism_services(apps, schema_editor):
    ServiceType = apps.get_model("core", "ServiceType")
    for code, _name, _ru, _en, children in TOURISM_SERVICES:
        for child_code, *_ in children:
            try:
                ServiceType.objects.filter(code=child_code).delete()
            except ProtectedError:
                pass  # already used by a venue; leave it in place
        try:
            ServiceType.objects.filter(code=code).delete()
        except ProtectedError:
            pass
    ServiceType.objects.filter(code="OTHER").update(sort_order=FIRST_SORT_ORDER)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_add_women_barber_service"),
    ]

    operations = [
        migrations.RunPython(seed_tourism_services, remove_tourism_services),
    ]
