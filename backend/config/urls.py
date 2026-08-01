"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config import demo_mode

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/", include("core.urls")),
    path("api/", include("lesson_plans.urls")),
    path("api/", include("schools.urls")),
    path("api/", include("students.urls")),
    path("api/", include("users.urls")),
    path("api/", include("workspaces.urls")),
    path("api/", include("quizzy.urls")),
    path("api/", include("attendance.urls")),
]

# The demo endpoints provision real users with a shared password and require no
# authentication. They are registered only when demo mode is on, so with the
# toggle off they 404 because the routes do not exist — not because a check
# rejected the caller.
if demo_mode.enabled():
    urlpatterns += [path("api/demo/", include("demo.urls"))]

# Streamable-HTTP MCP arm — same absence-means-404 discipline as demo mode.
# Off by default (settings.MCP_HTTP_ENABLED); when off the path is not
# registered at all.
if settings.MCP_HTTP_ENABLED:
    from mcp_server.http import MCP_HTTP_PATH, mcp_http_view

    urlpatterns += [path(MCP_HTTP_PATH, mcp_http_view)]
