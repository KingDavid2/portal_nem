from django.urls import path

from quizzy.views import (
    ConversationDetailView,
    ConversationListView,
    QuizzyChatView,
)

urlpatterns = [
    path("quizzy/chat/", QuizzyChatView.as_view(), name="quizzy-chat"),
    path(
        "quizzy/conversations/",
        ConversationListView.as_view(),
        name="quizzy-conversation-list",
    ),
    path(
        "quizzy/conversations/<uuid:conversation_id>/",
        ConversationDetailView.as_view(),
        name="quizzy-conversation-detail",
    ),
]
