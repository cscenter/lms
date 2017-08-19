from rest_framework import serializers, fields

from learning.settings import FOUNDATION_YEAR
from users.models import CSCUser


class UserSearchSerializer(serializers.ModelSerializer):
    short_name = serializers.SerializerMethodField()

    class Meta:
            model = CSCUser
            fields = ('short_name', 'pk')

    def get_short_name(self, user):
        return user.get_short_name()


class FacesQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False, min_value=FOUNDATION_YEAR)
    # FIXME : move codes to settings?
    city = fields.ChoiceField(required=False, choices=['nsk', 'spb'])
