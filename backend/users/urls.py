from django.urls import path

from users.views import CsrfBootstrapView

urlpatterns = [
    path("auth/csrf/", CsrfBootstrapView.as_view(), name="auth-csrf"),
]
