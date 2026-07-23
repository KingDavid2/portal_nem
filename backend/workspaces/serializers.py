from rest_framework import serializers

from workspaces.models import Membership


class MembershipListSerializer(serializers.ModelSerializer):
    """One row per caller membership (workspaces spec — "Workspace-List
    Endpoint Returns Only the Caller's Memberships").
    """

    id = serializers.UUIDField(source="workspace_id")
    name = serializers.CharField(source="workspace.name")
    type = serializers.CharField(source="workspace.type")

    class Meta:
        model = Membership
        fields = ["id", "name", "type", "role"]
