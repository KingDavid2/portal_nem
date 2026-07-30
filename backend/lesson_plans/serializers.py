from rest_framework import serializers

from lesson_plans.core.catalog import (
    content_by_id,
    methodology_by_id,
    pda_by_id,
    subject_by_id,
    theme_by_id,
)
from lesson_plans.models import LessonPlan
from lesson_plans.validation import (
    DUPLICATE_CONTENT_SELECTIONS_ERROR,
    DUPLICATE_PDAS_ERROR,
    DUPLICATE_THEMES_ERROR,
    EMPTY_CONTENT_SELECTIONS_ERROR,
    EMPTY_THEMES_ERROR,
    END_DATE_BEFORE_START_DATE_ERROR,
    FOREIGN_PDA_ERROR,
    UNSUPPORTED_CONTENT_ERROR,
    UNSUPPORTED_METHODOLOGY_ERROR,
    UNSUPPORTED_SUBJECT_ERROR,
    UNSUPPORTED_THEME_ERROR,
    require_secondary_group,
    resolve_field,
)
from schools.models import Group


class ContentSelectionSerializer(serializers.Serializer):
    """One official content plus the PDAs chosen under it."""

    content_id = serializers.CharField()
    pda_ids = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class ContentPdaTextSerializer(serializers.Serializer):
    """One official content from the grounding snapshot plus its PDAs."""

    content = serializers.CharField()
    pdas = serializers.ListField(child=serializers.CharField())


class LessonPlanSerializer(serializers.ModelSerializer):
    # Declared rather than left to `JSONField` inference: the model stores both
    # as bare JSON, which the schema would emit untyped, and the client needs
    # them typed to rebuild a create body from a plan the API returned.
    cross_cutting_theme_ids = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    content_selections = ContentSelectionSerializer(many=True, read_only=True)

    invented_pda_texts = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    grounding_selections = ContentPdaTextSerializer(many=True, read_only=True)

    class Meta:
        model = LessonPlan
        fields = [
            "id",
            "workspace",
            "group",
            "campo",
            "grade",
            "theme",
            "field_id",
            "subject_id",
            "methodology_id",
            "duration_weeks",
            "start_date",
            "end_date",
            "scenario",
            "context_diagnosis",
            "cross_cutting_theme_ids",
            "content_selections",
            "title",
            "proyecto",
            "status",
            "failure_reason",
            "provider",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "invented_pdas",
            "invented_pda_texts",
            "grounding_selections",
            "generated_at",
            "created_at",
        ]
        read_only_fields = [
            "workspace",
            "field_id",
            "subject_id",
            "methodology_id",
            "duration_weeks",
            "start_date",
            "end_date",
            "scenario",
            "context_diagnosis",
            "cross_cutting_theme_ids",
            "content_selections",
            "title",
            "proyecto",
            "status",
            "failure_reason",
            "provider",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "invented_pdas",
            "invented_pda_texts",
            "grounding_selections",
            "generated_at",
            "created_at",
        ]


class LessonPlanCreateSerializer(serializers.Serializer):
    """Write contract of `POST /api/lesson-plans/`.

    Every curriculum value arrives as an official catalog id — free text is
    only accepted for the teacher's own prose (`theme`, `context_diagnosis`).
    `campo` and `grade` are deliberately absent: the server derives them from
    the resolved field and the group, so a client that sends them is ignored.

    All catalog rules live in `validate()` rather than in per-field
    `validate_<name>` hooks because every one of them is answerable only once
    `field_id` is known, and DRF does not order field-level hooks.
    """

    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects)
    field_id = serializers.CharField()
    subject_id = serializers.CharField(required=False, allow_blank=True, default="")
    methodology_id = serializers.CharField()
    theme = serializers.CharField()
    context_diagnosis = serializers.CharField()
    scenario = serializers.ChoiceField(choices=LessonPlan.Scenario.choices)
    duration_weeks = serializers.IntegerField(min_value=1, max_value=12)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    cross_cutting_theme_ids = serializers.ListField(child=serializers.CharField())
    content_selections = ContentSelectionSerializer(many=True)

    def validate(self, attrs):
        require_secondary_group(attrs["group"], error_key="group")
        field = resolve_field(attrs["field_id"], error_key="field_id")
        attrs["field_id"] = field.id
        attrs["subject_id"] = self._validate_subject(field.id, attrs["subject_id"])
        attrs["methodology_id"] = self._validate_methodology(attrs["methodology_id"])
        attrs["cross_cutting_theme_ids"] = self._validate_themes(
            attrs["cross_cutting_theme_ids"]
        )
        attrs["content_selections"] = self._validate_content_selections(
            field.id, attrs["content_selections"]
        )
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": END_DATE_BEFORE_START_DATE_ERROR}
            )
        return attrs

    def _validate_subject(self, field_id: str, subject_id: str) -> str:
        if not subject_id:
            return ""
        try:
            return subject_by_id(field_id, subject_id).id
        except KeyError:
            raise serializers.ValidationError({"subject_id": UNSUPPORTED_SUBJECT_ERROR})

    def _validate_methodology(self, methodology_id: str) -> str:
        try:
            return methodology_by_id(methodology_id).id
        except KeyError:
            raise serializers.ValidationError(
                {"methodology_id": UNSUPPORTED_METHODOLOGY_ERROR}
            )

    def _validate_themes(self, theme_ids: list[str]) -> list[str]:
        if not theme_ids:
            raise serializers.ValidationError(
                {"cross_cutting_theme_ids": EMPTY_THEMES_ERROR}
            )
        resolved = []
        for theme_id in theme_ids:
            try:
                resolved.append(theme_by_id(theme_id).id)
            except KeyError:
                raise serializers.ValidationError(
                    {"cross_cutting_theme_ids": UNSUPPORTED_THEME_ERROR}
                )
        if len(set(resolved)) != len(resolved):
            raise serializers.ValidationError(
                {"cross_cutting_theme_ids": DUPLICATE_THEMES_ERROR}
            )
        return resolved

    def _validate_content_selections(
        self, field_id: str, selections: list[dict]
    ) -> list[dict]:
        if not selections:
            raise serializers.ValidationError(
                {"content_selections": EMPTY_CONTENT_SELECTIONS_ERROR}
            )
        # Errors are collected per index (rather than raised on the first bad
        # row) so the response mirrors the submitted list and the form can put
        # each message back on the row that produced it.
        errors: list[dict] = [{} for _ in selections]
        resolved: list[dict] = []
        for index, selection in enumerate(selections):
            try:
                content = content_by_id(field_id, selection["content_id"])
            except KeyError:
                errors[index]["content_id"] = [UNSUPPORTED_CONTENT_ERROR]
                continue
            pda_ids = self._resolve_pda_ids(
                field_id, content.id, selection["pda_ids"], errors[index]
            )
            if pda_ids is None:
                continue
            resolved.append({"content_id": content.id, "pda_ids": pda_ids})
        if any(errors):
            raise serializers.ValidationError({"content_selections": errors})
        content_ids = [selection["content_id"] for selection in resolved]
        if len(set(content_ids)) != len(content_ids):
            raise serializers.ValidationError(
                {"content_selections": DUPLICATE_CONTENT_SELECTIONS_ERROR}
            )
        return resolved

    def _resolve_pda_ids(
        self, field_id: str, content_id: str, pda_ids: list[str], row_errors: dict
    ) -> list[str] | None:
        resolved = []
        for pda_id in pda_ids:
            try:
                pda = pda_by_id(field_id, pda_id)
            except KeyError:
                row_errors["pda_ids"] = [FOREIGN_PDA_ERROR]
                return None
            # A PDA can resolve inside the field yet hang off another content;
            # that is the same client mistake as an unknown id.
            if pda.content_id != content_id:
                row_errors["pda_ids"] = [FOREIGN_PDA_ERROR]
                return None
            resolved.append(pda.id)
        if len(set(resolved)) != len(resolved):
            row_errors["pda_ids"] = [DUPLICATE_PDAS_ERROR]
            return None
        return resolved


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


def catalog_group_payload(group) -> dict:
    """Group identity dict shared by the catalog action and `list_groups`.

    Extracted from the inline dict formerly at `viewsets.catalog` so the HTTP
    catalog surface and the MCP tool cannot drift (design D2 — same anti-drift
    move as `quota.format_period`).
    """
    school = group.school_year.school
    return {
        "id": group.pk,
        "label": f"{group.grado}° {group.grupo}",
        "grade": group.grado,
        "school_name": school.name,
        "school_cct": school.cct,
        "school_year_label": group.school_year.label,
    }


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


class GenerationQuotaSerializer(serializers.Serializer):
    """Full payload of `GET /api/lesson-plans/quota/` (the "Generaciones de
    este mes" card).

    `remaining` is served rather than left to the client: it is floored at
    zero, and a lowered `LESSON_PLAN_MONTHLY_GENERATION_LIMIT` can leave a
    workspace above its own allowance, where `limit - used` would render as
    a negative countdown.
    """

    period = serializers.CharField(read_only=True)
    used = serializers.IntegerField(read_only=True)
    limit = serializers.IntegerField(read_only=True)
    remaining = serializers.IntegerField(read_only=True)


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
