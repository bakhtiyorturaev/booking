import uuid

from django.db.models import F, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.clubs.models import (
    Branch,
    BranchImage,
    City,
    Club,
    District,
    Favorite,
    OperatingHour,
    ResourceBlock,
    SpecialSchedule,
    Zone,
)
from apps.clubs.permissions import (
    IsClubOperator,
    IsOwnerOrPlatformAdmin,
    can_manage_club,
    is_platform_admin,
)
from apps.clubs.serializers import (
    BranchImageSerializer,
    BranchManagementSerializer,
    CitySerializer,
    ClubManagementSerializer,
    DistrictSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    OperatingHourSerializer,
    PublicBranchDetailSerializer,
    PublicClubListSerializer,
    ResourceBlockSerializer,
    SpecialScheduleSerializer,
    ZoneSerializer,
)
from apps.clubs.public_serializers import PublicBranchListSerializer
from apps.clubs.services.geo import haversine_km


def parse_decimal_parameter(request, name, minimum=None, maximum=None):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise ValidationError({name: "clubs.invalid_integer"}, code="clubs.invalid_integer") from error
    if minimum is not None and value < minimum:
        raise ValidationError({name: "clubs.below_minimum"}, code="clubs.below_minimum")
    if maximum is not None and value > maximum:
        raise ValidationError({name: "clubs.above_maximum"}, code="clubs.above_maximum")
    return value


def parse_integer_parameter(request, name, minimum=None, maximum=None):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ValidationError({name: "clubs.invalid_integer"}, code="clubs.invalid_integer") from error
    if str(value) != str(raw).strip() and not str(raw).strip().startswith("+"):
        raise ValidationError({name: "clubs.invalid_integer"}, code="clubs.invalid_integer")
    if minimum is not None and value < minimum:
        raise ValidationError({name: "clubs.below_minimum"}, code="clubs.below_minimum")
    if maximum is not None and value > maximum:
        raise ValidationError({name: "clubs.above_maximum"}, code="clubs.above_maximum")
    return value


def requested_location(request):
    latitude = parse_decimal_parameter(request, "latitude", -90, 90)
    longitude = parse_decimal_parameter(request, "longitude", -180, 180)
    if (latitude is None) != (longitude is None):
        raise ValidationError(
            {"location": "clubs.lat_lng_both_required"},
            code="clubs.lat_lng_both_required",
        )
    return latitude, longitude


def requested_service_type(request):
    value = request.query_params.get("service_type")
    if not value:
        return None
    value = value.strip().upper()
    if value in ("PC", "CYBER", "COMPUTER"):
        return Zone.ResourceType.COMPUTER
    if value in ("PS", "PS5", "PLAYSTATION"):
        return Zone.ResourceType.PLAYSTATION
    if value in Zone.ResourceType.values:
        return value
    return None


def location_filter(prefix, field, value):
    if not value:
        return Q()
    value = value.strip()
    try:
        return Q(**{f"{prefix}{field}_id": uuid.UUID(value)})
    except (TypeError, ValueError):
        return Q(**{f"{prefix}{field}__slug__iexact": value}) | Q(
            **{f"{prefix}{field}__name__iexact": value}
        )


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def active_branch_queryset():
    active_zones = Zone.objects.filter(status=Zone.Status.ACTIVE)
    return (
        Branch.objects.filter(status=Branch.Status.ACTIVE)
        .annotate(min_price_tiyin=Min("zones__price_per_hour_tiyin", filter=Q(zones__status=Zone.Status.ACTIVE),))
        .select_related("club", "city", "district", "district__city")
        .prefetch_related("images", "operating_hours", "special_schedules",Prefetch("zones", queryset=active_zones),)
    )


