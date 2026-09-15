from datetime import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.clubs.models import Branch, City, Club, District, OperatingHour, Zone


DEMO_CLUBS = (
    {
        "name": "Pixel Arena",
        "slug": "pixel-arena",
        "description": "Kuchli gaming kompyuterlar va turnirlar uchun zamonaviy arena.",
        "district": "Mirzo Ulugʻbek",
        "address": "Buyuk Ipak Yo‘li ko‘chasi, 105",
        "latitude": "41.326500",
        "longitude": "69.326200",
        "is_24_hours": True,
        "verified": True,
        "zones": (("Standard PC", "COMPUTER", 24, 1800000),),
    },
    {
        "name": "Cyber Point",
        "slug": "cyber-point",
        "description": "Kompyuter va PlayStation zonalari bir joyda.",
        "district": "Chilonzor",
        "address": "Bunyodkor shoh ko‘chasi, 52",
        "latitude": "41.285200",
        "longitude": "69.203100",
        "is_24_hours": True,
        "verified": True,
        "zones": (
            ("Pro PC", "COMPUTER", 18, 2200000),
            ("PlayStation 5", "PLAYSTATION", 4, 12000000, "PER_ZONE", 2),
        ),
    },
    {
        "name": "Respawn Gaming",
        "slug": "respawn-gaming",
        "description": "Do‘stlar bilan o‘ynash uchun qulay va tezkor gaming makon.",
        "district": "Yunusobod",
        "address": "Amir Temur shoh ko‘chasi, 108",
        "latitude": "41.366700",
        "longitude": "69.288600",
        "is_24_hours": False,
        "verified": False,
        "zones": (("Gaming PC", "COMPUTER", 20, 1600000),),
    },
    {
        "name": "Nova Esports",
        "slug": "nova-esports",
        "description": "Esports mashg‘ulotlari va premium gaming uchun maxsus klub.",
        "district": "Mirobod",
        "address": "Afrosiyob ko‘chasi, 14",
        "latitude": "41.292600",
        "longitude": "69.270800",
        "is_24_hours": False,
        "verified": True,
        "zones": (
            ("Premium PC", "COMPUTER", 16, 2800000),
            ("PlayStation Lounge", "PLAYSTATION", 6, 15000000, "PER_ZONE", 1),
        ),
    },
)

EXTRA_BRANCHES = (
    {
        "club_slug": "pixel-arena",
        "district": "Chilonzor",
        "address": "Muqimiy ko‘chasi, 21",
        "latitude": "41.292900",
        "longitude": "69.221800",
        "is_24_hours": True,
        "zones": (
            ("Standard PC", "COMPUTER", 20, 1800000),
            ("PlayStation 5", "PLAYSTATION", 4, 12000000, "PER_ZONE", 1),
        ),
    },
    {
        "club_slug": "cyber-point",
        "district": "Yunusobod",
        "address": "Yunusota ko‘chasi, 12",
        "latitude": "41.363200",
        "longitude": "69.285100",
        "is_24_hours": False,
        "zones": (("Pro PC", "COMPUTER", 22, 2200000),),
    },
)


class Command(BaseCommand):
    help = "Frontend katalogi uchun qayta ishlatiladigan demo klublarni yaratadi."

    @transaction.atomic
    def handle(self, *args, **options):
        city = City.objects.filter(slug="toshkent-shahri", is_active=True).first()
        owner = Club.objects.order_by("created_at").values_list("owner", flat=True).first()
        owner = User.objects.filter(id=owner).first() or User.objects.filter(
            status=User.Status.ACTIVE,
        ).first()
        if city is None or owner is None:
            raise CommandError("Demo klublar uchun faol Toshkent shahri va owner kerak.")

        districts = {
            district.name: district
            for district in District.objects.filter(city=city, is_active=True)
        }
        created_count = 0

        def upsert_branch(club, item):
            district = districts.get(item["district"])
            branch, _ = Branch.objects.update_or_create(
                club=club,
                name=f"{club.name} — {item['district']}",
                defaults={
                    "description": club.description,
                    "address": item["address"],
                    "city": city,
                    "district": district,
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "status": Branch.Status.ACTIVE,
                    "is_24_hours": item["is_24_hours"],
                },
            )
            for order, zone_data in enumerate(item["zones"]):
                name, resource_type, capacity, price, *config = zone_data
                Zone.objects.update_or_create(
                    branch=branch,
                    name=name,
                    defaults={
                        "status": Zone.Status.ACTIVE,
                        "resource_type": resource_type,
                        "capacity": capacity,
                        "booking_type": config[0] if config else Zone.BookingType.PER_SEAT,
                        "unit_count": config[1] if len(config) > 1 else 1,
                        "price_per_hour_tiyin": price,
                        "sort_order": order,
                    },
                )
            if not branch.is_24_hours:
                for weekday in range(7):
                    OperatingHour.objects.update_or_create(
                        branch=branch,
                        weekday=weekday,
                        defaults={
                            "opens_at": time(10),
                            "closes_at": time(23),
                            "is_closed": False,
                        },
                    )
            return branch

        for item in DEMO_CLUBS:
            club, created = Club.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "owner": owner,
                    "name": item["name"],
                    "description": item["description"],
                    "status": Club.Status.ACTIVE,
                    "is_verified": item["verified"],
                },
            )
            created_count += int(created)
            upsert_branch(club, item)

        for item in EXTRA_BRANCHES:
            upsert_branch(Club.objects.get(slug=item["club_slug"]), item)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo klublar tayyor: {created_count} ta yaratildi, "
                f"{len(DEMO_CLUBS) - created_count} ta yangilandi."
            )
        )
