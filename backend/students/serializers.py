from rest_framework import serializers

from students.models import Student


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "group",
            "first_name",
            "last_name_paternal",
            "last_name_maternal",
            "curp",
            "workspace",
        ]
        read_only_fields = ["workspace"]
