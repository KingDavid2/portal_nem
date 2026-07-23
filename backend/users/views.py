"""Auth views (identity-auth spec): CSRF bootstrap plus session login/
logout/me.
"""

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from users.serializers import LoginSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfBootstrapView(APIView):
    """Anonymous GET that sets the `csrftoken` cookie (design "dedicated
    GET /api/auth/csrf/"). Must stay reachable pre-login: `/me/` is
    IsAuthenticated and cannot bootstrap CSRF for the login call itself.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: OpenApiResponse(description="CSRF cookie set")})
    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


class LoginView(APIView):
    """Session login (identity-auth spec — "Session Login/Logout/Me
    Endpoints"). No JWT: this establishes the standard Django session
    cookie via `django.contrib.auth.login`.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        django_login(request, serializer.validated_data["user"])
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    """Clears the current session server-side."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Session cleared")})
    def post(self, request):
        django_logout(request)
        return Response(status=HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Returns the current authenticated user's identity."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)
