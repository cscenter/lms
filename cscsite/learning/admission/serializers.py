from rest_framework import serializers
from rest_framework.fields import TimeField

from learning.admission.models import InterviewSlot


class InterviewSlotSerializer(serializers.ModelSerializer):
    start_at = TimeField(format="%H:%M", input_formats=None)
    class Meta:
        model = InterviewSlot
        fields = ("pk", "start_at", "interview_id")
