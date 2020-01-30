from rest_framework import serializers

from learning.models import StudentAssignment
from users.models import User, Group


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("name",)


class ParticipantsStatsSerializer(serializers.Serializer):
    # FIXME: groups -> roles
    groups = serializers.SlugRelatedField(many=True, read_only=True,
                                          slug_field='role')
    curriculum_year = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class StudentSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(many=True, read_only=True,
                                          slug_field='role')

    class Meta:
        model = User
        fields = ("curriculum_year", "gender", "groups")


class StudentAssignmentsSerializer(serializers.ModelSerializer):
    sent = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    first_student_comment_at = serializers.DateTimeField()
    score = serializers.IntegerField()
    student = StudentSerializer(read_only=True)

    class Meta:
        model = StudentAssignment
        fields = ("id", "sent", "first_student_comment_at", "score", "student",
                  "state")

    def get_state(self, obj):
        return obj.state.value

    def get_sent(self, obj):
        """
        Let's say user passed assignment if he sent comment or has score
        """
        # FIXME: rewrite with `submission_is_received`? Check what about
        #  offline assignments here.
        return int(obj.score is not None or
                   obj.submission_is_received != StudentAssignment.CommentAuthorTypes.NOBODY)


class AssignmentsStatsSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    is_online = serializers.ReadOnlyField()
    title = serializers.CharField(read_only=True)
    deadline_at = serializers.DateTimeField(label="deadline", read_only=True)
    passing_score = serializers.IntegerField(read_only=True)
    maximum_score = serializers.IntegerField(read_only=True)
    students = StudentAssignmentsSerializer(many=True, read_only=True)

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