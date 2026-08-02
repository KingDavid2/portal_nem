"""Serializers for grades activities list/create, matrix, and bulk upsert."""

from __future__ import annotations

from rest_framework import serializers

from grades.models import Activity


class TermSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()


class ActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    group = serializers.IntegerField(source="group_id")
    term = serializers.IntegerField(source="term_id")
    title = serializers.CharField()
    type = serializers.CharField(source="activity_type")
    due_date = serializers.DateField()
    field = serializers.CharField(source="formative_field_id")
    subject_ids = serializers.ListField(child=serializers.CharField())
    description = serializers.CharField()


class ActivitiesStatsSerializer(serializers.Serializer):
    total_activities = serializers.IntegerField()
    graded_activities = serializers.IntegerField()
    pending_activities = serializers.IntegerField()
    average_score = serializers.DecimalField(
        max_digits=4, decimal_places=1, allow_null=True
    )


class ActivitiesListQuerySerializer(serializers.Serializer):
    group = serializers.IntegerField()
    term = serializers.IntegerField()
    field = serializers.CharField(required=False)
    subject = serializers.CharField(required=False)
    type = serializers.ChoiceField(
        choices=Activity.ActivityType.choices, required=False
    )
    q = serializers.CharField(required=False)


class ActivitiesListResponseSerializer(serializers.Serializer):
    terms = TermSerializer(many=True)
    activities = ActivitySerializer(many=True)
    stats = ActivitiesStatsSerializer()


class ActivityCreateSerializer(serializers.Serializer):
    group = serializers.IntegerField()
    term = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=Activity.ActivityType.choices)
    due_date = serializers.DateField()
    field = serializers.CharField(max_length=64)
    subject_ids = serializers.ListField(
        child=serializers.CharField(max_length=64), allow_empty=False
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")


class StudentBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name_paternal = serializers.CharField()


class ScoreCellSerializer(serializers.Serializer):
    student = serializers.IntegerField(source="student_id")
    activity = serializers.IntegerField(source="activity_id")
    score = serializers.DecimalField(
        max_digits=3, decimal_places=1, allow_null=True
    )


class ScoresMatrixQuerySerializer(serializers.Serializer):
    group = serializers.IntegerField()
    term = serializers.IntegerField()
    field = serializers.CharField(required=False)
    subject = serializers.CharField(required=False)
    type = serializers.ChoiceField(
        choices=Activity.ActivityType.choices, required=False
    )


class ScoresMatrixResponseSerializer(serializers.Serializer):
    terms = TermSerializer(many=True)
    students = StudentBriefSerializer(many=True)
    activities = ActivitySerializer(many=True)
    scores = ScoreCellSerializer(many=True)


class ScoresBulkEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField()
    activity = serializers.IntegerField()
    score = serializers.DecimalField(
        max_digits=3, decimal_places=1, required=False, allow_null=True
    )


class ScoresBulkRequestSerializer(serializers.Serializer):
    group = serializers.IntegerField()
    entries = ScoresBulkEntrySerializer(many=True)

    def validate_entries(self, value):
        if not value:
            raise serializers.ValidationError("At least one entry is required.")
        return value


class ScoresBulkResponseSerializer(serializers.Serializer):
    saved = serializers.IntegerField()
