from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from users.models import CSCUser


class StageByYearSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Append course name by course enum id"""
        if instance["course"] in CSCUser.COURSES:
            instance["course__name"] = CSCUser.COURSES[instance["course"]]
        else:
            instance["course__name"] = _("Other")
        return instance
