from rest_framework.routers import DefaultRouter

from apps.clubs.views import (
    CabinetBranchImageViewSet,
    CabinetBranchViewSet,
    CabinetClubViewSet,
    CabinetOperatingHourViewSet,
    CabinetResourceBlockViewSet,
    CabinetSpecialScheduleViewSet,
    CabinetZoneViewSet,
    CityViewSet,
    DistrictViewSet,
    FavoriteViewSet,
    PublicBranchViewSet,
    PublicClubViewSet,
)


router = DefaultRouter()
router.register("clubs", PublicClubViewSet, basename="clubs")
router.register("branches", PublicBranchViewSet, basename="branches")
router.register("locations/cities", CityViewSet, basename="cities")
router.register("locations/districts", DistrictViewSet, basename="districts")
router.register("favorites", FavoriteViewSet, basename="favorites")
router.register("cabinet/clubs", CabinetClubViewSet, basename="cabinet-clubs")
router.register("cabinet/branches", CabinetBranchViewSet, basename="cabinet-branches")
router.register("cabinet/zones", CabinetZoneViewSet, basename="cabinet-zones")
router.register(
    "cabinet/operating-hours",
    CabinetOperatingHourViewSet,
    basename="cabinet-operating-hours",
)
router.register(
    "cabinet/special-schedules",
    CabinetSpecialScheduleViewSet,
    basename="cabinet-special-schedules",
)
router.register(
    "cabinet/branch-images",
    CabinetBranchImageViewSet,
    basename="cabinet-branch-images",
)
router.register(
    "cabinet/resource-blocks",
    CabinetResourceBlockViewSet,
    basename="cabinet-resource-blocks",
)

urlpatterns = router.urls
