from rest_framework.routers import DefaultRouter

from lesson_plans.viewsets import LessonPlanViewSet

router = DefaultRouter()
router.register("lesson-plans", LessonPlanViewSet, basename="lessonplan")

urlpatterns = router.urls
