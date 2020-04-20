from django.utils import formats
from rest_framework import serializers
from rest_framework.fields import TimeField

from admission.models import InterviewSlot


class InterviewSlotSerializer(serializers.ModelSerializer):
    start_at = TimeField(format="%H:%M", input_formats=None)
    stream = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSlot
        fields = ("id", "start_at", "interview_id", "stream")

    def get_stream(self, obj):
        return formats.date_format(obj.stream.date, "SHORT_DATE_FORMAT")
