from rest_framework.routers import DefaultRouter

from students.viewsets import StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")

urlpatterns = router.urls
