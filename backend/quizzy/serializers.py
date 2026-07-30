from rest_framework import serializers


class QuizzyChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, max_length=8000)
    agent_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )

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


class QuizzyChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    agent_id = serializers.CharField()
    model = serializers.CharField()
