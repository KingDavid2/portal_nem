import importlib.metadata

from django.db.transaction import non_atomic_requests
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config import demo_mode

try:
    APP_VERSION = importlib.metadata.version("portal-nem-backend")
except importlib.metadata.PackageNotFoundError:
    APP_VERSION = "0.0.0"


@method_decorator(non_atomic_requests, name="dispatch")
class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {"status": "ok", "version": APP_VERSION, "demo_mode": demo_mode.enabled()}
        )
