from rest_framework import serializers

from webapp.apps.users.models import Project


class PublishSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField(required=False)
    user_count = serializers.IntegerField(required=False)
    # see to_representation
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        if not obj.has_write_access(user):
            rep.pop("sim_count")
            rep.pop("user_count")
        return rep

    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "repo_url",
            "server_size",
            "exp_task_time",
            "server_cost",
            "listed",
            "owner",
            "cluster_type",
            "sim_count",
            "status",
            "user_count",
        )
        read_only = ("sim_count", "user_count", "status")


class ProjectWithVersionSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField(required=False)
    version = serializers.CharField(required=False)
    user_count = serializers.IntegerField(required=False)
    # see to_representation
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        if not obj.has_write_access(user):
            rep.pop("sim_count")
            rep.pop("user_count")
        return rep

    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "repo_url",
            "server_size",
            "exp_task_time",
            "server_cost",
            "listed",
            "owner",
            "cluster_type",
            "sim_count",
            "status",
            "user_count",
            "version",
        )
        read_only = ("sim_count", "status", "user_count", "version")
