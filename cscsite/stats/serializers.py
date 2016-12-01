from django.contrib.auth.models import Group
from rest_framework import serializers

from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("name",)


class ParticipantsStatsSerializer(serializers.Serializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    curriculum_year = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
