from django.urls import path

from users.views import CsrfBootstrapView, LoginView, LogoutView, MeView

urlpatterns = [
    path("auth/csrf/", CsrfBootstrapView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
