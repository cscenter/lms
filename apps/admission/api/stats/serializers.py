from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_pandas import SimpleSerializer

from learning.settings import AcademicDegreeLevels


class StageByYearSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Append course name by course enum id"""
        label = AcademicDegreeLevels.values.get(instance["level_of_education"],
                                                _("Other"))
        instance["course__name"] = label
        return instance


class ApplicationSubmissionSerializer(SimpleSerializer):
    class Meta:
        pandas_index = ['date']
