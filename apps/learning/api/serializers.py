from rest_framework import serializers

from django.utils.translation import gettext_lazy as _

from api.utils import DynamicFieldsModelSerializer
from core.api.serializers import BranchSerializer
from courses.api.serializers import BaseAssignmentSerializer, CourseSerializer
from learning.models import CourseNewsNotification, Enrollment, StudentAssignment
from users.models import StudentProfile, User


class UserSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'patronymic', 'gender')


class StudentProfileSerializer(DynamicFieldsModelSerializer):
    branch = BranchSerializer()
    student = UserSerializer(source='user', fields=('id', 'first_name', 'last_name', 'patronymic', 'gender'))
    # TODO: remove
    short_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ('id', 'type', 'status', 'branch', 'year_of_admission', 'year_of_curriculum',
                  'student', 'short_name')

    def get_short_name(self, student_profile):
        return student_profile.user.get_short_name()


class EnrollmentSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(fields=('id', 'type', 'branch', 'year_of_admission', 'student'))

    class Meta:
        model = Enrollment
        fields = ('id', 'grade', 'student_profile',)


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(fields=('first_name', 'last_name'))

    class Meta:
        model = CourseNewsNotification
        fields = ('user', 'is_unread', 'is_notified')


class BaseStudentAssignmentSerializer(serializers.ModelSerializer):
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


class AssignmentScoreSerializer(BaseStudentAssignmentSerializer):
    class Meta(BaseStudentAssignmentSerializer.Meta):
        fields = ('score',)


class StudentAssignmentAssigneeSerializer(BaseStudentAssignmentSerializer):
    class Meta(BaseStudentAssignmentSerializer.Meta):
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


class CourseAssignmentSerializer(BaseAssignmentSerializer):
    class Meta(BaseAssignmentSerializer.Meta):
        fields = ('id', 'deadline_at', 'title', 'passing_score',
                  'maximum_score', 'weight', 'ttc', 'solution_format')


class EnrollmentStudentProfileSerializer(StudentProfileSerializer):
    class Meta(StudentProfileSerializer.Meta):
        fields = ('id', 'type', 'branch', 'year_of_admission')


class MyEnrollmentSerializer(EnrollmentSerializer):
    student = UserSerializer(fields=('id', 'first_name', 'last_name', 'patronymic'))
    student_profile = EnrollmentStudentProfileSerializer()

    class Meta(EnrollmentSerializer.Meta):
        fields = ('id', 'grade', 'student', 'student_profile')
