from django.contrib.auth.models import Group
from rest_framework import serializers

from learning.models import StudentAssignment
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


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CSCUser
        fields = ("curriculum_year", "gender")


class StudentAssignmentsSerializer(serializers.ModelSerializer):
    sent = serializers.SerializerMethodField()
    first_submission_at = serializers.DateTimeField()
    grade = serializers.IntegerField()
    student = StudentSerializer(read_only=True)

    class Meta:
        model = StudentAssignment
        fields = ("id", "sent", "first_submission_at", "grade", "student", "state")

    def get_sent(self, obj):
        """
        Let's say user passed assignment if he sent comment or has grade
        """
        return int(obj.grade is not None or
                obj.is_passed != StudentAssignment.LAST_COMMENT_NOBODY)


class AssignmentsStatsSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    title = serializers.CharField(read_only=True)
    deadline_at = serializers.DateTimeField(label="deadline", read_only=True)
    grade_min = serializers.IntegerField(read_only=True)
    grade_max = serializers.IntegerField(read_only=True)
    assigned_to = StudentAssignmentsSerializer(many=True, read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class EnrollmentsStatsSerializer(serializers.Serializer):
    grade = serializers.CharField(read_only=True)
    student = StudentSerializer(read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass