from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.clubs.models import Branch, City, Club, District, OperatingHour, Zone
from apps.core.models import ServiceType


LANDMARK_OWNER = "uz_landmarks"
SAMPLE_OWNER = "namuna_demo"
SAMPLE_PREFIX = "Namuna: "

# Real public landmarks: (service code, name, description, city slug, district, address, lat, lng)
# Coordinates are approximate (building/complex centre).
LANDMARKS = (
    ("HISTORICAL_SITE", "Registon maydoni", "Ulug‘bek, Sherdor va Tillakori madrasalaridan iborat XV–XVII asrlar me’moriy ansambli.", "samarqand-viloyati", None, "Registon ko‘chasi, Samarqand", "39.654700", "66.975800"),
    ("MAUSOLEUM", "Go‘ri Amir maqbarasi", "Amir Temur va Temuriylar sulolasi vakillari dafn etilgan maqbara (XV asr).", "samarqand-viloyati", None, "Bo‘stonsaroy ko‘chasi, Samarqand", "39.648400", "66.969100"),
    ("MAUSOLEUM", "Shohi Zinda majmuasi", "XI–XIX asrlarga oid maqbaralar ko‘chasi, Samarqandning eng go‘zal obidalaridan biri.", "samarqand-viloyati", None, "Shohi Zinda ko‘chasi, Samarqand", "39.663100", "66.987500"),
    ("HISTORICAL_SITE", "Bibixonim masjidi", "Amir Temur buyrug‘i bilan qurilgan O‘rta Osiyodagi eng yirik masjidlardan biri.", "samarqand-viloyati", None, "Toshkent ko‘chasi, Samarqand", "39.660800", "66.979600"),
    ("MUSEUM", "Ulug‘bek rasadxonasi", "Mirzo Ulug‘bek tomonidan XV asrda qurilgan rasadxona qoldiqlari va muzey.", "samarqand-viloyati", None, "Toshkent ko‘chasi, Samarqand", "39.674800", "67.005500"),
    ("MUSEUM", "Afrosiyob muzeyi", "Qadimiy Samarqand — Afrosiyob shaharchasi topilmalari va VII asr devoriy suratlari.", "samarqand-viloyati", None, "Toshkent ko‘chasi, Samarqand", "39.669400", "66.990500"),
    ("HISTORICAL_SITE", "Ark qal’asi", "Buxoro amirlarining qadimiy qarorgohi va qal’asi.", "buxoro-viloyati", None, "Registon maydoni, Buxoro", "39.777800", "64.410800"),
    ("HISTORICAL_SITE", "Poi Kalon majmuasi", "Minorai Kalon, Kalon masjidi va Mir Arab madrasasidan iborat ansambl.", "buxoro-viloyati", None, "Xo‘ja Nurobod ko‘chasi, Buxoro", "39.775700", "64.414800"),
    ("MAUSOLEUM", "Ismoil Somoniy maqbarasi", "IX–X asrlarga oid, Markaziy Osiyodagi eng qadimiy pishiq g‘isht maqbaralardan biri.", "buxoro-viloyati", None, "Samoniylar bog‘i, Buxoro", "39.776700", "64.401300"),
    ("HISTORICAL_SITE", "Labi Hovuz ansambli", "Hovuz atrofidagi Ko‘kaldosh madrasasi va Nodir Devonbegi xonaqosi.", "buxoro-viloyati", None, "Labi Hovuz, Buxoro", "39.773900", "64.419900"),
    ("HISTORICAL_SITE", "Chor Minor", "To‘rt minorali o‘ziga xos madrasa darvozaxonasi (XIX asr).", "buxoro-viloyati", None, "Chor Minor ko‘chasi, Buxoro", "39.778300", "64.429000"),
    ("MAUSOLEUM", "Bahouddin Naqshband majmuasi", "Naqshbandiya tariqati asoschisi maqbarasi va ziyoratgoh.", "buxoro-viloyati", None, "Kogon tumani, Buxoro", "39.804700", "64.533600"),
    ("HISTORICAL_SITE", "Ichan qal’a", "Xivaning devor bilan o‘ralgan ichki shahri — ochiq osmon ostidagi muzey.", "xorazm-viloyati", None, "Ichan qal’a, Xiva", "41.378300", "60.363900"),
    ("HISTORICAL_SITE", "Kalta Minor", "Xivaning ramziga aylangan, firuza koshinli tugallanmagan minora.", "xorazm-viloyati", None, "Ichan qal’a, Xiva", "41.378600", "60.358900"),
    ("MAUSOLEUM", "Pahlavon Mahmud maqbarasi", "Xivaning homiysi sanalgan shoir va polvon maqbarasi.", "xorazm-viloyati", None, "Ichan qal’a, Xiva", "41.377200", "60.361500"),
    ("HISTORICAL_SITE", "Oqsaroy", "Amir Temurning Shahrisabzdagi saroyi qoldiqlari.", "qashqadaryo-viloyati", None, "Ipak yo‘li ko‘chasi, Shahrisabz", "39.061200", "66.829700"),
    ("MAUSOLEUM", "Dor ut-Tilovat majmuasi", "Temuriylar davri maqbaralari va Ko‘k gumbaz masjidi.", "qashqadaryo-viloyati", None, "Shahrisabz", "39.053800", "66.830000"),
    ("MUSEUM", "I. V. Savitskiy nomidagi san’at muzeyi", "Rus avangardi asarlarining dunyodagi eng yirik to‘plamlaridan biri.", "qoraqalpogiston-respublikasi", None, "Do‘stlik guzari, Nukus", "42.464600", "59.610500"),
    ("MAUSOLEUM", "Al-Hakim at-Termiziy maqbarasi", "IX asr mutafakkiri Al-Hakim at-Termiziy ziyoratgohi.", "surxondaryo-viloyati", None, "Termiz", "37.275700", "67.196400"),
    ("HISTORICAL_SITE", "Xudoyorxon o‘rdasi", "Qo‘qon xonining XIX asrdagi saroyi, hozir o‘lkashunoslik muzeyi.", "fargona-viloyati", None, "Istiqlol ko‘chasi, Qo‘qon", "40.539700", "70.942600"),
    ("MUSEUM", "Temuriylar tarixi davlat muzeyi", "Amir Temur va Temuriylar davriga bag‘ishlangan muzey.", "toshkent-shahri", "Yunusobod", "Amir Temur shoh ko‘chasi, 1, Toshkent", "41.311500", "69.279700"),
    ("MUSEUM", "O‘zbekiston tarixi davlat muzeyi", "Qadimdan hozirgi kungacha bo‘lgan O‘zbekiston tarixi ekspozitsiyasi.", "toshkent-shahri", "Yunusobod", "Sharof Rashidov ko‘chasi, 3, Toshkent", "41.316500", "69.272500"),
    ("MUSEUM", "Amaliy san’at muzeyi", "O‘zbek xalq hunarmandchiligi namunalari saqlanadigan muzey.", "toshkent-shahri", "Yakkasaroy", "Rakatboshi ko‘chasi, 15, Toshkent", "41.300500", "69.266200"),
    ("HISTORICAL_SITE", "Hazrati Imom majmuasi", "Toshkentning diniy markazi, Usmon Mushafi saqlanadigan majmua.", "toshkent-shahri", "Olmazor", "Qorasaroy ko‘chasi, Toshkent", "41.338300", "69.241000"),
    ("HISTORICAL_SITE", "Ko‘kaldosh madrasasi", "XVI asrga oid Toshkentning eng yirik madrasalaridan biri.", "toshkent-shahri", "Shayxontohur", "Chorsu, Toshkent", "41.326500", "69.236800"),
)

