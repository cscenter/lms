from django.conf import settings
from rest_framework import serializers, fields

from core.settings.base import FOUNDATION_YEAR
from learning.settings import Branches
from users.models import User


class UserSearchSerializer(serializers.ModelSerializer):
    short_name = serializers.SerializerMethodField()

    class Meta:
            model = User
            fields = ('short_name', 'pk')

    def get_short_name(self, user):
        return user.get_short_name()


class FacesQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False, min_value=FOUNDATION_YEAR)
    branch = fields.ChoiceField(required=False, choices=Branches.choices)
