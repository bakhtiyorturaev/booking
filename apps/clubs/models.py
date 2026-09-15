import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
IMAGE_VALIDATORS = (
    FileExtensionValidator(
        allowed_extensions=IMAGE_EXTENSIONS,
        message="clubs.invalid_image_format",
        code="clubs.invalid_image_format",
    ),
)


def validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError("clubs.image_size_exceeded", code="clubs.image_size_exceeded")


def _image_upload_path(folder, object_id, filename):
    extension = Path(filename).suffix.lower()
    return f"clubs/{object_id}/{folder}/{uuid.uuid4().hex}{extension}"


def club_logo_upload_to(instance, filename):
    return _image_upload_path("logo", instance.id, filename)


def club_cover_upload_to(instance, filename):
    return _image_upload_path("cover", instance.id, filename)


def branch_image_upload_to(instance, filename):
    return _image_upload_path("branches", instance.branch_id, filename)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Club(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending moderation"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        ARCHIVED = "ARCHIVED", "Archived"

    class Category(models.TextChoices):
        GAMING_CLUB = "GAMING_CLUB", "Gaming Club"
        BARBERSHOP = "BARBERSHOP", "Barbershop"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_clubs",
        help_text="Klub egasi.",
    )
    name = models.CharField(max_length=180, help_text="Klub nomi.")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GAMING_CLUB,
        help_text="Muassasa toifasi.",
    )
    slug = models.SlugField(max_length=210, unique=True, help_text="URL uchun nom.")
    description = models.TextField(blank=True, help_text="Klub tavsifi.")
    logo = models.ImageField(
        upload_to=club_logo_upload_to,
        blank=True,
        validators=(*IMAGE_VALIDATORS, validate_image_size),
        help_text="Klub logotipi.",
    )
    cover = models.ImageField(
        upload_to=club_cover_upload_to,
        blank=True,
        validators=(*IMAGE_VALIDATORS, validate_image_size),
        help_text="Klub muqova rasmi.",
    )
    phone = models.CharField(max_length=20, blank=True, help_text="Aloqa telefoni.")
    email = models.EmailField(blank=True, help_text="Aloqa emaili.")
    website = models.URLField(max_length=500, blank=True, help_text="Klub sayti.")
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Klub holati.",
    )
    is_verified = models.BooleanField(default=False, help_text="Tekshiruvdan o‘tganmi.")
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="O‘rtacha reyting.",
    )
    review_count = models.PositiveIntegerField(default=0, help_text="Izohlar soni.")

    class Meta:
        db_table = "clubs"
        verbose_name = "Klub"
        verbose_name_plural = "Klublar"
        ordering = ("-is_verified", "-rating", "name")
        indexes = [
            models.Index(fields=["status", "rating"], name="club_status_rating_idx"),
            models.Index(fields=["owner", "status"], name="club_owner_status_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "club"
            candidate = base
            number = 2
            while Club.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class City(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, help_text="Shahar nomi.")
    slug = models.SlugField(max_length=140, unique=True, help_text="Shahar kodi.")
    is_active = models.BooleanField(default=True, help_text="Tanlash uchun faolmi.")
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")

    class Meta:
        db_table = "cities"
        verbose_name = "Shahar"
        verbose_name_plural = "Shaharlar"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "city"
            candidate = base
            number = 2
            while City.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class District(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="districts",
        help_text="Tuman tegishli shahar.",
    )
    name = models.CharField(max_length=120, help_text="Tuman nomi.")
    slug = models.SlugField(max_length=140, help_text="Tuman kodi.")
    is_active = models.BooleanField(default=True, help_text="Tanlash uchun faolmi.")
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")

    class Meta:
        db_table = "districts"
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        ordering = ("city__sort_order", "city__name", "sort_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["city", "slug"],
                name="unique_district_slug_per_city",
            ),
            models.UniqueConstraint(
                fields=["city", "name"],
                name="unique_district_name_per_city",
            ),
        ]
        indexes = [
            models.Index(
                fields=["city", "is_active", "sort_order"],
                name="district_city_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.city.name} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "district"
            candidate = base
            number = 2
            while (
                District.objects.exclude(pk=self.pk)
                .filter(city_id=self.city_id, slug=candidate)
                .exists()
            ):
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class Branch(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        TEMPORARILY_CLOSED = "TEMP_CLOSED", "Temporarily closed"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="branches",
        help_text="Filial tegishli klub.",
    )
    name = models.CharField(max_length=180, help_text="Filial nomi.")
    description = models.TextField(blank=True, help_text="Filial tavsifi.")
    address = models.CharField(max_length=300, help_text="Ko‘cha, uy va bino manzili.")
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="branches",
        help_text="Filial joylashgan shahar.",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="branches",
        null=True,
        blank=True,
        help_text="Filial joylashgan tuman.",
    )
    landmark = models.CharField(max_length=250, blank=True, help_text="Mo‘ljal.")
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Xarita kengligi.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Xarita uzunligi.",
    )
    phone = models.CharField(max_length=20, blank=True, help_text="Filial telefoni.")
    timezone = models.CharField(
        max_length=64,
        default="Asia/Tashkent",
        help_text="Vaqt mintaqasi.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Filial holati.",
    )
    slot_interval_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        help_text="Bron vaqt qadami, daqiqada.",
    )
    minimum_booking_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(30), MaxValueValidator(1440)],
        help_text="Minimal bron vaqti.",
    )
    maximum_booking_minutes = models.PositiveSmallIntegerField(
        default=720,
        validators=[MinValueValidator(30), MaxValueValidator(1440)],
        help_text="Maksimal bron vaqti.",
    )
    booking_hold_minutes = models.PositiveSmallIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Joyni ushlab turish vaqti.",
    )
    advance_booking_days = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Oldindan bron qilish kunlari.",
    )
    free_cancellation_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Bepul bekor qilish muddati.",
    )
    no_show_grace_minutes = models.PositiveSmallIntegerField(
        default=20,
        help_text="Kechikish uchun kutish vaqti.",
    )
    auto_confirm_booking = models.BooleanField(
        default=True,
        help_text="Bron avtomatik tasdiqlanadimi.",
    )
    is_24_hours = models.BooleanField(default=False, help_text="Filial 24/7 ishlaydimi.")

    class Meta:
        db_table = "club_branches"
        verbose_name = "Klub filiali"
        verbose_name_plural = "Klub filiallari"
        ordering = ("club__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["club", "name"],
                name="unique_branch_name_per_club",
            ),
            models.CheckConstraint(
                condition=Q(maximum_booking_minutes__gte=models.F("minimum_booking_minutes")),
                name="branch_max_booking_gte_min",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "city"], name="branch_status_city_idx"),
            models.Index(fields=["latitude", "longitude"], name="branch_geo_idx"),
        ]

    def __str__(self):
        return f"{self.club.name} — {self.name}"

    def clean(self):
        if (
            self.city_id
            and self.district_id
            and self.district.city_id != self.city_id
        ):
            raise ValidationError({"district": "clubs.district_not_belong_to_city"})
        if self.maximum_booking_minutes < self.minimum_booking_minutes:
            raise ValidationError(
                {"maximum_booking_minutes": "clubs.max_duration_less_than_min"}
            )
        if self.minimum_booking_minutes % self.slot_interval_minutes:
            raise ValidationError(
                {"minimum_booking_minutes": "clubs.min_duration_not_divisible_by_interval"}
            )

    @property
    def hold_duration(self):
        return timedelta(minutes=self.booking_hold_minutes)

    @property
    def full_address(self):
        parts = [self.city.name]
        if self.district_id:
            parts.append(self.district.name)
        parts.append(self.address)
        return ", ".join(part for part in parts if part)


