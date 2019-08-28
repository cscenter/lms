from django.core.cache import caches, InvalidCacheBackendError
from django.utils.encoding import force_bytes
from rest_framework import serializers

from api.utils import make_api_fragment_key
from core.utils import render_markdown
from learning.models import CourseNewsNotification, GraduateProfile
from users.api.serializers import PhotoSerializerField
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class StudentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source="first_name")
    surname = serializers.CharField(source="last_name")
    branch = serializers.CharField(source="branch.code")
    sex = serializers.CharField(source="gender")

    class Meta:
        model = User
        fields = ('id', 'name', 'surname', 'patronymic', 'sex', 'branch')


# TODO: add detail_url?
class GraduateProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    student = StudentSerializer()
    photo = PhotoSerializerField(User.ThumbnailSize.BASE,
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
        return graduate_profile.student.get_full_name()


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseNewsNotification
        fields = ('user', 'is_unread', 'is_notified')
