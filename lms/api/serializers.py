from courses.api.serializers import CourseSerializer


class OfferingsCourseSerializer(CourseSerializer):
    class Meta(CourseSerializer.Meta):
        fields = ('name', 'url', 'is_club_course', 'teachers')
