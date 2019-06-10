from django.core.cache import caches, InvalidCacheBackendError
from django.utils.encoding import force_bytes
from rest_framework import serializers

from api.utils import make_api_fragment_key
from core.utils import render_markdown
from learning.models import CourseNewsNotification, GraduateProfile
from users.api.serializers import PhotoSerializerField
from users.models import User


# FIXME: Create base AlumniSerializer. TestimonialSerializer should override Meta.fields only (and photo?)
class AlumniSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    sex = serializers.SerializerMethodField()
    photo = PhotoSerializerField(User.ThumbnailSize.BASE,
                                 thumbnail_options={"stub_official": False})
    year = serializers.IntegerField(source="graduation_year")
    city = serializers.CharField(source="city_id")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="areas_of_study")

    class Meta:
        model = User
        fields = ('id', 'name', 'sex', 'year', 'city', 'photo', 'areas')

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_sex(self, obj: User):
        return "b" if obj.gender == obj.GENDER_MALE else "g"


class GraduateProfileSerializer(serializers.ModelSerializer):
    # FIXME: add student_id?
    id = serializers.IntegerField(source="pk")
    author = serializers.SerializerMethodField()
    photo = PhotoSerializerField(User.ThumbnailSize.SQUARE,
                                 thumbnail_options={"stub_official": False})
    year = serializers.IntegerField(source="graduation_year")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="academic_disciplines")
    text = serializers.SerializerMethodField()

    class Meta:
        model = GraduateProfile
        fields = ("id", "author", "photo", "year", "areas", "text")

    def get_author(self, graduate_profile):
        return graduate_profile.student.get_full_name()

    def get_text(self, graduate_profile):
        try:
            fragment_cache = caches['markdown_fragments']
        except InvalidCacheBackendError:
            fragment_cache = caches['default']
        expire_time = 3600
        vary_on = [bytes(graduate_profile.pk),
                   force_bytes(graduate_profile.modified)]
        cache_key = make_api_fragment_key("csc_review", vary_on)
        value = fragment_cache.get(cache_key)
        if value is None:
            value = render_markdown(graduate_profile.testimonial)
            fragment_cache.set(cache_key, value, expire_time)
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class CourseNewsNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CourseNewsNotification
        fields = ('user', 'is_unread', 'is_notified')
