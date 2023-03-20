from rest_framework import serializers
from rest_framework.fields import TimeField

from django.conf import settings
from django.utils import formats

from admission.models import Campaign, InterviewSlot


class InterviewSlotBaseSerializer(serializers.ModelSerializer):
    start_at = TimeField(format="%H:%M")
    stream = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSlot
        fields = ("id", "start_at", "interview_id", "stream")

    def get_stream(self, obj):
        return formats.date_format(obj.stream.date, "SHORT_DATE_FORMAT")


class OpenRegistrationCampaignField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        if self.queryset:
            return self.queryset.all()
        return Campaign.with_open_registration().filter(
            branch__site_id=settings.SITE_ID
        )
