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


class CatalogFieldSerializer(serializers.Serializer):
    """A curriculum formative field (`campo formativo`)."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class CatalogMethodologySerializer(serializers.Serializer):
    """The official Phase 6 planning methodology."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class CatalogSubjectSerializer(serializers.Serializer):
    """A subject belonging to a formative field."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    field_id = serializers.CharField(read_only=True)


class CatalogThemeSerializer(serializers.Serializer):
    """A cross-cutting theme (`eje articulador`)."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class CatalogPdaSerializer(serializers.Serializer):
    """A verified learning process (`PDA`) of an official content."""

    id = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)


class CatalogContentSerializer(serializers.Serializer):
    """An official content with its verified learning processes."""

    id = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)
    pdas = CatalogPdaSerializer(many=True, read_only=True)


class CatalogGroupSerializer(serializers.Serializer):
    """The automatic group context shown by the planning form."""

    id = serializers.IntegerField(read_only=True)
    label = serializers.CharField(read_only=True)
    grade = serializers.IntegerField(read_only=True)
    school_name = serializers.CharField(read_only=True)
    school_cct = serializers.CharField(read_only=True, allow_blank=True)
    school_year_label = serializers.CharField(read_only=True)


class CatalogTeacherSerializer(serializers.Serializer):
    """The requesting teacher's identity."""

    email = serializers.EmailField(read_only=True)


class LessonPlanCatalogSerializer(serializers.Serializer):
    """Full payload of `GET /api/lesson-plans/catalog/`."""

    phase = serializers.IntegerField(read_only=True)
    grade = serializers.IntegerField(read_only=True)
    field = CatalogFieldSerializer(read_only=True)
    methodology = CatalogMethodologySerializer(read_only=True)
    subjects = CatalogSubjectSerializer(many=True, read_only=True)
    cross_cutting_themes = CatalogThemeSerializer(many=True, read_only=True)
    contents = CatalogContentSerializer(many=True, read_only=True)
    group = CatalogGroupSerializer(read_only=True)
    teacher = CatalogTeacherSerializer(read_only=True)
