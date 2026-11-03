import json
import math
import re
from datetime import time
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.clubs.models import Branch, City, Club, OperatingHour
from apps.core.models import ServiceType


OSM_OWNER = "osm_import"
ATTRIBUTION = "Manba: © OpenStreetMap ishtirokchilari (ODbL), openstreetmap.org"

# Approximate region centres; a place is assigned to the nearest one (Toshkent shahri inside a 16 km radius).
REGION_CENTRES = {
    "toshkent-shahri": (41.3111, 69.2797), "toshkent-viloyati": (41.0, 69.6),
    "samarqand-viloyati": (39.65, 66.96), "buxoro-viloyati": (39.77, 64.42),
    "xorazm-viloyati": (41.55, 60.63), "qoraqalpogiston-respublikasi": (42.46, 59.61),
    "navoiy-viloyati": (40.10, 65.37), "qashqadaryo-viloyati": (38.86, 65.79),
    "surxondaryo-viloyati": (37.94, 67.57), "jizzax-viloyati": (40.12, 67.84),
    "sirdaryo-viloyati": (40.49, 68.78), "fargona-viloyati": (40.39, 71.78),
    "andijon-viloyati": (40.78, 72.34), "namangan-viloyati": (41.00, 71.67),
}
SERVICE_LABELS = {
    "HOTEL": "Mehmonxona", "HOSTEL": "Hostel", "GUEST_HOUSE": "Mehmon uyi", "APARTMENT": "Kvartira",
    "RESTAURANT": "Restoran", "NATIONAL_CUISINE": "Milliy taomlar restorani", "PLOV_CENTER": "Osh markazi",
    "TERRACE_CAFE": "Terrasali kafe", "GYM": "Sport zali", "POOL": "Basseyn", "CAR_WASH": "Avtoyuvish",
    "BARBERSHOP": "Sartaroshxona", "BEAUTY": "Go‘zallik saloni", "COWORKING": "Kovorking",
    "FOOTBALL": "Futbol maydoni", "BILLIARDS": "Bilyard", "COMPUTER": "Kompyuter klubi",
    "PHOTO_STUDIO": "Fotostudiya", "EVENT_HALL": "Tadbirlar zali", "INTERCITY_TRAIN": "Temir yo‘l vokzali",
    "INTERCITY_BUS": "Avtovokzal", "EXCURSION": "Sayohat agentligi",
}
PLOV_WORDS = re.compile(r"\b(osh|plov|palov|плов|ош)\b", re.I)
BARBER_WORDS = re.compile(r"barber|барбер|sartarosh|сартарош|men'?s|мужск", re.I)
# Names that only repeat the place type carry no information ("Автомойка", "Sartaroshxona").
GENERIC_NAMES = {
    "автомойка", "мойка", "carwash", "avtomoyka", "сартарошхона", "sartaroshxona", "парикмахерская", "barbershop",
    "салонкрасоты", "кафе", "cafe", "kafe", "ресторан", "restaurant", "restoran", "чайхана", "choyxona", "гостиница",
    "hotel", "mehmonxona", "хостел", "hostel", "фитнес", "fitness", "спортзал", "автовокзал", "avtovokzal", "вокзал",
    "компьютерныйклуб", "интернеткафе", "фотостудия", "бильярд", "basseyn", "бассейн",
}
DAYS = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}


