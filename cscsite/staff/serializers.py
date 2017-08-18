from rest_framework import serializers

from users.models import CSCUser


class UserSearchSerializer(serializers.ModelSerializer):
    short_name = serializers.SerializerMethodField()

    class Meta:
            model = CSCUser
            fields = ('short_name', 'pk')

    def get_short_name(self, user):
        return user.get_short_name()
