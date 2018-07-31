import hashlib

from django.core.cache import caches, InvalidCacheBackendError
from django.core.cache.utils import make_template_fragment_key
from django.utils.encoding import force_bytes
from django.utils.http import urlquote
from rest_framework import serializers

from core.utils import render_markdown
from users.models import CSCUser


API_FRAGMENT_KEY_TEMPLATE = 'api.cache.%s.%s'


def make_api_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(urlquote(var) for var in vary_on)
    args = hashlib.md5(force_bytes(key))
    return API_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())


class PhotoSerializerField(serializers.Field):
    def __init__(self, photo_dimensions, **kwargs):
        self.photo_dimensions = photo_dimensions
        super().__init__(**kwargs)

    def get_attribute(self, obj):
        return obj

    def to_internal_value(self, data):
        pass

    def to_representation(self, obj):
        # TODO: move size to settings?
        image = obj.get_thumbnail(self.photo_dimensions, use_stub=False)
        if image:
            return image.url
        else:
            return None


class AlumniSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    sex = serializers.SerializerMethodField()
    photo = PhotoSerializerField("170x238")
    year = serializers.IntegerField(source="graduation_year")
    city = serializers.CharField(source="city_id")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="areas_of_study")

    class Meta:
        model = CSCUser
        fields = ('id', 'name', 'sex', 'year', 'city', 'photo', 'areas')

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_sex(self, obj: CSCUser):
        return "m" if obj.gender == obj.GENDER_MALE else "f"


class TestimonialSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    author = serializers.SerializerMethodField()
    photo = PhotoSerializerField("150x150")
    year = serializers.IntegerField(source="graduation_year")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True,
                                               source="areas_of_study")
    text = serializers.SerializerMethodField()

    class Meta:
        model = CSCUser
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

