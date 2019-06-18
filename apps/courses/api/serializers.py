from rest_framework import serializers

from courses.models import Course, CourseTeacher, Semester
from users.api.serializers import PhotoSerializerField
from users.constants import ThumbnailSizes
from users.models import User


class CourseRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.course.meta_course_id


class CourseTeacherRelatedField(serializers.RelatedField):
    def to_representation(self, value: CourseTeacher):
        return value.teacher.get_abbreviated_name()


class SemesterSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    index = serializers.IntegerField()
    year = serializers.IntegerField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Semester
        fields = ("id", "index", "year", "name")

    def get_name(self, obj: Semester):
        return str(obj)


class MetaCourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="meta_course_id")
    name = serializers.SerializerMethodField()

    def get_name(self, obj: Course):
        return obj.meta_course.name

    class Meta:
        model = Course
        fields = ('id', 'name')


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    semester = SemesterSerializer()
    teachers = CourseTeacherRelatedField(
        many=True, read_only=True, source="course_teachers")

    class Meta:
        model = Course
        fields = ('id', 'name', 'url', 'semester', 'teachers')

    def get_name(self, obj: Course):
        return obj.meta_course.name

    def get_url(self, obj: Course):
        return obj.get_absolute_url()


class TeacherSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    photo = PhotoSerializerField(User.ThumbnailSize.BASE)
    city = serializers.CharField(source="city_id")
    courses = CourseRelatedField(
        source="courseteacher_set", many=True, read_only=True,
        help_text="List of meta course ids. May contain duplicates")
    latest_session = serializers.SerializerMethodField(
        help_text="The latest term index when the teacher read the course")

    class Meta:
        model = User
        fields = ('id', 'name', 'workplace', 'city', 'photo',
                  'courses', 'latest_session')

    def get_name(self, obj):
        return obj.get_full_name()

    def get_latest_session(self, obj):
        last = 0
        for t in obj.courseteacher_set.all():
            last = max(last, t.course.semester.index)
        return last
