"""Serializers for the demo endpoints.

The persona serializer is deliberately explicit rather than derived from the
dataclass: `Persona.provisioner` is a dotted import path and must never reach
an unauthenticated client.
"""

from __future__ import annotations

from rest_framework import serializers

from demo import personas
from demo.models import DemoSession


class PersonaSerializer(serializers.Serializer):
    """One entry of the frozen persona registry, as shown in the picker."""

    key = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    features = serializers.ListField(child=serializers.CharField(), read_only=True)


class DemoSessionCreateSerializer(serializers.Serializer):
    """Validates the requested persona against the registry.

    Rejecting an unknown key here (400) rather than in the task keeps a
    guaranteed-to-fail session from ever being written.
    """

    persona = serializers.ChoiceField(choices=personas.keys())


class DemoSessionSerializer(serializers.ModelSerializer):
    """The provisioning receipt as the polling client sees it.

    `workspace` and `email` are null until the session is `ready`;
    `error_message` is empty unless it `failed`.
    """

    email = serializers.SerializerMethodField()

    class Meta:
        model = DemoSession
        fields = ["id", "persona", "status", "workspace", "email", "error_message"]
        read_only_fields = fields

    def get_email(self, obj: DemoSession) -> str | None:
        return obj.user.email if obj.user_id else None
