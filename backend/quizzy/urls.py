from django.urls import path

from quizzy.views import QuizzyChatView

urlpatterns = [
    path("quizzy/chat/", QuizzyChatView.as_view(), name="quizzy-chat"),
]
