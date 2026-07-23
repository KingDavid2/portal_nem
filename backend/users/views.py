"""Auth views (identity-auth spec): CSRF bootstrap plus session login/
logout/me.
"""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfBootstrapView(APIView):
    """Anonymous GET that sets the `csrftoken` cookie (design "dedicated
    GET /api/auth/csrf/"). Must stay reachable pre-login: `/me/` is
    IsAuthenticated and cannot bootstrap CSRF for the login call itself.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})
