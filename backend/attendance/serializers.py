"""Serializers for attendance roster read and bulk upsert endpoints."""

from __future__ import annotations

from rest_framework import serializers

from attendance.models import AttendanceRecord


class AttendanceRosterQuerySerializer(serializers.Serializer):
    group = serializers.IntegerField()
    date = serializers.DateField()


class AttendanceRosterEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField(source="student.id")
    first_name = serializers.CharField(source="student.first_name")
    last_name_paternal = serializers.CharField(source="student.last_name_paternal")
    curp = serializers.CharField(source="student.curp")
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    notes = serializers.CharField()


class AttendanceBulkEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class AttendanceBulkRequestSerializer(serializers.Serializer):
    group = serializers.IntegerField()
    date = serializers.DateField()
    entries = AttendanceBulkEntrySerializer(many=True)

    def validate_entries(self, value):
        if not value:
            raise serializers.ValidationError("At least one entry is required.")
        return value


class AttendanceBulkResponseSerializer(serializers.Serializer):
    saved = serializers.IntegerField()


class AttendanceWeekQuerySerializer(serializers.Serializer):
    group = serializers.IntegerField()
    week_start = serializers.DateField()

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("week_start must be a Monday.")
        return value


class AttendanceWeekStudentSerializer(serializers.Serializer):
    student = serializers.IntegerField(source="student.id")
    first_name = serializers.CharField(source="student.first_name")
    last_name_paternal = serializers.CharField(source="student.last_name_paternal")
    days = serializers.DictField(
        child=serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    )


class AttendanceWeekResponseSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    dates = serializers.ListField(child=serializers.DateField())
    students = AttendanceWeekStudentSerializer(many=True)


class AttendanceWeekBulkEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField()
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)


class AttendanceWeekBulkRequestSerializer(serializers.Serializer):
    group = serializers.IntegerField()
    week_start = serializers.DateField()
    entries = AttendanceWeekBulkEntrySerializer(many=True)

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("week_start must be a Monday.")
        return value

    def validate_entries(self, value):
        if not value:
            raise serializers.ValidationError("At least one entry is required.")
        return value
