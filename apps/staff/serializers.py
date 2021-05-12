from rest_framework import fields, serializers

from django.conf import settings

from learning.settings import Branches


class FacesQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False,
                               min_value=settings.ESTABLISHED)
    branch = fields.ChoiceField(required=False, choices=Branches.choices)
