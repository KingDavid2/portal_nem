"""Demo routes, included by `config/urls.py` only when demo mode is enabled."""

from django.urls import path

from demo.views import (
    DemoPersonaListView,
    DemoSessionCreateView,
    DemoSessionDetailView,
)

urlpatterns = [
    path("personas/", DemoPersonaListView.as_view(), name="demo-personas"),
    path("sessions/", DemoSessionCreateView.as_view(), name="demo-session-create"),
    path("sessions/<uuid:pk>/", DemoSessionDetailView.as_view(), name="demo-session-detail"),
]
