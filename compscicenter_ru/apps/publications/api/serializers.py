from rest_framework import serializers

from compscicenter_ru.api.serializers import CourseVideoSerializer
from publications.models import RecordedEvent, Speaker


class SpeakersRelatedField(serializers.RelatedField):
    def to_representation(self, value: Speaker):
        return value.abbreviated_name


class RecordedEventSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="lecture")
    year = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    # preview_url = serializers.SerializerMethodField()
    speakers = SpeakersRelatedField(many=True, read_only=True)

    class Meta(CourseVideoSerializer.Meta):
        model = RecordedEvent

    def get_url(self, obj: RecordedEvent):
        return obj.get_absolute_url()

    def get_year(self, obj: RecordedEvent):
        return obj.date_at.year