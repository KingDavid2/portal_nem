from rest_framework import serializers

from quizzy.models import Conversation, Message
from schools.models import Group


class QuizzyChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, max_length=8000)
    agent_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    group_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_message(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("message must not be empty.")
        return cleaned

    def validate_agent_id(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def validate_group_id(self, value: int | None) -> int | None:
        if value is None:
            return None
        # ScopedManager limits to the active workspace on data requests.
        if not Group.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "group_id must belong to the active workspace."
            )
        return value


class QuizzyChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    agent_id = serializers.CharField()
    model = serializers.CharField()
    conversation_id = serializers.UUIDField()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "created_at")
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "title", "agent_id", "created_at", "updated_at")
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "agent_id", "created_at", "updated_at", "messages")
        read_only_fields = fields


class ConversationRenameSerializer(serializers.Serializer):
    title = serializers.CharField(allow_blank=False, max_length=80)

    def validate_title(self, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise serializers.ValidationError("title must not be empty.")
        return cleaned
