from rest_framework import serializers

from users.models import User


class UserSearchSerializer(serializers.ModelSerializer):
    short_name = serializers.SerializerMethodField()

    class Meta:
            model = User
            fields = ('short_name', 'pk')

    def get_short_name(self, user):
        return user.get_short_name()
