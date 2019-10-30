from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from courses.api.serializers import CourseSerializer, AssignmentSerializer
from learning.models import CourseNewsNotification, StudentAssignment, \
    Enrollment
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class StudentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source="first_name")
    surname = serializers.CharField(source="last_name")
    branch = serializers.CharField(source="branch.code")
    sex = serializers.CharField(source="gender")

    class Meta:
        model = User
        fields = ('id', 'name', 'surname', 'patronymic', 'sex', 'branch')


class EnrollmentStudentSerializer(StudentSerializer):
    class Meta(StudentSerializer.Meta):
        fields = ('id', 'name', 'surname', 'patronymic', 'branch')


class EnrollmentSerializer(serializers.ModelSerializer):
    student = EnrollmentStudentSerializer()

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
