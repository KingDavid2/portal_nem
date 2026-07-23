from rest_framework.routers import DefaultRouter

from schools.viewsets import GroupViewSet, SchoolViewSet, SchoolYearViewSet

router = DefaultRouter()
router.register("schools", SchoolViewSet, basename="school")
router.register("school-years", SchoolYearViewSet, basename="schoolyear")
router.register("groups", GroupViewSet, basename="group")

urlpatterns = router.urls