def active_branch_list_queryset():
    return (
        Branch.objects.filter(status=Branch.Status.ACTIVE)
        .annotate(min_price_tiyin=Min("zones__price_per_hour_tiyin",filter=Q(zones__status=Zone.Status.ACTIVE),))
        .select_related("club", "city", "district", "district__city")
        .prefetch_related(
            Prefetch("images",queryset=BranchImage.objects.filter(is_cover=True),),
            Prefetch("zones",queryset=Zone.objects.filter(status=Zone.Status.ACTIVE).only("branch_id", "resource_type",),),
        )
        .order_by("club__name", "name")
    )


PUBLIC_CLUB_PARAMETERS = [
    OpenApiParameter("search", str, description="Club, branch, address, city or district"),
    OpenApiParameter("category", str, enum=Club.Category.values, description="GAMING_CLUB or BARBERSHOP"),
    OpenApiParameter("city", str, description="City UUID or slug"),
    OpenApiParameter("district", str, description="District UUID or slug"),
    OpenApiParameter("min_rating", float),
    OpenApiParameter("min_price_tiyin", int, description="Minimum hourly price in tiyin"),
    OpenApiParameter("max_price_tiyin", int, description="Maximum hourly price in tiyin"),
    OpenApiParameter("service_type",str, enum=Zone.ResourceType.values, description="COMPUTER or PLAYSTATION",),
    OpenApiParameter("latitude", float),
    OpenApiParameter("longitude", float),
    OpenApiParameter("radius_km", float),
    OpenApiParameter("ordering", str, enum=["distance", "price", "-price", "rating", "-rating", "name", "-name"],),
]