class BranchImage(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Rasm tegishli filial.",
    )
    image = models.ImageField(
        upload_to=branch_image_upload_to,
        validators=(*IMAGE_VALIDATORS, validate_image_size),
        help_text="Filial rasmi.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")
    is_cover = models.BooleanField(default=False, help_text="Asosiy rasmmi.")

    class Meta:
        db_table = "branch_images"
        verbose_name = "Filial rasmi"
        verbose_name_plural = "Filial rasmlari"
        ordering = ("sort_order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["branch"],
                condition=Q(is_cover=True),
                name="one_cover_image_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.branch} image"


class OperatingHour(TimeStampedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="operating_hours",
        help_text="Ish vaqti tegishli filial.",
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        help_text="Hafta kuni.",
    )
    opens_at = models.TimeField(null=True, blank=True, help_text="Ochilish vaqti.")
    closes_at = models.TimeField(null=True, blank=True, help_text="Yopilish vaqti.")
    is_closed = models.BooleanField(default=False, help_text="Yopilgan")

    class Meta:
        db_table = "branch_operating_hours"
        verbose_name = "Ish vaqti"
        verbose_name_plural = "Ish vaqtlari"
        ordering = ("weekday",)
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "weekday"],
                name="unique_branch_weekday",
            )
        ]

    def __str__(self):
        return f"{self.branch} — {self.get_weekday_display()}"

    def clean(self):
        if self.is_closed:
            return
        if self.opens_at is None or self.closes_at is None:
            raise ValidationError("clubs.open_hours_required")


