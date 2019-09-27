from rest_framework import serializers

from learning.models import CourseNewsNotification
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
