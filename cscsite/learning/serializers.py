from rest_framework import serializers

from learning.models import CourseOfferingNewsNotification
from users.models import CSCUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CSCUser
        fields = ('first_name', 'last_name')


class CourseOfferingNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseOfferingNewsNotification
        fields = ('user', 'is_unread', 'is_notified')
