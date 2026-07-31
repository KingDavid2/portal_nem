import uuid

from django.conf import settings
from django.db import models

from workspaces.models import ScopedModel


class Conversation(ScopedModel):
    """A Quizzy chat thread owned by one user inside a workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzy_conversations",
    )
    title = models.CharField(max_length=80, blank=True, default="")
    agent_id = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quizzy_conversation"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title or str(self.id)


class Message(models.Model):
    """One turn in a Quizzy conversation."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quizzy_message"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.role}:{self.id}"
