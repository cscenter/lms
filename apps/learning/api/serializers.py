from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from learning.models import CourseNewsNotification, StudentAssignment
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


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseNewsNotification
        fields = ('user', 'is_unread', 'is_notified')


class StudentAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAssignment
        fields = ('score',)

    def validate_score(self, value):
        max_score = self.instance.assignment.maximum_score
        if value and value > max_score:
            msg = _("Score can't be larger than %s") % max_score
            raise serializers.ValidationError(msg)
        return value


class AssignmentScoreSerializer(StudentAssignmentSerializer):
    class Meta(StudentAssignmentSerializer.Meta):
        fields = ('score',)