@extend_schema_view(
    list=extend_schema(
        tags=["Clubs"],
        summary="Faol klublarni qidirish va filtrlash",
        parameters=PUBLIC_CLUB_PARAMETERS,
    ),
    retrieve=extend_schema(tags=["Clubs"], summary="Klub tafsilotlarini olish"),
)
class PublicClubViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicClubListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = self.request.query_params
        city_filter = location_filter("", "city", params.get("city"))
        district_filter = location_filter("", "district", params.get("district"))
        branch_location_filter = location_filter("branches__", "city", params.get("city")) & location_filter("branches__", "district", params.get("district"))
        branches = active_branch_queryset().filter(city_filter, district_filter)
        queryset = (
            Club.objects.filter(status=Club.Status.ACTIVE, branches__status=Branch.Status.ACTIVE)
            .annotate(min_price_tiyin=Min("branches__zones__price_per_hour_tiyin",
                    filter=Q(
                        branches__status=Branch.Status.ACTIVE,
                        branches__zones__status=Zone.Status.ACTIVE,
                    )
                    & branch_location_filter,
                )
            )
            .prefetch_related(Prefetch("branches", queryset=branches))
            .distinct()
        )
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(branches__name__icontains=search)
                | Q(branches__address__icontains=search)
                | Q(branches__city__name__icontains=search)
                | Q(branches__district__name__icontains=search)
            ).distinct()
        if params.get("city"):
            queryset = queryset.filter(location_filter("branches__", "city", params["city"])).distinct()
        if params.get("district"):
            queryset = queryset.filter(location_filter("branches__", "district", params["district"])).distinct()
        min_rating = parse_decimal_parameter(self.request, "min_rating", 0, 5)
        min_price = parse_integer_parameter(self.request, "min_price_tiyin", 0)
        max_price = parse_integer_parameter(self.request, "max_price_tiyin", 0)
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError({"price": "clubs.min_price_greater_than_max"}, code="clubs.min_price_greater_than_max")
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)
        if min_price is not None:
            queryset = queryset.filter(min_price_tiyin__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(min_price_tiyin__lte=max_price)
        category = params.get("category")
        if category:
            category_val = category.strip().upper()
            if category_val in Club.Category.values:
                queryset = queryset.filter(category=category_val)
        service_type = requested_service_type(self.request)
        if service_type:
            queryset = queryset.filter(
                branches__status=Branch.Status.ACTIVE,
                branches__zones__status=Zone.Status.ACTIVE,
                branches__zones__resource_type=service_type,
            ).distinct()
        return queryset.distinct()

    def get_object(self):
        value = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
        queryset = self.get_queryset()
        try:
            uuid.UUID(str(value))
            lookup = {"pk": value}
        except ValueError:
            lookup = {"slug": value}
        obj = get_object_or_404(queryset, **lookup)
        self.check_object_permissions(self.request, obj)
        return obj

    def _distance_maps(self, clubs):
        latitude, longitude = requested_location(self.request)
        branch_distances = {}
        club_distances = {}
        if latitude is None:
            return club_distances, branch_distances
        for club in clubs:
            distances = []
            for branch in club.branches.all():
                distance = haversine_km(
                    latitude,
                    longitude,
                    branch.latitude,
                    branch.longitude,
                )
                branch_distances[str(branch.id)] = distance
                distances.append(distance)
            if distances:
                club_distances[str(club.id)] = min(distances)
        return club_distances, branch_distances

    def _serializer_context(self, clubs):
        club_distances, branch_distances = self._distance_maps(clubs)
        favorite_ids = set()
        if self.request.user and self.request.user.is_authenticated:
            favorite_ids = set(
                Favorite.objects.filter(
                    user=self.request.user,
                    club__in=clubs,
                ).values_list("club_id", flat=True)
            )
        context = self.get_serializer_context()
        context.update(
            {
                "club_distances": club_distances,
                "branch_distances": branch_distances,
                "favorite_club_ids": favorite_ids,
            }
        )
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        latitude, longitude = requested_location(request)
        radius = parse_decimal_parameter(request, "radius_km", 0.1, 1000)
        ordering = request.query_params.get("ordering") or (
            "distance" if latitude is not None else "-rating"
        )

        valid_orderings = {"distance", "price", "-price", "rating", "-rating", "name", "-name"}
        if ordering not in valid_orderings:
            raise ValidationError({"ordering": "clubs.invalid_ordering"}, code="clubs.invalid_ordering")

        if ordering == "distance" and latitude is None:
            raise ValidationError({"ordering": "clubs.distance_ordering_requires_coords"}, code="clubs.distance_ordering_requires_coords")

        if radius is not None and latitude is None:
            raise ValidationError({"radius_km": "clubs.distance_filter_requires_coords"}, code="clubs.distance_filter_requires_coords")

        # In-memory geo sorting or filtering when location distance is needed
        if ordering == "distance" or radius is not None:
            clubs = list(queryset)
            club_distances, _ = self._distance_maps(clubs)
            if radius is not None:
                clubs = [
                    club
                    for club in clubs
                    if club_distances.get(str(club.id), float("inf")) <= radius
                ]
            if ordering == "distance":
                clubs.sort(key=lambda item: club_distances.get(str(item.id), float("inf")))
            elif ordering in {"price", "-price"}:
                reverse = ordering.startswith("-")
                clubs.sort(
                    key=lambda item: (
                        item.min_price_tiyin is None,
                        item.min_price_tiyin if item.min_price_tiyin is not None else 0,
                    ),
                    reverse=reverse,
                )
            elif ordering in {"rating", "-rating", "name", "-name"}:
                reverse = ordering.startswith("-")
                field = ordering.lstrip("-")
                clubs.sort(key=lambda item: getattr(item, field), reverse=reverse)

            page = self.paginate_queryset(clubs)
            targets = page if page is not None else clubs
            serialized = self.get_serializer(
                targets,
                many=True,
                context=self._serializer_context(targets),
            )
            if page is not None:
                return self.get_paginated_response(serialized.data)
            return Response(serialized.data)

        # Database-level sorting & pagination when distance calculation is not required
        if ordering == "price":
            queryset = queryset.order_by(F("min_price_tiyin").asc(nulls_last=True), "name")
        elif ordering == "-price":
            queryset = queryset.order_by(F("min_price_tiyin").desc(nulls_last=True), "name")
        elif ordering == "rating":
            queryset = queryset.order_by("rating", "name")
        elif ordering == "-rating":
            queryset = queryset.order_by("-is_verified", "-rating", "name")
        elif ordering == "name":
            queryset = queryset.order_by("name")
        elif ordering == "-name":
            queryset = queryset.order_by("-name")

        page = self.paginate_queryset(queryset)
        targets = list(page) if page is not None else list(queryset)
        serialized = self.get_serializer(
            targets,
            many=True,
            context=self._serializer_context(targets),
        )
        if page is not None:
            return self.get_paginated_response(serialized.data)
        return Response(serialized.data)

    def retrieve(self, request, *args, **kwargs):
        club = self.get_object()
        serializer = self.get_serializer(
            club,
            context=self._serializer_context([club]),
        )
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=["Branches"],
        summary="Faol klub filiallarini olish",
        parameters=[
            OpenApiParameter("category", str, enum=Club.Category.values, description="GAMING_CLUB or BARBERSHOP"),
            OpenApiParameter("city", str, description="City UUID or slug"),
            OpenApiParameter("district", str, description="District UUID or slug"),
            OpenApiParameter("service_type",str, enum=Zone.ResourceType.values,),
            OpenApiParameter("latitude", float),
            OpenApiParameter("longitude", float),
            OpenApiParameter("radius_km", float),
            OpenApiParameter("ordering", str, enum=["distance", "name", "-name"],),
        ],
    ),
    retrieve=extend_schema(
        tags=["Branches"],
        summary="Filial tafsilotlari va bron qoidalarini olish",
    ),
)
class PublicBranchViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "list":
            return PublicBranchListSerializer
        return PublicBranchDetailSerializer

    def get_queryset(self):
        queryset = (
            active_branch_list_queryset()
            if self.action == "list"
            else active_branch_queryset()
        ).filter(club__status=Club.Status.ACTIVE)
        club_id = self.request.query_params.get("club")
        category = self.request.query_params.get("category")
        city = self.request.query_params.get("city")
        district = self.request.query_params.get("district")
        search = (self.request.query_params.get("search") or "").strip()
        min_price = parse_integer_parameter(self.request, "min_price_tiyin", 0)
        max_price = parse_integer_parameter(self.request, "max_price_tiyin", 0)
        min_rating = parse_decimal_parameter(self.request, "min_rating", 0, 5)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(club__name__icontains=search)
                | Q(full_address__icontains=search)
            )
        if club_id:
            queryset = queryset.filter(club_id=club_id)
        if category:
            category_val = category.strip().upper()
            if category_val in Club.Category.values:
                queryset = queryset.filter(club__category=category_val)
        if city:
            queryset = queryset.filter(location_filter("", "city", city))
        if district:
            queryset = queryset.filter(location_filter("", "district", district))
        if min_rating is not None:
            queryset = queryset.filter(club__rating__gte=min_rating)
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError({"price": "clubs.min_price_greater_than_max"}, code="clubs.min_price_greater_than_max")
        if min_price is not None:
            queryset = queryset.filter(min_price_tiyin__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(min_price_tiyin__lte=max_price)

        service_type = requested_service_type(self.request)
        if service_type:
            queryset = queryset.filter(
                zones__status=Zone.Status.ACTIVE,
                zones__resource_type=service_type,
            )
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        latitude, longitude = requested_location(request)
        radius = parse_decimal_parameter(request, "radius_km", 0.1, 1000)
        ordering = request.query_params.get("ordering") or ("distance" if latitude is not None else "-rating")

        valid_orderings = {"distance", "name", "-name", "rating", "-rating", "price", "-price"}
        if ordering not in valid_orderings:
            raise ValidationError({"ordering": "clubs.invalid_ordering"}, code="clubs.invalid_ordering")

        if ordering == "distance" and latitude is None:
            raise ValidationError({"ordering": "clubs.distance_ordering_requires_coords"}, code="clubs.distance_ordering_requires_coords")

        if radius is not None and latitude is None:
            raise ValidationError({"radius_km": "clubs.distance_filter_requires_coords"}, code="clubs.distance_filter_requires_coords")

        # In-memory geo sorting or filtering when location distance is needed
        if ordering == "distance" or radius is not None:
            branches = list(queryset)
            distances = {
                str(branch.id): haversine_km(
                    latitude,
                    longitude,
                    branch.latitude,
                    branch.longitude,
                )
                for branch in branches
            }
            if radius is not None:
                branches = [
                    branch
                    for branch in branches
                    if distances[str(branch.id)] <= radius
                ]
            if ordering == "distance":
                branches.sort(key=lambda branch: distances[str(branch.id)])
            elif ordering in {"name", "-name"}:
                branches.sort(
                    key=lambda branch: branch.name.casefold(),
                    reverse=ordering.startswith("-"),
                )
            elif ordering in {"price", "-price"}:
                branches.sort(
                    key=lambda branch: (
                        branch.min_price_tiyin is None,
                        branch.min_price_tiyin if branch.min_price_tiyin is not None else 0,
                    ),
                    reverse=ordering.startswith("-"),
                )
            elif ordering in {"rating", "-rating"}:
                branches.sort(
                    key=lambda branch: branch.club.rating or 0,
                    reverse=ordering.startswith("-"),
                )

            page = self.paginate_queryset(branches)
            serializer = self.get_serializer(
                page if page is not None else branches,
                many=True,
            )
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        # Database-level sorting & pagination when distance calculation is not required
        if ordering == "price":
            queryset = queryset.order_by(F("min_price_tiyin").asc(nulls_last=True), "name")
        elif ordering == "-price":
            queryset = queryset.order_by(F("min_price_tiyin").desc(nulls_last=True), "name")
        elif ordering == "rating":
            queryset = queryset.order_by("club__rating", "name")
        elif ordering == "-rating":
            queryset = queryset.order_by("-club__rating", "name")
        elif ordering == "name":
            queryset = queryset.order_by("club__name", "name")
        elif ordering == "-name":
            queryset = queryset.order_by("-club__name", "-name")

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        latitude, longitude = requested_location(self.request)
        if latitude is not None:
            context["location"] = (latitude, longitude)
        if latitude is not None and getattr(self, "kwargs", {}).get("pk"):
            try:
                branch = self.get_queryset().only("latitude", "longitude").get(pk=self.kwargs["pk"])
                context["distance_km"] = haversine_km(
                    latitude, longitude, branch.latitude, branch.longitude
                )
            except (Branch.DoesNotExist, ValueError):
                pass
        favorite_ids = set()
        if self.request.user and self.request.user.is_authenticated:
            favorite_ids = set(
                Favorite.objects.filter(
                    user=self.request.user,
                ).values_list("club_id", flat=True)
            )
        context["favorite_club_ids"] = favorite_ids
        return context

    @extend_schema(
        tags=["Branches"],
        summary="Filial zonalari va narxlarini olish",
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["get"], url_path="resources")
    def resources(self, request, pk=None):
        branch = self.get_object()
        return Response(
            {
                "branch_id": str(branch.id),
                "slot_interval_minutes": branch.slot_interval_minutes,
                "minimum_booking_minutes": branch.minimum_booking_minutes,
                "zones": PublicBranchDetailSerializer(branch, context=self.get_serializer_context(),).data["zones"],
            }
        )


@extend_schema_view(
    list=extend_schema(tags=["Locations"], summary="Faol shaharlarni olish"),
    retrieve=extend_schema(tags=["Locations"], summary="Shahar ma’lumotini olish"),
)
class CityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CitySerializer
    pagination_class = None
    queryset = City.objects.filter(is_active=True)

    def get_queryset(self):
        queryset = self.queryset
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Locations"], summary="Faol tumanlarni olish"),
    retrieve=extend_schema(tags=["Locations"], summary="Tuman ma’lumotini olish"),
)
class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = DistrictSerializer
    pagination_class = None
    queryset = District.objects.filter(is_active=True).select_related("city")

    def get_queryset(self):
        queryset = self.queryset
        city = self.request.query_params.get("city")
        search = self.request.query_params.get("search", "").strip()
        if city:
            queryset = queryset.filter(location_filter("", "city", city))
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Favorites"], summary="Sevimli klublarni olish"),
    create=extend_schema(tags=["Favorites"], summary="Klubni sevimlilarga qo‘shish"),
    destroy=extend_schema(tags=["Favorites"], summary="Klubni sevimlilardan o‘chirish"),
)
class FavoriteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    queryset = Favorite.objects.none()

    def get_queryset(self):
        return (
            Favorite.objects.filter(
                user=self.request.user,
                club__status=Club.Status.ACTIVE,
            )
            .select_related("club")
            .prefetch_related(
                Prefetch("club__branches", queryset=active_branch_queryset())
            )
        )

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        queryset = self.get_queryset()
        try:
            uuid.UUID(str(lookup))
            obj = queryset.filter(Q(id=lookup) | Q(club__id=lookup)).first()
            if obj:
                return obj
        except (ValueError, TypeError):
            pass
        obj = queryset.filter(club__slug=lookup).first()
        if obj:
            return obj
        return get_object_or_404(queryset, pk=lookup)

    def get_serializer_class(self):
        if self.action == "create":
            return FavoriteCreateSerializer
        return FavoriteSerializer


