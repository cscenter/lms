from rest_framework import serializers

from courses.api.serializers import CourseSerializer, CourseTeacherSerializer
from courses.services import group_teachers


class OfferingsCourseSerializer(CourseSerializer):
    grouped_teachers = serializers.SerializerMethodField()

    def get_grouped_teachers(self, obj):
        grouped = group_teachers(obj.course_teachers.all())
        serialized_grouped = {
            role: CourseTeacherSerializer(teachers, source="course_teachers",
                                          many=True, read_only=True).data
            for role, teachers in grouped.items()
        }
        return serialized_grouped

    class Meta(CourseSerializer.Meta):
        fields = ('name', 'url', 'is_club_course', 'is_completed', 'grouped_teachers', 'duration')
