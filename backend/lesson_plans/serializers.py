from rest_framework import serializers

from lesson_plans.models import LessonPlan


class LessonPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPlan
        fields = [
            "id",
            "workspace",
            "group",
            "campo",
            "grade",
            "theme",
            "title",
            "proyecto",
            "status",
            "failure_reason",
            "provider",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "invented_pdas",
            "generated_at",
            "created_at",
        ]
        read_only_fields = [
            "workspace",
            "title",
            "proyecto",
            "status",
            "failure_reason",
            "provider",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "invented_pdas",
            "generated_at",
            "created_at",
        ]
