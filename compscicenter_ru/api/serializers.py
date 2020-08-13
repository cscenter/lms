from django.core.cache import caches, InvalidCacheBackendError
from django.utils.encoding import force_bytes
from rest_framework import serializers

from api.utils import make_api_fragment_key
from compscicenter_ru.utils import course_public_url
from core.utils import render_markdown
from courses.api.serializers import CourseSerializer
from courses.models import Course, CourseTeacher
from learning.api.serializers import StudentSerializer
from learning.models import GraduateProfile
from users.api.serializers import PhotoSerializerField
from users.models import User


class CourseRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.course.meta_course_id


class CourseTeacherRelatedField(serializers.RelatedField):
    def to_representation(self, value: CourseTeacher):
        return value.teacher.get_abbreviated_name()


class CourseVideoSerializer(CourseSerializer):
    type = serializers.CharField(default="course")
    year = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    speakers = CourseTeacherRelatedField(
        many=True, read_only=True, source="course_teachers")

    class Meta(CourseSerializer.Meta):
        fields = ('id', 'name', 'preview_url', 'url', 'type', 'year', 'speakers')

    def get_url(self, obj: Course):
        return course_public_url(obj, tab='classes')

    def get_year(self, obj: Course):
        return obj.semester.year

    def get_preview_url(self, obj: Course):
        video_id = obj.youtube_video_id
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        return ""


class TeacherSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    photo = PhotoSerializerField(User.ThumbnailSize.BASE)
    occupation = serializers.CharField(source="workplace")
    branch = serializers.CharField(source="branch.code")
    courses = CourseRelatedField(
        source="courseteacher_set", many=True, read_only=True,
        help_text="List of meta course ids. May contain duplicates")
    latest_session = serializers.SerializerMethodField(
        help_text="The latest term index when the teacher read the course")

    class Meta:
        model = User
        fields = ('id', 'name', 'occupation', 'branch', 'photo',
                  'courses', 'latest_session')

    def get_name(self, obj):
        return obj.get_full_name()

    def get_latest_session(self, obj):
        last = 0
        for t in obj.courseteacher_set.all():
            last = max(last, t.course.semester.index)
        return last


class SiteCourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="meta_course_id")
    name = serializers.SerializerMethodField()

    def get_name(self, obj: Course):
        return obj.meta_course.name

    class Meta:
        model = Course
        fields = ('id', 'name')


# TODO: add detail_url?
class GraduateProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    student = StudentSerializer(source="student_profile")
    photo = PhotoSerializerField(GraduateProfile.ThumbnailSize.BASE,
                                 thumbnail_options={"stub_official": False})
    year = serializers.IntegerField(source="graduation_year")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="academic_disciplines")
    testimonial = serializers.SerializerMethodField()

    class Meta:
        model = GraduateProfile
        fields = ("id", "student", "photo", "year", "areas", "testimonial")

    def get_testimonial(self, graduate_profile):
        try:
            fragment_cache = caches['markdown_fragments']
        except InvalidCacheBackendError:
            fragment_cache = caches['default']
        expire_time = 3600
        vary_on = [bytes(graduate_profile.pk),
                   force_bytes(graduate_profile.modified)]
        cache_key = make_api_fragment_key(GraduateProfile.TESTIMONIAL_CACHE_KEY,
                                          vary_on)
        value = fragment_cache.get(cache_key)
        if value is None:
            value = render_markdown(graduate_profile.testimonial)
            fragment_cache.set(cache_key, value, expire_time)
        return value


class AlumniSerializer(GraduateProfileSerializer):
    class Meta:
        model = GraduateProfile
        fields = ('id', 'student', 'photo', 'year', 'areas')


class TestimonialCardSerializer(GraduateProfileSerializer):
    student = serializers.SerializerMethodField()
    photo = PhotoSerializerField(User.ThumbnailSize.SQUARE,
                                 thumbnail_options={"stub_official": False})

    def get_student(self, graduate_profile):
        return graduate_profile.student_profile.user.get_full_name()


class CoursePublicSerializer(CourseSerializer):
    def get_url(self, obj: Course):
        return course_public_url(obj)

    class Meta(CourseSerializer.Meta):
        fields = ('id', 'name', 'url', 'semester', 'teachers', 'branch',
                  'materials')
