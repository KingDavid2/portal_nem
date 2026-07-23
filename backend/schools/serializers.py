from rest_framework import serializers

from schools.models import Group, School, SchoolYear


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "cct", "level", "workspace"]
        read_only_fields = ["workspace"]


class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ["id", "school", "label", "workspace"]
        read_only_fields = ["workspace"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "school_year", "grado", "grupo", "workspace"]
        read_only_fields = ["workspace"]
