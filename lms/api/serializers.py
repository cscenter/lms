from collections import OrderedDict
from itertools import groupby

from rest_framework import serializers


class CourseSerializer(serializers.Serializer):
    def to_representation(self, obj):
        teachers = [{"url": u.teacher_profile_url(),
                     "name": u.get_abbreviated_name()} for u in
                    obj.teachers.all()]
        return {
            "name": obj.meta_course.name,
            "url": obj.get_absolute_url(),
            "is_open": obj.is_open,
            "with_video": bool(obj.videos_count),
            "with_slides": obj.materials_slides,
            "with_files": obj.materials_files,
            "teachers": teachers
        }


class CoursesSerializer(serializers.Serializer):
    def to_representation(self, obj):
        by_year = OrderedDict()
        # Group courses by (year, term_type)
        for term, courses in groupby(obj, key=lambda x: x.semester):
            slug = "{0.year}-{0.type}".format(term)
            by_year[slug] = CourseSerializer(courses, many=True).data
        return by_year