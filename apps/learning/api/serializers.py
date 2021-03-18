from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from api.utils import DynamicFieldsModelSerializer
from core.api.serializers import BranchSerializer
from courses.api.serializers import CourseSerializer, AssignmentSerializer
from learning.models import CourseNewsNotification, StudentAssignment, \
    Enrollment
from users.models import User, StudentProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class StudentSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ('id', 'first_name', 'last_name', 'patronymic', 'gender')


class StudentProfileSerializer(DynamicFieldsModelSerializer):
    branch = BranchSerializer()
    student = StudentSerializer(source='user')
    short_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ('id', 'type', 'branch', 'year_of_admission', 'student', 'short_name')

    def get_short_name(self, student_profile):
        return student_profile.user.get_short_name()


class EnrollmentSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(fields=('id', 'type', 'branch', 'year_of_admission', 'student'))

    class Meta:
        model = Enrollment
        fields = ('id', 'grade', 'student_profile',)


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
        read_only_fields = ['state', 'student_id']

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


class StudentAssignmentAssigneeSerializer(StudentAssignmentSerializer):
    class Meta(StudentAssignmentSerializer.Meta):
        fields = ('pk', 'assignee',)

    def validate_assignee(self, value):
        teachers = self.instance.assignment.course.course_teachers.all()
        valid_values = {t for t in teachers if not t.roles.spectator}
        if value and value not in valid_values:
            msg = _("Invalid course teacher %s") % value
            raise serializers.ValidationError(msg)
        return value


class MyCourseSerializer(CourseSerializer):
    class Meta(CourseSerializer.Meta):
        fields = ('id', 'name', 'url', 'semester')


class MyCourseAssignmentSerializer(AssignmentSerializer):
    class Meta(AssignmentSerializer.Meta):
        fields = ('pk', 'deadline_at', 'title', 'passing_score',
                  'maximum_score', 'weight', 'ttc', 'solution_format')


class EnrollmentStudentProfileSerializer(StudentProfileSerializer):
    class Meta(StudentProfileSerializer.Meta):
        fields = ('id', 'type', 'branch', 'year_of_admission')


class MyEnrollmentSerializer(EnrollmentSerializer):
    student = StudentSerializer()
    student_profile = EnrollmentStudentProfileSerializer()

    class Meta(EnrollmentSerializer.Meta):
        fields = ('id', 'grade', 'student', 'student_profile')