def service_code(tags):
    name = tags.get("name", "")
    tourism, amenity, leisure, shop = tags.get("tourism"), tags.get("amenity"), tags.get("leisure"), tags.get("shop")
    if tourism in ("hotel", "hostel", "guest_house", "apartment"):
        return {"hotel": "HOTEL", "hostel": "HOSTEL", "guest_house": "GUEST_HOUSE", "apartment": "APARTMENT"}[tourism]
    if amenity == "restaurant":
        if PLOV_WORDS.search(name) or "plov" in tags.get("cuisine", ""):
            return "PLOV_CENTER"
        if re.search(r"uzbek|central_asian|regional", tags.get("cuisine", "")):
            return "NATIONAL_CUISINE"
        return "RESTAURANT"
    if amenity == "cafe":
        return "TERRACE_CAFE" if tags.get("outdoor_seating") == "yes" else "RESTAURANT"
    if leisure == "fitness_centre":
        return "GYM"
    if (leisure == "sports_centre" and tags.get("sport") == "swimming") or leisure == "swimming_pool":
        return "POOL"
    if amenity == "car_wash":
        return "CAR_WASH"
    if shop == "hairdresser":
        return "BARBERSHOP" if BARBER_WORDS.search(name) or tags.get("male") == "yes" else "BEAUTY"
    if shop == "beauty":
        return "BEAUTY"
    if amenity == "coworking_space" or tags.get("office") == "coworking":
        return "COWORKING"
    if leisure == "pitch" and tags.get("sport") == "soccer":
        return "FOOTBALL"
    if tags.get("sport") == "billiards":
        return "BILLIARDS"
    if amenity == "internet_cafe" or leisure == "amusement_arcade":
        return "COMPUTER"
    if shop == "photo_studio" or tags.get("craft") == "photographer":
        return "PHOTO_STUDIO"
    if amenity in ("events_venue", "conference_centre"):
        return "EVENT_HALL"
    if tags.get("railway") == "station":
        return "INTERCITY_TRAIN"
    if amenity == "bus_station":
        return "INTERCITY_BUS"
    if shop == "travel_agency" or tags.get("office") == "travel_agent" or tags.get("information") == "office":
        return "EXCURSION"
    return None


def region_slug(lat, lng):
    def dist(centre):
        return math.hypot(lat - centre[0], (lng - centre[1]) * math.cos(math.radians(lat)))
    if dist(REGION_CENTRES["toshkent-shahri"]) < 0.145:  # ~16 km
        return "toshkent-shahri"
    return min((slug for slug in REGION_CENTRES if slug != "toshkent-shahri"), key=lambda s: dist(REGION_CENTRES[s]))


def parse_hours(value):
    """Return ('24/7', None) or ('weekly', {weekday: (opens, closes)}) for simple OSM opening_hours; else None."""
    value = (value or "").strip()
    if value == "24/7":
        return "24/7", None
    result = {}
    for part in value.split(";"):
        m = re.fullmatch(r"\s*(Mo|Tu|We|Th|Fr|Sa|Su)(?:-(Mo|Tu|We|Th|Fr|Sa|Su))?\s+(\d{2}):(\d{2})-(\d{2}):(\d{2})\s*", part)
        if not m:
            return None
        start, end = DAYS[m[1]], DAYS[m[2] or m[1]]
        opens, closes = int(m[3]), int(m[5])
        if opens > 23 or closes > 24:
            return None
        days = range(start, end + 1) if start <= end else list(range(start, 7)) + list(range(0, end + 1))
        for day in days:
            result[day] = (time(opens, int(m[4])), time(min(closes, 23), 59 if closes == 24 else int(m[6])))
    return ("weekly", result) if result else None