def manageable_club_filter(user, prefix=""):
    if is_platform_admin(user):
        return Q()
    owner_lookup = f"{prefix}owner"
    return Q(**{owner_lookup: user})


class CabinetAccessMixin:
    club_path = "club"
    managers_only = False

    def _club_from_validated_data(self, data):
        obj = data.get(self.club_path)
        if isinstance(obj, Club):
            return obj
        if isinstance(obj, Branch):
            return obj.club
        if isinstance(obj, Zone):
            return obj.branch.club
        return None

    def _assert_write_access(self, serializer):
        club = self._club_from_validated_data(serializer.validated_data)
        if club is None and serializer.instance is not None:
            if hasattr(serializer.instance, "club"):
                club = serializer.instance.club
            elif hasattr(serializer.instance, "branch"):
                club = serializer.instance.branch.club
            elif hasattr(serializer.instance, "zone"):
                club = serializer.instance.zone.branch.club
        if not can_manage_club(
            self.request.user,
            club,
            managers_only=self.managers_only,
        ):
            raise PermissionDenied("clubs.permission_denied", code="clubs.permission_denied")

    def perform_create(self, serializer):
        self._assert_write_access(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._assert_write_access(serializer)
        serializer.save()


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Boshqariladigan klublarni olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Klub yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Klub ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Klubni to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Klubni qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Klubni arxivlash"),
)
class CabinetClubViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrPlatformAdmin]
    serializer_class = ClubManagementSerializer
    pagination_class = StandardPagination
    queryset = Club.objects.none()

    def get_queryset(self):
        user = self.request.user
        if is_platform_admin(user):
            qs = Club.objects.all()
        else:
            qs = Club.objects.filter(owner=user)
        status_param = self.request.query_params.get("status")
        if status_param and status_param in Club.Status.values:
            qs = qs.filter(status=status_param)
        query = self.request.query_params.get("query", "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query) | Q(slug__icontains=query) | Q(phone__icontains=query)
            )
        return qs.order_by("-created_at")

    def get_permissions(self):
        if self.action in {"list", "create"}:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        initial_status = serializer.validated_data.get(
            "status",
            Club.Status.ACTIVE if is_platform_admin(self.request.user) else Club.Status.DRAFT,
        )
        serializer.save(owner=self.request.user, status=initial_status)

    def perform_destroy(self, instance):
        instance.status = Club.Status.ARCHIVED
        instance.save(update_fields=["status", "updated_at"])


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Filiallarni olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Filial yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Filial ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Filialni to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Filialni qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Filialni o‘chirish"),
)
class CabinetBranchViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = BranchManagementSerializer
    pagination_class = StandardPagination
    club_path = "club"
    queryset = Branch.objects.none()

    def get_queryset(self):
        qs = (
            Branch.objects.filter(manageable_club_filter(self.request.user, "club__"))
            .select_related("club", "city", "district")
            .distinct()
        )
        club_id = self.request.query_params.get("club_id")
        if club_id:
            qs = qs.filter(club_id=club_id)
        status_param = self.request.query_params.get("status")
        if status_param and status_param in Branch.Status.values:
            qs = qs.filter(status=status_param)
        query = self.request.query_params.get("query", "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(address__icontains=query)
                | Q(phone__icontains=query)
            )
        return qs.order_by("-created_at")


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Zonalarni olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Zona yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Zona ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Zonani to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Zonani qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Zonani o‘chirish"),
)
class CabinetZoneViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = ZoneSerializer
    pagination_class = StandardPagination
    club_path = "branch"
    queryset = Zone.objects.none()

    def get_queryset(self):
        qs = (
            Zone.objects.filter(
                manageable_club_filter(self.request.user, "branch__club__")
            )
            .select_related("branch__club")
            .distinct()
        )
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("name")


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Ish vaqtlarini olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Ish vaqtini yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Ish vaqti ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Ish vaqtini to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Ish vaqtini qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Ish vaqtini o‘chirish"),
)
class CabinetOperatingHourViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = OperatingHourSerializer
    pagination_class = StandardPagination
    club_path = "branch"
    queryset = OperatingHour.objects.none()

    def get_queryset(self):
        return (
            OperatingHour.objects.filter(
                manageable_club_filter(self.request.user, "branch__club__")
            )
            .select_related("branch__club")
            .distinct()
        )


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Maxsus jadvallarni olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Maxsus jadval yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Maxsus jadval ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Maxsus jadvalni to‘liq yangilash"),
    partial_update=extend_schema(
        tags=["Club Cabinet"],
        summary="Maxsus jadvalni qisman yangilash",
    ),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Maxsus jadvalni o‘chirish"),
)
class CabinetSpecialScheduleViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = SpecialScheduleSerializer
    pagination_class = StandardPagination
    club_path = "branch"
    queryset = SpecialSchedule.objects.none()

    def get_queryset(self):
        return (
            SpecialSchedule.objects.filter(
                manageable_club_filter(self.request.user, "branch__club__")
            )
            .select_related("branch__club")
            .distinct()
        )


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Filial rasmlarini olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Filial rasmini qo‘shish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Filial rasmi ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Filial rasmini to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Filial rasmini qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Filial rasmini o‘chirish"),
)
class CabinetBranchImageViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = BranchImageSerializer
    pagination_class = StandardPagination
    club_path = "branch"
    queryset = BranchImage.objects.none()

    def get_queryset(self):
        return (BranchImage.objects.filter(manageable_club_filter(self.request.user, "branch__club__"))
            .select_related("branch__club")
            .distinct()
        )


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Zona bloklarini olish"),
    create=extend_schema(tags=["Club Cabinet"], summary="Zona blokini yaratish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Zona bloki ma’lumotini olish"),
    update=extend_schema(tags=["Club Cabinet"], summary="Zona blokini to‘liq yangilash"),
    partial_update=extend_schema(tags=["Club Cabinet"], summary="Zona blokini qisman yangilash"),
    destroy=extend_schema(tags=["Club Cabinet"], summary="Zona blokini o‘chirish"),
)
class CabinetResourceBlockViewSet(CabinetAccessMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsClubOperator]
    serializer_class = ResourceBlockSerializer
    pagination_class = StandardPagination
    club_path = "zone"
    queryset = ResourceBlock.objects.none()

    def get_queryset(self):
        return (
            ResourceBlock.objects.filter(
                manageable_club_filter(self.request.user, "zone__branch__club__")
            )
            .select_related("zone__branch__club")
            .distinct()
        )
