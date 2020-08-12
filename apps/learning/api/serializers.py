from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from courses.api.serializers import CourseSerializer, AssignmentSerializer
from learning.models import CourseNewsNotification, StudentAssignment, \
    Enrollment
from users.models import User, StudentProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class StudentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user_id")
    name = serializers.CharField(source="user.first_name")
    surname = serializers.CharField(source="user.last_name")
    patronymic = serializers.CharField(source="user.patronymic")
    branch = serializers.CharField(source="branch.code")
    sex = serializers.CharField(source="user.gender")

    class Meta:
        model = StudentProfile
        fields = ('id', 'name', 'surname', 'patronymic', 'sex', 'branch')


class EnrollmentSerializer(serializers.ModelSerializer):
    student = StudentSerializer()

    class Meta:
        model = Enrollment
        fields = ('student', 'grade')


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseNewsNotification
        fields = ('user', 'is_unread', 'is_notified')


class StudentAssignmentSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()

    class Meta:
        model = StudentAssignment
        fields = ('pk', 'score', 'state', 'student_id')

    def validate_score(self, value):
        max_score = self.instance.assignment.maximum_score
        if value and value > max_score:
            msg = _("Score can't be larger than %s") % max_score
            raise serializers.ValidationError(msg)
        return value

    def get_state(self, obj):
        return obj.state.value


class AssignmentScoreSerializer(StudentAssignmentSerializer):
    class Meta(StudentAssignmentSerializer.Meta):
        fields = ('score',)


class MyCourseSerializer(CourseSerializer):
    class Meta(CourseSerializer.Meta):
        fields = ('id', 'name', 'url', 'semester', 'branch')


class MyCourseAssignmentSerializer(AssignmentSerializer):
    class Meta(AssignmentSerializer.Meta):
        fields = ('pk', 'deadline_at', 'title', 'passing_score',
                  'maximum_score', 'weight')