# District centres in Toshkent, used to spread the sample places across the city.
TASHKENT_POINTS = (
    ("Chilonzor", "41.275000", "69.204000"), ("Yunusobod", "41.366000", "69.288000"),
    ("Mirobod", "41.292000", "69.282000"), ("Mirzo Ulugʻbek", "41.338000", "69.335000"),
    ("Yakkasaroy", "41.283000", "69.258000"), ("Shayxontohur", "41.322000", "69.245000"),
    ("Yashnobod", "41.300000", "69.330000"), ("Olmazor", "41.350000", "69.222000"),
    ("Uchtepa", "41.300000", "69.170000"), ("Sergeli", "41.227000", "69.219000"),
    ("Bektemir", "41.209000", "69.334000"), ("Yangihayot", "41.205000", "69.250000"),
)

# Fictional sample places: (service code, name, description, zone name, resource type, capacity, price tiyin/hour, booking type)
SAMPLES = (
    ("COMPUTER", "Neon PC Club", "Sinov uchun namuna: gaming kompyuterlar zali.", "Gaming PC", "COMPUTER", 20, 1500000, "PER_SEAT"),
    ("PLAYSTATION", "PlayZone Lounge", "Sinov uchun namuna: PlayStation 5 xonalari.", "PlayStation 5", "PLAYSTATION", 4, 4000000, "PER_ZONE"),
    ("BARBER", "Ustoz Barbershop", "Sinov uchun namuna: erkaklar sartaroshxonasi.", "Sartarosh kreslosi", "GENERAL", 3, 6000000, "PER_SEAT"),
    ("BILLIARDS", "Shar Bilyard", "Sinov uchun namuna: rus va amerika bilyardi.", "Bilyard stoli", "BILLIARDS", 6, 5000000, "PER_ZONE"),
    ("GYM", "Kuch Fitness", "Sinov uchun namuna: trenajyor zali.", "Trenajyor zali", "GENERAL", 30, 2500000, "PER_SEAT"),
    ("FOOTBALL", "Yashil Maydon", "Sinov uchun namuna: sun’iy qoplamali mini-futbol maydoni.", "Mini-futbol maydoni", "GENERAL", 1, 25000000, "PER_ZONE"),
    ("POOL", "Moviy Basseyn", "Sinov uchun namuna: yopiq suzish havzasi.", "Suzish yo‘lakchasi", "GENERAL", 20, 4000000, "PER_SEAT"),
    ("CAR_WASH", "Toza Avto", "Sinov uchun namuna: avtoyuvish shoxobchasi.", "Yuvish boksi", "GENERAL", 3, 5000000, "PER_ZONE"),
    ("BEAUTY", "Gulnoz Go‘zallik saloni", "Sinov uchun namuna: ayollar go‘zallik saloni.", "Usta joyi", "GENERAL", 4, 8000000, "PER_SEAT"),
    ("COWORKING", "Ish Makon", "Sinov uchun namuna: ochiq ish joylari va majlis xonasi.", "Ish stoli", "GENERAL", 40, 2000000, "PER_SEAT"),
    ("PHOTO_STUDIO", "Kadr Fotostudiya", "Sinov uchun namuna: yorug‘lik uskunali fotostudiya.", "Studiya zali", "GENERAL", 2, 15000000, "PER_ZONE"),
    ("EVENT_HALL", "Bayram Tadbirlar zali", "Sinov uchun namuna: 150 kishilik tadbirlar zali.", "Asosiy zal", "GENERAL", 1, 100000000, "PER_ZONE"),
    ("HOTEL", "Ipak Yo‘li Mehmonxonasi", "Sinov uchun namuna: shahar markazidagi mehmonxona.", "Standart xona", "GENERAL", 10, 6000000, "PER_ZONE"),
    ("HOSTEL", "Karvon Hostel", "Sinov uchun namuna: sayohatchilar uchun hostel.", "Yotoq joyi", "GENERAL", 24, 1500000, "PER_SEAT"),
    ("GUEST_HOUSE", "Ko‘hna Hovli mehmon uyi", "Sinov uchun namuna: an’anaviy o‘zbek hovlisidagi mehmon uyi.", "Mehmon xonasi", "GENERAL", 5, 4000000, "PER_ZONE"),
    ("APARTMENT", "Shahar Kvartirasi", "Sinov uchun namuna: kunlik ijaraga beriladigan kvartira.", "2 xonali kvartira", "GENERAL", 1, 5000000, "PER_ZONE"),
    ("NATIONAL_CUISINE", "Dasturxon Milliy Taomlar", "Sinov uchun namuna: milliy taomlar restorani.", "Stol", "GENERAL", 12, 1000000, "PER_ZONE"),
    ("PLOV_CENTER", "Sharq Osh Markazi", "Sinov uchun namuna: to‘y oshi va choyxona.", "Stol", "GENERAL", 15, 1000000, "PER_ZONE"),
    ("TERRACE_CAFE", "Bog‘ Terrasa Kafe", "Sinov uchun namuna: ochiq terrasali kafe.", "Terrasa stoli", "GENERAL", 10, 1000000, "PER_ZONE"),
    ("CITY_GUIDED_TOUR", "Toshkent bo‘ylab gid bilan sayohat", "Sinov uchun namuna: shaharning asosiy joylari bo‘ylab gidli tur.", "Guruh turi", "GENERAL", 15, 5000000, "PER_SEAT"),
    ("WALKING_TOUR", "Eski shahar piyoda turi", "Sinov uchun namuna: Chorsu va eski mahallalar bo‘ylab piyoda tur.", "Piyoda guruh", "GENERAL", 12, 3000000, "PER_SEAT"),
    ("AUDIO_GUIDE", "Toshkent audiogidi", "Sinov uchun namuna: muzeylar uchun audiogid ijarasi.", "Audiogid qurilmasi", "GENERAL", 30, 1000000, "PER_SEAT"),
    ("AIRPORT_TRANSFER", "Aeroport transferi xizmati", "Sinov uchun namuna: aeroportdan mehmonxonagacha transfer.", "Yengil avtomobil", "GENERAL", 5, 10000000, "PER_ZONE"),
    ("CAR_WITH_DRIVER", "Haydovchili avtomobil ijarasi", "Sinov uchun namuna: soatbay haydovchili avtomobil.", "Avtomobil", "GENERAL", 4, 12000000, "PER_ZONE"),
    ("INTERCITY_TRAIN", "Shaharlararo poyezd xizmati", "Sinov uchun namuna: shaharlararo poyezd chiptalari.", "Vagon o‘rni", "GENERAL", 40, 8000000, "PER_SEAT"),
    ("INTERCITY_BUS", "Shaharlararo avtobus xizmati", "Sinov uchun namuna: shaharlararo avtobus qatnovi.", "Avtobus o‘rni", "GENERAL", 40, 5000000, "PER_SEAT"),
)


