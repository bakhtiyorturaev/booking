import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User, UserProfile
from apps.barbers.models import Barber
from apps.clubs.models import City, Club, Branch


class Command(BaseCommand):
    help = "Sartaroshxona va sartarosh ustalar uchun to'liq mock ma'lumotlarni yaratish."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Eski mock sartaroshlar va salonlarni tozalab, qaytadan yaratish.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("clear"):
            self.stdout.write("Eski sartaroshlar va salonlar tozalanmoqda...")
            Barber.objects.all().delete()
            Club.objects.filter(category=Club.Category.BARBERSHOP).delete()
            self.stdout.write(self.style.WARNING("Eski ma'lumotlar tozalandi."))

        admin_user = (
            User.objects.filter(role__in=[User.Role.ADMIN, User.Role.MODERATOR]).first()
            or User.objects.first()
        )
        if not admin_user:
            admin_user = User.objects.create_superuser(
                phone="+998900000001",
                username="admin",
                role=User.Role.ADMIN,
            )
            UserProfile.objects.get_or_create(
                user=admin_user, defaults={"full_name": "Tizim Administratori"}
            )

        tashkent = City.objects.filter(name__icontains="Toshkent").first()
        samarkand = City.objects.filter(name__icontains="Samarqand").first()
        bukhara = City.objects.filter(name__icontains="Buxoro").first()
        fergana = City.objects.filter(name__icontains="Fargʻona").first() or City.objects.filter(name__icontains="Farg'ona").first()
        namangan = City.objects.filter(name__icontains="Namangan").first()
        andijan = City.objects.filter(name__icontains="Andijon").first()

        salons = [
            {
                "slug": "gentleman-barbershop",
                "name": "Gentleman Barbershop",
                "desc": "Toshkentdagi eng mashhur premium erkaklar sartaroshxonasi. Professional soch turmaklash va soqol parvarishi.",
                "phone": "+998712001122",
                "rating": "4.95",
                "reviews": 48,
                "branches": [
                    {
                        "name": "Gentleman — Yunusobod",
                        "desc": "Amir Temur shoh ko'chasi, Mega Planet ro'parasida",
                        "address": "Amir Temur shoh ko'chasi, 128",
                        "city": tashkent,
                        "phone": "+998712001122",
                        "lat": 41.3654,
                        "lon": 69.2891,
                    },
                    {
                        "name": "Gentleman — Mirobod",
                        "desc": "Oybek metro yaqinida, Mirobod bozori yonida",
                        "address": "Mirobod ko'chasi, 42",
                        "city": tashkent,
                        "phone": "+998712001123",
                        "lat": 41.2985,
                        "lon": 69.2741,
                    },
                ],
            },
            {
                "slug": "oldboy-barbershop",
                "name": "OldBoy Barbershop & Lounge",
                "desc": "Klassik va zamonaviy uslubdagi xalqaro sartaroshlik tarmog'i. Yuqori servis va tajribali ustalar.",
                "phone": "+998712003344",
                "rating": "4.90",
                "reviews": 36,
                "branches": [
                    {
                        "name": "OldBoy — Chilonzor",
                        "desc": "Bunyodkor shoh ko'chasi, Novza metro bekati",
                        "address": "Bunyodkor shoh ko'chasi, 45",
                        "city": tashkent,
                        "phone": "+998712003344",
                        "lat": 41.2858,
                        "lon": 69.2045,
                    },
                    {
                        "name": "OldBoy — Shayxontohur",
                        "desc": "Navoiy shoh ko'chasi, Xadra maydoni",
                        "address": "Navoiy ko'chasi, 16",
                        "city": tashkent,
                        "phone": "+998712003345",
                        "lat": 41.3214,
                        "lon": 69.2415,
                    },
                ],
            },
            {
                "slug": "chop-chop-tashkent",
                "name": "Chop-Chop Men's Grooming",
                "desc": "Erkaklar uchun minimalist va estetik sartaroshxona. Aniq chiziqlar va sifatli brend vositalari.",
                "phone": "+998712005566",
                "rating": "4.85",
                "reviews": 29,
                "branches": [
                    {
                        "name": "Chop-Chop — Yakkasaroy",
                        "desc": "Shota Rustaveli ko'chasi, Grand Mir mehmonxonasi yonida",
                        "address": "Shota Rustaveli ko'chasi, 22",
                        "city": tashkent,
                        "phone": "+998712005566",
                        "lat": 41.2912,
                        "lon": 69.2618,
                    }
                ],
            },
            {
                "slug": "samarkand-royal-barbershop",
                "name": "Samarkand Royal Barbershop",
                "desc": "Samarqand markazidagi eng nufuzli sartaroshxona. Tajribali ustalar va shohona xizmat.",
                "phone": "+998662334455",
                "rating": "4.96",
                "reviews": 42,
                "branches": [
                    {
                        "name": "Royal Barber — Registon",
                        "desc": "Registon maydoni yaqinida",
                        "address": "Registon ko'chasi, 5",
                        "city": samarkand,
                        "phone": "+998662334455",
                        "lat": 39.6542,
                        "lon": 66.9758,
                    }
                ],
            },
            {
                "slug": "bukhara-star-barber",
                "name": "Bukhara Star Barbershop",
                "desc": "Buxoro shahridagi zamonaviy erkaklar saloni. Soch, soqol va yuz parvarishi.",
                "phone": "+998652223344",
                "rating": "4.91",
                "reviews": 23,
                "branches": [
                    {
                        "name": "Star Barber — Buxoro Markaz",
                        "desc": "Ibn Sino ko'chasi, Markaziy xiyobon",
                        "address": "Ibn Sino ko'chasi, 18",
                        "city": bukhara,
                        "phone": "+998652223344",
                        "lat": 39.7747,
                        "lon": 64.4286,
                    }
                ],
            },
            {
                "slug": "topgun-barbershop",
                "name": "TopGun Barbershop Tashkent",
                "desc": "Zamonaviy stil, erkaklar muhiti va eng yaxshi sartaroshlar jamoasi.",
                "phone": "+998712008899",
                "rating": "4.98",
                "reviews": 54,
                "branches": [
                    {
                        "name": "TopGun — Mirzo Ulug'bek",
                        "desc": "Mustaqillik shoh ko'chasi, Buyuk Ipak Yo'li",
                        "address": "Mustaqillik shoh ko'chasi, 88",
                        "city": tashkent,
                        "phone": "+998712008899",
                        "lat": 41.3265,
                        "lon": 69.3241,
                    }
                ],
            },
        ]

        created_branches = {}

        for s in salons:
            club, _ = Club.objects.update_or_create(
                slug=s["slug"],
                defaults={
                    "owner": admin_user,
                    "name": s["name"],
                    "category": Club.Category.BARBERSHOP,
                    "description": s["desc"],
                    "phone": s["phone"],
                    "status": Club.Status.ACTIVE,
                    "is_verified": True,
                    "rating": s["rating"],
                    "review_count": s["reviews"],
                },
            )
            for b_data in s["branches"]:
                branch, _ = Branch.objects.update_or_create(
                    club=club,
                    name=b_data["name"],
                    defaults={
                        "description": b_data["desc"],
                        "address": b_data["address"],
                        "city": b_data["city"],
                        "phone": b_data["phone"],
                        "latitude": b_data["lat"],
                        "longitude": b_data["lon"],
                        "status": Branch.Status.ACTIVE,
                        "is_24_hours": False,
                    },
                )
                created_branches[b_data["name"]] = (club, branch)

        barbers_data = [
            # Gentleman Yunusobod
            {
                "phone": "+998901112233",
                "username": "jasur_barber",
                "name": "Jasur Beknazarov",
                "b_name": "Gentleman — Yunusobod",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.95",
                "revs": 32,
                "start": "09:00",
                "end": "21:00",
            },
            {
                "phone": "+998902223344",
                "username": "sherzod_barber",
                "name": "Sherzod Qodirov",
                "b_name": "Gentleman — Yunusobod",
                "status": Barber.Status.BREAK,
                "rating": "4.85",
                "revs": 19,
                "start": "10:00",
                "end": "20:00",
            },
            {
                "phone": "+998903331122",
                "username": "doniyor_barber",
                "name": "Doniyor Mahmudov",
                "b_name": "Gentleman — Yunusobod",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.94",
                "revs": 28,
                "start": "09:00",
                "end": "19:00",
            },
            # Gentleman Mirobod
            {
                "phone": "+998904441122",
                "username": "jamshid_barber",
                "name": "Jamshid Olimov",
                "b_name": "Gentleman — Mirobod",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.90",
                "revs": 24,
                "start": "10:00",
                "end": "22:00",
            },
            {
                "phone": "+998905551122",
                "username": "sardor_mirobod",
                "name": "Sardorbek Rahimov",
                "b_name": "Gentleman — Mirobod",
                "status": Barber.Status.NOT_AT_WORK,
                "rating": "4.82",
                "revs": 15,
                "start": "11:00",
                "end": "21:00",
            },
            # OldBoy Chilonzor
            {
                "phone": "+998903334455",
                "username": "alisher_barber",
                "name": "Alisher Mirzayev",
                "b_name": "OldBoy — Chilonzor",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.92",
                "revs": 38,
                "start": "09:00",
                "end": "21:00",
            },
            {
                "phone": "+998904445566",
                "username": "bobur_barber",
                "name": "Bobur Karimov",
                "b_name": "OldBoy — Chilonzor",
                "status": Barber.Status.AVAILABLE,
                "rating": "5.00",
                "revs": 44,
                "start": "09:00",
                "end": "20:00",
            },
            {
                "phone": "+998905556677",
                "username": "dilshod_barber",
                "name": "Dilshod Rustamov",
                "b_name": "OldBoy — Chilonzor",
                "status": Barber.Status.DAY_OFF,
                "rating": "4.70",
                "revs": 11,
                "start": "10:00",
                "end": "19:00",
            },
            # OldBoy Shayxontohur
            {
                "phone": "+998906665544",
                "username": "ulugbek_barber",
                "name": "Ulug'bek Xoliqov",
                "b_name": "OldBoy — Shayxontohur",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.89",
                "revs": 21,
                "start": "10:00",
                "end": "22:00",
            },
            # Chop-Chop Yakkasaroy
            {
                "phone": "+998907776655",
                "username": "farrux_barber",
                "name": "Farrux Usmonov",
                "b_name": "Chop-Chop — Yakkasaroy",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.88",
                "revs": 33,
                "start": "09:30",
                "end": "21:00",
            },
            {
                "phone": "+998908887766",
                "username": "shaxzod_barber",
                "name": "Shaxzod Saidov",
                "b_name": "Chop-Chop — Yakkasaroy",
                "status": Barber.Status.NOT_AT_WORK,
                "rating": "4.75",
                "revs": 16,
                "start": "10:00",
                "end": "20:00",
            },
            # Samarkand Royal Registon
            {
                "phone": "+998911112233",
                "username": "temur_samarkand",
                "name": "Temur Rahmonov",
                "b_name": "Royal Barber — Registon",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.96",
                "revs": 47,
                "start": "09:00",
                "end": "21:00",
            },
            {
                "phone": "+998912223344",
                "username": "sardor_samarkand",
                "name": "Sardor Jo'rayev",
                "b_name": "Royal Barber — Registon",
                "status": Barber.Status.BREAK,
                "rating": "4.80",
                "revs": 25,
                "start": "09:00",
                "end": "20:00",
            },
            # Bukhara Star
            {
                "phone": "+998931112233",
                "username": "elyor_bukhara",
                "name": "Elyor Hakimov",
                "b_name": "Star Barber — Buxoro Markaz",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.91",
                "revs": 31,
                "start": "09:00",
                "end": "20:00",
            },
            # TopGun Mirzo Ulug'bek
            {
                "phone": "+998909998877",
                "username": "azizbek_topgun",
                "name": "Azizbek To'rayev",
                "b_name": "TopGun — Mirzo Ulug'bek",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.98",
                "revs": 52,
                "start": "09:00",
                "end": "22:00",
            },
            {
                "phone": "+998908889900",
                "username": "otabek_topgun",
                "name": "Otabek Shukurov",
                "b_name": "TopGun — Mirzo Ulug'bek",
                "status": Barber.Status.AVAILABLE,
                "rating": "4.86",
                "revs": 29,
                "start": "10:00",
                "end": "21:00",
            },
            {
                "phone": "+998907778899",
                "username": "miraziz_topgun",
                "name": "Miraziz Ziyodov",
                "b_name": "TopGun — Mirzo Ulug'bek",
                "status": Barber.Status.NOT_AT_WORK,
                "rating": "4.78",
                "revs": 18,
                "start": "11:00",
                "end": "20:00",
            },
        ]

        barber_count = 0
        for b in barbers_data:
            user, _ = User.objects.get_or_create(
                phone=b["phone"],
                defaults={"username": b["username"], "role": User.Role.CUSTOMER},
            )
            UserProfile.objects.get_or_create(
                user=user, defaults={"full_name": b["name"]}
            )

            club, branch = created_branches[b["b_name"]]
            start_h, start_m = map(int, b["start"].split(":"))
            end_h, end_m = map(int, b["end"].split(":"))

            Barber.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": b["name"],
                    "phone": b["phone"],
                    "club": club,
                    "branch": branch,
                    "affiliation_status": Barber.AffiliationStatus.APPROVED,
                    "status": b["status"],
                    "work_start_time": datetime.time(start_h, start_m),
                    "work_end_time": datetime.time(end_h, end_m),
                    "working_days": [1, 2, 3, 4, 5, 6, 7],
                    "rating": b["rating"],
                    "review_count": b["revs"],
                    "is_active": True,
                },
            )
            barber_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Muvaffaqiyatli yakunlandi: {len(salons)} ta sartaroshxona va {barber_count} nafar sartarosh yaratildi/yangilandi."
            )
        )
