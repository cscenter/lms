from rest_framework import serializers

from learning.models import CourseOfferingNewsNotification
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseOfferingNewsNotification
        fields = ('user', 'is_unread', 'is_notified')
