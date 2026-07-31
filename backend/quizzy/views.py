"""Quizzy chat + conversation history endpoints."""

from __future__ import annotations

from django.conf import settings
from django.db.transaction import non_atomic_requests
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_503_SERVICE_UNAVAILABLE,
)
from rest_framework.views import APIView

from quizzy.agent import QuizzyAgentError
from quizzy.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    ConversationRenameSerializer,
    QuizzyChatRequestSerializer,
    QuizzyChatResponseSerializer,
)
from quizzy.services import (
    create_conversation_turn,
    delete_conversation,
    get_conversation,
    list_conversations,
    rename_conversation,
)
from workspaces.permissions import WorkspacePermission


@method_decorator(non_atomic_requests, name="dispatch")
class QuizzyChatView(APIView):
    """POST /api/quizzy/chat/ — Composer turn + persist conversation."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"post": "edit_content"}
    action = "post"

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
            conversation, reply = create_conversation_turn(
                membership=request.membership,
                user=request.user,
                message=message,
                api_key=api_key,
                conversation_id=serializer.validated_data.get("conversation_id"),
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
                    "conversation_id": conversation.id,
                }
            ).data
        )


class ConversationListView(APIView):
    """GET /api/quizzy/conversations/ — owner's threads in active workspace."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"get": "view_workspace"}
    action = "get"

    @extend_schema(responses={200: ConversationListSerializer(many=True)})
    def get(self, request):
        qs = list_conversations(membership=request.membership, user=request.user)
        return Response(ConversationListSerializer(qs, many=True).data)


class ConversationDetailView(APIView):
    """GET/PATCH/DELETE /api/quizzy/conversations/<id>/."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {
        "get": "view_workspace",
        "patch": "edit_content",
        "delete": "edit_content",
    }

    def initial(self, request, *args, **kwargs):
        self.action = request.method.lower()
        super().initial(request, *args, **kwargs)

    @extend_schema(responses={200: ConversationDetailSerializer})
    def get(self, request, conversation_id):
        conversation = get_conversation(
            membership=request.membership,
            user=request.user,
            conversation_id=conversation_id,
        )
        return Response(ConversationDetailSerializer(conversation).data)

    @extend_schema(
        request=ConversationRenameSerializer,
        responses={200: ConversationListSerializer},
    )
    def patch(self, request, conversation_id):
        serializer = ConversationRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = rename_conversation(
            membership=request.membership,
            user=request.user,
            conversation_id=conversation_id,
            title=serializer.validated_data["title"],
        )
        return Response(ConversationListSerializer(conversation).data)

    @extend_schema(responses={204: None})
    def delete(self, request, conversation_id):
        delete_conversation(
            membership=request.membership,
            user=request.user,
            conversation_id=conversation_id,
        )
        return Response(status=HTTP_204_NO_CONTENT)
