"""DEBUG/local Quizzy chat endpoint backed by Cursor Composer.

Mounted always (auth + CURSOR_API_KEY required). Intended for local smoke
testing only — Composer is a full agent that can touch the working tree.
"""

from __future__ import annotations

from django.conf import settings
from django.db.transaction import non_atomic_requests
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_503_SERVICE_UNAVAILABLE,
)
from rest_framework.views import APIView

from quizzy.agent import QuizzyAgentError, run_chat
from quizzy.serializers import QuizzyChatRequestSerializer, QuizzyChatResponseSerializer


@method_decorator(non_atomic_requests, name="dispatch")
class QuizzyChatView(APIView):
    """POST /api/quizzy/chat/ — local Composer turn (registered only when DEBUG)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=QuizzyChatRequestSerializer,
        responses={200: QuizzyChatResponseSerializer},
    )
    def post(self, request):
        serializer = QuizzyChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]

        api_key = settings.CURSOR_API_KEY
        if not api_key:
            return Response(
                {
                    "detail": (
                        "CURSOR_API_KEY is not set. Add it to .env "
                        "(Cursor Dashboard → Integrations)."
                    )
                },
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            reply = run_chat(
                message=message,
                agent_id=serializer.validated_data.get("agent_id"),
                api_key=api_key,
            )
        except QuizzyAgentError as exc:
            return Response(
                {"detail": exc.message, "retryable": exc.retryable},
                status=exc.status,
            )

        return Response(
            QuizzyChatResponseSerializer(
                {
                    "reply": reply.reply,
                    "agent_id": reply.agent_id,
                    "model": reply.model,
                }
            ).data
        )
