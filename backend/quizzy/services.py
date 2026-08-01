"""Services for Quizzy conversation persistence."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404

from quizzy.agent import ChatReply, run_chat
from quizzy.models import Conversation, Message
from workspaces.permissions import has_permission

TITLE_MAX = 80


def _require_edit_content(membership) -> None:
    if not has_permission(membership, "edit_content"):
        raise PermissionDenied("Membership lacks edit_content capability.")


def _require_view_workspace(membership) -> None:
    if not has_permission(membership, "view_workspace"):
        raise PermissionDenied("Membership lacks view_workspace capability.")


def _title_from_message(message: str) -> str:
    cleaned = " ".join(message.split())
    if len(cleaned) <= TITLE_MAX:
        return cleaned
    return cleaned[: TITLE_MAX - 1].rstrip() + "…"


def list_conversations(*, membership, user):
    _require_view_workspace(membership)
    return Conversation.objects.filter(created_by=user).order_by("-updated_at")


def get_conversation(*, membership, user, conversation_id) -> Conversation:
    _require_view_workspace(membership)
    return get_object_or_404(
        Conversation.objects.prefetch_related("messages"),
        pk=conversation_id,
        created_by=user,
    )


def delete_conversation(*, membership, user, conversation_id) -> None:
    _require_edit_content(membership)
    conversation = get_object_or_404(
        Conversation,
        pk=conversation_id,
        created_by=user,
    )
    with transaction.atomic():
        conversation.delete()


def rename_conversation(
    *, membership, user, conversation_id, title: str
) -> Conversation:
    _require_edit_content(membership)
    cleaned = " ".join(title.split())
    if not cleaned:
        raise ValueError("title must not be empty.")
    if len(cleaned) > TITLE_MAX:
        cleaned = cleaned[: TITLE_MAX - 1].rstrip() + "…"

    conversation = get_object_or_404(
        Conversation,
        pk=conversation_id,
        created_by=user,
    )
    with transaction.atomic():
        conversation.title = cleaned
        conversation.save(update_fields=["title", "updated_at"])
    return conversation


def create_conversation_turn(
    *,
    membership,
    user,
    message: str,
    api_key: str,
    conversation_id=None,
    selected_group_id: int | None = None,
) -> tuple[Conversation, ChatReply]:
    """Call Composer, then persist the user + assistant turn.

    On agent failure nothing is written (matches ephemeral-chat UX).
    """
    _require_edit_content(membership)

    conversation: Conversation | None = None
    agent_id: str | None = None
    if conversation_id is not None:
        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            created_by=user,
        )
        agent_id = conversation.agent_id or None

    reply = run_chat(
        message=message,
        agent_id=agent_id,
        api_key=api_key,
        membership=membership,
        selected_group_id=selected_group_id,
    )

    with transaction.atomic():
        if conversation is None:
            conversation = Conversation.objects.create(
                workspace=membership.workspace,
                created_by=user,
                title=_title_from_message(message),
                agent_id=reply.agent_id,
            )
        else:
            conversation.agent_id = reply.agent_id
            if not conversation.title:
                conversation.title = _title_from_message(message)
            conversation.save(update_fields=["agent_id", "title", "updated_at"])

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message,
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=reply.reply,
        )

    return conversation, reply
