from collections import OrderedDict
from itertools import groupby
from rest_framework import serializers

from learning.models import CourseOffering
from users.models import CSCUser


class TeacherSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        return {
            "url": instance.teacher_profile_url(),
            "name": instance.get_abbreviated_name()
        }

    class Meta:
        model = CSCUser
        fields = ["name", "url"]


class CourseSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    teachers = TeacherSerializer(many=True)
    is_open = serializers.BooleanField()
    with_video = serializers.BooleanField(source="materials_video")
    with_slides = serializers.BooleanField(source="materials_slides")
    with_files = serializers.BooleanField(source="materials_files")

    class Meta:
        model = CourseOffering
        fields = ["name", "url", "is_open", "teachers", "with_video",
                  "with_slides", "with_files"]

    def get_name(self, obj):
        return obj.course.name

    def get_url(self, obj):
        return obj.get_absolute_url()


class CourseOfferingSerializer(serializers.Serializer):
    def to_representation(self, obj):
        by_year = OrderedDict()
        # Group courses by (year, term_type)
        for term, courses in groupby(obj, key=lambda x: x.semester):
            slug = "{0.year}-{0.type}".format(term)
            by_year[slug] = CourseSerializer(courses, many=True).data
        return by_year
