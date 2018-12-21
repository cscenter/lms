from django.core.cache import caches, InvalidCacheBackendError
from django.utils.encoding import force_bytes
from rest_framework import serializers

from api.utils import make_api_fragment_key
from core.utils import render_markdown
from learning.models import CourseNewsNotification
from users.api.serializers import PhotoSerializerField
from users.models import User


class AlumniSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    sex = serializers.SerializerMethodField()
    photo = PhotoSerializerField("176x246")
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


class TestimonialSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    author = serializers.SerializerMethodField()
    photo = PhotoSerializerField("150x150")
    year = serializers.IntegerField(source="graduation_year")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="areas_of_study")
    text = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "author", "photo", "year", "areas", "text"]

    def get_author(self, obj):
        return obj.get_full_name()

    def get_text(self, obj):
        try:
            fragment_cache = caches['markdown_fragments']
        except InvalidCacheBackendError:
            fragment_cache = caches['default']
        expire_time = 3600
        vary_on = [bytes(obj.pk), force_bytes(obj.modified)]
        cache_key = make_api_fragment_key("csc_review", vary_on)
        value = fragment_cache.get(cache_key)
        if value is None:
            value = render_markdown(obj.csc_review)
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
