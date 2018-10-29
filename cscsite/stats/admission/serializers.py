from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from rest_pandas import SimpleSerializer

from users.models import User


class StageByYearSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Append course name by course enum id"""
        if instance["course"] in User.COURSES:
            instance["course__name"] = User.COURSES[instance["course"]]
        else:
            instance["course__name"] = _("Other")
        return instance


class ApplicationSubmissionSerializer(SimpleSerializer):
    class Meta:
        pandas_index = ['date']