class Command(BaseCommand):
    help = "OpenStreetMap JSON (Overpass `out tags center`) dan joylarni 'ma’lumot uchun' (bron qilinmaydigan) qilib import qiladi."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", help="Overpass JSON fayli yoki shunday fayllar papkasi.")
        parser.add_argument("--per-service", type=int, default=40, help="Har bir xizmat turi uchun eng ko‘pi bilan nechta joy.")
        parser.add_argument("--remove", action="store_true", help="Avval import qilingan OSM joylarini o‘chirish.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["remove"]:
            clubs = Club.objects.filter(owner__username=OSM_OWNER)
            count = clubs.count()
            Branch.objects.filter(club__in=clubs).delete()
            clubs.delete()
            self.stdout.write(self.style.SUCCESS(f"{count} ta OSM joyi o‘chirildi."))
            return
        if not options["path"]:
            raise CommandError("JSON fayl yo‘lini kiriting yoki --remove ishlating.")

        source = Path(options["path"])
        files = sorted(source.glob("*.json")) if source.is_dir() else [source]
        elements = [el for file in files for el in json.loads(file.read_text(encoding="utf-8"))]
        cities = {city.slug: city for city in City.objects.all()}
        services = {s.code: s for s in ServiceType.objects.all()}
        owner, created = User.objects.get_or_create(username=OSM_OWNER, defaults={"role": User.Role.CLIENT})
        if created:
            owner.set_unusable_password()
            owner.save(update_fields=["password"])

        # Prefer places with more useful details, then keep the per-service cap.
        def score(el):
            t = el["tags"]
            return sum(bool(t.get(k)) for k in ("addr:street", "phone", "contact:phone", "website", "opening_hours", "stars"))

        buckets = {}
        kept = {}  # normalized name -> [(lat, lng)] to drop node/way duplicates of the same place
        for el in sorted(elements, key=score, reverse=True):
            tags = el.get("tags", {})
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lng = el.get("lon") or (el.get("center") or {}).get("lon")
            code = service_code(tags)
            if not code or lat is None or code not in services:
                continue
            name = (tags.get("name:uz") or tags.get("name") or "").strip()
            # Skip names that are not real place names ("9 xona.", "12", "A").
            if len(re.sub(r"[\W\d_]", "", name)) < 3 or re.match(r"^\d", name):
                continue
            key = re.sub(r"[\W_]+", "", name.lower())
            if key in GENERIC_NAMES:
                continue
            lat, lng = float(lat), float(lng)
            if any(abs(lat - a) < 0.002 and abs(lng - b) < 0.0025 for a, b in kept.get(key, [])):  # ~200 m
                continue
            bucket = buckets.setdefault(code, [])
            if len(bucket) < options["per_service"]:
                bucket.append((el, tags, lat, lng))
                kept.setdefault(key, []).append((lat, lng))

        total = 0
        for code, items in buckets.items():
            service = services[code]
            for el, tags, lat, lng in items:
                name = (tags.get("name:uz") or tags.get("name"))[:170]
                city = cities[region_slug(lat, lng)]
                street = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
                address = (tags.get("addr:full") or ", ".join(filter(None, [street, tags.get("addr:city")])) or city.name)[:300]
                phone = re.split(r"[;,]", tags.get("phone") or tags.get("contact:phone") or "")[0].strip()[:20]
                website = (tags.get("website") or tags.get("contact:website") or "").strip()
                details = [SERVICE_LABELS.get(code, service.name) + "."]
                if tags.get("stars"):
                    details.append(f"Yulduzlar: {tags['stars']}.")
                if tags.get("cuisine"):
                    details.append("Oshxona: " + tags["cuisine"].replace(";", ", ").replace("_", " ") + ".")
                if tags.get("opening_hours"):
                    details.append("Ish vaqti: " + tags["opening_hours"] + ".")
                description = " ".join(details) + "\n\n" + ATTRIBUTION

                club, _ = Club.objects.update_or_create(owner=owner, slug=f"osm-{el['type'][0]}{el['id']}", defaults={
                    "name": name, "service_type": service, "description": description, "address": address,
                    "phone": phone, "website": website[:500] if website.startswith(("http://", "https://")) else "",
                    "latitude": Decimal(f"{lat:.6f}"), "longitude": Decimal(f"{lng:.6f}"),
                    "status": Club.Status.ACTIVE, "is_verified": False,
                })
                hours = parse_hours(tags.get("opening_hours"))
                branch, _ = Branch.objects.update_or_create(club=club, defaults={
                    "name": name, "description": description, "address": address, "city": city,
                    "phone": phone,
                    "latitude": Decimal(f"{lat:.6f}"), "longitude": Decimal(f"{lng:.6f}"),
                    "status": Branch.Status.ACTIVE, "is_24_hours": bool(hours and hours[0] == "24/7"),
                })
                if hours and hours[0] == "weekly":
                    for weekday in range(7):
                        span = hours[1].get(weekday)
                        OperatingHour.objects.update_or_create(branch=branch, weekday=weekday, defaults={
                            "opens_at": span[0] if span else None, "closes_at": span[1] if span else None,
                            "is_closed": span is None,
                        })
                total += 1
            self.stdout.write(f"  {code}: {len(items)}")
        self.stdout.write(self.style.SUCCESS(f"{total} ta OSM joyi import qilindi (ma’lumot uchun)."))
