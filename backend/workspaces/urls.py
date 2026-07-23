from django.urls import path

from workspaces.views import WorkspaceListView

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
]
