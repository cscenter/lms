from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from rest_pandas import SimpleSerializer

from learning.settings import AcademicDegreeYears
from users.models import User


class StageByYearSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Append course name by course enum id"""
        label = AcademicDegreeYears.values.get(instance["course"], _("Other"))
        instance["course__name"] = label
        return instance


class AnnotatedApplicationSubmissionSerializer(SimpleSerializer):
    class Meta:
        pandas_index = ['day', 'month', 'year']


class ApplicationSubmissionSerializer(SimpleSerializer):
    class Meta:
        pandas_index = ['date']