class Command(BaseCommand):
    help = (
        "Katalogga O‘zbekistonning mashhur obidalarini va 'Namuna:' belgili sinov joylarini qo‘shadi. "
        "--remove-samples faqat sinov joylarini o‘chiradi."
    )

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=("landmarks", "samples"), help="Faqat bitta turini qo‘shish.")
        parser.add_argument("--remove-samples", action="store_true", help="'Namuna:' sinov joylarini o‘chirish.")

    def system_owner(self, username):
        owner, created = User.objects.get_or_create(username=username, defaults={"role": User.Role.CLIENT})
        if created:
            owner.set_unusable_password()
            owner.save(update_fields=["password"])
        return owner

    def service(self, code):
        service = ServiceType.objects.filter(code=code).first()
        if service is None:
            raise CommandError(f"Xizmat turi topilmadi: {code}. Avval `migrate` ni ishga tushiring.")
        return service

    def set_hours(self, branch, opens, closes):
        for weekday in range(7):
            OperatingHour.objects.update_or_create(
                branch=branch, weekday=weekday,
                defaults={"opens_at": opens, "closes_at": closes, "is_closed": False},
            )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["remove_samples"]:
            clubs = Club.objects.filter(owner__username=SAMPLE_OWNER, name__startswith=SAMPLE_PREFIX)
            count = clubs.count()
            Zone.objects.filter(branch__club__in=clubs).delete()
            Branch.objects.filter(club__in=clubs).delete()
            clubs.delete()
            self.stdout.write(self.style.SUCCESS(f"{count} ta namuna joy o‘chirildi."))
            return

        cities = {city.slug: city for city in City.objects.all()}
        districts = {(d.city_id, d.name): d for d in District.objects.all()}
        if options["only"] != "samples":
            self.seed_landmarks(cities, districts)
        if options["only"] != "landmarks":
            self.seed_samples(cities, districts)

    def seed_landmarks(self, cities, districts):
        owner = self.system_owner(LANDMARK_OWNER)
        for code, name, description, city_slug, district_name, address, lat, lng in LANDMARKS:
            city = cities.get(city_slug)
            if city is None:
                raise CommandError(f"Shahar topilmadi: {city_slug}")
            club, _ = Club.objects.update_or_create(owner=owner, name=name, defaults={
                "service_type": self.service(code), "description": description, "address": address,
                "latitude": Decimal(lat), "longitude": Decimal(lng),
                "status": Club.Status.ACTIVE, "is_verified": True,
            })
            branch, _ = Branch.objects.update_or_create(club=club, name=name, defaults={
                "description": description, "address": address, "city": city,
                "district": districts.get((city.id, district_name)) if district_name else None,
                "latitude": Decimal(lat), "longitude": Decimal(lng), "status": Branch.Status.ACTIVE,
            })
            self.set_hours(branch, time(9), time(18))
        self.stdout.write(self.style.SUCCESS(f"{len(LANDMARKS)} ta obida tayyor."))

    def seed_samples(self, cities, districts):
        owner = self.system_owner(SAMPLE_OWNER)
        city = cities.get("toshkent-shahri")
        if city is None:
            raise CommandError("Toshkent shahri topilmadi.")
        for index, (code, name, description, zone_name, resource, capacity, price, booking_type) in enumerate(SAMPLES):
            district_name, lat, lng = TASHKENT_POINTS[index % len(TASHKENT_POINTS)]
            # Spread places that share a district centre a little apart.
            offset = Decimal("0.004") * (index // len(TASHKENT_POINTS))
            service = self.service(code)
            full_name = SAMPLE_PREFIX + name
            club, _ = Club.objects.update_or_create(owner=owner, name=full_name, defaults={
                "service_type": service, "description": description,
                "status": Club.Status.ACTIVE, "is_verified": False,
            })
            branch, _ = Branch.objects.update_or_create(club=club, name=full_name, defaults={
                "description": description, "address": f"{district_name} tumani (namuna manzil)", "city": city,
                "district": districts.get((city.id, district_name)),
                "latitude": Decimal(lat) + offset, "longitude": Decimal(lng) + offset,
                "status": Branch.Status.ACTIVE,
            })
            Zone.objects.update_or_create(branch=branch, name=zone_name, defaults={
                "service_type": service, "status": Zone.Status.ACTIVE, "resource_type": resource,
                "capacity": capacity, "booking_type": booking_type, "unit_count": 1,
                "price_per_hour_tiyin": price,
            })
            self.set_hours(branch, time(9), time(22))
        self.stdout.write(self.style.SUCCESS(f"{len(SAMPLES)} ta namuna joy tayyor (Toshkent)."))
