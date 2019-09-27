from rest_framework import serializers, fields

from core.settings.base import FOUNDATION_YEAR
from learning.settings import Branches


class FacesQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False, min_value=FOUNDATION_YEAR)
    branch = fields.ChoiceField(required=False, choices=Branches.choices)
