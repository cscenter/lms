from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

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


class StudentProfileSerializer(serializers.ModelSerializer):
    branch = BranchSerializer()
    student = StudentSerializer(source='user')

    class Meta:
        model = StudentProfile
        fields = ('id', 'type', 'branch', 'year_of_admission', 'student')


class EnrollmentSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer()

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
        read_only_fields = ['state']

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
