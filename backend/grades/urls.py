from django.urls import path

from grades.views import ActivitiesView, ScoresBulkView, ScoresMatrixView

urlpatterns = [
    path("activities/", ActivitiesView.as_view(), name="grades-activities"),
    path("scores/matrix/", ScoresMatrixView.as_view(), name="grades-scores-matrix"),
    path("scores/bulk/", ScoresBulkView.as_view(), name="grades-scores-bulk"),
]
