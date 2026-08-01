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