class SpecialSchedule(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="special_schedules",
        help_text="Jadval tegishli filial.",
    )
    date = models.DateField(help_text="Maxsus sana.")
    opens_at = models.TimeField(null=True, blank=True, help_text="Ochilish vaqti.")
    closes_at = models.TimeField(null=True, blank=True, help_text="Yopilish vaqti.")
    is_closed = models.BooleanField(default=False, help_text="Filial yopiqmi.")
    note = models.CharField(max_length=250, blank=True, help_text="Qo‘shimcha izoh.")

    class Meta:
        db_table = "branch_special_schedules"
        verbose_name = "Maxsus ish jadvali"
        verbose_name_plural = "Maxsus ish jadvallari"
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "date"],
                name="unique_branch_special_date",
            )
        ]

    def __str__(self):
        return f"{self.branch} — {self.date}"

    def clean(self):
        if not self.is_closed and (self.opens_at is None or self.closes_at is None):
            raise ValidationError("clubs.special_open_hours_required")


class Zone(TimeStampedModel):
    class BookingType(models.TextChoices):
        PER_SEAT = "PER_SEAT", "Har bir joy uchun"
        PER_ZONE = "PER_ZONE", "Butun xona uchun"

    class ResourceType(models.TextChoices):
        COMPUTER = "COMPUTER", "Computer"
        PLAYSTATION = "PLAYSTATION", "PlayStation"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        DISABLED = "DISABLED", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="zones",
        help_text="Zona tegishli filial.",
    )
    name = models.CharField(max_length=120, help_text="Zona nomi.")
    description = models.TextField(blank=True, help_text="Zona tavsifi.")
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Zona holati.",
    )
    resource_type = models.CharField(
        max_length=12,
        choices=ResourceType.choices,
        default=ResourceType.COMPUTER,
        help_text="O‘yin qurilmasi turi.",
    )
    capacity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Zaldagi joylar yoki bitta xonaning odam sig‘imi.",
    )
    booking_type = models.CharField(
        max_length=8,
        choices=BookingType.choices,
        default=BookingType.PER_SEAT,
        help_text="Narx har bir joy yoki butun xona uchun hisoblanishi.",
    )
    unit_count = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Bir xil xonalar soni. Joy bo‘yicha bronlashda 1.",
    )
    price_per_hour_tiyin = models.PositiveBigIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Bitta joy yoki xonaning bir soatlik narxi, tiyinlarda.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")

    class Meta:
        db_table = "club_zones"
        verbose_name = "O‘yin zonasi"
        verbose_name_plural = "O‘yin zonalari"
        ordering = ("sort_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                name="unique_zone_name_per_branch",
            )
        ]
        indexes = [
            models.Index(
                fields=["branch", "resource_type", "status"],
                name="zone_branch_type_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.branch} — {self.name}"

    @property
    def booking_capacity(self):
        if self.booking_type == self.BookingType.PER_ZONE:
            return self.unit_count
        return self.capacity


class ResourceBlock(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="resource_blocks",
        help_text="Blok tegishli zona.",
    )
    starts_at = models.DateTimeField(help_text="Blok boshlanish vaqti.")
    ends_at = models.DateTimeField(help_text="Blok tugash vaqti.")
    reason = models.CharField(max_length=250, help_text="Bloklash sababi.")
    is_active = models.BooleanField(default=True, help_text="Blok faolmi.")

    class Meta:
        db_table = "club_resource_blocks"
        verbose_name = "Zona blokirovkasi"
        verbose_name_plural = "Zona blokirovkalari"
        ordering = ("starts_at",)
        indexes = [
            models.Index(fields=["zone", "starts_at", "ends_at"], name="block_zone_time_idx"),
        ]

    def __str__(self):
        return f"{self.zone} — {self.starts_at:%Y-%m-%d %H:%M}"

    def clean(self):
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "clubs.end_time_before_start_time"})

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now < self.ends_at


class Favorite(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_clubs",
        help_text="Sevimliga qo‘shgan foydalanuvchi.",
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        help_text="Sevimli klub.",
    )

    class Meta:
        db_table = "favorite_clubs"
        verbose_name = "Sevimli klub"
        verbose_name_plural = "Sevimli klublar"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "club"],
                name="unique_user_favorite_club",
            )
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} — {self.club}"
